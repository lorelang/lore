"""Tests for the Lore parser."""
import pytest
from pathlib import Path
from lore.parser import (
    parse_ontology, _split_frontmatter, _split_sections,
    _parse_attributes, _extract_tags, _parse_list_items,
)
from lore.models import Ontology


# --- Utility function tests ---

class TestSplitFrontmatter:
    def test_with_frontmatter(self):
        text = "---\nentity: Foo\n---\n## Attributes\nname: string"
        fm, body = _split_frontmatter(text)
        assert fm == {"entity": "Foo"}
        assert "## Attributes" in body

    def test_without_frontmatter(self):
        text = "Just some body text"
        fm, body = _split_frontmatter(text)
        assert fm == {}
        assert body == "Just some body text"

    def test_empty_frontmatter(self):
        text = "---\n---\nBody content"
        fm, body = _split_frontmatter(text)
        assert fm == {}
        assert body == "Body content"

    def test_multiline_frontmatter(self):
        text = "---\nentity: Bar\ndescription: >\n  Some long\n  description\n---\nBody"
        fm, body = _split_frontmatter(text)
        assert fm["entity"] == "Bar"
        assert "long" in fm["description"]
        assert body == "Body"


class TestSplitSections:
    def test_basic_sections(self):
        body = "Preamble text\n\n## Attributes\nattr content\n\n## Notes\nnote content"
        sections = _split_sections(body)
        assert "__preamble__" in sections
        assert "Attributes" in sections
        assert "Notes" in sections
        assert "attr content" in sections["Attributes"]
        assert "note content" in sections["Notes"]

    def test_no_sections(self):
        body = "Just plain text with no headings"
        sections = _split_sections(body)
        assert "__preamble__" in sections
        assert len(sections) == 1

    def test_empty_body(self):
        sections = _split_sections("")
        assert sections.get("__preamble__", "") == ""


class TestParseAttributes:
    def test_simple_attribute(self):
        text = "name: string [required, unique]"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert attrs[0].name == "name"
        assert attrs[0].type == "string"
        assert "required" in attrs[0].constraints
        assert "unique" in attrs[0].constraints

    def test_no_constraints(self):
        text = "industry: string"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert attrs[0].name == "industry"
        assert attrs[0].type == "string"
        assert attrs[0].constraints == []

    def test_reference_type(self):
        text = "csm_owner: -> Contact"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert attrs[0].type == "reference"
        assert attrs[0].reference_to == "Contact"

    def test_list_reference_type(self):
        text = "participants: list<-> Contact"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert attrs[0].type == "list<reference>"
        assert attrs[0].reference_to == "Contact"

    def test_enum_type(self):
        text = "stage: enum [prospect, active, churned]"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert attrs[0].type == "enum"
        assert attrs[0].enum_values == ["prospect", "active", "churned"]

    def test_description_lines(self):
        text = "name: string [required]\n  | Legal entity name.\n  | Used for display."
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert "Legal entity name." in attrs[0].description

    def test_annotation(self):
        text = "score: float\n  | Some score.\n  | @computed: rules/scoring.lore#test"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert "computed" in attrs[0].annotations

    def test_multiple_attributes(self):
        text = "name: string [required]\nage: int\nemail: string [unique]"
        attrs = _parse_attributes(text)
        assert len(attrs) == 3
        assert attrs[0].name == "name"
        assert attrs[1].name == "age"
        assert attrs[2].name == "email"

    def test_float_range_constraint(self):
        text = "health_score: float [0.0 .. 100.0]"
        attrs = _parse_attributes(text)
        assert len(attrs) == 1
        assert attrs[0].name == "health_score"
        assert attrs[0].type == "float"


class TestExtractTags:
    def test_single_tag(self):
        name, tags = _extract_tags("Usage Spike @tag: product-led")
        assert name == "Usage Spike"
        assert tags == ["product-led"]

    def test_no_tags(self):
        name, tags = _extract_tags("Usage Spike")
        assert name == "Usage Spike"
        assert tags == []

    def test_multiple_tags(self):
        name, tags = _extract_tags("Foo @tag: a @tag: b")
        assert name == "Foo"
        assert "a" in tags
        assert "b" in tags


class TestParseListItems:
    def test_basic_list(self):
        text = "- Item one\n- Item two\n- Item three"
        items = _parse_list_items(text)
        assert items == ["Item one", "Item two", "Item three"]

    def test_empty_text(self):
        assert _parse_list_items("") == []

    def test_non_list_text(self):
        assert _parse_list_items("No list items here") == []


# --- Entity parsing ---

