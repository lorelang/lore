"""Tests for transcript/memory ingestion and proposal review workflows."""
from pathlib import Path
import json

import pytest

from lore.cli import cmd_ingest_memory, cmd_ingest_transcript, cmd_review
from lore.ingest import ingest_memory, ingest_transcript
from lore.parser import parse_ontology
from lore.review import review_proposals


def _write_min_ontology(root: Path):
    (root / "lore.yaml").write_text(
        "name: ingest-test\n"
        "version: 0.2.0\n"
    )
    (root / "entities").mkdir(parents=True, exist_ok=True)
    (root / "entities" / "account.lore").write_text(
        "---\n"
        "entity: Account\n"
        "---\n"
        "\n"
        "## Attributes\n"
        "\n"
        "id: string [required]\n"
    )


def test_ingest_transcript_generates_claims(tmp_path):
    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir()
    _write_min_ontology(ontology_dir)

    transcript = tmp_path / "meeting.txt"
    transcript.write_text(
        "Alex: Acme has 4 sales teams and 2 RevOps analysts. "
        "We think security review is likely the critical path. "
        "It is important to complete SSO before pilot. "
        "Historically this integration failed before this when scope was unclear.\n"
    )

    out = ingest_transcript(
        ontology_dir,
        transcript,
        "Account",
        observed_by="transcript-agent",
        source="meeting-recording",
        date_str="2026-02-20",
    )
    assert out.exists()

    ont = parse_ontology(ontology_dir)
    assert len(ont.observation_files) == 1
    obs_file = ont.observation_files[0]
    assert obs_file.about == "Account"
    assert obs_file.observed_by == "transcript-agent"
    assert obs_file.date == "2026-02-20"

    claim_kinds = {
        claim.kind
        for obs in obs_file.observations
        for claim in obs.claims
    }
    assert {"fact", "belief", "value", "precedent"} <= claim_kinds


@pytest.mark.parametrize(
    "adapter,records",
    [
        (
            "arscontexta",
            [{"summary": "Client has 3 teams. This is important for rollout.", "tags": ["discovery"]}],
        ),
        (
            "mem0",
            [{"memory": "There are 2 blockers and we think security is likely gating.", "title": "Blockers"}],
        ),
        (
            "graphiti",
            [{
                "fact": "Launch includes 2 integrations.",
                "source": "Client",
                "relation": "DEPENDS_ON",
                "target": "SecurityReview",
            }],
        ),
    ],
)
def test_ingest_memory_supports_adapters(tmp_path, adapter, records):
    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir()
    _write_min_ontology(ontology_dir)

    export = tmp_path / f"{adapter}.json"
    export.write_text(json.dumps(records))

    out = ingest_memory(
        ontology_dir,
        export,
        adapter,
        "Account",
        date_str="2026-02-20",
    )
    assert out.exists()

    ont = parse_ontology(ontology_dir)
    assert len(ont.observation_files) == 1
    obs_file = ont.observation_files[0]
    assert obs_file.about == "Account"
    assert obs_file.observations
    assert obs_file.observed_by == f"{adapter}-adapter"


def test_review_proposals_updates_and_skips(tmp_path):
    proposals = tmp_path / "proposals"
    proposals.mkdir()

    open_proposal = proposals / "p1.lore"
    open_proposal.write_text(
        "---\n"
        "proposal: improve-rule\n"
        "review_required: true\n"
        "review_state: proposed\n"
        "---\n"
        "\n"
        "## Summary\n"
        "Draft proposal.\n"
    )

    accepted_proposal = proposals / "p2.lore"
    accepted_proposal.write_text(
        "---\n"
        "proposal: already-reviewed\n"
        "review_required: false\n"
        "review_state: accepted\n"
        "review_decision: accept\n"
        "---\n"
        "\n"
        "## Summary\n"
        "Already accepted.\n"
    )

    result = review_proposals(
        proposals,
        decision="accept",
        reviewer="ontology-curator",
        note="Looks good",
        include_all=False,
    )
    assert open_proposal in result.reviewed
    assert accepted_proposal in result.skipped

    updated = open_proposal.read_text()
    assert "review_state: accepted" in updated
    assert "review_decision: accept" in updated
    assert "review_required: false" in updated
    assert "reviewed_by: ontology-curator" in updated
    assert "review_note: Looks good" in updated


def test_cmd_ingest_handlers_and_review_handler(tmp_path):
    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir()
    _write_min_ontology(ontology_dir)

    transcript = tmp_path / "client-call.txt"
    transcript.write_text("Facilitator: Client has 2 teams and important rollout deadlines.\n")
    cmd_ingest_transcript(
        str(ontology_dir),
        str(transcript),
        "Account",
        name=None,
        observed_by="ingest-cli-agent",
        confidence=0.7,
        source="imported",
        date_str="2026-02-20",
        output="transcript-observations.lore",
        max_sections=5,
    )
    assert (ontology_dir / "observations" / "transcript-observations.lore").exists()

    memory_json = tmp_path / "mem0.json"
    memory_json.write_text(json.dumps([{"memory": "There are 3 blockers in this onboarding flow."}]))
    cmd_ingest_memory(
        str(ontology_dir),
        "mem0",
        str(memory_json),
        "Account",
        name=None,
        observed_by=None,
        confidence=0.6,
        source="imported",
        date_str="2026-02-20",
        output="memory-observations.lore",
        max_sections=3,
    )
    assert (ontology_dir / "observations" / "memory-observations.lore").exists()

    proposals = tmp_path / "proposals"
    proposals.mkdir()
    proposal = proposals / "proposal-1.lore"
    proposal.write_text(
        "---\n"
        "proposal: test\n"
        "review_required: true\n"
        "---\n"
        "\n"
        "## Summary\n"
        "Candidate change.\n"
    )
    cmd_review(
        str(proposals),
        decision="reject",
        reviewer="reviewer-1",
        note="Need better evidence",
        include_all=False,
    )
    reviewed_text = proposal.read_text()
    assert "review_state: rejected" in reviewed_text
    assert "review_decision: reject" in reviewed_text
    assert "reviewed_by: reviewer-1" in reviewed_text


def test_cmd_ingest_rejects_invalid_confidence(tmp_path):
    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir()
    _write_min_ontology(ontology_dir)

    transcript = tmp_path / "call.txt"
    transcript.write_text("Speaker: Short note.\n")

    with pytest.raises(SystemExit):
        cmd_ingest_transcript(
            str(ontology_dir),
            str(transcript),
            "Account",
            name=None,
            observed_by="agent",
            confidence=1.2,
            source="imported",
            date_str="2026-02-20",
            output=None,
            max_sections=3,
        )
