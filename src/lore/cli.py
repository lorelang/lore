"""
Lore CLI.

Command-line interface for parsing, validating, compiling,
and inspecting ontologies defined in .lore format.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from .parser import parse_ontology
from .validator import validate, Severity
from .models import TaxonomyNode


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

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate an ontology")
    p_validate.add_argument("dir", help="Ontology directory")

    # compile
    p_compile = subparsers.add_parser("compile", help="Compile to target format")
    p_compile.add_argument("dir", help="Ontology directory")
    p_compile.add_argument("-t", "--target", required=True,
                          choices=["neo4j", "json", "agent", "embeddings", "mermaid", "palantir"],
                          help="Compilation target")
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
    p_curate.add_argument("--job", choices=["staleness", "coverage", "consistency", "index", "summarize", "all"],
                          default="all", help="Which curation job to run (default: all)")
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

    if root.exists() and any(root.iterdir()):
        print(f"  Directory '{directory}' is not empty. Use an empty or new directory.")
        sys.exit(1)

    root.mkdir(parents=True, exist_ok=True)

    # lore.yaml manifest
    manifest = (
        f"name: {ont_name}\n"
        f"version: 0.1.0\n"
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

    if target == "neo4j":
        from .compilers.neo4j import compile_neo4j
        result = compile_neo4j(ontology)
    elif target == "json":
        from .compilers.json_export import compile_json
        result = compile_json(ontology)
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
        print(f"Unknown target: {target}")
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

    if job == "all":
        reports = curate_all(ontology, root_dir=root_path)
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
