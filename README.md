<div align="center">

# Archeo para agentes de IA

**Do banco legado ao agente de IA, sem número inventado.**

[![Licença Apache 2.0](https://img.shields.io/badge/licen%C3%A7a-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757.svg)](#claude-code)
[![Codex plugin](https://img.shields.io/badge/Codex-plugin-10a37f.svg)](#codex)
[![Release](https://img.shields.io/github/v/release/cd2tec/archeo-harness-plugins?label=release)](https://github.com/cd2tec/archeo-harness-plugins/releases/latest)
[![Archeo](https://img.shields.io/badge/archeo-archeo.cd2.com.br-0000ff.svg)](https://archeo.cd2.com.br)
[![Site](https://img.shields.io/badge/site-cd2tec.github.io-0000ff.svg)](https://cd2tec.github.io/archeo-harness-plugins/)
[![Bancos](https://img.shields.io/badge/bancos-SQL%20Server%20%7C%20PostgreSQL%20%7C%20Oracle%20%7C%20MySQL-555.svg)](#bancos-suportados)

**[Conheça o site do plugin →](https://cd2tec.github.io/archeo-harness-plugins/)**

</div>

---

O [Archeo](https://archeo.cd2.com.br) conecta bancos de dados legados a assistentes de IA. Com o **Archeo MCP Creator**, cada consulta vira uma ferramenta que o modelo pode chamar: um SELECT fixo, com parâmetros, que o servidor valida antes de aceitar.

Este repositório reúne plugins que tiram o trabalho braçal desse processo, com **as mesmas skills empacotadas para mais de um harness de agente**: hoje [Claude Code](#claude-code), [Claude Cowork](#claude-cowork), [Codex](#codex) e [ChatGPT Work](#chatgpt-work).

- **`spec-mcp-tool`** transforma uma pergunta de negócio em ferramenta pronta para cadastrar no MCP Creator.
- **`build-mcp-dashboard`** monta um painel executivo de varejo direto do ERP conectado, em snapshot, ao vivo ou com atualização agendada.
- **`analyze-mcp-*`** gera os relatórios de um ERP de varejo (estoque, vendas, compras, preços, perdas, fiscal, contábil e financeiro), cada um com sua prova de reconciliação.

## O problema

Cadastrar uma boa ferramenta não é só escrever um SELECT. Você precisa:

- achar a tabela ou view certa num schema que ninguém documentou;
- descobrir quais registros excluir (cancelados, estornados, marcados para expurgo);
- transformar filtros em parâmetros `$1`, `$2`, ... com o tipo certo;
- escrever uma descrição que outro modelo de IA entenda sem ambiguidade;
- testar tudo antes de publicar.

Um detalhe errado não dá erro. A ferramenta simplesmente **devolve zero linhas, ou um número inflado, e ninguém percebe**.

## A solução: `spec-mcp-tool`

Você descreve o que quer em português. O agente explora o banco conectado ao Archeo, escreve o SQL, roda no banco real e devolve a ficha pronta para copiar e colar na tela **Nova ferramenta**.

```
Você: crie uma ferramenta no Archeo para vendas por loja e mês, com filtro de período e loja

Agente: [identifica o banco conectado, procura colunas de venda, data e loja,
         confere cancelamentos e nulos, escreve o SQL, roda com valores de teste]

        Banco: loja_demo (SQL Server 16.0)

        | Nome técnico  | pdv_venda_resumo_loja_mes |
        | Schema        | dbo                       |
        | Descrição     | Venda bruta, descontos, venda líquida e ticket médio por
                          loja e mês, sem cupons cancelados. $1 = data inicial ... |

        SQL, parâmetros com tipos, limites e resultado esperado do teste ...
```

Veja uma ficha completa em [`exemplo-ficha.md`](core/archeo/skills/spec-mcp-tool/references/exemplo-ficha.md).

## Como funciona

```mermaid
flowchart LR
    A[Pedido em português] --> B[Identifica o banco<br/>conectado ao Archeo]
    B --> C[Explora o schema<br/>tabelas, colunas, amostras]
    C --> D[Mede os dados<br/>volume, período, nulos, flags]
    D --> E[Escreve o SQL<br/>com $1..$n]
    E --> F{Roda no banco<br/>com valores de teste}
    F -- falhou --> G[Diagnostica e ajusta]
    G --> F
    F -- ok --> H[Ficha pronta<br/>para copiar e colar]
```

## O que vem na ficha

| Campo | O que a skill entrega |
|---|---|
| **Nome técnico** | `snake_case` com prefixo do sistema, sem colisão entre bancos |
| **Nome de exibição** | Rótulo curto em português |
| **Descrição** | Escrita para o modelo que vai chamar a ferramenta: o que retorna, cada parâmetro, convenções |
| **Schema** | O schema certo para o dropdown |
| **SQL** | Um único SELECT no dialeto do seu banco, com parâmetros posicionais |
| **Parâmetros** | Nome, tipo (`date`, `integer`, `string`...) e obrigatoriedade de cada `$n` |
| **Limites** | Linhas, bytes e timeout dimensionados para a consulta |
| **Teste** | Valores de entrada e o resultado esperado, para conferir depois de salvar |
| **Premissas** | Regras de negócio assumidas e qualquer ajuste aplicado |

## Boas práticas embutidas

A skill aplica, por padrão, regras que evitam os erros silenciosos mais comuns:

- **Datas com fim exclusivo** (`>= início AND < fim`), sem perder o último dia nem matar o índice.
- **"Todos" sem armadilha**: o filtro opcional usa um valor sentinela (`0 = todas as lojas`) e não devolve zero linhas quando o parâmetro chega vazio.
- **Somas à prova de nulo**: `COALESCE` dentro de expressões compostas, para um campo vazio não zerar o total.
- **Tipos como contrato**: o tipo do parâmetro na tela valida a entrada antes de chegar no banco.
- **Validação obrigatória**: nenhuma ficha sai sem ter rodado no banco conectado, em pelo menos dois cenários. Quando não dá para validar, a ficha avisa com destaque.

## Painel de varejo: `build-mcp-dashboard`

Peça um painel e receba um artefato pronto para abrir, com os números do ERP ou PDV conectado ao Archeo:

| Bloco | O que mostra |
|---|---|
| **Totalizadores** | Venda líquida, cupons, ticket médio, itens por cupom, desconto, cancelamentos, margem e clientes identificados, com variação contra o período anterior |
| **Índice de saúde (0 a 100)** | Um número com a decomposição por componente: crescimento, ticket, desconto, cancelamento, margem e identificação de clientes |
| **Linha do tempo** | Venda por dia, período atual contra o anterior alinhado |
| **Mapa de calor** | Venda por dia da semana e hora, para escala de equipe e abastecimento |
| **Rankings** | Departamentos, produtos, meios de pagamento, lojas e operadores (descontos e cancelamentos) |
| **Curva ABC** | Quantos SKUs fazem 80% da venda |
| **Leitura** | De 3 a 6 alertas em linguagem de negócio, do mais urgente ao menos |

O painel não esconde dado ruim: seção sem dado confiável sai do painel e aparece no rodapé com o motivo. A skill reconcilia cada ranking com a venda total, detecta custo estimado (margem idêntica em todos os departamentos), campo nunca preenchido e período anterior sem base de comparação.

```
Você: monta um dashboard da operação dos últimos 30 dias

Agente: [mapeia venda, itens, cadastros, pagamento, custo e estoque no banco conectado,
         calcula e reconcilia cada seção, escreve a leitura, publica o painel]
```

Três modos de atualização:

| Modo | Para quem | Como atualiza |
|---|---|---|
| **Snapshot** | Relatório de período fechado, qualquer pessoa com o link | Republicando |
| **Ao vivo** | Quem usa o Claude com o conector Archeo | A página consulta o banco ao abrir e a cada 5 minutos |
| **Agendado** | Diretoria sem conector | Uma tarefa agendada roda a skill e republica, por exemplo todo dia às 6h |

## Relatórios de ERP: `analyze-mcp-*`

Peça o relatório pelo nome que você já usa no ERP. A skill do módulo localiza os dados no banco conectado, mede a qualidade, calcula e **prova** o resultado antes de entregar.

| Skill | Você pede | Ela entrega |
|---|---|---|
| `analyze-mcp-estoque` | "Kardex do produto 1234 em julho" | Movimentação com saldo acumulado, conferida contra o saldo atual |
| `analyze-mcp-vendas` | "curva ABC de venda do trimestre" | Classes A, B e C com participação e acumulado, somando a venda total |
| `analyze-mcp-compras` | "sugestão de compra do fornecedor X" | Demanda, saldo, pendente e sugestão por embalagem, em planilha editável |
| `analyze-mcp-precos` | "o que estou vendendo abaixo do custo?" | Itens com margem negativa, depois do teste de confiabilidade do custo |
| `analyze-mcp-perdas` | "quebras por motivo e setor" | Perda identificada e não identificada, a custo e sobre a venda |
| `analyze-mcp-fiscal` | "documentos fiscais por CFOP do mês" | Sintético por operação, com conferência de cabeçalho contra itens |
| `analyze-mcp-contabil` | "balancete de julho" | Saldo anterior, débitos, créditos e saldo atual, com débito = crédito |
| `analyze-mcp-financeiro` | "títulos vencidos e fluxo dos próximos 30 dias" | Aging e projeção, separando realizado, previsto e não incluído |

Três regras valem para todas:

- **Relatório sem prova não sai.** Kardex fecha com o saldo, balancete fecha débito com crédito, ABC soma a venda total. O que não fecha vira o primeiro item da entrega.
- **Dado ruim aparece.** Custo estimado, campo nunca preenchido, módulo sem uso e posição desatualizada são achados, não rodapé.
- **Fiscal e contábil são conferência gerencial.** Não substituem escrituração, livros oficiais nem apuração.

O relatório que você vai pedir de novo vira ferramenta: cada skill indica os parâmetros e passa para `spec-mcp-tool` o SQL já validado.

## Bancos suportados

| Engine | Status |
|---|---|
| SQL Server | Validado contra banco real |
| PostgreSQL | Validado contra banco real |
| Oracle | Suportado, ainda não validado: sintaxe padrão a confirmar no primeiro uso |
| MySQL / MariaDB | Validado contra banco real |

Em qualquer engine, a palavra final é do teste no banco conectado: se algo não roda, a skill diagnostica e ajusta antes de entregar.

## Instalação

O plugin `archeo` é o mesmo em todos os ambientes. Muda só a forma de instalar:

| Ambiente | Como instala | Atualiza sozinho? |
|---|---|---|
| [Claude Code](#claude-code) | Marketplace direto do GitHub | Opcional (ative o auto-update) |
| [Claude Cowork](#claude-cowork) | Upload do ZIP da release | Não, suba o ZIP novo |
| [Codex](#codex) | Marketplace direto do GitHub | Não, rode o upgrade |
| [ChatGPT Work](#chatgpt-work) | Admin importa o repositório | Sim, sincroniza todo dia |

**Requisito, em qualquer ambiente:** um conector do Archeo ativo na sessão, com as ferramentas de consulta somente leitura (`db_*`). Sem ele, a skill avisa e só monta a ficha se você fornecer a estrutura das tabelas, marcada como não validada.

### Downloads

Cada versão gera uma [release](https://github.com/cd2tec/archeo-harness-plugins/releases/latest) com um ZIP por ambiente. Os links abaixo sempre apontam para a versão mais recente:

- **[`archeo-claude.zip`](https://github.com/cd2tec/archeo-harness-plugins/releases/latest/download/archeo-claude.zip)**, para o Claude Cowork
- **[`archeo-codex.zip`](https://github.com/cd2tec/archeo-harness-plugins/releases/latest/download/archeo-codex.zip)**, para o Codex e o ChatGPT Work, quando não der para instalar direto do GitHub

Na página de cada release também ficam os mesmos arquivos com a versão no nome (por exemplo, `archeo-claude-0.3.0.zip`), para quem precisa guardar uma versão específica.

### Claude Code

Dentro de uma sessão:

```
/plugin marketplace add cd2tec/archeo-harness-plugins
/plugin install archeo@archeo-harness
```

**Atualizar:** rode `/plugin marketplace update archeo-harness` na sessão, ou `claude plugin update archeo@archeo-harness` no terminal. Para receber as versões novas sem pedir, abra `/plugin`, vá em **Marketplaces**, escolha `archeo-harness` e selecione **Enable auto-update**.

### Claude Cowork

No app do Claude, a instalação é pelo ZIP. A sincronização de marketplace pelo GitHub existe, mas só aceita repositório privado, e este é público.

1. Baixe o [`archeo-claude.zip`](https://github.com/cd2tec/archeo-harness-plugins/releases/latest/download/archeo-claude.zip).
2. Escolha onde instalar:
   - **Só para você:** em **Customize > Plugins**, faça o upload do ZIP. Dali você também pode compartilhar o plugin com colegas ou grupos.
   - **Para a organização** (Owner ou Primary Owner, planos Team e Enterprise, com Cowork e Skills habilitados): em **Organization settings > Plugins & skills**, clique em **Add > Upload a plugin**. Na primeira vez, dê um nome ao marketplace (sugestão: `archeo-harness`) e suba o ZIP.
3. Na organização, defina quem recebe o plugin: aba **Inventory**, menu da linha do `archeo`, **Default access**. As opções são **Available to install**, **Installed by default**, **Required** ou **Not available**.
4. Os membros encontram o plugin em **Customize > Plugins**, na aba **Discover**. Plugins **Installed by default** e **Required** já aparecem instalados.

**Atualizar:** baixe o ZIP novo e repita o upload no mesmo lugar. Na organização, um plugin com o mesmo nome substitui a versão anterior, e os membros recebem a atualização na próxima sessão.

### Codex

```
codex plugin marketplace add cd2tec/archeo-harness-plugins
codex plugin add archeo@archeo-harness
```

No app do Codex, depois de adicionar o marketplace, você também pode instalar pelo diretório de plugins: reinicie o app, escolha o marketplace **Archeo (CD2 Retail Tech)** e instale o `archeo`. Para conferir, use `codex plugin list`, que mostra `archeo@archeo-harness` com a versão instalada.

**Atualizar:** `codex plugin marketplace upgrade archeo-harness`. Se o `codex plugin list` continuar mostrando a versão antiga, rode `codex plugin add archeo@archeo-harness` de novo.

### ChatGPT Work

No workspace do ChatGPT, quem instala é o admin, que importa o marketplace direto do GitHub:

1. Em **Workspace settings > Plugins**, clique em **Add** e depois em **Import marketplace**.
2. Preencha:
   - **Source:** `https://github.com/cd2tec/archeo-harness-plugins`
   - **Path:** deixe vazio
   - **Branch, tag, or commit:** deixe vazio para acompanhar as atualizações
3. Clique em **Import marketplace** e autorize o acesso ao GitHub.
4. Em **Import results**, confira se o `archeo` veio de `plugins/codex/archeo`. Abra o plugin e defina a **Installation policy** (**Available** ou **Installed**) para cada papel.
5. Os membros instalam em **Plugins**, na barra lateral, com **Install plugin**.

**O conector é obrigatório:** as skills só encontram o banco se o conector do Archeo estiver disponível no workspace como app MCP (Model Context Protocol, protocolo de contexto de modelo). No Enterprise, a permissão **Create plugins with MCPs** vem desligada por padrão.

**Atualizar:** é automático, o ChatGPT sincroniza o marketplace uma vez por dia. Para trazer uma versão nova na hora, vá em **Workspace settings > Plugins > Marketplaces**, escolha `archeo-harness` e clique em **Sync now**. Se você fixou uma tag no import, as versões novas só chegam quando você trocar a tag.

> **Diferença entre ambientes:** no Claude (Code e Cowork), a `build-mcp-dashboard` publica o painel como artefato, nos modos snapshot, ao vivo e agendado. No Codex e no ChatGPT Work, ela entrega o mesmo painel como arquivo HTML, só no modo snapshot, porque os modos ao vivo e agendado dependem de recursos do Claude. As demais skills funcionam igual em todos.

Depois de instalar, é só pedir:

- *"crie uma ferramenta no Archeo para títulos vencidos por cliente"*
- *"transforma essa query em ferramenta do MCP Creator"*
- *"quais tipos uso nos parâmetros dessa ferramenta?"*
- *"monta um dashboard da rede dos últimos 30 dias"*
- *"quero um painel ao vivo da loja 3 para acompanhar a semana"*
- *"me dá o Kardex do produto 1234 no último mês"*
- *"balancete de julho no nível 3"*
- *"o que comprar do fornecedor X para a loja 2?"*

## Segurança

- A skill **só lê**. Toda exploração e validação usa as ferramentas somente leitura do conector.
- O SQL gerado é sempre **um único SELECT**, sem escrita e sem identificador vindo de parâmetro, o mesmo que o validador do Archeo exige.
- Nada é cadastrado automaticamente: você revisa a ficha e decide o que publicar.

## Plugins

| Plugin | Skills | Harnesses | Para quê |
|---|---|---|---|
| `archeo` | `spec-mcp-tool`, `build-mcp-dashboard`, `analyze-mcp-estoque`, `-vendas`, `-compras`, `-precos`, `-perdas`, `-fiscal`, `-contabil`, `-financeiro` | [Claude Code](plugins/claude/archeo), [Codex](plugins/codex/archeo) | Criar ferramentas no Archeo MCP Creator, painéis de varejo e relatórios de ERP a partir do banco conectado |

## Estrutura do repositório

As skills são escritas **uma vez**, em `core/`, e copiadas para o pacote de cada harness por um script. Assim o conteúdo não diverge entre Claude e Codex, e cada harness mantém só o que é dele: manifesto, marketplace e README.

```
core/archeo/                    fonte única: skills/, references/, plugin.core.json
plugins/claude/archeo/          pacote do Claude Code (.claude-plugin/plugin.json + cópias geradas)
plugins/codex/archeo/           pacote do Codex (plugin.json + cópias geradas)
.claude-plugin/marketplace.json marketplace do Claude Code
.agents/plugins/marketplace.json marketplace do Codex
harnesses.json                  quais harnesses recebem cada plugin
scripts/sync_plugins.py         copia core/ para os harnesses e confere a sincronia
docs/                           site (GitHub Pages, publicado por .github/workflows/pages.yml)
index.html                      redireciona para docs/ se o Pages publicar a partir da raiz do branch
```

```mermaid
flowchart LR
    C[core/archeo<br/>skills e references] -->|sync_plugins.py| CL[plugins/claude/archeo]
    C -->|sync_plugins.py| CX[plugins/codex/archeo]
    CL --> MC[.claude-plugin/marketplace.json]
    CX --> MX[.agents/plugins/marketplace.json]
```

## Contribuindo

1. Edite as skills em `core/`, nunca nas cópias dentro de `plugins/<harness>/`.
2. Rode `python3 scripts/sync_plugins.py` e depois `python3 scripts/sync_plugins.py --check`.
3. Para lançar versão, suba a versão em `core/archeo/plugin.core.json` e nos manifestos de cada harness. Ao chegar na `main`, o workflow de release cria a tag `archeo-v<versão>` com um ZIP por harness, e os links de download passam a entregar a versão nova.
4. Abra o pull request. O CI repete o `--check` e falha se `core/` e as cópias divergirem, se algum manifesto tiver nome ou versão diferente do core ou se uma referência entre arquivos estiver quebrada.

Para adicionar um harness, crie `plugins/<harness>/<plugin>/` com o manifesto, registre-o em `harnesses.json`, crie o marketplace correspondente e rode o sync. Os detalhes estão em [`AGENTS.md`](AGENTS.md).

Encontrou uma engine com comportamento diferente, ou um caso que a skill não cobre? Abra uma issue com a engine, a versão e a consulta.

## Licença

[Apache License 2.0](LICENSE), por [CD2 Retail Tech](https://github.com/cd2tec). Uso, modificação e redistribuição livres, inclusive comercial. Veja o [NOTICE](NOTICE) sobre nomes e marcas.

As versões publicadas até a 0.4.0 estavam sob a licença MIT; quem já baixou essas versões mantém os direitos que a MIT concede.
