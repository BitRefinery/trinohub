"""Extract one release's section from CHANGELOG.md.

The release workflow publishes the extracted text as the GitHub Release body,
so the changelog is the single source of release notes rather than a duplicate
of auto-generated ones.

Usage:
    python scripts/changelog_section.py v0.3.0 [CHANGELOG.md]

Writes the section body to stdout. Exits non-zero when the version has no
section or the section is empty, so a release cannot publish blank notes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# "## [0.3.0] - 2026-07-29" — the trailing date is optional so an entry that
# has not been dated yet still resolves.
HEADING = re.compile(r"^##\s+\[([^\]]+)\]")


def extract(text: str, version: str) -> str:
    """Return the body of the section for ``version``.

    ``version`` may be given with or without a leading "v"; changelog headings
    carry the bare number.
    """
    wanted = version.lstrip("vV")
    lines = text.splitlines()
    collected: list[str] = []
    inside = False
    for line in lines:
        match = HEADING.match(line)
        if match:
            if inside:
                break  # next release heading ends the section
            inside = match.group(1).lstrip("vV") == wanted
            continue
        if inside:
            collected.append(line)
    if not inside and not collected:
        raise SystemExit(f"No changelog section found for {version}.")
    # Drop the link-reference block ("[0.3.0]: https://...") that trails the
    # final section, plus surrounding blank lines.
    while collected and (not collected[-1].strip() or collected[-1].startswith("[")):
        collected.pop()
    body = "\n".join(collected).strip("\n")
    if not body.strip():
        raise SystemExit(f"Changelog section for {version} is empty.")
    return body


def main(argv: list[str]) -> int:
    if not 2 <= len(argv) <= 3:
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[2]) if len(argv) == 3 else Path("CHANGELOG.md")
    print(extract(path.read_text(encoding="utf-8"), argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
