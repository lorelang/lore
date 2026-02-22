"""
Embeddings Compiler.

Generates chunked text with metadata optimized for embedding
and vector store ingestion. Each chunk is self-contained and
carries enough context for an LLM to reason over it after retrieval.
"""
from __future__ import annotations
import json
from ..models import Ontology, TaxonomyNode


def compile_embeddings(ontology: Ontology) -> str:
    """
    Compile ontology to embedding-ready chunks.

    Output format: JSON Lines (one JSON object per line).
    Each object has: id, type, text, metadata.
    """
    chunks: list[dict] = []
    name = ontology.manifest.name if ontology.manifest else "ontology"

    def _prov_metadata(obj):
        """Extract provenance fields as flat metadata dict entries."""
        meta = {}
        if hasattr(obj, 'provenance') and obj.provenance:
            if obj.provenance.source:
                meta["provenance_source"] = obj.provenance.source
            if obj.provenance.confidence is not None:
                meta["provenance_confidence"] = obj.provenance.confidence
            if obj.provenance.created:
                meta["provenance_created"] = obj.provenance.created
        if hasattr(obj, 'status') and obj.status:
            meta["status"] = obj.status
        return meta

    # Entity chunks
    for entity in ontology.entities:
        # Main entity chunk
        text_parts = [
            f"Entity: {entity.name}",
            entity.description,
        ]
        if entity.attributes:
            attr_list = ", ".join(
                f"{a.name} ({a.type})" for a in entity.attributes
            )
            text_parts.append(f"Attributes: {attr_list}")

        # Attribute details as a separate chunk
        if entity.attributes:
            attr_text = f"Attributes of {entity.name}:\n"
            for a in entity.attributes:
                attr_text += f"- {a.name} ({a.type}): {a.description}\n"
            chunks.append({
                "id": f"entity:{entity.name}:attributes",
                "type": "entity_attributes",
                "text": attr_text.strip(),
                "metadata": {"entity": entity.name, "source": str(entity.source_file)},
            })

        # Identity chunk
        if entity.identity:
            text_parts.append(f"Identity: {entity.identity}")

        entity_meta = {"entity": entity.name, "source": str(entity.source_file)}
        entity_meta.update(_prov_metadata(entity))
        chunks.append({
            "id": f"entity:{entity.name}",
            "type": "entity",
            "text": "\n".join(text_parts),
            "metadata": entity_meta,
        })

        # Lifecycle as separate chunk (rich prose)
        if entity.lifecycle:
            chunks.append({
                "id": f"entity:{entity.name}:lifecycle",
                "type": "entity_lifecycle",
                "text": f"Lifecycle of {entity.name}: {entity.lifecycle}",
                "metadata": {"entity": entity.name, "source": str(entity.source_file)},
            })

        # Notes as separate chunk
        if entity.notes:
            chunks.append({
                "id": f"entity:{entity.name}:notes",
                "type": "entity_notes",
                "text": f"Notes on {entity.name}: {entity.notes}",
                "metadata": {"entity": entity.name, "source": str(entity.source_file)},
            })

    # Relationship chunks
    for rel in ontology.all_relationships:
        text = (
            f"Relationship: {rel.name}\n"
            f"{rel.from_entity} → {rel.to_entity} ({rel.cardinality})\n"
            f"{rel.description}"
        )
        if rel.properties:
            props = ", ".join(f"{p.name}: {p.type}" for p in rel.properties)
            text += f"\nProperties: {props}"

        chunks.append({
            "id": f"relationship:{rel.name}",
            "type": "relationship",
            "text": text,
            "metadata": {
                "from_entity": rel.from_entity,
                "to_entity": rel.to_entity,
            },
        })

    # Traversal chunks
    for trav in ontology.all_traversals:
        chunks.append({
            "id": f"traversal:{trav.name}",
            "type": "traversal",
            "text": (
                f"Reasoning path: {trav.name}\n"
                f"Path: {trav.path}\n"
                f"Use: {trav.description}"
            ),
            "metadata": {"traversal": trav.name},
        })

    # Rule chunks
    for rule in ontology.all_rules:
        text_parts = [f"Rule: {rule.name}"]
        if rule.applies_to:
            text_parts.append(f"Applies to: {rule.applies_to}")
        if rule.severity:
            text_parts.append(f"Severity: {rule.severity}")
        if rule.trigger:
            text_parts.append(f"Trigger: {rule.trigger}")
        if rule.outputs:
            text_parts.append(f"Computes: {rule.outputs}")
        if rule.condition:
            text_parts.append(f"Condition: {rule.condition}")
        if rule.action:
            text_parts.append(f"Action: {rule.action}")
        if rule.prose:
            text_parts.append(rule.prose)

        chunks.append({
            "id": f"rule:{rule.name}",
            "type": "rule",
            "text": "\n".join(text_parts),
            "metadata": {
                "applies_to": rule.applies_to,
                "severity": rule.severity,
            },
        })

    # Taxonomy chunks (one per leaf path)
    for tax in ontology.taxonomies:
        if tax.root:
            _chunk_taxonomy(tax.root, [], tax.name, chunks)

        if tax.inheritance_rules:
            chunks.append({
                "id": f"taxonomy:{tax.name}:inheritance",
                "type": "taxonomy_rules",
                "text": (
                    f"Inheritance rules for {tax.name} taxonomy:\n"
                    f"{tax.inheritance_rules}"
                ),
                "metadata": {"taxonomy": tax.name},
            })

    # Glossary chunks (one per term)
    for entry in ontology.all_glossary_entries:
        chunks.append({
            "id": f"glossary:{entry.term}",
            "type": "glossary",
            "text": f"Definition of '{entry.term}': {entry.definition}",
            "metadata": {"term": entry.term},
        })

    # Observation chunks (one per observation)
    for of in ontology.observation_files:
        for obs in of.observations:
            obs_meta = {}
            if of.about:
                obs_meta["about"] = of.about
            if of.observed_by:
                obs_meta["observed_by"] = of.observed_by
            if of.date:
                obs_meta["date"] = of.date
            if of.confidence is not None:
                obs_meta["confidence"] = of.confidence
            if of.status:
                obs_meta["status"] = of.status
            obs_meta["source"] = str(of.source_file)
            chunks.append({
                "id": f"observation:{of.name}:{obs.heading}",
                "type": "observation",
                "text": f"Observation: {obs.heading}\n{obs.prose}",
                "metadata": obs_meta,
            })

    # Outcome chunks (one per outcome)
    for of in ontology.outcome_files:
        for outcome in of.outcomes:
            outcome_meta = {}
            if of.reviewed_by:
                outcome_meta["reviewed_by"] = of.reviewed_by
            if of.date:
                outcome_meta["date"] = of.date
            if outcome.refs:
                outcome_meta["refs"] = outcome.refs
            if outcome.takeaways:
                outcome_meta["takeaways"] = outcome.takeaways
            outcome_meta["source"] = str(of.source_file)
            text_parts = [f"Outcome: {outcome.heading}", outcome.prose]
            if outcome.takeaways:
                for t in outcome.takeaways:
                    text_parts.append(f"Takeaway: {t}")
            chunks.append({
                "id": f"outcome:{of.name}:{outcome.heading}",
                "type": "outcome",
                "text": "\n".join(text_parts),
                "metadata": outcome_meta,
            })

    # Output as JSON Lines
    return "\n".join(json.dumps(chunk) for chunk in chunks)


