# Guia de Integração — DANFSe NT 008/009 → upstream BrazilFiscalReport

Alvo: **PR para `Engenere/BrazilFiscalReport`** (`main`).
Estilo: parser/renderer separados, sem quebrar módulos compartilhados.

---

## 0. ⚠️ Antes de tudo: o upstream JÁ EVOLUIU

O código-base que originou este port é um snapshot mais antigo. No `main`
atual existem diferenças que **precisam ser reconciliadas** antes do PR:

| Item | Snapshot do port | `main` atual (upstream) |
|---|---|---|
| Bug `issqn_retained` | corrigido por nós | **já corrigido** (commit `48db172`, 08/jun/2026) |
| `DecimalConfig.price_precision` | 2 | **4** |
| `utils.format_cpf_cnpj` | alfanumérico | `re.sub(r"\D","")` (só dígitos) — **compartilhado** |
| `utils.get_tag_text` | com `.strip()` | sem `.strip()` |
| `danfse.py` | monolítico | monolítico (mesma base) |

**Ação:** começar o trabalho a partir de um clone fresco do `main`, e tratar
apenas as melhorias que ainda NÃO existem lá (lista na seção 4).

```bash
git clone https://github.com/Engenere/BrazilFiscalReport
cd BrazilFiscalReport
git checkout -b feat/danfse-nt009
```

---

## 1. Regra de ouro: não tocar em módulos compartilhados

`brazilfiscalreport/utils.py` e `brazilfiscalreport/xfpdf.py` são usados por
NFe, CTe, MDFe e CCe. **Não alterar assinaturas existentes.**

Por isso:
- Helpers exclusivos da NFS-e (CNPJ alfanumérico, `truncate_text`, `to_float`,
  `competence_allows_pis_cofins`, `iso2_country`) vão em
  **`danfse/nt009_utils.py`** (módulo local — arquivo já gerado).
- Helpers visuais NT 008 (`shade_rect`, `divider`, `page_border`) ficam
  **como métodos da classe `Danfse`**, não no `xFPDF` compartilhado.

Reaproveitar do `..utils` o que é compatível:
`format_phone`, `format_number`, `get_date_utc`, `get_tag_text`.

---

## 2. Mapeamento de arquivos

| Arquivo do port | Destino no upstream | Ação |
|---|---|---|
| `nt009_utils.py` | `danfse/nt009_utils.py` | **novo** |
| `constants.py` (domínios) | `danfse/danfse_conf.py` | **acrescentar** abaixo do `URL` |
| `fonts.py` | `danfse/fonts.py` | **novo** |
| `municipios.py` | `danfse/municipios.py` | **novo** |
| `parser.py` | `danfse/parser.py` | **novo** (split) |
| `renderer.py` → classe `Danfse` | `danfse/danfse.py` | **substituir** classe |
| `config.py` | `danfse/config.py` | **estender** (arquivo já gerado) |
| `nfse_logo.png`, `municipios.json` | `danfse/` | já existem |
| `generate_qrcode.py` | `..generate_qrcode` | **reusar** o do upstream (ver §3) |

---

## 3. Ajuste de imports (port → upstream)

No `parser.py` / `danfse.py`, trocar os imports relativos-ao-port:

```python
# de:
from . import constants as K
from .utils import format_cpf_cnpj, get_tag_text, ...
from .xfpdf import xFPDF

# para:
from .danfse_conf import URL
from . import danfse_conf as K          # se mover domínios p/ lá
from .nt009_utils import (
    truncate_text, format_cpf_cnpj_nfse, to_float,
    competence_allows_pis_cofins, iso2_country,
)
from ..utils import (
    format_phone, format_number, get_date_utc, get_tag_text,
)
from ..xfpdf import xFPDF
from ..generate_qrcode import draw_qr_code   # conferir assinatura
```

> **QR Code:** o upstream usa `python-barcode`/`qrcode` próprio. Verificar a
> assinatura de `draw_qr_code` do upstream e adaptar a chamada (não embarcar
> a reimplementação do port se já existir uma).

---

## 4. Escopo do PR (o que realmente entra)

