from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

import app
import database
from contato import CONTATOS


class ContactApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        db_path = f"{self.temp_dir.name}/contacts.sqlite3"
        self.test_engine = database.create_database_engine(f"sqlite:///{db_path}")
        self.previous_session_factory = database.SessionLocal
        database.SessionLocal = sessionmaker(bind=self.test_engine, expire_on_commit=False)
        database.initialize_database(self.test_engine)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.AplicacaoHandler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        with app.estado_lock:
            app.estado.update({
                "running": False,
                "completed": False,
                "total": 0,
                "processed": 0,
                "current": None,
                "results": [],
                "error": None,
            })

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.test_engine.dispose()
        database.SessionLocal = self.previous_session_factory
        self.temp_dir.cleanup()

    def request_json(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_legacy_contacts_are_imported_and_listed(self) -> None:
        status, response = self.request_json("GET", "/api/contacts")
        self.assertEqual(status, 200)
        self.assertEqual(response["total"], len(CONTATOS))
        self.assertEqual(len(response["contacts"]), len(CONTATOS))
        self.assertTrue(all(item["id"] > 0 for item in response["contacts"]))

    def test_contact_can_be_created_updated_and_deleted(self) -> None:
        status, created = self.request_json("POST", "/api/contacts", {
            "nome": "Contato de teste",
            "telefone": "+5511999990000",
        })
        self.assertEqual(status, 201)
        contact_id = created["contact"]["id"]

        status, updated = self.request_json("PUT", f"/api/contacts/{contact_id}", {
            "nome": "Contato atualizado",
            "telefone": "+5511999990001",
        })
        self.assertEqual(status, 200)
        self.assertEqual(updated["contact"]["nome"], "Contato atualizado")
        self.assertEqual(updated["contact"]["telefone"], "+5511999990001")

        status, deleted = self.request_json("DELETE", f"/api/contacts/{contact_id}")
        self.assertEqual(status, 200)
        self.assertTrue(deleted["success"])
        status, response = self.request_json("PUT", f"/api/contacts/{contact_id}", {
            "nome": "Não existe",
            "telefone": "+5511999990002",
        })
        self.assertEqual(status, 404)
        self.assertIn("error", response)

    def test_invalid_phone_is_rejected(self) -> None:
        status, response = self.request_json("POST", "/api/contacts", {
            "nome": "Contato inválido",
            "telefone": "11999990000",
        })
        self.assertEqual(status, 400)
        self.assertIn("telefone", response["error"])

    def test_contacts_are_not_reimported_after_all_are_deleted(self) -> None:
        with database.SessionLocal.begin() as session:
            session.execute(delete(database.Contact))

        imported = database.initialize_database(self.test_engine)
        rows = database.SessionLocal().scalars(select(database.Contact.id)).all()
        self.assertEqual(imported, 0)
        self.assertEqual(rows, [])

    def test_contact_mutations_are_blocked_during_a_send(self) -> None:
        with app.estado_lock:
            app.estado["running"] = True
        try:
            status, response = self.request_json("POST", "/api/contacts", {
                "nome": "Não cadastrar durante envio",
                "telefone": "+5511999990003",
            })
        finally:
            with app.estado_lock:
                app.estado["running"] = False
        self.assertEqual(status, 409)
        self.assertIn("envio", response["error"])


if __name__ == "__main__":
    unittest.main()
