"""
Proposal review helpers.

Supports human-in-the-loop acceptance/rejection of generated proposal files.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
import yaml


@dataclass
class ReviewResult:
    reviewed: list[Path]
    skipped: list[Path]


def review_proposals(
    path: Path,
    *,
    decision: str,
    reviewer: str,
    note: str = "",
    include_all: bool = False,
    today: date | None = None,
) -> ReviewResult:
    """
    Review a proposal file or directory.

    If path is a directory, processes all .lore files. By default, files already
    in accepted/rejected state are skipped unless include_all=True.
    """
    decision_norm = decision.strip().lower()
    if decision_norm not in {"accept", "reject"}:
        raise ValueError("decision must be 'accept' or 'reject'")

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.glob("*.lore"))
    else:
        raise FileNotFoundError(path)

    reviewed: list[Path] = []
    skipped: list[Path] = []
    stamp = (today or date.today()).isoformat()

    for proposal_path in files:
        text = proposal_path.read_text()
        fm, body = _split_frontmatter(text)
        state = str(fm.get("review_state", "")).strip().lower()
        if not include_all and state in {"accepted", "rejected"}:
            skipped.append(proposal_path)
            continue

        fm["review_state"] = "accepted" if decision_norm == "accept" else "rejected"
        fm["review_decision"] = decision_norm
        fm["reviewed_by"] = reviewer
        fm["reviewed_at"] = stamp
        if note.strip():
            fm["review_note"] = note.strip()
        if "review_required" in fm:
            fm["review_required"] = False

        proposal_path.write_text(_render_frontmatter(fm, body))
        reviewed.append(proposal_path)

    return ReviewResult(reviewed=reviewed, skipped=skipped)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\n")
            if isinstance(fm, dict):
                return fm, body
    return {}, text


def _render_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    yaml_block = yaml.safe_dump(frontmatter, sort_keys=False).rstrip()
    return f"---\n{yaml_block}\n---\n\n{body.lstrip()}"

