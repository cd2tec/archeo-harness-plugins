# Formato do JSON do relatório

Entrada de `scripts/render_relatorio.py`. O script valida, avalia a prova e gera a entrega. Em caso de erro, sai com código 2 e `{"errors": [...]}` em português: corrija o JSON e rode de novo.

Valores numéricos vão como número (`4812640.0`), nunca já formatados. A formatação brasileira é do script.

## Campos

```json
{
  "area": "Análise de vendas",
  "titulo": "ABC de venda",
  "cliente": "Rede Exemplo, 3 lojas",
  "gerado_em": "2026-11-08",
  "fonte": { "banco": "erp_varejo", "engine": "SQL Server 16", "conector": "Archeo Manager" },
  "recorte": { "unidade": "Todas as 3 lojas", "periodo": "08/08/2026 a 05/11/2026", "filtros": "Sem filtro", "nivel": "Sintético e os 20 maiores" },
  "conferencia": false,
  "avisos": [],
  "veredito": {
    "titulo": "386 produtos fazem 80% da sua venda",
    "texto": "E 41 deles vendem com margem abaixo de 3%.",
    "numeros": [ { "valor": 4812640.0, "formato": "moeda", "legenda": "venda líquida em 90 dias" } ]
  },
  "resumo": [ { "rotulo": "Classe A", "valor": 79.8, "formato": "pct", "legenda": "da venda vem de 7,5% dos itens" } ],
  "leitura": [ { "nivel": "critico", "texto": "41 itens da classe A têm margem abaixo de 3%. Revise preço e custo deles primeiro." } ],
  "blocos": [],
  "prova": {
    "tolerancia_pct": 2,
    "conferencias": [
      { "nome": "Soma das classes = venda total", "esperado": 4812640.0, "obtido": 4812640.0, "formato": "moeda" },
      { "nome": "Amostra de 5 itens conferida na origem", "fechou": true, "detalhe": "5 de 5 itens iguais" }
    ]
  },
  "premissas": {
    "filtros": [ "Fora da conta: 1.204 cupons cancelados." ],
    "qualidade": [ "312 produtos com custo zerado, 4,3% da venda." ],
    "indisponiveis": [ { "item": "Margem por loja", "motivo": "o custo tem uma linha por produto" } ],
    "consulta": "SELECT ..."
  },
  "proximos": [ { "tag": "Virar ferramenta", "titulo": "ABC sob demanda", "texto": "Parâmetros: data inicial, data final, loja e departamento." } ]
}
```

| Campo | Regra |
|---|---|
| `veredito.titulo` | O achado principal, em uma frase, com o número. Abre a página. Não descreva o relatório ("Curva ABC do período" não serve) |
| `veredito.numeros` | Até 3 |
| `conferencia` | `true` em relatório fiscal e contábil: põe o aviso de conferência no topo |
| `avisos` | Avisos que precisam vir antes de tudo, por exemplo cobertura de custo abaixo de 90% |
| `resumo` | De 1 a 6 totais. `legenda` diz o que o número mede |
| `leitura` | De 3 a 5 itens, do mais urgente ao menos, com número e o que fazer. `nivel`: `critico`, `atencao`, `bom`, `info` ou `dado` (qualidade do dado) |
| `formato` | `moeda`, `inteiro`, `decimal`, `pct`, `pp`, `dias`, `data`, `texto` |
| `proximos` | Até 2: ferramenta (`spec-mcp-tool`) e painel (`build-mcp-dashboard`) |

## Prova

É o script que decide se fechou. Duas formas de conferência:

- **Numérica:** `esperado`, `obtido` e `formato`. Fecha se a diferença couber na tolerância. Use `"tolerancia_pct": 0` onde não pode haver diferença (débito = crédito, Kardex, soma de títulos). Sem resultado, passe `"obtido": null` e `"motivo"`.
- **Por amostra ou verificação:** `fechou` (booleano) e `detalhe`, para provas que não são soma ("5 de 5 itens conferidos").

