[![tests](https://github.com/engenere/BrazilFiscalReport/workflows/tests/badge.svg)](https://github.com/Engenere/BrazilFiscalReport/actions)
[![codecov](https://codecov.io/gh/engenere/BrazilFiscalReport/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Engenere/BrazilFiscalReport)
[![versões de python](https://img.shields.io/pypi/pyversions/brazilfiscalreport)](https://pypi.org/project/BrazilFiscalReport/)
[![pypi](https://img.shields.io/pypi/v/brazilfiscalreport.svg)](https://pypi.org/project/BrazilFiscalReport/)
[![licença](https://img.shields.io/github/license/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/blob/main/LICENSE)
[![contribuidores](https://img.shields.io/github/contributors/Engenere/BrazilFiscalReport)](https://github.com/Engenere/BrazilFiscalReport/graphs/contributors)
[![downloads no pypi](https://static.pepy.tech/badge/brazilfiscalreport)](https://pepy.tech/projects/brazilfiscalreport)

# Brazil Fiscal Report

Biblioteca Python para geração de documentos fiscais auxiliares brasileiros em PDF a partir de documentos XML.

## Documentos Suportados

| Prévia | Documento | Origem XML |
|:---:|-----------|:---:|
| [![Prévia do DANFE](assets/screenshots/danfe.png){ width="120" }](danfe.md) | [**DANFE**](danfe.md) — Documento Auxiliar da Nota Fiscal Eletrônica | NF-e |
| [![Prévia do DACTE](assets/screenshots/dacte.png){ width="120" }](dacte.md) | [**DACTE**](dacte.md) — Documento Auxiliar do Conhecimento de Transporte Eletrônico | CT-e |
| [![Prévia do DAMDFE](assets/screenshots/damdfe.png){ width="120" }](damdfe.md) | [**DAMDFE**](damdfe.md) — Documento Auxiliar do Manifesto Eletrônico de Documentos Fiscais | MDF-e |
| [![Prévia do DACCe](assets/screenshots/dacce.png){ width="120" }](dacce.md) | [**DACCe**](dacce.md) — Documento Auxiliar da Carta de Correção Eletrônica | CC-e |
| [![Prévia do DANFSe](assets/screenshots/danfse.png){ width="120" }](danfse.md) | [**DANFSe**](danfse.md) — Documento Auxiliar da Nota Fiscal de Serviços Eletrônica | NFS-e |

## Modos de Uso

### 1. Código Python

Para personalização completa e integração, use a biblioteca diretamente em Python. Configure margens, fontes, posição do recibo e muito mais para cada tipo de documento.

[Começar :material-arrow-right:](getting-started.md){ .md-button }

### 2. CLI (Linha de Comando)

Para geração rápida de PDF pelo terminal com um simples arquivo `config.yaml`.

[Documentação do CLI :material-arrow-right:](cli.md){ .md-button }

### 3. Teste Online

Faça upload do seu XML fiscal e obtenha o PDF instantaneamente — sem precisar instalar nada.

[Teste online :material-arrow-right:](https://brazilfiscalreport.streamlit.app){ .md-button }

## Dependências

- [FPDF2](https://github.com/py-pdf/fpdf2) - Biblioteca de criação de PDF para Python
- [phonenumbers](https://github.com/daviddrysdale/python-phonenumbers) - Formatação de números de telefone
- [python-barcode](https://github.com/WhyNotHugo/python-barcode) - Geração de código de barras
- [qrcode](https://github.com/lincolnloop/python-qrcode) - Geração de QR code (necessário para DACTE, DAMDFE e DANFSe)
