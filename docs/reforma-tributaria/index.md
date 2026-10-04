# Tax Reform

Research and roadmap for the auxiliary documents (DANFE, DACTE, DANFSe and others) under the Brazilian
Consumption Tax Reform (IBS, CBS and the Selective Tax; EC 132/2023 and LC 214/2025).

!!! info "Status"
    Proposal for alignment with the maintainers, as of 2026-10-04. Nothing here has been implemented yet.
    What is confirmed in the regulations is kept apart from what is still research.

## Why this exists

NT 2026.010 (DANFE Tax Reform) goes into production on **2026-12-01** and changes the print layout of
the model 55 DANFE. Today the library prints none of the new taxes in the DANFE or DANFSe, and only
the DACTE has an option to show IBS and CBS. Consumers of the library need a published release before
the deadline, with room to integrate and test.

## Status on 2026-10-04

| Document | In the library today | Regulation | Situation |
|---|---|---|---|
| DANFE (NF-e 55) | no IBS/CBS/IS | NT 2026.010 v1.00, production 2026-12-01 | regulation read, see [research](research.md) |
| DACTE (CT-e) | `display_ibs_cbs` option | NT 2026.004, production 2026-11-16 | to confirm whether the NT changes the print |
| DAMDFE (MDF-e) | n/a | the MDF-e layout has no IBS/CBS | no change expected |
| DANFSe (NFS-e) | no IBS/CBS | NT 008 v1.02 and NT 009 v1.01 | to confirm; NT 009 has no production date |
| DANFCe (NFC-e) | does not exist | PR #202 open | no print NT found |
| Simplified DANFE | does not exist | NT 2026.003 | to confirm any link with the reform |
| NFCom, BP-e, NF3e, NFAg, NFGas, NF-e ABI | do not exist | Ato Conjunto RFB/CGIBS 4/2026 | no print NT confirmed |

## Read more

- [Research](research.md): what each regulation requires, with sources and what is still unconfirmed.
- [Roadmap](roadmap.md): tasks, date limits and the Gantt schedule.

## How to contribute

Factual corrections, better sources and disagreements about the schedule are welcome in an issue or
PR. The date table and the Gantt generator (`scripts/generate_reforma_gantt.py`) live in the
repository so anyone can adjust them.
