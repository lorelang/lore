"""
Prompt Projection System.

Tiered rendering with token budget enforcement for the agent compiler.
Prevents context rot by prioritizing high-value entities and sections
when the ontology exceeds the model's effective context window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from .models import Ontology, Entity, View
from .view_scope import resolve_view_scope


class RenderTier(IntEnum):
    """Rendering fidelity tiers, ordered by detail level."""
    OMIT = 0
    STUB = 1      # Name + one-line description (~10% of full)
    SUMMARY = 2   # Name, first-sentence desc, attr names, key note (~40%)
    FULL = 3      # Everything


@dataclass
class EntityPriority:
    """Scored entity with render tier assignment."""
    name: str
    score: float
    tier: RenderTier = RenderTier.FULL
    estimated_tokens: int = 0


@dataclass
class ProjectionPlan:
    """The result of budget planning."""
    entity_tiers: dict[str, RenderTier] = field(default_factory=dict)
    section_flags: dict[str, bool] = field(default_factory=dict)
    dropped_entities: list[str] = field(default_factory=list)
    budget_total: int = 0
    budget_used: int = 0

    @property
    def budget_utilization(self) -> float:
        return self.budget_used / self.budget_total if self.budget_total else 0.0


@dataclass
class ContextBudget:
    """Token budget tracker."""
    total_tokens: int
    reserved_tokens: int = 200  # XML scaffolding overhead
    used_tokens: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total_tokens - self.reserved_tokens - self.used_tokens)

    def consume(self, n: int) -> bool:
        """Try to consume n tokens. Returns True if affordable."""
        if n <= self.remaining:
            self.used_tokens += n
            return True
        return False

    def can_afford(self, n: int) -> bool:
        return n <= self.remaining


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.

    Heuristic: ~4 characters per token for English/mixed text.
    No external dependency (no tiktoken).
    """
    return len(text) // 4


# ── Tiered rendering helpers ──────────────────────────────────

def render_entity_full(entity: Entity) -> str:
    """Render entity at full fidelity."""
    lines: list[str] = []
    lines.append(f'<entity name="{entity.name}">')
    if entity.status:
        lines.append(f"  Status: {entity.status}")
    if entity.provenance:
        prov_parts = []
        if entity.provenance.source:
            prov_parts.append(f"source={entity.provenance.source}")
        if entity.provenance.confidence is not None:
            prov_parts.append(f"confidence={entity.provenance.confidence}")
        if entity.provenance.author:
            prov_parts.append(f"author={entity.provenance.author}")
        if entity.provenance.created:
            prov_parts.append(f"created={entity.provenance.created}")
        if prov_parts:
            lines.append(f"  Provenance: {', '.join(prov_parts)}")
    if entity.description:
        lines.append(f"  {entity.description}")
    if entity.inherits:
        lines.append(f"  Inherits from: {entity.inherits}")
    lines.append("")
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
        lines.append("")
    if entity.identity:
        lines.append(f"  Identity: {entity.identity}")
        lines.append("")
    if entity.lifecycle:
        lines.append(f"  Lifecycle: {entity.lifecycle}")
        lines.append("")
    if entity.notes:
        lines.append(f"  Notes: {entity.notes}")
        lines.append("")
    lines.append(f"</entity>")
    return "\n".join(lines)


def render_entity_summary(entity: Entity) -> str:
    """Render entity at summary fidelity (~40% of full)."""
    lines: list[str] = []
    lines.append(f'<entity name="{entity.name}" tier="summary">')
    if entity.status:
        lines.append(f"  Status: {entity.status}")
    # First sentence of description
    if entity.description:
        first_sentence = entity.description.split(".")[0] + "."
        lines.append(f"  {first_sentence}")
    # Attribute names only
    if entity.attributes:
        attr_names = ", ".join(a.name for a in entity.attributes)
        lines.append(f"  Attributes: {attr_names}")
    # Key note sentence
    if entity.notes:
        first_note = entity.notes.split(".")[0] + "."
        lines.append(f"  Key note: {first_note}")
    lines.append(f"</entity>")
    return "\n".join(lines)


def render_entity_stub(entity: Entity) -> str:
    """Render entity at stub fidelity (~10% of full)."""
    desc = entity.description.split(".")[0] + "." if entity.description else ""
    return f'<entity name="{entity.name}" tier="stub">{desc}</entity>'


TIER_RENDERERS = {
    RenderTier.FULL: render_entity_full,
    RenderTier.SUMMARY: render_entity_summary,
    RenderTier.STUB: render_entity_stub,
}


# ── Scoring ───────────────────────────────────────────────────

_STATUS_SCORES = {
    "stable": 4,
    "proposed": 3,
    "draft": 2,
    "": 1,
    "deprecated": 0,
}


def _score_entity(entity: Entity, ontology: Ontology) -> float:
    """Score an entity for prioritization."""
    score = float(_STATUS_SCORES.get(entity.status, 1))

    # Relationship bonus: +2 per relationship involving this entity
    for rel in ontology.all_relationships:
        if rel.from_entity == entity.name or rel.to_entity == entity.name:
            score += 2

    # Notes bonus
    if entity.notes:
        score += 3

    # Lifecycle bonus
    if entity.lifecycle:
        score += 2

    return score


# ── Section definitions (last-to-first cutting order) ────────

# Sections are cut in this order when budget is tight:
# decisions, outcomes, observations, taxonomies, glossary, traversals,
# rules, relationships, entities, guidance, overview
SECTION_CUT_ORDER = [
    "decisions",
    "outcomes",
    "observations",
    "taxonomies",
    "glossary",
    "traversals",
    "rules",
    "relationships",
    "entities",
    "guidance",
    "overview",
]


