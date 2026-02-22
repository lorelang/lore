"""Tests for the Lore curator — opinionated health checks."""
from datetime import date
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Provenance, EvolutionConfig,
    ObservationFile, Observation, OutcomeFile, Outcome,
    Taxonomy, TaxonomyNode,
)
from lore.curator import (
    curate_staleness, curate_coverage, curate_consistency,
    curate_summarize, curate_all,
    _parse_staleness, _parse_date, _days_old,
)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_parse_staleness_days(self):
        td = _parse_staleness("90d")
        assert td is not None
        assert td.days == 90

    def test_parse_staleness_months(self):
        td = _parse_staleness("3m")
        assert td is not None
        assert td.days == 90

    def test_parse_staleness_empty(self):
        assert _parse_staleness("") is None
        assert _parse_staleness(None) is None

    def test_parse_staleness_invalid(self):
        assert _parse_staleness("abc") is None
        assert _parse_staleness("90x") is None

    def test_parse_date(self):
        d = _parse_date("2025-01-15")
        assert d == date(2025, 1, 15)

    def test_parse_date_empty(self):
        assert _parse_date("") is None
        assert _parse_date(None) is None

    def test_days_old(self):
        age = _days_old("2025-01-01", today=date(2025, 4, 1))
        assert age == 90


# ---------------------------------------------------------------------------
# Job 1: Staleness
# ---------------------------------------------------------------------------

class TestStaleness:
    def test_fresh_entity(self):
        """Entity created within the threshold is not flagged."""
        ont = Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="90d"),
            ),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(created="2025-03-01"),
            )],
        )
        report = curate_staleness(ont, today=date(2025, 4, 1))
        assert len(report.warnings) == 0

    def test_stale_entity(self):
        """Entity older than threshold is flagged."""
        ont = Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="90d"),
            ),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(created="2024-01-01"),
            )],
        )
        report = curate_staleness(ont, today=date(2025, 4, 1))
        assert len(report.warnings) == 1
        assert "Account" in report.warnings[0].message
        assert "days old" in report.warnings[0].message

    def test_no_provenance_is_info(self):
        """Entity with no provenance gets an info, not a warning."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
        )
        report = curate_staleness(ont, today=date(2025, 4, 1))
        assert len(report.warnings) == 0
        assert len(report.infos) == 1
        assert "no provenance" in report.infos[0].message

    def test_stale_observation(self):
        """Old observation file is flagged."""
        ont = Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="30d"),
            ),
            observation_files=[ObservationFile(
                name="Q2 Notes", date="2025-01-01",
                observed_by="agent",
                observations=[Observation(heading="Note", prose="text")],
            )],
        )
        report = curate_staleness(ont, today=date(2025, 4, 1))
        assert len(report.warnings) == 1
        assert "Q2 Notes" in report.warnings[0].message

    def test_default_threshold_when_no_evolution(self):
        """Falls back to 180d when no evolution config."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(created="2025-01-01"),
            )],
        )
        # 100 days old, default threshold is 180d -> should be fine
        report = curate_staleness(ont, today=date(2025, 4, 11))
        assert len(report.warnings) == 0

        # 200 days old -> should flag
        report = curate_staleness(ont, today=date(2025, 7, 20))
        assert len(report.warnings) == 1

    def test_stale_rule_file(self):
        """Old rule file is flagged."""
        ont = Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="60d"),
            ),
            rule_files=[RuleFile(
                domain="Churn",
                rules=[Rule(name="test-rule", applies_to="Account")],
                provenance=Provenance(created="2024-06-01"),
            )],
        )
        report = curate_staleness(ont, today=date(2025, 4, 1))
        assert len(report.warnings) == 1
        assert "Churn" in report.warnings[0].message

    def test_summary_format(self):
        """Report summary has counts."""
        ont = Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="90d"),
            ),
            entities=[
                Entity(name="Fresh", attributes=[], provenance=Provenance(created="2025-03-15")),
                Entity(name="Stale", attributes=[], provenance=Provenance(created="2024-01-01")),
                Entity(name="Unknown", attributes=[]),
            ],
        )
        report = curate_staleness(ont, today=date(2025, 4, 1))
        assert "1 stale" in report.summary
        assert "1 undated" in report.summary
        assert "1 fresh" in report.summary


