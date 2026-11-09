"""Testes do renderizador comum e do kit de marca, na cópia gerada para o Claude."""
import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins/claude/archeo/skills/analyze-mcp-vendas/scripts"
sys.path.insert(0, str(SCRIPTS))

import brand  # noqa: E402
import render_relatorio as rr  # noqa: E402

BASE = json.loads((ROOT / "tests/fixtures/relatorio-abc.json").read_text(encoding="utf-8"))


def novo():
    return copy.deepcopy(BASE)


def rodar(rel, *args):
    with tempfile.TemporaryDirectory() as tmp:
        entrada = Path(tmp) / "r.json"
        entrada.write_text(json.dumps(rel, ensure_ascii=False), encoding="utf-8")
        saida = io.StringIO()
        with redirect_stdout(saida):
            codigo = rr.main(["--input", str(entrada), *args])
    return codigo, saida.getvalue()


class Formatos(unittest.TestCase):
    def test_moeda_e_numero(self):
        self.assertEqual(brand.moeda(4812640), "R$ 4.812.640,00")
        self.assertEqual(brand.moeda(-1234.5), "-R$ 1.234,50")
        self.assertEqual(brand.moeda(-0.001), "R$ 0,00")
        self.assertEqual(brand.numero(5130), "5.130")

    def test_arredondamento_para_cima(self):
        self.assertEqual(brand.moeda(1.005), "R$ 1,01")
        self.assertEqual(brand.pct(79.75), "79,8%")

    def test_compacta_e_data(self):
        self.assertEqual(brand.moeda_compacta(1642310.4), "R$ 1,6 mi")
        self.assertEqual(brand.moeda_compacta(40000), "R$ 40 mil")
        self.assertEqual(brand.data_br("2026-11-08T09:30:00"), "08/11/2026")

    def test_vazio_vira_sem_dado(self):
        self.assertEqual(brand.formatar(None, "moeda"), "s/d")

    def test_tokens_do_design_system(self):
        css = brand.tokens_css()
        self.assertIn("--brand: #0000ff", css)
        self.assertIn("--surface: #f2f2f2", css)
        self.assertIn("Manrope", css)
        self.assertIn('prefers-color-scheme: dark', css)
        self.assertIn(':root[data-theme="dark"]', css)

    def test_rodape_tem_logo_e_aviso(self):
        rodape = brand.footer_html("2026-11-08")
        self.assertIn("cd2-logo-claro", rodape)
        self.assertIn("08/11/2026", rodape)
        self.assertIn("CD2 Tech", brand.footer_text())


class Validacao(unittest.TestCase):
    def test_sem_prova_nao_sai(self):
        rel = novo()
        rel["prova"]["conferencias"] = []
        codigo, saida = rodar(rel, "--format", "html")
        self.assertEqual(codigo, 2)
        self.assertIn("Relatório sem prova não sai", json.loads(saida)["errors"][0])

    def test_recorte_e_obrigatorio(self):
        rel = novo()
        del rel["recorte"]["periodo"]
        self.assertTrue(any("recorte.periodo" in e for e in rr.validar(rel)))

    def test_cpf_sem_mascara_e_recusado(self):
        rel = novo()
        rel["leitura"][0]["texto"] = "Cliente 123.456.789-09 parou de comprar."
        self.assertTrue(any("CPF" in e for e in rr.validar(rel)))

    def test_coluna_cpf_sem_pontuacao_e_recusada(self):
        rel = novo()
        bloco = rel["blocos"][4]
        bloco["colunas"].append({"campo": "cpf", "rotulo": "CPF"})
        bloco["linhas"][0]["cpf"] = "12345678909"
        self.assertTrue(any("CPF" in e for e in rr.validar(rel)))

    def test_cpf_mascarado_passa(self):
        rel = novo()
        rel["leitura"][0]["texto"] = "Cliente ***.456.789-** parou de comprar."
        self.assertEqual(rr.validar(rel), [])

    def test_json_invalido(self):
        with tempfile.TemporaryDirectory() as tmp:
            entrada = Path(tmp) / "r.json"
            entrada.write_text("{", encoding="utf-8")
            saida = io.StringIO()
            with redirect_stdout(saida):
                self.assertEqual(rr.main(["--input", str(entrada), "--format", "html"]), 2)

    def test_tipo_de_bloco_invalido(self):
        rel = novo()
        rel["blocos"].append({"tipo": "pizza", "titulo": "x"})
        self.assertTrue(any("pizza" in e for e in rr.validar(rel)))


