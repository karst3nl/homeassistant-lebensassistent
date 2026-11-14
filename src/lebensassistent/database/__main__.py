"""Explizites lokales Migrationstool ohne voreingestellten Repository-Datenpfad."""

import argparse
from pathlib import Path

from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import migrate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize or upgrade a local database"
    )
    parser.add_argument("--path", required=True, type=Path)
    args = parser.parse_args()
    version = migrate(Database(args.path))
    print(f"Database ready; schema version {version}")


if __name__ == "__main__":
    main()
