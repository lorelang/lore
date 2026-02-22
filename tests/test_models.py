"""Tests for Lore data models."""
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, RelationshipProperty, Traversal, Rule, RuleFile,
    Taxonomy, TaxonomyNode, Glossary, GlossaryEntry, View, FileType,
)


class TestFileType:
    def test_enum_values(self):
        assert FileType.ENTITY.value == "entity"
        assert FileType.RELATIONSHIP.value == "relationship"
        assert FileType.RULE.value == "rule"
        assert FileType.TAXONOMY.value == "taxonomy"
        assert FileType.GLOSSARY.value == "glossary"
        assert FileType.VIEW.value == "view"


class TestAttribute:
    def test_defaults(self):
        attr = Attribute(name="test", type="string")
        assert attr.constraints == []
        assert attr.description == ""
        assert attr.annotations == {}
        assert attr.reference_to is None

    def test_full_attribute(self):
        attr = Attribute(
            name="score",
            type="float",
            constraints=["required"],
            description="A score",
            annotations={"computed": "rules/scoring.lore"},
            reference_to=None,
        )
        assert attr.name == "score"
        assert attr.type == "float"


class TestEntity:
    def test_defaults(self):
        e = Entity(name="Test")
        assert e.description == ""
        assert e.inherits is None
        assert e.attributes == []
        assert e.identity == ""
        assert e.lifecycle == ""
        assert e.notes == ""
        assert e.source_file is None


class TestRelationship:
    def test_basic(self):
        r = Relationship(name="HAS", from_entity="A", to_entity="B")
        assert r.cardinality == ""
        assert r.properties == []


class TestOntologyProperties:
    def test_all_relationships(self):
        ont = Ontology(
            relationship_files=[
                RelationshipFile(domain="A", relationships=[
                    Relationship(name="R1", from_entity="X", to_entity="Y"),
                ]),
                RelationshipFile(domain="B", relationships=[
                    Relationship(name="R2", from_entity="Y", to_entity="Z"),
                ]),
            ]
        )
        assert len(ont.all_relationships) == 2
        assert ont.all_relationships[0].name == "R1"
        assert ont.all_relationships[1].name == "R2"

    def test_all_traversals(self):
        ont = Ontology(
            relationship_files=[
                RelationshipFile(domain="A", traversals=[
                    Traversal(name="t1", path="A -> B"),
                    Traversal(name="t2", path="B -> C"),
                ]),
            ]
        )
        assert len(ont.all_traversals) == 2

    def test_all_rules(self):
        ont = Ontology(
            rule_files=[
                RuleFile(domain="A", rules=[Rule(name="r1"), Rule(name="r2")]),
                RuleFile(domain="B", rules=[Rule(name="r3")]),
            ]
        )
        assert len(ont.all_rules) == 3

    def test_entity_names(self):
        ont = Ontology(
            entities=[Entity(name="Foo"), Entity(name="Bar")]
        )
        assert ont.entity_names == {"Foo", "Bar"}

    def test_all_glossary_entries_with_glossary(self):
        ont = Ontology(
            glossary=Glossary(entries=[
                GlossaryEntry(term="A", definition="def A"),
                GlossaryEntry(term="B", definition="def B"),
            ])
        )
        assert len(ont.all_glossary_entries) == 2

    def test_all_glossary_entries_no_glossary(self):
        ont = Ontology()
        assert ont.all_glossary_entries == []

    def test_empty_ontology(self):
        ont = Ontology()
        assert ont.manifest is None
        assert ont.entities == []
        assert ont.all_relationships == []
        assert ont.all_rules == []
        assert ont.entity_names == set()


class TestTaxonomyNode:
    def test_leaf_node(self):
        node = TaxonomyNode(name="Leaf")
        assert node.children == []
        assert node.tags == []

    def test_tree_structure(self):
        root = TaxonomyNode(
            name="Root",
            children=[
                TaxonomyNode(name="A", children=[
                    TaxonomyNode(name="A1"),
                    TaxonomyNode(name="A2"),
                ]),
                TaxonomyNode(name="B"),
            ],
        )
        assert len(root.children) == 2
        assert len(root.children[0].children) == 2
