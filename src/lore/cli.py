"""
Lore CLI.

Command-line interface for parsing, validating, compiling,
and inspecting ontologies defined in .lore format.
"""
from __future__ import annotations
import argparse
import inspect
import re
import sys
from datetime import date
from pathlib import Path
from .parser import parse_ontology
from .validator import validate, Severity
from .models import TaxonomyNode
from .plugins import (
    available_compilers, available_curators,
    resolve_compiler, resolve_curator,
)


BUILTIN_COMPILE_TARGETS = {
    "neo4j", "json", "jsonld", "agent", "embeddings", "mermaid", "palantir",
}

BUILTIN_CURATION_JOBS = {"staleness", "coverage", "consistency", "index", "summarize", "all"}


def main():
    parser = argparse.ArgumentParser(
        prog="lore",
        description="Lore — human-readable ontology toolkit",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init
    p_init = subparsers.add_parser("init", help="Scaffold a new ontology directory")
    p_init.add_argument("dir", help="Directory to create")
    p_init.add_argument("--name", help="Ontology name (default: directory name)")
    p_init.add_argument("--domain", default="", help="Domain description")

    # setup
    p_setup = subparsers.add_parser(
        "setup",
        aliases=["/setup", "lore:setup", "/lore:setup"],
        help="AI-first domain setup scaffold",
    )
    p_setup.add_argument("dir", help="Directory to create")
    p_setup.add_argument("--name", help="Ontology name (default: directory name)")
    p_setup.add_argument("--domain", default="", help="Domain description")
    p_setup.add_argument("--maintainer", default="Domain Team",
                         help="Primary maintainer name")
    p_setup.add_argument("--role", default="Domain Owner",
                         help="Primary maintainer role")
    p_setup.add_argument(
        "--proposals", default="review-required",
        choices=["open", "review-required", "closed"],
        help="Evolution proposal mode",
    )
    p_setup.add_argument(
        "--staleness", default="45d",
        help="Freshness window (e.g., 30d, 12h, 3m)",
    )

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest transcripts or memory exports")
    ingest_sub = p_ingest.add_subparsers(dest="ingest_type", help="Ingestion source type")

    p_ingest_transcript = ingest_sub.add_parser("transcript", help="Ingest transcript file into observations/")
    p_ingest_transcript.add_argument("dir", help="Ontology directory")
    p_ingest_transcript.add_argument("--input", required=True, help="Transcript file path")
    p_ingest_transcript.add_argument("--about", required=True, help="Entity name for observations.about")
    p_ingest_transcript.add_argument("--name", help="Observations collection name")
    p_ingest_transcript.add_argument("--observed-by", default="transcript-ingest-agent",
                                     help="Observer id for frontmatter")
    p_ingest_transcript.add_argument("--confidence", type=float, default=0.65,
                                     help="Confidence score [0.0..1.0]")
    p_ingest_transcript.add_argument("--source", default="imported",
                                     help="Provenance source label")
    p_ingest_transcript.add_argument("--date", help="Observation date YYYY-MM-DD")
    p_ingest_transcript.add_argument("--output", help="Output filename in observations/")
    p_ingest_transcript.add_argument("--max-sections", type=int, default=8,
                                     help="Maximum transcript sections to emit")

    p_ingest_memory = ingest_sub.add_parser("memory", help="Ingest memory export JSON/JSONL into observations/")
    p_ingest_memory.add_argument("dir", help="Ontology directory")
    p_ingest_memory.add_argument("--adapter", required=True,
                                 choices=["arscontexta", "mem0", "graphiti"],
                                 help="Memory export adapter schema")
    p_ingest_memory.add_argument("--input", required=True, help="Memory export file path (.json or .jsonl)")
    p_ingest_memory.add_argument("--about", required=True, help="Entity name for observations.about")
    p_ingest_memory.add_argument("--name", help="Observations collection name")
    p_ingest_memory.add_argument("--observed-by", help="Observer id for frontmatter")
    p_ingest_memory.add_argument("--confidence", type=float, default=0.60,
                                 help="Confidence score [0.0..1.0]")
    p_ingest_memory.add_argument("--source", default="imported",
                                 help="Provenance source label")
    p_ingest_memory.add_argument("--date", help="Observation date YYYY-MM-DD")
    p_ingest_memory.add_argument("--output", help="Output filename in observations/")
    p_ingest_memory.add_argument("--max-sections", type=int, default=12,
                                 help="Maximum memory records to emit")

    # review
    p_review = subparsers.add_parser("review", help="Review generated proposal files")
    p_review.add_argument("path", help="Proposal file path or proposals directory")
    p_review.add_argument("--decision", required=True, choices=["accept", "reject"],
                          help="Review decision")
    p_review.add_argument("--reviewer", required=True, help="Reviewer identity")
    p_review.add_argument("--note", default="", help="Optional review note")
    p_review.add_argument("--all", action="store_true",
                          help="Include already-reviewed files when path is a directory")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate an ontology")
    p_validate.add_argument("dir", help="Ontology directory")

    # compile
    p_compile = subparsers.add_parser("compile", help="Compile to target format")
    p_compile.add_argument("dir", help="Ontology directory")
    p_compile.add_argument(
        "-t", "--target", required=True,
        help=("Compilation target (built-ins: neo4j, json, jsonld, agent, "
              "embeddings, mermaid, palantir; plus plugins from lore.yaml)"),
    )
    p_compile.add_argument("-o", "--output", help="Output file (default: stdout)")
    p_compile.add_argument("--view", help="Scope to a specific view (agent target only)")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show ontology statistics")
    p_stats.add_argument("dir", help="Ontology directory")

    # viz
    p_viz = subparsers.add_parser("viz", help="ASCII visualization of entity graph")
    p_viz.add_argument("dir", help="Ontology directory")

    # evolve
    p_evolve = subparsers.add_parser("evolve", help="Generate improvement proposals from outcomes")
    p_evolve.add_argument("dir", help="Ontology directory")
    p_evolve.add_argument("-o", "--output", help="Proposals output directory (default: <dir>/proposals)")

    # curate
    p_curate = subparsers.add_parser("curate", help="Run curation health checks")
    p_curate.add_argument("dir", help="Ontology directory")
    p_curate.add_argument(
        "--job", default="all",
        help=("Curation job (built-ins: staleness, coverage, consistency, index, "
              "summarize, all; plus plugin curators from lore.yaml)"),
    )
    p_curate.add_argument("--dry-run", action="store_true",
                          help="Report only, don't generate proposal files")

    # index
    p_index = subparsers.add_parser("index", help="Generate INDEX.lore routing files")
    p_index.add_argument("dir", help="Ontology directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        cmd_init(args.dir, getattr(args, 'name', None), getattr(args, 'domain', ''))
    elif args.command in {"setup", "/setup", "lore:setup", "/lore:setup"}:
        cmd_setup(
            args.dir,
            getattr(args, 'name', None),
            getattr(args, 'domain', ''),
            args.maintainer,
            args.role,
            args.proposals,
            args.staleness,
        )
    elif args.command == "ingest":
        if args.ingest_type == "transcript":
            cmd_ingest_transcript(
                args.dir,
                args.input,
                args.about,
                name=getattr(args, "name", None),
                observed_by=getattr(args, "observed_by", "transcript-ingest-agent"),
                confidence=getattr(args, "confidence", 0.65),
                source=getattr(args, "source", "imported"),
                date_str=getattr(args, "date", None),
                output=getattr(args, "output", None),
                max_sections=getattr(args, "max_sections", 8),
            )
        elif args.ingest_type == "memory":
            cmd_ingest_memory(
                args.dir,
                args.adapter,
                args.input,
                args.about,
                name=getattr(args, "name", None),
                observed_by=getattr(args, "observed_by", None),
                confidence=getattr(args, "confidence", 0.60),
                source=getattr(args, "source", "imported"),
                date_str=getattr(args, "date", None),
                output=getattr(args, "output", None),
                max_sections=getattr(args, "max_sections", 12),
            )
        else:
            p_ingest.print_help()
            sys.exit(1)
    elif args.command == "review":
        cmd_review(
            args.path,
            decision=args.decision,
            reviewer=args.reviewer,
            note=getattr(args, "note", ""),
            include_all=getattr(args, "all", False),
        )
    elif args.command == "validate":
        cmd_validate(args.dir)
    elif args.command == "compile":
        cmd_compile(args.dir, args.target, args.output, getattr(args, 'view', None))
    elif args.command == "stats":
        cmd_stats(args.dir)
    elif args.command == "viz":
        cmd_viz(args.dir)
    elif args.command == "evolve":
        cmd_evolve(args.dir, getattr(args, 'output', None))
    elif args.command == "curate":
        cmd_curate(args.dir, args.job, getattr(args, 'dry_run', False))
    elif args.command == "index":
        cmd_index(args.dir)


def cmd_init(directory: str, name: str | None, domain: str):
    """Scaffold a new ontology directory."""
    root = Path(directory)
    ont_name = name or root.name

    _ensure_empty_target(root, directory)

    root.mkdir(parents=True, exist_ok=True)

    # lore.yaml manifest
    manifest = (
        f"name: {ont_name}\n"
        f"version: 0.2.0\n"
        f"description: >\n"
        f"  {ont_name} domain ontology.\n"
    )
    if domain:
        manifest += f"domain: {domain}\n"
    manifest += (
        "\n"
        "evolution:\n"
        "  proposals: open\n"
        "  staleness: 90d\n"
    )
    (root / "lore.yaml").write_text(manifest)

    # Core directories
    for d in ["entities", "relationships", "rules", "taxonomies",
              "glossary", "views", "observations", "outcomes"]:
        (root / d).mkdir(exist_ok=True)

    # Starter entity
    (root / "entities" / "example.lore").write_text(
        "---\n"
        "entity: Example\n"
        "description: >\n"
        "  A sample entity. Replace with your first domain concept.\n"
        "---\n"
        "\n"
        "## Attributes\n"
        "\n"
        "name: string [required]\n"
        "  | The display name.\n"
        "\n"
        "## Identity\n"
        "\n"
        "An Example is uniquely identified by its name.\n"
        "\n"
        "## Notes\n"
        "\n"
        "Replace this with domain knowledge, edge cases, and\n"
        "guidance for AI agents interpreting this entity.\n"
    )

    print(f"\n  Ontology '{ont_name}' created at {root}/\n")
    print(f"  {root}/")
    print(f"  ├── lore.yaml")
    print(f"  ├── entities/")
    print(f"  │   └── example.lore")
    print(f"  ├── relationships/")
    print(f"  ├── rules/")
    print(f"  ├── taxonomies/")
    print(f"  ├── glossary/")
    print(f"  ├── views/")
    print(f"  ├── observations/")
    print(f"  └── outcomes/")
    print(f"\n  Next steps:")
    print(f"    1. Edit entities/example.lore or add new entities")
    print(f"    2. lore validate {root}")
    print(f"    3. lore compile {root} -t agent")
    print()


def _ensure_empty_target(root: Path, directory: str):
    if root.exists() and any(root.iterdir()):
        print(f"  Directory '{directory}' is not empty. Use an empty or new directory.")
        sys.exit(1)


def _validate_staleness(value: str):
    if not re.match(r"^\d+[dhm]$", value.strip()):
        print("  Invalid --staleness value. Use format like 45d, 12h, or 3m.")
        sys.exit(1)


def _validate_date_arg(value: str | None):
    if not value:
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        print("  Invalid --date value. Use YYYY-MM-DD.")
        sys.exit(1)


def _validate_confidence(value: float):
    if value < 0.0 or value > 1.0:
        print("  Invalid --confidence value. Expected number between 0.0 and 1.0.")
        sys.exit(1)


def _validate_max_sections(value: int):
    if value <= 0:
        print("  Invalid --max-sections value. Expected positive integer.")
        sys.exit(1)


def cmd_setup(
    directory: str,
    name: str | None,
    domain: str,
    maintainer: str,
    role: str,
    proposals: str,
    staleness: str,
):
    """Create an AI-first domain starter ontology with governance defaults."""
    root = Path(directory)
    ont_name = name or root.name
    today = date.today().isoformat()

    _ensure_empty_target(root, directory)
    _validate_staleness(staleness)
    root.mkdir(parents=True, exist_ok=True)

    manifest = (
        f"name: {ont_name}\n"
        "version: 0.2.0\n"
        "description: >\n"
        f"  AI-first ontology for {ont_name}.\n"
    )
    if domain:
        manifest += f"domain: {domain}\n"
    manifest += (
        "maintainers:\n"
        f"  - name: {maintainer}\n"
        f"    role: {role}\n"
        "\n"
        "evolution:\n"
        f"  proposals: {proposals}\n"
        f"  staleness: {staleness}\n"
    )
    (root / "lore.yaml").write_text(manifest)

    for d in ["entities", "relationships", "rules", "taxonomies",
              "glossary", "views", "observations", "outcomes"]:
        (root / d).mkdir(exist_ok=True)

    (root / "entities" / "domain_object.lore").write_text(
        "---\n"
        "entity: DomainObject\n"
        "description: A durable concept distilled from unstructured signals.\n"
        "provenance:\n"
        f"  author: {maintainer}\n"
        "  source: domain-expert\n"
        "  confidence: 0.9\n"
        f"  created: {today}\n"
        "status: draft\n"
        "---\n"
        "\n"
        "## Attributes\n"
        "\n"
        "name: string [required, unique]\n"
        "  | Canonical object name.\n"
        "\n"
        "category: enum [signal, actor, process, precedent]\n"
        "  | Coarse ontology category used for curation.\n"
        "\n"
        "confidence: float [0.0 .. 1.0]\n"
        "  | Best-effort confidence in this object's current definition.\n"
        "\n"
        "source_ref: string\n"
        "  | Pointer to source notes, transcript segments, or references.\n"
        "\n"
        "## Identity\n"
        "\n"
        "A DomainObject is identified by name.\n"
        "\n"
        "## Notes\n"
        "\n"
        "Write narrative meaning first. Keep structured fields as guardrails.\n"
        "When updating, preserve precedents and rationale.\n"
    )

    (root / "relationships" / "semantic_links.lore").write_text(
        "---\n"
        "domain: Domain Semantic Links\n"
        "description: Core relationships used in early ontology bootstrapping.\n"
        "---\n"
        "\n"
        "## RELATES_TO\n"
        "  from: DomainObject -> to: DomainObject\n"
        "  cardinality: many-to-many\n"
        "  | Expresses a contextual relationship between two domain objects.\n"
        "\n"
        "  properties:\n"
        "    relation_kind: string\n"
        "      | Causal, precedential, compositional, or dependency link.\n"
        "    weight: float\n"
        "      | Relative confidence in this link.\n"
        "\n"
        "## Traversal: context-bridge\n"
        "  path: DomainObject -[RELATES_TO]-> DomainObject\n"
        "  | Follow these links to build context paths for agent reasoning.\n"
    )

    (root / "rules" / "distillation.lore").write_text(
        "---\n"
        "domain: Distillation Rules\n"
        "description: Rules for promoting raw learning into ontology updates.\n"
        "---\n"
        "\n"
        "## promote-high-confidence-learning\n"
        "  applies_to: DomainObject\n"
        "  severity: info\n"
        "  trigger: Weekly ontology distillation review\n"
        "\n"
        "  condition:\n"
        "    DomainObject.confidence >= 0.8\n"
        "    AND DomainObject.category in [\"signal\", \"precedent\"]\n"
        "\n"
        "  action:\n"
        "    Propose upgrade from draft to proposed status\n"
        "    Attach supporting observations and outcomes\n"
        "\n"
        "  Distillation should remain human-reviewed before becoming stable knowledge.\n"
    )

    (root / "taxonomies" / "domain_object_category.lore").write_text(
        "---\n"
        "taxonomy: DomainObjectCategory\n"
        "applied_to: DomainObject.category\n"
        "description: Top-level grouping for bootstrap ontology objects.\n"
        "---\n"
        "\n"
        "Object Category\n"
        "├── Signal      @tag: evidence\n"
        "├── Actor       @tag: stakeholder\n"
        "├── Process     @tag: workflow\n"
        "└── Precedent   @tag: history\n"
        "\n"
        "## Inheritance Rules\n"
        "\n"
        "If a node is tagged Precedent and repeatedly linked to active signals,\n"
        "it should influence prioritization in related views.\n"
    )

    (root / "glossary" / "terms.lore").write_text(
        "---\n"
        "description: Core language for AI-first ontology development.\n"
        "---\n"
        "\n"
        "## Distillation\n"
        "\n"
        "Turning unstructured learning into durable ontology artifacts.\n"
        "\n"
        "## Learning Claim\n"
        "\n"
        "A semi-structured statement captured as Fact, Belief, Value, or Precedent.\n"
        "\n"
        "## Precedent Signal\n"
        "\n"
        "A recurring historical pattern that should inform future decisions.\n"
    )

    (root / "views" / "domain_curator.lore").write_text(
        "---\n"
        "view: Domain Curator\n"
        "audience: Ontology curators and agent platform engineers\n"
        "description: Curator view for evolving ontology from new field learning.\n"
        "---\n"
        "\n"
        "## Entities\n"
        "- DomainObject (all)\n"
        "\n"
        "## Relationships\n"
        "- RELATES_TO\n"
        "- context-bridge\n"
        "\n"
        "## Rules\n"
        "- promote-high-confidence-learning\n"
        "\n"
        "## Key Questions\n"
        "- What did we learn that should become durable ontology?\n"
        "- Which claims are strong enough to promote into stable definitions?\n"
        "- Which precedents should shape future agent behavior?\n"
        "\n"
        "## Not In Scope\n"
        "\n"
        "Raw event logs and full transcript storage.\n"
    )

    (root / "observations" / "kickoff_notes.lore").write_text(
        "---\n"
        "observations: Kickoff Distillation Notes\n"
        "about: DomainObject\n"
        "observed_by: setup-agent\n"
        f"date: {today}\n"
        "confidence: 0.75\n"
        "status: proposed\n"
        "provenance:\n"
        "  author: setup-agent\n"
        "  source: ai-generated\n"
        "  confidence: 0.75\n"
        f"  created: {today}\n"
        "---\n"
        "\n"
        "## First domain signal cluster\n"
        "\n"
        "Kickoff synthesis found repeated mentions of an unresolved dependency.\n"
        "\n"
        "Fact: Teams identified one shared blocker across three implementation tracks.\n"
        "Belief: This blocker will drive timeline risk without named ownership.\n"
        "Value: The team prioritizes predictable delivery over rapid scope expansion.\n"
        "Precedent: Similar blockers previously delayed launch by two to four weeks.\n"
    )

    (root / "outcomes" / "kickoff_retro.lore").write_text(
        "---\n"
        "outcomes: Kickoff Retrospective\n"
        "reviewed_by: setup-agent\n"
        f"date: {today}\n"
        "provenance:\n"
        "  author: setup-agent\n"
        "  source: ai-generated\n"
        "  confidence: 0.8\n"
        f"  created: {today}\n"
        "status: proposed\n"
        "---\n"
        "\n"
        "## Dependency risk assessment\n"
        "\n"
        "Initial prediction was directionally correct and improved planning quality.\n"
        "\n"
        "Takeaway: convert recurring dependency blockers into explicit ontology rules\n"
        "Takeaway: maintain precedents as first-class context in curator workflows\n"
        "\n"
        "Ref: observations/kickoff_notes.lore#first-domain-signal-cluster\n"
    )

    print(f"\n  Domain setup '{ont_name}' created at {root}/\n")
    print(f"  Included AI-first starter files for:")
    print(f"    entities, relationships, rules, taxonomies, glossary, views, observations, outcomes")
    print(f"\n  Next steps:")
    print(f"    1. lore validate {root}")
    print(f"    2. lore index {root}")
    print(f"    3. lore compile {root} -t agent --view \"Domain Curator\"")
    print(f"    4. lore curate {root}")
    print(f"    5. lore evolve {root}")
    print()


def cmd_ingest_transcript(
    directory: str,
    input_path: str,
    about: str,
    *,
    name: str | None,
    observed_by: str,
    confidence: float,
    source: str,
    date_str: str | None,
    output: str | None,
    max_sections: int,
):
    """Ingest transcript text into observations/*.lore."""
    from .ingest import ingest_transcript

    ontology_dir = Path(directory)
    transcript_path = Path(input_path)

    if not transcript_path.is_file():
        print(f"  Input transcript not found: {transcript_path}")
        sys.exit(1)

    _validate_confidence(confidence)
    _validate_max_sections(max_sections)
    _validate_date_arg(date_str)

    try:
        out_path = ingest_transcript(
            ontology_dir,
            transcript_path,
            about,
            observations_name=name,
            observed_by=observed_by,
            confidence=confidence,
            source=source,
            date_str=date_str,
            output_name=output,
            max_sections=max_sections,
        )
    except Exception as exc:
        print(f"  Transcript ingest failed: {exc}")
        sys.exit(1)

    print(f"  Wrote observations file: {out_path}")
    print(f"  Next: lore validate {ontology_dir}")


def cmd_ingest_memory(
    directory: str,
    adapter: str,
    input_path: str,
    about: str,
    *,
    name: str | None,
    observed_by: str | None,
    confidence: float,
    source: str,
    date_str: str | None,
    output: str | None,
    max_sections: int,
):
    """Ingest memory export JSON/JSONL into observations/*.lore."""
    from .ingest import ingest_memory

    ontology_dir = Path(directory)
    memory_path = Path(input_path)

    if not memory_path.is_file():
        print(f"  Input memory export not found: {memory_path}")
        sys.exit(1)

    _validate_confidence(confidence)
    _validate_max_sections(max_sections)
    _validate_date_arg(date_str)

    try:
        out_path = ingest_memory(
            ontology_dir,
            memory_path,
            adapter,
            about,
            observations_name=name,
            observed_by=observed_by,
            confidence=confidence,
            source=source,
            date_str=date_str,
            output_name=output,
            max_sections=max_sections,
        )
    except Exception as exc:
        print(f"  Memory ingest failed: {exc}")
        sys.exit(1)

    print(f"  Wrote observations file: {out_path}")
    print(f"  Next: lore validate {ontology_dir}")


def cmd_review(path: str, *, decision: str, reviewer: str, note: str, include_all: bool):
    """Apply acceptance/rejection review decision to proposal files."""
    from .review import review_proposals

    target = Path(path)
    try:
        result = review_proposals(
            target,
            decision=decision,
            reviewer=reviewer,
            note=note,
            include_all=include_all,
        )
    except Exception as exc:
        print(f"  Review failed: {exc}")
        sys.exit(1)

    if result.reviewed:
        for proposal_path in result.reviewed:
            print(f"  Updated: {proposal_path}")
    if result.skipped:
        for proposal_path in result.skipped:
            print(f"  Skipped: {proposal_path}")

    print(
        f"  Review complete: {len(result.reviewed)} updated, "
        f"{len(result.skipped)} skipped."
    )


def cmd_validate(directory: str):
    """Validate an ontology directory."""
    print(f"\n🔍 Validating ontology: {directory}\n")

    try:
        ontology = parse_ontology(directory)
    except Exception as e:
        print(f"  ✗ Parse error: {e}")
        sys.exit(1)

    diagnostics = validate(ontology)

    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    warnings = [d for d in diagnostics if d.severity == Severity.WARNING]
    infos = [d for d in diagnostics if d.severity == Severity.INFO]

    if errors:
        print("Errors:")
        for d in errors:
            print(d)
        print()

    if warnings:
        print("Warnings:")
        for d in warnings:
            print(d)
        print()

    if infos:
        print("Info:")
        for d in infos:
            print(d)
        print()

    total = len(diagnostics)
    if not errors:
        print(f"✓ Ontology is valid ({len(warnings)} warnings, {len(infos)} notes)")
    else:
        print(f"✗ Ontology has {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)


def cmd_compile(directory: str, target: str, output: str | None, view: str | None):
    """Compile ontology to target format."""
    ontology = parse_ontology(directory)
    target = target.strip()

    if target == "neo4j":
        from .compilers.neo4j import compile_neo4j
        result = compile_neo4j(ontology)
    elif target == "json":
        from .compilers.json_export import compile_json
        result = compile_json(ontology)
    elif target == "jsonld":
        from .compilers.jsonld import compile_jsonld
        result = compile_jsonld(ontology)
    elif target == "agent":
        from .compilers.agent import compile_agent_context
        result = compile_agent_context(ontology, view_name=view)
    elif target == "embeddings":
        from .compilers.embeddings import compile_embeddings
        result = compile_embeddings(ontology)
    elif target == "mermaid":
        from .compilers.mermaid import compile_mermaid
        result = compile_mermaid(ontology)
    elif target == "palantir":
        from .compilers.palantir import compile_palantir
        result = compile_palantir(ontology)
    else:
        try:
            compile_fn = resolve_compiler(ontology, target)
        except KeyError:
            plugin_targets = sorted(available_compilers(ontology).keys())
            print(f"Unknown target: {target}")
            if plugin_targets:
                print(f"Available plugin targets: {', '.join(plugin_targets)}")
            else:
                print("No plugin compilers configured in lore.yaml")
            print(f"Built-in targets: {', '.join(sorted(BUILTIN_COMPILE_TARGETS))}")
            sys.exit(1)
        except Exception as exc:
            print(f"Failed to load compiler plugin '{target}': {exc}")
            sys.exit(1)

        try:
            sig = inspect.signature(compile_fn)
            params = sig.parameters
            if view and "view_name" in params:
                result = compile_fn(ontology, view_name=view)
            elif view and "view" in params:
                result = compile_fn(ontology, view=view)
            else:
                result = compile_fn(ontology)
        except Exception as exc:
            print(f"Compiler plugin '{target}' failed: {exc}")
            sys.exit(1)

    if output:
        Path(output).write_text(result)
        print(f"✓ Compiled to {output}")
    else:
        print(result)


def cmd_stats(directory: str):
    """Show ontology statistics."""
    ontology = parse_ontology(directory)
    name = ontology.manifest.name if ontology.manifest else directory

    print(f"\n📊 Ontology: {name}")
    if ontology.manifest:
        print(f"   Version: {ontology.manifest.version}")
        print(f"   Domain: {ontology.manifest.domain}")
    print()

    print(f"   Entities:        {len(ontology.entities)}")
    total_attrs = sum(len(e.attributes) for e in ontology.entities)
    print(f"   Attributes:      {total_attrs}")
    print(f"   Relationships:   {len(ontology.all_relationships)}")
    print(f"   Traversals:      {len(ontology.all_traversals)}")
    print(f"   Rules:           {len(ontology.all_rules)}")
    print(f"   Taxonomies:      {len(ontology.taxonomies)}")

    if ontology.taxonomies:
        for tax in ontology.taxonomies:
            if tax.root:
                count = _count_tax_nodes(tax.root)
                print(f"     └─ {tax.name}: {count} nodes")

    glossary_count = len(ontology.all_glossary_entries)
    print(f"   Glossary terms:  {glossary_count}")
    print(f"   Claims:          {len(ontology.all_claims)}")
    print(f"   Views:           {len(ontology.views)}")

    # Entity detail
    print(f"\n   Entity breakdown:")
    for entity in ontology.entities:
        refs = [a for a in entity.attributes if a.reference_to]
        computed = [a for a in entity.attributes if a.annotations.get("computed")]
        print(f"     {entity.name}: {len(entity.attributes)} attrs "
              f"({len(refs)} refs, {len(computed)} computed)")

    print()


def cmd_viz(directory: str):
    """ASCII visualization of entity relationship graph."""
    ontology = parse_ontology(directory)
    name = ontology.manifest.name if ontology.manifest else directory

    print(f"\n🔗 Entity Graph: {name}\n")

    # Build adjacency info
    for entity in ontology.entities:
        outgoing = []
        incoming = []

        for rel in ontology.all_relationships:
            if rel.from_entity == entity.name:
                outgoing.append((rel.name, rel.to_entity))
            if rel.to_entity == entity.name:
                incoming.append((rel.name, rel.from_entity))

        print(f"  [{entity.name}]")

        for rel_name, target in outgoing:
            print(f"    ──{rel_name}──▶ [{target}]")
        for rel_name, source in incoming:
            print(f"    ◀──{rel_name}── [{source}]")

        if not outgoing and not incoming:
            print(f"    (no relationships)")
        print()

    # Traversals
    if ontology.all_traversals:
        print("  Named Traversals:")
        for trav in ontology.all_traversals:
            print(f"    ⟿ {trav.name}: {trav.path}")
        print()


def cmd_evolve(directory: str, output: str | None):
    """Generate improvement proposals from outcomes."""
    from .evolution import evolve

    ontology = parse_ontology(directory)
    output_dir = Path(output) if output else Path(directory) / "proposals"

    total_outcomes = len(ontology.all_outcomes)
    total_takeaways = len(ontology.all_takeaways)

    print(f"\n  Reading {total_outcomes} outcome(s) with {total_takeaways} takeaway(s)...\n")

    if not total_takeaways:
        print("  No takeaways found in outcomes. Nothing to propose.")
        return

    proposals = evolve(ontology, output_dir)

    if not proposals:
        print("  No proposals generated.")
        return

    for i, p in enumerate(proposals, 1):
        print(f"  Proposal {i}: {p['name']}")
        print(f"    {len(p['takeaways'])} takeaway(s) from {len(p['source_outcomes'])} outcome(s)")
        print(f"    -> {p['path']}")
        print()

    print(f"  {len(proposals)} proposal(s) generated. Review in {output_dir}/\n")


def cmd_index(directory: str):
    """Generate INDEX.lore routing files."""
    from .indexer import write_indexes

    ontology = parse_ontology(directory)
    name = ontology.manifest.name if ontology.manifest else directory

    print(f"\n📇 Indexing: {name}\n")

    written = write_indexes(ontology, Path(directory))
    for p in written:
        print(f"  ✓ {p}")

    print(f"\n  {len(written)} INDEX.lore file(s) generated.\n")


def cmd_curate(directory: str, job: str, dry_run: bool):
    """Run curation health checks."""
    from .curator import (
        curate_staleness, curate_coverage, curate_consistency,
        curate_index, curate_summarize, curate_all,
    )

    ontology = parse_ontology(directory)
    name = ontology.manifest.name if ontology.manifest else directory
    root_path = Path(directory)

    print(f"\n🩺 Curating: {name}\n")

    def _run_plugin_curator(job_name: str):
        try:
            curate_fn = resolve_curator(ontology, job_name)
        except KeyError:
            plugin_jobs = sorted(available_curators(ontology).keys())
            print(f"Unknown curation job: {job_name}")
            if plugin_jobs:
                print(f"Available plugin jobs: {', '.join(plugin_jobs)}")
            else:
                print("No plugin curators configured in lore.yaml")
            print(f"Built-in jobs: {', '.join(sorted(BUILTIN_CURATION_JOBS))}")
            sys.exit(1)
        except Exception as exc:
            print(f"Failed to load curator plugin '{job_name}': {exc}")
            sys.exit(1)

        try:
            report = curate_fn(ontology)
        except Exception as exc:
            print(f"Curator plugin '{job_name}' failed: {exc}")
            sys.exit(1)
        return report

    if job == "all":
        base_reports = curate_all(ontology, root_dir=root_path)
        plugin_reports = []
        for plugin_job in sorted(available_curators(ontology).keys()):
            plugin_reports.append(_run_plugin_curator(plugin_job))
        if plugin_reports:
            reports = base_reports[:-1] + plugin_reports
            reports.append(curate_summarize(ontology, reports))
        else:
            reports = base_reports
    elif job == "staleness":
        reports = [curate_staleness(ontology)]
    elif job == "coverage":
        reports = [curate_coverage(ontology)]
    elif job == "consistency":
        reports = [curate_consistency(ontology)]
    elif job == "index":
        reports = [curate_index(ontology, root_dir=root_path)]
    elif job == "summarize":
        # Run all first to feed into summarize
        staleness = curate_staleness(ontology)
        coverage = curate_coverage(ontology)
        consistency = curate_consistency(ontology)
        index = curate_index(ontology, root_dir=root_path)
        reports = [curate_summarize(ontology, [staleness, coverage, consistency, index])]
    else:
        reports = [_run_plugin_curator(job)]

    for report in reports:
        icon = {
            "staleness": "🕰️",
            "coverage": "📊",
            "consistency": "🔍",
            "index": "📇",
            "summarize": "📝",
        }.get(report.job, "•")

        print(f"  {icon}  {report.job.upper()}")

        if report.job == "summarize":
            # Print the summary text directly
            for line in report.summary.split("\n"):
                print(f"     {line}")
            print()
            continue

        if report.findings:
            for finding in report.findings:
                f_icon = "⚠" if finding.severity == "warning" else "ℹ"
                print(f"     {f_icon} {finding.message}")
                if finding.source:
                    print(f"       {finding.source}")
                if finding.suggestion and not dry_run:
                    print(f"       → {finding.suggestion}")
        else:
            print(f"     ✓ No issues found")

        if report.summary:
            print(f"     {report.summary}")
        print()

    # Overall
    total_warnings = sum(len(r.warnings) for r in reports if r.job != "summarize")
    total_infos = sum(len(r.infos) for r in reports if r.job != "summarize")
    if total_warnings == 0:
        print(f"  ✓ Ontology is healthy ({total_infos} suggestion{'s' if total_infos != 1 else ''})\n")
    else:
        print(f"  {total_warnings} warning{'s' if total_warnings != 1 else ''}, "
              f"{total_infos} suggestion{'s' if total_infos != 1 else ''}\n")


def _count_tax_nodes(node: TaxonomyNode) -> int:
    count = 1
    for child in node.children:
        count += _count_tax_nodes(child)
    return count


if __name__ == "__main__":
    main()
