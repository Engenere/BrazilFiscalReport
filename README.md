[![tests](https://github.com/engenere/BrazilFiscalReport/workflows/tests/badge.svg)](https://github.com/Engenere/BrazilFiscalReport/actions)
[![codecov](https://codecov.io/gh/engenere/BrazilFiscalReport/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Engenere/BrazilFiscalReport)
[![python](https://img.shields.io/github/languages/top/Engenere/brazilfiscalreport)](https://pypi.org/project/BrazilFiscalReport/)
[![pypi](https://img.shields.io/pypi/v/brazilfiscalreport.svg)](https://pypi.org/project/BrazilFiscalReport/)
[![license](https://img.shields.io/github/license/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE)
[![contributors](https://img.shields.io/github/contributors/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/graphs/contributors)
[![pypi-downloads](https://static.pepy.tech/badge/brazilfiscalreport)](https://pepy.tech/projects/brazilfiscalreport)

# Brazil Fiscal Report

![Brazil Fiscal Report - XML to PDF](docs/assets/banner.svg)

Python library for generating Brazilian auxiliary fiscal documents in PDF from XML documents.

> Biblioteca Python para gerar **DANFE**, **DACTE**, **DAMDFE**, **DACCe** e **DANFSE** em PDF a partir de XML de NF-e, CT-e, MDF-e, CC-e e NFS-e.

**[Documentation](https://engenere.github.io/BrazilFiscalReport/)** | **[PyPI](https://pypi.org/project/BrazilFiscalReport/)** | **[Try it Online](https://brazilfiscalreport.streamlit.app)**

## Supported Documents

| Document | Description | XML Source |
|----------|-------------|------------|
| **DANFE** | Documento Auxiliar da Nota Fiscal Eletrônica | NF-e |
| **DACCe** | Documento Auxiliar da Carta de Correção Eletrônica | CC-e |
| **DACTE** | Documento Auxiliar do Conhecimento de Transporte Eletrônico | CT-e |
| **DAMDFE** | Documento Auxiliar do Manifesto Eletrônico de Documentos Fiscais | MDF-e |
| **DANFSE** | Documento Auxiliar da Nota Fiscal de Serviços Eletrônica | NFS-e |

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
from brazilfiscalreport.dacce import DaCCe

dacte = Dacte(xml=cte_xml)
dacte.output("dacte.pdf")

damdfe = Damdfe(xml=mdfe_xml)
damdfe.output("damdfe.pdf")

dacce = DaCCe(xml=cce_xml)
dacce.output("dacce.pdf")
```

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

## Credits

This is a fork of the [nfe_utils](https://github.com/edsonbernar/nfe_utils) project, originally created by [Edson Bernardino](https://github.com/edsonbernar).

## Maintainer

[![Engenere](https://storage.googleapis.com/eng-imagens/logo-fundo-preto.webp)](https://engenere.one/)
