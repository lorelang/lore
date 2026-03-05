"""Tests for the Lore SDK."""
import json
import pytest
from pathlib import Path
from lore.sdk import LoreOntology
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Glossary, GlossaryEntry, View,
    ObservationFile, Observation, KnowledgeClaim, Provenance,
)
from lore.validator import Severity


EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "b2b-saas-gtm"


class TestLoreOntologyInit:
    """SDK initialization and lazy parsing."""

    def test_lazy_parse(self):
        o = LoreOntology(EXAMPLE_DIR)
        assert o._ontology is None
        _ = o.ontology
        assert o._ontology is not None

    def test_reload(self):
        o = LoreOntology(EXAMPLE_DIR)
        _ = o.ontology
        assert o._ontology is not None
        o.reload()
        assert o._ontology is None

    def test_path_property(self):
        o = LoreOntology(EXAMPLE_DIR)
        assert o.path == EXAMPLE_DIR


class TestSDKCompilation:
    """SDK compile methods."""

    def test_compile_agent_context(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_agent_context()
        assert "<domain_ontology>" in result
        assert "Account" in result

    def test_compile_agent_context_with_view(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_agent_context(view="Account Executive")
        assert "Scoped to view" in result

    def test_compile_agent_context_with_budget(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_agent_context(budget=4000)
        assert "<budget_metadata>" in result

    def test_compile_json(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_json()
        data = json.loads(result)
        assert "entities" in data
        assert len(data["entities"]) > 0

    def test_compile_mermaid(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_mermaid()
        assert "erDiagram" in result

    def test_compile_embeddings(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_embeddings()
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        assert len(chunks) > 0


class TestSDKQuery:
    """SDK query methods."""

    def test_query_entities_all(self):
        o = LoreOntology(EXAMPLE_DIR)
        entities = o.query_entities()
        assert len(entities) == len(o.ontology.entities)

    def test_query_entities_by_status(self):
        o = LoreOntology(EXAMPLE_DIR)
        stable = o.query_entities(status="stable")
        for e in stable:
            assert e.status == "stable"

    def test_query_entities_by_name(self):
        o = LoreOntology(EXAMPLE_DIR)
        results = o.query_entities(name_contains="account")
        for e in results:
            assert "account" in e.name.lower()

    def test_get_entity(self):
        o = LoreOntology(EXAMPLE_DIR)
        e = o.get_entity("Account")
        assert e is not None
        assert e.name == "Account"

    def test_get_entity_case_insensitive(self):
        o = LoreOntology(EXAMPLE_DIR)
        e = o.get_entity("account")
        assert e is not None
        assert e.name == "Account"

    def test_get_entity_not_found(self):
        o = LoreOntology(EXAMPLE_DIR)
        e = o.get_entity("NonExistent")
        assert e is None

    def test_relationships_for(self):
        o = LoreOntology(EXAMPLE_DIR)
        rels = o.relationships_for("Account")
        assert len(rels) > 0
        for r in rels:
            assert r.from_entity == "Account" or r.to_entity == "Account"

    def test_rules_for(self):
        o = LoreOntology(EXAMPLE_DIR)
        # Find an entity that has rules
        all_rules = o.ontology.all_rules
        if all_rules:
            entity_name = all_rules[0].applies_to
            if entity_name:
                rules = o.rules_for(entity_name)
                assert len(rules) > 0


class TestSDKSearch:
    """SDK full-text search."""

    def test_search_returns_results(self):
        o = LoreOntology(EXAMPLE_DIR)
        results = o.search("churn risk")
        assert len(results) > 0

    def test_search_results_have_scores(self):
        o = LoreOntology(EXAMPLE_DIR)
        results = o.search("account revenue")
        for r in results:
            assert "score" in r
            assert r["score"] > 0

    def test_search_results_sorted_by_score(self):
        o = LoreOntology(EXAMPLE_DIR)
        results = o.search("subscription plan")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_empty_query(self):
        o = LoreOntology(EXAMPLE_DIR)
        results = o.search("")
        assert results == []


class TestSDKStats:
    """SDK stats property."""

    def test_stats_has_all_keys(self):
        o = LoreOntology(EXAMPLE_DIR)
        stats = o.stats
        expected_keys = {
            "name", "version", "entities", "attributes", "relationships",
            "traversals", "rules", "taxonomies", "glossary_terms",
            "views", "observations", "outcomes", "claims", "decisions",
        }
        assert expected_keys == set(stats.keys())

    def test_stats_values_positive(self):
        o = LoreOntology(EXAMPLE_DIR)
        stats = o.stats
        assert stats["entities"] > 0
        assert stats["relationships"] > 0


class TestSDKValidation:
    """SDK validate method."""

    def test_validate_returns_diagnostics(self):
        o = LoreOntology(EXAMPLE_DIR)
        diags = o.validate()
        assert isinstance(diags, list)
        # Example should have no errors
        errors = [d for d in diags if d.severity == Severity.ERROR]
        assert len(errors) == 0


class TestSDKEntityContext:
    """SDK entity context slice."""

    def test_compile_entity_context(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_entity_context("Account")
        assert "<entity_context" in result
        assert "Account" in result
        assert "</entity_context>" in result

    def test_entity_context_includes_relationships(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_entity_context("Account")
        # Should include related entities section if Account has relationships
        if o.relationships_for("Account"):
            assert "<related_entities>" in result

    def test_entity_context_not_found(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_entity_context("NonExistent")
        assert result == ""

    def test_entity_context_with_budget(self):
        o = LoreOntology(EXAMPLE_DIR)
        result = o.compile_entity_context("Account", budget=500)
        assert isinstance(result, str)
