"""
Lore Indexer.

Generates and updates INDEX.lore files that serve as routing guides for
AI agents navigating the ontology. INDEX.lore files exist at:
  - Root level: ontology-wide map of what exists
  - Directory level: per-directory summary of contents

INDEX.lore files are machine-generated from actual ontology contents.
They help agents decide WHERE to look before they grep/cat.

Format:
---
index: true
generated: YYYY-MM-DD
---

## Overview
Brief description of what's in this directory.

## Contents
- filename.lore — one-line summary

## Search Guide
Natural language routing hints for agents.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Optional
from .models import Ontology


def generate_root_index(ontology: Ontology, root_dir: Path,
                        today: Optional[date] = None) -> str:
    """Generate the root-level INDEX.lore content."""
    ref = today or date.today()
    name = ontology.manifest.name if ontology.manifest else root_dir.name
    desc = ontology.manifest.description if ontology.manifest else ""
    version = ontology.manifest.version if ontology.manifest else ""

    lines = [
        "---",
        "index: true",
        f"generated: {ref.isoformat()}",
        "---",
        "",
        "## Overview",
        "",
        f"This is the **{name}** ontology" + (f" (v{version})" if version else "") + ".",
    ]
    if desc:
        lines.append(f"{desc.strip()}")
    lines.append("")

    # Stats summary
    n_entities = len(ontology.entities)
    n_rels = len(ontology.all_relationships)
    n_rules = len(ontology.all_rules)
    n_tax = len(ontology.taxonomies)
    n_obs = len(ontology.all_observations)
    n_outcomes = len(ontology.all_outcomes)
    n_views = len(ontology.views)
    n_glossary = len(ontology.all_glossary_entries)

    lines.append("## Stats")
    lines.append("")
    lines.append(f"- {n_entities} entities, {n_rels} relationships, {n_rules} rules")
    lines.append(f"- {n_tax} taxonomies, {n_glossary} glossary terms")
    lines.append(f"- {n_obs} observations, {n_outcomes} outcomes")
    lines.append(f"- {n_views} views")
    lines.append("")

    # Directory map
    lines.append("## Directory Map")
    lines.append("")

    dir_descriptions = {
        "entities": "Domain concepts — the nouns of this ontology",
        "relationships": "How entities connect — the verbs",
        "rules": "Business logic, scoring, and alert conditions",
        "taxonomies": "Classification hierarchies and type trees",
        "glossary": "Canonical term definitions — use these meanings",
        "views": "Team-scoped perspectives (filtered ontology slices)",
        "observations": "Field notes from AI agents and domain experts",
        "outcomes": "Retrospectives — what actually happened",
    }

    for dirname, desc in dir_descriptions.items():
        dir_path = root_dir / dirname
        if dir_path.exists():
            count = len(list(dir_path.glob("*.lore")))
            if count > 0:
                lines.append(f"- `{dirname}/` — {desc} ({count} files)")

    lines.append("")

    # Entity listing (most important for routing)
    if ontology.entities:
        lines.append("## Entities")
        lines.append("")
        for entity in ontology.entities:
            desc_short = entity.description.strip().split("\n")[0][:80] if entity.description else ""
            n_attrs = len(entity.attributes)
            lines.append(f"- **{entity.name}** ({n_attrs} attrs) — {desc_short}")
        lines.append("")

    # Search guide
    lines.append("## Search Guide")
    lines.append("")
    lines.append("When an AI agent needs to find information in this ontology:")
    lines.append("")
    lines.append("- **What is X?** → Look in `entities/` for the entity definition, "
                 "`glossary/` for term definitions")
    lines.append("- **How does X relate to Y?** → Look in `relationships/` for connections")
    lines.append("- **What rules apply to X?** → Look in `rules/` and check `applies_to` fields")
    lines.append("- **What happened with X?** → Look in `observations/` for field notes, "
                 "`outcomes/` for retrospectives")
    lines.append("- **What types/categories exist?** → Look in `taxonomies/`")
    lines.append("- **What does this term mean?** → Look in `glossary/`")
    if ontology.views:
        view_names = [v.name for v in ontology.views]
        lines.append(f"- **Team-specific context?** → Look in `views/` "
                     f"(available: {', '.join(view_names)})")
    lines.append("")
    lines.append("For full compiled context, run: `lore compile . -t agent`")
    lines.append("")

    return "\n".join(lines)


def generate_directory_index(ontology: Ontology, dir_path: Path,
                             dir_type: str, today: Optional[date] = None) -> str:
    """Generate a directory-level INDEX.lore."""
    ref = today or date.today()

    lines = [
        "---",
        "index: true",
        f"generated: {ref.isoformat()}",
        "---",
        "",
    ]

    if dir_type == "entities":
        lines.extend(_index_entities(ontology))
    elif dir_type == "relationships":
        lines.extend(_index_relationships(ontology))
    elif dir_type == "rules":
        lines.extend(_index_rules(ontology))
    elif dir_type == "observations":
        lines.extend(_index_observations(ontology))
    elif dir_type == "taxonomies":
        lines.extend(_index_taxonomies(ontology))
    elif dir_type == "views":
        lines.extend(_index_views(ontology))
    else:
        lines.append(f"## Overview")
        lines.append("")
        lore_files = sorted(dir_path.glob("*.lore"))
        lines.append(f"This directory contains {len(lore_files)} .lore files.")
        lines.append("")
        lines.append("## Contents")
        lines.append("")
        for f in lore_files:
            if f.name != "INDEX.lore":
                lines.append(f"- `{f.name}`")
        lines.append("")

    return "\n".join(lines)


def _index_entities(ontology: Ontology) -> list[str]:
    lines = [
        "## Overview",
        "",
        f"Domain entities ({len(ontology.entities)} total). "
        f"Each file defines one concept with attributes, identity, and prose notes.",
        "",
        "## Contents",
        "",
    ]
    for entity in ontology.entities:
        fname = entity.source_file.name if entity.source_file else f"{entity.name.lower()}.lore"
        n_attrs = len(entity.attributes)
        has_notes = "notes" if entity.notes else "no notes"
        has_identity = "identity" if entity.identity else "no identity"
        lines.append(f"- `{fname}` — **{entity.name}** ({n_attrs} attrs, {has_notes}, {has_identity})")

    lines.extend(["", "## Search Guide", ""])
    lines.append("- To find an entity by name: `grep -l 'entity: Name' entities/*.lore`")
    lines.append("- To find entities with a specific attribute: `grep -l 'attr_name:' entities/*.lore`")
    lines.append("- To find entities by domain concept: `grep -rl 'keyword' entities/`")
    lines.append("")
    return lines


def _index_relationships(ontology: Ontology) -> list[str]:
    lines = [
        "## Overview",
        "",
        f"Relationship definitions ({len(ontology.all_relationships)} total across "
        f"{len(ontology.relationship_files)} files).",
        "",
        "## Contents",
        "",
    ]
    for rf in ontology.relationship_files:
        fname = rf.source_file.name if rf.source_file else f"{rf.domain.lower()}.lore"
        rel_names = [r.name for r in rf.relationships]
        lines.append(f"- `{fname}` — {rf.domain}: {', '.join(rel_names)}")

    lines.extend(["", "## Relationship Map", ""])
    for rel in ontology.all_relationships:
        lines.append(f"- {rel.from_entity} --[{rel.name}]--> {rel.to_entity}")
    lines.append("")
    return lines


def _index_rules(ontology: Ontology) -> list[str]:
    lines = [
        "## Overview",
        "",
        f"Business rules ({len(ontology.all_rules)} total across "
        f"{len(ontology.rule_files)} files).",
        "",
        "## Contents",
        "",
    ]
    for rf in ontology.rule_files:
        fname = rf.source_file.name if rf.source_file else f"{rf.domain.lower()}.lore"
        for rule in rf.rules:
            applies = f" (applies to: {rule.applies_to})" if rule.applies_to else ""
            lines.append(f"- `{fname}` > **{rule.name}**{applies} [{rule.severity}]")

    lines.extend(["", "## Search Guide", ""])
    lines.append("- To find rules for an entity: `grep -l 'applies_to: EntityName' rules/*.lore`")
    lines.append("- To find rules by severity: `grep -l 'severity: critical' rules/*.lore`")
    lines.append("")
    return lines


def _index_observations(ontology: Ontology) -> list[str]:
    lines = [
        "## Overview",
        "",
        f"Field notes and observations ({len(ontology.all_observations)} entries across "
        f"{len(ontology.observation_files)} files).",
        "",
        "## Contents",
        "",
    ]
    for of in ontology.observation_files:
        fname = of.source_file.name if of.source_file else f"{of.name.lower()}.lore"
        about = f" about {of.about}" if of.about else ""
        date_str = f" ({of.date})" if of.date else ""
        lines.append(f"- `{fname}` — {of.name}{about}{date_str}: "
                     f"{len(of.observations)} observations")

    lines.extend(["", "## Search Guide", ""])
    lines.append("- To find observations about an entity: `grep -l 'about: EntityName' observations/*.lore`")
    lines.append("- To find recent observations: sort by `date:` field in frontmatter")
    lines.append("")
    return lines


def _index_taxonomies(ontology: Ontology) -> list[str]:
    lines = [
        "## Overview",
        "",
        f"Classification hierarchies ({len(ontology.taxonomies)} taxonomies).",
        "",
        "## Contents",
        "",
    ]
    for tax in ontology.taxonomies:
        fname = tax.source_file.name if tax.source_file else f"{tax.name.lower()}.lore"
        applied = f" (applied to: {tax.applied_to})" if tax.applied_to else ""
        lines.append(f"- `{fname}` — **{tax.name}**{applied}")
    lines.append("")
    return lines


def _index_views(ontology: Ontology) -> list[str]:
    lines = [
        "## Overview",
        "",
        f"Team-scoped perspectives ({len(ontology.views)} views).",
        "",
        "## Contents",
        "",
    ]
    for view in ontology.views:
        fname = view.source_file.name if view.source_file else f"{view.name.lower()}.lore"
        audience = f" for {view.audience}" if view.audience else ""
        lines.append(f"- `{fname}` — **{view.name}**{audience}")
    lines.append("")
    return lines


def generate_all_indexes(ontology: Ontology, root_dir: Path,
                         today: Optional[date] = None) -> dict[str, str]:
    """
    Generate all INDEX.lore files for the ontology.

    Returns a dict of {relative_path: content} for each INDEX.lore to write.
    """
    indexes: dict[str, str] = {}

    # Root index
    indexes["INDEX.lore"] = generate_root_index(ontology, root_dir, today=today)

    # Directory indexes
    known_dirs = ["entities", "relationships", "rules", "taxonomies",
                  "glossary", "views", "observations", "outcomes"]

    for dirname in known_dirs:
        dir_path = root_dir / dirname
        if dir_path.exists():
            lore_files = [f for f in dir_path.glob("*.lore") if f.name != "INDEX.lore"]
            if lore_files:
                indexes[f"{dirname}/INDEX.lore"] = generate_directory_index(
                    ontology, dir_path, dirname, today=today
                )

    return indexes


def write_indexes(ontology: Ontology, root_dir: Path,
                  today: Optional[date] = None) -> list[Path]:
    """Write all INDEX.lore files to disk. Returns list of written paths."""
    root = Path(root_dir)
    indexes = generate_all_indexes(ontology, root, today=today)
    written = []
    for rel_path, content in indexes.items():
        full_path = root / rel_path
        full_path.write_text(content)
        written.append(full_path)
    return written
