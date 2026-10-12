---
name: add-mcp-dashboard
description: Monta automaticamente um dashboard executivo de varejo (totalizadores, índice de saúde de 0 a 100, linha do tempo, mapa de calor por dia e hora, rankings de departamentos, produtos, meios de pagamento e operadores, curva ABC e leitura com alertas) a partir do ERP ou PDV conectado ao Archeo, e publica como artefato em modo snapshot, ao vivo (consulta o banco ao abrir) ou com atualização agendada. Use quando o usuário pedir dashboard, painel, visão geral, indicadores, KPIs, score ou "como está a operação" de um varejo, supermercado, loja ou rede cujo banco esteja conectado ao Archeo, mesmo sem dizer "dashboard".
---

# add-mcp-dashboard: dashboard de varejo a partir do banco conectado ao Archeo

Entrega um painel que um diretor de varejo abre e entende em 30 segundos: quanto vendeu, se está melhor ou pior que antes, onde está o problema e o que olhar primeiro. Os números saem do banco conectado ao Archeo, por consultas somente leitura, e o painel é publicado como artefato.

O painel não inventa nada. Toda seção vem de uma consulta que rodou no banco; seção sem dado confiável sai do painel e aparece no rodapé com o motivo. Um painel bonito com número errado é pior que nenhum painel.

## Fluxo

### 1. Identifique o banco conectado

As ferramentas de um conector Archeo seguem o padrão `mcp__<conector>__db_<banco>_<engine>_<id>__<ação>` (`db_connection_status`, `db_list_tables`, `db_search_columns`, `db_describe_table`, `db_sample_table`, `db_read_only_query`). Podem estar deferidas: procure com ToolSearch e carregue as do conector numa chamada só. Com vários conectores, pergunte qual banco; sem nenhum, diga que o painel precisa de um banco do Archeo conectado e pare.

Rode `db_connection_status` e anote engine e versão. Para sintaxe por engine e ajustes do conector, leia `../add-mcp-tool/references/regras-sql.md` (seções 1, 3 e 4) antes da primeira consulta.

### 2. Combine o escopo em uma pergunta, se precisar

Defaults, quando o usuário não disser: **todas as lojas**, **últimos 30 dias até a última data com venda** (não até hoje: bases de laboratório e réplicas param de receber movimento), comparado com os **30 dias imediatamente anteriores**, modo **snapshot**. Pergunte só o que mudaria o painel (por exemplo, "ao vivo ou snapshot?" quando o usuário falou em atualização sem dizer como). Declare no painel e na resposta o recorte usado.

Se o período padrão tiver pouco movimento (menos de ~100 cupons, ou menos de 10% do volume médio da base), diga isso e proponha o recorte com mais movimento antes de seguir.

### 3. Mapeie o ERP

Siga `references/indicadores-varejo.md`, seção "Mapeamento": localize venda por cupom, itens vendidos, cadastros de produto, departamento, loja e meio de pagamento, custo, estoque e identificação de cliente. Prefira views de resumo do próprio sistema. Para cada domínio, meça antes de usar (`COUNT`, `MIN`/`MAX` de data, nulos, valores distintos de flags), porque é aqui que se descobre cancelamento, registro indevido, custo estimado e campo nunca preenchido.

Evite despejar o catálogo inteiro: consulte `INFORMATION_SCHEMA.COLUMNS` filtrando tabelas ou padrões de nome, nunca sem `WHERE`.

### 4. Calcule cada seção

Use o catálogo de `references/indicadores-varejo.md`: para cada seção há o dado necessário, a consulta-modelo, o gráfico e a regra de quando omitir. Antes de aceitar um número:

- **Reconcilie.** Seções que repartem a venda (departamentos, meios de pagamento, lojas) precisam somar perto da venda total. Diferença acima de 2% indica join que multiplica linhas (cadastro com uma linha por loja é o caso clássico) ou filtro faltando. Corrija antes de publicar.
- **Desconfie de uniformidade.** Margem idêntica em todos os departamentos é custo estimado, não custo real. Campo 0% ou vazio em todo o histórico é campo não capturado, não desempenho ruim.
- **Compare com base.** Se algum dos dois períodos tiver menos de 30 cupons, ou um tiver menos de 10% dos cupons do outro, a variação é ruído: marque como "sem base comparável".

Calcule o índice de saúde com `references/score.md`.

### 5. Escreva a leitura

De 3 a 6 itens curtos, do mais urgente ao menos, com nível `critico`, `atencao`, `bom` ou `info`. Cada item cita o número que o sustenta e diz o que olhar. Inclua sempre um item sobre a qualidade do dado quando algo da etapa 4 apareceu (custo estimado, base sem comparação, concentração anormal). Leitura de negócio, não descrição do gráfico.

### 6. Monte e publique o artefato

1. Escreva o config JSON no formato de `references/config.md`.
2. Gere a página: `python3 scripts/build_dashboard.py config.json painel.html` (caminho relativo a esta skill). O script valida o config e recusa formato errado.
3. Confira a renderização uma vez: `python3 scripts/preview_dashboard.py painel.html` gera screenshots claro, escuro e celular e lista erros de JavaScript e rolagem lateral. Olhe a captura principal antes de publicar (rótulos sobrepostos, seção vazia, número estranho). No modo ao vivo, passe também a página ao vivo e um JSON com respostas reais das consultas para testar a capability simulada.
4. Carregue as skills `artifact-design` e, no modo ao vivo, `artifact-capabilities` antes de publicar, como o Artifact tool exige. O template já segue o contrato de página (tokens claro e escuro, largura de celular, sem dependências externas).
5. Publique com o Artifact tool, ícone `chart`, título com o nome da rede ou da operação (ex.: "Painel Rede Exemplo"), descrição de uma frase com período e fonte.
6. Modo ao vivo: siga `references/modos-atualizacao.md` para declarar a capability `mcp` e testar. Modo agendado: crie a tarefa agendada descrita no mesmo arquivo depois do primeiro publish.

Para republicar com dados novos, gere a página de novo e publique no mesmo caminho de arquivo, ou passe a `url` do artefato existente.

### 7. Responda

Uma ou duas frases com o achado principal, o recorte usado, o modo de atualização e as seções que ficaram de fora e por quê. O card do artefato já leva o link.

## Escolha do modo de atualização

| Modo | Quando usar | Custo |
|---|---|---|
| **snapshot** (padrão) | Relatório de um período fechado, compartilhamento amplo, quem vê não tem o conector | Fica parado até republicar |
| **ao vivo** | Acompanhamento diário por quem tem o conector Archeo no Claude | Cada visualização consulta o banco; quem vê precisa do conector e autoriza o acesso; o artefato não pode ser compartilhado publicamente |
| **agendado** | Diretoria quer o painel atualizado todo dia sem ter o conector | Uma sessão agendada roda a skill e republica; precisa do conector disponível no horário |

Detalhes, manifesto e cuidados em `references/modos-atualizacao.md`.
