"""Kit de marca CD2 Tech das entregas do plugin archeo.

Só biblioteca padrão. O sync copia este arquivo para scripts/ de cada skill e os
arquivos de marca para assets/, por isso tudo é lido de ../assets relativo a
este arquivo. Valores vindos do Design System CD2 Tech: cores, tipografia, raios.
"""
from __future__ import annotations

import base64
import html
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

CORES = {
    "blue-retail": "#0000ff",
    "blue-tech": "#3c1fff",
    "white-human": "#f2f2f2",
    "black-agile": "#000000",
    "blue-experience": "#011e80",
    "blue-qwerty": "#0333f7",
    "blue-sky": "#019eff",
    "purple-shift": "#210e9e",
    "frente-lilas": "#8a72ff",
    "gray-tech": "#6a717f",
    "gray-solution": "#a1a6ae",
    "yellow-like": "#dbff2a",
    "frente-neutro-escuro": "#464a53",
}

FORMATOS = ("moeda", "inteiro", "decimal", "pct", "pp", "dias", "data", "texto")
SEM_DADO = "s/d"


def esc(texto) -> str:
    return html.escape(str(texto), quote=True)


def _arredonda(valor, casas: int) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def numero(valor, casas: int = 0) -> str:
    dec = _arredonda(abs(valor), casas)
    inteiro, _, frac = f"{dec:.{casas}f}".partition(".")
    corpo = f"{int(inteiro):,}".replace(",", ".") + ("," + frac if casas else "")
    return ("-" if valor < 0 and dec != 0 else "") + corpo


def moeda(valor) -> str:
    texto = numero(abs(valor), 2)
    return ("-" if valor < 0 and texto != "0,00" else "") + "R$ " + texto


def moeda_compacta(valor) -> str:
    sinal = "-" if valor < 0 else ""
    v = abs(valor)
    if v >= 1e6:
        return f"{sinal}R$ {numero(v / 1e6, 1)} mi"
    if v >= 1000:
        return f"{sinal}R$ {numero(v / 1000, 0)} mil"
    return f"{sinal}R$ {numero(v, 0)}"


def pct(valor, casas: int = 1) -> str:
    return numero(valor, casas) + "%"


def data_br(iso) -> str:
    texto = str(iso)
    if len(texto) >= 10 and texto[4] == "-" and texto[7] == "-":
        return f"{texto[8:10]}/{texto[5:7]}/{texto[:4]}"
    return texto


def e_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def formatar(valor, formato=None) -> str:
    if valor is None or valor == "":
        return SEM_DADO
    if formato == "data":
        return data_br(valor)
    if not e_numero(valor):
        return str(valor)
    if formato == "moeda":
        return moeda(valor)
    if formato == "decimal":
        return numero(valor, 2)
    if formato == "pct":
        return pct(valor)
    if formato == "pp":
        return numero(valor, 1) + " p.p."
    if formato == "dias":
        return numero(valor, 0) + " d"
    if formato == "inteiro":
        return numero(valor, 0)
    return numero(valor, 0) if float(valor).is_integer() else numero(valor, 2)


