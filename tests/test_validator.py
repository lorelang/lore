"""Tests for the Lore validator."""
import pytest
from lore.validator import validate, Severity, Diagnostic
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Traversal, Rule, RuleFile, Taxonomy, TaxonomyNode,
    Glossary, GlossaryEntry, View,
)


def _make_ontology(**kwargs):
    """Helper to build minimal ontology for testing."""
    return Ontology(**kwargs)


def _errors(diags):
    return [d for d in diags if d.severity == Severity.ERROR]

def _warnings(diags):
    return [d for d in diags if d.severity == Severity.WARNING]

def _infos(diags):
    return [d for d in diags if d.severity == Severity.INFO]


class TestManifestValidation:
    def test_missing_manifest(self):
        ont = _make_ontology()
        diags = validate(ont)
        assert any("No lore.yaml" in d.message for d in _warnings(diags))

    def test_manifest_missing_name(self):
        ont = _make_ontology(manifest=OntologyManifest(name=""))
        diags = validate(ont)
        assert any("missing 'name'" in d.message for d in _errors(diags))

    def test_manifest_missing_version(self):
        ont = _make_ontology(manifest=OntologyManifest(name="test"))
        diags = validate(ont)
        assert any("missing 'version'" in d.message for d in _warnings(diags))

    def test_valid_manifest(self):
        ont = _make_ontology(manifest=OntologyManifest(name="test", version="1.0"))
        diags = validate(ont)
        manifest_errors = [d for d in _errors(diags) if "manifest" in d.message.lower() or "lore.yaml" in d.source]
        assert len(manifest_errors) == 0


class TestEntityValidation:
    def test_duplicate_entities(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Foo", attributes=[Attribute(name="id", type="string")]),
                Entity(name="Foo", attributes=[Attribute(name="id", type="string")]),
            ]
        )
        diags = validate(ont)
        assert any("Duplicate entity: Foo" in d.message for d in _errors(diags))

    def test_entity_no_attributes(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Empty")]
        )
        diags = validate(ont)
        assert any("no attributes" in d.message for d in _warnings(diags))

    def test_entity_no_identity(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Foo", attributes=[Attribute(name="id", type="string")])]
        )
        diags = validate(ont)
        assert any("no Identity section" in d.message for d in _infos(diags))

    def test_entity_unknown_reference(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Foo",
                attributes=[Attribute(name="owner", type="reference", reference_to="NonExistent")],
            )]
        )
        diags = validate(ont)
        assert any("unknown entity 'NonExistent'" in d.message for d in _warnings(diags))

    def test_entity_valid_reference(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Foo", attributes=[
                    Attribute(name="bar_ref", type="reference", reference_to="Bar"),
                ]),
                Entity(name="Bar", attributes=[
                    Attribute(name="id", type="string"),
                ]),
            ]
        )
        diags = validate(ont)
        ref_warnings = [d for d in _warnings(diags) if "unknown entity" in d.message]
        assert len(ref_warnings) == 0

    def test_entity_unknown_inheritance(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Foo",
                inherits="BaseEntity",
                attributes=[Attribute(name="id", type="string")],
            )]
        )
        diags = validate(ont)
        assert any("inherits from 'BaseEntity'" in d.message for d in _infos(diags))


class TestRelationshipValidation:
    def test_unknown_from_entity(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Bar", attributes=[Attribute(name="id", type="string")])],
            relationship_files=[RelationshipFile(
                domain="test",
                relationships=[Relationship(
                    name="TEST_REL",
                    from_entity="Unknown",
                    to_entity="Bar",
                    cardinality="one-to-many",
                )],
            )],
        )
        diags = validate(ont)
        assert any("unknown entity 'Unknown'" in d.message for d in _errors(diags))

    def test_unknown_to_entity(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Foo", attributes=[Attribute(name="id", type="string")])],
            relationship_files=[RelationshipFile(
                domain="test",
                relationships=[Relationship(
                    name="TEST_REL",
                    from_entity="Foo",
                    to_entity="Unknown",
                    cardinality="one-to-many",
                )],
            )],
        )
        diags = validate(ont)
        assert any("unknown entity 'Unknown'" in d.message for d in _errors(diags))

    def test_unknown_cardinality_warning(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Foo", attributes=[Attribute(name="id", type="string")]),
                Entity(name="Bar", attributes=[Attribute(name="id", type="string")]),
            ],
            relationship_files=[RelationshipFile(
                domain="test",
                relationships=[Relationship(
                    name="TEST_REL",
                    from_entity="Foo",
                    to_entity="Bar",
                    cardinality="zero-to-many",
                )],
            )],
        )
        diags = validate(ont)
        assert any("unknown cardinality" in d.message for d in _warnings(diags))


