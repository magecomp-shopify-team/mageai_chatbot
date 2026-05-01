#!/usr/bin/env python3
"""Create or update master admin credentials and write hashed password to .env."""
import getpass
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import base64
import hashlib

import bcrypt


def _prepare(plain: str) -> bytes:
    return base64.b64encode(hashlib.sha256(plain.encode()).digest())
ENV_PATH = Path(".env")


def _read_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    lines = ENV_PATH.read_text().splitlines()
    env: dict[str, str] = {}
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _write_env(env: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in env.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n")
    print(f"✓ Written to {ENV_PATH}")


def main() -> None:
    print("=== Master Admin Setup ===\n")

    password = getpass.getpass("Enter admin password (min 12 chars): ")
    if len(password) < 12:
        print("Error: password must be at least 12 characters.")
        sys.exit(1)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: passwords do not match.")
        sys.exit(1)

    hashed = bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=12)).decode()
    print(f"\nBcrypt hash generated.")

    env = _read_env()
    env["MASTER_ADMIN_PASSWORD_HASH"] = hashed

    if not env.get("AUTH_SECRET_KEY") or env["AUTH_SECRET_KEY"].startswith("replace"):
        env["AUTH_SECRET_KEY"] = secrets.token_hex(32)
        print("✓ AUTH_SECRET_KEY generated")

    if not env.get("CSRF_SECRET_KEY") or env["CSRF_SECRET_KEY"].startswith("replace"):
        env["CSRF_SECRET_KEY"] = secrets.token_hex(32)
        print("✓ CSRF_SECRET_KEY generated")

    _write_env(env)
    print("\n✓ Admin setup complete. Run: uvicorn src.api.main:app --reload")


if __name__ == "__main__":
    main()
