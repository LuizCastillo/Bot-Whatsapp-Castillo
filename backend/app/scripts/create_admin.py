"""Cria (ou promove) o primeiro administrador.

Uso:  python -m app.scripts.create_admin --email voce@exemplo.com --nome "Seu Nome"
A senha é lida do prompt (ou da variável ADMIN_PASSWORD). Mínimo de 10 caracteres.
"""
import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.config.settings import get_settings
from app.database.enums import Papel
from app.database.models import Atendente
from app.database.session import make_session_factory
from app.services import auth


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--nome", required=True)
    args = p.parse_args()
    senha = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Senha: ")
    if len(senha) < auth.MIN_PASSWORD:
        print(f"A senha precisa ter ao menos {auth.MIN_PASSWORD} caracteres.", file=sys.stderr)
        return 1
    factory = make_session_factory(get_settings())
    async with factory() as s:
        async with s.begin():
            a = await s.scalar(select(Atendente).where(Atendente.email == args.email.lower()))
            if a:
                a.senha_hash, a.papel, a.ativo = auth.hash_password(senha), Papel.ADMIN, True
                print("Usuário existente atualizado como ADMIN.")
            else:
                s.add(Atendente(nome=args.nome, email=args.email.lower(), senha_hash=auth.hash_password(senha), papel=Papel.ADMIN))
                print("Administrador criado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