Se uma conferência não fechar, a página abre em vermelho com a diferença, antes de qualquer outro conteúdo. Não ajuste os números para fechar.

## Blocos

Aparecem na ordem da lista. Todos têm `tipo`, `titulo` e `nota` opcional.

### `tabela`

```json
{ "tipo": "tabela", "titulo": "Maiores produtos", "nota": "Os 20 maiores por valor.",
  "colunas": [
    { "campo": "descricao", "rotulo": "Produto" },
    { "campo": "valor", "rotulo": "Venda líquida", "formato": "moeda" },
    { "campo": "margem", "rotulo": "Margem", "formato": "pct", "alerta_abaixo": 3 },
    { "campo": "classe", "rotulo": "Classe", "formato": "classe" }
  ],
  "linhas": [ { "descricao": "7891 Arroz tipo 1 5 kg", "valor": 184734.0, "margem": 6.2, "classe": "A" } ],
  "total": { "descricao": "Total", "valor": 184734.0 } }
```

A primeira coluna é o rótulo da linha: junte código e descrição nela. A página mostra até 30 linhas; o CSV leva todas. `alerta_abaixo` e `alerta_acima` destacam o valor em vermelho.

### `pareto`

```json
{ "tipo": "pareto", "titulo": "Curva ABC", "rotulo_itens": "itens", "formato": "moeda",
  "classes": [ { "classe": "A", "itens": 386, "valor": 3838214.4 }, { "classe": "B", "itens": 742, "valor": 723118.9 }, { "classe": "C", "itens": 4002, "valor": 251306.7 } ],
  "pontos": [ [1.0, 22.0], [5.0, 66.0], [15.0, 90.4] ] }
```

`rotulo_itens` é o que está sendo classificado, no plural masculino (`itens`, `produtos`, `clientes`, `fornecedores`). Desenha a curva e o quadro de classes (itens, % dos itens, valor, % do valor). `pontos` é opcional: pares `[% acumulado dos itens, % acumulado do valor]`, até uns 20, para a curva sair suave.

### `barras`

```json
{ "tipo": "barras", "titulo": "Por departamento", "formato": "moeda", "melhor": "alta",
  "linhas": [ { "rotulo": "Mercearia", "valor": 1684424.0, "var_pct": 6.1 } ] }
```

Calcula a participação de cada linha. `var_pct` é opcional. `melhor: "baixa"` inverte a cor da variação.

### `linha`

```json
{ "tipo": "linha", "titulo": "Venda por dia", "formato": "moeda", "series": { "atual": "Outubro", "anterior": "Setembro" },
  "pontos": [ { "x": "2026-10-01", "atual": 52000.0, "anterior": 49800.0 } ] }
```

### `cascata`

```json
{ "tipo": "cascata", "titulo": "Do saldo inicial ao final", "formato": "moeda",
  "etapas": [ { "rotulo": "Saldo inicial", "valor": 100000.0, "tipo": "inicial" }, { "rotulo": "Entradas", "valor": 40000.0, "tipo": "delta" }, { "rotulo": "Saídas", "valor": -55000.0, "tipo": "delta" }, { "rotulo": "Saldo final", "valor": 85000.0, "tipo": "final" } ] }
```

Serve para Kardex, fluxo de caixa e resultado. Valor de saída vai negativo.

## Saídas

```bash
python3 <pasta da skill>/scripts/render_relatorio.py --input relatorio.json --format html --output relatorio.html
python3 <pasta da skill>/scripts/render_relatorio.py --input relatorio.json --format markdown
python3 <pasta da skill>/scripts/render_relatorio.py --input relatorio.json --format whatsapp
python3 <pasta da skill>/scripts/render_relatorio.py --input relatorio.json --format csv --output relatorio.csv
```

`--theme` aceita `auto` (padrão, acompanha quem abre), `light` e `dark`. Toda saída já traz o rodapé da CD2 Tech. Não edite o resultado à mão. Veja também `references/marca.md`.
