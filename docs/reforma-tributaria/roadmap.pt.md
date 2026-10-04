# Roadmap

Tarefas por documento, com o **limite legal** (quando a norma define) e uma **proposta de datas**
que volta a partir dele. As datas propostas dependem do alinhamento com os mantenedores.

![Cronograma proposto](../assets/reforma-gantt-pt-light.png#only-light)
![Cronograma proposto](../assets/reforma-gantt-pt-dark.png#only-dark)

## Limites legais

| Data | O que | Fonte |
|---|---|---|
| 16/11/2026 | NT 2026.004 em produção (CT-e e outros) | NT 2026.004 |
| 01/12/2026 | NT 2026.010 em produção (DANFE da NF-e) | NT 2026.010 |

## Tarefas

| ID | Tarefa | Início | Fim | Situação |
|---|---|---|---|---|
| A1 | Pesquisa da NT 2026.010 | 03/10 | 04/10 | concluída |
| A2 | Alinhamento com os mantenedores (este PR) | 05/10 | 16/10 | proposta |
| A3 | Implementação do DANFE em retrato: bloco de totais, CRT, campos por item, regra de alíquota efetiva | 19/10 | 06/11 | proposta |
| A4 | Testes e PDFs de referência | 09/11 | 13/11 | proposta |
| A5 | Revisão e merge | 16/11 | 19/11 | proposta |
| A6 | Release da biblioteca | 20/11 | 20/11 | proposta |
| A7 | Integração nos consumidores | 23/11 | 30/11 | proposta |
| A8 | Layout em paisagem | 07/12 | 18/12 | opcional |
| B1 | Pesquisa: a NT 2026.004 altera o DACTE? | 05/10 | 16/10 | proposta |
| B2 | Implementação no DACTE, se houver mudança | 19/10 | 06/11 | condicional a B1 |
| B3 | Testes e revisão do DACTE | 09/11 | 13/11 | condicional a B1 |
| C1 | Pesquisa: NT 008 e NT 009 (DANFSe) | 19/10 | 30/10 | proposta |
| C2 | Implementação no DANFSe | sem data | sem data | depende da data da NT 009 |
| D1 | Pesquisa: DANFCe e DANFE simplificado | 19/10 | 30/10 | proposta |
| D2 | Acompanhar o PR #202 (DANFCe) | 02/11 | contínuo | sem data |
| E1 | Pesquisa de NT de impressão: NFCom, BP-e, NF3e... | 02/11 | 13/11 | opcional |

A margem entre a release (A6, 20/11) e o limite de 01/12 existe para os consumidores integrarem e
testarem (A7). Se o alinhamento (A2) atrasar, o primeiro item a deslizar é A8.

## Premissas

1. Um módulo por PR, para a revisão em partes.
2. Os PDFs de referência em `tests/fixtures` e `tests/generated` seguem o procedimento já documentado
   (mesma versão do `fpdf2` do CI).
3. A integração em outros projetos (A7) é responsabilidade de cada consumidor e não faz parte deste
   repositório.
4. Documentos novos (NFCom, BP-e, NF3e...) só entram com NT de impressão confirmada e demanda.

## Atualizar o cronograma

As datas ficam em `scripts/generate_reforma_gantt.py` (listas `TASKS` e `DEADLINES`). Depois de
editar, rode `pip install matplotlib` e `python scripts/generate_reforma_gantt.py` para regenerar as
imagens em `docs/assets/`. O matplotlib é usado só para a documentação e não é dependência da
biblioteca.
