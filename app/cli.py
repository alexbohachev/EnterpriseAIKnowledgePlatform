"""Bootstrap first user without hardcoding passwords or exposing registration endpoint."""
import argparse
from getpass import getpass
import sys
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .config import Settings
from .db import make_session_factory
from .models import User
from .security import hash_password


def main():
    parser = argparse.ArgumentParser(description="EAKP local administrator bootstrap")
    parser.add_argument("create-user", choices=["create-user"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=["admin", "reader"], default="admin")
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\n") if args.password_stdin else getpass("Password: ")
    try:
        digest = hash_password(password)
    except ValueError as exc:
        parser.error(str(exc))
    cfg = Settings()
    _, factory = make_session_factory(cfg.database_url)
    with factory() as db:
        user = User(email=args.email.strip().lower(), password_hash=digest, role=args.role)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            parser.error("User already exists or migrations are not applied")
        print(f"Created {args.role} {user.email} (id={user.id})")


if __name__ == "__main__":
    main()
