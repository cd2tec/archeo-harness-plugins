#!/usr/bin/env python3
"""Sincroniza a fonte única (core/) com os pacotes de cada harness (plugins/<harness>/).

As skills são escritas uma vez em core/<plugin>/ e copiadas para cada harness
declarado em harnesses.json. Os diretórios gerados (skills/ e references/) não
devem ser editados à mão: edite core/ e rode este script.

Uso:
    python3 scripts/sync_plugins.py           # copia core/ para os harnesses
    python3 scripts/sync_plugins.py --check   # só verifica; sai com 1 se houver divergência (CI)

Layouts de harness (campo "layout" em harnesses.json, padrão "plugin"):

- "plugin": copia os diretórios de synced_dirs (skills/ e references/) como estão.
  O harness instala o pacote inteiro, então as referências compartilhadas em
  references/ continuam acessíveis por caminho relativo (../../references/x.md).
- "flat-skills": copia só skills/. Serve para harnesses que leem cada skill de um
  diretório plano (por exemplo ~/.agents/skills/<nome>/SKILL.md, caso do
  DeepSeek Harness), onde não existe "raiz do plugin". As referências
  compartilhadas que uma skill cita são copiadas para dentro de references/
  dessa skill e os caminhos são reescritos para o novo lugar.

Além da cópia, o script confere:
- se cada manifesto de harness existe e tem o mesmo nome e versão do core;
- se todo SKILL.md tem frontmatter com name igual ao nome da pasta e description;
- se toda referência relativa a um arquivo .md/.py/.html resolve, tanto em core/
  quanto na árvore gerada de cada harness.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "harnesses.json"
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
# Caminho relativo entre crases apontando para um arquivo de texto da skill.
REF_PATTERN = re.compile(r"`((?:\.\./|references/|assets/|scripts/)[^`\s]+\.(?:md|py|html))`")
LAYOUTS = ("plugin", "flat-skills")


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


def skill_roots(tree: Path) -> list[Path]:
    return [p.parent for p in tree.glob("skills/*/SKILL.md")]


def resolve_ref(doc: Path, ref: str, tree: Path, prefer: Path | None = None) -> Path | None:
    """Resolve uma referência relativa de `doc` dentro de `tree`.

    Caminhos podem ser relativos ao arquivo ou à raiz da skill. Documentos fora
    de uma skill (references/ do plugin) citam arquivos de "cada skill", então
    valem se resolverem a partir de qualquer skill; `prefer` indica a raiz de
    skill a tentar primeiro nesse caso.
    """
    roots = skill_roots(tree)
    skill_root = next((d for d in roots if d in doc.parents), None)
    if skill_root is None and prefer is not None:
        roots = [prefer] + [r for r in roots if r != prefer]
    bases = [doc.parent] + ([skill_root] if skill_root else roots)
    for base in bases:
        candidate = (base / ref).resolve()
        if candidate.exists():
            return candidate
    return None


def check_frontmatter(core: Path) -> list[str]:
    problems: list[str] = []
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
    return problems


def check_refs(tree: Path, label: Path | None = None) -> list[str]:
    """Confere que toda referência entre arquivos de `tree` resolve.

    `label` é o caminho mostrado nas mensagens no lugar de `tree` (útil quando a
    árvore é temporária).
    """
    problems: list[str] = []
    shown = label or tree
    for doc in sorted(tree.rglob("*.md")):
        for ref in REF_PATTERN.findall(doc.read_text(encoding="utf-8")):
            if resolve_ref(doc, ref, tree) is None:
                rel = shown / doc.relative_to(tree)
                problems.append(f"{rel}: referência quebrada '{ref}'")
    return problems


def rewrite_ref(text: str, old: str, new: str) -> str:
    return text.replace(f"`{old}`", f"`{new}`")


def build_flat_skills(core: Path, work: Path) -> list[str]:
    """Monta em `work/skills` a versão plana das skills de `core`.

    Cada skill continua uma pasta `<nome>/` com SKILL.md e seus references/,
    assets/ e scripts/. As referências compartilhadas (core/references/) citadas
    por uma skill são copiadas para `<nome>/references/` e os caminhos reescritos.
    Referências entre skills (../outra-skill/...) já funcionam no layout plano,
    porque as skills continuam irmãs, e não são tocadas.
    """
    problems: list[str] = []
    core_skills, core_shared = core / "skills", core / "references"
    work_skills = work / "skills"
    shutil.copytree(core_skills, work_skills, ignore=IGNORED)

    # Fila de (documento gerado, documento de origem em core/, nome da skill dona).
    queue: list[tuple[Path, Path, str]] = []
    for doc in sorted(work_skills.rglob("*.md")):
        rel = doc.relative_to(work_skills)
        queue.append((doc, core_skills / rel, rel.parts[0]))

    while queue:
        doc, origin, skill = queue.pop(0)
        text = doc.read_text(encoding="utf-8")
        origin_is_shared = core_shared in origin.parents
        for ref in REF_PATTERN.findall(text):
            # Documento compartilhado cita "references/x.md de cada skill": na cópia,
            # isso significa o arquivo da skill dona.
            target = resolve_ref(origin, ref, core, prefer=core_skills / skill)
            if target is None:
                continue  # check_refs(core) já reporta
            if core_skills in target.parents:
                if not origin_is_shared:
                    continue  # referência entre skills: válida como está
                new_target = work_skills / target.relative_to(core_skills)
            elif core_shared in target.parents:
                new_target = work_skills / skill / "references" / target.relative_to(core_shared)
                if new_target.exists():
                    if not filecmp.cmp(target, new_target, shallow=False):
                        problems.append(
                            f"skills/{skill}/references/{target.relative_to(core_shared)} já existe na "
                            f"skill e difere de {target.relative_to(ROOT)}; renomeie um dos dois"
                        )
                        continue
                else:
                    new_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, new_target)
                    queue.append((new_target, target, skill))
            else:
                continue
            if resolve_ref(doc, ref, work, prefer=work_skills / skill) == new_target:
                continue  # já resolve a partir do novo lugar: não mexe no texto
            new_ref = Path(os.path.relpath(new_target, doc.parent)).as_posix()
            text = rewrite_ref(text, ref, new_ref)
        doc.write_text(text, encoding="utf-8")
    return problems


def build_tree(core: Path, spec: dict, target: dict, work: Path) -> tuple[list[str], list[str]]:
    """Gera em `work` o conteúdo esperado dos diretórios sincronizados.

    Devolve (problemas, subdiretórios gerados).
    """
    layout = target.get("layout", "plugin")
    if layout == "plugin":
        for sub in spec["synced_dirs"]:
            shutil.copytree(core / sub, work / sub, ignore=IGNORED)
        return [], list(spec["synced_dirs"])
    if layout == "flat-skills":
        return build_flat_skills(core, work), ["skills"]
    return [f"layout desconhecido '{layout}' (use um de: {', '.join(LAYOUTS)})"], []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="só verifica, não escreve")
    args = parser.parse_args()

    config = load_config()
    problems: list[str] = []

    for plugin, spec in config["plugins"].items():
        core = ROOT / spec["core"]
        core_meta = read_manifest(core / "plugin.core.json")
        problems += check_frontmatter(core)
        problems += check_refs(core, core.relative_to(ROOT))

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

            with tempfile.TemporaryDirectory(prefix=f"sync-{plugin}-{harness}-") as tmp:
                work = Path(tmp)
                build_problems, subs = build_tree(core, spec, target, work)
                problems += [f"[{harness}] {p}" for p in build_problems]
                problems += [f"[{harness}] {p}" for p in check_refs(work, dst.relative_to(ROOT))]
                stale = [s for s in ("skills", "references") if s not in subs and (dst / s).exists()]
                problems += [f"[{harness}] sobrando: {(dst / s).relative_to(ROOT)} (layout não gera {s}/)" for s in stale]

                for sub in subs:
                    src_dir, dst_dir = work / sub, dst / sub
                    if args.check:
                        problems += [f"[{harness}] {p}" for p in diff_trees(src_dir, dst_dir)]
                    else:
                        if dst_dir.exists():
                            shutil.rmtree(dst_dir)
                        shutil.copytree(src_dir, dst_dir)
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
