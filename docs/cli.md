Generate DANFE, DACCe, DACTE, DAMDFE, and DANFSE documents directly from the terminal.
The PDF is saved in the current working directory using the same base name as the
XML file (e.g., `nfe.xml` → `nfe.pdf`), and you can create a `config.yaml` file
with issuer details and other configurations.

## Installation

The CLI requires additional dependencies. Install them with:

```bash
pip install 'brazilfiscalreport[cli]'
```

## Version

Use the `--version` or `-v` option to check the installed version:

```bash
bfrep --version
```

## Commands

### [DANFE](danfe.md)

```bash
bfrep danfe /path/to/nfe.xml
```

### [DACCe](dacce.md)

```bash
bfrep dacce /path/to/cce.xml
```

### [DACTE](dacte.md)

```bash
bfrep dacte /path/to/cte.xml
```

### [DAMDFE](damdfe.md)

```bash
bfrep damdfe /path/to/mdfe.xml
```

### [DANFSE](danfse.md)

```bash
bfrep danfse /path/to/nfse.xml
```

## Configuration File ⚙️

Create a `config.yaml` file in the directory where you run the command. This file allows you to configure issuer details, logo, and margins.

#### Example of `config.yaml`

```yaml
ISSUER:
  nome: "EMPRESA LTDA"
  end: "AV. TEST, 100"
  bairro: "CENTRO"
  cep: "01010-000"
  cidade: "SÃO PAULO"
  uf: "SP"
  fone: "(11) 1234-5678"

LOGO: "/path/to/logo.jpg"
TOP_MARGIN: 5.0
RIGHT_MARGIN: 5.0
BOTTOM_MARGIN: 5.0
LEFT_MARGIN: 5.0
```

Each setting applies to a different set of commands:

| Setting | Applies to |
|---------|------------|
| `ISSUER` | `dacce` only |
| `LOGO` | `danfe`, `dacte`, `damdfe` |
| `TOP/RIGHT/BOTTOM/LEFT_MARGIN` | `danfe`, `dacte`, `damdfe`, `danfse` |

If no `config.yaml` is found, default values are used. If the `LOGO` path does not exist, it is ignored with a console warning and the document is generated without a logo.

!!! warning
    For `dacce`, configuring the `ISSUER` section is effectively required — without a `config.yaml`, placeholder issuer data ("EMPRESA LTDA" / "AV. TEST, 100") is printed on the PDF.
