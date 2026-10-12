# Modos de atualização do painel

O mesmo template atende os três modos; muda o config e a forma de publicar.

## Snapshot (padrão)

Os dados vão embutidos no config (`"modo": "snapshot"` e `dados` em cada seção). A página abre instantaneamente para qualquer pessoa com o link, não consulta nada e mostra "Snapshot de dd/mm/aaaa hh:mm" no cabeçalho.

Para atualizar: rode a skill de novo e republique no mesmo artefato (mesmo caminho de arquivo nesta sessão, ou `url` do artefato existente).

## Ao vivo (capability `mcp`)

A página consulta o banco pelo conector Archeo **com as credenciais de quem está vendo**, ao abrir e a cada intervalo (`refetchMs`, padrão 5 minutos, mínimo 30 segundos; pausa com a aba escondida).

### Config

- `"modo": "live"`, sem `dados` em nenhuma seção. Não embuta valores observados no banco como amostra; a página mostra estados de carregamento até a primeira resposta.
- Toda seção (e o `meta`, se houver) leva `sql`. Use o período relativo de `indicadores-varejo.md`, 4.1, para o painel andar sozinho.
- `live.server`: nome de exibição do conector no Claude. No nome da ferramenta `mcp__Archeo_Manager__db_..._db_read_only_query`, o conector é `Archeo_Manager`, ou seja, **"Archeo Manager"**.
- `live.tool`: o nome da ferramenta no conector, o trecho depois de `mcp__<conector>__`. Exemplo: `db_erp_varejo_sql_server_1a2b3c__db_read_only_query`. O nome carrega o identificador da conexão: o painel fica preso a esse banco.
- `live.schema`: o schema padrão das consultas (ex.: `dbo`), quando a ferramenta aceitar.
- A leitura escrita (`leitura`) não acompanha os números ao vivo; o painel diz quando foi escrita. Escreva itens estruturais (concentração, qualidade de dado), não frases presas a um valor do dia.

### Publicação

Carregue a skill `artifact-capabilities` antes. Publique com:

```json
"capabilities": { "mcp": { "servers": [ { "server": "Archeo Manager", "tools": ["<live.tool>"] } ] } }
```

Declare só a ferramenta de consulta. Consequências para dizer ao usuário:

- Quem abre precisa ter o conector Archeo no próprio Claude e autorizar o acesso no primeiro uso.
- Um artefato com conector declarado **não pode ser compartilhado publicamente**.
- Cada abertura e cada intervalo executa as consultas no banco. Com muitas pessoas olhando, prefira intervalos longos ou o modo agendado.

### Teste antes de entregar

1. Gere a página e abra localmente num navegador headless (Playwright e Chromium estão no ambiente) com um `window.claude.use("mcp")` falso que responde `watchTool` com as linhas de uma consulta real desta sessão. Confira que as seções preenchem e que um erro `server_not_connected` mostra o aviso de conector.
2. Publique e diga em uma linha o que foi exercitado (renderização com resposta simulada) e o que não pôde ser (a consulta real pela página só roda quando o usuário abre e autoriza).

## Agendado

Snapshot republicado por uma tarefa agendada, para quem vai ver sem ter o conector.

Depois do primeiro publish, crie a tarefa com a ferramenta de agendamento da sessão (procure com ToolSearch; chame de "tarefa agendada" ao falar com o usuário). Prompt da tarefa, autocontido:

```
Rode a skill /archeo:build-mcp-dashboard no modo snapshot, com o mesmo recorte do painel
<url do artefato>: <lojas>, últimos <N> dias até a última data com venda, comparado com o
período anterior equivalente. Use o banco <nome> pelo conector <conector>. Leia o artefato,
gere a página com os dados novos e republique na mesma url. Se o banco não responder,
não republique e registre o motivo.
```

Horário sugerido: logo depois do fechamento do movimento do dia anterior (ex.: 6h). A tarefa precisa do conector Archeo disponível na conta no horário de execução.
