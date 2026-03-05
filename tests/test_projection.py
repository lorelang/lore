"""Tests for the projection (token budget) system."""
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Glossary, GlossaryEntry, View,
    Provenance,
)
from lore.compilers.agent import compile_agent_context
from lore.projection import (
    ContextProjector, ContextBudget, RenderTier,
    estimate_tokens, render_entity_full, render_entity_summary,
    render_entity_stub, ProjectionPlan,
)


def _make_entity(i: int, status: str = "stable", n_attrs: int = 5) -> Entity:
    """Build a synthetic entity."""
    return Entity(
        name=f"Entity_{i:03d}",
        description=f"Synthetic entity number {i} with a decent description.",
        attributes=[
            Attribute(name=f"attr_{j}", type="string", description=f"Attr {j}")
            for j in range(n_attrs)
        ],
        identity=f"Entity_{i:03d} is identified by attr_0.",
        lifecycle=f"Created, then evolves over time for entity {i}.",
        notes=f"Important notes about entity {i}. " * 5,
        status=status,
        provenance=Provenance(author="test", source="domain-expert",
                              confidence=0.9, created="2025-01-01"),
    )


class TestBudgetLimitsOutput:
    """Compile with budget=4000, assert output within budget."""

    def test_output_within_budget(self):
        entities = [_make_entity(i) for i in range(20)]
        ont = Ontology(
            manifest=OntologyManifest(name="budget-test", version="1.0"),
            entities=entities,
            relationship_files=[RelationshipFile(
                domain="Test",
                relationships=[
                    Relationship(name=f"REL_{i}", from_entity=f"Entity_{i:03d}",
                                 to_entity=f"Entity_{(i+1)%20:03d}",
                                 cardinality="one-to-many")
                    for i in range(10)
                ],
            )],
            rule_files=[RuleFile(
                domain="Test",
                rules=[Rule(name=f"rule_{i}", applies_to=f"Entity_{i:03d}",
                            severity="warning", condition=f"cond_{i}",
                            action=f"action_{i}")
                       for i in range(5)],
            )],
        )
        result = compile_agent_context(ont, budget_tokens=4000)
        tokens = estimate_tokens(result)
        # Allow some overhead for XML scaffolding
        assert tokens <= 4500, f"Output {tokens} tokens exceeds budget 4000 + margin"

    def test_smaller_budget_produces_smaller_output(self):
        entities = [_make_entity(i) for i in range(20)]
        ont = Ontology(
            manifest=OntologyManifest(name="budget-test", version="1.0"),
            entities=entities,
        )
        small = compile_agent_context(ont, budget_tokens=2000)
        large = compile_agent_context(ont, budget_tokens=8000)
        assert len(small) < len(large)


class TestBudgetPrioritizesStable:
    """10 stable + 10 draft entities, budget forces dropping. Stable kept."""

    def test_stable_entities_kept(self):
        stable = [_make_entity(i, status="stable") for i in range(10)]
        draft = [_make_entity(i + 10, status="draft") for i in range(10)]
        ont = Ontology(
            manifest=OntologyManifest(name="priority-test", version="1.0"),
            entities=stable + draft,
        )
        # Use a budget that can't fit all 20 entities at full fidelity
        result = compile_agent_context(ont, budget_tokens=3000)
        # Check stable entities are more likely to appear
        stable_present = sum(1 for i in range(10)
                             if f"Entity_{i:03d}" in result)
        draft_present = sum(1 for i in range(10, 20)
                            if f"Entity_{i:03d}" in result)
        assert stable_present >= draft_present, \
            f"Stable ({stable_present}) should be >= draft ({draft_present})"


class TestBudgetPreservesStructure:
    """Even at minimum budget, XML skeleton is present."""

    def test_skeleton_present(self):
        entities = [_make_entity(i) for i in range(10)]
        ont = Ontology(
            manifest=OntologyManifest(name="skeleton-test", version="1.0"),
            entities=entities,
        )
        result = compile_agent_context(ont, budget_tokens=500)
        assert "<domain_ontology>" in result
        assert "</domain_ontology>" in result
        assert "<entities>" in result
        assert "</entities>" in result


class TestNoBudgetUnchanged:
    """Without --budget, output identical to current behavior."""

    def test_output_identical(self):
        ont = Ontology(
            manifest=OntologyManifest(name="unchanged-test", version="1.0",
                                      description="Test domain"),
            entities=[
                Entity(name="Widget", description="A widget",
                       attributes=[Attribute(name="id", type="string")]),
            ],
        )
        with_none = compile_agent_context(ont, budget_tokens=None)
        without = compile_agent_context(ont)
        assert with_none == without


class TestTieredRenderingSizes:
    """Full > summary > stub for the same entity."""

    def test_sizes_decrease(self):
        entity = _make_entity(0)
        full = render_entity_full(entity)
        summary = render_entity_summary(entity)
        stub = render_entity_stub(entity)
        assert len(full) > len(summary) > len(stub)


class TestProjectionPlanMetadata:
    """Dropped entities are listed correctly in metadata."""

    def test_dropped_entities_in_output(self):
        entities = [_make_entity(i) for i in range(50)]
        ont = Ontology(
            manifest=OntologyManifest(name="metadata-test", version="1.0"),
            entities=entities,
        )
        # Very small budget to force dropping
        result = compile_agent_context(ont, budget_tokens=1000)
        assert "<budget_metadata>" in result
        # Should report some dropped entities or tier information
        assert "Dropped:" in result or "OMIT:" in result or "Used:" in result

    def test_plan_has_all_entities(self):
        entities = [_make_entity(i) for i in range(10)]
        ont = Ontology(
            manifest=OntologyManifest(name="plan-test", version="1.0"),
            entities=entities,
        )
        projector = ContextProjector(ont, budget_tokens=5000)
        plan = projector.plan()
        assert len(plan.entity_tiers) == 10
        assert plan.budget_total == 5000
        assert plan.budget_used > 0

    def test_budget_utilization(self):
        entities = [_make_entity(i) for i in range(5)]
        ont = Ontology(
            manifest=OntologyManifest(name="util-test", version="1.0"),
            entities=entities,
        )
        projector = ContextProjector(ont, budget_tokens=10000)
        plan = projector.plan()
        assert 0.0 <= plan.budget_utilization <= 1.0


class TestEstimateTokens:
    """Token estimation heuristic."""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        assert estimate_tokens("hello world") > 0

    def test_roughly_4_chars_per_token(self):
        text = "a" * 400
        tokens = estimate_tokens(text)
        assert 90 <= tokens <= 110  # Should be ~100


class TestContextBudget:
    """Budget tracker behavior."""

    def test_consume_within_budget(self):
        budget = ContextBudget(total_tokens=1000)
        assert budget.consume(500)
        assert budget.remaining == 300  # 1000 - 200 reserved - 500

    def test_consume_over_budget(self):
        budget = ContextBudget(total_tokens=1000)
        assert not budget.consume(900)  # 900 > 800 remaining (after reserve)

    def test_can_afford(self):
        budget = ContextBudget(total_tokens=1000)
        assert budget.can_afford(500)
        assert not budget.can_afford(900)
