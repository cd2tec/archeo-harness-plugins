"""Testes do kit compartilhado no sync e do painel com a marca."""
import filecmp
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "core/archeo/shared"
HARNESSES = ("claude", "codex", "dsh")
SKILLS_COM_KIT = sorted(p.name for p in (ROOT / "core/archeo/skills").iterdir() if p.name != "spec-mcp-tool" and p.is_dir())


def carrega_sync():
    spec = importlib.util.spec_from_file_location("sync_plugins", ROOT / "scripts/sync_plugins.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["sync_plugins"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


class Kit(unittest.TestCase):
    def test_kit_em_cada_skill_e_harness(self):
        arquivos = [p.relative_to(SHARED) for p in SHARED.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"]
        self.assertTrue(arquivos)
        for harness in HARNESSES:
            for skill in SKILLS_COM_KIT:
                base = ROOT / f"plugins/{harness}/archeo/skills/{skill}"
                for rel in arquivos:
                    self.assertTrue(filecmp.cmp(SHARED / rel, base / rel, shallow=False), f"{base / rel}")

    def test_spec_mcp_tool_fica_sem_kit(self):
        for harness in HARNESSES:
            self.assertFalse((ROOT / f"plugins/{harness}/archeo/skills/spec-mcp-tool/scripts/brand.py").exists())

    def test_licenca_da_fonte_acompanha(self):
        self.assertTrue((SHARED / "assets/fonts/OFL.txt").is_file())

    def test_colisao_com_arquivo_da_skill_e_erro(self):
        sync = carrega_sync()
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "core"
            (core / "shared/scripts").mkdir(parents=True)
            (core / "shared/scripts/brand.py").write_text("kit", encoding="utf-8")
            (core / "skills/a/scripts").mkdir(parents=True)
            (core / "skills/a/SKILL.md").write_text("x", encoding="utf-8")
            (core / "skills/a/scripts/brand.py").write_text("da skill", encoding="utf-8")
            with tempfile.TemporaryDirectory() as work:
                _, problemas = sync.effective_core(core, {"shared": {"dir": "shared", "skip": []}}, Path(work))
        self.assertEqual(len(problemas), 1)
        self.assertIn("colide", problemas[0])

    def test_skip_nao_recebe_kit(self):
        sync = carrega_sync()
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "core"
            (core / "shared/references").mkdir(parents=True)
            (core / "shared/references/m.md").write_text("kit", encoding="utf-8")
            for nome in ("a", "b"):
                (core / f"skills/{nome}").mkdir(parents=True)
                (core / f"skills/{nome}/SKILL.md").write_text("x", encoding="utf-8")
            with tempfile.TemporaryDirectory() as work:
                efetivo, problemas = sync.effective_core(core, {"shared": {"dir": "shared", "skip": ["b"]}}, Path(work))
                self.assertEqual(problemas, [])
                self.assertTrue((efetivo / "skills/a/references/m.md").exists())
                self.assertFalse((efetivo / "skills/b/references/m.md").exists())
                self.assertFalse((efetivo / "shared").exists())


class Painel(unittest.TestCase):
    SCRIPT = ROOT / "plugins/claude/archeo/skills/build-mcp-dashboard/scripts/build_dashboard.py"

    def cfg(self, **extra):
        base = {
            "titulo": "Painel Rede Exemplo", "rede": "Rede Exemplo", "fonte": {"banco": "b", "engine": "e", "conector": "c"},
            "geradoEm": "2026-11-08T09:30:00-03:00", "modo": "snapshot", "metaSecao": "kpis",
            "secoes": [{"id": "kpis", "tipo": "kpis", "titulo": "T", "cards": [{"campo": "v", "rotulo": "Venda", "formato": "moeda"}], "dados": [{"v": 10}]}],
        }
        base.update(extra)
        return base

    def construir(self, cfg):
        with tempfile.TemporaryDirectory() as tmp:
            entrada, saida = Path(tmp) / "c.json", Path(tmp) / "p.html"
            entrada.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
            res = subprocess.run([sys.executable, str(self.SCRIPT), str(entrada), str(saida)], capture_output=True, text=True)
            return res, saida.read_text(encoding="utf-8") if saida.exists() else ""

    def test_gera_com_a_marca(self):
        res, html = self.construir(self.cfg(veredito={"titulo": "Vendeu mais", "texto": "Subiu 4,8%."}))
        self.assertEqual(res.returncode, 0, res.stdout)
        for marca in ("__FONT_FACE__", "__TOKENS_CSS__", "__LOGO__", "__FOOTER__", "__DASH_CONFIG__", "__DASH_TITLE__"):
            self.assertNotIn(marca, html)
        self.assertIn("--brand: #0000ff", html)
        self.assertIn("font/woff2;base64", html)
        self.assertIn("cd2-assinatura", html)
        self.assertIn("08/11/2026", html)
        self.assertNotIn("#2a78d6", html)

    def test_snapshot_remove_codigo_ao_vivo(self):
        _, html = self.construir(self.cfg())
        self.assertNotIn("LIVE-START", html)

    def test_ao_vivo_recusa_veredito(self):
        cfg = self.cfg(modo="live", live={"server": "s", "tool": "t"}, veredito={"titulo": "x"})
        for sec in cfg["secoes"]:
            del sec["dados"]
            sec["sql"] = "SELECT 1"
        res, _ = self.construir(cfg)
        self.assertEqual(res.returncode, 1)
        self.assertIn("veredito", res.stdout)

    def test_dado_nao_expande_marca(self):
        res, html = self.construir(self.cfg(rede="__LOGO__"))
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertIn('"rede": "__LOGO__"', html)


class Versao(unittest.TestCase):
    def test_changelog_tem_a_versao_do_core(self):
        versao = json.loads((ROOT / "core/archeo/plugin.core.json").read_text(encoding="utf-8"))["version"]
        self.assertIn(f"## {versao}", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
