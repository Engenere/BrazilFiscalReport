DANFSe (Auxiliary Document of the Electronic Service Invoice — "Documento Auxiliar da NFS-e") is a printed document used in Brazil to accompany the electronic service invoice (NFS-e). It serves as a simplified version of the NFS-e, providing key details about the service provided, such as issuer and taker information, tax details, and total amounts. The generated PDF follows the layout of the Brazilian National NFS-e System and includes a QR code for authenticity verification at the national portal.

![Example of a DANFSe generated from an NFS-e XML](assets/screenshots/danfse.png){ width="480" }

!!! note "Supported XML layout"
    The accepted XML is the NFS-e **National Standard** (Sistema Nacional NFS-e, namespace `http://www.sped.fazenda.gov.br/nfse`). Municipal ABRASF layouts are not supported.

## Installation

The DANFSe requires the `qrcode` optional dependency:

```bash
pip install 'brazilfiscalreport[danfse]'
```

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

## Customizing DANFSe 🎨

This section describes how to customize the PDF output of the DANFSe using the `DanfseConfig` class.

### Configuration Options ⚙️

---

**Margins**

- **Type**: `Margins`
- **Fields**: `top`, `right`, `bottom`, `left` (all of type `Number`)
- **Description**: Sets the page margins for the PDF document, in millimeters.
- **Example**:
    ```python
    config.margins = Margins(top=10, right=10, bottom=10, left=10)
    ```
- **Default**: top, right, bottom, and left are set to 5 mm.

---

**Font Type**

- **Type**: `FontType` (Enum)
- **Values**: `COURIER`, `TIMES`
- **Description**: Font style used throughout the PDF document.
- **Example**:
    ```python
    config.font_type = FontType.COURIER
    ```
- **Default**: `TIMES`

---

**Decimal Configuration**

- **Type**: `DecimalConfig`
- **Fields**: `price_precision`, `quantity_precision` (both `int`; only `price_precision` affects the DANFSe)
- **Description**: Defines the number of decimal places used for monetary values. With the default of `4`, amounts are printed like "R$ 1.000,0000" — set it to `2` for standard monetary display.
- **Example**:
    ```python
    config.decimal_config = DecimalConfig(price_precision=2)
    ```
- **Default**: `4`

---

**Watermark Cancelled**

- **Type**: `bool`
- **Description**: When set to `True`, displays a "CANCELADA" watermark on the DANFSe for cancelled documents. If the XML belongs to the homologation environment, the text becomes "CANCELADA - SEM VALOR FISCAL".
- **Example**:
    ```python
    config.watermark_cancelled = True
    ```
- **Default**: `False`

!!! note
    Independently of this setting, a "SEM VALOR FISCAL" watermark is drawn automatically whenever the XML was issued in the homologation environment (`tpAmb` = 2).

---

### Usage Example with Customization

```python
from brazilfiscalreport.danfse import (
    Danfse,
    DanfseConfig,
    DecimalConfig,
    FontType,
    Margins,
)

# Path to the XML file
xml_file_path = 'nfse.xml'

# Load XML Content
with open(xml_file_path, "r", encoding="utf8") as file:
    xml_content = file.read()

# Create a configuration instance
config = DanfseConfig(
    margins=Margins(top=10, right=10, bottom=10, left=10),
    font_type=FontType.TIMES,
    decimal_config=DecimalConfig(price_precision=2),
)

# Use this config when creating a Danfse instance
danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```
