"""Tests for decisions as a first-class file type."""
import json
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute,
    Decision, DecisionFile, KnowledgeClaim, Provenance,
    Rule, RuleFile,
    Observation, ObservationFile,
    Outcome, OutcomeFile,
)
from lore.validator import validate, Severity
from lore.compilers.agent import compile_agent_context
from lore.compilers.json_export import compile_json
from lore.compilers.embeddings import compile_embeddings
from lore.compilers.agents_md import compile_agents_md
from lore.compilers.metrics import compile_metrics
from lore.diff import diff_ontologies


# ── Fixtures ──────────────────────────────────────────────────

FULL_DECISION_FILE = """---
decision: Seasonal Churn Exception
decided_by: VP Customer Success
date: 2025-07-15
status: stable
provenance:
  author: outcome-tracker-agent
  source: domain-expert
  confidence: 0.92
  created: 2025-07-15
---

## Exempt cyclical industries from usage-decline alerts

## Context

Beta Corp was flagged as churn risk by the usage-decline-alert rule,
but the usage drop was seasonal. Retail and agriculture accounts
routinely show 40-60% usage drops during their off-season quarters.

## Resolution

Add seasonal adjustment to the usage-decline-alert rule. Accounts
in cyclical industries (retail, agriculture, tourism) are exempt
from churn risk alerts during their known off-season periods.

## Rationale

Fact: Retail accounts show 40-60% usage drop every Q3
Precedent: Three previous false positives on seasonal accounts in 2024
Belief: Seasonal patterns are predictable enough to exempt automatically
Value: Reducing false positive noise improves CSM trust in alert system

## Affects
- rules/churn-risk.lore#usage-decline-alert
- entities/account.lore

## Evidence
- outcomes/q2-retrospective.lore#beta-corp-churn-risk-false-positive
- observations/feature-adoption-patterns.lore
"""

MINIMAL_DECISION_FILE = """---
decision: Quick Decision
date: 2025-01-01
---

## Switch to weekly syncs

We decided to switch from daily to weekly syncs.
"""

MULTI_DECISION_FILE = """---
decision: Q3 Policy Decisions
decided_by: Leadership Team
date: 2025-09-01
---

## Raise free tier limits

## Context

User feedback shows free tier is too restrictive.

## Resolution

Double the free tier limits from 100 to 200 requests/day.

## Deprecate legacy API v1

## Context

v1 API has <5% of traffic and is expensive to maintain.

## Resolution

Sunset v1 by end of Q4 2025. Migrate remaining users.

## Rationale

Fact: v1 handles less than 5% of total API traffic
Value: Reducing maintenance burden frees up engineering resources
"""


# ── Parser Tests ──────────────────────────────────────────────

