# Research

Result of reading the regulations on 2026-10-04. Each item says whether it is **confirmed** (regulation
text read) or **to confirm**. The print layouts refer to the paper and PDF representation; fields remain
defined by the MOC and the NF-e schemas.

## NF-e DANFE (model 55): NT 2026.010 v1.00

- **Source:** [NT 2026.010 (NF-e Portal)](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=ugn4MYF5PLg=),
  published 2026-10-01 and approved by Ato Técnico Conjunto RFB/CGIBS 8/2026. sha256 of the PDF read:
  `eadc5246235f37a55f8140ddcf84595c8ce77f2d760f111f7b85ddf389b8f484`.
- **Production:** 2026-12-01. No test phase is stated.
- **Guidelines:** minimal disruption to the current model, legibility and A4 compatibility. It defines a
  reference **portrait** layout and an alternative **landscape** one, with the same fields.

### 4.1 New "Total IBS/CBS/IS" block

Inserted right after the "Total ICMS/IPI" block.

| Printed field | Tag (ID) |
|---|---|
| CBS amount | `vCBS` (W56) |
| IBS UF amount | `vIBSUF` (W41) |
| IBS Municipality amount | `vIBSMun` (W46) |
| Selective Tax amount | `vIS` (W33) |
| Monophase IBS amount | `vIBSMono` (W58) |
| Monophase CBS amount | `vCBSMono` (W59) |
| Monophase IBS by withholding | `vIBSMonoReten` (W59a) |
| Monophase CBS by withholding | `vCBSMonoReten` (W59b) |

### 4.2 Issuer block

- **Tax Regime Code** (`CRT`, C21): now printed.
- **IBS/CBS assessment regime type:** the NT reserves the area, but the tag will be published in a
  future NT. Until the source is defined, **do not print content** in that field.

### 4.3 Items ("Products/Services data")

| Printed field | Tag (ID) |
|---|---|
| IBS/CBS tax classification | `cClassTrib` (UB14) |
| IBS/CBS calculation base | `vBC` (UB16) |
| IBS UF rate / amount | `pIBSUF` (UB18) or `pAliqEfet` (UB28) / `vIBSUF` (UB35) |
| IBS Municipality rate / amount | `pIBSMun` (UB37) or `pAliqEfet` (UB47) / `vIBSMun` (UB54) |
| CBS rate / amount | `pCBS` (UB56) or `pAliqEfet` (UB66) / `vCBS` (UB67) |
| IS base, rate and amount | `vBCIS` (UB05), `pIS` (UB06), `vIS` (UB11) |

**Rate printing rule:** when there is a rate reduction (`gRed`) or government purchase (`gCompraGov`),
print the effective rate (`pAliqEfet`) for IBS UF, IBS Municipality and CBS; without `gRed`, print the
current rate (`pIBSUF`, `pIBSMun`, `pCBS`).

### 4.4 Optional fields and blocks

Display is optional or conditional on the information existing in the XML, for example the receipt
stub, invoice/installments, `vFCP`, `vFCPST`, `vICMSUFDest`, `vFCPUFDest` and the monophase ICMS
quantity base. The NT is explicit: optional display **does not allow creating, inferring or printing
information that is not in the XML**.

## DACTE (CT-e)

- **Today:** the library's DACTE already has the `display_ibs_cbs` option, with IBS UF, IBS Municipality
  and CBS columns (`brazilfiscalreport/dacte/dacte.py`).
- **Regulation:** NT 2026.004 v1.00 (CT-e, NFCom, BP-e, NF3e, NFAg, NFGas), test 2026-10-13 and
  production 2026-11-16 (Simplified CT-e: 2026-12-14). Total rule: `vTotDFe` repeats `vTPrest`, and from
  2027 IBS and CBS sit inside `vTPrest`; the `vTPrestLiq` field is added.
  Source: [NT 2026.004 (CT-e Portal)](https://www.cte.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=r9eZhnUIcAk=).
- **To confirm:** whether the NT changes the DACTE print layout or only the XML.

## DANFSe (NFS-e)

- **Regulation:** NT SE/CGNFS-e 008 v1.02 (DANFSe layout, 2026-07-20) and NT 009 v1.01 (approved by Ato
  Técnico Conjunto 7/2026, published 2026-10-01), which brings the DPS IBS/CBS group. NT 009 has **no
  production date**. Source: [NFS-e Portal](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc).
- **To confirm:** which IBS/CBS fields the DANFSe must print.

## Other documents

- **DAMDFE:** the MDF-e layout has no IBS/CBS fields; no change expected.
- **DANFCe:** the library has PR #202 (open) and issue #122. I found no print NT for the DANFCe with
  IBS/CBS.
- **Simplified DANFE:** NT 2026.003 defines the Type 2 Simplified DANFE (label); library issue #115
  covers it. A direct link with the reform is not clear.
- **NFCom, BP-e, NF3e, NFAg, NFGas and NF-e ABI:** have mandatory dates in
  [Ato Conjunto RFB/CGIBS 4/2026](https://www.cgibs.gov.br/atos-conjuntos) (NFCom 2026-10-01; the others
  2026-12-01), but I found no print NT for them. They are new documents in the library.

## Sources and access

All sources are official regulations and portals, accessed on 2026-10-04: NF-e Portal, CT-e Portal,
NFS-e Portal and CGIBS. The list of technical acts is at <https://www.cgibs.gov.br/atos-tecnicos-conjuntos>.