class Prova(unittest.TestCase):
    def test_dentro_da_tolerancia_fecha(self):
        res = rr.avaliar_prova({"conferencias": [{"nome": "a", "esperado": 100.0, "obtido": 101.5}]})
        self.assertTrue(res[0]["fechou"])

    def test_acima_da_tolerancia_nao_fecha(self):
        res = rr.avaliar_prova({"conferencias": [{"nome": "a", "esperado": 100.0, "obtido": 103.0}]})
        self.assertFalse(res[0]["fechou"])

    def test_tolerancia_zero(self):
        res = rr.avaliar_prova({"conferencias": [{"nome": "d=c", "esperado": 1000.0, "obtido": 1000.5, "tolerancia_pct": 0}]})
        self.assertFalse(res[0]["fechou"])

    def test_sem_obtido_nao_fecha(self):
        res = rr.avaliar_prova({"conferencias": [{"nome": "a", "esperado": 100.0, "obtido": None, "motivo": "tabela vazia"}]})
        self.assertFalse(res[0]["fechou"])
        self.assertEqual(res[0]["diferenca"], "tabela vazia")

    def test_prova_que_nao_fecha_vem_antes_do_veredito(self):
        rel = novo()
        rel["prova"]["conferencias"][0]["obtido"] = 4000000.0
        pagina = rr.render_html(rel)
        self.assertIn("Este relatório ainda não fechou", pagina)
        self.assertLess(pagina.index("Este relatório ainda não fechou"), pagina.index(rel["veredito"]["titulo"]))
        self.assertIn("A CONFERIR", pagina)

    def test_prova_fechada_mostra_selo(self):
        self.assertIn("Prova fechada, diferença de R$ 0,00", rr.render_html(novo()))


class Html(unittest.TestCase):
    def setUp(self):
        self.pagina = rr.render_html(novo())

    def test_sem_marcador_sobrando(self):
        self.assertNotIn("{{", self.pagina)

    def test_autocontido(self):
        self.assertIn("font/woff2;base64", self.pagina)
        self.assertNotIn('src="http', self.pagina)
        self.assertNotIn("<link", self.pagina)

    def test_titulo_antes_da_fonte(self):
        self.assertLess(self.pagina.index("<title>"), 8000)

    def test_secoes_na_ordem(self):
        marcos = ["386 produtos fazem", 'class="recorte"', 'aria-label="Resumo"', "DO SEU BANCO", "Curva ABC", "Prova</h2>", "Premissas e qualidade", '<p class="cd2-assinatura-aviso"']
        posicoes = [self.pagina.index(m) for m in marcos]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_sem_travessao_gerado(self):
        self.assertNotIn("—", self.pagina)
        self.assertNotIn("–", self.pagina)

    def test_escapa_texto_do_banco(self):
        rel = novo()
        rel["blocos"][4]["linhas"][0]["descricao"] = "<script>alert(1)</script>"
        rel["premissas"]["consulta"] = "SELECT '</pre><img src=x>'"
        pagina = rr.render_html(rel)
        self.assertNotIn("<script>alert", pagina)
        self.assertNotIn("<img src=x>", pagina)

    def test_marcador_vindo_do_banco_nao_expande(self):
        rel = novo()
        rel["cliente"] = "{{FONT_FACE}}"
        self.assertIn("{{FONT_FACE}}", rr.render_html(rel))

    def test_alerta_na_coluna(self):
        self.assertEqual(self.pagina.count('class="n alerta"'), 1)

    def test_tabela_corta_em_30_linhas(self):
        rel = novo()
        rel["blocos"][4]["linhas"] = [{"descricao": f"Item {i}", "valor": 1.0, "margem": 5.0, "classe": "C"} for i in range(45)]
        pagina = rr.render_html(rel)
        self.assertIn("Item 29", pagina)
        self.assertNotIn("Item 30<", pagina)
        self.assertIn("Mostrando 30 de 45", pagina)

    def test_aviso_de_conferencia(self):
        rel = novo()
        rel["conferencia"] = True
        self.assertIn("Não é documento oficial", rr.render_html(rel))

    def test_tema_forcado(self):
        self.assertIn('data-theme="dark"', rr.render_html(novo(), "dark"))
        self.assertNotIn('<html lang="pt-BR" data-theme', self.pagina)

    def test_linha_com_valores_negativos(self):
        rel = novo()
        rel["blocos"][2]["pontos"] = [{"x": "2026-10-01", "atual": -5000.0}, {"x": "2026-10-02", "atual": 8000.0}]
        self.assertIn("polyline", rr.render_html(rel))


