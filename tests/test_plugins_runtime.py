"""Runtime tests for plugin loading and execution."""
from pathlib import Path
from lore.cli import cmd_compile, cmd_curate
from lore.parser import parse_ontology


def _write_plugin_module(tmp_path: Path):
    module_path = tmp_path / "demo_plugins.py"
    module_path.write_text(
        "from lore.curator import CurationReport, CurationFinding\n"
        "def compile_demo(ontology):\n"
        "    return f'plugin-compiled:{len(ontology.entities)}'\n"
        "\n"
        "def curate_demo(ontology):\n"
        "    report = CurationReport(job='demo-check')\n"
        "    report.findings.append(CurationFinding(job='demo-check', severity='info', message='plugin curator ran'))\n"
        "    report.summary = 'plugin summary'\n"
        "    return report\n"
        "\n"
        "def parse_playbook(path):\n"
        "    text = path.read_text().strip()\n"
        "    return {'kind': 'playbook', 'name': path.stem, 'size': len(text)}\n"
    )


def _write_minimal_ontology(tmp_path: Path, manifest_text: str):
    root = tmp_path / "ont"
    root.mkdir()
    (root / "lore.yaml").write_text(manifest_text)
    (root / "entities").mkdir()
    (root / "entities" / "account.lore").write_text(
        "---\nentity: Account\n---\n## Attributes\nid: string\n"
    )
    return root


def test_compile_uses_plugin_target(tmp_path, monkeypatch, capsys):
    _write_plugin_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    root = _write_minimal_ontology(
        tmp_path,
        "name: demo\nversion: 0.2.0\nplugins:\n  compilers:\n    demo: demo_plugins:compile_demo\n",
    )

    cmd_compile(str(root), "demo", output=None, view=None)
    out = capsys.readouterr().out
    assert "plugin-compiled:1" in out


def test_curate_uses_plugin_job(tmp_path, monkeypatch, capsys):
    _write_plugin_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    root = _write_minimal_ontology(
        tmp_path,
        "name: demo\nversion: 0.2.0\nplugins:\n  curators:\n    demo: demo_plugins:curate_demo\n",
    )

    cmd_curate(str(root), job="demo", dry_run=True)
    out = capsys.readouterr().out
    assert "DEMO-CHECK" in out
    assert "plugin curator ran" in out


def test_parser_loads_extension_directory_with_plugin_parser(tmp_path, monkeypatch):
    _write_plugin_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    root = _write_minimal_ontology(
        tmp_path,
        "name: demo\nversion: 0.2.0\nplugins:\n  directories:\n    playbooks: demo_plugins:parse_playbook\n",
    )
    (root / "playbooks").mkdir()
    (root / "playbooks" / "onboarding.lore").write_text(
        "---\nname: onboarding\n---\n## Steps\n- Do thing\n"
    )

    ontology = parse_ontology(root)
    assert "playbooks" in ontology.extensions
    parsed = ontology.extensions["playbooks"][0]
    assert parsed["kind"] == "playbook"
    assert parsed["name"] == "onboarding"
