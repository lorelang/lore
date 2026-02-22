"""
Lore ingestion helpers.

Turn raw transcript/memory artifacts into observation .lore files.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
from typing import Any


def ingest_transcript(
    ontology_dir: Path,
    transcript_path: Path,
    about: str,
    *,
    observations_name: str | None = None,
    observed_by: str = "transcript-ingest-agent",
    confidence: float = 0.65,
    source: str = "imported",
    date_str: str | None = None,
    output_name: str | None = None,
    max_sections: int = 8,
) -> Path:
    """Convert a transcript file into an observations/*.lore file."""
    text = transcript_path.read_text().strip()
    if not text:
        raise ValueError(f"Transcript file is empty: {transcript_path}")

    sections = _extract_transcript_sections(text, max_sections=max_sections)
    if not sections:
        sections = [("Transcript synthesis", text)]

    name = observations_name or f"{transcript_path.stem.replace('-', ' ').replace('_', ' ').title()} Distillation"
    target_date = date_str or date.today().isoformat()
    output = _observation_output_path(ontology_dir / "observations", output_name or f"{_slug(transcript_path.stem)}-ingested.lore")

    content = _render_observation_file(
        name=name,
        about=about,
        observed_by=observed_by,
        confidence=confidence,
        source=source,
        date_str=target_date,
        sections=sections,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return output


def ingest_memory(
    ontology_dir: Path,
    input_path: Path,
    adapter: str,
    about: str,
    *,
    observations_name: str | None = None,
    observed_by: str | None = None,
    confidence: float = 0.6,
    source: str = "imported",
    date_str: str | None = None,
    output_name: str | None = None,
    max_sections: int = 12,
) -> Path:
    """Convert memory export JSON/JSONL into an observations/*.lore file."""
    adapter = adapter.strip().lower()
    if adapter not in {"arscontexta", "mem0", "graphiti"}:
        raise ValueError(f"Unsupported adapter '{adapter}'. Expected one of: arscontexta, mem0, graphiti")

    records = _load_memory_records(input_path)
    if not records:
        raise ValueError(f"No memory records found in {input_path}")

    sections: list[tuple[str, str]] = []
    for idx, record in enumerate(records, start=1):
        heading, prose = _normalize_memory_record(record, adapter, idx)
        if prose:
            sections.append((heading, prose))
        if len(sections) >= max_sections:
            break

    if not sections:
        raise ValueError(f"No usable memory records found in {input_path}")

    target_date = date_str or date.today().isoformat()
    observer = observed_by or f"{adapter}-adapter"
    name = observations_name or f"{adapter.title()} Memory Import"
    output = _observation_output_path(ontology_dir / "observations", output_name or f"{_slug(adapter)}-memory-import.lore")

    content = _render_observation_file(
        name=name,
        about=about,
        observed_by=observer,
        confidence=confidence,
        source=source,
        date_str=target_date,
        sections=sections,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return output


def _extract_transcript_sections(text: str, *, max_sections: int) -> list[tuple[str, str]]:
    blocks = _speaker_blocks(text)
    sections: list[tuple[str, str]] = []
    for idx, (speaker, chunk) in enumerate(blocks, start=1):
        prose = _summarize(chunk, max_sentences=5)
        if len(prose) < 40:
            continue
        heading = _heading_from_chunk(speaker, prose, idx)
        sections.append((heading, prose))
        if len(sections) >= max_sections:
            break
    return sections


def _speaker_blocks(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    blocks: list[tuple[str, str]] = []
    speaker = "Discussion"
    buf: list[str] = []

    speaker_pattern = re.compile(
        r"^(?:\[\d{1,2}:\d{2}(?::\d{2})?\]\s*)?([A-Za-z][A-Za-z0-9 .'\-]{1,40}):\s*(.+)$"
    )

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = speaker_pattern.match(line)
        if m:
            if buf:
                blocks.append((speaker, " ".join(buf).strip()))
            speaker = m.group(1).strip()
            buf = [m.group(2).strip()]
        else:
            buf.append(line)
    if buf:
        blocks.append((speaker, " ".join(buf).strip()))

    if blocks:
        return blocks

    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [("Discussion", p) for p in paras]


def _heading_from_chunk(speaker: str, prose: str, idx: int) -> str:
    first = _first_sentence(prose)
    short = first[:84].strip()
    if short and short[-1] in ".!?":
        short = short[:-1].strip()
    if speaker and speaker.lower() not in {"discussion", "speaker"}:
        return f"{speaker}: {short}" if short else f"{speaker} segment {idx}"
    return short if short else f"Transcript segment {idx}"


def _first_sentence(text: str) -> str:
    parts = _sentences(text)
    return parts[0] if parts else text


def _summarize(text: str, *, max_sentences: int = 4) -> str:
    sentences = _sentences(text)
    if not sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences]).strip()


def _sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    out = [s.strip() for s in raw if s and s.strip()]
    return out


def _render_observation_file(
    *,
    name: str,
    about: str,
    observed_by: str,
    confidence: float,
    source: str,
    date_str: str,
    sections: list[tuple[str, str]],
) -> str:
    lines = [
        "---",
        f"observations: {name}",
        f"about: {about}",
        f"observed_by: {observed_by}",
        f"date: {date_str}",
        f"confidence: {confidence:.2f}",
        "status: proposed",
        "provenance:",
        f"  author: {observed_by}",
        f"  source: {source}",
        f"  confidence: {confidence:.2f}",
        f"  created: {date_str}",
        "---",
        "",
    ]

    for idx, (heading, prose) in enumerate(sections, start=1):
        lines.append(f"## {heading or f'Observation {idx}'}")
        lines.append("")
        lines.append(prose.strip())
        claims = _extract_claims(prose)
        if claims:
            lines.append("")
            for kind, claim_text in claims:
                lines.append(f"{kind}: {claim_text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _extract_claims(text: str) -> list[tuple[str, str]]:
    claims: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    counts = {"Fact": 0, "Belief": 0, "Value": 0, "Precedent": 0}

    for sent in _sentences(text):
        lowered = sent.lower()
        cleaned = sent.strip().rstrip(".")
        if not cleaned:
            continue

        kind = ""
        if _is_precedent(lowered):
            kind = "Precedent"
        elif _is_belief(lowered):
            kind = "Belief"
        elif _is_value(lowered):
            kind = "Value"
        elif _is_fact(lowered):
            kind = "Fact"

        if not kind:
            continue
        if counts[kind] >= 1:
            continue
        key = (kind, cleaned.lower())
        if key in seen:
            continue
        seen.add(key)
        counts[kind] += 1
        claims.append((kind, cleaned))

    return claims


def _is_belief(text: str) -> bool:
    return any(k in text for k in [
        "i think", "we think", "likely", "probably", "maybe", "assume",
        "suspect", "expect", "hypothesis", "appears to",
    ])


def _is_value(text: str) -> bool:
    return any(k in text for k in [
        "important", "must", "non-negotiable", "priority", "prefer",
        "optimize for", "we care about", "should",
    ])


def _is_precedent(text: str) -> bool:
    return any(k in text for k in [
        "last time", "previous", "historically", "in the past", "before this",
        "again", "repeatedly", "prior ",
    ])


def _is_fact(text: str) -> bool:
    has_number = bool(re.search(r"\b\d+(?:\.\d+)?\b", text))
    concrete_verb = any(k in text for k in [" is ", " are ", " has ", " have ", " contains ", " includes "])
    uncertain = any(k in text for k in ["maybe", "likely", "probably", "might", "could"])
    return (has_number or concrete_verb) and not uncertain


def _load_memory_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        records = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
        return records

    data = json.loads(path.read_text())
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("records", "items", "data", "memories", "events", "nodes"):
            val = data.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
        return [data]
    return []


def _normalize_memory_record(record: dict[str, Any], adapter: str, idx: int) -> tuple[str, str]:
    title = (
        _pick_first(record, "title", "topic", "name", "id")
        or f"{adapter.title()} record {idx}"
    )
    text = ""

    if adapter == "mem0":
        text = _pick_first(record, "memory", "text", "value", "content", "summary") or ""
    elif adapter == "graphiti":
        text = _pick_first(record, "fact", "content", "summary", "text", "description") or ""
        src = _pick_first(record, "source", "source_node", "from")
        rel = _pick_first(record, "relation", "edge", "predicate")
        dst = _pick_first(record, "target", "target_node", "to")
        if src and rel and dst:
            relation_text = f"Relation path: {src} -[{rel}]-> {dst}."
            text = f"{text}\n{relation_text}".strip()
    else:  # arscontexta
        text = _pick_first(record, "summary", "note", "content", "text", "body", "memory") or ""

    if not text:
        text = json.dumps(record, ensure_ascii=True)

    tags = record.get("tags")
    if isinstance(tags, list) and tags:
        text = f"{text}\nTags: {', '.join(str(t) for t in tags)}"

    created = _pick_first(record, "created_at", "timestamp", "time")
    if created:
        text = f"{text}\nRecorded at: {created}"

    prose = _summarize(text, max_sentences=5)
    return str(title)[:96], prose


def _pick_first(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _observation_output_path(obs_dir: Path, filename: str) -> Path:
    obs_dir.mkdir(parents=True, exist_ok=True)
    candidate = obs_dir / filename
    if candidate.suffix != ".lore":
        candidate = candidate.with_suffix(".lore")
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for i in range(2, 1000):
        alt = obs_dir / f"{stem}-{i}{suffix}"
        if not alt.exists():
            return alt
    raise RuntimeError("Could not allocate output filename for observations")


def _slug(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-") or "observations"