class TestDecisionParser:
    def test_full_decision_file(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"account.lore": "---\nentity: Account\n---\n## Attributes\nid: string"},
            decisions={"seasonal-churn-exception.lore": FULL_DECISION_FILE},
        )
        assert len(ont.decision_files) == 1
        df = ont.decision_files[0]
        assert df.name == "Seasonal Churn Exception"
        assert df.decided_by == "VP Customer Success"
        assert df.date == "2025-07-15"
        assert df.status == "stable"
        assert df.provenance is not None
        assert df.provenance.author == "outcome-tracker-agent"
        assert df.provenance.confidence == 0.92

        assert len(df.decisions) == 1
        dec = df.decisions[0]
        assert dec.heading == "Exempt cyclical industries from usage-decline alerts"
        assert "Beta Corp" in dec.context
        assert "seasonal adjustment" in dec.resolution
        assert len(dec.rationale_claims) == 4
        kinds = {c.kind for c in dec.rationale_claims}
        assert kinds == {"fact", "precedent", "belief", "value"}
        assert len(dec.affects) == 2
        assert "rules/churn-risk.lore#usage-decline-alert" in dec.affects
        assert len(dec.evidence) == 2

    def test_minimal_decision_file(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"quick.lore": MINIMAL_DECISION_FILE},
        )
        assert len(ont.decision_files) == 1
        df = ont.decision_files[0]
        assert df.name == "Quick Decision"
        assert df.date == "2025-01-01"
        assert len(df.decisions) == 1
        dec = df.decisions[0]
        assert dec.heading == "Switch to weekly syncs"
        assert "weekly syncs" in dec.context  # prose falls through to context

    def test_multi_decision_file(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"q3-policies.lore": MULTI_DECISION_FILE},
        )
        assert len(ont.decision_files) == 1
        df = ont.decision_files[0]
        assert df.decided_by == "Leadership Team"
        assert len(df.decisions) == 2

        dec1 = df.decisions[0]
        assert dec1.heading == "Raise free tier limits"
        assert "free tier" in dec1.context
        assert "Double" in dec1.resolution

        dec2 = df.decisions[1]
        assert dec2.heading == "Deprecate legacy API v1"
        assert "v1 API" in dec2.context
        assert "Sunset v1" in dec2.resolution
        assert len(dec2.rationale_claims) == 2  # Fact + Value

    def test_decision_without_frontmatter_name(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"my-cool-decision.lore": """---
date: 2025-03-01
---

## Something important

We decided something.
"""},
        )
        df = ont.decision_files[0]
        # Should derive name from filename
        assert df.name == "My Cool Decision"

    def test_decision_no_subsections(self, tmp_ontology):
        """A decision file with just a heading and prose, no Context/Resolution sections."""
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"simple.lore": """---
decision: Simple Choice
---

## We chose option A

Option A was cheaper and faster to implement.
"""},
        )
        df = ont.decision_files[0]
        assert len(df.decisions) == 1
        dec = df.decisions[0]
        assert dec.heading == "We chose option A"
        assert "Option A" in dec.context

    def test_all_decisions_aggregation(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={
                "a.lore": "---\ndecision: A\n---\n## Decision A\nContent A",
                "b.lore": "---\ndecision: B\n---\n## Decision B\nContent B",
            },
        )
        assert len(ont.decision_files) == 2
        assert len(ont.all_decisions) == 2
        headings = {d.heading for d in ont.all_decisions}
        assert headings == {"Decision A", "Decision B"}

    def test_decision_claims_in_all_claims(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": """---
decision: D
---

## A decision

## Context

Something happened.

## Resolution

We fixed it.

## Rationale

Fact: The sky is blue
Belief: Things will improve
"""},
        )
        # Claims from decision rationale should appear in all_claims
        all_claims = ont.all_claims
        decision_claims = [c for c in all_claims if c.kind in ("fact", "belief")]
        assert len(decision_claims) >= 2
        texts = {c.text for c in decision_claims}
        assert "The sky is blue" in texts
        assert "Things will improve" in texts

    def test_empty_decisions_directory(self, tmp_ontology, tmp_path):
        """An empty decisions/ directory should not break parsing."""
        (tmp_path / "lore.yaml").write_text("name: test\nversion: 0.1.0")
        (tmp_path / "decisions").mkdir(exist_ok=True)
        from lore.parser import parse_ontology
        ont = parse_ontology(tmp_path)
        assert len(ont.decision_files) == 0
        assert len(ont.all_decisions) == 0


# ── Validator Tests ───────────────────────────────────────────

class TestDecisionValidator:
    def test_valid_decision_no_errors(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"account.lore": "---\nentity: Account\n---\n## Attributes\nid: string"},
            decisions={"d.lore": FULL_DECISION_FILE},
            observations={"feature-adoption-patterns.lore": """---
observations: Feature Adoption
about: Account
date: 2025-06-01
---

## Pattern observed

Some patterns.
"""},
            outcomes={"q2-retrospective.lore": """---
outcomes: Q2 Retrospective
date: 2025-07-01
---

## Beta Corp churn risk false positive

This was a false positive.
"""},
        )
        diags = validate(ont)
        decision_errors = [d for d in diags
                          if d.severity == Severity.ERROR and "Decision" in d.message]
        assert len(decision_errors) == 0

    def test_invalid_date_warning(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": """---
decision: Bad Date
date: not-a-date
---

## Something

Decided this.
"""},
        )
        diags = validate(ont)
        date_warns = [d for d in diags
                      if "invalid date" in d.message.lower()]
        assert len(date_warns) == 1

    def test_unknown_claim_kind_warning(self):
        """Unknown claim kinds injected directly trigger validator warnings."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            decision_files=[DecisionFile(
                name="Bad Claims",
                date="2025-01-01",
                decisions=[Decision(
                    heading="A decision",
                    context="Something",
                    resolution="Something",
                    rationale_claims=[
                        KnowledgeClaim(kind="madeupkind", text="Not valid"),
                    ],
                )],
            )],
        )
        diags = validate(ont)
        claim_warns = [d for d in diags
                       if "unknown claim kind" in d.message.lower()]
        assert len(claim_warns) == 1

    def test_missing_resolution_info(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": """---
decision: No Resolution
date: 2025-01-01
---

## A heading

Just context, no resolution section.
"""},
        )
        diags = validate(ont)
        info_msgs = [d for d in diags
                     if d.severity == Severity.INFO and "no Resolution" in d.message]
        assert len(info_msgs) >= 1

    def test_empty_decision_file_warning(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": """---
decision: Empty
date: 2025-01-01
---
"""},
        )
        diags = validate(ont)
        empty_warns = [d for d in diags
                       if "no decision sections" in d.message.lower()]
        assert len(empty_warns) == 1

    def test_unresolvable_evidence_warning(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": """---
decision: Bad Evidence
date: 2025-01-01
---

## A decision

## Context

Stuff.

## Resolution

More stuff.

## Evidence
- observations/nonexistent.lore
- outcomes/also-nonexistent.lore
"""},
        )
        diags = validate(ont)
        evidence_warns = [d for d in diags
                         if "unknown" in d.message.lower()
                         and ("observation" in d.message.lower()
                              or "outcome" in d.message.lower())]
        assert len(evidence_warns) == 2


# ── Agent Compiler Tests ──────────────────────────────────────

class TestDecisionAgentCompiler:
    def _ontology_with_decision(self):
        return Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            entities=[Entity(name="Account", attributes=[
                Attribute(name="id", type="string"),
            ])],
            decision_files=[DecisionFile(
                name="Seasonal Exception",
                decided_by="VP CS",
                date="2025-07-15",
                decisions=[Decision(
                    heading="Exempt cyclical industries",
                    context="Usage drop was seasonal",
                    resolution="Add seasonal adjustment",
                    rationale="Seasonal patterns are predictable",
                    rationale_claims=[
                        KnowledgeClaim(kind="Fact", text="40-60% drop every Q3"),
                        KnowledgeClaim(kind="Value", text="Reduce false positive noise"),
                    ],
                    affects=["rules/churn-risk.lore"],
                    evidence=["outcomes/q2-retro.lore"],
                )],
            )],
        )

    def test_decisions_in_agent_context(self):
        ont = self._ontology_with_decision()
        output = compile_agent_context(ont)
        assert "<decisions>" in output
        assert "</decisions>" in output
        assert "Exempt cyclical industries" in output
        assert "VP CS" in output
        assert "seasonal adjustment" in output
        assert "Fact: 40-60% drop every Q3" in output
        assert "Value: Reduce false positive noise" in output

    def test_decisions_with_budget(self):
        ont = self._ontology_with_decision()
        # Large budget — decisions should be included
        output = compile_agent_context(ont, budget_tokens=10000)
        assert "<decisions>" in output

    def test_no_decisions_no_section(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            entities=[Entity(name="X", attributes=[
                Attribute(name="id", type="string"),
            ])],
        )
        output = compile_agent_context(ont)
        assert "<decisions>" not in output


# ── JSON Compiler Tests ───────────────────────────────────────

class TestDecisionJsonCompiler:
    def test_decisions_in_json_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            decision_files=[DecisionFile(
                name="Test Decision",
                decided_by="Alice",
                date="2025-01-01",
                decisions=[Decision(
                    heading="Do the thing",
                    context="We needed to do it",
                    resolution="We did it",
                    rationale_claims=[
                        KnowledgeClaim(kind="Fact", text="It works"),
                    ],
                    affects=["entities/x.lore"],
                    evidence=["observations/y.lore"],
                )],
            )],
        )
        output = compile_json(ont)
        data = json.loads(output)
        assert "decisions" in data
        assert len(data["decisions"]) == 1
        df = data["decisions"][0]
        assert df["name"] == "Test Decision"
        assert df["decided_by"] == "Alice"
        assert len(df["decisions"]) == 1
        dec = df["decisions"][0]
        assert dec["heading"] == "Do the thing"
        assert dec["context"] == "We needed to do it"
        assert dec["resolution"] == "We did it"
        assert len(dec["rationale_claims"]) == 1
        assert dec["affects"] == ["entities/x.lore"]
        assert dec["evidence"] == ["observations/y.lore"]


# ── Embeddings Compiler Tests ─────────────────────────────────

class TestDecisionEmbeddingsCompiler:
    def test_decision_chunks(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            decision_files=[DecisionFile(
                name="Test",
                decided_by="Bob",
                date="2025-03-01",
                decisions=[Decision(
                    heading="Choose framework",
                    context="We evaluated options",
                    resolution="We chose Django",
                )],
            )],
        )
        output = compile_embeddings(ont)
        chunks = [json.loads(line) for line in output.strip().split("\n") if line.strip()]
        decision_chunks = [c for c in chunks if c.get("type") == "decision"]
        assert len(decision_chunks) == 1
        chunk = decision_chunks[0]
        assert "Choose framework" in chunk["text"]
        assert "Django" in chunk["text"]
        assert chunk["metadata"]["decided_by"] == "Bob"
        assert "decision:Test:Choose framework" in chunk["id"]


# ── AGENTS.md Compiler Tests ─────────────────────────────────

class TestDecisionAgentsMdCompiler:
    def test_decisions_in_agents_md(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            decision_files=[DecisionFile(
                name="Policy",
                decisions=[Decision(
                    heading="Use HTTPS only",
                    resolution="All endpoints must use HTTPS",
                    context="Security audit recommended it.",
                    affects=["entities/api.lore"],
                )],
            )],
        )
        output = compile_agents_md(ont)
        assert "# Decisions" in output
        assert "Use HTTPS only" in output
        assert "All endpoints must use HTTPS" in output


# ── Metrics Compiler Tests ────────────────────────────────────

class TestDecisionMetricsCompiler:
    def test_decision_count_in_metrics(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="0.1.0"),
            decision_files=[DecisionFile(
                name="D1",
                decisions=[
                    Decision(heading="A"),
                    Decision(heading="B"),
                ],
            )],
        )
        output = compile_metrics(ont)
        data = json.loads(output)
        assert data["counts"]["decisions"] == 2


# ── Diff Tests ────────────────────────────────────────────────

class TestDecisionDiff:
    def test_decision_added(self):
        ont_a = Ontology(manifest=OntologyManifest(name="test"))
        ont_b = Ontology(
            manifest=OntologyManifest(name="test"),
            decision_files=[DecisionFile(
                name="New",
                decisions=[Decision(heading="New decision")],
            )],
        )
        result = diff_ontologies(ont_a, ont_b)
        added = [c for c in result.changes
                 if c.kind == "decision" and c.action == "added"]
        assert len(added) == 1
        assert added[0].name == "New decision"

    def test_decision_removed(self):
        ont_a = Ontology(
            manifest=OntologyManifest(name="test"),
            decision_files=[DecisionFile(
                name="Old",
                decisions=[Decision(heading="Old decision")],
            )],
        )
        ont_b = Ontology(manifest=OntologyManifest(name="test"))
        result = diff_ontologies(ont_a, ont_b)
        removed = [c for c in result.changes
                   if c.kind == "decision" and c.action == "removed"]
        assert len(removed) == 1
        assert removed[0].name == "Old decision"

    def test_decision_unchanged(self):
        df = DecisionFile(
            name="Same",
            decisions=[Decision(heading="Same decision")],
        )
        ont_a = Ontology(manifest=OntologyManifest(name="test"), decision_files=[df])
        ont_b = Ontology(manifest=OntologyManifest(name="test"), decision_files=[df])
        result = diff_ontologies(ont_a, ont_b)
        decision_changes = [c for c in result.changes if c.kind == "decision"]
        assert len(decision_changes) == 0


# ── SDK Tests ─────────────────────────────────────────────────

class TestDecisionSdk:
    def test_decisions_in_stats(self, tmp_ontology, tmp_path):
        tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": MINIMAL_DECISION_FILE},
        )
        from lore.sdk import LoreOntology
        sdk = LoreOntology(tmp_path)
        stats = sdk.stats
        assert "decisions" in stats
        assert stats["decisions"] == 1

    def test_decisions_in_search(self, tmp_ontology, tmp_path):
        tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": FULL_DECISION_FILE},
        )
        from lore.sdk import LoreOntology
        sdk = LoreOntology(tmp_path)
        results = sdk.search("seasonal churn")
        # Decisions don't appear in search (only entities, rules, glossary, observations)
        # This is by current design — future enhancement could add decision search
        # Just make sure search doesn't crash with decisions present
        assert isinstance(results, list)


# ── Example File Tests ────────────────────────────────────────

class TestDecisionExample:
    def test_b2b_example_has_decisions(self, example_ontology):
        """The B2B SaaS GTM example should include the decision file."""
        assert len(example_ontology.decision_files) >= 1
        df = example_ontology.decision_files[0]
        assert df.name == "Seasonal Churn Exception"
        assert len(df.decisions) >= 1

    def test_b2b_example_validates_with_decisions(self, example_ontology):
        diags = validate(example_ontology)
        decision_errors = [d for d in diags
                          if d.severity == Severity.ERROR
                          and "decision" in d.message.lower()]
        assert len(decision_errors) == 0

    def test_b2b_example_compiles_with_decisions(self, example_ontology):
        output = compile_agent_context(example_ontology)
        assert "<decisions>" in output
        assert "Seasonal Churn Exception" in output or "Exempt cyclical" in output


# ── Indexer Tests ─────────────────────────────────────────────

class TestDecisionIndexer:
    def test_decisions_in_root_index(self, tmp_ontology, tmp_path):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": MINIMAL_DECISION_FILE},
        )
        from lore.indexer import generate_root_index
        index = generate_root_index(ont, tmp_path)
        assert "decision" in index.lower()

    def test_decisions_in_stats_line(self, tmp_ontology, tmp_path):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            decisions={"d.lore": MINIMAL_DECISION_FILE},
        )
        from lore.indexer import generate_root_index
        index = generate_root_index(ont, tmp_path)
        assert "1 decisions" in index
