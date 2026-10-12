#!/usr/bin/env python3
"""Sincroniza a fonte única (core/) com os pacotes de cada harness (plugins/<harness>/).

As skills são escritas uma vez em core/<plugin>/ e copiadas para cada harness
declarado em harnesses.json. Os diretórios gerados (skills/ e references/) não
devem ser editados à mão: edite core/ e rode este script.

Uso:
    python3 scripts/sync_plugins.py           # copia core/ para os harnesses
    python3 scripts/sync_plugins.py --check   # só verifica; sai com 1 se houver divergência (CI)

Além da cópia, o script confere:
- se cada manifesto de harness existe e tem o mesmo nome e versão do core;
- se todo SKILL.md tem frontmatter com name igual ao nome da pasta e description;
- se toda referência relativa a um arquivo .md/.py/.html dentro das skills resolve.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "harnesses.json"
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def load_config() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        return json.load(fh)


def read_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def diff_trees(src: Path, dst: Path) -> list[str]:
    """Lista arquivos que diferem entre src e dst (relativos a dst)."""
    problems: list[str] = []
    if not dst.exists():
        return [f"{dst.relative_to(ROOT)} não existe"]
    cmp = filecmp.dircmp(src, dst, ignore=["__pycache__", ".DS_Store"])

    def walk(c: filecmp.dircmp, rel: Path) -> None:
        for name in c.left_only:
            problems.append(f"faltando: {(dst / rel / name).relative_to(ROOT)}")
        for name in c.right_only:
            problems.append(f"sobrando: {(dst / rel / name).relative_to(ROOT)}")
        # dircmp compara só stat por padrão; refaz com conteúdo
        for name in c.common_files:
            if not filecmp.cmp(Path(c.left) / name, Path(c.right) / name, shallow=False):
                problems.append(f"diferente: {(dst / rel / name).relative_to(ROOT)}")
        for name, sub in c.subdirs.items():
            walk(sub, rel / name)

    walk(cmp, Path())
    return problems


def check_skills(core: Path) -> list[str]:
    problems: list[str] = []
    ref_pattern = re.compile(r"`((?:\.\./|references/|assets/|scripts/)[^`\s]+\.(?:md|py|html))`")
    for skill_md in sorted(core.glob("skills/*/SKILL.md")):
        folder = skill_md.parent.name
        text = skill_md.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not match:
            problems.append(f"{skill_md.relative_to(ROOT)}: sem frontmatter")
            continue
        front = match.group(1)
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        if not name or name.group(1).strip() != folder:
            problems.append(f"{skill_md.relative_to(ROOT)}: name diferente da pasta '{folder}'")
        if not re.search(r"^description:\s*\S", front, re.M):
            problems.append(f"{skill_md.relative_to(ROOT)}: sem description")
    skill_dirs = [p.parent for p in core.glob("skills/*/SKILL.md")]
    for doc in sorted(core.rglob("*.md")):
        # Caminhos podem ser relativos ao arquivo ou à raiz da skill. Documentos fora
        # de uma skill (references/ do plugin) citam arquivos de "cada skill".
        skill_root = next((d for d in skill_dirs if d in doc.parents), None)
        bases = [doc.parent] + ([skill_root] if skill_root else skill_dirs)
        for ref in ref_pattern.findall(doc.read_text(encoding="utf-8")):
            if not any((base / ref).resolve().exists() for base in bases):
                problems.append(f"{doc.relative_to(ROOT)}: referência quebrada '{ref}'")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="só verifica, não escreve")
    args = parser.parse_args()

    config = load_config()
    problems: list[str] = []

    for plugin, spec in config["plugins"].items():
        core = ROOT / spec["core"]
        core_meta = read_manifest(core / "plugin.core.json")
        problems += check_skills(core)

        for harness, target in spec["harnesses"].items():
            dst = ROOT / target["path"]
            manifest_path = dst / target["manifest"]
            if not manifest_path.exists():
                problems.append(f"[{harness}] manifesto ausente: {manifest_path.relative_to(ROOT)}")
            else:
                manifest = read_manifest(manifest_path)
                for key in ("name", "version"):
                    if manifest.get(key) != core_meta[key]:
                        problems.append(
                            f"[{harness}] {manifest_path.relative_to(ROOT)}: {key} "
                            f"'{manifest.get(key)}' diferente do core '{core_meta[key]}'"
                        )

            for sub in spec["synced_dirs"]:
                src_dir, dst_dir = core / sub, dst / sub
                if args.check:
                    problems += [f"[{harness}] {p}" for p in diff_trees(src_dir, dst_dir)]
                else:
                    if dst_dir.exists():
                        shutil.rmtree(dst_dir)
                    shutil.copytree(src_dir, dst_dir, ignore=IGNORED)
                    print(f"[{harness}] {plugin}: {sub}/ sincronizado em {dst_dir.relative_to(ROOT)}")

    if problems:
        print("\nProblemas encontrados:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        if args.check:
            print("\nEdite core/ e rode: python3 scripts/sync_plugins.py", file=sys.stderr)
        return 1

    print("OK: core e harnesses consistentes." if args.check else "OK: sincronização concluída.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
