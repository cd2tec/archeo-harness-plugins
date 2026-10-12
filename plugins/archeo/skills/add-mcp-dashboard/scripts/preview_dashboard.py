"""Renderiza o painel gerado em Chromium headless e tira screenshots.

Uso:
  python3 preview_dashboard.py painel.html
      -> desk-light.png, desk-dark.png, phone.png; imprime largura de rolagem e erros de JS
  python3 preview_dashboard.py painel.html painel-live.html respostas.json
      -> tambem testa o modo ao vivo com um window.claude.use("mcp") simulado:
         live-ok.png (watchTool responde com linhas) e live-error.png (server_not_connected)

respostas.json mapeia um trecho do SQL de cada secao para as linhas que a consulta
devolveu de verdade nesta sessao: {"trecho do sql": [ {...}, ... ]}.
Use so para conferir a renderizacao; nao embuta essas linhas na pagina publicada.
"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

SKEL = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>{}</body></html>'

MOCK = """
window.__rows = %s;
window.__mode = %s;
window.claude = { use: function(name){ return new Promise(function(res){ setTimeout(function(){
  if (name !== 'mcp') return res(null);
  res(Object.freeze({ watchTool: function(server, tool, input, handler, opts){
    window.__calls = (window.__calls||[]).concat([{server:server, tool:tool, q: input.query.slice(0,60), opts: opts}]);
    setTimeout(function(){
      if (window.__mode === 'error') handler({type:'error', error:{code:'server_not_connected', message:'x'}});
      else { var key = Object.keys(window.__rows).filter(function(k){ return input.query.indexOf(k) >= 0; })[0];
             handler({type:'data', result:{ content:[], payload: window.__rows[key] || [] }}); }
    }, 50);
    return function(){};
  }}));
}, 30); }); } };
"""

async def shot(page, html, path, width, dark=False, init=None):
    await page.set_viewport_size({"width": width, "height": 900})
    await page.emulate_media(color_scheme="dark" if dark else "light")
    if init: await page.add_init_script(init)
    import tempfile, os
    f = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, dir=os.getcwd()); f.write(SKEL.replace("{}", html)); f.close()
    await page.goto("file://" + f.name)
    await page.wait_for_timeout(600)
    errs = await page.evaluate("window.__errs || []")
    sw = await page.evaluate("document.documentElement.scrollWidth")
    await page.screenshot(path=path, full_page=True)
    return sw, errs

async def main():
    html = Path(sys.argv[1]).read_text()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        out = {}
        for name, w, dark in [("desk-light", 1280, False), ("desk-dark", 1280, True), ("phone", 400, False)]:
            pg = await b.new_page(); errs = []
            pg.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
            pg.on("console", lambda m, errs=errs: errs.append(m.text) if m.type == "error" else None)
            sw, _ = await shot(pg, html, f"{name}.png", w, dark)
            out[name] = {"scrollWidth": sw, "errors": errs}
        if len(sys.argv) > 2:
            live = Path(sys.argv[2]).read_text(); rows = Path(sys.argv[3]).read_text()
            for mode in ["ok", "error"]:
                pg = await b.new_page(); errs = []
                pg.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                sw, _ = await shot(pg, live, f"live-{mode}.png", 1280, False, MOCK % (rows, json.dumps(mode)))
                st = await pg.inner_text("#status"); calls = await pg.evaluate("(window.__calls||[]).length")
                out["live-"+mode] = {"status": st, "calls": calls, "errors": errs, "banner": await pg.inner_text("#banner") if await pg.is_visible("#banner") else ""}
        print(json.dumps(out, indent=1, ensure_ascii=False))
        for f in Path.cwd().glob("tmp*.html"):
            f.unlink()
        await b.close()
asyncio.run(main())
