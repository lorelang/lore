"""
Lore SDK — Programmatic API for ontology access.

Provides a clean interface for third-party tools, harnesses,
and applications to work with Lore ontologies without
touching the CLI or parser internals directly.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .models import Entity, Relationship, Rule, Ontology
from .parser import parse_ontology
from .validator import validate as _validate, Diagnostic


class LoreOntology:
    """High-level ontology accessor with lazy parsing."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._ontology: Optional[Ontology] = None

    @property
    def ontology(self) -> Ontology:
        """Lazily parse the ontology on first access."""
        if self._ontology is None:
            self._ontology = parse_ontology(self._path)
        return self._ontology

    @property
    def path(self) -> Path:
        return self._path

    def reload(self) -> None:
        """Force re-parse from disk."""
        self._ontology = None

    # ── Compilation ──────────────────────────────────────────────

    def compile_agent_context(
        self,
        view: Optional[str] = None,
        budget: Optional[int] = None,
    ) -> str:
        """Compile to agent context document."""
        from .compilers.agent import compile_agent_context
        return compile_agent_context(self.ontology, view_name=view,
                                     budget_tokens=budget)

    def compile_json(self) -> str:
        from .compilers.json_export import compile_json
        return compile_json(self.ontology)

    def compile_jsonld(self) -> str:
        from .compilers.jsonld import compile_jsonld
        return compile_jsonld(self.ontology)

    def compile_neo4j(self) -> str:
        from .compilers.neo4j import compile_neo4j
        return compile_neo4j(self.ontology)

    def compile_mermaid(self) -> str:
        from .compilers.mermaid import compile_mermaid
        return compile_mermaid(self.ontology)

    def compile_embeddings(self) -> str:
        from .compilers.embeddings import compile_embeddings
        return compile_embeddings(self.ontology)

    def compile_tools(self, fmt: str = "openai") -> str:
        from .compilers.tools import compile_tools
        return compile_tools(self.ontology, fmt=fmt)

    def compile_agents_md(self, view: Optional[str] = None) -> str:
        from .compilers.agents_md import compile_agents_md
        return compile_agents_md(self.ontology, view_name=view)

    def compile_metrics(self) -> str:
        from .compilers.metrics import compile_metrics
        return compile_metrics(self.ontology)

    # ── Entity context slice ─────────────────────────────────────

    def compile_entity_context(
        self,
        entity_name: str,
        budget: Optional[int] = None,
    ) -> str:
        """
        Compile context for a single entity and its immediate neighborhood.

        Includes the entity itself, directly related entities (summary only),
        applicable rules, relevant observations, and glossary entries that
        mention the entity. This is the "slice" primitive for on-demand
        retrieval instead of dumping the entire ontology.
        """
        ont = self.ontology
        entity = self.get_entity(entity_name)
        if entity is None:
            return ""

        lines: list[str] = []
        lines.append(f"<entity_context name=\"{entity.name}\">")

        # Full entity rendering
        lines.append(f"<entity name=\"{entity.name}\">")
        if entity.status:
            lines.append(f"  Status: {entity.status}")
        if entity.description:
            lines.append(f"  {entity.description}")
        if entity.attributes:
            lines.append("  Attributes:")
            for attr in entity.attributes:
                type_str = attr.type
                if attr.type == "enum" and attr.enum_values:
                    type_str = f"enum [{', '.join(attr.enum_values)}]"
                if attr.reference_to:
                    type_str = f"reference to {attr.reference_to}"
                constraint_str = (f" [{', '.join(attr.constraints)}]"
                                  if attr.constraints else "")
                lines.append(f"    - {attr.name}: {type_str}{constraint_str}")
                if attr.description:
                    lines.append(f"      {attr.description}")
        if entity.identity:
            lines.append(f"  Identity: {entity.identity}")
        if entity.lifecycle:
            lines.append(f"  Lifecycle: {entity.lifecycle}")
        if entity.notes:
            lines.append(f"  Notes: {entity.notes}")
        lines.append(f"</entity>")
        lines.append("")

        # Related entities (summary only)
        rels = self.relationships_for(entity_name)
        if rels:
            lines.append("<related_entities>")
            neighbor_names: set[str] = set()
            for rel in rels:
                other = (rel.to_entity if rel.from_entity == entity_name
                         else rel.from_entity)
                lines.append(
                    f"  {rel.from_entity} -[{rel.name}]-> {rel.to_entity}"
                    f" ({rel.cardinality})"
                )
                if rel.description:
                    lines.append(f"    {rel.description}")
                neighbor_names.add(other)

            # Brief summary of neighbors
            for neighbor_name in sorted(neighbor_names):
                neighbor = self.get_entity(neighbor_name)
                if neighbor:
                    lines.append(
                        f"  <entity_summary name=\"{neighbor.name}\">"
                        f"{neighbor.description}</entity_summary>"
                    )
            lines.append("</related_entities>")
            lines.append("")

        # Applicable rules
        entity_rules = self.rules_for(entity_name)
        if entity_rules:
            lines.append("<applicable_rules>")
            for rule in entity_rules:
                lines.append(f"  <rule name=\"{rule.name}\">")
                if rule.severity:
                    lines.append(f"    Severity: {rule.severity}")
                if rule.condition:
                    lines.append(f"    Condition: {rule.condition}")
                if rule.action:
                    lines.append(f"    Action: {rule.action}")
                if rule.prose:
                    lines.append(f"    Context: {rule.prose}")
                lines.append(f"  </rule>")
            lines.append("</applicable_rules>")
            lines.append("")

        # Relevant observations
        obs_entries = []
        for of in ont.observation_files:
            if of.about == entity_name:
                for obs in of.observations:
                    obs_entries.append((of, obs))
        if obs_entries:
            lines.append("<observations>")
            for of, obs in obs_entries:
                meta_parts = []
                if of.observed_by:
                    meta_parts.append(f"by {of.observed_by}")
                if of.date:
                    meta_parts.append(f"on {of.date}")
                meta = f" ({', '.join(meta_parts)})" if meta_parts else ""
                lines.append(f"  <observation>{obs.heading}{meta}")
                lines.append(f"    {obs.prose}")
                if obs.claims:
                    for claim in obs.claims:
                        lines.append(f"    - {claim.kind}: {claim.text}")
                lines.append(f"  </observation>")
            lines.append("</observations>")
            lines.append("")

        # Relevant glossary entries
        if ont.glossary and ont.glossary.entries:
            relevant = [e for e in ont.glossary.entries
                        if entity_name.lower() in e.term.lower()
                        or entity_name.lower() in e.definition.lower()]
            if relevant:
                lines.append("<glossary>")
                for entry in relevant:
                    lines.append(f"  {entry.term}: {entry.definition}")
                lines.append("</glossary>")
                lines.append("")

        lines.append(f"</entity_context>")

        result = "\n".join(lines)

        # Apply budget if specified
        if budget is not None:
            from .projection import estimate_tokens
            tokens = estimate_tokens(result)
            if tokens > budget:
                # Truncate to fit budget (rough cut)
                char_budget = budget * 4
                result = result[:char_budget]
                # Try to end on a complete line
                last_newline = result.rfind("\n")
                if last_newline > char_budget * 0.8:
                    result = result[:last_newline]
                result += "\n</entity_context>"

        return result

    # ── Query ────────────────────────────────────────────────────

    def query_entities(
        self,
        status: Optional[str] = None,
        name_contains: Optional[str] = None,
    ) -> list[Entity]:
        """Filter entities by status and/or name substring."""
        results = list(self.ontology.entities)
        if status:
            results = [e for e in results if e.status == status]
        if name_contains:
            pattern = name_contains.lower()
            results = [e for e in results if pattern in e.name.lower()]
        return results

    def get_entity(self, name: str) -> Optional[Entity]:
        """Look up entity by exact name (case-insensitive)."""
        lower = name.lower()
        for e in self.ontology.entities:
            if e.name.lower() == lower:
                return e
        return None

    def relationships_for(self, entity_name: str) -> list[Relationship]:
        """All relationships involving the given entity."""
        lower = entity_name.lower()
        return [
            r for r in self.ontology.all_relationships
            if r.from_entity.lower() == lower or r.to_entity.lower() == lower
        ]

    def rules_for(self, entity_name: str) -> list[Rule]:
        """All rules that apply to the given entity."""
        lower = entity_name.lower()
        return [
            r for r in self.ontology.all_rules
            if r.applies_to.lower() == lower
        ]

    def search(self, query: str) -> list[dict]:
        """
        Full-text search across all prose in the ontology.

        Returns a list of dicts with keys: type, name, text, score.
        Score is the number of query-word matches found.
        """
        words = [w.lower() for w in query.split() if len(w) > 1]
        if not words:
            return []

        results: list[dict] = []

        def _score(text: str) -> int:
            lower_text = text.lower()
            return sum(1 for w in words if w in lower_text)

        # Entities
        for e in self.ontology.entities:
            corpus = " ".join(filter(None, [
                e.name, e.description, e.identity, e.lifecycle, e.notes,
            ]))
            s = _score(corpus)
            if s > 0:
                results.append({
                    "type": "entity", "name": e.name,
                    "text": e.description[:200], "score": s,
                })

        # Rules
        for r in self.ontology.all_rules:
            corpus = " ".join(filter(None, [
                r.name, r.applies_to, r.trigger, r.condition, r.action, r.prose,
            ]))
            s = _score(corpus)
            if s > 0:
                results.append({
                    "type": "rule", "name": r.name,
                    "text": r.prose[:200] if r.prose else r.condition[:200],
                    "score": s,
                })

        # Glossary
        for entry in self.ontology.all_glossary_entries:
            corpus = f"{entry.term} {entry.definition}"
            s = _score(corpus)
            if s > 0:
                results.append({
                    "type": "glossary", "name": entry.term,
                    "text": entry.definition[:200], "score": s,
                })

        # Observations
        for of in self.ontology.observation_files:
            for obs in of.observations:
                corpus = f"{obs.heading} {obs.prose}"
                s = _score(corpus)
                if s > 0:
                    results.append({
                        "type": "observation", "name": obs.heading,
                        "text": obs.prose[:200], "score": s,
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # ── Tool schemas ─────────────────────────────────────────────

    def tool_schemas(self, fmt: str = "openai") -> list[dict]:
        """Generate function-calling tool schemas from the ontology."""
        from .compilers.tools import generate_tool_schemas
        return generate_tool_schemas(self.ontology, fmt=fmt)

    # ── Stats & Validation ───────────────────────────────────────

    @property
    def stats(self) -> dict:
        """Ontology statistics."""
        ont = self.ontology
        return {
            "name": ont.manifest.name if ont.manifest else "",
            "version": ont.manifest.version if ont.manifest else "",
            "entities": len(ont.entities),
            "attributes": sum(len(e.attributes) for e in ont.entities),
            "relationships": len(ont.all_relationships),
            "traversals": len(ont.all_traversals),
            "rules": len(ont.all_rules),
            "taxonomies": len(ont.taxonomies),
            "glossary_terms": len(ont.all_glossary_entries),
            "views": len(ont.views),
            "observations": len(ont.all_observations),
            "outcomes": len(ont.all_outcomes),
            "claims": len(ont.all_claims),
            "decisions": len(ont.all_decisions),
        }

    def validate(self) -> list[Diagnostic]:
        """Run validation and return diagnostics."""
        return _validate(self.ontology)
