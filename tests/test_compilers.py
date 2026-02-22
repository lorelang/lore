"""Tests for all Lore compilers."""
import json
import pytest
from lore.compilers.agent import compile_agent_context
from lore.compilers.json_export import compile_json
from lore.compilers.neo4j import compile_neo4j
from lore.compilers.mermaid import compile_mermaid
from lore.compilers.embeddings import compile_embeddings
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Traversal, Rule, RuleFile, Taxonomy, TaxonomyNode,
    Glossary, GlossaryEntry, View,
)


@pytest.fixture
def minimal_ontology():
    """A minimal ontology for compiler testing."""
    return Ontology(
        manifest=OntologyManifest(name="test-domain", version="1.0", description="Test domain", domain="Testing"),
        entities=[
            Entity(
                name="Widget",
                description="A test widget",
                attributes=[
                    Attribute(name="id", type="string", constraints=["required", "unique"]),
                    Attribute(name="status", type="enum [active, inactive]"),
                    Attribute(name="owner", type="reference", reference_to="Person"),
                ],
                identity="Identified by id.",
                lifecycle="Created, then activated.",
                notes="Test entity.",
            ),
            Entity(
                name="Person",
                description="A person",
                attributes=[
                    Attribute(name="name", type="string", constraints=["required"]),
                    Attribute(name="email", type="string", constraints=["unique"]),
                ],
            ),
        ],
        relationship_files=[RelationshipFile(
            domain="Core",
            relationships=[
                Relationship(
                    name="OWNS",
                    from_entity="Person",
                    to_entity="Widget",
                    cardinality="one-to-many",
                    description="A person owns widgets.",
                ),
            ],
            traversals=[
                Traversal(
                    name="person-widgets",
                    path="Person -[OWNS]-> Widget",
                    description="Find all widgets for a person.",
                ),
            ],
        )],
        rule_files=[RuleFile(
            domain="Alerts",
            rules=[
                Rule(
                    name="inactive-widget-alert",
                    applies_to="Widget",
                    severity="warning",
                    trigger="Widget becomes inactive",
                    condition="widget.status = 'inactive'",
                    action="Notify owner",
                    prose="Inactive widgets may need attention.",
                ),
            ],
        )],
        taxonomies=[
            Taxonomy(
                name="WidgetType",
                applied_to="Widget.type",
                root=TaxonomyNode(
                    name="Widget",
                    children=[
                        TaxonomyNode(name="Physical", tags=["tangible"], children=[
                            TaxonomyNode(name="Large", description="Big widgets"),
                            TaxonomyNode(name="Small", description="Tiny widgets"),
                        ]),
                        TaxonomyNode(name="Digital", tags=["virtual"]),
                    ],
                ),
                inheritance_rules="Physical widgets must have dimensions.",
            ),
        ],
        glossary=Glossary(entries=[
            GlossaryEntry(term="Widget", definition="A thing that does stuff."),
            GlossaryEntry(term="Owner", definition="The person responsible."),
        ]),
        views=[
            View(
                name="Admin",
                description="Admin view of all widgets.",
                audience="Administrators",
                entities=["Widget", "Person"],
                relationships=["OWNS"],
                rules=["inactive-widget-alert"],
                key_questions=["How many inactive widgets?", "Who owns the most?"],
                not_in_scope="Billing info",
            ),
        ],
    )


# --- Agent Compiler ---

