---
name: analyze-mcp-fiscal
description: Gera relatórios de conferência fiscal de um ERP de varejo a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre documentos fiscais em resumo sintético (por CFOP, CST, alíquota, modelo ou dia) e analítico por produto ou por nota, conferência de cabeçalho contra itens, entradas e saídas por CFOP, resumo de tributos por período (ICMS, ICMS-ST, PIS, COFINS, IPI e os campos de IBS, CBS e IS da reforma tributária), sequência de numeração com notas canceladas, inutilizadas e saltos, e inconsistências de cadastro tributário (NCM, CST, CEST, alíquota). Use quando o usuário pedir relatório de documentos fiscais, notas fiscais por CFOP ou por produto, conferência de notas, resumo de impostos, numeração faltando, notas canceladas ou cadastro fiscal inconsistente de um banco conectado ao Archeo. Não gera obrigações acessórias nem apuração oficial.
---

# analyze-mcp-fiscal: relatórios de conferência fiscal a partir do banco conectado ao Archeo

Responde às perguntas de quem confere o fiscal antes do fechamento: o que foi emitido e recebido, com qual operação e tributação, se as notas fecham e o que está fora do padrão.

Siga o método comum em `references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`.

## Limite desta skill (diga na entrega)

**Relatório de conferência, não documento fiscal.** A skill lê o que o ERP gravou e aponta totais e inconsistências. Ela não apura imposto a recolher, não gera SPED (Sistema Público de Escrituração Digital), EFD (Escrituração Fiscal Digital), livros de entrada, saída ou apuração, e não interpreta legislação: se uma tributação está "certa" depende de UF, regime, produto e data, e essa resposta é do contador ou do fiscal da empresa. A skill mostra **onde olhar**: o que diverge do padrão do próprio banco.

Toda entrega desta skill leva no cabeçalho: `Conferência gerencial. Não substitui a escrituração fiscal oficial.`

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "documentos fiscais sintético", "notas por CFOP", "resumo por alíquota" | Documentos fiscais: sintético | 3.1 |
| "documentos fiscais por produto", "notas de conferência" | Documentos fiscais: analítico | 3.2 |
| "as notas fecham?", "total diferente dos itens" | Cabeçalho x itens | 3.3 |
| "entradas e saídas do mês", "resumo por operação" | Entradas x saídas por CFOP | 3.4 |
| "quanto de imposto", "resumo de ICMS, PIS e COFINS" | Resumo de tributos | 3.5 |
| "numeração faltando", "canceladas", "inutilizadas" | Sequência e situação | 3.6 |
| "cadastro fiscal errado", "NCM", "CST inconsistente" | Cadastro tributário | 3.7 |
| "estamos preenchendo IBS e CBS?" | Campos da reforma tributária | 3.8 |

Pedido genérico ("relatório fiscal do mês") recebe o **sintético por CFOP** de entradas e de saídas, com a conferência cabeçalho x itens.

## Defaults de escopo

- **Período:** o último mês fechado com movimento (fiscal trabalha por competência mensal), por data de emissão nas saídas e data de entrada nas entradas. Declare qual data foi usada.
- **Unidade:** por estabelecimento (CNPJ), nunca a rede somada sem quebra: cada estabelecimento apura o seu.
- **Situação:** só documentos autorizados; canceladas, denegadas e inutilizadas contadas à parte.

## O que fiscal tem de particular

1. **Entrada e saída na mesma tabela ou em tabelas diferentes.** Descubra o indicador (tipo de nota, primeiro dígito do CFOP: 1, 2, 3 entradas; 5, 6, 7 saídas) antes de somar.
2. **Vários modelos de documento.** NF-e (modelo 55), NFC-e (modelo 65), CT-e (57), cupom de ECF ou SAT em base antiga, NFS-e de serviço. A venda de caixa pode estar em outra tabela e só o resumo ir para a tabela de notas: confira se o sintético cobre tudo ou só as notas avulsas.
3. **Situação do documento.** Autorizada, cancelada, denegada, inutilizada, em contingência, rejeitada, pendente de envio. Liste as situações distintas com contagem e valor; só as autorizadas entram nos totais. Uma coluna de data de cancelamento preenchida vale como cancelada mesmo sem flag.
4. **Código de Situação Tributária.** CST (Código de Situação Tributária) para o regime normal, CSOSN (Código de Situação da Operação no Simples Nacional) para o Simples. Para ICMS, o CST tem origem (1 dígito) + tributação (2 dígitos); alguns bancos guardam separado.
5. **Base, alíquota e valor.** Confira `valor = base x alíquota` dentro de tolerância de centavos por item; redução de base e diferimento explicam a maior parte das diferenças legítimas.
6. **Total da nota tem composição.** Total = produtos - desconto + frete + seguro + outras despesas + IPI + ICMS-ST (+ FCP-ST, Fundo de Combate à Pobreza), conforme o caso. Comparar total do cabeçalho com soma simples dos itens gera falsa divergência: compare valor de produtos com valor de produtos, e o total com a composição.
7. **Chave de junção.** Itens ligam ao cabeçalho por loja + número + série + modelo + tipo (e às vezes fornecedor, na entrada). Join só por número mistura notas de séries e emitentes diferentes.
8. **Reforma tributária.** Bancos atualizados já têm colunas de IBS (Imposto sobre Bens e Serviços), CBS (Contribuição sobre Bens e Serviços) e IS (Imposto Seletivo). O relatório 3.8 mede se estão sendo preenchidas; alíquotas e regras de transição mudam por ano, então a conferência do valor fica com o fiscal.

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| Sintético | Soma por CFOP = soma dos documentos autorizados do período |
| Analítico | Soma dos itens por nota = valor de produtos do cabeçalho |
| Cabeçalho x itens | Total de notas = fecham + divergentes + sem item |
| Resumo de tributos | Imposto por CFOP = imposto por alíquota = total |
| Sequência | Último - primeiro + 1 = emitidas + canceladas + inutilizadas + faltantes |

## Entrega

Formato do método comum, com o aviso de conferência no cabeçalho. Divergência é apresentada como "a conferir", com a nota e o valor, nunca como "erro fiscal" ou "imposto a pagar".

Relatórios que valem virar ferramenta (`spec-mcp-tool`): sintético por CFOP (`$1`, `$2` período, `$3` loja, `$4` entrada ou saída) e notas com divergência (`$1`, `$2` período, `$3` loja).
