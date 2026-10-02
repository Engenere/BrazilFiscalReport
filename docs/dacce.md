DACCe (Auxiliary Document of the Electronic Correction Letter) is a printed representation of the CC-e (Electronic Correction Letter) used in Brazil. It provides details about corrections made to a previously issued NF-e (Electronic Invoice), including the correction text, the referenced invoice key, and protocol information.

![Example of a DACCe generated from a CC-e XML](assets/screenshots/dacce.png){ width="480" }

## Basic Usage

=== "Python"

    ```python
    from brazilfiscalreport.dacce import DaCCe

    # Path to the XML file
    xml_file_path = 'cce.xml'

    # Load XML Content
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instantiate the CC-e PDF object with the loaded XML content
    cce = DaCCe(xml=xml_content)

    # Save the generated PDF to a file
    cce.output('cce.pdf')
    ```

=== "CLI"

    ```bash
    bfrep dacce /path/to/cce.xml
    ```

    !!! note
        The `dacce` command reads the issuer data from the `ISSUER` section of a `config.yaml` in the working directory — see the [CLI documentation](cli.md). Without it, placeholder issuer data is printed on the PDF. Adding a logo via CLI is not supported for DACCe; use the Python API.

## Output notes

- The recipient is printed as **CNPJ** (`CNPJDest`) or, for an individual, as **CPF** (`CPFDest`).
- Events registered in the homologation environment (`tpAmb` = 2) get a **SEM VALOR FISCAL** watermark, like the DANFE.
- Line breaks in the correction text are kept, including `\n` sent as a literal backslash and `n`.

## Customizing DACCe 🎨

The `DaCCe` class accepts the following parameters:

### Parameters

---

**xml**

- **Type**: `str`
- **Description**: The XML content of the CC-e event.
- **Required**: Yes.

---

**emitente**

- **Type**: `dict` or `None`
- **Description**: A dictionary containing the issuer (emitente) information. When provided, the issuer details are displayed in the header of the DACCe. All six keys are required when the dictionary is provided; missing keys raise a `KeyError`.
- **Keys**: `nome`, `end`, `bairro`, `cidade`, `uf`, `fone`. Optional: `cnpj` and `ie`, printed in an extra line of the header when present.
- **Example**:
    ```python
    emitente = {
        "nome": "EMPRESA LTDA",
        "end": "AV. TEST, 100",
        "bairro": "CENTRO",
        "cidade": "SÃO PAULO",
        "uf": "SP",
        "fone": "(11) 1234-5678",
        "cnpj": "01234567890123",  # optional
        "ie": "123456789012",  # optional
    }
    ```
- **Default**: `None` (no issuer info displayed).

---

**image**

- **Type**: `str`, `BytesIO`, `bytes`, or `None`
- **Description**: Path to a logo image file or binary image data to be displayed in the header alongside the issuer information. The value is passed directly to [fpdf2](https://github.com/py-pdf/fpdf2), so URLs and `PIL.Image.Image` instances are also accepted.
- **Example**:
    ```python
    image = "path/to/logo.jpg"
    ```
- **Default**: `None` (no logo).

---

### Usage Example with Customization

```python
from brazilfiscalreport.dacce import DaCCe

# Path to the XML file
xml_file_path = 'cce.xml'

# Load XML Content
with open(xml_file_path, "r", encoding="utf8") as file:
    xml_content = file.read()

# Issuer information
emitente = {
    "nome": "EMPRESA LTDA",
    "end": "AV. TEST, 100",
    "bairro": "CENTRO",
    "cidade": "SÃO PAULO",
    "uf": "SP",
    "fone": "(11) 1234-5678",
}

# Instantiate with issuer and logo
cce = DaCCe(xml=xml_content, emitente=emitente, image="path/to/logo.png")

# Save the generated PDF to a file
cce.output('cce.pdf')
```
