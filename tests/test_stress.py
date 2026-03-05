"""Stress and performance tests for Lore."""
import json
import time
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Traversal, Rule, RuleFile, Taxonomy, TaxonomyNode,
    Glossary, GlossaryEntry, View, Provenance,
    ObservationFile, Observation, KnowledgeClaim,
)
from lore.compilers.agent import compile_agent_context, _detect_observation_conflicts
from lore.compilers.embeddings import compile_embeddings


pytestmark = pytest.mark.slow


def _make_entity(i: int, n_attrs: int = 5) -> Entity:
    """Build a synthetic entity with n_attrs attributes."""
    return Entity(
        name=f"Entity_{i:04d}",
        description=f"Synthetic entity number {i}.",
        attributes=[
            Attribute(name=f"attr_{j}", type="string", description=f"Attribute {j}")
            for j in range(n_attrs)
        ],
        identity=f"Entity_{i:04d} is identified by attr_0.",
        notes=f"Notes for entity {i}. " * 5,
        status="stable" if i % 2 == 0 else "draft",
        provenance=Provenance(author="stress-test", source="ai-generated",
                              confidence=0.9, created="2025-01-01"),
    )


class TestCompile1000Entities:
    """1000 entities x 5 attrs each, compile to agent context."""

    def test_completes_under_2s(self):
        entities = [_make_entity(i) for i in range(1000)]
        ont = Ontology(
            manifest=OntologyManifest(name="stress-1k", version="1.0"),
            entities=entities,
        )
        start = time.monotonic()
        result = compile_agent_context(ont)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Compilation took {elapsed:.2f}s, expected <2s"
        # Verify all entity names present
        for i in range(0, 1000, 100):  # spot check every 100th
            assert f"Entity_{i:04d}" in result


class TestDeepTaxonomy100Levels:
    """100-level deep linear taxonomy chain."""

    def test_no_recursion_errors(self):
        # Build a linear chain: Root -> Level_1 -> Level_2 -> ... -> Level_99
        node = TaxonomyNode(name="Level_99", depth=99)
        for i in range(98, -1, -1):
            node = TaxonomyNode(name=f"Level_{i}" if i > 0 else "Root",
                                children=[node], depth=i)

        ont = Ontology(
            manifest=OntologyManifest(name="deep-tax", version="1.0"),
            entities=[Entity(name="Item", attributes=[Attribute(name="type", type="string")])],
            taxonomies=[Taxonomy(name="DeepTax", applied_to="Item.type", root=node)],
        )
        result = compile_agent_context(ont)
        assert "Root" in result
        assert "Level_99" in result

    def test_embeddings_handles_deep_tree(self):
        node = TaxonomyNode(name="Level_99", depth=99)
        for i in range(98, -1, -1):
            node = TaxonomyNode(name=f"Level_{i}" if i > 0 else "Root",
                                children=[node], depth=i)

        ont = Ontology(
            manifest=OntologyManifest(name="deep-tax", version="1.0"),
            taxonomies=[Taxonomy(name="DeepTax", root=node)],
        )
        result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        assert len(chunks) >= 1


class TestDenseRelationshipGraph:
    """50 entities, 200 relationships."""

    def test_compiles_and_traversals_correct(self):
        entities = [_make_entity(i, n_attrs=2) for i in range(50)]
        relationships = []
        for i in range(200):
            from_idx = i % 50
            to_idx = (i * 7 + 3) % 50  # pseudo-random but deterministic
            if from_idx == to_idx:
                to_idx = (to_idx + 1) % 50
            relationships.append(Relationship(
                name=f"REL_{i:03d}",
                from_entity=f"Entity_{from_idx:04d}",
                to_entity=f"Entity_{to_idx:04d}",
                cardinality="many-to-many",
            ))

        ont = Ontology(
            manifest=OntologyManifest(name="dense-graph", version="1.0"),
            entities=entities,
            relationship_files=[RelationshipFile(
                domain="Dense",
                relationships=relationships,
            )],
        )
        result = compile_agent_context(ont)
        assert "<relationships>" in result
        # Spot check some relationships
        assert "REL_000" in result
        assert "REL_199" in result


