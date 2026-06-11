# DANFSe v2.0 — Port refatorado (Python / FPDF2)

Port da classe `Danfse` original, **refatorado**, com **correção de bugs** e
**implementação da NT 009 (LC 214/2025)**. Conformidade visual com a **NT 008**.

## Como usar

```python
from danfse.port import Danfse, DanfseConfig, generate_danfse

xml = open("nota.xml", encoding="utf-8").read()

# 1) atalho
generate_danfse(xml, "danfse.pdf")

# 2) com configuração
cfg = DanfseConfig(
    watermark_cancelled=False,     # marca d'água "CANCELADA"
    show_receipt=True,             # imprime o canhoto (bloco 9)
    custom_font_path="micross.ttf" # MS Sans Serif real (NT 008) — opcional
)
doc = Danfse(xml, cfg)
doc.output("danfse.pdf")

# 3) só os dados (sem PDF)
from danfse.port import DanfseParser
data = DanfseParser(xml).parse()
```

## Estrutura

| Módulo | Responsabilidade |
|---|---|
| `constants.py` | Namespace XML + domínios de tradução (NT 009) + limites NT 008 |
| `utils.py` | Formatadores seguros + `truncate_text` + CNPJ alfanumérico |
| `config.py` | `DanfseConfig` (sem fonte hardcoded do Windows) |
| `fonts.py` | Tipografia NT 008 (Arial labels / MS Sans Serif valores) |
| `municipios.py` | De-Para IBGE (7 díg) → "Nome - UF" |
| `generate_qrcode.py` | QR Code 1,52×1,52 cm (NT 008) |
| `xfpdf.py` | Classe base (`long_field`, `text_box`, sombreamento, divisórias) |
| `parser.py` | `DanfseParser` — XML → dict (ETL) |
| `renderer.py` | `Danfse` — desenho dos 9 blocos (FPDF2) |

## Camadas

```
XML ──► DanfseParser.parse() ──► data (dict) ──► Danfse(renderer) ──► PDF
```

Parser e renderer são independentes e testáveis em separado.

## Bugs do original corrigidos

1. `tax_regim` nunca aparecia (comparava texto traduzido com código "3").
2. Retenções zeravam (somava número com string `"R$ ..."`).
3. `KeyError` em `tpRetISSQN`/`tpSusp` (acesso direto sem default).
4. `Id[3:]` quebrava quando `Id` era `None`.
5. Fonte Windows hardcoded (`C:\Windows\Fonts\micross.ttf`).

## NT 009 implementado

- CNPJ alfanumérico (Tipo C).
- `finNFSe` (0/1/2) e `cStat` traduzidos por domínio.
- `opSimpNac` domínio 4 (Optante Pendente).
- Deduções ISSQN = `vAjusteBCISSQN + vCalcAjusteBCISSQN` (substitui `vDR`).
- Grupo IBS/CBS completo, incl. `gTribSN` (Simples Nacional).
- PIS/COFINS apenas para competência ≤ dez/2026.
- `pCopropriedade` (locação de imóvel).
- País em ISO-2; concatenação por pipe + truncamento 1997 + Lei 12.741/2012.
- Blocos novos: Destinatário, Intermediário e Canhoto.

## NT 008 (visual)

- Fontes: Arial (labels) / MS Sans Serif (valores, com fallback Helvetica).
- Sombreamento cinza 5% (cabeçalho, títulos, Emitente, Valor Líquido + IBS/CBS).
- QR Code 1,52×1,52 cm.
- Marca d'água (CANCELADA / SEM VALOR FISCAL) e aviso de homologação.
- Borda 1pt / divisórias 0,5pt.

> **Fonte MS Sans Serif:** sem a TTF `micross.ttf`, os valores usam Helvetica
> (sem-serifa). Para conformidade total, informe `custom_font_path`.

## Testes

```bash
python3 danfse/port/tests/test_parser.py     # 11 testes do parser
```

Saídas de exemplo geradas em `tests/out_real.pdf` e `tests/out_canhoto.pdf`.