class TestRuleValidation:
    def test_duplicate_rules(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Foo", attributes=[Attribute(name="id", type="string")])],
            rule_files=[RuleFile(
                domain="test",
                rules=[
                    Rule(name="my-rule", applies_to="Foo"),
                    Rule(name="my-rule", applies_to="Foo"),
                ],
            )],
        )
        diags = validate(ont)
        assert any("Duplicate rule" in d.message for d in _errors(diags))

    def test_rule_unknown_applies_to(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Foo", attributes=[Attribute(name="id", type="string")])],
            rule_files=[RuleFile(
                domain="test",
                rules=[Rule(name="my-rule", applies_to="NonExistent")],
            )],
        )
        diags = validate(ont)
        assert any("unknown entity 'NonExistent'" in d.message for d in _warnings(diags))

    def test_rule_no_applies_to(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            rule_files=[RuleFile(domain="test", rules=[Rule(name="my-rule")])],
        )
        diags = validate(ont)
        assert any("no applies_to" in d.message for d in _infos(diags))

    def test_rule_unknown_severity(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Foo", attributes=[Attribute(name="id", type="string")])],
            rule_files=[RuleFile(
                domain="test",
                rules=[Rule(name="my-rule", applies_to="Foo", severity="urgent")],
            )],
        )
        diags = validate(ont)
        assert any("unknown severity" in d.message for d in _warnings(diags))


class TestTaxonomyValidation:
    def test_empty_taxonomy(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            taxonomies=[Taxonomy(name="Empty")],
        )
        diags = validate(ont)
        assert any("no tree structure" in d.message for d in _warnings(diags))

    def test_single_node_taxonomy(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            taxonomies=[Taxonomy(name="Small", root=TaxonomyNode(name="Root"))],
        )
        diags = validate(ont)
        assert any("only 1 node" in d.message for d in _warnings(diags))

    def test_taxonomy_unknown_entity(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            taxonomies=[Taxonomy(
                name="Types",
                applied_to="NonExistent.type",
                root=TaxonomyNode(name="Root", children=[TaxonomyNode(name="Child")]),
            )],
        )
        diags = validate(ont)
        assert any("unknown entity 'NonExistent'" in d.message for d in _warnings(diags))

    def test_taxonomy_unknown_attribute(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
            taxonomies=[Taxonomy(
                name="Types",
                applied_to="Account.category",
                root=TaxonomyNode(name="Root", children=[TaxonomyNode(name="Child")]),
            )],
        )
        diags = validate(ont)
        assert any("unknown attribute" in d.message for d in _warnings(diags))


class TestViewValidation:
    def test_view_no_entities(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            views=[View(name="Empty View")],
        )
        diags = validate(ont)
        assert any("lists no entities" in d.message for d in _warnings(diags))

    def test_view_no_key_questions(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            views=[View(name="Test View", entities=["Foo"])],
        )
        diags = validate(ont)
        assert any("no Key Questions" in d.message for d in _infos(diags))

    def test_view_unknown_references(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
            views=[View(
                name="Bad View",
                entities=["UnknownEntity"],
                relationships=["NO_REL"],
                rules=["NO_RULE"],
                key_questions=["Q?"],
            )],
        )
        diags = validate(ont)
        warnings = _warnings(diags)
        assert any("unknown entity" in d.message for d in warnings)
        assert any("unknown relationship/traversal" in d.message for d in warnings)
        assert any("unknown rule" in d.message for d in warnings)

    def test_view_prose_placeholders(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Account", attributes=[Attribute(name="id", type="string")]),
                Entity(name="Contact", attributes=[Attribute(name="id", type="string")]),
            ],
            relationship_files=[
                RelationshipFile(
                    domain="Commercial",
                    relationships=[Relationship(name="HAS_CONTACT", from_entity="Account", to_entity="Contact")],
                    traversals=[Traversal(name="account-contact", path="Account -[HAS_CONTACT]-> Contact")],
                )
            ],
            rule_files=[
                RuleFile(
                    domain="Scoring",
                    rules=[Rule(name="account-score", applies_to="Account")],
                )
            ],
            views=[View(
                name="Prose",
                entities=["All entities with all attributes"],
                relationships=["All commercial relationships", "All traversals"],
                rules=["All scoring rules"],
                key_questions=["Q?"],
            )],
        )
        warnings = _warnings(validate(ont))
        assert not any("unknown entity" in d.message for d in warnings)
        assert not any("unknown relationship/traversal" in d.message for d in warnings)
        assert not any("unknown rule" in d.message for d in warnings)


class TestGlossaryValidation:
    def test_no_glossary(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
        )
        diags = validate(ont)
        assert any("No glossary defined" in d.message for d in _infos(diags))

    def test_empty_glossary(self):
        ont = _make_ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            glossary=Glossary(),
        )
        diags = validate(ont)
        assert any("Glossary is empty" in d.message for d in _warnings(diags))


class TestDiagnosticFormatting:
    def test_error_str(self):
        d = Diagnostic(Severity.ERROR, "Bad thing", "file.lore")
        s = str(d)
        assert "✗" in s
        assert "Bad thing" in s
        assert "file.lore" in s

    def test_warning_str(self):
        d = Diagnostic(Severity.WARNING, "Meh thing")
        s = str(d)
        assert "⚠" in s

    def test_info_str(self):
        d = Diagnostic(Severity.INFO, "FYI")
        s = str(d)
        assert "ℹ" in s


class TestFullExampleValidation:
    def test_example_has_no_errors(self, example_ontology):
        """The B2B SaaS GTM example should have no errors."""
        diags = validate(example_ontology)
        errors = _errors(diags)
        assert len(errors) == 0, f"Unexpected errors: {[str(d) for d in errors]}"
