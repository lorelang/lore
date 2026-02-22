"""Tests for the lore evolve command (Phase 4)."""
import pytest
from pathlib import Path
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute,
    Rule, RuleFile, Outcome, OutcomeFile, EvolutionConfig,
)
from lore.evolution import evolve, _group_takeaways, _slugify, _compute_confidence


class TestEvolveBasic:
    def test_no_outcomes_returns_empty(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
        )
        proposals = evolve(ont, tmp_path / "proposals")
        assert proposals == []

    def test_no_takeaways_returns_empty(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(heading="Just a note", prose="No lessons.")],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        assert proposals == []

    def test_single_takeaway_generates_proposal(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Q2 Retro",
                date="2025-07-01",
                outcomes=[Outcome(
                    heading="Something happened",
                    prose="Details here.",
                    takeaways=["improve the process"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        assert len(proposals) >= 1
        # Should be in general bucket since no entities/rules match
        assert any(p["kind"] == "general" for p in proposals)

    def test_proposal_file_is_written(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="Result",
                    prose="Details.",
                    takeaways=["do something better"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        assert len(proposals) >= 1
        for p in proposals:
            assert Path(p["path"]).exists()
            content = Path(p["path"]).read_text()
            assert "proposal:" in content
            assert "status: proposed" in content
            assert "source: derived" in content

    def test_creates_output_dir(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(heading="R", prose=".", takeaways=["fix it"])],
            )],
        )
        out = tmp_path / "deep" / "nested" / "proposals"
        proposals = evolve(ont, out)
        assert out.exists()

    def test_evolution_closed_generates_no_proposals(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(
                name="test",
                version="1.0",
                evolution=EvolutionConfig(proposals="closed"),
            ),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(heading="R", prose=".", takeaways=["fix it"])],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        assert proposals == []

    def test_evolution_review_required_marks_proposals(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(
                name="test",
                version="1.0",
                evolution=EvolutionConfig(proposals="review-required"),
            ),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(heading="R", prose=".", takeaways=["fix it"])],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        assert len(proposals) >= 1
        content = Path(proposals[0]["path"]).read_text()
        assert "review_required: true" in content


class TestEvolveGrouping:
    def test_takeaway_mentioning_rule_groups_by_rule(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
            rule_files=[RuleFile(
                domain="test",
                rules=[Rule(name="usage-decline-alert", applies_to="Account")],
            )],
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="False positive",
                    prose="Details.",
                    takeaways=["the usage-decline-alert rule needs seasonal adjustment"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        rule_proposals = [p for p in proposals if p["kind"] == "rule-adjustment"]
        assert len(rule_proposals) >= 1
        assert "usage-decline-alert" in rule_proposals[0]["name"]

    def test_takeaway_mentioning_entity_groups_by_entity(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="Account insight",
                    prose="Details.",
                    takeaways=["Account entity needs a new segment field"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        entity_proposals = [p for p in proposals if p["kind"] == "entity-observation"]
        assert len(entity_proposals) >= 1
        assert "Account" in entity_proposals[0]["name"]

    def test_multiple_takeaways_for_same_rule(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            rule_files=[RuleFile(
                domain="test",
                rules=[Rule(name="churn-risk", applies_to="Account")],
            )],
            outcome_files=[OutcomeFile(
                name="Q1",
                outcomes=[
                    Outcome(heading="O1", prose=".", takeaways=["churn-risk rule is too aggressive"]),
                    Outcome(heading="O2", prose=".", takeaways=["churn-risk needs lower threshold"]),
                    Outcome(heading="O3", prose=".", takeaways=["churn-risk false positive again"]),
                ],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        rule_proposals = [p for p in proposals if p["kind"] == "rule-adjustment"]
        assert len(rule_proposals) >= 1
        # All 3 takeaways should be in the same proposal
        assert len(rule_proposals[0]["takeaways"]) == 3

    def test_unmatched_takeaways_go_to_general(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="Random",
                    prose=".",
                    takeaways=["something unrelated to anything"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        general = [p for p in proposals if p["kind"] == "general"]
        assert len(general) == 1


class TestGroupTakeaways:
    def test_groups_by_rule_name(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            rule_files=[RuleFile(domain="t", rules=[Rule(name="my-rule")])],
        )
        entries = [{"takeaway": "my-rule needs fixing", "outcome_heading": "O1", "outcome_file": "f", "refs": [], "date": ""}]
        groups = _group_takeaways(entries, ont)
        assert "rule:my-rule" in groups

    def test_groups_by_entity_name(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Widget", attributes=[Attribute(name="id", type="string")])],
        )
        entries = [{"takeaway": "Widget needs more attributes", "outcome_heading": "O1", "outcome_file": "f", "refs": [], "date": ""}]
        groups = _group_takeaways(entries, ont)
        assert "entity:Widget" in groups

    def test_unmatched_goes_to_general(self):
        ont = Ontology(manifest=OntologyManifest(name="test", version="1.0"))
        entries = [{"takeaway": "random thing", "outcome_heading": "O1", "outcome_file": "f", "refs": [], "date": ""}]
        groups = _group_takeaways(entries, ont)
        assert "general" in groups


class TestHelpers:
    def test_slugify(self):
        assert _slugify("Adjust rule: usage-decline-alert") == "adjust-rule-usage-decline-alert"
        assert _slugify("Review entity: Account") == "review-entity-account"
        assert _slugify("hello world") == "hello-world"

    def test_compute_confidence_single(self):
        assert _compute_confidence([{"takeaway": "a"}]) == 0.5

    def test_compute_confidence_double(self):
        assert _compute_confidence([{"takeaway": "a"}, {"takeaway": "b"}]) == 0.65

    def test_compute_confidence_triple_plus(self):
        entries = [{"takeaway": "a"}, {"takeaway": "b"}, {"takeaway": "c"}]
        assert _compute_confidence(entries) == 0.8


class TestProposalFileContent:
    def test_proposal_has_expected_sections(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="Outcome 1",
                    prose="Details.",
                    takeaways=["lesson learned here"],
                    refs=["observations/q1.lore#something"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        content = Path(proposals[0]["path"]).read_text()
        assert "## Summary" in content
        assert "## Takeaways" in content
        assert "- lesson learned here" in content
        assert "## Source Outcomes" in content
        assert "- Outcome 1" in content
        assert "## References" in content
        assert "- observations/q1.lore#something" in content

    def test_proposal_without_refs_has_no_references_section(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="O1",
                    prose=".",
                    takeaways=["do better"],
                )],
            )],
        )
        proposals = evolve(ont, tmp_path / "proposals")
        content = Path(proposals[0]["path"]).read_text()
        assert "## References" not in content


class TestEvolveEndToEnd:
    def test_full_ontology_with_outcomes(self, tmp_ontology, tmp_path):
        """Parse a full ontology with outcomes and run evolve."""
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={
                "account.lore": "---\nentity: Account\n---\n## Attributes\nid: string\nname: string",
            },
            rules={"alerts.lore": """---
domain: Alerts
---
## usage-decline-alert
  applies_to: Account
  severity: warning
  condition: usage_change < -20%
  action: flag for CSM review
"""},
            outcomes={"q2.lore": """---
outcomes: Q2 Retro
reviewed_by: agent
date: 2025-07-01
---

## False positive on Beta Corp

The usage-decline-alert fired but was seasonal.

Takeaway: usage-decline-alert rule needs seasonal adjustment
Takeaway: Account entity should track industry vertical for seasonal patterns

## Acme expansion correct

Prediction was right.

Takeaway: increase weight of executive signals
"""},
        )
        proposals_dir = tmp_path / "evolve_output"
        proposals = evolve(ont, proposals_dir)

        # Should have at least a rule proposal and possibly entity/general proposals
        assert len(proposals) >= 1

        # Verify rule-adjustment proposal exists
        rule_proposals = [p for p in proposals if p["kind"] == "rule-adjustment"]
        assert len(rule_proposals) >= 1

        # Verify files exist
        for p in proposals:
            assert Path(p["path"]).exists()
