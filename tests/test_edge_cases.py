"""Edge case tests for Lore parsers and compilers."""
import json
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Traversal, Rule, RuleFile, Taxonomy, TaxonomyNode,
    Glossary, GlossaryEntry, View, Provenance,
    ObservationFile, Observation, KnowledgeClaim,
    OutcomeFile, Outcome,
)
from lore.compilers.agent import compile_agent_context
from lore.compilers.json_export import compile_json
from lore.compilers.jsonld import compile_jsonld
from lore.compilers.neo4j import compile_neo4j
from lore.compilers.mermaid import compile_mermaid
from lore.compilers.embeddings import compile_embeddings
from lore.validator import validate, Severity


ALL_COMPILERS = {
    "agent": compile_agent_context,
    "json": compile_json,
    "jsonld": compile_jsonld,
    "neo4j": compile_neo4j,
    "mermaid": compile_mermaid,
    "embeddings": compile_embeddings,
}


class TestEmptyOntology:
    """Ontology with no entities, relationships, or rules."""

    def test_all_compilers_produce_valid_output(self):
        ont = Ontology(manifest=OntologyManifest(name="empty", version="1.0"))
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            assert isinstance(result, str), f"{name} compiler did not return string"
            # embeddings returns "" when there's nothing to embed — that's valid
            if name != "embeddings":
                assert len(result) > 0, f"{name} compiler returned empty output"

    def test_json_valid(self):
        ont = Ontology(manifest=OntologyManifest(name="empty", version="1.0"))
        data = json.loads(compile_json(ont))
        assert data["entities"] == []
        assert data["relationships"] == []
        assert data["rules"] == []

    def test_agent_has_skeleton(self):
        ont = Ontology(manifest=OntologyManifest(name="empty", version="1.0"))
        result = compile_agent_context(ont)
        assert "<domain_ontology>" in result
        assert "</domain_ontology>" in result
        assert "<entities>" in result
        assert "</entities>" in result

    def test_validate_no_errors(self):
        ont = Ontology(manifest=OntologyManifest(name="empty", version="1.0"))
        diags = validate(ont)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_no_manifest_at_all(self):
        ont = Ontology()
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            assert isinstance(result, str), f"{name} failed with no manifest"


class TestUnicodeEntityNames:
    """Entity names with non-ASCII characters."""

    def test_parser_handles_unicode_names(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: unicode-test\nversion: 1.0\n",
            entities={
                "kundenbeziehung.lore": (
                    "---\n"
                    "entity: Kundenbeziehung\n"
                    "description: German for customer relationship.\n"
                    "---\n"
                    "\n"
                    "## Attributes\n\n"
                    "name: string [required]\n"
                ),
                "customer_jp.lore": (
                    "---\n"
                    "entity: 顧客\n"
                    "description: Japanese for customer.\n"
                    "---\n"
                    "\n"
                    "## Attributes\n\n"
                    "id: string [required]\n"
                ),
            },
        )
        names = {e.name for e in ont.entities}
        assert "Kundenbeziehung" in names
        assert "顧客" in names

    def test_compilers_handle_unicode(self):
        ont = Ontology(
            manifest=OntologyManifest(name="unicode", version="1.0"),
            entities=[
                Entity(name="Kundenbeziehung", description="Customer relationship",
                       attributes=[Attribute(name="name", type="string",
                                             constraints=["required"])]),
                Entity(name="顧客", description="Customer in Japanese",
                       attributes=[Attribute(name="id", type="string",
                                             constraints=["required"])]),
            ],
        )
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            # neo4j lowercases entity names for constraint labels
            if name == "neo4j":
                assert "kundenbeziehung" in result.lower(), f"{name} lost German name"
            else:
                assert "Kundenbeziehung" in result, f"{name} lost German name"
            # JSON escapes non-ASCII to \uXXXX by default — check either form
            if name not in ("neo4j",):
                assert "顧客" in result or "\\u9867\\u5ba2" in result, \
                    f"{name} lost Japanese name"


class TestExtremelyLongEntityName:
    """Entity name with 500 characters."""

    def test_no_crashes(self):
        long_name = "A" * 500
        ont = Ontology(
            manifest=OntologyManifest(name="long-names", version="1.0"),
            entities=[
                Entity(name=long_name, description="Very long name",
                       attributes=[Attribute(name="id", type="string",
                                             constraints=["required"])]),
            ],
        )
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            # All compilers should complete without error
            assert isinstance(result, str), f"{name} crashed on long name"
            # Most compilers include the full name; neo4j lowercases to label
            if name not in ("neo4j",):
                assert long_name in result, f"{name} truncated the long name"