class TestParseEntity:
    def test_full_entity(self, example_ontology):
        account = next(e for e in example_ontology.entities if e.name == "Account")
        assert account.description
        assert len(account.attributes) >= 10
        assert account.identity
        assert account.lifecycle
        assert account.notes

    def test_entity_attributes_types(self, example_ontology):
        account = next(e for e in example_ontology.entities if e.name == "Account")
        name_attr = next(a for a in account.attributes if a.name == "name")
        assert name_attr.type == "string"
        assert "required" in name_attr.constraints
        assert "unique" in name_attr.constraints

    def test_entity_reference_attribute(self, example_ontology):
        account = next(e for e in example_ontology.entities if e.name == "Account")
        csm = next(a for a in account.attributes if a.name == "csm_owner")
        assert csm.type == "reference"
        assert csm.reference_to == "Contact"

    def test_entity_enum_attribute(self, example_ontology):
        account = next(e for e in example_ontology.entities if e.name == "Account")
        segment = next(a for a in account.attributes if a.name == "segment")
        assert "enum" in segment.type

    def test_entity_computed_annotation(self, example_ontology):
        account = next(e for e in example_ontology.entities if e.name == "Account")
        health = next(a for a in account.attributes if a.name == "health_score")
        assert "computed" in health.annotations

    def test_minimal_entity(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"thing.lore": "---\nentity: Thing\n---\n## Attributes\nid: string [required]"},
        )
        assert len(ont.entities) == 1
        assert ont.entities[0].name == "Thing"
        assert len(ont.entities[0].attributes) == 1


# --- Relationship parsing ---

class TestParseRelationships:
    def test_relationship_count(self, example_ontology):
        assert len(example_ontology.all_relationships) == 18

    def test_relationship_fields(self, example_ontology):
        has_sub = next(r for r in example_ontology.all_relationships if r.name == "HAS_SUBSCRIPTION")
        assert has_sub.from_entity == "Account"
        assert has_sub.to_entity == "Subscription"
        assert has_sub.cardinality == "one-to-many"

    def test_relationship_with_properties(self, example_ontology):
        owns = next(r for r in example_ontology.all_relationships if r.name == "OWNS")
        assert len(owns.properties) >= 1

    def test_relationship_property_description(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={
                "a.lore": "---\nentity: A\n---\n## Attributes\nid: string",
                "b.lore": "---\nentity: B\n---\n## Attributes\nid: string",
            },
            relationships={"rels.lore": """---
domain: Core
---
## LINKS
  from: A -> to: B
  cardinality: one-to-many
  properties:
    since: date
      | Date when link became active.
"""}
        )
        rel = ont.all_relationships[0]
        assert rel.properties[0].name == "since"
        assert "link became active" in rel.properties[0].description

    def test_traversal_count(self, example_ontology):
        assert len(example_ontology.all_traversals) >= 7

    def test_traversal_fields(self, example_ontology):
        rev = next(t for t in example_ontology.all_traversals if t.name == "revenue-by-product")
        assert "Account" in rev.path
        assert "Subscription" in rev.path
        assert "Product" in rev.path

    def test_relationship_file_metadata(self, example_ontology):
        commercial = next(rf for rf in example_ontology.relationship_files if rf.domain == "Commercial")
        assert commercial.description
        assert len(commercial.relationships) == 6
        assert len(commercial.traversals) == 4


# --- Rule parsing ---

class TestParseRules:
    def test_rule_count(self, example_ontology):
        assert len(example_ontology.all_rules) == 16

    def test_rule_with_condition_action(self, example_ontology):
        champion = next(r for r in example_ontology.all_rules if r.name == "champion-departure-alert")
        assert champion.applies_to == "Account"
        assert champion.severity == "critical"
        assert champion.trigger
        assert champion.condition
        assert champion.action

    def test_rule_with_prose(self, example_ontology):
        champion = next(r for r in example_ontology.all_rules if r.name == "champion-departure-alert")
        assert champion.prose
        assert "churn predictor" in champion.prose.lower() or "champion" in champion.prose.lower()

    def test_scoring_rule_with_outputs(self, example_ontology):
        health = next(r for r in example_ontology.all_rules if r.name == "account-health-score")
        assert health.outputs or health.applies_to

    def test_rule_file_metadata(self, example_ontology):
        churn = next(rf for rf in example_ontology.rule_files if rf.domain == "Churn Risk")
        assert churn.description
        assert len(churn.rules) == 4


# --- Taxonomy parsing ---

