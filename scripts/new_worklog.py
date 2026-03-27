from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

WORKLOG_DIR = Path("docs/worklog")
INDEX_PATH = WORKLOG_DIR / "INDEX.md"
TEMPLATE_PATH = WORKLOG_DIR / "TEMPLATE.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new Mirage worklog entry.")
    parser.add_argument("title", help="Short task title, for example: Phase 2 follow-up")
    parser.add_argument(
        "--date",
        dest="entry_date",
        help="Override the entry date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated file path and content without writing files.",
    )
    args = parser.parse_args()

    entry_date = args.entry_date or date.today().isoformat()
    slug = slugify(args.title)
    filename = f"{entry_date}-{slug}.md"
    entry_path = WORKLOG_DIR / filename
    entry_title = f"{entry_date} {args.title}"
    content = render_template(entry_title=entry_title)

    if args.dry_run:
        print(entry_path)
        print()
        print(content)
        return 0

    WORKLOG_DIR.mkdir(parents=True, exist_ok=True)
    if entry_path.exists():
        raise SystemExit(f"Worklog entry already exists: {entry_path}")

    entry_path.write_text(content, encoding="utf-8")
    update_index(
        entry_date=entry_date,
        title=args.title,
        filename=filename,
        index_path=INDEX_PATH,
    )
    print(entry_path)
    return 0


def render_template(*, entry_title: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{ENTRY_TITLE}}", entry_title).rstrip() + "\n"


def update_index(*, entry_date: str, title: str, filename: str, index_path: Path) -> None:
    header = """# Mirage Worklog

Create a new entry with:

```bash
make worklog TITLE="Short Task Title"
```

Template:

- [Worklog Template](TEMPLATE.md)

Entries:
"""

    bullet = f"- [{entry_date} {title}]({filename})"
    if not index_path.exists():
        index_path.write_text(f"{header}\n{bullet}\n", encoding="utf-8")
        return

    existing = index_path.read_text(encoding="utf-8")
    if bullet in existing:
        return

    if "Entries:\n" not in existing:
        updated = existing.rstrip() + f"\n\nEntries:\n\n{bullet}\n"
    else:
        prefix, entries = existing.split("Entries:\n", 1)
        entry_lines = [line for line in entries.strip().splitlines() if line.strip()]
        updated_entries = "\n".join([bullet, *entry_lines])
        updated = f"{prefix}Entries:\n\n{updated_entries}\n"
    index_path.write_text(updated, encoding="utf-8")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not normalized:
        raise SystemExit("Title must contain at least one alphanumeric character.")
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())
