#!/usr/bin/env python3
"""Monta o HTML do dashboard a partir de um config JSON e do template.

Uso:
  python3 build_dashboard.py config.json saida.html

Valida a estrutura do config antes de gerar, para que erros de formato
aparecam aqui e nao como uma secao vazia na pagina publicada.
"""
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "dashboard-template.html"
TIPOS = {"kpis", "score", "linha", "barras", "heatmap", "tabela"}
FORMATOS = {None, "moeda", "inteiro", "decimal", "pct", "dias"}


def erro(msgs, texto):
    msgs.append(texto)


def validar(cfg):
    msgs = []
    if cfg.get("modo") not in ("snapshot", "live"):
        erro(msgs, "modo deve ser 'snapshot' ou 'live'")
    if not cfg.get("titulo"):
        erro(msgs, "titulo e obrigatorio")
    if cfg.get("modo") == "live":
        live = cfg.get("live") or {}
        for k in ("server", "tool"):
            if not live.get(k):
                erro(msgs, f"live.{k} e obrigatorio no modo ao vivo")
    ids = set()
    for i, sec in enumerate(cfg.get("secoes") or []):
        nome = sec.get("id") or f"secoes[{i}]"
        if not sec.get("id"):
            erro(msgs, f"{nome}: falta id")
        elif sec["id"] in ids:
            erro(msgs, f"{nome}: id repetido")
        ids.add(sec.get("id"))
        if sec.get("tipo") not in TIPOS:
            erro(msgs, f"{nome}: tipo '{sec.get('tipo')}' invalido ({', '.join(sorted(TIPOS))})")
        if sec.get("formato") not in FORMATOS:
            erro(msgs, f"{nome}: formato '{sec.get('formato')}' invalido")
        if cfg.get("modo") == "live" and not sec.get("sql"):
            erro(msgs, f"{nome}: modo ao vivo exige sql em toda secao")
        if cfg.get("modo") == "snapshot" and not isinstance(sec.get("dados"), list):
            erro(msgs, f"{nome}: modo snapshot exige dados (lista de linhas)")
        if cfg.get("modo") == "live" and sec.get("dados"):
            erro(msgs, f"{nome}: no modo ao vivo nao embuta dados; a pagina busca no banco")
        if sec.get("tipo") == "score":
            comps = sec.get("componentes") or []
            if not comps:
                erro(msgs, f"{nome}: score sem componentes")
            for c in comps:
                if not all(k in c for k in ("campo", "rotulo", "peso", "ruim", "bom")):
                    erro(msgs, f"{nome}: componente sem campo/rotulo/peso/ruim/bom: {c}")
                elif c["ruim"] == c["bom"]:
                    erro(msgs, f"{nome}: componente {c['campo']} com ruim == bom")
        if sec.get("tipo") == "kpis" and not sec.get("cards"):
            erro(msgs, f"{nome}: kpis sem cards")
        if sec.get("tipo") == "tabela" and not sec.get("colunas"):
            erro(msgs, f"{nome}: tabela sem colunas")
    for nivel in [x.get("nivel") for x in cfg.get("leitura") or []]:
        if nivel not in ("critico", "atencao", "bom", "info"):
            erro(msgs, f"leitura com nivel invalido: {nivel}")
    return msgs


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    msgs = validar(cfg)
    if msgs:
        print("Config invalido:")
        for m in msgs:
            print(" -", m)
        sys.exit(1)
    html = TEMPLATE.read_text(encoding="utf-8")
    titulo = (cfg.get("titulo") or "Painel do varejo").replace("<", "").replace(">", "")
    if cfg["modo"] == "snapshot":
        ini, fim = html.find("/*LIVE-START*/"), html.find("/*LIVE-END*/")
        if ini < 0 or fim < 0:
            print("Template sem marcadores LIVE-START/LIVE-END")
            sys.exit(1)
        html = html[:ini] + html[fim + len("/*LIVE-END*/"):]
    payload = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("__DASH_TITLE__", titulo, 1).replace("__DASH_CONFIG__", payload, 1)
    Path(sys.argv[2]).write_text(html, encoding="utf-8")
    n = len(cfg.get("secoes") or [])
    print(f"OK: {sys.argv[2]} ({n} secoes, modo {cfg['modo']}, {len(html)//1024} KB)")


if __name__ == "__main__":
    main()