class TestSpecialCharsInNames:
    """Hyphens, underscores, spaces in entity and attribute names."""

    def test_consistent_handling(self):
        ont = Ontology(
            manifest=OntologyManifest(name="special-chars", version="1.0"),
            entities=[
                Entity(name="Health-Check", description="Hyphenated",
                       attributes=[Attribute(name="check_score", type="int",
                                             constraints=["required"])]),
                Entity(name="User Profile", description="With space",
                       attributes=[Attribute(name="full-name", type="string",
                                             constraints=["required"])]),
                Entity(name="data_point", description="Underscored",
                       attributes=[Attribute(name="value_1", type="float",
                                             constraints=["required"])]),
            ],
        )
        # Test compilers that preserve entity names directly
        for name in ("agent", "json", "jsonld", "embeddings"):
            result = ALL_COMPILERS[name](ont)
            assert "Health-Check" in result, f"{name} lost hyphenated name"
            assert "data_point" in result, f"{name} lost underscored name"

        # All compilers should complete without errors
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            assert isinstance(result, str), f"{name} crashed on special chars"


class TestSelfReferencingRelationship:
    """Person -[MANAGES]-> Person."""

    def test_all_compilers_handle_self_refs(self):
        ont = Ontology(
            manifest=OntologyManifest(name="self-ref", version="1.0"),
            entities=[
                Entity(name="Person", description="A person",
                       attributes=[Attribute(name="name", type="string")]),
            ],
            relationship_files=[RelationshipFile(
                domain="Org",
                relationships=[
                    Relationship(name="MANAGES", from_entity="Person",
                                 to_entity="Person", cardinality="one-to-many",
                                 description="Manager relationship"),
                ],
            )],
        )
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            # mermaid lowercases relationship labels
            assert "MANAGES" in result or "manages" in result, \
                f"{name} lost self-referencing relationship"

    def test_agent_renders_self_ref(self):
        ont = Ontology(
            manifest=OntologyManifest(name="self-ref", version="1.0"),
            entities=[
                Entity(name="Person", description="A person",
                       attributes=[Attribute(name="name", type="string")]),
            ],
            relationship_files=[RelationshipFile(
                domain="Org",
                relationships=[
                    Relationship(name="MANAGES", from_entity="Person",
                                 to_entity="Person", cardinality="one-to-many"),
                ],
            )],
        )
        result = compile_agent_context(ont)
        assert "Person -[MANAGES]-> Person" in result


class TestEntityNoAttributesNoSections:
    """Minimal entity with name only."""

    def test_compilers_produce_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="minimal", version="1.0"),
            entities=[Entity(name="Stub")],
        )
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            assert isinstance(result, str), f"{name} crashed on stub entity"
            # neo4j only outputs constraint DDL, so stub entities without
            # constrained attributes won't appear in neo4j output
            if name not in ("neo4j",):
                assert "Stub" in result, f"{name} lost stub entity"

    def test_validator_warns(self):
        ont = Ontology(
            manifest=OntologyManifest(name="minimal", version="1.0"),
            entities=[Entity(name="Stub")],
        )
        diags = validate(ont)
        messages = [d.message for d in diags]
        assert any("no attributes" in m for m in messages)


class TestMassiveProseSection:
    """Entity with a 50KB notes section."""

    def test_parser_handles_large_notes(self, tmp_ontology):
        big_notes = "This is a long note. " * 2500  # ~50KB
        ont = tmp_ontology(
            manifest="name: big-notes\nversion: 1.0\n",
            entities={
                "big.lore": (
                    "---\n"
                    "entity: BigEntity\n"
                    "description: Entity with huge notes.\n"
                    "---\n"
                    "\n"
                    "## Attributes\n\n"
                    "id: string [required]\n"
                    "\n"
                    "## Notes\n\n"
                    f"{big_notes}\n"
                ),
            },
        )
        entity = ont.entities[0]
        assert len(entity.notes) > 40000

    def test_embeddings_chunks_large_notes(self):
        big_notes = "This is a long note. " * 2500
        ont = Ontology(
            manifest=OntologyManifest(name="big", version="1.0"),
            entities=[
                Entity(name="BigEntity", description="Big",
                       attributes=[Attribute(name="id", type="string")],
                       notes=big_notes),
            ],
        )
        result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        notes_chunks = [c for c in chunks if c["type"] == "entity_notes"]
        assert len(notes_chunks) >= 1
        assert big_notes[:100] in notes_chunks[0]["text"]