# ---------------------------------------------------------------------------
# Job 2: Coverage
# ---------------------------------------------------------------------------

class TestCoverage:
    def test_entity_missing_notes(self):
        """Entity without Notes section is a warning."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
        )
        report = curate_coverage(ont)
        warnings = [f for f in report.warnings if "Notes" in f.message]
        assert len(warnings) == 1
        assert "Account" in warnings[0].message

    def test_entity_with_notes_ok(self):
        """Entity with Notes section is not flagged for missing Notes."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="id", type="string")],
                notes="This is important context.",
            )],
        )
        report = curate_coverage(ont)
        notes_warnings = [f for f in report.warnings if "Notes" in f.message]
        assert len(notes_warnings) == 0

    def test_entity_missing_identity_is_info(self):
        """Entity without Identity section is an info."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
        )
        report = curate_coverage(ont)
        identity_infos = [f for f in report.infos if "Identity" in f.message]
        assert len(identity_infos) == 1

    def test_orphaned_entity(self):
        """Entity in no relationships is flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Account", attributes=[]),
                Entity(name="Orphan", attributes=[]),
            ],
            relationship_files=[RelationshipFile(
                domain="Core",
                relationships=[Relationship(
                    name="SELF_REF", from_entity="Account", to_entity="Account",
                )],
            )],
        )
        report = curate_coverage(ont)
        orphan_warnings = [f for f in report.warnings if "orphaned" in f.message.lower()]
        assert len(orphan_warnings) == 1
        assert "Orphan" in orphan_warnings[0].message

    def test_no_orphans_when_connected(self):
        """All entities in relationships are not flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="A", attributes=[]),
                Entity(name="B", attributes=[]),
            ],
            relationship_files=[RelationshipFile(
                domain="Core",
                relationships=[Relationship(name="LINKS", from_entity="A", to_entity="B")],
            )],
        )
        report = curate_coverage(ont)
        orphan_warnings = [f for f in report.warnings if "orphaned" in f.message.lower()]
        assert len(orphan_warnings) == 0

    def test_entity_with_no_observations(self):
        """Entity not referenced by any observation is info."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[], notes="Has notes.")],
            observation_files=[ObservationFile(
                name="Notes", about="Contact",
                observations=[Observation(heading="X", prose="text")],
            )],
        )
        report = curate_coverage(ont)
        obs_infos = [f for f in report.infos if "observations" in f.message.lower()]
        assert any("Account" in f.message for f in obs_infos)

    def test_observation_without_claims_flagged(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[], notes="Detailed notes for context.")],
            observation_files=[ObservationFile(
                name="Discovery",
                about="Account",
                observations=[Observation(heading="Thin", prose="short text")],
            )],
        )
        report = curate_coverage(ont)
        assert any("no semi-structured claims" in f.message for f in report.infos)
        assert any("very little narrative signal" in f.message for f in report.warnings)

    def test_observation_with_claims_not_flagged(self):
        from lore.models import KnowledgeClaim
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[], notes="Detailed notes for context.")],
            observation_files=[ObservationFile(
                name="Discovery",
                about="Account",
                observations=[Observation(
                    heading="Rich",
                    prose="This call had substantial context and specifics.",
                    claims=[KnowledgeClaim(kind="fact", text="Client requires SOC2")],
                )],
            )],
        )
        report = curate_coverage(ont)
        assert not any("no semi-structured claims" in f.message for f in report.infos)

    def test_coverage_score(self):
        """Coverage score is calculated."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="A", attributes=[], notes="notes", identity="unique by id"),
                Entity(name="B", attributes=[], notes="notes"),
            ],
            relationship_files=[RelationshipFile(
                domain="Core",
                relationships=[Relationship(name="R", from_entity="A", to_entity="B")],
            )],
        )
        report = curate_coverage(ont)
        assert "Coverage:" in report.summary
        # A has notes+identity, B has notes only, both connected
        # notes: 2/2=1.0, identity: 1/2=0.5, connected: 2/2=1.0
        # score = (1.0*0.4 + 0.5*0.3 + 1.0*0.3)*100 = 85%
        assert "85%" in report.summary

    def test_empty_ontology_coverage(self):
        """Empty ontology reports 'no entities'."""
        ont = Ontology(manifest=OntologyManifest(name="test", version="1.0"))
        report = curate_coverage(ont)
        assert "No entities" in report.summary


# ---------------------------------------------------------------------------
# Job 3: Consistency
# ---------------------------------------------------------------------------

class TestConsistency:
    def test_rule_references_missing_attribute(self):
        """Rule condition referencing nonexistent attribute is flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="name", type="string")],
            )],
            rule_files=[RuleFile(
                domain="Test",
                rules=[Rule(
                    name="bad-rule",
                    applies_to="Account",
                    condition="Account.nonexistent > 5",
                )],
            )],
        )
        report = curate_consistency(ont)
        attr_warnings = [f for f in report.warnings if "nonexistent" in f.message]
        assert len(attr_warnings) == 1
        assert "bad-rule" in attr_warnings[0].message

    def test_rule_references_valid_attribute(self):
        """Rule referencing existing attribute is not flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="score", type="float")],
            )],
            rule_files=[RuleFile(
                domain="Test",
                rules=[Rule(
                    name="good-rule",
                    applies_to="Account",
                    condition="Account.score > 0.5",
                )],
            )],
        )
        report = curate_consistency(ont)
        attr_warnings = [f for f in report.warnings if "score" in f.message]
        assert len(attr_warnings) == 0

    def test_taxonomy_applied_to_missing_attribute(self):
        """Taxonomy referencing nonexistent attribute is flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="name", type="string")],
            )],
            taxonomies=[Taxonomy(
                name="Industry",
                applied_to="Account.industry",
                root=TaxonomyNode(name="Root"),
            )],
        )
        report = curate_consistency(ont)
        tax_warnings = [f for f in report.warnings if "Taxonomy" in f.message]
        assert len(tax_warnings) == 1
        assert "industry" in tax_warnings[0].message

    def test_taxonomy_applied_to_valid_attribute(self):
        """Taxonomy referencing existing attribute is fine."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="industry", type="string")],
            )],
            taxonomies=[Taxonomy(
                name="Industry",
                applied_to="Account.industry",
                root=TaxonomyNode(name="Root"),
            )],
        )
        report = curate_consistency(ont)
        tax_warnings = [f for f in report.warnings if "Taxonomy" in f.message]
        assert len(tax_warnings) == 0

    def test_high_confidence_wrong_prediction(self):
        """High-confidence observation with wrong outcome is flagged."""
        from pathlib import Path
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Q2 Notes",
                confidence=0.85,
                source_file=Path("observations/q2.lore"),
                observations=[Observation(heading="Acme signals", prose="looks good")],
            )],
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="Acme prediction — false positive",
                    prose="We were wrong.",
                    refs=["observations/q2.lore#acme-signals"],
                )],
            )],
        )
        report = curate_consistency(ont)
        drift_findings = [f for f in report.infos if "confidence" in f.message]
        assert len(drift_findings) == 1
        assert "0.85" in drift_findings[0].message

    def test_no_issues_on_clean_ontology(self):
        """Clean ontology has no consistency issues."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="score", type="float")],
            )],
            rule_files=[RuleFile(
                domain="Test",
                rules=[Rule(
                    name="good-rule",
                    applies_to="Account",
                    condition="Account.score > 0.5",
                )],
            )],
        )
        report = curate_consistency(ont)
        assert len(report.findings) == 0

    def test_outcome_without_takeaways_or_refs_flagged(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(heading="Result", prose="Something happened.")],
            )],
        )
        report = curate_consistency(ont)
        messages = [f.message for f in report.infos]
        assert any("no Takeaway markers" in m for m in messages)
        assert any("no observation references" in m for m in messages)


