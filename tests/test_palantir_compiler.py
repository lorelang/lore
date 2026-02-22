"""Tests for the Palantir Foundry ontology compiler."""
import json
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Provenance,
)
from lore.compilers.palantir import (
    compile_palantir, _api_name, _palantir_type, _plural,
)


class TestHelpers:
    def test_api_name_pascal_case(self):
        assert _api_name("Account") == "account"

    def test_api_name_already_lower(self):
        assert _api_name("name") == "name"

    def test_api_name_snake_case(self):
        assert _api_name("health_score") == "healthScore"

    def test_api_name_multi_word(self):
        assert _api_name("fiscal_year_end") == "fiscalYearEnd"

    def test_palantir_type_string(self):
        assert _palantir_type("string") == {"type": "string"}

    def test_palantir_type_int(self):
        assert _palantir_type("integer") == {"type": "integer"}

    def test_palantir_type_float(self):
        assert _palantir_type("float") == {"type": "double"}

    def test_palantir_type_boolean(self):
        assert _palantir_type("boolean") == {"type": "boolean"}

    def test_palantir_type_date(self):
        assert _palantir_type("date") == {"type": "date"}

    def test_palantir_type_unknown_defaults_string(self):
        assert _palantir_type("some_custom_type") == {"type": "string"}

    def test_plural_regular(self):
        assert _plural("Account") == "Accounts"

    def test_plural_y_ending(self):
        assert _plural("Opportunity") == "Opportunities"

    def test_plural_s_ending(self):
        assert _plural("Status") == "Statuses"


class TestPalantirCompiler:
    def test_basic_output_structure(self):
        """Compiler produces valid OntologyFullMetadata structure."""
        ont = Ontology(
            manifest=OntologyManifest(name="test-ont", version="1.0",
                                      description="Test ontology"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="name", type="string", constraints=["required"])],
            )],
        )
        result = json.loads(compile_palantir(ont))
        assert "ontology" in result
        assert "objectTypes" in result
        assert "actionTypes" in result
        assert result["ontology"]["displayName"] == "test-ont"

    def test_entity_becomes_object_type(self):
        """Entity maps to a Palantir Object Type."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                description="A customer account",
                attributes=[
                    Attribute(name="name", type="string", constraints=["required"]),
                    Attribute(name="arr", type="currency"),
                    Attribute(name="active", type="boolean"),
                ],
            )],
        )
        result = json.loads(compile_palantir(ont))
        account = result["objectTypes"]["account"]
        assert account["objectType"]["apiName"] == "account"
        assert account["objectType"]["displayName"] == "Account"
        assert account["objectType"]["description"] == "A customer account"
        assert "name" in account["objectType"]["properties"]
        assert "arr" in account["objectType"]["properties"]
        assert "active" in account["objectType"]["properties"]

    def test_primary_key_from_required(self):
        """First required attribute becomes primary key."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[
                    Attribute(name="domain_id", type="string", constraints=["required"]),
                    Attribute(name="name", type="string"),
                ],
            )],
        )
        result = json.loads(compile_palantir(ont))
        assert result["objectTypes"]["account"]["objectType"]["primaryKey"] == "domainId"

    def test_auto_generated_primary_key(self):
        """Entity with no required attrs gets auto-generated PK."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Signal",
                attributes=[Attribute(name="type", type="string")],
            )],
        )
        result = json.loads(compile_palantir(ont))
        pk = result["objectTypes"]["signal"]["objectType"]["primaryKey"]
        assert pk == "signalId"  # auto-generated

    def test_relationships_become_link_types(self):
        """Relationships map to Palantir Link Types."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Account", attributes=[]),
                Entity(name="Contact", attributes=[]),
            ],
            relationship_files=[RelationshipFile(
                domain="Core",
                relationships=[Relationship(
                    name="HAS_CONTACT",
                    from_entity="Account",
                    to_entity="Contact",
                    description="Account has contacts",
                )],
            )],
        )
        result = json.loads(compile_palantir(ont))
        account = result["objectTypes"]["account"]
        assert "hasContact" in account["linkTypes"]
        link = account["linkTypes"]["hasContact"]
        assert link["objectTypeApiName"] == "contact"

    def test_rules_become_action_types(self):
        """Rules map to Palantir Action Types."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
            rule_files=[RuleFile(
                domain="Churn",
                rules=[Rule(
                    name="churn-alert",
                    applies_to="Account",
                    trigger="Usage drops 30%",
                    condition="Account.usage_trend < -0.3",
                    action="Flag for CSM review",
                )],
            )],
        )
        result = json.loads(compile_palantir(ont))
        assert "churnAlert" in result["actionTypes"]
        action = result["actionTypes"]["churnAlert"]
        assert "Trigger:" in action["description"]
        assert "targetEntity" in action["parameters"]

    def test_status_mapping(self):
        """Lore status maps to Palantir status."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Stable", attributes=[], status="stable"),
                Entity(name="Draft", attributes=[], status="draft"),
                Entity(name="Old", attributes=[], status="deprecated"),
            ],
        )
        result = json.loads(compile_palantir(ont))
        assert result["objectTypes"]["stable"]["objectType"]["status"] == "ACTIVE"
        assert result["objectTypes"]["draft"]["objectType"]["status"] == "EXPERIMENTAL"
        assert result["objectTypes"]["old"]["objectType"]["status"] == "DEPRECATED"

    def test_rid_format(self):
        """Generated RIDs follow Palantir format."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        result = json.loads(compile_palantir(ont))
        rid = result["ontology"]["rid"]
        assert rid.startswith("ri.ontology.main.ontology.")

    def test_property_types(self):
        """Various Lore types map correctly to Palantir types."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Test",
                attributes=[
                    Attribute(name="name", type="string"),
                    Attribute(name="count", type="integer"),
                    Attribute(name="score", type="float"),
                    Attribute(name="active", type="boolean"),
                    Attribute(name="created", type="date"),
                    Attribute(name="amount", type="currency"),
                    Attribute(name="rate", type="percentage"),
                ],
            )],
        )
        result = json.loads(compile_palantir(ont))
        props = result["objectTypes"]["test"]["objectType"]["properties"]
        assert props["name"]["dataType"] == {"type": "string"}
        assert props["count"]["dataType"] == {"type": "integer"}
        assert props["score"]["dataType"] == {"type": "double"}
        assert props["active"]["dataType"] == {"type": "boolean"}
        assert props["created"]["dataType"] == {"type": "date"}
        assert props["amount"]["dataType"] == {"type": "double"}
        assert props["rate"]["dataType"] == {"type": "double"}


class TestPalantirOnExample:
    def test_example_compiles(self, example_ontology):
        """Full example compiles to valid JSON."""
        result = json.loads(compile_palantir(example_ontology))
        assert len(result["objectTypes"]) == 11
        assert "account" in result["objectTypes"]
        assert len(result["actionTypes"]) > 0

    def test_example_has_link_types(self, example_ontology):
        """Example has link types on object types."""
        result = json.loads(compile_palantir(example_ontology))
        account = result["objectTypes"]["account"]
        assert len(account["linkTypes"]) > 0
