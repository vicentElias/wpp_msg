"""Servidor local da interface e da automação de saudações."""

from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Formatter
import json
import threading
from urllib.parse import urlsplit

from contato import CONTATOS
from whatsapp_saudar import enviar_mensagens, telefone_valido


HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
ASSETS = {
    "/": "index.html",
    "/index.html": "index.html",
    "/style.css": "style.css",
    "/app.js": "app.js",
}

estado_lock = threading.Lock()
estado: dict[str, object] = {
    "running": False,
    "completed": False,
    "total": 0,
    "processed": 0,
    "current": None,
    "results": [],
    "error": None,
}


def contatos_validos() -> list[dict[str, object]]:
    return [
        {"id": indice, "nome": str(contato["nome"]).strip(), "telefone": str(contato["telefone"]).strip()}
        for indice, contato in enumerate(CONTATOS)
        if str(contato.get("nome", "")).strip()
        and telefone_valido(str(contato.get("telefone", "")).strip())
    ]


def snapshot_estado() -> dict[str, object]:
    with estado_lock:
        return {**estado, "results": list(estado["results"])}


def validar_modelo(modelo: object) -> str:
    if not isinstance(modelo, str) or not modelo.strip() or len(modelo) > 4000:
        raise ValueError("Informe uma mensagem com até 4.000 caracteres.")

    try:
        for _, campo, formato, conversao in Formatter().parse(modelo):
            if campo is not None and (
                campo not in {"nome", "saudacao"} or formato or conversao
            ):
                raise ValueError("Use somente os campos {nome} e {saudacao}.")
    except ValueError as erro:
        if str(erro) == "Use somente os campos {nome} e {saudacao}.":
            raise
        raise ValueError("O modelo contém chaves de formatação inválidas.") from erro
    return modelo


def validar_inteiro(dados: dict[str, object], campo: str, minimo: int, maximo: int) -> int:
    valor = dados.get(campo)
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValueError(f"O campo {campo} deve ser um número entre {minimo} e {maximo}.")
    return valor


def executar_envio(
    destinatarios: list[dict[str, str]],
    modelo: str,
    intervalo_minimo: int,
    intervalo_maximo: int,
    tempo_de_espera: int,
) -> None:
    def atualizar(resultado: dict[str, object]) -> None:
        with estado_lock:
            estado["current"] = resultado
            if resultado["status"] in {"concluido", "erro"}:
                estado["processed"] = int(estado["processed"]) + 1
                resultados = list(estado["results"])
                resultados.append(resultado)
                estado["results"] = resultados

    try:
        enviar_mensagens(
            contatos=destinatarios,
            texto_padrao=modelo,
            intervalo_minimo=intervalo_minimo,
            intervalo_maximo=intervalo_maximo,
            tempo_de_espera=tempo_de_espera,
            ao_atualizar=atualizar,
        )
    except Exception as erro:
        with estado_lock:
            estado["error"] = str(erro)
    finally:
        with estado_lock:
            estado["running"] = False
            estado["completed"] = True
            estado["current"] = None


class AplicacaoHandler(BaseHTTPRequestHandler):
    server_version = "SaudacoesLocal/1.0"

    def responder_json(self, status: int, dados: dict[str, object]) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:
        caminho = urlsplit(self.path).path
        if caminho == "/api/contacts":
            contatos = contatos_validos()
            self.responder_json(200, {"contacts": contatos, "total": len(contatos)})
            return
        if caminho == "/api/status":
            self.responder_json(200, snapshot_estado())
            return

        arquivo = ASSETS.get(caminho)
        if arquivo is None:
            self.responder_json(404, {"error": "Recurso não encontrado."})
            return
        corpo = (ROOT / arquivo).read_bytes()
        tipo = "text/css" if arquivo.endswith(".css") else "text/javascript" if arquivo.endswith(".js") else "text/html"
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(corpo)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/start":
            self.responder_json(404, {"error": "Recurso não encontrado."})
            return

        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if tamanho < 1 or tamanho > 100_000:
                raise ValueError("A solicitação está vazia ou excede o limite permitido.")
            dados = json.loads(self.rfile.read(tamanho))
            if not isinstance(dados, dict):
                raise ValueError("Formato de solicitação inválido.")

            indices = dados.get("indices")
            contatos = contatos_validos()
            if not isinstance(indices, list) or not indices:
                raise ValueError("Selecione pelo menos um contato.")
            if len(indices) > len(contatos) or any(
                type(indice) is not int or indice not in {item["id"] for item in contatos}
                for indice in indices
            ):
                raise ValueError("A seleção contém contatos inválidos.")

            modelo = validar_modelo(dados.get("texto_padrao"))
            intervalo_minimo = validar_inteiro(dados, "intervalo_minimo", 0, 3600)
            intervalo_maximo = validar_inteiro(dados, "intervalo_maximo", 0, 3600)
            tempo_de_espera = validar_inteiro(dados, "tempo_de_espera", 1, 120)
            if intervalo_minimo > intervalo_maximo:
                raise ValueError("O intervalo mínimo não pode superar o máximo.")
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as erro:
            self.responder_json(400, {"error": str(erro)})
            return

        selecionados = set(indices)
        destinatarios = [
            {"nome": str(contato["nome"]), "telefone": str(contato["telefone"])}
            for contato in contatos
            if contato["id"] in selecionados
        ]

        with estado_lock:
            if estado["running"]:
                self.responder_json(409, {"error": "Já existe um envio em andamento."})
                return
            estado.update({
                "running": True,
                "completed": False,
                "total": len(destinatarios),
                "processed": 0,
                "current": None,
                "results": [],
                "error": None,
            })
            worker: Callable[..., None] = executar_envio
            threading.Thread(
                target=worker,
                args=(destinatarios, modelo, intervalo_minimo, intervalo_maximo, tempo_de_espera),
                daemon=True,
            ).start()

        self.responder_json(202, {"status": snapshot_estado()})

    def log_message(self, formato: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {formato % args}")


if __name__ == "__main__":
    servidor = ThreadingHTTPServer((HOST, PORT), AplicacaoHandler)
    print(f"Interface disponível em http://{HOST}:{PORT}")
    print("Pressione Ctrl+C para encerrar a aplicação.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nAplicação encerrada.")
    finally:
        servidor.server_close()