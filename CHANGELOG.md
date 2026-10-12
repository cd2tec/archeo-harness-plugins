# Changelog

As notas de cada versão entram automaticamente na release do GitHub. Use um título `## <versão>` por versão, da mais recente para a mais antiga.

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
