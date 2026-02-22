"""
Lore Evolution.

Reads outcomes, collects takeaways, groups related ones,
and generates proposal .lore files for ontology improvements.

This closes the self-updating loop:
  .lore files -> compile -> AI agent -> observe -> outcomes -> evolve -> proposals
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
from .models import Ontology, Outcome


def evolve(ontology: Ontology, output_dir: Path) -> list[dict]:
    """
    Analyze outcomes and generate improvement proposals.

    Returns a list of proposal dicts with:
      - name: proposal name
      - path: where the file was written
      - takeaways: the takeaways that motivated it
      - kind: 'rule-adjustment' | 'new-entity' | 'observation-pattern'
    """
    proposals = []

    # Collect all takeaways with context
    takeaway_entries = []
    for of in ontology.outcome_files:
        for outcome in of.outcomes:
            for takeaway in outcome.takeaways:
                takeaway_entries.append({
                    "takeaway": takeaway,
                    "outcome_heading": outcome.heading,
                    "outcome_file": of.name,
                    "refs": outcome.refs,
                    "date": of.date,
                })

    if not takeaway_entries:
        return proposals

    # Group takeaways by what they reference
    groups = _group_takeaways(takeaway_entries, ontology)

    # Generate proposals
    output_dir.mkdir(parents=True, exist_ok=True)

    for group_name, group in groups.items():
        proposal = _generate_proposal(group_name, group, ontology, output_dir)
        if proposal:
            proposals.append(proposal)

    return proposals


def _group_takeaways(entries: list[dict], ontology: Ontology) -> dict[str, list[dict]]:
    """
    Group takeaways by the entity or rule they mention.

    Strategy: scan each takeaway for known entity names and rule names.
    If multiple takeaways mention the same thing, they form a group.
    Ungrouped takeaways go into a 'general' bucket.
    """
    groups: dict[str, list[dict]] = defaultdict(list)

    entity_names = ontology.entity_names
    rule_names = {r.name for r in ontology.all_rules}
    all_names = entity_names | rule_names

    for entry in entries:
        text = entry["takeaway"].lower()
        matched = False

        # Check for rule name mentions
        for name in rule_names:
            if name.lower().replace("-", " ") in text or name.lower() in text:
                groups[f"rule:{name}"].append(entry)
                matched = True

        # Check for entity name mentions
        for name in entity_names:
            if name.lower() in text:
                groups[f"entity:{name}"].append(entry)
                matched = True

        if not matched:
            groups["general"].append(entry)

    return dict(groups)


def _generate_proposal(
    group_name: str,
    entries: list[dict],
    ontology: Ontology,
    output_dir: Path,
) -> dict | None:
    """Generate a single proposal .lore file from a group of takeaways."""
    if not entries:
        return None

    takeaways = [e["takeaway"] for e in entries]
    outcomes = list({e["outcome_heading"] for e in entries})
    refs = []
    for e in entries:
        refs.extend(e.get("refs", []))
    refs = list(set(refs))

    # Determine proposal kind and name
    if group_name.startswith("rule:"):
        rule_name = group_name[5:]
        kind = "rule-adjustment"
        slug = _slugify(f"adjust-{rule_name}")
        title = f"Adjust rule: {rule_name}"
        description = (
            f"Multiple outcomes suggest adjustments to the '{rule_name}' rule.\n"
            f"Based on {len(entries)} takeaway(s) from {len(outcomes)} outcome(s)."
        )
    elif group_name.startswith("entity:"):
        entity_name = group_name[7:]
        kind = "entity-observation"
        slug = _slugify(f"review-{entity_name}")
        title = f"Review entity: {entity_name}"
        description = (
            f"Multiple outcomes reference the '{entity_name}' entity.\n"
            f"Based on {len(entries)} takeaway(s) from {len(outcomes)} outcome(s)."
        )
    else:
        kind = "general"
        slug = "general-improvements"
        title = "General improvements"
        description = (
            f"Takeaways that don't map to a specific rule or entity.\n"
            f"Based on {len(entries)} takeaway(s)."
        )

    # Build the .lore file content
    lines = [
        "---",
        f"proposal: {title}",
        "provenance:",
        "  source: derived",
        f"  confidence: {_compute_confidence(entries)}",
        "status: proposed",
        "---",
        "",
        f"## Summary",
        "",
        description,
        "",
        "## Takeaways",
        "",
    ]

    for t in takeaways:
        lines.append(f"- {t}")

    lines.append("")
    lines.append("## Source Outcomes")
    lines.append("")

    for o in outcomes:
        lines.append(f"- {o}")

    if refs:
        lines.append("")
        lines.append("## References")
        lines.append("")
        for r in refs:
            lines.append(f"- {r}")

    lines.append("")

    # Write
    filepath = output_dir / f"{slug}.lore"
    filepath.write_text("\n".join(lines))

    return {
        "name": title,
        "path": str(filepath),
        "takeaways": takeaways,
        "kind": kind,
        "source_outcomes": outcomes,
    }


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    return (
        text.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace(":", "")
        .replace("/", "-")
        .replace(".", "-")
    )


def _compute_confidence(entries: list[dict]) -> float:
    """
    Compute proposal confidence based on number of supporting takeaways.

    More takeaways = higher confidence.
    1 takeaway = 0.5, 2 = 0.65, 3+ = 0.8
    """
    n = len(entries)
    if n >= 3:
        return 0.8
    elif n == 2:
        return 0.65
    else:
        return 0.5
