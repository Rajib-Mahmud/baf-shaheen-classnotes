"""Create the first Super Admin account.

Usage (from the project root, venv active):
    python scripts/seed_admin.py <login_id> <full name>

The password is prompted (hidden) so it never lands in shell history.
The account is created with must_change_password=False.
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import Role, User


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/seed_admin.py <login_id> <full name>")
        sys.exit(1)

    login_id = sys.argv[1].strip()
    full_name = " ".join(sys.argv[2:]).strip()

    app = create_app()
    with app.app_context():
        if db.session.scalar(db.select(User).filter_by(role=Role.SUPER_ADMIN)):
            print("A Super Admin already exists. Aborting.")
            sys.exit(1)
        if db.session.scalar(db.select(User).filter_by(login_id=login_id)):
            print(f"Login ID '{login_id}' is already taken. Aborting.")
            sys.exit(1)

        password = getpass.getpass("Password for the Super Admin: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match. Aborting.")
            sys.exit(1)
        if len(password) < 8:
            print("Password must be at least 8 characters. Aborting.")
            sys.exit(1)

        admin = User(
            login_id=login_id,
            full_name=full_name,
            role=Role.SUPER_ADMIN,
            must_change_password=False,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Super Admin '{login_id}' created.")


if __name__ == "__main__":
    main()
