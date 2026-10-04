from __future__ import annotations

from app.db_schema import create_schema
from app.persistence import seed_demo_database


def main() -> None:
    engine = create_schema()
    counts = seed_demo_database(engine)
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
