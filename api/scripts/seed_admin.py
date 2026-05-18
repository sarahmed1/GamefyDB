"""Seed an initial admin user.

Usage:
    python -m api.scripts.seed_admin --email <addr> --password <pw>
    # or rely on env vars GAMEFYDB_SEED_EMAIL / GAMEFYDB_SEED_PASSWORD

Idempotent: if the email already exists, the script reports it and exits 0.
"""
import argparse
import asyncio
import os
import sys

from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import UserAlreadyExists

from api.auth.manager import UserManager
from api.db import async_session_maker
from api.models import User
from api.schemas import UserCreate


async def _seed(email: str, password: str) -> int:
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        manager = UserManager(user_db)
        try:
            user = await manager.create(UserCreate(email=email, password=password, role="admin"), safe=False)
            await session.commit()
            print(f"created admin user: {user.email}")
            return 0
        except UserAlreadyExists:
            print(f"admin already exists: {email}")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=os.environ.get("GAMEFYDB_SEED_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("GAMEFYDB_SEED_PASSWORD"))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("error: --email and --password are required (or set GAMEFYDB_SEED_EMAIL / GAMEFYDB_SEED_PASSWORD)", file=sys.stderr)
        return 2

    return asyncio.run(_seed(args.email, args.password))


if __name__ == "__main__":
    sys.exit(main())
