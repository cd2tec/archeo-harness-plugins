# archeo para DeepSeek Harness (DSH)

Skills do [Archeo](https://archeo.cd2.com.br) no [DeepSeek Harness](https://www.deepseek.com/en/harness/): `spec-mcp-tool` (ficha de ferramenta para o MCP Creator), `build-mcp-dashboard` (painel executivo de varejo) e `analyze-mcp-*` (relatórios de estoque, vendas, compras, preços, perdas, fiscal, contábil e financeiro), sempre validadas no banco conectado.

O conteúdo das skills é o mesmo dos pacotes para Claude e Codex. Muda só o empacotamento: o DSH lê skills de diretórios planos, uma pasta por skill, então este pacote não tem a pasta `references/` compartilhada do plugin. O que cada skill cita foi copiado para dentro dela pelo `scripts/sync_plugins.py` (layout `flat-skills` em `harnesses.json`).

> **O DSH está em developer preview** e a própria DeepSeek avisa que haverá mudanças incompatíveis. O que está aqui foi escrito a partir da documentação do repositório `deepseek-ai/deepseek-harness`. Se um caminho ou comando mudar, abra uma issue com a versão do DSH (`dsh --version`).

## Requisitos

- DeepSeek Harness instalado: app desktop (macOS ou Windows) ou Web UI (`npx @deepseek-ai/dsh web`), com uma chave de API da DeepSeek configurada em **Settings > Models**.
- Python 3 no PATH, para o `install.py` e para os scripts da `build-mcp-dashboard`.
- **O conector do Archeo configurado no DSH como servidor MCP** (Model Context Protocol, protocolo de contexto de modelo). As skills só funcionam com as ferramentas somente leitura `db_*` do Archeo na sessão. Veja [Conectar o Archeo](#conectar-o-archeo-mcp).

## Instalar

### Pelo ZIP da release

1. Baixe o [`archeo-dsh.zip`](https://github.com/cd2tec/archeo-harness-plugins/releases/latest/download/archeo-dsh.zip) e descompacte.
2. Na pasta descompactada, rode:

```
python3 install.py
```

Isso copia as dez skills para `~/.agents/skills/`, que o DSH lê para qualquer projeto. Outras opções:

| Comando | Destino | Quando usar |
|---|---|---|
| `python3 install.py` | `~/.agents/skills` | Padrão. Vale para todos os projetos e também é lido por outros agentes que seguem o padrão Agent Skills |
| `python3 install.py --project` | `./.agents/skills` | Só para o projeto atual, versionado junto com ele |
| `python3 install.py --dsh-home` | `$DSH_HOME/skills` (padrão `~/.dsh/skills`) | Quando quiser que só o DSH veja as skills |
| `python3 install.py --dest CAMINHO` | o caminho informado | Qualquer outro diretório de skills |
| `python3 install.py --dry-run` | nenhum | Mostra o que faria |

O script só toca nas pastas com os nomes das skills do Archeo. Outras skills no mesmo diretório ficam como estão.

### Pelo clone do repositório

```
git clone https://github.com/cd2tec/archeo-harness-plugins.git
python3 archeo-harness-plugins/plugins/dsh/archeo/install.py
```

### À mão

Copie cada pasta de `skills/` para um dos diretórios que o DSH lê. Em caso de nome repetido, o diretório de menor número vence:

| Ordem | Diretório |
|---|---|
| 1 | `<projeto>/.dsh/skills` |
| 2 | `<projeto>/.agents/skills` |
| 3 | diretórios extras em `customSkillDirs` da configuração do DSH |
| 4 | `$DSH_HOME/skills` (padrão `~/.dsh/skills`) |
| 5 | `~/.agents/skills` |

O "projeto" é a pasta mais próxima com `.git`, ou a pasta onde o `dsh` foi iniciado. Cada skill precisa ficar como `<diretório>/<nome-da-skill>/SKILL.md`; o DSH não procura em subpastas mais fundas.

## Conectar o Archeo (MCP)

O DSH liga servidores MCP pelo plugin `@deepseek-ai/dsh-mcp-client`, um por servidor, declarado num arquivo de patch:

- `$DSH_HOME/cordis.patch.yml` para todos os perfis, ou
- `$DSH_HOME/profiles/<perfil>/cordis.patch.yml` para um perfil só (`web`, por exemplo).

Se o arquivo já existir, acrescente a entrada em vez de substituir o conteúdo. Exemplo para o conector do Archeo por HTTP, com o token lido de uma variável de ambiente:

```yaml
- insert:
    - id: mcp-archeo
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: archeo
        transport: streamable-http
        url: <URL do servidor MCP do seu Archeo>
        headers:
          Authorization: !!js '`Bearer ${process.env.ARCHEO_MCP_TOKEN}`'
```

- A URL e a forma de autenticação são as do seu servidor Archeo; pegue-as na tela do MCP Creator. Não grave o token no YAML.
- Para um servidor local via processo, use `transport: stdio` com `command`, `args` e `env`.
- As ferramentas aparecem para o modelo como `mcp__archeo__db_<banco>_<engine>_<id>__<ação>`, o mesmo padrão `mcp__<conector>__db_...` que as skills esperam. A descoberta é assíncrona: espere as ferramentas aparecerem antes de testar.
- A documentação do DSH mostra o patch sendo aplicado também na linha de comando, com `dsh web --patch <arquivo>`.

## Verificar

Abra uma sessão nova no DSH, com o workspace escolhido, e peça algo que uma skill cubra:

- *"crie uma ferramenta no Archeo para títulos vencidos por cliente"* (carrega `spec-mcp-tool`)
- *"me dá o Kardex do produto 1234 no último mês"* (carrega `analyze-mcp-estoque`)
- *"monta um dashboard da rede dos últimos 30 dias"* (carrega `build-mcp-dashboard`)

O DSH lista as skills disponíveis para o modelo e as carrega pela ferramenta `skill` quando o pedido combina com a descrição. Se o modelo disser que não há banco do Archeo conectado, o problema é o conector MCP, não a skill.

## Atualizar e remover

- **Atualizar:** baixe o ZIP novo e rode `python3 install.py` de novo, no mesmo destino. As pastas das skills do Archeo são substituídas; as demais, não.
- **Remover:** `python3 install.py --remove` (com a mesma opção de destino usada na instalação).

## Diferenças em relação ao Claude

| O que muda | Claude (Code e Cowork) | DeepSeek Harness |
|---|---|---|
| Painel `build-mcp-dashboard` | Publicado como artefato, nos modos snapshot, ao vivo e agendado | Entregue como arquivo HTML, só no modo snapshot. Os modos ao vivo e agendado dependem de recursos do Claude |
| Pré-visualização do painel | Chromium disponível no ambiente | O script `preview_dashboard.py` precisa de Playwright e Chromium; sem eles, a skill avisa que a renderização não foi conferida |
| Demais skills | Iguais | Iguais |

## O que há neste pacote

| Arquivo | O que é |
|---|---|
| `skills/<nome>/` | As dez skills, geradas a partir de `core/archeo/` do repositório. Não edite aqui |
| `install.py` | Copia as skills para um diretório lido pelo DSH |
| `plugin.json` | Nome e versão do pacote, conferidos pelo CI. O DSH não lê este arquivo |
| `LICENSE` e `NOTICE` | Apache 2.0 e aviso sobre nomes e marcas |

## Outros agentes que leem `~/.agents/skills`

A pasta `skills/` deste pacote segue o padrão aberto [Agent Skills](https://agentskills.io) (`SKILL.md` com `name` e `description`). Outros agentes que leem `~/.agents/skills`, como o Codex e o Deep Code CLI, enxergam as mesmas skills. Para o Codex, porém, o caminho suportado continua sendo o marketplace descrito no [README principal](../../../README.md#codex), que cuida das atualizações.

## Próximo passo previsto

Quando o DSH sair de preview, este pacote deve virar um *bundle* npm instalável com `dsh plugin --profile <perfil> add`, declarando as skills e a conexão MCP do Archeo numa única instalação. A instalação por cópia descrita acima continuará funcionando.
