# Reforma Tributária

Pesquisa e roadmap para os documentos auxiliares (DANFE, DACTE, DANFSe e demais) diante da Reforma
Tributária do Consumo (IBS, CBS e Imposto Seletivo; EC 132/2023 e LC 214/2025).

!!! info "Status"
    Proposta para alinhamento com os mantenedores, em 04/10/2026. Nada aqui foi implementado ainda.
    O que está confirmado em norma fica separado do que ainda é pesquisa.

## Por que isto existe

A NT 2026.010 (DANFE Reforma Tributária) entra em produção em **01/12/2026** e altera o leiaute de
impressão do DANFE modelo 55. Hoje a biblioteca não imprime nenhum dos novos tributos no DANFE e no
DANFSe, e só o DACTE tem uma opção de exibição de IBS e CBS. Os consumidores da biblioteca precisam
de uma versão publicada antes do prazo, com margem para integrar e testar.

## Estado em 04/10/2026

| Documento | Na biblioteca hoje | Norma | Situação |
|---|---|---|---|
| DANFE (NF-e 55) | sem IBS/CBS/IS | NT 2026.010 v1.00, produção 01/12/2026 | norma lida, ver [pesquisa](research.pt.md) |
| DACTE (CT-e) | opção `display_ibs_cbs` | NT 2026.004, produção 16/11/2026 | falta confirmar se a NT altera a impressão |
| DAMDFE (MDF-e) | n/a | o leiaute do MDF-e não tem IBS/CBS | sem mudança prevista |
| DANFSe (NFS-e) | sem IBS/CBS | NT 008 v1.02 e NT 009 v1.01 | falta confirmar; a NT 009 não tem data de produção |
| DANFCe (NFC-e) | não existe | PR #202 em aberto | sem NT de impressão encontrada |
| DANFE simplificado | não existe | NT 2026.003 | falta confirmar relação com a reforma |
| NFCom, BP-e, NF3e, NFAg, NFGas, NF-e ABI | não existem | Ato Conjunto RFB/CGIBS 4/2026 | sem NT de impressão confirmada |

## Onde ler mais

- [Pesquisa](research.pt.md): o que cada norma exige, com fontes e o que ainda falta confirmar.
- [Roadmap](roadmap.pt.md): tarefas, limites de data e o cronograma em Gantt.

## Como contribuir

Correções de fato, fontes melhores e discordâncias de cronograma são bem-vindas em issue ou PR. A
tabela de datas e o gerador do Gantt (`scripts/generate_reforma_gantt.py`) ficam no repositório para
qualquer pessoa ajustar.