# ── Projector ─────────────────────────────────────────────────

class ContextProjector:
    """Plans token-budget-aware rendering of an ontology."""

    def __init__(
        self,
        ontology: Ontology,
        budget_tokens: int,
        view: Optional[View] = None,
    ):
        self.ontology = ontology
        self.budget = ContextBudget(total_tokens=budget_tokens)
        self.view = view

    def plan(self) -> ProjectionPlan:
        """Create a projection plan within the token budget."""
        plan = ProjectionPlan(budget_total=self.budget.total_tokens)

        # Score and sort entities by priority
        scored = self._score_entities()
        scored.sort(key=lambda ep: ep.score, reverse=True)

        # Estimate tokens for each tier per entity
        for ep in scored:
            entity = self._get_entity(ep.name)
            if entity:
                full_text = render_entity_full(entity)
                ep.estimated_tokens = estimate_tokens(full_text)

        # Greedy allocation: highest priority first, best tier that fits
        for ep in scored:
            entity = self._get_entity(ep.name)
            if not entity:
                continue

            full_tokens = ep.estimated_tokens
            summary_tokens = max(1, int(full_tokens * 0.4))
            stub_tokens = max(1, int(full_tokens * 0.1))

            if self.budget.can_afford(full_tokens):
                ep.tier = RenderTier.FULL
                self.budget.consume(full_tokens)
            elif self.budget.can_afford(summary_tokens):
                ep.tier = RenderTier.SUMMARY
                self.budget.consume(summary_tokens)
            elif self.budget.can_afford(stub_tokens):
                ep.tier = RenderTier.STUB
                self.budget.consume(stub_tokens)
            else:
                ep.tier = RenderTier.OMIT
                plan.dropped_entities.append(ep.name)

            plan.entity_tiers[ep.name] = ep.tier

        # Determine which non-entity sections to include
        # Reserve remaining budget for sections
        section_content = self._estimate_section_tokens()
        plan.section_flags = {}
        for section_name in reversed(SECTION_CUT_ORDER):
            if section_name == "entities":
                plan.section_flags["entities"] = True
                continue
            tokens_needed = section_content.get(section_name, 0)
            if tokens_needed > 0 and self.budget.can_afford(tokens_needed):
                plan.section_flags[section_name] = True
                self.budget.consume(tokens_needed)
            else:
                plan.section_flags[section_name] = False

        plan.budget_used = self.budget.used_tokens
        return plan

    def _score_entities(self) -> list[EntityPriority]:
        """Score all in-scope entities."""
        scope = None
        if self.view:
            scope = resolve_view_scope(self.ontology, self.view)

        in_scope = (
            scope.entity_names
            if scope
            else {e.name for e in self.ontology.entities}
        )

        scored = []
        for entity in self.ontology.entities:
            if entity.name not in in_scope:
                continue
            score = _score_entity(entity, self.ontology)
            scored.append(EntityPriority(name=entity.name, score=score))
        return scored

    def _get_entity(self, name: str) -> Optional[Entity]:
        for e in self.ontology.entities:
            if e.name == name:
                return e
        return None

    def _estimate_section_tokens(self) -> dict[str, int]:
        """Rough token estimates for each non-entity section."""
        ont = self.ontology
        estimates: dict[str, int] = {}

        # Overview + guidance are small, fixed overhead
        estimates["overview"] = 50
        estimates["guidance"] = 60

        # Relationships
        rel_text = ""
        for rel in ont.all_relationships:
            rel_text += f"{rel.from_entity} -[{rel.name}]-> {rel.to_entity}\n"
            if rel.description:
                rel_text += f"  {rel.description}\n"
        estimates["relationships"] = estimate_tokens(rel_text)

        # Traversals
        trav_text = ""
        for trav in ont.all_traversals:
            trav_text += f"{trav.name}: {trav.path}\n"
        estimates["traversals"] = estimate_tokens(trav_text)

        # Rules
        rule_text = ""
        for rule in ont.all_rules:
            rule_text += f"{rule.name} {rule.condition} {rule.action} {rule.prose}\n"
        estimates["rules"] = estimate_tokens(rule_text)

        # Taxonomies
        tax_text = ""
        for tax in ont.taxonomies:
            tax_text += f"{tax.name} {tax.applied_to}\n"
        estimates["taxonomies"] = estimate_tokens(tax_text) if tax_text else 0

        # Glossary
        gloss_text = ""
        for entry in ont.all_glossary_entries:
            gloss_text += f"{entry.term}: {entry.definition}\n"
        estimates["glossary"] = estimate_tokens(gloss_text)

        # Observations
        obs_text = ""
        for of in ont.observation_files:
            for obs in of.observations:
                obs_text += f"{obs.heading} {obs.prose}\n"
        estimates["observations"] = estimate_tokens(obs_text)

        # Outcomes
        out_text = ""
        for of in ont.outcome_files:
            for outcome in of.outcomes:
                out_text += f"{outcome.heading} {outcome.prose}\n"
        estimates["outcomes"] = estimate_tokens(out_text)

        # Decisions
        dec_text = ""
        for df in ont.decision_files:
            for dec in df.decisions:
                dec_text += f"{dec.heading} {dec.context} {dec.resolution} {dec.rationale}\n"
        estimates["decisions"] = estimate_tokens(dec_text)

        return estimates
