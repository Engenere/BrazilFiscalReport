DANFSE (Auxiliary Document of the Electronic Service Invoice) is a printed document used in Brazil to accompany the electronic service invoice (NFS-e). It serves as a simplified version of the NFS-e, providing key details about the service provided, such as issuer and taker information, tax details, and total amounts.

## Basic Usage

=== "Python"

    ```python
    from brazilfiscalreport.danfse import Danfse

    # Path to the XML file
    xml_file_path = 'nfse.xml'

    # Load XML Content
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instantiate the DANFSE object with the loaded XML content
    danfse = Danfse(xml=xml_content)
    danfse.output('output_danfse.pdf')
    ```

=== "CLI"

    ```bash
    bfrep danfse /path/to/nfse.xml
    ```

## Customizing DANFSE

This section describes how to customize the PDF output of the DANFSE using the `DanfseConfig` class. You can adjust various settings such as margins and fonts according to your needs.

### Margins

You can customize the margins of the PDF output by providing a `Margins` object.

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig, Margins

config = DanfseConfig(
    margins=Margins(top=5, right=5, bottom=5, left=5)
)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

### Cancellation / Replacement (Events)

In the national NFS-e model, an **authorized NFS-e XML is immutable**: it keeps
its original status (`cStat` 100/107) forever. Cancellation and replacement are
recorded in a **separate event document** (`<evento>`, e.g. `e101101 -
Cancelamento de NFS-e`) that references the invoice by its access key
(`chNFSe`).

There are two ways to render a cancelled/replaced DANFSE:

**1. Associating the event XML (recommended)**

Pass the event XML alongside the NFS-e. The library reads the event, matches it
to the invoice by the access key, and sets the status accordingly — applying the
**"CANCELADA"** or **"SUBSTITUÍDA"** watermark (NT 008, item 2.5):

```python
from brazilfiscalreport.danfse import Danfse

with open("nfse.xml", encoding="utf8") as f:
    xml_content = f.read()
with open("evento_cancelamento.xml", encoding="utf8") as f:
    event_content = f.read()

danfse = Danfse(xml=xml_content, event_xml=event_content)
danfse.output("output_danfse.pdf")
```

The event is only applied when its `chNFSe` matches the NFS-e access key, so an
unrelated event is safely ignored. Per the NT, an event XML cannot be used as
the main document — passing one as `xml` raises a `ValueError`.

The shortcut helper accepts the event too:

```python
from brazilfiscalreport.danfse import generate_danfse

generate_danfse(xml_content, "output_danfse.pdf", event_xml=event_content)
```

**2. Forcing the watermark via config**

When you already know the document is cancelled and don't have the event XML at
hand, force the watermark directly:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(watermark_cancelled=True)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

> **Note:** re-downloading the NFS-e via `GET /nfse/{chave}` does **not** return
> a "cancelled" XML — the invoice is immutable. To know the real status you must
> read the events (`GET /nfse/{chave}/eventos`) or receive them through DF-e
> distribution, and then associate the event as shown above.

### NT 008 / NT 009 Support

The DANFSE generator follows the **NT 008** layout and the **NT 009**
(LC 214/2025) tax rules:

**NT 009 (data / Tax Reform):**

- **IBS/CBS** block parsed from the official nested structure (NT-004):
  `infNFSe/IBSCBS/valores/{uf,mun,fed}` and
  `infNFSe/IBSCBS/totCIBS/{gIBS,gCBS}`, including totals and the
  *Valor Líquido + IBS/CBS*.
- **Simples Nacional** pulls IBS/CBS apuration from the `gTribSN` group.
- **Alphanumeric CNPJ** (Type C) handled as string.
- `finNFSe` and `cStat` translated by domain; `opSimpNac` includes the new
  *Optante Pendente* value.
- ISSQN deductions from `vAjusteBCISSQN + vCalcAjusteBCISSQN`.
- PIS/COFINS only printed for competence up to **Dec/2026**.
- Country in **ISO-2**; complementary info concatenated with `|`, truncated to
  1997 chars, always keeping the Lei 12.741/2012 line.

**NT 008 (visual):**

- Fonts: **Arial** (labels) / **Microsoft Sans Serif** (values), black (K100).
- 5% gray shading on header, block titles, *Emitente* and
  *Valor Líquido + IBS/CBS*.
- QR Code fixed at **1.52 × 1.52 cm**.
- Cancellation/replacement watermark: diagonal, Arial, ≥ 50pt, gray **K35**.
- Homologation notice **"NFS-e SEM VALIDADE JURÍDICA"** (red) in the header.
- Blocks: Prestador, Tomador, **Destinatário**, **Intermediário**, with the
  exact suppression phrases from the NT when a block is absent.
- Page border 1pt / dividers 0.5pt.

### Receipt (Canhoto)

To display the optional receipt block (Canhoto) at the bottom:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(show_receipt=True)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

### Custom Fonts

NT 008 requires specific fonts (Arial for labels, Microsoft Sans Serif for values). You can provide the path to the MS Sans Serif TTF file if it's not installed in the system:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(
    custom_font_path='/path/to/micross.ttf'
)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```
