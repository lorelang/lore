"""
Lore Curator.

Opinionated health checks that go beyond validation.
Validation asks "is this correct?" — curation asks "is this good?"

Four focused jobs:
  - staleness:   Flag knowledge that's past its freshness window
  - coverage:    Find gaps — missing Notes, orphaned entities, undocumented relationships
  - consistency: Find contradictions — rules referencing missing attributes, taxonomy/enum drift
  - summarize:   Generate a natural-language health digest (optional LLM)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
import re
from typing import Callable, Optional
from pathlib import Path
from .models import Ontology


@dataclass
class CurationFinding:
    """A single issue found by a curation job."""
    job: str                # "staleness" | "coverage" | "consistency"
    severity: str           # "warning" | "info"
    message: str
    source: str = ""        # file path or location
    suggestion: str = ""    # optional fix suggestion


@dataclass
class CurationReport:
    """Results from a single curation job."""
    job: str
    findings: list[CurationFinding] = field(default_factory=list)
    summary: str = ""

    @property
    def warnings(self) -> list[CurationFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def infos(self) -> list[CurationFinding]:
        return [f for f in self.findings if f.severity == "info"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_staleness(staleness_str: str) -> Optional[timedelta]:
    """Parse a staleness string like '90d' into a timedelta."""
    if not staleness_str:
        return None
    m = re.match(r"^(\d+)([dhm])$", staleness_str.strip())
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    if unit == "d":
        return timedelta(days=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "m":
        return timedelta(days=value * 30)  # approximate
    return None


def _parse_date(date_str: str) -> Optional[date]:
    """Parse a YYYY-MM-DD date string."""
    if not date_str:
        return None
    try:
        parts = date_str.strip().split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def _days_old(created: str, today: Optional[date] = None) -> Optional[int]:
    """How many days old is this knowledge?"""
    d = _parse_date(created)
    if d is None:
        return None
    ref = today or date.today()
    return (ref - d).days


# ---------------------------------------------------------------------------
# Job 1: Staleness
# ---------------------------------------------------------------------------

def curate_staleness(ontology: Ontology, today: Optional[date] = None) -> CurationReport:
    """
    Flag knowledge past its freshness window.

    Uses evolution.staleness from manifest (e.g., '90d').
    Falls back to 180 days if no staleness configured.
    """
    report = CurationReport(job="staleness")

    # Determine threshold
    threshold = None
    if ontology.manifest and ontology.manifest.evolution:
        threshold = _parse_staleness(ontology.manifest.evolution.staleness)
    if threshold is None:
        threshold = timedelta(days=180)  # sensible default

    threshold_days = threshold.days
    ref_date = today or date.today()

    # Check entities
    for entity in ontology.entities:
        if entity.provenance and entity.provenance.created:
            age = _days_old(entity.provenance.created, ref_date)
            if age is not None and age > threshold_days:
                report.findings.append(CurationFinding(
                    job="staleness", severity="warning",
                    message=f"Entity '{entity.name}' is {age} days old (threshold: {threshold_days}d)",
                    source=str(entity.source_file) if entity.source_file else "",
                    suggestion=f"Review and refresh — authored by {entity.provenance.author}",
                ))
        elif entity.provenance is None:
            report.findings.append(CurationFinding(
                job="staleness", severity="info",
                message=f"Entity '{entity.name}' has no provenance — age unknown",
                source=str(entity.source_file) if entity.source_file else "",
                suggestion="Add provenance.created date to track freshness",
            ))

    # Check observation files
    for of in ontology.observation_files:
        if of.date:
            age = _days_old(of.date, ref_date)
            if age is not None and age > threshold_days:
                report.findings.append(CurationFinding(
                    job="staleness", severity="warning",
                    message=f"Observation '{of.name}' is {age} days old (threshold: {threshold_days}d)",
                    source=str(of.source_file) if of.source_file else "",
                    suggestion=f"Observations decay fast — refresh or deprecate (by {of.observed_by})",
                ))

    # Check rule files
    for rf in ontology.rule_files:
        if rf.provenance and rf.provenance.created:
            age = _days_old(rf.provenance.created, ref_date)
            if age is not None and age > threshold_days:
                report.findings.append(CurationFinding(
                    job="staleness", severity="warning",
                    message=f"Rule file '{rf.domain}' is {age} days old (threshold: {threshold_days}d)",
                    source=str(rf.source_file) if rf.source_file else "",
                    suggestion=f"Rules should be validated against recent outcomes",
                ))

    # Check relationship files
    for rf in ontology.relationship_files:
        if rf.provenance and rf.provenance.created:
            age = _days_old(rf.provenance.created, ref_date)
            if age is not None and age > threshold_days:
                report.findings.append(CurationFinding(
                    job="staleness", severity="warning",
                    message=f"Relationship file '{rf.domain}' is {age} days old (threshold: {threshold_days}d)",
                    source=str(rf.source_file) if rf.source_file else "",
                ))

    # Check taxonomies
    for tax in ontology.taxonomies:
        if tax.provenance and tax.provenance.created:
            age = _days_old(tax.provenance.created, ref_date)
            if age is not None and age > threshold_days:
                report.findings.append(CurationFinding(
                    job="staleness", severity="warning",
                    message=f"Taxonomy '{tax.name}' is {age} days old (threshold: {threshold_days}d)",
                    source=str(tax.source_file) if tax.source_file else "",
                ))

    # Summary
    stale = len(report.warnings)
    undated = len(report.infos)
    total_items = (len(ontology.entities) + len(ontology.observation_files) +
                   len(ontology.rule_files) + len(ontology.relationship_files) +
                   len(ontology.taxonomies))
    fresh = total_items - stale - undated
    report.summary = f"{stale} stale, {undated} undated, {fresh} fresh (threshold: {threshold_days}d)"
    return report


# ---------------------------------------------------------------------------
# Job 2: Coverage
# ---------------------------------------------------------------------------

def curate_coverage(ontology: Ontology) -> CurationReport:
    """
    Find gaps in ontology completeness.

    Checks for missing documentation, orphaned entities,
    undocumented relationships, and observation blind spots.
    """
    report = CurationReport(job="coverage")

    # Entities without Notes
    for entity in ontology.entities:
        if not entity.notes or not entity.notes.strip():
            report.findings.append(CurationFinding(
                job="coverage", severity="warning",
                message=f"Entity '{entity.name}' has no Notes section",
                source=str(entity.source_file) if entity.source_file else "",
                suggestion=("Agents lack context for reasoning about this entity. "
                            "Add a ## Notes section with domain knowledge, edge cases, "
                            "and guidance for AI interpretation."),
            ))

    # Entities without Identity
    for entity in ontology.entities:
        if not entity.identity or not entity.identity.strip():
            report.findings.append(CurationFinding(
                job="coverage", severity="info",
                message=f"Entity '{entity.name}' has no Identity section",
                source=str(entity.source_file) if entity.source_file else "",
                suggestion="Add ## Identity to define what makes this entity unique.",
            ))

    # Orphaned entities (not in any relationship)
    connected_entities = set()
    for rel in ontology.all_relationships:
        connected_entities.add(rel.from_entity)
        connected_entities.add(rel.to_entity)

    for entity in ontology.entities:
        if entity.name not in connected_entities:
            report.findings.append(CurationFinding(
                job="coverage", severity="warning",
                message=f"Entity '{entity.name}' is not in any relationship (orphaned)",
                source=str(entity.source_file) if entity.source_file else "",
                suggestion=("The agent can't traverse to or from this entity. "
                            "Add relationships or consider if this entity belongs "
                            "in the ontology."),
            ))

    # Relationships without descriptions
    for rel in ontology.all_relationships:
        if not rel.description or not rel.description.strip():
            report.findings.append(CurationFinding(
                job="coverage", severity="info",
                message=f"Relationship '{rel.name}' ({rel.from_entity} -> {rel.to_entity}) has no description",
                suggestion="Add a description to help agents understand the semantics.",
            ))

    # Entities with no observations about them
    observed_entities = set()
    for of in ontology.observation_files:
        if of.about:
            observed_entities.add(of.about)

    for entity in ontology.entities:
        if entity.name not in observed_entities:
            report.findings.append(CurationFinding(
                job="coverage", severity="info",
                message=f"Entity '{entity.name}' has no observations referencing it",
                source=str(entity.source_file) if entity.source_file else "",
                suggestion="No agent has recorded field notes about this entity yet.",
            ))

    # Traversals — check if all entities in path exist
    for trav in ontology.all_traversals:
        for entity_name in ontology.entity_names:
            pass  # traversal paths are free-form strings, skip deep validation

    # Coverage score
    total_entities = len(ontology.entities)
    if total_entities > 0:
        entities_with_notes = sum(1 for e in ontology.entities if e.notes and e.notes.strip())
        entities_with_identity = sum(1 for e in ontology.entities if e.identity and e.identity.strip())
        entities_connected = sum(1 for e in ontology.entities if e.name in connected_entities)

        notes_pct = entities_with_notes / total_entities
        identity_pct = entities_with_identity / total_entities
        connected_pct = entities_connected / total_entities

        coverage_score = int((notes_pct * 0.4 + identity_pct * 0.3 + connected_pct * 0.3) * 100)
        report.summary = (f"Coverage: {coverage_score}% — "
                          f"{entities_with_notes}/{total_entities} have Notes, "
                          f"{entities_with_identity}/{total_entities} have Identity, "
                          f"{entities_connected}/{total_entities} connected")
    else:
        report.summary = "No entities to check"

    return report


# ---------------------------------------------------------------------------
# Job 3: Consistency
# ---------------------------------------------------------------------------

def curate_consistency(ontology: Ontology) -> CurationReport:
    """
    Find contradictions and drift in the ontology.

    Checks for rules referencing nonexistent attributes,
    taxonomy/enum mismatches, and observation/outcome drift.
    """
    report = CurationReport(job="consistency")

    # Build attribute lookup: entity_name -> set of attribute names
    entity_attrs: dict[str, set[str]] = {}
    for entity in ontology.entities:
        entity_attrs[entity.name] = {a.name for a in entity.attributes}

    # Rules referencing attributes not on their applies_to entity
    for rule in ontology.all_rules:
        if not rule.applies_to or rule.applies_to not in entity_attrs:
            continue

        attrs = entity_attrs[rule.applies_to]
        # Scan condition and action for entity.attribute patterns
        for block_name, block in [("condition", rule.condition), ("action", rule.action)]:
            if not block:
                continue
            # Look for patterns like entity.attribute or just attribute names
            # Match word.word patterns that could be entity.attribute refs
            refs = re.findall(r'(\w+)\.(\w+)', block)
            for entity_ref, attr_ref in refs:
                # Check if entity_ref matches applies_to or a known entity
                if entity_ref.lower() == rule.applies_to.lower():
                    if attr_ref not in attrs and attr_ref not in ("trend", "status"):
                        report.findings.append(CurationFinding(
                            job="consistency", severity="warning",
                            message=(f"Rule '{rule.name}' {block_name} references "
                                     f"'{entity_ref}.{attr_ref}' but '{rule.applies_to}' "
                                     f"has no attribute '{attr_ref}'"),
                            suggestion=f"Known attributes: {', '.join(sorted(attrs))}",
                        ))

    # Taxonomy applied_to vs entity enum values
    for tax in ontology.taxonomies:
        if not tax.applied_to or "." not in tax.applied_to:
            continue
        entity_name, attr_name = tax.applied_to.split(".", 1)
        if entity_name not in entity_attrs:
            continue
        if attr_name not in entity_attrs[entity_name]:
            report.findings.append(CurationFinding(
                job="consistency", severity="warning",
                message=(f"Taxonomy '{tax.name}' applied_to '{tax.applied_to}' "
                         f"but '{entity_name}' has no attribute '{attr_name}'"),
            ))

    # High-confidence observations that led to wrong outcomes
    # Build a map of observation refs → outcomes
    for of in ontology.outcome_files:
        for outcome in of.outcomes:
            heading_lower = outcome.heading.lower()
            is_wrong = any(word in heading_lower for word in
                          ["false positive", "incorrect", "wrong", "missed", "failed"])
            if is_wrong and outcome.refs:
                # Find the referenced observation's confidence
                for ref in outcome.refs:
                    # ref format: observations/file.lore#heading
                    for obs_file in ontology.observation_files:
                        if obs_file.source_file and ref.startswith("observations/"):
                            ref_filename = ref.split("#")[0].replace("observations/", "")
                            if (obs_file.source_file.name == ref_filename
                                    and obs_file.confidence is not None
                                    and obs_file.confidence >= 0.7):
                                report.findings.append(CurationFinding(
                                    job="consistency", severity="info",
                                    message=(f"Observation '{obs_file.name}' had confidence "
                                             f"{obs_file.confidence} but outcome "
                                             f"'{outcome.heading}' suggests it was wrong"),
                                    suggestion="Consider lowering default confidence for this observer",
                                ))

    # Observation contradictions: two observations about the same entity
    # with opposing signal keywords
    _POSITIVE_SIGNALS = {
        "expansion", "growth", "increase", "uptick", "readiness",
        "adoption", "engagement", "upgrade", "upsell", "healthy",
        "renewed", "active", "improving", "positive",
    }
    _NEGATIVE_SIGNALS = {
        "churn", "decline", "decrease", "contraction", "risk",
        "disengagement", "downgrade", "cancellation", "inactive",
        "deteriorating", "negative", "attrition", "drop", "loss",
    }

    # Group observations by entity
    obs_by_entity: dict[str, list[tuple[str, str, str]]] = {}  # entity -> [(heading, prose, file)]
    for of in ontology.observation_files:
        if of.about:
            entity_key = of.about
            file_name = str(of.source_file) if of.source_file else of.name
            for obs in of.observations:
                obs_by_entity.setdefault(entity_key, []).append(
                    (obs.heading, obs.prose, file_name)
                )

    for entity_key, obs_list in obs_by_entity.items():
        if len(obs_list) < 2:
            continue
        # Check each pair for opposing signals
        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                h1, p1, f1 = obs_list[i]
                h2, p2, f2 = obs_list[j]
                text1 = (h1 + " " + p1).lower()
                text2 = (h2 + " " + p2).lower()
                pos1 = any(s in text1 for s in _POSITIVE_SIGNALS)
                neg1 = any(s in text1 for s in _NEGATIVE_SIGNALS)
                pos2 = any(s in text2 for s in _POSITIVE_SIGNALS)
                neg2 = any(s in text2 for s in _NEGATIVE_SIGNALS)
                # Contradiction: one is positive-only, other is negative-only
                if (pos1 and not neg1 and neg2 and not pos2) or \
                   (neg1 and not pos1 and pos2 and not neg2):
                    report.findings.append(CurationFinding(
                        job="consistency", severity="warning",
                        message=(f"Possible contradiction about '{entity_key}': "
                                 f"'{h1}' vs '{h2}'"),
                        source=f"{f1}, {f2}",
                        suggestion=(f"Review both observations — they contain "
                                    f"opposing signals about the same entity"),
                    ))

    # Entities referenced in rules but not defined
    entity_names = ontology.entity_names
    for rule in ontology.all_rules:
        if rule.applies_to and rule.applies_to not in entity_names:
            # Already caught by validator, but note it for consistency
            pass

    # Summary
    n = len(report.findings)
    report.summary = f"{n} consistency issue{'s' if n != 1 else ''} found"
    return report


# ---------------------------------------------------------------------------
# Job 4: Summarize
# ---------------------------------------------------------------------------

def curate_summarize(
    ontology: Ontology,
    reports: list[CurationReport],
    llm_fn: Optional[Callable[[str], str]] = None,
) -> CurationReport:
    """
    Generate a natural-language health digest.

    If llm_fn is provided, uses it to generate a polished summary.
    Otherwise falls back to a template-based summary.

    llm_fn signature: takes a prompt string, returns a response string.
    """
    report = CurationReport(job="summarize")

    # Collect all findings
    all_warnings = []
    all_infos = []
    for r in reports:
        all_warnings.extend(r.warnings)
        all_infos.extend(r.infos)

    # Build stats context
    name = ontology.manifest.name if ontology.manifest else "unnamed"
    version = ontology.manifest.version if ontology.manifest else "?"
    n_entities = len(ontology.entities)
    n_attrs = sum(len(e.attributes) for e in ontology.entities)
    n_rels = len(ontology.all_relationships)
    n_rules = len(ontology.all_rules)
    n_obs = len(ontology.all_observations)
    n_outcomes = len(ontology.all_outcomes)

    # Build the findings summary text
    findings_text = ""
    for r in reports:
        if r.findings:
            findings_text += f"\n{r.job}: {r.summary}\n"
            for f in r.findings:
                icon = "⚠" if f.severity == "warning" else "ℹ"
                findings_text += f"  {icon} {f.message}\n"

    if llm_fn is not None:
        # Use LLM for polished summary
        prompt = (
            f"You are a domain ontology health advisor. Given the health check "
            f"results below for the '{name}' ontology (v{version}), write a "
            f"concise 2-3 sentence executive summary and list the top 3 action "
            f"items in priority order.\n\n"
            f"Ontology stats: {n_entities} entities, {n_attrs} attributes, "
            f"{n_rels} relationships, {n_rules} rules, {n_obs} observations, "
            f"{n_outcomes} outcomes.\n\n"
            f"Health check findings:\n{findings_text}\n\n"
            f"Write the summary in a direct, actionable style. No preamble."
        )
        try:
            llm_response = llm_fn(prompt)
            report.summary = llm_response.strip()
        except Exception:
            # Fall through to template if LLM fails
            report.summary = _template_summary(
                name, version, n_entities, n_attrs, n_rels,
                all_warnings, all_infos, reports,
            )
    else:
        # Template fallback
        report.summary = _template_summary(
            name, version, n_entities, n_attrs, n_rels,
            all_warnings, all_infos, reports,
        )

    return report


def _template_summary(
    name: str, version: str, n_entities: int, n_attrs: int, n_rels: int,
    all_warnings: list[CurationFinding], all_infos: list[CurationFinding],
    reports: list[CurationReport],
) -> str:
    """Generate a template-based summary without LLM."""
    lines = [
        f"{name} (v{version}): {n_entities} entities, {n_attrs} attributes, {n_rels} relationships.",
        "",
    ]

    if not all_warnings and not all_infos:
        lines.append("No issues found. Ontology is in good shape.")
    else:
        if all_warnings:
            lines.append(f"{len(all_warnings)} warning(s):")
            # Group by job
            by_job: dict[str, list[CurationFinding]] = {}
            for w in all_warnings:
                by_job.setdefault(w.job, []).append(w)
            for job, findings in by_job.items():
                lines.append(f"  {job}: {len(findings)} issue(s)")

        if all_infos:
            lines.append(f"{len(all_infos)} improvement suggestion(s).")

        # Top 3 actions (prioritize warnings)
        top_actions = all_warnings[:3]
        if len(top_actions) < 3:
            top_actions.extend(all_infos[:3 - len(top_actions)])

        if top_actions:
            lines.append("")
            lines.append("Top actions:")
            for i, action in enumerate(top_actions, 1):
                text = action.suggestion if action.suggestion else action.message
                lines.append(f"  {i}. {text}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Job 5: Index freshness
# ---------------------------------------------------------------------------

def curate_index(ontology: Ontology, root_dir: Optional[Path] = None,
                 today: Optional[date] = None) -> CurationReport:
    """
    Check if INDEX.lore files exist and are up-to-date.

    INDEX.lore files are routing guides for AI agents navigating the ontology.
    This job checks whether they exist and whether their content matches the
    current ontology state.
    """
    report = CurationReport(job="index")

    if root_dir is None:
        report.summary = "No root directory provided — skipping index check"
        return report

    root = Path(root_dir)
    ref = today or date.today()

    # Check root INDEX.lore
    root_index = root / "INDEX.lore"
    if not root_index.exists():
        report.findings.append(CurationFinding(
            job="index", severity="warning",
            message="Root INDEX.lore is missing",
            source=str(root),
            suggestion="Run `lore index .` to generate INDEX.lore files",
        ))
    else:
        # Check if stale (generated date vs entity count mismatch)
        content = root_index.read_text()
        entity_count = len(ontology.entities)
        if f"{entity_count} entities" not in content:
            report.findings.append(CurationFinding(
                job="index", severity="warning",
                message="Root INDEX.lore appears stale (entity count mismatch)",
                source=str(root_index),
                suggestion="Run `lore index .` to regenerate",
            ))

    # Check directory-level INDEX.lore files
    known_dirs = ["entities", "relationships", "rules", "taxonomies",
                  "glossary", "views", "observations", "outcomes"]

    for dirname in known_dirs:
        dir_path = root / dirname
        if not dir_path.exists():
            continue
        lore_files = [f for f in dir_path.glob("*.lore") if f.name != "INDEX.lore"]
        if not lore_files:
            continue
        index_file = dir_path / "INDEX.lore"
        if not index_file.exists():
            report.findings.append(CurationFinding(
                job="index", severity="info",
                message=f"{dirname}/INDEX.lore is missing ({len(lore_files)} files unindexed)",
                source=str(dir_path),
                suggestion="Run `lore index .` to generate",
            ))
        else:
            # Check if all files are mentioned
            content = index_file.read_text()
            missing = [f.name for f in lore_files if f.name not in content]
            if missing:
                report.findings.append(CurationFinding(
                    job="index", severity="warning",
                    message=f"{dirname}/INDEX.lore is stale — missing: {', '.join(missing)}",
                    source=str(index_file),
                    suggestion="Run `lore index .` to regenerate",
                ))

    n = len(report.findings)
    if n == 0:
        report.summary = "All INDEX.lore files are present and up-to-date"
    else:
        report.summary = f"{n} index issue{'s' if n != 1 else ''} found"
    return report


# ---------------------------------------------------------------------------
# Run all jobs
# ---------------------------------------------------------------------------

def curate_all(
    ontology: Ontology,
    today: Optional[date] = None,
    llm_fn: Optional[Callable[[str], str]] = None,
    root_dir: Optional[Path] = None,
) -> list[CurationReport]:
    """Run all curation jobs and return reports."""
    staleness = curate_staleness(ontology, today=today)
    coverage = curate_coverage(ontology)
    consistency = curate_consistency(ontology)
    index = curate_index(ontology, root_dir=root_dir, today=today)
    summary = curate_summarize(ontology,
                               [staleness, coverage, consistency, index],
                               llm_fn=llm_fn)
    return [staleness, coverage, consistency, index, summary]