class TestParseTaxonomy:
    def test_taxonomy_metadata(self, example_ontology):
        assert len(example_ontology.taxonomies) == 2
        signal_tax = next(t for t in example_ontology.taxonomies if t.name == "SignalType")
        assert signal_tax.applied_to == "Signal.type"
        product_tax = next(t for t in example_ontology.taxonomies if t.name == "ProductCatalog")
        assert product_tax.applied_to == "Product.category"

    def test_taxonomy_tree_structure(self, example_ontology):
        tax = next(t for t in example_ontology.taxonomies if t.name == "SignalType")
        assert tax.root is not None
        assert tax.root.name == "Signal"
        assert len(tax.root.children) >= 3  # Expansion, Contraction, Neutral

    def test_taxonomy_leaf_nodes(self, example_ontology):
        tax = next(t for t in example_ontology.taxonomies if t.name == "SignalType")
        expansion = next(c for c in tax.root.children if "Expansion" in c.name)
        assert len(expansion.children) >= 5

    def test_taxonomy_tags(self, example_ontology):
        tax = next(t for t in example_ontology.taxonomies if t.name == "SignalType")
        expansion = next(c for c in tax.root.children if "Expansion" in c.name)
        assert "expansion" in expansion.tags

    def test_taxonomy_inheritance_rules(self, example_ontology):
        tax = next(t for t in example_ontology.taxonomies if t.name == "SignalType")
        assert tax.inheritance_rules
        assert "product-led" in tax.inheritance_rules

    def test_product_catalog_taxonomy(self, example_ontology):
        tax = next(t for t in example_ontology.taxonomies if t.name == "ProductCatalog")
        assert tax.root is not None
        assert tax.inheritance_rules
        assert "entry-tier" in tax.inheritance_rules


# --- Glossary parsing ---

class TestParseGlossary:
    def test_glossary_entries(self, example_ontology):
        assert example_ontology.glossary is not None
        entries = example_ontology.all_glossary_entries
        assert len(entries) >= 20

    def test_glossary_entry_content(self, example_ontology):
        arr = next(e for e in example_ontology.all_glossary_entries if "ARR" in e.term)
        assert "recurring revenue" in arr.definition.lower()

    def test_merges_multiple_glossary_files(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            glossary={
                "a.lore": "---\ndescription: A terms\n---\n## Alpha\nFirst",
                "b.lore": "---\ndescription: B terms\n---\n## Beta\nSecond",
            },
        )
        assert ont.glossary is not None
        terms = {e.term for e in ont.all_glossary_entries}
        assert terms == {"Alpha", "Beta"}
        assert "A terms" in ont.glossary.description
        assert "B terms" in ont.glossary.description


# --- View parsing ---

class TestParseView:
    def test_view_count(self, example_ontology):
        assert len(example_ontology.views) == 3

    def test_view_metadata(self, example_ontology):
        ae = next(v for v in example_ontology.views if v.name == "Account Executive")
        assert ae.audience
        assert ae.description

    def test_view_entities(self, example_ontology):
        ae = next(v for v in example_ontology.views if v.name == "Account Executive")
        assert len(ae.entities) >= 3

    def test_view_key_questions(self, example_ontology):
        ae = next(v for v in example_ontology.views if v.name == "Account Executive")
        assert len(ae.key_questions) >= 3

    def test_view_not_in_scope(self, example_ontology):
        ae = next(v for v in example_ontology.views if v.name == "Account Executive")
        assert ae.not_in_scope


# --- Manifest parsing ---

class TestParseManifest:
    def test_manifest_fields(self, example_ontology):
        m = example_ontology.manifest
        assert m is not None
        assert m.name == "b2b-saas-gtm"
        assert m.version == "0.2.0"
        assert m.domain == "B2B SaaS Revenue Operations"
        assert len(m.maintainers) >= 1
        assert m.evolution is not None
        assert m.evolution.proposals == "open"
        assert m.evolution.staleness == "90d"

    def test_missing_manifest(self, tmp_ontology):
        ont = tmp_ontology(
            entities={"thing.lore": "---\nentity: Thing\n---\n## Attributes\nid: string"},
        )
        assert ont.manifest is None


# --- Full ontology integration ---

class TestParseOntology:
    def test_full_parse(self, example_ontology):
        assert len(example_ontology.entities) == 11
        assert len(example_ontology.relationship_files) == 3
        assert len(example_ontology.rule_files) == 3
        assert len(example_ontology.taxonomies) == 2
        assert example_ontology.glossary is not None
        assert len(example_ontology.views) == 3

    def test_entity_names_property(self, example_ontology):
        names = example_ontology.entity_names
        assert "Account" in names
        assert "Contact" in names
        assert "Subscription" in names
        assert "Feature" in names
        assert "Competitor" in names
        assert "Play" in names
        assert len(names) == 11

    def test_empty_directory(self, tmp_path):
        (tmp_path / "lore.yaml").write_text("name: empty\nversion: 0.1.0")
        ont = parse_ontology(tmp_path)
        assert ont.manifest.name == "empty"
        assert len(ont.entities) == 0

    def test_sorted_file_loading(self, tmp_ontology):
        """Files should be loaded in sorted order."""
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={
                "z_entity.lore": "---\nentity: Zeta\n---\n## Attributes\nid: string",
                "a_entity.lore": "---\nentity: Alpha\n---\n## Attributes\nid: string",
            },
        )
        assert ont.entities[0].name == "Alpha"
        assert ont.entities[1].name == "Zeta"
