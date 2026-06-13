[![tests](https://github.com/Engenere/BrazilFiscalReport/workflows/tests/badge.svg)](https://github.com/Engenere/BrazilFiscalReport/actions)
[![codecov](https://codecov.io/gh/Engenere/BrazilFiscalReport/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Engenere/BrazilFiscalReport)
[![pypi](https://img.shields.io/pypi/v/brazilfiscalreport.svg)](https://pypi.org/project/BrazilFiscalReport/)
[![license](https://img.shields.io/github/license/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE)
[![contributors](https://img.shields.io/github/contributors/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/graphs/contributors)
[![pypi-downloads](https://static.pepy.tech/badge/brazilfiscalreport)](https://pepy.tech/projects/brazilfiscalreport)
[![Open in Streamlit](https://img.shields.io/badge/Open%20in-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://brazilfiscalreport.streamlit.app)

# Brazil Fiscal Report

Python library for generating Brazilian auxiliary fiscal documents in PDF from XML documents.

Every Brazilian electronic invoice is issued by the tax authority as an XML file. This library turns that XML into the official, printable PDF that has to accompany the goods or service: **NF-e → DANFE**, **CT-e → DACTE**, **MDF-e → DAMDFE** and **NFS-e → DANFSE**. It also renders the **DACCe**, the printout for the NF-e correction-letter event (CC-e).

> 🇧🇷 Biblioteca Python para gerar em PDF os documentos auxiliares das notas fiscais — **DANFE**, **DACTE**, **DAMDFE**, **DACCe** e **DANFSE** — a partir do XML de NF-e, CT-e, MDF-e, CC-e e NFS-e. **[Documentação em português →](https://engenere.github.io/BrazilFiscalReport/pt/)**

**[Documentation](https://engenere.github.io/BrazilFiscalReport/)** | **[PyPI](https://pypi.org/project/BrazilFiscalReport/)** | **[Try it Online](https://brazilfiscalreport.streamlit.app)**

## Output Examples

<table>
  <tr>
    <td align="center" width="25%"><a href="https://engenere.github.io/BrazilFiscalReport/danfe/"><b>DANFE</b></a></td>
    <td align="center" width="25%"><a href="https://engenere.github.io/BrazilFiscalReport/dacte/"><b>DACTE</b></a></td>
    <td align="center" width="25%"><a href="https://engenere.github.io/BrazilFiscalReport/damdfe/"><b>DAMDFE</b></a></td>
    <td align="center" width="25%"><a href="https://engenere.github.io/BrazilFiscalReport/danfse/"><b>DANFSE</b></a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://engenere.github.io/BrazilFiscalReport/danfe/"><img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/danfe.png" alt="DANFE generated in PDF" width="150"></a></td>
    <td align="center"><a href="https://engenere.github.io/BrazilFiscalReport/dacte/"><img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/dacte.png" alt="DACTE generated in PDF" width="150"></a></td>
    <td align="center"><a href="https://engenere.github.io/BrazilFiscalReport/damdfe/"><img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/damdfe.png" alt="DAMDFE generated in PDF" width="150"></a></td>
    <td align="center"><a href="https://engenere.github.io/BrazilFiscalReport/danfse/"><img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/danfse.png" alt="DANFSE generated in PDF" width="150"></a></td>
  </tr>
  <tr>
    <td align="center"><sub><b>NF-e</b> → PDF<br>Electronic invoice (goods)</sub></td>
    <td align="center"><sub><b>CT-e</b> → PDF<br>Freight bill</sub></td>
    <td align="center"><sub><b>MDF-e</b> → PDF<br>Cargo manifest</sub></td>
    <td align="center"><sub><b>NFS-e</b> → PDF<br>Service invoice</sub></td>
  </tr>
</table>

## Why BrazilFiscalReport?

- 🐍 **Pure Python** — built on [fpdf2](https://github.com/py-pdf/fpdf2); no wkhtmltopdf, no headless browser, no HTML templates
- 📄 **4 document types** — DANFE, DACTE, DAMDFE and DANFSE (plus the DACCe correction-letter event), straight from the official XML
- 🎨 **Customizable** — issuer logo, margins, fonts, decimal precision, cancellation watermarks and more
- ⚡ **3 ways to use it** — Python API, `bfrep` command line, or the [online demo](https://brazilfiscalreport.streamlit.app)
- ✅ **Python 3.8+** — tested on Python 3.8 through 3.13

## Installation

```bash
pip install brazilfiscalreport
```

This installs the core library with support for **DANFE** and **DACCe**. For additional document types and features:

```bash
pip install 'brazilfiscalreport[dacte]'   # DACTE support (requires qrcode)
pip install 'brazilfiscalreport[damdfe]'  # DAMDFE support (requires qrcode)
pip install 'brazilfiscalreport[danfse]'  # DANFSE support (requires qrcode)
pip install 'brazilfiscalreport[cli]'     # CLI tool
pip install 'brazilfiscalreport[dacte,damdfe,danfse,cli]'  # All extras
```

## Quick Start

```python
from brazilfiscalreport.danfe import Danfe

with open("nfe.xml", "r", encoding="utf8") as file:
    xml_content = file.read()

danfe = Danfe(xml=xml_content)
danfe.output("danfe.pdf")
```

> `nfe.xml` is the authorized XML your ERP or the SEFAZ portal returns once the invoice is approved.

The same pattern works for every document type — import the matching class (`Dacte`, `Damdfe`, `Danfse`, `DaCCe`), pass the XML and call `.output()`.

### Customization

Need a logo, custom margins or a different font? Pass a config object:

```python
from brazilfiscalreport.danfe import Danfe, DanfeConfig, Margins, FontType

with open("nfe.xml", encoding="utf8") as file:
    xml_content = file.read()

config = DanfeConfig(
    logo="logo.png",
    margins=Margins(top=5, right=5, bottom=5, left=5),
    font_type=FontType.TIMES,
)
danfe = Danfe(xml=xml_content, config=config)
danfe.output("danfe.pdf")
```

See the [documentation](https://engenere.github.io/BrazilFiscalReport/) for every option — watermarks, decimal precision, receipt position and more.

> 🚀 **No setup?** [Try it online](https://brazilfiscalreport.streamlit.app) — upload your fiscal XML, download the PDF.

## CLI

```bash
pip install 'brazilfiscalreport[cli]'

bfrep danfe nfe.xml        # writes nfe.pdf in the current folder
```

`bfrep` ships one subcommand per document type — `danfe`, `dacte`, `damdfe`, `dacce` and `danfse` — each turning its XML into the matching PDF. Drop a `config.yaml` next to your files to set issuer data, logo and margins.

See the [CLI documentation](https://engenere.github.io/BrazilFiscalReport/cli/) for all options.

## License

BrazilFiscalReport is free software licensed under the [LGPL-3.0](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE) license.

## Maintainer

Developed and maintained by [Engenere](https://engenere.one/). Issues and pull requests are welcome — see the [contributing guide](https://engenere.github.io/BrazilFiscalReport/contributing/).

[![Engenere](https://storage.googleapis.com/eng-imagens/logo-fundo-preto.webp)](https://engenere.one/)