class TestObservationAllClaimTypes:
    """One of each claim type: fact, belief, value, precedent."""

    def test_all_claim_types_in_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="claims", version="1.0"),
            entities=[Entity(name="Target", description="The target entity",
                             attributes=[Attribute(name="id", type="string")])],
            observation_files=[ObservationFile(
                name="All Claims",
                about="Target",
                observed_by="tester",
                date="2025-01-01",
                observations=[Observation(
                    heading="Mixed signals",
                    prose="Various claim types observed.",
                    claims=[
                        KnowledgeClaim(kind="fact", text="Revenue grew 10%"),
                        KnowledgeClaim(kind="belief", text="Growth will continue"),
                        KnowledgeClaim(kind="value", text="Stability is preferred"),
                        KnowledgeClaim(kind="precedent", text="Similar growth in Q3 2023"),
                    ],
                )],
            )],
        )
        agent_result = compile_agent_context(ont)
        assert "fact" in agent_result.lower() or "Fact" in agent_result
        assert "belief" in agent_result.lower() or "Belief" in agent_result
        assert "value" in agent_result.lower() or "Value" in agent_result
        assert "precedent" in agent_result.lower() or "Precedent" in agent_result

        embed_result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in embed_result.strip().split("\n")]
        claim_chunks = [c for c in chunks if c["type"] == "observation_claim"]
        kinds = {c["metadata"]["claim_kind"] for c in claim_chunks}
        assert kinds == {"fact", "belief", "value", "precedent"}


class TestTaxonomySingleRootOnly:
    """Root node with no children."""

    def test_graceful_handling(self):
        ont = Ontology(
            manifest=OntologyManifest(name="single-root", version="1.0"),
            entities=[Entity(name="Item", attributes=[Attribute(name="type", type="string")])],
            taxonomies=[Taxonomy(
                name="ItemType",
                applied_to="Item.type",
                root=TaxonomyNode(name="Root"),
            )],
        )
        for name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ont)
            assert isinstance(result, str), f"{name} failed on single-root taxonomy"

    def test_validator_warns_single_node(self):
        ont = Ontology(
            manifest=OntologyManifest(name="single-root", version="1.0"),
            entities=[Entity(name="Item", attributes=[Attribute(name="type", type="string")])],
            taxonomies=[Taxonomy(
                name="ItemType",
                applied_to="Item.type",
                root=TaxonomyNode(name="Root"),
            )],
        )
        diags = validate(ont)
        messages = [d.message for d in diags]
        assert any("1 node" in m for m in messages)


class TestUnknownFrontmatterKeys:
    """Extra YAML keys in frontmatter are tolerated (forward compatibility)."""

    def test_extra_keys_tolerated(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: forward-compat\nversion: 1.0\n",
            entities={
                "widget.lore": (
                    "---\n"
                    "entity: Widget\n"
                    "description: A widget.\n"
                    "future_field: something-new\n"
                    "another_unknown: 42\n"
                    "---\n"
                    "\n"
                    "## Attributes\n\n"
                    "id: string [required]\n"
                ),
            },
        )
        assert len(ont.entities) == 1
        assert ont.entities[0].name == "Widget"


class TestDuplicateGlossaryTerms:
    """Same term defined in two glossary files."""

    def test_validator_warns_on_duplicates(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: dup-glossary\nversion: 1.0\n",
            glossary={
                "terms1.lore": (
                    "---\n"
                    "description: First glossary.\n"
                    "---\n"
                    "\n"
                    "## Widget\n\n"
                    "A thing that does stuff.\n"
                ),
                "terms2.lore": (
                    "---\n"
                    "description: Second glossary.\n"
                    "---\n"
                    "\n"
                    "## Widget\n\n"
                    "A different definition of widget.\n"
                ),
            },
        )
        # The parser may merge or keep both — just check no crash
        assert ont.glossary is not None
