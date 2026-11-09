#!/usr/bin/env python3
"""Gera a entrega de um relatório analyze-mcp-* a partir de um JSON.

Uso:
    python3 render_relatorio.py --input relatorio.json --format html --output relatorio.html
    python3 render_relatorio.py --input relatorio.json --format whatsapp

Formatos: html, csv, whatsapp e markdown. O formato do JSON está em
references/formato-relatorio.md. Só biblioteca padrão.

Quem decide se a prova fechou é este script, a partir dos números informados.
Relatório sem prova não sai: sai com código 2 e {"errors": [...]} em português.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
if str(_AQUI) not in sys.path:
    sys.path.insert(0, str(_AQUI))

import brand  # noqa: E402
from brand import esc, formatar  # noqa: E402

TEMPLATE = _AQUI.parent / "assets" / "relatorio-template.html"
SAIDAS = ("html", "csv", "whatsapp", "markdown")
TEMAS = ("auto", "light", "dark")
NIVEIS = {"critico": "Urgente", "atencao": "Atenção", "bom": "Bom", "info": "Nota", "dado": "Dado"}
TIPOS_BLOCO = ("tabela", "pareto", "barras", "linha", "cascata")
FORMATOS_COLUNA = set(brand.FORMATOS) | {"classe"}
NUMERICOS = {"moeda", "inteiro", "decimal", "pct", "pp", "dias"}
TOLERANCIA_PADRAO = 2.0
MAX_LINHAS_PAGINA = 30
CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
AVISO_CONFERENCIA = "Para conferência e gestão. Não é documento oficial: livros, obrigações e apurações saem do ERP ou do sistema fiscal, com responsável técnico."
CHECK = ('<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3.2L13 5"/></svg>')


# ---------- validação ----------

def _textos(valor):
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for item in valor.values():
            yield from _textos(item)
    elif isinstance(valor, list):
        for item in valor:
            yield from _textos(item)


def _validar_bloco(bloco, indice, erros):
    nome = f"blocos[{indice}]"
    tipo = bloco.get("tipo") if isinstance(bloco, dict) else None
    if tipo not in TIPOS_BLOCO:
        erros.append(f"{nome}: tipo '{tipo}' inválido (use {', '.join(TIPOS_BLOCO)}).")
        return
    if not bloco.get("titulo"):
        erros.append(f"{nome}: falta o título.")
    if tipo == "tabela":
        colunas = bloco.get("colunas") or []
        if not colunas:
            erros.append(f"{nome}: tabela sem colunas.")
        if not isinstance(bloco.get("linhas"), list):
            erros.append(f"{nome}: tabela sem a lista de linhas.")
        for col in colunas:
            if not col.get("campo") or not col.get("rotulo"):
                erros.append(f"{nome}: coluna sem campo ou rótulo.")
            if col.get("formato") not in FORMATOS_COLUNA | {None}:
                erros.append(f"{nome}: formato '{col.get('formato')}' inválido.")
            if "cpf" in str(col.get("campo", "")).lower():
                for linha in bloco.get("linhas") or []:
                    if re.search(r"\d{3}\D?\d{3}\D?\d{3}", str(linha.get(col["campo"], ""))):
                        erros.append(f"{nome}: coluna de CPF sem máscara. Use ***.123.456-**.")
                        break
    elif tipo == "pareto":
        classes = bloco.get("classes") or []
        if not classes or any(not brand.e_numero(c.get("itens")) or not brand.e_numero(c.get("valor")) for c in classes):
            erros.append(f"{nome}: pareto precisa de classes com itens e valor numéricos.")
    elif tipo == "barras":
        if not bloco.get("linhas") or any(not brand.e_numero(l.get("valor")) for l in bloco["linhas"]):
            erros.append(f"{nome}: barras precisam de linhas com valor numérico.")
    elif tipo == "linha":
        if not bloco.get("pontos") or any(not brand.e_numero(p.get("atual")) for p in bloco["pontos"]):
            erros.append(f"{nome}: linha precisa de pontos com 'atual' numérico.")
    elif tipo == "cascata":
        etapas = bloco.get("etapas") or []
        if len(etapas) < 2 or any(not brand.e_numero(e.get("valor")) or e.get("tipo") not in ("inicial", "delta", "final") for e in etapas):
            erros.append(f"{nome}: cascata precisa de etapas com valor e tipo inicial, delta ou final.")


def validar(rel) -> list[str]:
    if not isinstance(rel, dict):
        return ["O relatório precisa ser um objeto JSON."]
    erros: list[str] = []
    for campo in ("area", "titulo", "cliente", "gerado_em"):
        if not rel.get(campo):
            erros.append(f"Falta '{campo}'.")
    fonte = rel.get("fonte") or {}
    for campo in ("banco", "engine", "conector"):
        if not fonte.get(campo):
            erros.append(f"Falta 'fonte.{campo}'.")
    recorte = rel.get("recorte") or {}
    for campo in ("unidade", "periodo", "filtros", "nivel"):
        if not recorte.get(campo):
            erros.append(f"Falta 'recorte.{campo}': declare o recorte, mesmo que seja o padrão.")
    if not (rel.get("veredito") or {}).get("titulo"):
        erros.append("Falta 'veredito.titulo': o achado principal, em uma frase.")
    if len((rel.get("veredito") or {}).get("numeros") or []) > 3:
        erros.append("'veredito.numeros' aceita até 3 números.")
    resumo = rel.get("resumo") or []
    if not 1 <= len(resumo) <= 6:
        erros.append("'resumo' precisa de 1 a 6 totais.")
    leitura = rel.get("leitura") or []
    if not 1 <= len(leitura) <= 6:
        erros.append("'leitura' precisa de 1 a 6 itens.")
    for item in leitura:
        if item.get("nivel") not in NIVEIS or not item.get("texto"):
            erros.append(f"Leitura inválida: use nível {', '.join(NIVEIS)} e texto.")
    conferencias = (rel.get("prova") or {}).get("conferencias") or []
    if not conferencias:
        erros.append("Relatório sem prova não sai: informe 'prova.conferencias'.")
    for conf in conferencias:
        if not conf.get("nome"):
            erros.append("Conferência sem nome.")
        manual = "fechou" in conf
        if manual and not conf.get("detalhe"):
            erros.append(f"Conferência '{conf.get('nome')}': quando informa 'fechou', precisa de 'detalhe' com o que foi conferido.")
        if not manual and ("esperado" not in conf or "obtido" not in conf):
            erros.append(f"Conferência '{conf.get('nome')}': informe esperado e obtido, ou fechou e detalhe.")
    if not isinstance(rel.get("premissas"), dict):
        erros.append("Falta 'premissas' (filtros, qualidade, indisponiveis).")
    for indice, bloco in enumerate(rel.get("blocos") or []):
        _validar_bloco(bloco, indice, erros)
    if any(CPF.search(t) for t in _textos(rel)):
        erros.append("Há CPF sem máscara no relatório. Use ***.123.456-**.")
    return erros


# ---------- prova ----------

def avaliar_prova(prova) -> list[dict]:
    base = prova.get("tolerancia_pct", TOLERANCIA_PADRAO)
    saida = []
    for conf in prova["conferencias"]:
        fmt = conf.get("formato", "moeda")
        if "fechou" in conf:
            saida.append({"nome": conf["nome"], "fechou": bool(conf["fechou"]), "esperado": "", "obtido": "",
                          "diferenca": conf["detalhe"], "numerica": False, "abs": 0.0, "formato": fmt})
            continue
        esperado, obtido = conf["esperado"], conf["obtido"]
        if not brand.e_numero(esperado) or not brand.e_numero(obtido):
            saida.append({"nome": conf["nome"], "fechou": False, "esperado": formatar(esperado, fmt), "obtido": formatar(obtido, fmt),
                          "diferenca": conf.get("motivo") or "Não foi possível conferir", "numerica": False, "abs": 0.0, "formato": fmt})
            continue
        tol = conf.get("tolerancia_pct", base)
        dif = obtido - esperado
        fechou = abs(dif) <= 0.005 if (tol == 0 or esperado == 0) else abs(dif) / abs(esperado) * 100 <= tol
        saida.append({"nome": conf["nome"], "fechou": fechou, "esperado": formatar(esperado, fmt), "obtido": formatar(obtido, fmt),
                      "diferenca": formatar(round(dif, 6), fmt), "numerica": True, "abs": abs(dif), "formato": fmt})
    return saida


def selo_prova(resultado) -> str:
    numericas = [r for r in resultado if r["numerica"] and r["formato"] == "moeda"]
    if numericas:
        return "Prova fechada, diferença de " + brand.moeda(max(r["abs"] for r in numericas))
    return "Prova fechada"


# ---------- gráficos ----------

def _eixo(valor, formato):
    if formato == "moeda":
        return brand.moeda_compacta(valor)
    if formato == "pct":
        return brand.pct(valor, 0)
    return brand.numero(valor, 0)


def _escala(minimo, maximo, passos=4):
    minimo, maximo = min(minimo, 0), max(maximo, 0)
    if minimo == maximo:
        maximo = 1
    bruto = (maximo - minimo) / passos
    potencia = 10 ** math.floor(math.log10(bruto))
    for fator in (1, 2, 2.5, 5, 10):
        passo = fator * potencia
        if passo >= bruto:
            break
    baixo = math.floor(minimo / passo) * passo
    alto = math.ceil(maximo / passo) * passo
    ticks, atual = [], baixo
    while atual <= alto + passo / 1000:
        ticks.append(atual)
        atual += passo
    return baixo, alto, ticks


def _pareto_pontos(bloco, cortes):
    extras = []
    for par in bloco.get("pontos") or []:
        if isinstance(par, (list, tuple)) and len(par) == 2 and all(brand.e_numero(v) for v in par):
            x, y = float(par[0]), float(par[1])
            if 0 <= x <= 100 and 0 <= y <= 100:
                extras.append((x, y))
    pontos = sorted(set([(0.0, 0.0)] + cortes + extras))
    # Curva acumulada só sobe: descarta ponto fora de ordem.
    saida, topo = [], -1.0
    for x, y in pontos:
        if y >= topo:
            saida.append((x, y))
            topo = y
    return saida


def svg_pareto(bloco):
    x0, y0, w, h = 56, 18, 644, 244
    fx = lambda p: x0 + w * p / 100
    fy = lambda p: y0 + h * (1 - p / 100)
    classes = bloco["classes"]
    total_itens = sum(c["itens"] for c in classes) or 1
    total_valor = sum(c["valor"] for c in classes) or 1
    cortes, acum_i, acum_v = [], 0.0, 0.0
    for c in classes:
        acum_i += c["itens"]
        acum_v += c["valor"]
        cortes.append((100 * acum_i / total_itens, 100 * acum_v / total_valor))
    linha = " ".join(f"{fx(a):.1f},{fy(b):.1f}" for a, b in _pareto_pontos(bloco, cortes))
    partes, inicio = [], 0.0
    cores = ("var(--band-a)", "var(--band-b)", "var(--band-c)")
    for i, (x, _) in enumerate(cortes):
        partes.append(f'<rect x="{fx(inicio):.1f}" y="{y0}" width="{fx(x) - fx(inicio):.1f}" height="{h}" fill="{cores[min(i, 2)]}"/>')
        inicio = x
    for p in range(0, 101, 20):
        partes.append(f'<line x1="{x0}" x2="{x0 + w}" y1="{fy(p):.1f}" y2="{fy(p):.1f}" stroke="var(--hairline)" opacity=".55"/>'
                      f'<text x="{x0 - 8}" y="{fy(p) + 4:.1f}" text-anchor="end" class="t">{p}%</text>'
                      f'<text x="{fx(p):.1f}" y="{y0 + h + 18}" text-anchor="middle" class="t">{p}%</text>')
    inicio = 0.0
    for c, (x, _) in zip(classes, cortes):
        partes.append(f'<text x="{(fx(inicio) + fx(x)) / 2:.1f}" y="{fy(6):.1f}" text-anchor="middle" class="tb">{esc(c.get("classe", ""))}</text>')
        inicio = x
    partes.append(f'<polyline points="{linha}" fill="none" stroke="var(--chart-1)" stroke-width="3" stroke-linejoin="round"/>')
    nome_itens = bloco.get("rotulo_itens", "itens")
    ultimo_y = None
    for x, y in cortes[:-1]:
        partes.append(f'<circle cx="{fx(x):.1f}" cy="{fy(y):.1f}" r="5" fill="var(--chart-1)"/>')
        if ultimo_y is not None and abs(fy(y) - ultimo_y) < 18:
            continue
        ultimo_y = fy(y)
        direita = x > 55
        ancora = ' text-anchor="end"' if direita else ""
        tx = fx(x) - 12 if direita else fx(x) + 12
        partes.append(f'<text x="{tx:.1f}" y="{fy(y) + 22:.1f}"{ancora} class="tv">{brand.pct(x)} dos {esc(nome_itens)}, {brand.pct(y)} do total</text>')
    partes.append(f'<text x="{x0 + w / 2}" y="{y0 + h + 38}" text-anchor="middle" class="t">% acumulado dos {esc(nome_itens)}</text>')
    legenda = f"Curva ABC: {brand.pct(cortes[0][0])} dos {nome_itens} somam {brand.pct(cortes[0][1])} do total"
    return f'<div class="rola"><svg class="grafico" viewBox="0 0 720 306" role="img" aria-label="{esc(legenda)}">{"".join(partes)}</svg></div>'


def tabela_classes(bloco):
    classes = bloco["classes"]
    fmt = bloco.get("formato", "moeda")
    total_i = sum(c["itens"] for c in classes) or 1
    total_v = sum(c["valor"] for c in classes) or 1
    colunas = [{"campo": "classe", "rotulo": "Classe", "formato": "classe"}, {"campo": "itens", "rotulo": "Itens", "formato": "inteiro"},
               {"campo": "pi", "rotulo": "% dos itens", "formato": "pct"}, {"campo": "valor", "rotulo": "Valor", "formato": fmt},
               {"campo": "pv", "rotulo": "% do valor", "formato": "pct"}]
    linhas = [{"classe": c.get("classe"), "itens": c["itens"], "pi": 100 * c["itens"] / total_i, "valor": c["valor"], "pv": 100 * c["valor"] / total_v} for c in classes]
    return colunas, linhas, {"classe": "Total", "itens": total_i, "pi": 100.0, "valor": total_v, "pv": 100.0}


def svg_linha(bloco):
    fmt = bloco.get("formato", "moeda")
    pontos = bloco["pontos"]
    series = bloco.get("series") or {}
    tem_b = any(brand.e_numero(p.get("anterior")) for p in pontos)
    valores = [p["atual"] for p in pontos] + [p["anterior"] for p in pontos if brand.e_numero(p.get("anterior"))]
    baixo, alto, ticks = _escala(min(valores), max(valores))
    x0, y0, w, h = 72, 14, 632, 196
    n = max(1, len(pontos) - 1)
    fx = lambda i: x0 + w * i / n
    fy = lambda v: y0 + h * (1 - (v - baixo) / (alto - baixo))
    partes = []
    for t in ticks:
        partes.append(f'<line x1="{x0}" x2="{x0 + w}" y1="{fy(t):.1f}" y2="{fy(t):.1f}" stroke="var(--hairline)" opacity=".55"/>'
                      f'<text x="{x0 - 8}" y="{fy(t) + 4:.1f}" text-anchor="end" class="t">{esc(_eixo(t, fmt))}</text>')
    passo = max(1, round(len(pontos) / 6))
    for i, p in enumerate(pontos):
        if i % passo == 0:
            rotulo = brand.data_br(p.get("x", ""))
            rotulo = rotulo[:5] if len(rotulo) == 10 and rotulo[2] == "/" else rotulo
            partes.append(f'<text x="{fx(i):.1f}" y="{y0 + h + 18}" text-anchor="middle" class="t">{esc(rotulo)}</text>')
    if tem_b:
        trilha = " ".join(f"{fx(i):.1f},{fy(p['anterior']):.1f}" for i, p in enumerate(pontos) if brand.e_numero(p.get("anterior")))
        partes.append(f'<polyline points="{trilha}" fill="none" stroke="var(--chart-2)" stroke-width="2"/>')
    trilha = " ".join(f"{fx(i):.1f},{fy(p['atual']):.1f}" for i, p in enumerate(pontos))
    partes.append(f'<polyline points="{trilha}" fill="none" stroke="var(--chart-1)" stroke-width="3" stroke-linejoin="round"/>')
    partes.append(f'<circle cx="{fx(len(pontos) - 1):.1f}" cy="{fy(pontos[-1]["atual"]):.1f}" r="5" fill="var(--chart-1)"/>')
    legenda = ""
    if tem_b:
        legenda = (f'<div class="legenda-g"><span><i style="background:var(--chart-1)"></i>{esc(series.get("atual", "Período atual"))}</span>'
                   f'<span><i style="background:var(--chart-2)"></i>{esc(series.get("anterior", "Período anterior"))}</span></div>')
    return f'{legenda}<div class="rola"><svg class="grafico" viewBox="0 0 720 236" role="img" aria-label="{esc(bloco["titulo"])}">{"".join(partes)}</svg></div>'


def _quebra(texto, limite=15):
    linhas, atual = [], ""
    for palavra in str(texto).split():
        if atual and len(atual) + 1 + len(palavra) > limite:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    linhas.append(atual)
    if len(linhas) > 2:
        linhas = [linhas[0], linhas[1][: limite - 3] + "..."]
    return linhas


def svg_cascata(bloco):
    fmt = bloco.get("formato", "moeda")
    etapas = bloco["etapas"]
    faixas, corrente = [], 0.0
    for e in etapas:
        if e["tipo"] == "delta":
            inicio, corrente = corrente, corrente + e["valor"]
            faixas.append((inicio, corrente))
        else:
            corrente = e["valor"]
            faixas.append((0.0, corrente))
    baixo, alto, ticks = _escala(min(min(f) for f in faixas), max(max(f) for f in faixas))
    x0, y0, w, h = 72, 24, 632, 196
    fy = lambda v: y0 + h * (1 - (v - baixo) / (alto - baixo))
    largura = w / len(etapas)
    partes = []
    for t in ticks:
        partes.append(f'<line x1="{x0}" x2="{x0 + w}" y1="{fy(t):.1f}" y2="{fy(t):.1f}" stroke="var(--hairline)" opacity=".55"/>'
                      f'<text x="{x0 - 8}" y="{fy(t) + 4:.1f}" text-anchor="end" class="t">{esc(_eixo(t, fmt))}</text>')
    for i, (e, (a, b)) in enumerate(zip(etapas, faixas)):
        x = x0 + i * largura + largura * .18
        topo, base = max(a, b), min(a, b)
        if e["tipo"] != "delta":
            cor = "var(--chart-1)"
        else:
            cor = "var(--up)" if e["valor"] >= 0 else "var(--down)"
        altura = max(fy(base) - fy(topo), 1)
        partes.append(f'<rect x="{x:.1f}" y="{fy(topo):.1f}" width="{largura * .64:.1f}" height="{altura:.1f}" rx="3" fill="{cor}"/>')
        centro = x0 + i * largura + largura / 2
        partes.append(f'<text x="{centro:.1f}" y="{fy(topo) - 6:.1f}" text-anchor="middle" class="tv">{esc(_eixo(e["valor"], fmt))}</text>')
        for j, linha in enumerate(_quebra(e.get("rotulo", ""))):
            partes.append(f'<text x="{centro:.1f}" y="{y0 + h + 18 + j * 14}" text-anchor="middle" class="t">{esc(linha)}</text>')
    return f'<div class="rola"><svg class="grafico" viewBox="0 0 720 268" role="img" aria-label="{esc(bloco["titulo"])}">{"".join(partes)}</svg></div>'


# ---------- HTML ----------

def _classe_html(valor):
    texto = str(valor)
    return f'<span class="cl cl-{esc(texto.lower())}">{esc(texto)}</span>' if texto in ("A", "B", "C") else esc(texto)


def _celula(col, linha):
    valor = linha.get(col["campo"])
    fmt = col.get("formato")
    return _classe_html(valor) if fmt == "classe" and valor is not None else esc(formatar(valor, fmt))


def _alerta(col, valor):
    if not brand.e_numero(valor):
        return False
    return ("alerta_abaixo" in col and valor < col["alerta_abaixo"]) or ("alerta_acima" in col and valor > col["alerta_acima"])


def tabela_html(colunas, linhas, total=None):
    classe_n = ' class="n"'
    head = "".join(f'<th scope="col"{classe_n if c.get("formato") in NUMERICOS else ""}>{esc(c["rotulo"])}</th>' for c in colunas)
    corpo = []
    def tds(linha, com_alerta):
        saida = [f'<th scope="row">{_celula(colunas[0], linha)}</th>']
        for col in colunas[1:]:
            classes = []
            if col.get("formato") in NUMERICOS:
                classes.append("n")
            if com_alerta and _alerta(col, linha.get(col["campo"])):
                classes.append("alerta")
            attr = f' class="{" ".join(classes)}"' if classes else ""
            saida.append(f'<td{attr} data-label="{esc(col["rotulo"])}">{_celula(col, linha)}</td>')
        return "".join(saida)
    for linha in linhas:
        corpo.append(f"<tr>{tds(linha, True)}</tr>")
    pe = ""
    if total:
        cols_total = dict(total)
        saida = [f'<th scope="row">{esc(cols_total.get(colunas[0]["campo"], "Total"))}</th>']
        for col in colunas[1:]:
            cls = ' class="n"' if col.get("formato") in NUMERICOS else ""
            valor = cols_total.get(col["campo"])
            saida.append(f'<td{cls} data-label="{esc(col["rotulo"])}">{"" if valor is None else esc(formatar(valor, col.get("formato")))}</td>')
        pe = f'<tfoot><tr>{"".join(saida)}</tr></tfoot>'
    return f'<table class="tabela"><thead><tr>{head}</tr></thead><tbody>{"".join(corpo)}</tbody>{pe}</table>'


def barras_html(bloco):
    linhas = bloco["linhas"]
    fmt = bloco.get("formato", "moeda")
    topo = max(abs(l["valor"]) for l in linhas) or 1
    total = sum(l["valor"] for l in linhas)
    tem_var = any(brand.e_numero(l.get("var_pct")) for l in linhas)
    melhor_baixa = bloco.get("melhor") == "baixa"
    saida = []
    for l in linhas:
        extra = ""
        if tem_var:
            v = l.get("var_pct")
            if brand.e_numero(v):
                bom = (v <= 0) if melhor_baixa else (v >= 0)
                extra = f'<span class="var {"up" if bom else "down"}">{"+" if v > 0 else ""}{brand.pct(v)}</span>'
            else:
                extra = '<span class="var"></span>'
        part = brand.pct(100 * l["valor"] / total) if total else ""
        saida.append(f'<div class="barra{" com-var" if tem_var else ""}"><span class="b-nome">{esc(l.get("rotulo", ""))}</span>'
                     f'<span class="b-trilho"><span class="b-ench" style="width:{100 * abs(l["valor"]) / topo:.1f}%"></span></span>'
                     f'<span class="b-val">{esc(formatar(l["valor"], fmt))}</span><span class="b-pct">{part}</span>{extra}</div>')
    return f'<div class="barras">{"".join(saida)}</div>'


def _bloco_html(bloco, indice):
    tid = f"b{indice}"
    tipo = bloco["tipo"]
    nota = f'<p class="body-sm mut">{esc(bloco["nota"])}</p>' if bloco.get("nota") else ""
    titulo = f'<div class="secao-topo"><h2 class="heading-md" id="{tid}">{esc(bloco["titulo"])}</h2>{nota}</div>'
    if tipo == "tabela":
        linhas = bloco["linhas"]
        corte = ""
        if len(linhas) > MAX_LINHAS_PAGINA:
            corte = f'<p class="legenda-g">Mostrando {MAX_LINHAS_PAGINA} de {brand.numero(len(linhas))} linhas. O restante vai na planilha.</p>'
        vazio = '<p class="body-sm mut">Sem linhas neste recorte.</p>' if not linhas else ""
        tab = tabela_html(bloco["colunas"], linhas[:MAX_LINHAS_PAGINA], bloco.get("total")) if linhas else ""
        return f'<section class="secao" aria-labelledby="{tid}">{titulo}{vazio}{tab}{corte}</section>'
    if tipo == "pareto":
        corpo = svg_pareto(bloco) + tabela_html(*tabela_classes(bloco))
    elif tipo == "barras":
        corpo = barras_html(bloco)
    elif tipo == "linha":
        corpo = svg_linha(bloco)
    else:
        corpo = svg_cascata(bloco)
    return f'<section class="bloco b-raised" aria-labelledby="{tid}">{titulo}{corpo}</section>'


def _numeros_html(numeros):
    if not numeros:
        return ""
    itens = []
    for i, n in enumerate(numeros):
        cls = "stat num" if i == 0 else "stat stat-sm num"
        itens.append(f'<div><p class="{cls}">{esc(formatar(n.get("valor"), n.get("formato")))}</p><p class="stat-line">{esc(n.get("legenda", ""))}</p></div>')
    return f'<div class="veredito-numeros">{"".join(itens)}</div>'


def _hero_html(rel, resultado):
    veredito = rel["veredito"]
    sub = f'<p class="veredito-sub">{esc(veredito["texto"])}</p>' if veredito.get("texto") else ""
    falhas = [r for r in resultado if not r["fechou"]]
    if not falhas:
        return (f'<section class="bloco b-brand" aria-labelledby="v"><span class="selo">{CHECK}{esc(selo_prova(resultado))}</span>'
                f'<h1 class="display-lg" id="v">{esc(veredito["titulo"])}</h1>{sub}{_numeros_html(veredito.get("numeros"))}</section>')
    f = falhas[0]
    resto = f" e mais {len(falhas) - 1} conferência(s)" if len(falhas) > 1 else ""
    numeros = ""
    if f["esperado"]:
        numeros = (f'<div class="veredito-numeros"><div><p class="stat stat-sm num">{esc(f["esperado"])}</p><p class="stat-line">esperado</p></div>'
                   f'<div><p class="stat stat-sm num">{esc(f["obtido"])}</p><p class="stat-line">obtido</p></div>'
                   f'<div><p class="stat stat-sm num">{esc(f["diferenca"])}</p><p class="stat-line">diferença</p></div></div>')
    alerta = (f'<section class="bloco b-red" role="alert" aria-labelledby="v"><span class="selo">Prova não fechou</span>'
              f'<h1 class="display-lg" id="v">Este relatório ainda não fechou</h1>'
              f'<p class="veredito-sub">{esc(f["nome"])}{esc(resto)}. Investigue a diferença antes de decidir com os números abaixo.</p>{numeros}</section>')
    pendente = (f'<section class="bloco b-raised" aria-labelledby="v2"><p class="eyebrow">O QUE OS NÚMEROS INDICAM, A CONFERIR</p>'
                f'<h2 class="heading-md" id="v2">{esc(veredito["titulo"])}</h2>{sub}{_numeros_html(veredito.get("numeros"))}</section>')
    return alerta + pendente


def _resumo_html(resumo):
    itens = []
    for r in resumo:
        linha = f'<p class="stat-line">{esc(r["legenda"])}</p>' if r.get("legenda") else ""
        itens.append(f'<article class="bloco b-raised kpi"><h3 class="label mut">{esc(r.get("rotulo", ""))}</h3>'
                     f'<p class="stat-sm num">{esc(formatar(r.get("valor"), r.get("formato")))}</p>{linha}</article>')
    colunas = "c4" if len(resumo) == 4 else "c3"
    return f'<section class="kpis {colunas}" aria-label="Resumo">{"".join(itens)}</section>'


def _leitura_html(leitura):
    itens = "".join(f'<li><span class="nv nv-{esc(i["nivel"])}">{NIVEIS[i["nivel"]]}</span><span>{esc(i["texto"])}</span></li>' for i in leitura)
    return ('<section class="bloco b-brand leitura" aria-labelledby="t-leitura"><span class="grifo">DO SEU BANCO</span>'
            f'<h2 class="heading-md" id="t-leitura">Leitura</h2><ol class="leit">{itens}</ol></section>')


def _prova_html(prova, resultado):
    linhas = []
    for r in resultado:
        pill = f'<span class="pill ok">{CHECK}Fechou</span>' if r["fechou"] else '<span class="pill falha">Não fechou</span>'
        linhas.append(f'<tr><th scope="row">{esc(r["nome"])}</th><td class="n" data-label="Esperado">{esc(r["esperado"])}</td>'
                      f'<td class="n" data-label="Obtido">{esc(r["obtido"])}</td><td class="n" data-label="Diferença">{esc(r["diferenca"])}</td>'
                      f'<td data-label="Situação">{pill}</td></tr>')
    tol = brand.numero(prova.get("tolerancia_pct", TOLERANCIA_PADRAO), 1).replace(",0", "")
    return ('<section class="bloco b-raised" aria-labelledby="t-prova"><div class="secao-topo"><h2 class="heading-md" id="t-prova">Prova</h2>'
            f'<p class="body-sm mut">Tolerância de {tol}%, salvo indicação na conferência.</p></div>'
            '<table class="tabela"><thead><tr><th scope="col">Conferência</th><th scope="col" class="n">Esperado</th><th scope="col" class="n">Obtido</th>'
            f'<th scope="col" class="n">Diferença</th><th scope="col">Situação</th></tr></thead><tbody>{"".join(linhas)}</tbody></table></section>')


def _lista(titulo, itens):
    if not itens:
        return ""
    return f'<div><h3 class="label">{esc(titulo)}</h3><ul class="lista body-sm">{"".join(f"<li>{esc(i)}</li>" for i in itens)}</ul></div>'


def _indisponiveis(premissas):
    saida = []
    for item in premissas.get("indisponiveis") or []:
        saida.append(f'{item.get("item", "")}: {item.get("motivo", "")}' if isinstance(item, dict) else str(item))
    return saida


def _premissas_html(premissas):
    colunas = _lista("Filtros e significados", premissas.get("filtros")) + _lista("Qualidade do dado", premissas.get("qualidade")) + _lista("O que ficou de fora", _indisponiveis(premissas))
    sql = ""
    if premissas.get("consulta"):
        sql = f'<details class="sql"><summary>Ver a consulta usada</summary><pre>{esc(premissas["consulta"])}</pre></details>'
    return ('<section class="bloco b-raised" aria-labelledby="t-prem"><h2 class="heading-md" id="t-prem">Premissas e qualidade do dado</h2>'
            f'<div class="duas">{colunas}</div>{sql}</section>')


def _proximos_html(proximos):
    if not proximos:
        return ""
    itens = "".join(f'<article class="bloco b-raised ponte"><span class="tag">{esc(p.get("tag", ""))}</span><h2 class="heading-sm">{esc(p.get("titulo", ""))}</h2>'
                    f'<p class="body-sm">{esc(p.get("texto", ""))}</p></article>' for p in proximos[:2])
    return f'<section class="pontes" aria-label="Próximos passos">{itens}</section>'


def _fonte_texto(rel):
    f = rel["fonte"]
    return f'Banco {f["banco"]} ({f["engine"]}), via {f["conector"]}'


def render_html(rel, tema="auto"):
    resultado = avaliar_prova(rel["prova"])
    recorte = rel["recorte"]
    gerado = brand.data_br(rel["gerado_em"])
    topo = (f'<header class="topo"><div>{brand.logo_html()}</div><div class="topo-meta"><p class="eyebrow">{esc(("ARCHEO · " + rel["area"]).upper())}</p>'
            f'<p class="para">{esc(rel["cliente"])}</p><p class="caption">{esc(_fonte_texto(rel))}. Gerado em {esc(gerado)}.</p></div></header>')
    avisos = ([AVISO_CONFERENCIA] if rel.get("conferencia") else []) + list(rel.get("avisos") or [])
    avisos_html = "".join(f'<p class="aviso-topo" role="note">{esc(a)}</p>' for a in avisos)
    dl = "".join(f"<div><dt>{r}</dt><dd>{esc(recorte[c])}</dd></div>" for r, c in (("Unidade", "unidade"), ("Período", "periodo"), ("Recorte", "filtros"), ("Nível", "nivel")))
    corpo = [topo, avisos_html, _hero_html(rel, resultado), f'<dl class="recorte">{dl}</dl>', _resumo_html(rel["resumo"]), _leitura_html(rel["leitura"])]
    corpo += [_bloco_html(b, i) for i, b in enumerate(rel.get("blocos") or [])]
    corpo += [_prova_html(rel["prova"], resultado), _premissas_html(rel["premissas"]), _proximos_html(rel.get("proximos")), brand.footer_html(rel["gerado_em"])]
    valores = {
        "THEME_ATTR": f' data-theme="{tema}"' if tema in ("light", "dark") else "",
        "COLOR_SCHEME": tema if tema in ("light", "dark") else "light dark",
        "TITULO": esc(f'{rel["titulo"]}: {rel["cliente"]}'),
        "FONT_FACE": brand.font_face(),
        "TOKENS_CSS": brand.tokens_css(),
        "CONTEUDO": "".join(corpo),
    }
    # Passada única: texto vindo do banco nunca é tratado como marcador.
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: valores.get(m.group(1), m.group(0)), TEMPLATE.read_text(encoding="utf-8"))


# ---------- texto ----------

def _md(texto):
    return str(texto).replace("|", "\\|").replace("\n", " ")


def _linhas_bloco(bloco):
    """Colunas, linhas e total de um bloco, para saídas em texto."""
    tipo = bloco["tipo"]
    if tipo == "tabela":
        return bloco["colunas"], bloco["linhas"], bloco.get("total")
    if tipo == "pareto":
        return tabela_classes(bloco)
    if tipo == "barras":
        fmt = bloco.get("formato", "moeda")
        colunas = [{"campo": "rotulo", "rotulo": "Item"}, {"campo": "valor", "rotulo": "Valor", "formato": fmt}]
        if any(brand.e_numero(l.get("var_pct")) for l in bloco["linhas"]):
            colunas.append({"campo": "var_pct", "rotulo": "Variação", "formato": "pct"})
        return colunas, bloco["linhas"], None
    if tipo == "linha":
        fmt = bloco.get("formato", "moeda")
        series = bloco.get("series") or {}
        colunas = [{"campo": "x", "rotulo": "Período", "formato": "data"}, {"campo": "atual", "rotulo": series.get("atual", "Atual"), "formato": fmt}]
        if any(brand.e_numero(p.get("anterior")) for p in bloco["pontos"]):
            colunas.append({"campo": "anterior", "rotulo": series.get("anterior", "Anterior"), "formato": fmt})
        return colunas, bloco["pontos"], None
    return [{"campo": "rotulo", "rotulo": "Etapa"}, {"campo": "valor", "rotulo": "Valor", "formato": bloco.get("formato", "moeda")}], bloco["etapas"], None


def _md_tabela(colunas, linhas, total=None):
    def celula(col, linha):
        return _md(formatar(linha.get(col["campo"]), None if col.get("formato") == "classe" else col.get("formato")))
    saida = ["| " + " | ".join(_md(c["rotulo"]) for c in colunas) + " |", "|" + "|".join("---" for _ in colunas) + "|"]
    for linha in linhas:
        saida.append("| " + " | ".join(celula(c, linha) for c in colunas) + " |")
    if total:
        saida.append("| " + " | ".join("" if total.get(c["campo"]) is None else celula(c, total) for c in colunas) + " |")
    return saida


def render_markdown(rel):
    resultado = avaliar_prova(rel["prova"])
    recorte = rel["recorte"]
    f = rel["fonte"]
    fechou = all(r["fechou"] for r in resultado)
    saida = [f'**{rel["titulo"]}**', f'Banco: {f["banco"]} ({f["engine"]}), via {f["conector"]}',
             f'Recorte: {recorte["unidade"]} | {recorte["periodo"]} | {recorte["filtros"]} | {recorte["nivel"]}', ""]
    if rel.get("conferencia"):
        saida += [AVISO_CONFERENCIA, ""]
    saida += [str(a) for a in rel.get("avisos") or []] + ([""] if rel.get("avisos") else [])
    if not fechou:
        falha = next(r for r in resultado if not r["fechou"])
        saida += [f'**A prova não fechou: {falha["nome"]}.** Investigue a diferença antes de decidir com os números abaixo.', ""]
    saida += [f'**{rel["veredito"]["titulo"]}**'] + ([rel["veredito"]["texto"]] if rel["veredito"].get("texto") else []) + [""]
    saida += ["**Resumo**"] + [f'- {r.get("rotulo", "")}: {formatar(r.get("valor"), r.get("formato"))}' + (f' ({r["legenda"]})' if r.get("legenda") else "") for r in rel["resumo"]] + [""]
    if rel.get("blocos"):
        saida.append("**Relatório**")
        for bloco in rel["blocos"]:
            colunas, linhas, total = _linhas_bloco(bloco)
            saida += ["", f'*{bloco["titulo"]}*']
            saida += _md_tabela(colunas, linhas[:MAX_LINHAS_PAGINA], total)
            if len(linhas) > MAX_LINHAS_PAGINA:
                saida.append(f"Mostrando {MAX_LINHAS_PAGINA} de {brand.numero(len(linhas))} linhas. O restante vai na planilha.")
        saida.append("")
    saida += ["**Leitura**"] + [f'{i}. {item["texto"]}' for i, item in enumerate(rel["leitura"], 1)] + [""]
    saida += ["**Prova**"]
    for r in resultado:
        estado = "fechou" if r["fechou"] else "não fechou"
        detalhe = f'esperado {r["esperado"]}, obtido {r["obtido"]}, diferença {r["diferenca"]}' if r["esperado"] else r["diferenca"]
        saida.append(f'- {r["nome"]}: {estado} ({detalhe})')
    saida += ["", "**Premissas e qualidade do dado**"]
    premissas = rel["premissas"]
    saida += [f"- {t}" for t in (premissas.get("filtros") or []) + (premissas.get("qualidade") or []) + _indisponiveis(premissas)]
    saida += ["", brand.footer_text(rel["gerado_em"])]
    return "\n".join(saida) + "\n"


def render_whatsapp(rel):
    resultado = avaliar_prova(rel["prova"])
    fechou = all(r["fechou"] for r in resultado)
    prova = selo_prova(resultado).replace("Prova fechada", "fechou") if fechou else "NÃO FECHOU, a conferir antes de decidir"
    recorte = rel["recorte"]
    saida = [f'*{rel["area"]}: {rel["cliente"]}*', f'{rel["titulo"]}, {recorte["periodo"]}, {recorte["unidade"]}', "", f'*{rel["veredito"]["titulo"]}*']
    numeros = rel["veredito"].get("numeros") or []
    if numeros:
        saida.append(f'{numeros[0].get("legenda", "").capitalize()}: {formatar(numeros[0].get("valor"), numeros[0].get("formato"))}.')
    saida += ["", "O que olhar primeiro:"]
    saida += [f'{i}. {item["texto"]}' for i, item in enumerate(rel["leitura"][:3], 1)]
    saida += ["", f"Prova: {prova}."]
    saida += ["", brand.footer_text(rel["gerado_em"])]
    return "\n".join(saida) + "\n"


def _csv_texto(valor):
    texto = "" if valor is None else str(valor)
    # Texto vindo do banco não pode virar fórmula na planilha.
    if texto[:1] in ("=", "+", "-", "@", "\t", "\r"):
        texto = "'" + texto
    if any(c in texto for c in (";", '"', "\n", "\r")):
        return '"' + texto.replace('"', '""') + '"'
    return texto


def _csv_valor(valor, formato):
    if brand.e_numero(valor):
        casas = 2 if formato in ("moeda", "decimal", "pct", "pp") else (0 if float(valor).is_integer() else 2)
        return f"{valor:.{casas}f}".replace(".", ",")
    return _csv_texto(formatar(valor, formato) if formato == "data" else valor)


def render_csv(rel):
    resultado = avaliar_prova(rel["prova"])
    linhas = [[_csv_texto(rel["titulo"]), _csv_texto(rel["cliente"])], [_csv_texto(_fonte_texto(rel))]]
    recorte = rel["recorte"]
    linhas.append([_csv_texto(f'{recorte["unidade"]} | {recorte["periodo"]} | {recorte["filtros"]} | {recorte["nivel"]}')])
    linhas += [[], ["Resumo"]] + [[_csv_texto(r.get("rotulo")), _csv_valor(r.get("valor"), r.get("formato"))] for r in rel["resumo"]]
    for bloco in rel.get("blocos") or []:
        colunas, dados, total = _linhas_bloco(bloco)
        linhas += [[], [_csv_texto(bloco["titulo"])], [_csv_texto(c["rotulo"]) for c in colunas]]
        linhas += [[_csv_valor(d.get(c["campo"]), c.get("formato")) for c in colunas] for d in dados]
        if total:
            linhas.append([_csv_valor(total.get(c["campo"]), c.get("formato")) for c in colunas])
    linhas += [[], ["Prova"], ["Conferência", "Esperado", "Obtido", "Diferença", "Situação"]]
    linhas += [[_csv_texto(r["nome"]), _csv_texto(r["esperado"]), _csv_texto(r["obtido"]), _csv_texto(r["diferenca"]), "Fechou" if r["fechou"] else "Não fechou"] for r in resultado]
    premissas = rel["premissas"]
    linhas += [[], ["Premissas"]] + [[_csv_texto(t)] for t in (premissas.get("filtros") or []) + (premissas.get("qualidade") or []) + _indisponiveis(premissas)]
    linhas += [[], [_csv_texto(brand.footer_text(rel["gerado_em"]).replace("\n", ". "))]]
    return "\ufeff" + "\r\n".join(";".join(l) for l in linhas) + "\r\n"


def render(rel, formato, tema="auto"):
    if formato == "html":
        return render_html(rel, tema)
    if formato == "csv":
        return render_csv(rel)
    if formato == "whatsapp":
        return render_whatsapp(rel)
    return render_markdown(rel)


def _falha(erros) -> int:
    print(json.dumps({"errors": erros}, ensure_ascii=False, indent=1))
    return 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", help="JSON do relatório (padrão: stdin)")
    parser.add_argument("--format", required=True, choices=SAIDAS)
    parser.add_argument("--theme", default="auto", choices=TEMAS)
    parser.add_argument("--output", help="grava neste arquivo em vez de imprimir")
    args = parser.parse_args(argv)
    try:
        bruto = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
        rel = json.loads(bruto)
    except (OSError, json.JSONDecodeError) as exc:
        return _falha([f"Não consegui ler o JSON do relatório: {exc}"])
    erros = validar(rel)
    if erros:
        return _falha(erros)
    saida = render(rel, args.format, args.theme)
    if not args.output:
        sys.stdout.write(saida)
        return 0
    Path(args.output).write_text(saida, encoding="utf-8", newline="")
    fechou = all(r["fechou"] for r in avaliar_prova(rel["prova"]))
    print(f"OK: {args.output} ({len(saida) // 1024} KB). Prova: {'fechou' if fechou else 'NÃO FECHOU'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
