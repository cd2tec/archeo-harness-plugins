#!/usr/bin/env python3
"""Instala as skills do Archeo num diretório de skills lido pelo DeepSeek Harness (DSH).

O DSH descobre skills em diretórios planos, uma pasta por skill com SKILL.md
dentro. Este script copia a pasta skills/ deste pacote para um deles.

Uso (rode de dentro da pasta descompactada do ZIP ou do clone do repositório):

    python3 install.py                  # ~/.agents/skills   (usuário; vale para todos os projetos)
    python3 install.py --project [DIR]  # DIR/.agents/skills (só o projeto; DIR padrão: pasta atual)
    python3 install.py --dsh-home       # $DSH_HOME/skills   (padrão ~/.dsh/skills; só o DSH lê)
    python3 install.py --dest CAMINHO   # qualquer outro diretório de skills
    python3 install.py --remove         # remove as skills do Archeo do destino escolhido
    python3 install.py --dry-run        # mostra o que faria, sem escrever

Só as pastas com os nomes das skills do Archeo são tocadas. Outras skills no
mesmo diretório ficam como estão. Uma pasta com o mesmo nome que não seja uma
skill do Archeo só é substituída com --force.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "skills"
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def our_skills() -> list[Path]:
    return sorted(p.parent for p in SOURCE.glob("*/SKILL.md"))


def skill_name(folder: Path) -> str | None:
    """Nome declarado no frontmatter de SKILL.md, ou None se não houver."""
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    name = re.search(r"^name:\s*(.+)$", match.group(1), re.M)
    return name.group(1).strip() if name else None


def resolve_dest(args: argparse.Namespace) -> Path:
    if args.dest:
        return Path(args.dest).expanduser().resolve()
    if args.dsh_home:
        home = os.environ.get("DSH_HOME") or str(Path.home() / ".dsh")
        return Path(home).expanduser().resolve() / "skills"
    if args.project is not None:
        base = Path(args.project or ".").expanduser().resolve()
        return base / ".agents" / "skills"
    return Path.home() / ".agents" / "skills"


def install(dest: Path, dry_run: bool, force: bool) -> int:
    failures = 0
    if not dest.exists():
        print(f"criando {dest}")
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
    for src in our_skills():
        target = dest / src.name
        if target.exists():
            existing = skill_name(target)
            if existing != src.name and not force:
                print(f"PULADA  {target}: já existe e não é a skill '{src.name}' do Archeo (use --force para substituir)")
                failures += 1
                continue
            action = "atualizando"
        else:
            action = "instalando"
        print(f"{action:<11} {target}")
        if dry_run:
            continue
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target, ignore=IGNORED)
    return failures


def remove(dest: Path, dry_run: bool) -> int:
    for src in our_skills():
        target = dest / src.name
        if not target.exists():
            continue
        if skill_name(target) != src.name:
            print(f"MANTIDA {target}: não é a skill '{src.name}' do Archeo")
            continue
        print(f"removendo   {target}")
        if not dry_run:
            if target.is_symlink():
                target.unlink()
            else:
                shutil.rmtree(target)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    where = parser.add_mutually_exclusive_group()
    where.add_argument("--project", nargs="?", const=".", metavar="DIR", help="instala em DIR/.agents/skills (DIR padrão: pasta atual)")
    where.add_argument("--dsh-home", action="store_true", help="instala em $DSH_HOME/skills (padrão ~/.dsh/skills)")
    where.add_argument("--dest", metavar="CAMINHO", help="instala neste diretório de skills")
    parser.add_argument("--remove", action="store_true", help="remove as skills do Archeo em vez de instalar")
    parser.add_argument("--force", action="store_true", help="substitui pasta de mesmo nome que não seja skill do Archeo")
    parser.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    args = parser.parse_args()

    if not our_skills():
        print(f"Nenhuma skill encontrada em {SOURCE}. Rode este script de dentro do pacote descompactado.", file=sys.stderr)
        return 2

    dest = resolve_dest(args)
    print(f"{'Removendo de' if args.remove else 'Instalando em'}: {dest}{' (simulação)' if args.dry_run else ''}")
    failures = remove(dest, args.dry_run) if args.remove else install(dest, args.dry_run, args.force)

    if not args.dry_run and not args.remove:
        print(
            "\nPronto. O DSH observa esses diretórios e atualiza o catálogo de skills sozinho; "
            "abra uma sessão nova para garantir. Confira também se o conector do Archeo (MCP) está configurado: "
            "sem as ferramentas db_* as skills param no primeiro passo."
        )
    if failures:
        print(f"\n{failures} pasta(s) pulada(s). Veja acima.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
