"""Tests for observations and outcomes (Phases 2 & 3)."""
import json
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute,
    Observation, ObservationFile, Outcome, OutcomeFile,
)
from lore.validator import validate, Severity
from lore.compilers.agent import compile_agent_context
from lore.compilers.json_export import compile_json
from lore.compilers.embeddings import compile_embeddings


# --- Observation Parser Tests ---

class TestObservationParser:
    def test_basic_observation_file(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"account.lore": "---\nentity: Account\n---\n## Attributes\nid: string"},
            observations={"q2-signals.lore": """---
observations: Q2 Account Signals
about: Account
observed_by: expansion-agent-v2
date: 2025-06-15
confidence: 0.75
status: proposed
---

## Acme Corp shows expansion readiness

Acme Corp is showing classic multi-signal expansion
patterns over the past 30 days.

## Beta Corp usage decline looks seasonal

Beta Corp showed a 30% usage decline in Q4,
but this matches their industry's seasonal pattern.
"""},
        )
        assert len(ont.observation_files) == 1
        of = ont.observation_files[0]
        assert of.name == "Q2 Account Signals"
        assert of.about == "Account"
        assert of.observed_by == "expansion-agent-v2"
        assert of.date == "2025-06-15"
        assert of.confidence == 0.75
        assert of.status == "proposed"
        assert len(of.observations) == 2
        assert of.observations[0].heading == "Acme Corp shows expansion readiness"
        assert "multi-signal expansion" in of.observations[0].prose
        assert of.observations[1].heading == "Beta Corp usage decline looks seasonal"

    def test_observation_without_optional_fields(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            observations={"notes.lore": """---
observations: Field Notes
---

## Something interesting

Just a note about something.
"""},
        )
        of = ont.observation_files[0]
        assert of.name == "Field Notes"
        assert of.about == ""
        assert of.observed_by == ""
        assert of.date == ""
        assert of.confidence is None
        assert of.status == ""

    def test_observation_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            observations={"notes.lore": """---
observations: AI Notes
observed_by: agent-v3
provenance:
  author: agent-v3
  source: ai-generated
  confidence: 0.8
status: draft
---

## A finding

Some finding here.
"""},
        )
        of = ont.observation_files[0]
        assert of.provenance is not None
        assert of.provenance.source == "ai-generated"
        assert of.provenance.confidence == 0.8

    def test_multiple_observation_files(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            observations={
                "q1.lore": "---\nobservations: Q1 Notes\n---\n## Note 1\nSome text.",
                "q2.lore": "---\nobservations: Q2 Notes\n---\n## Note 2\nMore text.",
            },
        )
        assert len(ont.observation_files) == 2
        assert len(ont.all_observations) == 2

    def test_all_observations_property(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            observations={
                "multi.lore": """---
observations: Multi
---
## First
Text 1.

## Second
Text 2.

## Third
Text 3.
""",
            },
        )
        assert len(ont.all_observations) == 3


# --- Outcome Parser Tests ---

