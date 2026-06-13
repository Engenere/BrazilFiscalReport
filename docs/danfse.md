DANFSe (Auxiliary Document of the Electronic Service Invoice) is a printed document used in Brazil to accompany the electronic service invoice (NFS-e). It serves as a simplified version of the NFS-e, providing key details about the service provided, such as issuer and taker information, tax details, and total amounts.

![Example of a DANFSe generated from an NFS-e XML](assets/screenshots/danfse.png){ width="480" }

The layout follows the **DANFSe v2.0** model defined by Technical Note **NT 008/2026 (SE/CGNFS-e)**, including the Recipient (Destinatário), IBS/CBS taxation and optional acknowledgment stub (canhoto) blocks introduced by the Brazilian consumption tax reform (RTC).

## Basic Usage

=== "Python"

    ```python
    from brazilfiscalreport.danfse import Danfse

    # Path to the XML file
    xml_file_path = 'nfse.xml'

    # Load XML Content
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instantiate the DANFSe object with the loaded XML content
    danfse = Danfse(xml=xml_content)
    danfse.output('output_danfse.pdf')
    ```

=== "CLI"

    ```bash
    bfrep danfse /path/to/nfse.xml
    ```

## Customizing DANFSe

This section describes how to customize the PDF output of the DANFSe using the `DanfseConfig` class. You can adjust various settings such as margins and fonts according to your needs.

### Margins

You can customize the margins of the PDF output by providing a `Margins` object. NT 008/2026 (item 2.2.2) requires margins between 1.5 mm and 2.0 mm; the default is 2 mm on all sides.

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig, Margins

config = DanfseConfig(
    margins=Margins(top=2, right=2, bottom=2, left=2)
)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

### Font

NT 008/2026 requires Arial for titles/labels and Microsoft Sans Serif for field contents. The library uses **Helvetica** by default, the metric-equivalent PDF core font, so no TTF embedding is needed. Times and Courier remain available:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig, FontType

config = DanfseConfig(font_type=FontType.HELVETICA)  # default

danfse = Danfse(xml=xml_content, config=config)
```

### Decimal precision

Monetary amounts and tax rates are printed with 2 decimal places by default, matching the `1-15V2`/`1-2V2` field formats of the NT 008/2026 layout:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig, DecimalConfig

config = DanfseConfig(decimal_config=DecimalConfig(price_precision=2))
```

### Cancelled Watermark

To display a "CANCELADA" watermark on cancelled documents (NT 008/2026, item 2.5.1 — diagonal, regular style, gray K35):

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(watermark_cancelled=True)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

### Replaced Watermark

To display a "SUBSTITUÍDA" watermark on replaced documents (NT 008/2026, item 2.5.2). When both `watermark_cancelled` and `watermark_replaced` are enabled, "CANCELADA" takes precedence:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(watermark_replaced=True)
```

### Acknowledgment stub (canhoto)

The canhoto is an optional block at the bottom of the document (NT 008/2026, item 2.1.13 and Note 11) with fields for acknowledgment date, signature and the NFS-e number/access key. It is disabled by default:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(display_canhoto=True)
```

## Layout notes

- Blocks without data in the XML are replaced by the fixed single-line texts of NT 008/2026 Notes 2–4 (e.g. "TOMADOR/ADQUIRENTE DA OPERAÇÃO NÃO IDENTIFICADO NA NFS-e"), and the freed space flows into the "Informações Complementares" block (§2.3).
- When the `IBSCBS/dest` group is absent and the taker is present, the document prints "O DESTINATÁRIO É O PRÓPRIO TOMADOR/ADQUIRENTE DA OPERAÇÃO" (Note 3).
- When `tpAmb=2` (homologation), the header shows "NFS-e SEM VALIDADE JURÍDICA" in red, as required by §2.4.3.
- Municipality names for the provider/taker/recipient/intermediary addresses are resolved from the IBGE municipality table bundled with the package (`municipios_ibge.csv`).
- The "Totais Aproximados dos Tributos" (Lei nº 12.741/2012) are always printed inside "Informações Complementares" in the fixed format of Note 10.
