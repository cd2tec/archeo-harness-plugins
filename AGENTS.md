# Instruções para agentes neste repositório

Este repositório publica os mesmos plugins para mais de um harness (hoje Claude Code e Codex).

## Regra principal

**Edite só `core/`.** As pastas `plugins/<harness>/<plugin>/skills/` e `plugins/<harness>/<plugin>/references/` são cópias geradas. Depois de qualquer mudança em `core/`, rode:

```
python3 scripts/sync_plugins.py
python3 scripts/sync_plugins.py --check
```

O CI roda o `--check` e falha se as cópias divergirem de `core/`.

## Onde fica cada coisa

| Caminho | O que é | Edita à mão? |
|---|---|---|
| `core/<plugin>/skills/` | Fonte única das skills | Sim |
| `core/<plugin>/references/` | Referências compartilhadas entre skills | Sim |
| `core/<plugin>/plugin.core.json` | Nome e versão de referência do plugin | Sim |
| `harnesses.json` | Quais harnesses recebem cada plugin e onde fica o manifesto | Sim |
| `plugins/<harness>/<plugin>/` (manifesto, README e, no DSH, `install.py`) | Empacotamento específico do harness | Sim |
| `plugins/<harness>/<plugin>/skills/` e `references/` | Cópias geradas | **Não** |
| `.claude-plugin/marketplace.json` | Marketplace do Claude Code | Sim |
| `.agents/plugins/marketplace.json` | Marketplace do Codex | Sim |

## Convenções

- Skills seguem o formato `skills/<nome>/SKILL.md` com frontmatter `name` (igual ao nome da pasta) e `description`. O formato é o mesmo nos dois harnesses.
- Referências entre skills usam caminho relativo (`../outra-skill/references/x.md`); por isso cada harness recebe o conjunto completo.
- Escreva as skills de forma neutra quanto ao harness. Quando um passo depender de um recurso exclusivo (por exemplo, publicar artefato no Claude), diga isso explicitamente na skill e ofereça a alternativa para os demais harnesses.
- Ao mudar a versão, atualize `core/<plugin>/plugin.core.json` e os manifestos de cada harness. Não declare `version` na entrada do marketplace do Claude: o Claude Code usa a do `plugin.json` e a duplicação só abre espaço para divergência. O `--check` confere nome e versão dos manifestos. A mudança em `plugin.core.json` na `main` dispara `.github/workflows/release.yml`, que cria a release `<plugin>-v<versão>` com um ZIP por harness (gerado por `scripts/package_plugins.py`). Release de versão já existente não é recriada: suba a versão.
- Layouts de harness, no campo `layout` de cada entrada em `harnesses.json`:
  - `plugin` (padrão; Claude e Codex): o harness instala o pacote inteiro, então `skills/` e `references/` são copiados como estão.
  - `flat-skills` (DSH): o harness lê cada skill de um diretório plano (`~/.agents/skills/<nome>/`), sem raiz de plugin. O sync copia só `skills/` e, para cada skill que cita um arquivo de `core/<plugin>/references/`, copia esse arquivo para `references/` da skill e reescreve o caminho. Consequência: não crie em `core/<plugin>/references/` um arquivo com o mesmo nome de um `references/` de skill, e não escreva caminhos para `references/` do plugin fora de crases (o sync só reescreve o que está entre crases).
- Para adicionar um harness: crie `plugins/<harness>/<plugin>/` com o manifesto, registre em `harnesses.json` (com `layout`, se não for o padrão), crie o marketplace correspondente quando o harness tiver um e rode o sync.
