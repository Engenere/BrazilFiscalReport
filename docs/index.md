[![tests](https://github.com/engenere/BrazilFiscalReport/workflows/tests/badge.svg)](https://github.com/Engenere/BrazilFiscalReport/actions)
[![codecov](https://codecov.io/gh/engenere/BrazilFiscalReport/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Engenere/BrazilFiscalReport)
[![python versions](https://img.shields.io/pypi/pyversions/brazilfiscalreport)](https://pypi.org/project/BrazilFiscalReport/)
[![pypi](https://img.shields.io/pypi/v/brazilfiscalreport.svg)](https://pypi.org/project/BrazilFiscalReport/)
[![license](https://img.shields.io/github/license/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE)
[![contributors](https://img.shields.io/github/contributors/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/graphs/contributors)
[![pypi-downloads](https://static.pepy.tech/badge/brazilfiscalreport)](https://pepy.tech/projects/brazilfiscalreport)

# Brazil Fiscal Report

![Brazil Fiscal Report - XML to PDF](assets/banner.svg)

Python library for generating Brazilian auxiliary fiscal documents in PDF from XML documents.

## Supported Documents

| Preview | Document | XML Source |
|:---:|----------|:---:|
| [![DANFE preview](assets/screenshots/danfe.png){ width="120" }](danfe.md) | [**DANFE**](danfe.md) — Documento Auxiliar da Nota Fiscal Eletrônica | NF-e |
| [![DACTE preview](assets/screenshots/dacte.png){ width="120" }](dacte.md) | [**DACTE**](dacte.md) — Documento Auxiliar do Conhecimento de Transporte Eletrônico | CT-e |
| [![DAMDFE preview](assets/screenshots/damdfe.png){ width="120" }](damdfe.md) | [**DAMDFE**](damdfe.md) — Documento Auxiliar do Manifesto Eletrônico de Documentos Fiscais | MDF-e |
| [![DACCe preview](assets/screenshots/dacce.png){ width="120" }](dacce.md) | [**DACCe**](dacce.md) — Documento Auxiliar da Carta de Correção Eletrônica | CC-e |
| [![DANFSE preview](assets/screenshots/danfse.png){ width="120" }](danfse.md) | [**DANFSE**](danfse.md) — Documento Auxiliar da Nota Fiscal de Serviços Eletrônica | NFS-e |

## Usage Modes

### 1. Python Code

For full customization and integration, use the library directly in Python. Configure margins, fonts, receipt positions, and more for each document type.

[Get started :material-arrow-right:](getting-started.md){ .md-button }

### 2. CLI (Command Line)

For quick PDF generation from the terminal with a simple `config.yaml` file.

[CLI documentation :material-arrow-right:](cli.md){ .md-button }

### 3. Try it Online

Upload your fiscal XML and get the PDF instantly — no installation needed.

[Try it online :material-arrow-right:](https://brazilfiscalreport.streamlit.app){ .md-button }

## Dependencies

- [FPDF2](https://github.com/py-pdf/fpdf2) - PDF creation library for Python
- [phonenumbers](https://github.com/daviddrysdale/python-phonenumbers) - Phone number formatting
- [python-barcode](https://github.com/WhyNotHugo/python-barcode) - Barcode generation
- [qrcode](https://github.com/lincolnloop/python-qrcode) - QR code generation (required for DACTE, DAMDFE and DANFSE)
