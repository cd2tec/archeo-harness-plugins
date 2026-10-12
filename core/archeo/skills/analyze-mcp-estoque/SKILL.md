---
name: analyze-mcp-estoque
description: Gera relatórios e análises de estoque de um ERP de varejo a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre estoque geral (posição por produto, loja, departamento ou fornecedor, a custo e a venda), Kardex (movimentação analítica com saldo acumulado), análise de lote de inventário (congelado, contado, divergência e acuracidade), cobertura e ruptura, estoque parado, estoque negativo, giro e posição retroativa. Use quando o usuário pedir relatório de estoque, posição de estoque, Kardex, extrato ou movimentação de produto, balanço, inventário, divergência de contagem, ruptura, cobertura, dias de estoque, excesso, estoque parado ou giro de um banco conectado ao Archeo, mesmo sem dizer "relatório".
---

# analyze-mcp-estoque: relatórios de estoque a partir do banco conectado ao Archeo

Responde às perguntas do módulo de estoque de um ERP de varejo: quanto tenho, onde está, quanto vale, como chegou a esse saldo e o quanto dá para confiar nele. Os números saem do banco conectado ao Archeo por consultas somente leitura.

Siga o método comum em `../../references/metodo-analise.md` (fluxo, regras de consulta, formato da entrega, volume e exportação). Este arquivo diz o que muda para estoque; mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`.

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "posição de estoque", "quanto tenho de X", "estoque por departamento" | Estoque geral | 3.1 |
| "Kardex", "extrato do produto", "o que movimentou esse item" | Kardex | 3.2 |
| "resultado do balanço", "divergência do inventário", "acuracidade" | Análise de lote de inventário | 3.3 |
| "o que está faltando", "ruptura", "dias de estoque", "excesso" | Cobertura e ruptura | 3.4 |
| "estoque parado", "sem giro", "encalhe" | Estoque sem venda | 3.5 |
| "estoque negativo", "saldo errado" | Inconsistências de saldo | 3.6 |
| "giro de estoque" | Giro e estoque médio | 3.7 |
| "quanto eu tinha no dia X" | Posição retroativa | 3.8 |

Pedido genérico ("me mostra o estoque") recebe o **Estoque geral sintético por departamento**, com os 20 maiores itens em valor e a contagem de negativos e zerados.

## Defaults de escopo

- **Posição:** a mais recente do banco. Descubra a data real da posição (coluna de data de atualização ou a maior data de movimento) e mostre no cabeçalho; posição sem data conhecida sai com esse aviso.
- **Movimento (Kardex, giro, cobertura):** últimos 30 dias até a última data com movimento. Kardex é sempre por produto: sem produto informado, peça o código ou mostre os 20 itens com mais movimento para o usuário escolher.
- **Valorização:** custo médio quando existir; senão o custo que o banco tiver, dizendo qual é (médio, última entrada, reposição, líquido de impostos ou não).
- **Unidade:** todas as lojas e depósitos, com quebra quando houver mais de um.

## O que estoque tem de particular

1. **Saldo atual não é saldo histórico.** A tabela de saldo guarda a posição de agora. Posição em data passada vem de fotografia diária, se o ERP guardar, ou de recomposição pelo Kardex (3.8). Nunca apresente o saldo atual como se fosse o de outra data.
2. **Sentido do movimento.** Entrada, saída, transferência, ajuste, quebra, devolução e estorno costumam ter quantidade positiva e o sinal em um tipo de operação. Liste os tipos distintos com a soma de cada um e monte o `CASE` de sinal a partir disso. Transferência entre lojas aparece duas vezes (saída em uma, entrada na outra): some zero na rede.
3. **Unidade e embalagem.** Compra em caixa, venda em unidade, pesável em quilo. Confirme em que unidade o saldo está antes de multiplicar por custo ou comparar com venda.
4. **Produto composto.** Kits, cestas, produção própria (padaria, açougue) e itens com receita movimentam os componentes, não o produto final. Saldo zerado no pai pode ser normal.
5. **Custo zerado ou ausente** distorce o valor de estoque. Meça a cobertura de custo (percentual do saldo com custo maior que zero) e informe.
6. **Inventário tem estados.** Lote aberto, congelado, em contagem, encerrado, cancelado. A análise de divergência só vale para lotes com contagem lançada; lote encerrado já ajustou o saldo.

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| Estoque geral | Soma por departamento = soma total sem join com cadastro |
| Kardex | Saldo inicial + entradas - saídas = saldo final; saldo final = saldo atual quando o período vai até a última data |
| Lote de inventário | Itens do lote = contados + não contados; divergência em valor = soma das divergências por item |
| Cobertura e ruptura | Venda usada no cálculo = venda do período pela fonte de vendas |
| Posição retroativa | Recompor até hoje devolve o saldo atual |

Kardex que não fecha com o saldo atual é um achado importante (movimento fora da tabela, ajuste direto no saldo, tipo de operação com sinal errado). Mostre a diferença e os tipos de movimento envolvidos em vez de forçar o fechamento.

## Entrega

Use o formato do método comum. No resumo de qualquer relatório de posição, inclua: itens com saldo, valor a custo, valor a venda quando houver preço, itens negativos, itens zerados e cobertura de custo.

Relatórios que valem virar ferramenta (`spec-mcp-tool`): Kardex (`$1` produto, `$2` loja, `$3` data inicial, `$4` data final), estoque geral por departamento (`$1` loja, `$2` departamento) e ruptura (`$1` loja, `$2` dias de venda recente).
