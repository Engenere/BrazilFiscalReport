# Começando

## Instalação

### Instalação básica

```bash
pip install brazilfiscalreport
```

Isso instala a biblioteca principal com suporte para **DANFE** e **DACCe**. Requer Python 3.8+.

### Dependências opcionais

Alguns tipos de documentos requerem pacotes adicionais:

=== "DACTE"

    ```bash
    pip install 'brazilfiscalreport[dacte]'
    ```

=== "DAMDFE"

    ```bash
    pip install 'brazilfiscalreport[damdfe]'
    ```

=== "DANFSe"

    ```bash
    pip install 'brazilfiscalreport[danfse]'
    ```

=== "CLI"

    ```bash
    pip install 'brazilfiscalreport[cli]'
    ```

=== "Todos os extras"

    ```bash
    pip install 'brazilfiscalreport[dacte,damdfe,danfse,cli]'
    ```

## Início Rápido

### Usando código Python

Gere um DANFE em PDF a partir de um arquivo XML de NF-e em poucas linhas:

```python
from brazilfiscalreport.danfe import Danfe

# Carregar o conteúdo do XML
with open("nfe.xml", "r", encoding="utf8") as file:
    xml_content = file.read()

# Gerar o PDF
danfe = Danfe(xml=xml_content)
danfe.output("danfe.pdf")
```

!!! tip "Sem um XML em mãos?"
    Pegue um exemplo em [tests/fixtures](https://github.com/Engenere/BrazilFiscalReport/tree/main/tests/fixtures) ou [teste a demo online](https://brazilfiscalreport.streamlit.app) com o seu próprio arquivo.

O mesmo padrão se aplica a todos os tipos de documentos:

=== "DANFE"

    ```python
    from brazilfiscalreport.danfe import Danfe

    danfe = Danfe(xml=xml_content)
    danfe.output("danfe.pdf")
    ```

=== "DACCe"

    ```python
    from brazilfiscalreport.dacce import DaCCe

    dacce = DaCCe(xml=xml_content)
    dacce.output("dacce.pdf")
    ```

=== "DACTE"

    ```python
    from brazilfiscalreport.dacte import Dacte

    dacte = Dacte(xml=xml_content)
    dacte.output("dacte.pdf")
    ```

=== "DAMDFE"

    ```python
    from brazilfiscalreport.damdfe import Damdfe

    damdfe = Damdfe(xml=xml_content)
    damdfe.output("damdfe.pdf")
    ```

=== "DANFSe"

    ```python
    from brazilfiscalreport.danfse import Danfse

    danfse = Danfse(xml=xml_content)
    danfse.output("danfse.pdf")
    ```

### Usando o CLI

Para geração rápida pelo terminal:

```bash
bfrep danfe /path/to/nfe.xml
bfrep dacce /path/to/cce.xml
bfrep dacte /path/to/cte.xml
bfrep damdfe /path/to/mdfe.xml
bfrep danfse /path/to/nfse.xml
```

Veja a [documentação do CLI](cli.md) para opções de configuração.

## Próximos passos

- Conheça as opções de personalização para cada tipo de documento: [DANFE](danfe.md), [DACTE](dacte.md), [DAMDFE](damdfe.md), [DACCe](dacce.md), [DANFSe](danfse.md)
- Configure o [CLI](cli.md) para geração em lote