class TestAgentCompiler:
    def test_output_has_domain_ontology_tags(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<domain_ontology>" in result
        assert "</domain_ontology>" in result

    def test_output_has_entities(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<entities>" in result
        assert '<entity name="Widget">' in result
        assert '<entity name="Person">' in result

    def test_entity_attributes_included(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "id: string" in result
        assert "required, unique" in result

    def test_output_has_relationships(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<relationships>" in result
        assert "Person -[OWNS]-> Widget" in result

    def test_output_has_traversals(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<traversals>" in result
        assert "person-widgets" in result

    def test_output_has_rules(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<rules>" in result
        assert "inactive-widget-alert" in result

    def test_output_has_taxonomies(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<taxonomies>" in result
        assert "WidgetType" in result

    def test_output_has_glossary(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology)
        assert "<glossary>" in result
        assert "Widget:" in result

    def test_view_scoping(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology, view_name="Admin")
        assert "Scoped to view: Admin" in result
        assert "<key_questions>" in result

    def test_view_not_found(self, minimal_ontology):
        result = compile_agent_context(minimal_ontology, view_name="NonExistent")
        # Should still produce output, just not scoped
        assert "<domain_ontology>" in result

    def test_full_example(self, example_ontology):
        result = compile_agent_context(example_ontology)
        assert "Account" in result
        assert "HAS_SUBSCRIPTION" in result
        assert "champion-departure-alert" in result


# --- JSON Compiler ---

class TestJsonCompiler:
    def test_valid_json(self, minimal_ontology):
        result = compile_json(minimal_ontology)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_json_has_metadata(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert data["metadata"]["name"] == "test-domain"
        assert data["metadata"]["version"] == "1.0"

    def test_json_has_entities(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["entities"]) == 2
        widget = next(e for e in data["entities"] if e["name"] == "Widget")
        assert len(widget["attributes"]) == 3

    def test_json_entity_attributes(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        widget = next(e for e in data["entities"] if e["name"] == "Widget")
        id_attr = next(a for a in widget["attributes"] if a["name"] == "id")
        assert id_attr["type"] == "string"
        assert "required" in id_attr["constraints"]

    def test_json_has_relationships(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["relationships"]) == 1
        rel = data["relationships"][0]
        assert rel["name"] == "OWNS"
        assert rel["from"] == "Person"

    def test_json_has_traversals(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["traversals"]) == 1

    def test_json_has_rules(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["rules"]) == 1
        rule = data["rules"][0]
        assert rule["name"] == "inactive-widget-alert"

    def test_json_has_taxonomies(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["taxonomies"]) == 1
        tax = data["taxonomies"][0]
        assert tax["tree"]["name"] == "Widget"
        assert len(tax["tree"]["children"]) == 2

    def test_json_has_glossary(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["glossary"]) == 2

    def test_json_has_views(self, minimal_ontology):
        data = json.loads(compile_json(minimal_ontology))
        assert len(data["views"]) == 1

    def test_json_no_manifest(self):
        ont = Ontology()
        data = json.loads(compile_json(ont))
        assert data["metadata"] == {}

    def test_full_example(self, example_ontology):
        data = json.loads(compile_json(example_ontology))
        assert len(data["entities"]) == 11
        assert len(data["relationships"]) == 18


# --- Neo4j Compiler ---

class TestNeo4jCompiler:
    def test_output_has_header(self, minimal_ontology):
        result = compile_neo4j(minimal_ontology)
        assert "Lore → Neo4j Schema" in result

    def test_unique_constraints(self, minimal_ontology):
        result = compile_neo4j(minimal_ontology)
        assert "widget_id_unique" in result
        assert "IS UNIQUE" in result

    def test_required_constraints(self, minimal_ontology):
        result = compile_neo4j(minimal_ontology)
        assert "IS NOT NULL" in result

    def test_indexes_for_enums(self, minimal_ontology):
        result = compile_neo4j(minimal_ontology)
        assert "CREATE INDEX" in result

    def test_relationship_documentation(self, minimal_ontology):
        result = compile_neo4j(minimal_ontology)
        assert "OWNS" in result
        assert "Person" in result
        assert "Widget" in result

    def test_traversal_queries(self, minimal_ontology):
        result = compile_neo4j(minimal_ontology)
        assert "person-widgets" in result

    def test_full_example(self, example_ontology):
        result = compile_neo4j(example_ontology)
        assert "Account" in result
        assert "CREATE CONSTRAINT" in result


# --- Mermaid Compiler ---

class TestMermaidCompiler:
    def test_output_starts_with_diagram(self, minimal_ontology):
        result = compile_mermaid(minimal_ontology)
        assert "erDiagram" in result

    def test_has_title(self, minimal_ontology):
        result = compile_mermaid(minimal_ontology)
        assert "test-domain" in result

    def test_entity_definitions(self, minimal_ontology):
        result = compile_mermaid(minimal_ontology)
        assert "Widget {" in result
        assert "Person {" in result

    def test_entity_attributes(self, minimal_ontology):
        result = compile_mermaid(minimal_ontology)
        assert "string id" in result
        assert "PK" in result  # unique constraint

    def test_relationship_lines(self, minimal_ontology):
        result = compile_mermaid(minimal_ontology)
        assert "Person" in result
        assert "Widget" in result
        assert "owns" in result.lower()

    def test_cardinality_mapping(self):
        from lore.compilers.mermaid import _mermaid_cardinality
        assert _mermaid_cardinality("one-to-many") == "||--o{"
        assert _mermaid_cardinality("many-to-one") == "}o--||"
        assert _mermaid_cardinality("one-to-one") == "||--||"
        assert _mermaid_cardinality("many-to-many") == "}o--o{"

    def test_type_mapping(self):
        from lore.compilers.mermaid import _mermaid_type
        assert _mermaid_type("string") == "string"
        assert _mermaid_type("int") == "int"
        assert _mermaid_type("boolean") == "bool"
        assert _mermaid_type("enum [a, b]") == "enum"
        assert _mermaid_type("list<string>") == "list"

    def test_full_example(self, example_ontology):
        result = compile_mermaid(example_ontology)
        assert "Account" in result
        assert "erDiagram" in result


# --- Embeddings Compiler ---

class TestEmbeddingsCompiler:
    def test_output_is_jsonl(self, minimal_ontology):
        result = compile_embeddings(minimal_ontology)
        lines = result.strip().split("\n")
        for line in lines:
            data = json.loads(line)
            assert "id" in data
            assert "type" in data
            assert "text" in data

    def test_entity_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        entity_chunks = [c for c in chunks if c["type"] == "entity"]
        assert len(entity_chunks) == 2

    def test_entity_attribute_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        attr_chunks = [c for c in chunks if c["type"] == "entity_attributes"]
        assert len(attr_chunks) == 2

    def test_relationship_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        rel_chunks = [c for c in chunks if c["type"] == "relationship"]
        assert len(rel_chunks) == 1

    def test_traversal_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        trav_chunks = [c for c in chunks if c["type"] == "traversal"]
        assert len(trav_chunks) == 1

    def test_rule_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        rule_chunks = [c for c in chunks if c["type"] == "rule"]
        assert len(rule_chunks) == 1

    def test_taxonomy_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        tax_chunks = [c for c in chunks if c["type"].startswith("taxonomy")]
        assert len(tax_chunks) >= 3  # branch + leaves + inheritance rules

    def test_glossary_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        gloss_chunks = [c for c in chunks if c["type"] == "glossary"]
        assert len(gloss_chunks) == 2

    def test_chunk_has_metadata(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        entity_chunk = next(c for c in chunks if c["type"] == "entity")
        assert "metadata" in entity_chunk

    def test_lifecycle_chunks(self, minimal_ontology):
        chunks = _parse_chunks(compile_embeddings(minimal_ontology))
        lc_chunks = [c for c in chunks if c["type"] == "entity_lifecycle"]
        assert len(lc_chunks) == 1  # Only Widget has lifecycle

    def test_full_example(self, example_ontology):
        chunks = _parse_chunks(compile_embeddings(example_ontology))
        assert len(chunks) > 30  # Should have many chunks


def _parse_chunks(jsonl: str) -> list[dict]:
    return [json.loads(line) for line in jsonl.strip().split("\n") if line.strip()]