def _chunk_taxonomy(
    node: TaxonomyNode,
    path: list[str],
    taxonomy_name: str,
    chunks: list[dict],
):
    """Recursively create chunks for taxonomy nodes."""
    current_path = path + [node.name]

    if not node.children:
        # Leaf node — create a chunk with full path
        chunks.append({
            "id": f"taxonomy:{taxonomy_name}:{node.name}",
            "type": "taxonomy_leaf",
            "text": (
                f"Classification: {' > '.join(current_path)}\n"
                f"Tags: {', '.join(node.tags) if node.tags else 'none'}\n"
                f"{node.description}"
            ),
            "metadata": {
                "taxonomy": taxonomy_name,
                "path": current_path,
                "tags": node.tags,
            },
        })
    else:
        # Branch node
        child_names = [c.name for c in node.children]
        chunks.append({
            "id": f"taxonomy:{taxonomy_name}:{node.name}",
            "type": "taxonomy_branch",
            "text": (
                f"Category: {' > '.join(current_path)}\n"
                f"Contains: {', '.join(child_names)}\n"
                f"Tags: {', '.join(node.tags) if node.tags else 'none'}\n"
                f"{node.description}"
            ),
            "metadata": {
                "taxonomy": taxonomy_name,
                "path": current_path,
                "tags": node.tags,
            },
        })

        for child in node.children:
            _chunk_taxonomy(child, current_path, taxonomy_name, chunks)
