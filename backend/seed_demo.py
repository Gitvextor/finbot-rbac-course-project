"""
Seed company RBAC demo accounts and documents.

Usage:
    cd backend
    python seed_demo.py
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from api.demo import DEMO_ACCOUNTS, seed_demo_data
from database import init_db, SessionLocal


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = seed_demo_data(db)
        print(result["message"])
        print("\nCompany demo credentials:")
        for account in DEMO_ACCOUNTS:
            print(
                f"  {account['label']:<8} "
                f"{account['username']:<14} / {account['password']:<12} "
                f"chat_role={account['chat_role']}"
            )
        print(f"\nDocuments ready: {len(result['documents'])}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
