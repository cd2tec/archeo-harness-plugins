# Changelog

As notas de cada versão entram automaticamente na release do GitHub. Use um título `## <versão>` por versão, da mais recente para a mais antiga.

## 0.6.0

**Entregas no padrão do Design System CD2 Tech.** As oito skills `analyze-mcp-*` agora entregam uma página, não só texto na conversa, e o painel da `build-mcp-dashboard` veste a marca.

- Novo renderizador comum, `render_relatorio.py`. A skill monta um JSON e o script gera HTML, CSV, resumo para WhatsApp e Markdown. A página abre com o achado principal e traz resumo, leitura, curva ABC, barras, linha, cascata, tabelas, prova e premissas, nos temas claro e escuro e no celular.
- Quem decide se a prova fechou é o script. Relatório sem prova não gera página, e prova que não fecha abre a página em vermelho, com a diferença.
- O painel usa cores, fonte Manrope e logo da CD2, com o bloco de veredito e o índice de saúde no topo. Campo novo e opcional no config: `veredito`. Consultas e modos de atualização não mudam.
- Novo kit em `core/archeo/shared/`, que o `sync_plugins.py` copia para cada skill, menos a `spec-mcp-tool`. Campo novo em `harnesses.json`: `shared`.
- Testes em `tests/`, rodados no CI.

## 0.5.0

**Pacote para o DeepSeek Harness (DSH).** As mesmas dez skills, agora também em `plugins/dsh/archeo` e no `archeo-dsh.zip` da release. O DSH lê skills de diretórios planos (`~/.agents/skills/<skill>/`), então o pacote vem com um `install.py` que copia as skills para lá e traz, dentro de cada skill, as referências compartilhadas que ela cita. O README do pacote explica como ligar o conector do Archeo como servidor MCP no DSH.

- Novo layout `flat-skills` em `harnesses.json` e no `scripts/sync_plugins.py`, que também passa a conferir as referências entre arquivos na árvore gerada de cada harness.
- `build-mcp-dashboard` cita o DeepSeek Harness entre os harnesses sem Artifact tool. O comportamento no Claude e no Codex não muda.
- O DSH está em developer preview; a instalação por cópia continuará funcionando quando o pacote virar um bundle npm.

## 0.4.1

**Licença Apache 2.0.** O repositório passa de MIT para Apache License 2.0. O uso continua livre, inclusive comercial, sem obrigação de abrir código derivado. O que muda para quem usa:

- A Apache 2.0 inclui concessão expressa de patentes por quem contribui.
- Ao redistribuir, mantenha os arquivos `LICENSE` e `NOTICE`. Eles agora também vão dentro dos ZIPs de cada harness.
- A licença não concede direito de uso dos nomes e marcas "Archeo" e "CD2" (seção 6).

As versões até a 0.4.0 continuam disponíveis sob a licença MIT em que foram publicadas. As skills não mudaram.

## 0.4.0

**Mudança de nome em duas skills.** Os nomes agora dizem o que a skill entrega:

| Antes | Agora | Por quê |
|---|---|---|
| `add-mcp-tool` | `spec-mcp-tool` | A skill não cadastra a ferramenta: ela entrega a especificação validada para você colar no Archeo MCP Creator. |
| `add-mcp-dashboard` | `build-mcp-dashboard` | A skill constrói o painel. No Claude ela também publica; no Codex e no ChatGPT Work, entrega o arquivo HTML. |

O comportamento das skills não mudou. Se você chamava pelo nome (por exemplo, `/archeo:add-mcp-tool` no Claude Code), passe a usar o nome novo. Pedidos em linguagem natural ("crie uma ferramenta no Archeo para...", "monta um dashboard da rede") continuam funcionando sem mudança.

As skills de relatório (`analyze-mcp-*`) mantêm os nomes.

## 0.3.0

Primeira versão no repositório `archeo-harness-plugins`, com pacotes para Claude Code, Claude Cowork, Codex e ChatGPT Work.
