# DANFSe v2.0 — Especificação de Layout (FPDF2)

> Documento Auxiliar da NFS-e. Spec estruturada para consumo por IA programadora.
> Engine: **FPDF2** · Unidade: **cm** · Normas: **NT 008**, **NT 009 (LC 214/2025)**
> Arquivo de máquina equivalente: [`danfse_spec.json`](./danfse_spec.json)

---

## Índice
1. [Helpers arquiteturais](#0-helpers-arquiteturais)
2. [Índice central de NTs](#índice-central-de-notas-técnicas)
3. [Domínios de tradução](#domínios-de-tradução)
4. [Blocos de desenho](#blocos-de-desenho)

---

## 0. Helpers arquiteturais

```python
def truncate_text(text: str, max_length: int) -> str:
    """Regra rígida de reticências (...) exigida pela NT 008."""
    if text and len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text or "-"

def apply_shading(pdf):
    """Fundo cinza 5% exigido pela NT 008 (RGB 242,242,242)."""
    pdf.set_fill_color(242, 242, 242)
    return True  # usar como fill=True em pdf.cell(...)
```

### Fontes (padrão global)
| Uso | Família | Tamanho | Estilo |
|---|---|---|---|
| Labels | Arial | 7pt | CAIXA ALTA |
| Valores | MS Sans Serif | 7pt | — |
| Título de bloco | Arial | 9pt | Negrito |
| Município (dir.) | — | 8pt | — |
| Ambiente (dir.) | — | 6pt | — |
| Legenda QR | MS Sans Serif | 6pt | — |
| Aviso homologação | Arial | 9pt | Vermelho M100/Y100 |

---

## Índice central de Notas Técnicas

### NT 008
- Regra rígida de reticências (`truncate_text`).
- Fundo cinza 5% (RGB 242,242,242) em títulos/blocos.
- Posicionamento exato de logomarca e QR Code.
- Hierarquia de fontes (Arial labels / MS Sans Serif valores).

### NT 009 (LC 214/2025)
- **CNPJ alfanumérico (Tipo C)** — NÃO tratar como inteiro no parser.
- `finNFSe` ganhou domínios **1 = Crédito** e **2 = Débito** (notas de ajuste).
- `opSimpNac` ganhou domínio **4 = Optante Pendente** e campo `cAtvSN`.
- `vDedRed`/`vDR` **descontinuado** → `vAjusteBC` (ISSQN = `vAjusteBCISSQN + vCalcAjusteBCISSQN`).
- Novos grupos IBS/CBS: `vCalcAjusteBCIBSCBS`, `vCalcAjusteBCLocImoveis`.
- **Simples Nacional**: valores IBS/CBS vêm do grupo `gTribSN` (`pIBSSN`, `vIBSSN`, `pCBSSN`, `vCBSSN`).
- **Locação de imóvel**: valores multiplicados por `pCopropriedade`.
- Indicador de operação IBS/CBS baseado na tabela **LC 214/2025**.
- Informações de pagamento no grupo `gPgtoVinc`.
- PIS/COFINS **apenas** para competência até **dez/2026**.

---

## Domínios de tradução

| Tag | Descrição | Domínio |
|---|---|---|
| `tpAmb` | Tipo de Ambiente | 1=Produção · 2=Homologação (→ aviso vermelho) |
| `tpEmit` | Emitente da NFS-e | 1=Prestador · 2=Tomador · 3=Intermediário |
| `finNFSe` | Finalidade (NT 009) | 0=Regular · 1=Crédito · 2=Débito |
| `cStat` | Situação da NFS-e | Tabela oficial SEFIN (truncar 37) |
| `opSimpNac` | Optante Simples (NT 009) | 1=Não Optante · 2=MEI · 3=ME/EPP · 4=Optante Pendente |
| `cIndOp` | Indicador Operação IBS/CBS (NT 009) | Tabela LC 214/2025 |

---

## Blocos de desenho

### 📦 1. `draw_header(pdf, data)` — Identificação (20 campos)
**Visuais fixos:** Logomarca (X:0,49cm Y:0,44cm) · "DANFSe v2.0" + "Documento Auxiliar da NFS-e" (Arial 9pt Bold) · "NFS-e SEM VALIDADE JURÍDICA" se `tpAmb==2` (vermelho).

| Campo | Tag | Regra |
|---|---|---|
| Município | `xLocEmi` + `UF` | Ocultar se cód. trib. nac.==99 · max 37 · 8pt |
| Ambiente Gerador | `ambGer` | 6pt |
| Tipo de Ambiente | `tpAmb` | traduzir · 6pt |
| Chave de Acesso | `id` | 50 dígitos, remover prefixo "NFS" · fundo branco |
| Número da NFS-e | `nNFSe` | |
| Competência | `dCompet` | DD/MM/AAAA |
| Data/Hora Emissão | `dhProc` | DD/MM/AAAA hh:mm:ss |
| Número da DPS | `nDPS` | |
| Série da DPS | `serie` | |
| Data/Hora Emissão DPS | `dhEmi` | DD/MM/AAAA hh:mm:ss |
| Emitente da NFS-e | `tpEmit` | traduzir (1–3) |
| Situação da NFS-e | `cStat` | traduzir · truncar 37 |
| Finalidade | `finNFSe` | traduzir (NT 009) · truncar 37 |

### 📦 2. `draw_qr_code(pdf, data)`
- QR: **1,52 × 1,52 cm** em **X:17,48cm / Y:1,67cm**.
- Legenda: 3 linhas, MS Sans Serif 6pt, texto fixo da norma logo abaixo.

### 📦 3. `draw_entities(pdf, data)` — Os Envolvidos
> Se nulos: fundo cinza no bloco inteiro + "NÃO IDENTIFICADO".

**Prestador (10 campos):** CNPJ/CPF/NIF (NT 009: alfanumérico, string) · IM · `fone` (20) · `xNome` (77) · Município/UF (De-Para IBGE 7díg + UF) · `cMun`+`cEndPost` (ex: `3106200 / 35494-000`) · Endereço `xLgr`+`nro`+`xCpl`+`xBairro` (77) · `email` · Simples Nacional `opSimpNac` (NT 009: domínio 4 + `cAtvSN`, truncar 37) · Regime Apuração SN `regApTribSN` (77).

**Tomador (8 campos):** mesmos do Prestador, *exceto* Simples/Regime. Se vazio → suprimir + frase fixa com fundo cinza.

**Destinatário (7 campos):** mesmos do Tomador **sem Inscrição Municipal**. Se for o próprio tomador → "O DESTINATÁRIO É O PRÓPRIO TOMADOR/ADQUIRENTE...".

**Intermediário (8 campos):** mesmos campos do Tomador.

### 📦 4. `draw_service_details(pdf, data)` — Serviço (5 campos)
| Campo | Tag/Regra |
|---|---|
| Código Trib Nac/Mun | `cTribNac` + `cTribMun` |
| Código NBS | `cNBS` |
| Local Prestação | `xLocPrestacao` + `cPaisPrestacao` (País em ISO-2, ex: BR) |
| Descrição Tributação | `xTribMun` (fallback `xTribNac`) · truncar 167 |
| Descrição do Serviço | `xDescServ` · truncar 1297 · `multi_cell` |

### 📦 5. `draw_taxes(pdf, data)` — Municipal e Federal

**ISSQN (14 campos · título fundo cinza)** — se `cTribNac` não incidir: "OPERAÇÃO NÃO SUJEITA AO ISSQN".

| Campo | Tag / Fórmula | Regra |
|---|---|---|
| Tipo Tributação | `tribISSQN` | truncar 21 |
| Município Incidência | `xLocIncid` + `cPaisResult` | |
| Regime Especial | `regEspTrib` | truncar 27 |
| Imunidade | `tpImunidade` | truncar 37 |
| Suspensão | `tpSusp` | truncar 37 |
| Nº Processo | `nProcesso` | truncar 37 |
| Benefício Municipal | `tpBM` | |
| Cálculo BM | `vCalcBM` / `vRedBCBM` | |
| Total Deduções | `vAjusteBCISSQN + vCalcAjusteBCISSQN` | **NT 009** (subst. `vDR`) |
| Desc. Incondicionado | `vDescIncond` | |
| BC ISSQN | `vBC = vServ − vDescIncond − (vAjusteBCISSQN + vCalcAjusteBCISSQN) − BM` | **NT 009** |
| Alíquota | `pAliqAplic` | |
| Retenção | `tpRetISSQN` | Sim/Não |
| ISSQN Apurado | `vISSQN` | |

**Federal exceto CBS (6 campos):** `vRetIRRF` · `vRetCP` · `vRetCSLL` · `vPis`* · `vCofins`* · Descrição `tpRetPisCofins` (truncar 35).
\* PIS/COFINS só se competência ≤ dez/2026.

### 📦 6. `draw_ibs_cbs(pdf, data)` — Reforma Tributária (NT 009 · 14 campos)
> **Simples Nacional:** puxar apuração de `gTribSN` (`pIBSSN`,`vIBSSN`,`pCBSSN`,`vCBSSN`).

| Campo | Tag / Fórmula |
|---|---|
| CST/cClassTrib | `CST` + `cClassTrib` (`nnn / nnnnnn`) |
| Ind/IBGE/Mun/UF | `cIndOp` + `cLocalidadeIncid` + `xLocalidadeIncid` + `UF` (LC 214) |
| Exclusões/Reduções | `vCalcAjusteBCIBSCBS + vCalcAjusteBCLocImoveis` |
| BC Após Exclusões | `vBC = vServ − vDescIncond − vCalcAjusteBCIBSCBS − vCalcAjusteBCLocImoveis − vISSQN − vPIS − vCOFINS` |
| Red. Alíquotas | `pRedAliqUF` + `pRedAliqMun` + `pRedAliqCBS` (% / % / %) |
| Alíquota IBS UF/Mun | `pIBSUF` + `pIBSMun` |
| Alíq Efetiva Mun | `pAliqEfetMun` |
| Valor Apurado Mun | `vIBSMun` |
| Alíq Efetiva Est | `pAliqEfetUF` |
| Valor Apurado Est | `vIBSUF` |
| Valor Total IBS | `vIBSTot` (SN → `gTribSN.vIBSSN`) |
| Alíquota CBS | `pCBS` (SN → `gTribSN.pCBSSN`) |
| Alíq Efetiva CBS | `pAliqEfetCBS` |
| Valor Total CBS | `vCBS` (SN → `gTribSN.vCBSSN`) |

### 📦 7. `draw_totals(pdf, data)` — Consolidado (7 campos)
| Campo | Tag / Fórmula | Regra |
|---|---|---|
| Valor Operação/Serviço | `vServ` | NT 009 Locação: × `pCopropriedade` |
| Desc. Incondicionado | `vDescIncond` | NT 009 Locação: × `pCopropriedade` |
| Desc. Condicionado | `vDescCond` | NT 009 Locação: × `pCopropriedade` |
| Total Retenções | `vTotalRet` | ISSQN + Federais |
| Valor Líquido | `vLiq` | |
| Total IBS/CBS | `vIBSTot + vCBS` | |
| **Valor Líquido + IBS/CBS** | `vTotNF` | **Fundo cinza 5% no label e na célula** |

### 📦 8. `draw_additional_info(pdf, data)` — Rodapé (`multi_cell` dinâmico)
Concatenação separada por **`|`**:
```
Inf. Cont.: {xInfComp} | NFS-e Subst.: {chSubstda} | Doc. Ref.: {docRef} |
Cod. Obra: {cObra} | Insc. Imob.: {inscImobFisc} | Cod. Evt.: {idAtvEvt} |
Doc. Tec.: {idDocTec} | Núm. Ped.: {xPed} | Item Ped.: {xItemPed} | Out. Inf.: {xOutInf}
```
- **NT 009:** incluir pagamento de `gPgtoVinc` se disponibilizado na emissão.
- **Truncar em exatos 1997 caracteres** — sem apagar a linha fixa final.
- **Linha fixa final (Lei 12.741/2012, ignora o limite):**
  `Totais Aproximados dos Tributos cfe. Lei nº 12.741/2012: Federais: R$ ...; Estaduais: R$ ...; Municipais: R$ ...`

### 📦 9. `draw_canhoto(pdf, data)` — Opcional
> Só se `config.show_receipt == True`.

- Data Cientificação
- Identificação/Assinatura
- Nº NFS-e / Chave NFS-e: `nNFSe` + `id` (concatenação)
