"""
Envio automatizado de saudações pelo WhatsApp Web usando pywhatkit.

Use somente com contatos que autorizaram previamente o recebimento das mensagens.
O script abre o WhatsApp Web no navegador padrão; não usa API paga.
"""

from datetime import datetime
import random
import re
import time
from urllib.parse import quote
import webbrowser
from collections.abc import Callable

# ============================================================
# CONFIGURAÇÕES EDITÁVEIS
# ============================================================



# Informe os telefones no formato internacional, sem espaços ou pontuação.
# Exemplo para o Brasil: +5516999999999
CONTATOS = [
    {"nome": "Vicente Elias ", "telefone": "+5516991023030"},
]

# Texto padrão da mensagem. Use {saudacao} para a saudação conforme o horário
# (Bom dia / Boa tarde / Boa noite) e {nome} para o nome do contato.
TEXTO_PADRAO = (
    "{saudacao}, {nome}! 😊\n"
    "Passando para falar com você. "
    "Caso esteja precisando de cotação, me chama por aqui. "
    "Vou ficar à disposição para te atender!"
)

# Intervalo aleatório entre mensagens, em segundos.
INTERVALO_MINIMO = 15


INTERVALO_MAXIMO = 30

# Tempo para o WhatsApp Web carregar a conversa antes do envio.
TEMPO_DE_ESPERA_PARA_CARREGAR = 20


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def saudacao_atual() -> str:
    """Retorna a saudação conforme a hora local do computador."""
    hora = datetime.now().hour

    if 5 <= hora < 12:
        return "Bom dia"
    if 12 <= hora < 18:
        return "Boa tarde"
    return "Boa noite"


def telefone_valido(telefone: str) -> bool:
    """Valida minimamente o formato internacional, como +5516999999999."""
    return bool(re.fullmatch(r"\+\d{10,15}", telefone))


def montar_mensagem(nome: str, texto_padrao: str | None = None) -> str:
    """Monta a mensagem final substituindo {saudacao} e {nome}."""
    modelo = TEXTO_PADRAO if texto_padrao is None else texto_padrao
    return modelo.format(saudacao=saudacao_atual(), nome=nome)


def enviar_mensagem_whatsapp(
    telefone: str,
    mensagem: str,
    tempo_de_espera: int,
) -> None:
    """Abre a conversa, foca o WhatsApp Web e envia a mensagem."""
    # A automação gráfica só é necessária durante um envio, não para iniciar a API.
    import pyautogui

    url = (
        f"https://web.whatsapp.com/send?phone={telefone}"
        f"&text={quote(mensagem)}"
    )
    webbrowser.open(url)

    # Aguarda a conversa carregar completamente antes de focar o compositor.
    time.sleep(tempo_de_espera)

    pyautogui.press("tab")   # Pequena pausa antes de focar o campo de mensagem.
    time.sleep(0.5)

    pyautogui.press("enter")   # Foca o campo de mensagem.
    time.sleep(3)
    #largura, altura = pyautogui.size()
    # O campo de mensagem fica na faixa inferior da janela, não no centro.
    #pyautogui.click(largura // 2, altura - 45)
    #time.sleep(0.5)
    #pyautogui.press("enter")
    #time.sleep(3)
    pyautogui.hotkey("ctrl", "w")


def enviar_mensagens(
    contatos: list[dict[str, str]] | None = None,
    texto_padrao: str | None = None,
    intervalo_minimo: int | None = None,
    intervalo_maximo: int | None = None,
    tempo_de_espera: int | None = None,
    ao_atualizar: Callable[[dict[str, object]], None] | None = None,
) -> None:
    """Abre cada conversa no WhatsApp Web e envia a mensagem correspondente."""
    lista_contatos = CONTATOS if contatos is None else contatos
    if not lista_contatos:
        print("A lista CONTATOS está vazia. Adicione pelo menos um contato.")
        return

    minimo = INTERVALO_MINIMO if intervalo_minimo is None else intervalo_minimo
    maximo = INTERVALO_MAXIMO if intervalo_maximo is None else intervalo_maximo
    espera = (
        TEMPO_DE_ESPERA_PARA_CARREGAR
        if tempo_de_espera is None
        else tempo_de_espera
    )

    for indice, contato in enumerate(lista_contatos, start=1):
        nome = str(contato["nome"]).strip()
        telefone = str(contato["telefone"]).strip()

        if not nome or not telefone_valido(telefone):
            print(
                f"[{indice}/{len(CONTATOS)}] Ignorado: dados inválidos "
                f"({nome!r}, {telefone!r})."
            )
            continue

        mensagem = montar_mensagem(nome, texto_padrao)
        print(f"[{indice}/{len(lista_contatos)}] Enviando para {nome} ({telefone})...")
        if ao_atualizar:
            ao_atualizar({
                "indice": indice,
                "total": len(lista_contatos),
                "nome": nome,
                "telefone": telefone,
                "status": "enviando",
            })

        try:
            enviar_mensagem_whatsapp(
                telefone=telefone,
                mensagem=mensagem,
                tempo_de_espera=espera,
            )

            print("Mensagem enviada (ou entregue ao fluxo do navegador).")
            if ao_atualizar:
                ao_atualizar({
                    "indice": indice,
                    "total": len(lista_contatos),
                    "nome": nome,
                    "telefone": telefone,
                    "status": "concluido",
                })
        except Exception as erro:
            # Continua com os próximos contatos em vez de interromper tudo.
            print(f"Erro ao enviar para {nome}: {erro}")
            if ao_atualizar:
                ao_atualizar({
                    "indice": indice,
                    "total": len(lista_contatos),
                    "nome": nome,
                    "telefone": telefone,
                    "status": "erro",
                    "erro": str(erro),
                })

        # Não espera depois do último contato.
        if indice < len(lista_contatos):
            intervalo = random.randint(minimo, maximo)
            print(f"Aguardando {intervalo} segundos antes do próximo envio...")
            time.sleep(intervalo)


if __name__ == "__main__":
    print("Iniciando automação do WhatsApp Web...")
    print(f"Saudação selecionada: {saudacao_atual()}.")
    print("Não interaja com o navegador enquanto os envios estiverem em andamento.\n")
    enviar_mensagens()
    print("\nProcesso concluído.")
