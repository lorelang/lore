"""Tests for the tool schema compiler."""
import json
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, RelationshipProperty,
)
from lore.compilers.tools import compile_tools, generate_tool_schemas


@pytest.fixture
def tool_ontology():
    return Ontology(
        manifest=OntologyManifest(name="tool-test", version="1.0"),
        entities=[
            Entity(
                name="Account",
                description="A customer account.",
                attributes=[
                    Attribute(name="id", type="string",
                              constraints=["required", "unique"],
                              description="Unique account identifier"),
                    Attribute(name="name", type="string",
                              constraints=["required"],
                              description="Account name"),
                    Attribute(name="status", type="enum",
                              enum_values=["active", "inactive", "churned"],
                              description="Current account status"),
                    Attribute(name="revenue", type="float",
                              description="Annual revenue"),
                ],
            ),
            Entity(
                name="Contact",
                description="A person at an account.",
                attributes=[
                    Attribute(name="email", type="string",
                              constraints=["required", "unique"],
                              description="Email address"),
                    Attribute(name="role", type="string",
                              description="Job role"),
                    Attribute(name="account", type="reference",
                              reference_to="Account",
                              description="Parent account"),
                ],
            ),
        ],
        relationship_files=[RelationshipFile(
            domain="Core",
            relationships=[
                Relationship(
                    name="HAS_CONTACT",
                    from_entity="Account",
                    to_entity="Contact",
                    cardinality="one-to-many",
                    description="Account's contacts.",
                    properties=[
                        RelationshipProperty(name="role", type="string",
                                             description="Contact role"),
                    ],
                ),
            ],
        )],
    )


class TestToolSchemaGeneration:
    def test_generates_get_and_list_per_entity(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        names = [s["function"]["name"] for s in schemas]
        assert "get_account" in names
        assert "list_accounts" in names
        assert "get_contact" in names
        assert "list_contacts" in names

    def test_generates_relationship_tools(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        names = [s["function"]["name"] for s in schemas]
        assert "query_has_contact" in names

    def test_get_tool_has_id_parameter(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        get_account = next(s for s in schemas
                           if s["function"]["name"] == "get_account")
        params = get_account["function"]["parameters"]
        assert "id" in params["properties"]
        assert "id" in params["required"]

    def test_list_tool_has_enum_filter(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        list_accounts = next(s for s in schemas
                             if s["function"]["name"] == "list_accounts")
        params = list_accounts["function"]["parameters"]
        assert "status" in params["properties"]
        assert params["properties"]["status"]["enum"] == [
            "active", "inactive", "churned"
        ]

    def test_list_tool_has_limit(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        list_accounts = next(s for s in schemas
                             if s["function"]["name"] == "list_accounts")
        params = list_accounts["function"]["parameters"]
        assert "limit" in params["properties"]

    def test_relationship_tool_has_from_entity(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        query = next(s for s in schemas
                     if s["function"]["name"] == "query_has_contact")
        params = query["function"]["parameters"]
        assert "from_entity" in params["properties"]
        assert "from_entity" in params["required"]


class TestToolSchemaFormats:
    def test_openai_format(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology, fmt="openai")
        for s in schemas:
            assert s["type"] == "function"
            assert "function" in s
            assert "name" in s["function"]

    def test_anthropic_format(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology, fmt="anthropic")
        for s in schemas:
            assert s["type"] == "function"
            assert "function" in s

    def test_json_schema_format(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology, fmt="json_schema")
        for s in schemas:
            assert "name" in s
            assert "parameters" in s
            assert "type" not in s or s.get("type") != "function"


class TestCompileToolsOutput:
    def test_valid_json(self, tool_ontology):
        result = compile_tools(tool_ontology)
        data = json.loads(result)
        assert isinstance(data, list)

    def test_reference_types(self, tool_ontology):
        schemas = generate_tool_schemas(tool_ontology)
        get_contact = next(s for s in schemas
                           if s["function"]["name"] == "get_contact")
        params = get_contact["function"]["parameters"]
        assert "email" in params["properties"]


class TestEmptyOntologyTools:
    def test_empty_produces_empty(self):
        ont = Ontology(manifest=OntologyManifest(name="empty", version="1.0"))
        schemas = generate_tool_schemas(ont)
        assert schemas == []

    def test_entity_no_attributes(self):
        ont = Ontology(
            manifest=OntologyManifest(name="stub", version="1.0"),
            entities=[Entity(name="Stub")],
        )
        schemas = generate_tool_schemas(ont)
        assert len(schemas) == 2  # get + list
