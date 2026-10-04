# Roadmap

Tasks per document, with the **legal deadline** (where the regulation sets one) and a **proposed
schedule** that works back from it. The proposed dates depend on alignment with the maintainers.

![Proposed schedule](../assets/reforma-gantt-en-light.png#only-light)
![Proposed schedule](../assets/reforma-gantt-en-dark.png#only-dark)

## Legal deadlines

| Date | What | Source |
|---|---|---|
| 2026-11-16 | NT 2026.004 in production (CT-e and others) | NT 2026.004 |
| 2026-12-01 | NT 2026.010 in production (NF-e DANFE) | NT 2026.010 |

## Tasks

| ID | Task | Start | End | Status |
|---|---|---|---|---|
| A1 | Research on NT 2026.010 | 10-03 | 10-04 | done |
| A2 | Alignment with maintainers (this PR) | 10-05 | 10-16 | proposed |
| A3 | Portrait DANFE implementation: totals block, CRT, per-item fields, effective rate rule | 10-19 | 11-06 | proposed |
| A4 | Tests and reference PDFs | 11-09 | 11-13 | proposed |
| A5 | Review and merge | 11-16 | 11-19 | proposed |
| A6 | Library release | 11-20 | 11-20 | proposed |
| A7 | Integration in consumers | 11-23 | 11-30 | proposed |
| A8 | Landscape layout | 12-07 | 12-18 | optional |
| B1 | Research: does NT 2026.004 change the DACTE? | 10-05 | 10-16 | proposed |
| B2 | DACTE implementation, if it changes | 10-19 | 11-06 | conditional on B1 |
| B3 | DACTE tests and review | 11-09 | 11-13 | conditional on B1 |
| C1 | Research: NT 008 and NT 009 (DANFSe) | 10-19 | 10-30 | proposed |
| C2 | DANFSe implementation | no date | no date | depends on the NT 009 date |
| D1 | Research: DANFCe and simplified DANFE | 10-19 | 10-30 | proposed |
| D2 | Follow PR #202 (DANFCe) | 11-02 | ongoing | no date |
| E1 | Print NT research: NFCom, BP-e, NF3e... | 11-02 | 11-13 | optional |

The gap between the release (A6, 11-20) and the 12-01 deadline is there for consumers to integrate
and test (A7). If alignment (A2) slips, A8 is the first item to move.

## Assumptions

1. One module per PR, for review in parts.
2. Reference PDFs in `tests/fixtures` and `tests/generated` follow the procedure already documented
   (same `fpdf2` version as CI).
3. Integration in other projects (A7) is each consumer's responsibility and is not part of this
   repository.
4. New documents (NFCom, BP-e, NF3e...) only come in with a confirmed print NT and demand.

## Updating the schedule

The dates live in `scripts/generate_reforma_gantt.py` (the `TASKS` and `DEADLINES` lists). After
editing, run `pip install matplotlib` and `python scripts/generate_reforma_gantt.py` to regenerate the
images in `docs/assets/`. Matplotlib is used only for the documentation and is not a dependency of the
library.