# ---------------------------------------------------------------------------
# Job 4: Summarize
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_template_summary_no_issues(self):
        """Clean ontology gets positive summary."""
        ont = Ontology(manifest=OntologyManifest(name="test", version="1.0"))
        report = curate_summarize(ont, [])
        assert "No issues found" in report.summary

    def test_template_summary_with_warnings(self):
        """Summary includes warning counts."""
        ont = Ontology(manifest=OntologyManifest(name="test", version="1.0"))
        staleness = curate_staleness(Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="30d"),
            ),
            entities=[Entity(
                name="Stale",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(created="2024-01-01"),
            )],
        ), today=date(2025, 4, 1))
        report = curate_summarize(ont, [staleness])
        assert "warning" in report.summary.lower()
        assert "Top actions" in report.summary

    def test_llm_fn_used_when_provided(self):
        """Summary uses LLM function when provided."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="A", attributes=[])],
        )

        def mock_llm(prompt: str) -> str:
            assert "test" in prompt  # ontology name should be in prompt
            return "LLM generated summary"

        report = curate_summarize(ont, [], llm_fn=mock_llm)
        assert report.summary == "LLM generated summary"

    def test_llm_fn_failure_falls_back(self):
        """If LLM fails, falls back to template."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="A", attributes=[])],
        )

        def failing_llm(prompt: str) -> str:
            raise RuntimeError("API error")

        report = curate_summarize(ont, [], llm_fn=failing_llm)
        assert "test" in report.summary  # template includes ontology name
        assert "No issues found" in report.summary