class Texto(unittest.TestCase):
    def test_markdown_segue_o_metodo(self):
        texto = rr.render_markdown(novo())
        marcos = ["**ABC de venda**", "Banco: erp_varejo (SQL Server 16), via Archeo Manager", "Recorte:", "**Resumo**", "**Relatório**", "**Leitura**", "**Prova**", "**Premissas e qualidade do dado**", "CD2 Tech"]
        posicoes = [texto.index(m) for m in marcos]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_markdown_escapa_barra(self):
        rel = novo()
        rel["blocos"][4]["linhas"][0]["descricao"] = "A|B"
        self.assertIn("A\\|B", rr.render_markdown(rel))

    def test_whatsapp_curto(self):
        texto = rr.render_whatsapp(novo())
        self.assertIn("*386 produtos fazem 80% da sua venda*", texto)
        self.assertIn("Prova: fechou, diferença de R$ 0,00.", texto)
        self.assertTrue(texto.rstrip().endswith("agir."))

    def test_whatsapp_avisa_prova_aberta(self):
        rel = novo()
        rel["prova"]["conferencias"][0]["obtido"] = 1.0
        self.assertIn("NÃO FECHOU", rr.render_whatsapp(rel))

    def test_csv_para_excel_brasileiro(self):
        texto = rr.render_csv(novo())
        self.assertTrue(texto.startswith("﻿"))
        self.assertIn("184734,00", texto)
        self.assertIn(";", texto)

    def test_csv_neutraliza_formula(self):
        rel = novo()
        rel["blocos"][4]["linhas"][0]["descricao"] = '=HYPERLINK("http://x")'
        texto = rr.render_csv(rel)
        self.assertNotIn(";=HYPERLINK", texto)
        self.assertNotIn("\r\n=HYPERLINK", texto)
        self.assertIn("'=HYPERLINK", texto)

    def test_csv_leva_todas_as_linhas(self):
        rel = novo()
        rel["blocos"][4]["linhas"] = [{"descricao": f"Item {i}", "valor": 1.0, "margem": 5.0, "classe": "C"} for i in range(45)]
        self.assertIn("Item 44", rr.render_csv(rel))


class Cli(unittest.TestCase):
    def test_grava_arquivo_e_informa_a_prova(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "saida.html"
            codigo, saida = rodar(novo(), "--format", "html", "--output", str(destino))
            self.assertEqual(codigo, 0)
            self.assertIn("Prova: fechou", saida)
            self.assertTrue(destino.read_text(encoding="utf-8").startswith("<!doctype html>"))


if __name__ == "__main__":
    unittest.main()
