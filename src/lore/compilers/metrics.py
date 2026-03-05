"""
Metrics Compiler.

Exports ontology health metrics as JSON for dashboards:
entity coverage scores, staleness distribution, relationship
density, observation recency.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from ..models import Ontology


def compile_metrics(ontology: Ontology) -> str:
    """Compile ontology health metrics to JSON."""
    metrics = _compute_metrics(ontology)
    return json.dumps(metrics, indent=2)


def _compute_metrics(ontology: Ontology) -> dict:
    """Compute all metrics for the ontology."""
    ont = ontology
    today = date.today()

    # Basic counts
    entity_count = len(ont.entities)
    relationship_count = len(ont.all_relationships)
    rule_count = len(ont.all_rules)
    taxonomy_count = len(ont.taxonomies)
    glossary_count = len(ont.all_glossary_entries)
    observation_count = len(ont.all_observations)
    outcome_count = len(ont.all_outcomes)
    claim_count = len(ont.all_claims)
    decision_count = len(ont.all_decisions)

    # Entity coverage scores
    coverage = _entity_coverage(ont)

    # Status distribution
    status_dist = _status_distribution(ont)

    # Staleness distribution
    staleness = _staleness_distribution(ont, today)

    # Relationship density
    rel_density = (
        (2 * relationship_count) / entity_count
        if entity_count > 0 else 0.0
    )

    # Observation recency
    obs_recency = _observation_recency(ont, today)

    return {
        "ontology": {
            "name": ont.manifest.name if ont.manifest else "",
            "version": ont.manifest.version if ont.manifest else "",
        },
        "counts": {
            "entities": entity_count,
            "attributes": sum(len(e.attributes) for e in ont.entities),
            "relationships": relationship_count,
            "traversals": len(ont.all_traversals),
            "rules": rule_count,
            "taxonomies": taxonomy_count,
            "glossary_terms": glossary_count,
            "observations": observation_count,
            "outcomes": outcome_count,
            "claims": claim_count,
            "decisions": decision_count,
            "views": len(ont.views),
        },
        "coverage": coverage,
        "status_distribution": status_dist,
        "staleness": staleness,
        "relationship_density": round(rel_density, 2),
        "observation_recency": obs_recency,
    }


def _entity_coverage(ont: Ontology) -> dict:
    """Score each entity's documentation completeness."""
    scores: dict[str, float] = {}
    for entity in ont.entities:
        score = 0.0
        total = 5.0  # 5 possible sections

        if entity.description:
            score += 1.0
        if entity.attributes:
            score += 1.0
        if entity.identity:
            score += 1.0
        if entity.lifecycle:
            score += 1.0
        if entity.notes:
            score += 1.0

        scores[entity.name] = round(score / total, 2)

    avg = round(sum(scores.values()) / len(scores), 2) if scores else 0.0
    return {
        "entity_scores": scores,
        "average": avg,
    }


def _status_distribution(ont: Ontology) -> dict:
    """Count entities by status."""
    dist: dict[str, int] = {}
    for entity in ont.entities:
        status = entity.status or "unset"
        dist[status] = dist.get(status, 0) + 1
    return dist


def _staleness_distribution(ont: Ontology, today: date) -> dict:
    """Categorize entities by age buckets."""
    buckets = {"fresh": 0, "aging": 0, "stale": 0, "unknown": 0}

    for entity in ont.entities:
        if entity.provenance and entity.provenance.created:
            try:
                created = date.fromisoformat(entity.provenance.created)
                age_days = (today - created).days
                if age_days <= 30:
                    buckets["fresh"] += 1
                elif age_days <= 90:
                    buckets["aging"] += 1
                else:
                    buckets["stale"] += 1
            except ValueError:
                buckets["unknown"] += 1
        else:
            buckets["unknown"] += 1

    return buckets


def _observation_recency(ont: Ontology, today: date) -> dict:
    """Analyze observation dates."""
    dates: list[int] = []
    for of in ont.observation_files:
        if of.date:
            try:
                obs_date = date.fromisoformat(of.date)
                dates.append((today - obs_date).days)
            except ValueError:
                pass

    if not dates:
        return {"total": 0, "newest_days_ago": None, "oldest_days_ago": None,
                "median_days_ago": None}

    dates.sort()
    median_idx = len(dates) // 2
    return {
        "total": len(dates),
        "newest_days_ago": dates[0],
        "oldest_days_ago": dates[-1],
        "median_days_ago": dates[median_idx],
    }