Somente o que ainda não existe no `main`:

**NT 009 (parser):**
- [ ] CNPJ alfanumérico (`format_cpf_cnpj_nfse`).
- [ ] `finNFSe` (0/1/2) e `cStat` traduzidos por domínio.
- [ ] `opSimpNac` domínio 4 (Optante Pendente).
- [ ] Deduções ISSQN = `vAjusteBCISSQN + vCalcAjusteBCISSQN` (substitui `vDR`).
- [ ] Grupo IBS/CBS completo + `gTribSN` (Simples Nacional).
- [ ] PIS/COFINS só p/ competência ≤ dez/2026.
- [ ] `pCopropriedade` (locação de imóvel).
- [ ] País ISO-2; rodapé por pipe + truncamento 1997 + Lei 12.741/2012.

**NT 008 (renderer):**
- [ ] Módulo `fonts.py` (Arial labels / MS Sans Serif valores + fallback).
- [ ] Sombreamento 5%, divisórias 0,5pt, borda 1pt.
- [ ] QR Code 1,52×1,52 cm.
- [ ] Blocos novos: Destinatário, Intermediário (grid), Canhoto.

**Refactor:**
- [ ] Helper `_field()` (elimina repetição set_font/set_xy/cell).
- [ ] Split parser/renderer.

> Bug `issqn_retained`: **NÃO incluir** (já corrigido no upstream).

---

## 5. Conformidade com as convenções do projeto

Do `pyproject.toml` do upstream:

- **Python 3.8+** → sem `X | Y` em type hints; usar `Optional[...]`, `Union`.
- **ruff** (E, F, UP, B, SIM, C4, I) → rodar `ruff check` e `ruff format`.
- **isort** (`known-first-party = brazilfiscalreport, test`).
- **doc8** max-line 88.
- Mensagens de commit no padrão `fix(danfse): ...` / `feat(danfse): ...`.

```bash
ruff check brazilfiscalreport/danfse/
ruff format brazilfiscalreport/danfse/
```

---

## 6. Testes e regressão visual

O upstream guarda **PDFs de referência** e regenera após os testes.

- [ ] Adaptar os 11 testes do parser para `tests/` do projeto.
- [ ] Adicionar fixtures XML (sem dados sensíveis): um simples, um com
      IBS/CBS, um do Simples Nacional, um cancelado/homologação.
- [ ] Rodar `pytest` e **regenerar os PDFs de referência**.
- [ ] Conferir diff visual dos PDFs de referência (a NT 008 muda o layout —
      explicar isso na descrição do PR).

```bash
pytest tests/ -k danfse
```

---

## 7. Roteiro de commits sugerido

1. `feat(danfse): add nt009_utils (cnpj alfanumérico, truncate, helpers)`
2. `feat(danfse): add fonts module (NT 008 typography)`
3. `feat(danfse): add municipios de-para (IBGE)`
4. `refactor(danfse): split parser from renderer`
5. `feat(danfse): parse IBS/CBS, gTribSN, ajustes BC (NT 009)`
6. `feat(danfse): render destinatário, intermediário e canhoto`
7. `feat(danfse): config show_receipt + custom_font_path`
8. `test(danfse): fixtures NT 009 + regenerate reference PDFs`
9. `docs(danfse): update docs/danfse.md`

---

## 8. Descrição do PR (rascunho)

> **feat(danfse): NT 008/009 — IBS/CBS, tipografia e novos blocos**
>
> Implementa a NT 009 (LC 214/2025) no parser e a NT 008 no layout:
> grupo IBS/CBS (incl. gTribSN do Simples), CNPJ alfanumérico, deduções
> via vAjusteBC, PIS/COFINS até dez/2026, país ISO-2, rodapé por pipe.
> No visual: fontes Arial/MS Sans Serif, sombreamento 5%, QR 1,52cm,
> e os blocos Destinatário, Intermediário e Canhoto.
>
> Refactor: split parser/renderer + helper `_field`.
> Helpers exclusivos da NFS-e isolados em `danfse/nt009_utils.py` para
> não impactar utils/xfpdf compartilhados.