def _data_uri(caminho: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(caminho.read_bytes()).decode("ascii")


def font_face() -> str:
    uri = _data_uri(ASSETS / "fonts" / "Manrope-Variable.woff2", "font/woff2")
    return f"@font-face {{ font-family: 'Manrope'; src: url({uri}) format('woff2'); font-weight: 200 800; font-display: swap; }}"


def logo_html() -> str:
    """Os dois logos; tokens_css() mostra o certo conforme o tema de quem abre."""
    claro = _data_uri(ASSETS / "brand" / "cd2tech-horizontal.svg", "image/svg+xml")
    escuro = _data_uri(ASSETS / "brand" / "cd2tech-horizontal-white.svg", "image/svg+xml")
    return (f'<img class="cd2-logo cd2-logo-claro" src="{claro}" alt="CD2 Tech">'
            f'<img class="cd2-logo cd2-logo-escuro" src="{escuro}" alt="CD2 Tech">')


_ESCURO = """
  --surface: {black-agile}; --raised: #121212; --ink: {white-human}; --muted: {gray-solution};
  --link: {blue-sky}; --hairline: {frente-neutro-escuro}; --focus: {yellow-like};
  --up: #3ecf8a; --down: #ff8a80; --warn-ink: #ffb800;
  --chart-1: {blue-sky}; --chart-2: {gray-solution}; --track: #2a2a2e;
  --band-a: rgba(1, 158, 255, .20); --band-b: rgba(138, 114, 255, .12); --band-c: rgba(161, 166, 174, .07);
  --s1: #0b1730; --s2: {blue-experience}; --s3: {blue-qwerty}; --s4: {blue-sky}; --s5: #a5dcff;
  --cla: {blue-sky}; --on-cla: {black-agile}; --clb: {frente-lilas}; --on-clb: {black-agile};
  color-scheme: dark;
"""


def tokens_css() -> str:
    c = CORES
    escuro = _ESCURO.format(**c)
    return f"""
:root {{
  --surface: {c['white-human']}; --raised: #ffffff; --brand: {c['blue-retail']}; --ink: {c['black-agile']};
  --muted: {c['frente-neutro-escuro']}; --on-brand: {c['white-human']}; --link: {c['blue-retail']};
  --border: {c['gray-tech']}; --hairline: {c['gray-solution']}; --focus: {c['blue-tech']};
  --highlight: {c['yellow-like']}; --on-highlight: {c['black-agile']};
  --red: #c4281c; --on-red: #ffffff; --amber: #ffb800; --on-amber: #000000; --green: #13804a; --on-green: #ffffff;
  --up: #13804a; --down: #c4281c; --warn-ink: #8a5a00;
  --chart-1: {c['blue-retail']}; --chart-2: {c['gray-tech']}; --track: #d9d9de;
  --band-a: rgba(0, 0, 255, .10); --band-b: rgba(33, 14, 158, .06); --band-c: rgba(70, 74, 83, .05);
  --s1: #dfe0ff; --s2: #a9acff; --s3: #6a6eff; --s4: #2b30ff; --s5: #0000b8;
  --cla: {c['blue-retail']}; --on-cla: {c['white-human']}; --clb: {c['purple-shift']}; --on-clb: {c['white-human']};
  --r-sm: 6px; --r-md: 12px; --r-lg: 24px; --r-pill: 999px;
  --font: 'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{{escuro}}} }}
:root[data-theme="dark"] {{{escuro}}}
.cd2-logo {{ height: 28px; width: auto; display: block; }}
.cd2-logo-escuro {{ display: none; }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) .cd2-logo-escuro {{ display: block; }}
  :root:not([data-theme="light"]) .cd2-logo-claro {{ display: none; }}
}}
:root[data-theme="dark"] .cd2-logo-escuro {{ display: block; }}
:root[data-theme="dark"] .cd2-logo-claro {{ display: none; }}
.cd2-assinatura {{ display: flex; gap: 24px; align-items: center; margin-top: 8px; padding: 24px 0; border-top: 1px solid var(--border); }}
.cd2-assinatura-logo {{ flex: none; }}
.cd2-assinatura-aviso {{ margin: 0; font-size: 14px; line-height: 20px; color: var(--muted); }}
@media (max-width: 600px) {{ .cd2-assinatura {{ flex-direction: column; align-items: flex-start; gap: 16px; }} }}
""".strip()


def aviso(data=None) -> str:
    quando = f" em {data_br(data)}" if data else ""
    return (f"Números gerenciais, calculados por consultas somente leitura ao banco conectado{quando}. "
            "Não substituem livros, obrigações acessórias nem apurações oficiais. "
            "A CD2 Tech não tem nenhuma responsabilidade sobre decisões tomadas com base neles. "
            "Confira com seu contador antes de agir.")


def footer_html(data=None) -> str:
    return (f'<footer class="cd2-assinatura"><div class="cd2-assinatura-logo">{logo_html()}</div>'
            f'<p class="cd2-assinatura-aviso">{esc(aviso(data))}</p></footer>')


def footer_text(data=None) -> str:
    return "CD2 Tech\n" + aviso(data)