class TestOutcomeParser:
    def test_basic_outcome_file(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            outcomes={"q2-retro.lore": """---
outcomes: Q2 2025 Retrospective
reviewed_by: outcome-tracker-agent
date: 2025-07-01
---

## Acme Corp expansion — correct

We predicted Acme Corp was expansion-ready.
They expanded. Upsell closed for +$45K ARR.

Takeaway: increase weight of executive engagement signals
Ref: observations/q2-signals.lore#acme-corp

## Beta Corp churn risk — false positive

We flagged Beta Corp as churn risk.
They renewed at the same tier.

Takeaway: usage-decline-alert rule needs seasonal adjustment
Ref: observations/q2-signals.lore#beta-corp
"""},
        )
        assert len(ont.outcome_files) == 1
        of = ont.outcome_files[0]
        assert of.name == "Q2 2025 Retrospective"
        assert of.reviewed_by == "outcome-tracker-agent"
        assert of.date == "2025-07-01"
        assert len(of.outcomes) == 2

        outcome1 = of.outcomes[0]
        assert "Acme Corp expansion" in outcome1.heading
        assert "expansion-ready" in outcome1.prose
        assert len(outcome1.takeaways) == 1
        assert "executive engagement" in outcome1.takeaways[0]
        assert len(outcome1.refs) == 1
        assert "q2-signals.lore#acme-corp" in outcome1.refs[0]

        outcome2 = of.outcomes[1]
        assert "false positive" in outcome2.heading
        assert len(outcome2.takeaways) == 1
        assert "seasonal adjustment" in outcome2.takeaways[0]

    def test_outcome_without_refs_or_takeaways(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            outcomes={"simple.lore": """---
outcomes: Simple Retro
reviewed_by: human
date: 2025-07-01
---

## Something happened

We observed something and it was fine.
No specific takeaways or references needed.
"""},
        )
        outcome = ont.outcome_files[0].outcomes[0]
        assert outcome.heading == "Something happened"
        assert len(outcome.takeaways) == 0
        assert len(outcome.refs) == 0
        assert "fine" in outcome.prose

    def test_outcome_with_multiple_takeaways(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            outcomes={"multi.lore": """---
outcomes: Multi Takeaway
date: 2025-07-01
---

## Big learning

Lots of things happened.

Takeaway: first lesson learned
Takeaway: second lesson learned
Takeaway: third lesson learned
Ref: observations/q1.lore#something
Ref: observations/q2.lore#something-else
"""},
        )
        outcome = ont.outcome_files[0].outcomes[0]
        assert len(outcome.takeaways) == 3
        assert len(outcome.refs) == 2

    def test_all_outcomes_property(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            outcomes={
                "a.lore": "---\noutcomes: A\ndate: 2025-01-01\n---\n## O1\nText.\n\n## O2\nText.",
                "b.lore": "---\noutcomes: B\ndate: 2025-01-01\n---\n## O3\nText.",
            },
        )
        assert len(ont.all_outcomes) == 3

    def test_all_takeaways_property(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            outcomes={"t.lore": """---
outcomes: Takeaways
date: 2025-01-01
---

## First

Takeaway: lesson A
Takeaway: lesson B

## Second

Takeaway: lesson C
"""},
        )
        assert len(ont.all_takeaways) == 3
        assert "lesson A" in ont.all_takeaways
        assert "lesson B" in ont.all_takeaways
        assert "lesson C" in ont.all_takeaways

    def test_outcome_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            outcomes={"retro.lore": """---
outcomes: Retro
reviewed_by: agent
date: 2025-07-01
provenance:
  author: agent
  source: ai-generated
  confidence: 0.9
status: proposed
---

## Result

It worked.
"""},
        )
        of = ont.outcome_files[0]
        assert of.provenance is not None
        assert of.provenance.source == "ai-generated"
        assert of.status == "proposed"


# --- Observation Validation Tests ---

class TestObservationValidation:
    def test_about_references_unknown_entity(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
            observation_files=[ObservationFile(
                name="Notes",
                about="NonExistent",
                observations=[Observation(heading="Test", prose="text")],
            )],
        )
        diags = validate(ont)
        assert any("unknown entity 'NonExistent'" in d.message for d in diags if d.severity == Severity.WARNING)

    def test_about_references_valid_entity(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[Attribute(name="id", type="string")])],
            observation_files=[ObservationFile(
                name="Notes",
                about="Account",
                observations=[Observation(heading="Test", prose="text")],
            )],
        )
        diags = validate(ont)
        about_warnings = [d for d in diags if "unknown entity" in d.message]
        assert len(about_warnings) == 0

    def test_empty_about_is_fine(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Notes",
                about="",
                observations=[Observation(heading="Test", prose="text")],
            )],
        )
        diags = validate(ont)
        about_warnings = [d for d in diags if "unknown entity" in d.message]
        assert len(about_warnings) == 0

    def test_observation_confidence_out_of_range(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Notes",
                confidence=1.5,
                observations=[Observation(heading="Test", prose="text")],
            )],
        )
        diags = validate(ont)
        assert any("confidence" in d.message.lower() for d in diags if d.severity == Severity.WARNING)


# --- Outcome Validation Tests ---

