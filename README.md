[![tests](https://github.com/engenere/BrazilFiscalReport/workflows/tests/badge.svg)](https://github.com/Engenere/BrazilFiscalReport/actions)
[![codecov](https://codecov.io/gh/engenere/BrazilFiscalReport/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Engenere/BrazilFiscalReport)
[![python versions](https://img.shields.io/pypi/pyversions/brazilfiscalreport)](https://pypi.org/project/BrazilFiscalReport/)
[![pypi](https://img.shields.io/pypi/v/brazilfiscalreport.svg)](https://pypi.org/project/BrazilFiscalReport/)
[![license](https://img.shields.io/github/license/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE)
[![contributors](https://img.shields.io/github/contributors/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/graphs/contributors)
[![pypi-downloads](https://static.pepy.tech/badge/brazilfiscalreport)](https://pepy.tech/projects/brazilfiscalreport)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://brazilfiscalreport.streamlit.app)

# Brazil Fiscal Report

![Brazil Fiscal Report - XML to PDF](https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/banner.svg)

Python library for generating Brazilian auxiliary fiscal documents in PDF from XML documents.

> 🇧🇷 Biblioteca Python para gerar em PDF os documentos auxiliares das notas fiscais — **DANFE**, **DACTE**, **DAMDFE**, **DACCe** e **DANFSE** — a partir do XML de NF-e, CT-e, MDF-e, CC-e e NFS-e. **[Documentação em português →](https://engenere.github.io/BrazilFiscalReport/pt/)**

**[Documentation](https://engenere.github.io/BrazilFiscalReport/)** | **[PyPI](https://pypi.org/project/BrazilFiscalReport/)** | **[Try it Online](https://brazilfiscalreport.streamlit.app)**

## Output Examples

| [**DANFE**](https://engenere.github.io/BrazilFiscalReport/danfe/) | [**DACTE**](https://engenere.github.io/BrazilFiscalReport/dacte/) | [**DAMDFE**](https://engenere.github.io/BrazilFiscalReport/damdfe/) | [**DACCe**](https://engenere.github.io/BrazilFiscalReport/dacce/) | [**DANFSE**](https://engenere.github.io/BrazilFiscalReport/danfse/) |
|:---:|:---:|:---:|:---:|:---:|
| [<img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/danfe.png" alt="DANFE generated in PDF" width="150">](https://engenere.github.io/BrazilFiscalReport/danfe/) | [<img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/dacte.png" alt="DACTE generated in PDF" width="150">](https://engenere.github.io/BrazilFiscalReport/dacte/) | [<img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/damdfe.png" alt="DAMDFE generated in PDF" width="150">](https://engenere.github.io/BrazilFiscalReport/damdfe/) | [<img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/dacce.png" alt="DACCe generated in PDF" width="150">](https://engenere.github.io/BrazilFiscalReport/dacce/) | [<img src="https://raw.githubusercontent.com/Engenere/BrazilFiscalReport/main/docs/assets/screenshots/danfse.png" alt="DANFSE generated in PDF" width="150">](https://engenere.github.io/BrazilFiscalReport/danfse/) |
| <sub>Documento Auxiliar da Nota Fiscal Eletrônica<br>**NF-e** → PDF</sub> | <sub>Documento Auxiliar do Conhecimento de Transporte Eletrônico<br>**CT-e** → PDF</sub> | <sub>Documento Auxiliar do Manifesto Eletrônico de Documentos Fiscais<br>**MDF-e** → PDF</sub> | <sub>Documento Auxiliar da Carta de Correção Eletrônica<br>**CC-e** → PDF</sub> | <sub>Documento Auxiliar da Nota Fiscal de Serviços Eletrônica<br>**NFS-e** → PDF</sub> |

## Why BrazilFiscalReport?

- 🐍 **Pure Python** — built on [fpdf2](https://github.com/py-pdf/fpdf2); no wkhtmltopdf, no headless browser, no HTML templates
- 📄 **5 document types** — DANFE, DACTE, DAMDFE, DACCe and DANFSE, straight from the official XML
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

The same pattern applies to all document types:

```python
from brazilfiscalreport.dacte import Dacte
from brazilfiscalreport.damdfe import Damdfe
from brazilfiscalreport.danfse import Danfse
from brazilfiscalreport.dacce import DaCCe

dacte = Dacte(xml=cte_xml)
dacte.output("dacte.pdf")

damdfe = Damdfe(xml=mdfe_xml)
damdfe.output("damdfe.pdf")

danfse = Danfse(xml=nfse_xml)
danfse.output("danfse.pdf")

# emitente (optional): issuer info shown in the DACCe header
dacce = DaCCe(xml=cce_xml)
dacce.output("dacce.pdf")
```

Each document type accepts a configuration object for customization (logo, margins, fonts, watermarks and more) — see the [documentation](https://engenere.github.io/BrazilFiscalReport/) for all options.

> 🚀 **No setup?** [Try it online](https://brazilfiscalreport.streamlit.app) — upload your fiscal XML, download the PDF.

## CLI

Generate PDFs directly from the terminal:

```bash
bfrep danfe /path/to/nfe.xml
bfrep dacte /path/to/cte.xml
bfrep damdfe /path/to/mdfe.xml
bfrep dacce /path/to/cce.xml
bfrep danfse /path/to/nfse.xml
```

See the [CLI documentation](https://engenere.github.io/BrazilFiscalReport/cli/) for configuration options.

## Dependencies

- [FPDF2](https://github.com/py-pdf/fpdf2) - PDF creation library for Python
- [phonenumbers](https://github.com/daviddrysdale/python-phonenumbers) - Phone number formatting
- [python-barcode](https://github.com/WhyNotHugo/python-barcode) - Barcode generation
- [qrcode](https://github.com/lincolnloop/python-qrcode) - QR code generation (required for DACTE, DAMDFE and DANFSE)

## License

BrazilFiscalReport is free software licensed under the [LGPL-3.0](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE) license.

## Credits

This is a fork of the [nfe_utils](https://github.com/edsonbernar/nfe_utils) project, originally created by [Edson Bernardino](https://github.com/edsonbernar).

## Maintainer

Developed and maintained by [Engenere](https://engenere.one/). Issues and pull requests are welcome — see the [contributing guide](https://engenere.github.io/BrazilFiscalReport/contributing/).

[![Engenere](https://storage.googleapis.com/eng-imagens/logo-fundo-preto.webp)](https://engenere.one/)
