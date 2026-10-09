"""Tests de app/main.py::ConnectionManager — el manejador de las conexiones
WebSocket que retransmite nuevo_pin / pin_eliminado a todos los navegadores
conectados.

REQUIERE: fastapi, sqlalchemy, python-jose, httpx instalados.
Correr con:  python -m unittest tests.test_websocket_manager -v
"""

import os
import sys
import unittest

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

import main  # noqa: E402


class FakeWebSocket:
    """Doble de prueba: no abre ningún socket real, solo registra llamadas."""

    def __init__(self, fail_on_send=False):
        self.accepted = False
        self.sent = []
        self.fail_on_send = fail_on_send

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        if self.fail_on_send:
            raise ConnectionResetError("cliente desconectado a la fuerza")
        self.sent.append(data)


class ConnectionManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_accepts_and_registers_the_socket(self):
        manager = main.ConnectionManager()
        ws = FakeWebSocket()
        await manager.connect(ws)
        self.assertTrue(ws.accepted)
        self.assertIn(ws, manager.active)

    async def test_disconnect_removes_a_registered_socket(self):
        manager = main.ConnectionManager()
        ws = FakeWebSocket()
        await manager.connect(ws)
        manager.disconnect(ws)
        self.assertNotIn(ws, manager.active)

    async def test_disconnect_on_an_unregistered_socket_does_not_raise(self):
        manager = main.ConnectionManager()
        manager.disconnect(FakeWebSocket())  # nunca conectado; no debe explotar

    async def test_broadcast_sends_the_same_payload_to_every_connected_socket(self):
        manager = main.ConnectionManager()
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await manager.connect(ws1)
        await manager.connect(ws2)

        payload = {"tipo": "nuevo_pin", "casa": {"id": 1}}
        await manager.broadcast(payload)

        self.assertEqual(ws1.sent, [payload])
        self.assertEqual(ws2.sent, [payload])

    async def test_broadcast_prunes_sockets_that_fail_to_send(self):
        # Esta es la lógica real que protege el servidor: si un cliente se
        # desconectó abruptamente, el próximo broadcast() no debe reventar
        # para TODOS los demás clientes, y el socket muerto debe salir del
        # set `active` para no reintentarlo por siempre.
        manager = main.ConnectionManager()
        vivo = FakeWebSocket()
        muerto = FakeWebSocket(fail_on_send=True)
        await manager.connect(vivo)
        await manager.connect(muerto)

        await manager.broadcast({"tipo": "ping"})

        self.assertEqual(vivo.sent, [{"tipo": "ping"}])
        self.assertNotIn(muerto, manager.active)
        self.assertIn(vivo, manager.active)

    async def test_broadcast_with_no_connections_does_not_raise(self):
        manager = main.ConnectionManager()
        await manager.broadcast({"tipo": "pin_eliminado", "id": 1})


if __name__ == "__main__":
    unittest.main()