class TestOutcomeValidation:
    def test_ref_to_nonexistent_observation(self):
        """Outcomes referencing non-existent observation files should warn."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(
                    heading="Test",
                    prose="text",
                    refs=["observations/nonexistent.lore#heading"],
                )],
            )],
        )
        diags = validate(ont)
        assert any("unknown observation file" in d.message for d in diags if d.severity == Severity.WARNING)

    def test_outcome_with_no_refs_is_fine(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[Outcome(heading="Test", prose="text", refs=[], takeaways=[])],
            )],
        )
        diags = validate(ont)
        ref_issues = [d for d in diags if "Ref" in d.message]
        assert len(ref_issues) == 0


# --- Agent Compiler Tests ---

class TestObservationsInAgentCompiler:
    def test_observations_in_agent_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Q2 Notes",
                about="Account",
                observed_by="agent-v2",
                date="2025-06-15",
                confidence=0.75,
                observations=[
                    Observation(heading="Acme expansion", prose="Acme is growing fast."),
                    Observation(heading="Beta decline", prose="Beta usage dropped."),
                ],
            )],
        )
        result = compile_agent_context(ont)
        assert "<observations>" in result
        assert "</observations>" in result
        assert "Acme expansion" in result
        assert "Acme is growing fast." in result
        assert "Beta decline" in result
        assert "by agent-v2" in result
        assert "on 2025-06-15" in result
        assert "confidence=0.75" in result
        assert "about Account" in result

    def test_no_observations_no_section(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Widget", attributes=[Attribute(name="id", type="string")])],
        )
        result = compile_agent_context(ont)
        assert "<observations>" not in result


class TestOutcomesInAgentCompiler:
    def test_outcomes_in_agent_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Q2 Retro",
                reviewed_by="tracker-agent",
                date="2025-07-01",
                outcomes=[
                    Outcome(
                        heading="Acme expanded",
                        prose="Prediction was correct.",
                        takeaways=["increase executive signal weight"],
                    ),
                ],
            )],
        )
        result = compile_agent_context(ont)
        assert "<outcomes>" in result
        assert "</outcomes>" in result
        assert "Acme expanded" in result
        assert "Prediction was correct." in result
        assert "increase executive signal weight" in result
        assert "by tracker-agent" in result
        assert "on 2025-07-01" in result

    def test_no_outcomes_no_section(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Widget", attributes=[Attribute(name="id", type="string")])],
        )
        result = compile_agent_context(ont)
        assert "<outcomes>" not in result


# --- JSON Compiler Tests ---

class TestObservationsInJsonCompiler:
    def test_observations_in_json(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Q2 Notes",
                about="Account",
                observed_by="agent-v2",
                date="2025-06-15",
                confidence=0.75,
                status="proposed",
                observations=[
                    Observation(heading="Acme expansion", prose="Acme is growing."),
                ],
            )],
        )
        data = json.loads(compile_json(ont))
        assert "observations" in data
        assert len(data["observations"]) == 1
        obs_file = data["observations"][0]
        assert obs_file["name"] == "Q2 Notes"
        assert obs_file["about"] == "Account"
        assert obs_file["observed_by"] == "agent-v2"
        assert obs_file["date"] == "2025-06-15"
        assert obs_file["confidence"] == 0.75
        assert obs_file["status"] == "proposed"
        assert len(obs_file["observations"]) == 1
        assert obs_file["observations"][0]["heading"] == "Acme expansion"
        assert obs_file["observations"][0]["prose"] == "Acme is growing."

    def test_no_observations_empty_list(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
        )
        data = json.loads(compile_json(ont))
        assert data["observations"] == []


class TestOutcomesInJsonCompiler:
    def test_outcomes_in_json(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Q2 Retro",
                reviewed_by="tracker",
                date="2025-07-01",
                outcomes=[
                    Outcome(
                        heading="Acme expanded",
                        prose="Correct prediction.",
                        refs=["observations/q2.lore#acme"],
                        takeaways=["boost exec signals"],
                    ),
                ],
            )],
        )
        data = json.loads(compile_json(ont))
        assert "outcomes" in data
        assert len(data["outcomes"]) == 1
        out_file = data["outcomes"][0]
        assert out_file["name"] == "Q2 Retro"
        assert out_file["reviewed_by"] == "tracker"
        assert len(out_file["outcomes"]) == 1
        outcome = out_file["outcomes"][0]
        assert outcome["heading"] == "Acme expanded"
        assert outcome["prose"] == "Correct prediction."
        assert outcome["refs"] == ["observations/q2.lore#acme"]
        assert outcome["takeaways"] == ["boost exec signals"]

    def test_no_outcomes_empty_list(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
        )
        data = json.loads(compile_json(ont))
        assert data["outcomes"] == []


# --- Embeddings Compiler Tests ---

class TestObservationsInEmbeddingsCompiler:
    def test_observation_chunks(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Q2 Notes",
                about="Account",
                observed_by="agent-v2",
                date="2025-06-15",
                confidence=0.75,
                status="proposed",
                observations=[
                    Observation(heading="Acme expansion", prose="Acme is growing."),
                    Observation(heading="Beta decline", prose="Beta usage dropped."),
                ],
            )],
        )
        result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        obs_chunks = [c for c in chunks if c["type"] == "observation"]
        assert len(obs_chunks) == 2

        acme_chunk = next(c for c in obs_chunks if "Acme" in c["text"])
        assert acme_chunk["metadata"]["about"] == "Account"
        assert acme_chunk["metadata"]["observed_by"] == "agent-v2"
        assert acme_chunk["metadata"]["date"] == "2025-06-15"
        assert acme_chunk["metadata"]["confidence"] == 0.75
        assert acme_chunk["metadata"]["status"] == "proposed"
        assert "Observation: Acme expansion" in acme_chunk["text"]
        assert "Acme is growing." in acme_chunk["text"]


class TestOutcomesInEmbeddingsCompiler:
    def test_outcome_chunks(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Q2 Retro",
                reviewed_by="tracker",
                date="2025-07-01",
                outcomes=[
                    Outcome(
                        heading="Acme expanded",
                        prose="Correct prediction.",
                        refs=["observations/q2.lore#acme"],
                        takeaways=["boost exec signals"],
                    ),
                ],
            )],
        )
        result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        out_chunks = [c for c in chunks if c["type"] == "outcome"]
        assert len(out_chunks) == 1

        chunk = out_chunks[0]
        assert chunk["metadata"]["reviewed_by"] == "tracker"
        assert chunk["metadata"]["date"] == "2025-07-01"
        assert chunk["metadata"]["refs"] == ["observations/q2.lore#acme"]
        assert chunk["metadata"]["takeaways"] == ["boost exec signals"]
        assert "Outcome: Acme expanded" in chunk["text"]
        assert "Correct prediction." in chunk["text"]
        assert "Takeaway: boost exec signals" in chunk["text"]

    def test_outcome_without_takeaways_no_takeaway_text(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            outcome_files=[OutcomeFile(
                name="Retro",
                outcomes=[
                    Outcome(heading="Simple", prose="Just happened."),
                ],
            )],
        )
        result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        out_chunks = [c for c in chunks if c["type"] == "outcome"]
        assert len(out_chunks) == 1
        assert "Takeaway:" not in out_chunks[0]["text"]


# --- Backward Compatibility ---

class TestObservationsOutcomesBackwardCompat:
    def test_example_has_observations_and_outcomes(self, example_ontology):
        """The v0.2 B2B SaaS example includes observations and outcomes."""
        assert len(example_ontology.observation_files) == 3
        assert len(example_ontology.outcome_files) == 1
        assert len(example_ontology.all_observations) == 9
        assert len(example_ontology.all_outcomes) == 3
        assert len(example_ontology.all_takeaways) == 6

    def test_example_compilers_include_observations_and_outcomes(self, example_ontology):
        result = compile_agent_context(example_ontology)
        assert "<observations>" in result
        assert "<outcomes>" in result

        data = json.loads(compile_json(example_ontology))
        assert len(data["observations"]) == 3
        assert len(data["outcomes"]) == 1

        embeddings = compile_embeddings(example_ontology)
        chunks = [json.loads(line) for line in embeddings.strip().split("\n")]
        obs_chunks = [c for c in chunks if c["type"] == "observation"]
        out_chunks = [c for c in chunks if c["type"] == "outcome"]
        assert len(obs_chunks) == 9
        assert len(out_chunks) == 3

    def test_ontology_without_observations_still_works(self, tmp_ontology):
        """An ontology without observations/ or outcomes/ dirs works fine."""
        ont = tmp_ontology(
            manifest="name: minimal\nversion: 0.1.0",
            entities={"thing.lore": "---\nentity: Thing\n---\n## Attributes\nid: string"},
        )
        assert len(ont.observation_files) == 0
        assert len(ont.outcome_files) == 0

        result = compile_agent_context(ont)
        assert "<observations>" not in result
        assert "<outcomes>" not in result

        data = json.loads(compile_json(ont))
        assert data["observations"] == []
        assert data["outcomes"] == []