class Test500ObservationsConflictDetection:
    """500 observations with mixed signals."""

    def test_conflict_detection_under_1s(self):
        obs_files = []
        for i in range(50):
            observations = []
            for j in range(10):
                idx = i * 10 + j
                # Alternate positive and negative
                if idx % 2 == 0:
                    prose = f"Strong growth and expansion in metric {idx}."
                else:
                    prose = f"Concerning decline and churn risk in metric {idx}."
                observations.append(Observation(
                    heading=f"Signal_{idx}",
                    prose=prose,
                    claims=[KnowledgeClaim(
                        kind="fact" if idx % 3 == 0 else "belief",
                        text=f"Observation {idx} data point.",
                    )],
                ))
            obs_files.append(ObservationFile(
                name=f"batch_{i}",
                about="Target",
                observed_by=f"agent_{i}",
                date="2025-01-01",
                observations=observations,
            ))

        ont = Ontology(
            manifest=OntologyManifest(name="obs-stress", version="1.0"),
            entities=[Entity(name="Target", attributes=[Attribute(name="id", type="string")])],
            observation_files=obs_files,
        )

        start = time.monotonic()
        conflicts = _detect_observation_conflicts(ont)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Conflict detection took {elapsed:.2f}s, expected <1s"
        # Should detect at least some conflicts
        assert len(conflicts) > 0


class Test100RulesViewScoped:
    """100 rules, view selects 5."""

    def test_exactly_5_in_output(self):
        selected_names = [f"rule_{i}" for i in range(5)]
        rules = [
            Rule(name=f"rule_{i}", applies_to="Widget", severity="info",
                 condition=f"condition_{i}", action=f"action_{i}")
            for i in range(100)
        ]
        ont = Ontology(
            manifest=OntologyManifest(name="rules-scope", version="1.0"),
            entities=[Entity(name="Widget", attributes=[Attribute(name="id", type="string")])],
            rule_files=[RuleFile(domain="Many Rules", rules=rules)],
            views=[View(
                name="Focused",
                entities=["Widget"],
                rules=selected_names,
            )],
        )
        result = compile_agent_context(ont, view_name="Focused")
        # Count rule tags in output
        import re
        rule_matches = re.findall(r'<rule name="(rule_\d+)">', result)
        assert len(rule_matches) == 5
        assert set(rule_matches) == set(selected_names)


class TestLargeEmbeddingsOutput:
    """100 entities with full prose."""

    def test_valid_json_per_chunk_unique_ids(self):
        entities = []
        for i in range(100):
            entities.append(Entity(
                name=f"Entity_{i:03d}",
                description=f"Entity {i} description with some prose.",
                attributes=[
                    Attribute(name="id", type="string"),
                    Attribute(name="value", type="float"),
                ],
                identity=f"Identified by id field for entity {i}.",
                lifecycle=f"Lifecycle: created, activated, retired for entity {i}.",
                notes=f"Detailed notes about entity {i}. " * 10,
            ))

        ont = Ontology(
            manifest=OntologyManifest(name="embed-stress", version="1.0"),
            entities=entities,
        )
        result = compile_embeddings(ont)
        lines = result.strip().split("\n")
        ids = set()
        for line in lines:
            chunk = json.loads(line)
            assert "id" in chunk
            assert "type" in chunk
            assert "text" in chunk
            assert chunk["id"] not in ids, f"Duplicate chunk id: {chunk['id']}"
            ids.add(chunk["id"])
        # Should have many chunks
        assert len(ids) >= 100


class TestCompilePerfRegressionGuard:
    """200 entities / 50 relationships / 30 rules: agent compile <500ms."""

    def test_under_500ms(self):
        entities = [_make_entity(i, n_attrs=3) for i in range(200)]
        relationships = [
            Relationship(
                name=f"REL_{i:02d}",
                from_entity=f"Entity_{i % 200:04d}",
                to_entity=f"Entity_{(i * 3 + 1) % 200:04d}",
                cardinality="one-to-many",
            )
            for i in range(50)
        ]
        rules = [
            Rule(name=f"rule_{i}", applies_to=f"Entity_{i % 200:04d}",
                 severity="warning", condition=f"cond_{i}", action=f"act_{i}")
            for i in range(30)
        ]

        ont = Ontology(
            manifest=OntologyManifest(name="perf-guard", version="1.0"),
            entities=entities,
            relationship_files=[RelationshipFile(domain="Perf", relationships=relationships)],
            rule_files=[RuleFile(domain="Perf", rules=rules)],
            glossary=Glossary(entries=[
                GlossaryEntry(term=f"Term_{i}", definition=f"Definition {i}")
                for i in range(20)
            ]),
        )
        start = time.monotonic()
        result = compile_agent_context(ont)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, f"Agent compile took {elapsed:.2f}s, expected <500ms"
        assert "<domain_ontology>" in result
