---
name: analyze-mcp-perdas
description: Gera relatórios de perdas e prevenção de perdas de um ERP de varejo a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre quebra por motivo, departamento e produto, percentual de perda sobre a venda, perda identificada (quebras lançadas) e não identificada (ajuste de inventário), vencidos e validade a vencer, ajustes manuais de estoque, e exceções de frente de caixa (cancelamentos, descontos, devoluções e trocas por operador). Use quando o usuário pedir relatório de quebras, perdas, avarias, vencidos, shrink, índice de perda, ajuste de inventário, ou auditoria de cancelamentos e descontos no caixa de um banco conectado ao Archeo.
---

# analyze-mcp-perdas: relatórios de perdas a partir do banco conectado ao Archeo

Responde às perguntas da prevenção de perdas: quanto se perde, em quê, por quê, onde, e o quanto disso é conhecido.

Siga o método comum em `references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`. Movimento e inventário são mapeados como em `../analyze-mcp-estoque/references/relatorios.md`, seção 1.

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "quebras", "perdas por setor", "motivos de perda" | Quebra por motivo e departamento | 3.1 |
| "índice de perda", "perda sobre a venda", "shrink" | Perda total: identificada e não identificada | 3.2 |
| "vencidos", "o que vai vencer" | Validade | 3.3 |
| "ajustes de estoque", "quem ajustou" | Ajustes manuais | 3.4 |
| "cancelamentos no caixa", "descontos por operador" | Exceções de frente de caixa | 3.5 |
| "trocas e devoluções suspeitas" | Trocas e devoluções | 3.6 |

Pedido genérico ("como estão as perdas") recebe a **perda total** (3.2) com a quebra por departamento.

## Defaults de escopo

- **Período:** últimos 30 dias até a última data com movimento; para perda não identificada, o intervalo entre os dois últimos inventários do departamento.
- **Valorização:** a custo. Perda a preço de venda mistura margem que nunca existiu; se o usuário pedir a venda, mostre as duas colunas.
- **Base do percentual:** venda líquida do mesmo período, do mesmo departamento e da mesma loja.

## Definições (declare)

- **Perda identificada (quebra conhecida):** baixa lançada com motivo: vencimento, avaria, furto constatado, degustação, uso interno, quebra operacional de produção.
- **Perda não identificada:** falta apurada no inventário, sem lançamento que a explique. É a divergência **líquida** do balanço (faltas - sobras), a custo.
- **Perda total** = identificada + não identificada.
- **Índice de perda %** = perda a custo / venda líquida. Informe sempre a base: há empresas que usam venda a custo ou venda bruta, e o número muda.

## O que perdas tem de particular

1. **Motivo é texto livre ou código mal usado.** Meça a distribuição dos motivos primeiro. Um motivo genérico ("outros", "ajuste") dominante é o achado principal: a empresa não sabe por que perde.
2. **Quebra pode estar em três lugares:** tipo de movimento de estoque, nota fiscal de baixa (CFOP, Código Fiscal de Operações e Prestações, 5.927) e módulo próprio de perdas. Compare os três antes de escolher; somar dois deles duplica.
3. **Uso e consumo, degustação e transferência para produção** saem do estoque e não são perda no mesmo sentido. Separe na apresentação.
4. **Inventário rotativo x geral.** Perda não identificada só existe onde houve contagem. Departamento sem inventário no período não tem "zero de perda", tem perda desconhecida.
5. **Sobra não é ganho.** Sobra grande ao lado de falta grande aponta erro de processo (troca de código no recebimento ou no caixa).
6. **Operador é pessoa.** Relatórios por operador servem para priorizar auditoria, não para acusar. Mostre taxa com a base (cupons, valor) e o comparativo com a média da loja; nunca apresente como prova de fraude (método comum, seção 6).

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| Quebra por motivo | Soma por motivo = soma por departamento = total de quebras |
| Perda total | Não identificada = divergência líquida dos lotes considerados (lista dos lotes na entrega) |
| Ajustes manuais | Ajustes do relatório = movimentos dos tipos de ajuste no período |
| Exceções de caixa | Cancelado + válido = total registrado |

## Entrega

Formato do método comum. Sempre diga quais departamentos tiveram inventário no período e quais não tiveram.

Relatórios que valem virar ferramenta (`spec-mcp-tool`): quebra por motivo (`$1`, `$2` período, `$3` loja, `$4` departamento) e exceções por operador (`$1`, `$2` período, `$3` loja).