# ---------------------------------------------------------------------------
# curate_all
# ---------------------------------------------------------------------------

class TestCurateAll:
    def test_returns_five_reports(self):
        """curate_all returns exactly 5 reports."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="id", type="string")],
                notes="Has notes.",
                identity="Unique by id.",
            )],
        )
        reports = curate_all(ont, today=date(2025, 4, 1))
        assert len(reports) == 5
        jobs = [r.job for r in reports]
        assert jobs == ["staleness", "coverage", "consistency", "index", "summarize"]

    def test_curate_all_passes_today(self):
        """curate_all passes the today parameter to staleness."""
        ont = Ontology(
            manifest=OntologyManifest(
                name="test", version="1.0",
                evolution=EvolutionConfig(staleness="30d"),
            ),
            entities=[Entity(
                name="Account",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(created="2025-03-01"),
                notes="Notes.", identity="Unique.",
            )],
        )
        # 15 days old, threshold 30d -> not stale
        reports = curate_all(ont, today=date(2025, 3, 16))
        staleness = reports[0]
        assert len(staleness.warnings) == 0

        # 45 days old, threshold 30d -> stale
        reports = curate_all(ont, today=date(2025, 4, 15))
        staleness = reports[0]
        assert len(staleness.warnings) == 1


# ---------------------------------------------------------------------------
# Integration: full example
# ---------------------------------------------------------------------------

class TestCuratorOnExample:
    def test_example_runs_without_error(self, example_ontology):
        """Curator runs on the full B2B SaaS example without crashing."""
        reports = curate_all(example_ontology)
        assert len(reports) == 5
        for r in reports:
            assert r.summary  # every job produces a summary

    def test_example_staleness_report_available(self, example_ontology):
        """The example ontology produces a staleness report."""
        report = curate_staleness(example_ontology)
        assert report.job == "staleness"
        assert "threshold:" in report.summary

    def test_example_coverage_score(self, example_ontology):
        """The example ontology should have a reasonable coverage score."""
        report = curate_coverage(example_ontology)
        assert "Coverage:" in report.summary
