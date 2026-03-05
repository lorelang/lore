"""Tests for the AGENTS.md compiler."""
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Glossary, GlossaryEntry, View,
)
from lore.compilers.agents_md import compile_agents_md


@pytest.fixture
def agents_md_ontology():
    return Ontology(
        manifest=OntologyManifest(
            name="test-domain",
            version="1.0",
            description="A test domain for AGENTS.md.",
        ),
        entities=[
            Entity(
                name="Widget",
                description="A test widget.",
                attributes=[
                    Attribute(name="id", type="string", constraints=["required"]),
                    Attribute(name="status", type="enum",
                              enum_values=["active", "inactive"]),
                ],
                notes="Widgets are the core unit.",
            ),
            Entity(
                name="Person",
                description="A person.",
                attributes=[
                    Attribute(name="name", type="string", constraints=["required"]),
                ],
            ),
        ],
        relationship_files=[RelationshipFile(
            domain="Core",
            relationships=[
                Relationship(name="OWNS", from_entity="Person",
                             to_entity="Widget", cardinality="one-to-many",
                             description="A person owns widgets."),
            ],
        )],
        rule_files=[RuleFile(
            domain="Alerts",
            rules=[
                Rule(name="critical-alert", applies_to="Widget",
                     severity="critical",
                     action="Immediately escalate to support"),
                Rule(name="soft-warning", applies_to="Widget",
                     severity="warning",
                     action="Flag for review next cycle"),
                Rule(name="fyi-note", applies_to="Widget",
                     severity="info",
                     action="Log for reference"),
            ],
        )],
        glossary=Glossary(entries=[
            GlossaryEntry(term="Widget", definition="The fundamental unit."),
            GlossaryEntry(term="Owner", definition="The responsible person."),
        ]),
        views=[View(
            name="Admin",
            description="Admin view.",
            audience="Administrators",
            entities=["Widget", "Person"],
            relationships=["OWNS"],
            rules=["critical-alert"],
            key_questions=["How many widgets are inactive?"],
        )],
    )


class TestAgentsMdOutput:
    def test_has_frontmatter(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert result.startswith("---")
        assert "name: test-domain" in result

    def test_has_domain_knowledge(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "# Domain Knowledge" in result
        assert "## Widget" in result
        assert "## Person" in result

    def test_has_entity_attributes(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "`id`" in result
        assert "`status`" in result

    def test_has_glossary(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "## Glossary" in result
        assert "**Widget**" in result

    def test_has_rules(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "# Rules" in result

    def test_rules_use_must_should_may(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "**MUST**" in result
        assert "**SHOULD**" in result
        assert "**MAY**" in result

    def test_has_relationships(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "# Relationships" in result
        assert "**OWNS**" in result

    def test_entity_notes_included(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology)
        assert "Widgets are the core unit" in result


class TestAgentsMdViewScoping:
    def test_view_scopes_output(self, agents_md_ontology):
        full = compile_agents_md(agents_md_ontology)
        scoped = compile_agents_md(agents_md_ontology, view_name="Admin")
        # Scoped should have key questions
        assert "# Key Questions" in scoped
        assert "How many widgets are inactive?" in scoped

    def test_view_in_frontmatter(self, agents_md_ontology):
        result = compile_agents_md(agents_md_ontology, view_name="Admin")
        assert "scope: Admin" in result


class TestAgentsMdEmpty:
    def test_empty_ontology(self):
        ont = Ontology(manifest=OntologyManifest(name="empty", version="1.0"))
        result = compile_agents_md(ont)
        assert "---" in result
        assert "# Domain Knowledge" in result
