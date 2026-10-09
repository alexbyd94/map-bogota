"""Tests de las funciones de autenticación en app/main.py.

REQUIERE: fastapi, python-jose, sqlalchemy, httpx instalados (los de
requirements.txt) — importar main.py los necesita todos, aunque estos tests
solo tocan las funciones JWT/auth, que no requieren una base de datos viva.

Correr con:  python -m unittest tests.test_auth -v
"""

import os
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

from fastapi import HTTPException
from jose import jwt as jose_jwt

import main  # noqa: E402


class CrearYVerificarJwtTests(unittest.TestCase):
    def test_roundtrip_preserves_the_payload(self):
        token = main.crear_jwt({"sub": "42", "email": "a@b.com"})
        decoded = main.verificar_jwt(token)
        self.assertEqual(decoded["sub"], "42")
        self.assertEqual(decoded["email"], "a@b.com")

    def test_token_expires_roughly_jwt_expire_days_from_now(self):
        token = main.crear_jwt({"sub": "1"})
        # Decodificamos crudo (sin pasar por verificar_jwt) solo para leer "exp".
        raw = jose_jwt.decode(token, main.JWT_SECRET, algorithms=[main.JWT_ALGORITHM])
        expected = datetime.utcnow() + timedelta(days=main.JWT_EXPIRE_DAYS)
        actual = datetime.utcfromtimestamp(raw["exp"])
        self.assertLess(abs((actual - expected).total_seconds()), 5)

    def test_garbage_token_returns_none(self):
        self.assertIsNone(main.verificar_jwt("esto-no-es-un-jwt"))

    def test_token_signed_with_wrong_secret_returns_none(self):
        forged = jose_jwt.encode({"sub": "1"}, "otro-secreto-cualquiera", algorithm=main.JWT_ALGORITHM)
        self.assertIsNone(main.verificar_jwt(forged))

    def test_expired_token_returns_none(self):
        expired = jose_jwt.encode(
            {"sub": "1", "exp": datetime.utcnow() - timedelta(days=1)},
            main.JWT_SECRET, algorithm=main.JWT_ALGORITHM,
        )
        self.assertIsNone(main.verificar_jwt(expired))

    def test_token_without_exp_claim_is_still_valid(self):
        # crear_jwt siempre agrega "exp", pero verificar_jwt no debería
        # exigirlo si algún día alguien genera un token a mano sin esa clave.
        no_exp = jose_jwt.encode({"sub": "1"}, main.JWT_SECRET, algorithm=main.JWT_ALGORITHM)
        self.assertEqual(main.verificar_jwt(no_exp)["sub"], "1")


class UsuarioActualTests(unittest.TestCase):
    def test_no_cookie_returns_none(self):
        self.assertIsNone(main.usuario_actual(auth_token=None))

    def test_valid_cookie_returns_the_payload(self):
        token = main.crear_jwt({"sub": "7"})
        result = main.usuario_actual(auth_token=token)
        self.assertEqual(result["sub"], "7")

    def test_invalid_cookie_returns_none_not_an_exception(self):
        # usuario_actual no debe propagar la excepción de jose; debe devolver
        # None y dejar que requiere_auth decida si eso es un 401.
        self.assertIsNone(main.usuario_actual(auth_token="basura"))


class RequiereAuthTests(unittest.TestCase):
    def test_raises_401_when_there_is_no_user(self):
        with self.assertRaises(HTTPException) as ctx:
            main.requiere_auth(usuario=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_returns_the_user_dict_unchanged_when_present(self):
        usuario = {"sub": "3", "email": "x@y.com"}
        self.assertEqual(main.requiere_auth(usuario=usuario), usuario)


if __name__ == "__main__":
    unittest.main()
