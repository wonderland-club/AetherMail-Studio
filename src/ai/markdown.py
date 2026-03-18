"""Markdown normalization helpers for AI-generated content."""

import re


def normalize_markdown(md: str) -> str:
    """Normalize spacing around headings and list items."""
    if not md:
        return ""

    lines = [line.rstrip() for line in md.splitlines()]
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if out and out[-1] == "":
                continue
            out.append("")
            continue

        is_heading = stripped.startswith("#")
        is_unordered = stripped.startswith(("- ", "* ", "+ "))
        is_ordered = bool(re.match(r"^\d+\.\s", stripped))

        if out and out[-1] != "" and (is_heading or is_unordered or is_ordered):
            out.append("")

        out.append(stripped)

    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()

    return "\n".join(out)
