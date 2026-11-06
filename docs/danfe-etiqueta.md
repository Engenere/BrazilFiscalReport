The DANFE Simplificado – Etiqueta is a reduced DANFE printed on a label, used mainly to ship e-commerce orders. It follows Technical Note **NT 2020.004 v1.10** and item 3.12 of the *Manual de Especificações Técnicas do DANFE* (MOC 7.0, Anexo II). The NF-e is the same as for the regular DANFE, with `tpImp=3` (DANFE Simplificado).

![Example of a DANFE Simplificado – Etiqueta generated from an NF-e XML](assets/screenshots/danfe-etiqueta.png){ width="320" }

## Basic Usage

=== "Python"

    ```python
    from brazilfiscalreport.danfe import DanfeEtiqueta

    with open("nfe.xml", "r", encoding="utf8") as file:
        xml_content = file.read()

    etiqueta = DanfeEtiqueta(xml=xml_content)
    etiqueta.output("etiqueta.pdf")
    ```

=== "CLI"

    ```bash
    bfrep danfe-etiqueta /path/to/nfe.xml
    ```

## Customizing the label

The `DanfeEtiquetaConfig` class holds the options:

```python
from brazilfiscalreport.danfe import DanfeEtiqueta, DanfeEtiquetaConfig

config = DanfeEtiquetaConfig(
    paper_width=100,
    paper_height=150,
    display_items=True,
)
etiqueta = DanfeEtiqueta(xml=xml_content, config=config)
```

| Option | Default | Description |
|---|---|---|
| `paper_width`, `paper_height` | `100`, `150` | Label size in mm. The 10 x 15 cm thermal label is the usual shipping label; the NT only requires at least **55 mm** of width. |
| `margins` | `Margins(3, 3, 3, 3)` | Margins in mm. |
| `font_type` | `FontType.TIMES` | `TIMES` or `COURIER`. |
| `logo`, `logo_height` | `None`, `12` | Brand logo (path, bytes or `BytesIO`), printed centered between the header and the issuer data, `logo_height` mm tall, as in the marketplace shipping labels. |
| `display_total` | `True` | Prints the total value of the NF-e (`vNF`), optional since NT 2020.004 v1.10. |
| `display_delivery_address` | `True` | Prints the recipient address, or the `entrega` group address (and receiver) when the NF-e has it. |
| `display_items` | `False` | Lists the items (code, description and quantity). The items that don't fit are counted in a last line, "E MAIS N ITEM(NS) NÃO LISTADO(S)". |
| `watermark_cancelled` | `False` | Prints the "CANCELADA" watermark. |
| `epec_protocol` | `""` | Protocol of the EPEC event (number and date/time), printed while the NF-e issued in EPEC contingency has no authorization. It comes in the response to the event, not in the NF-e XML. |

## Layout notes

- The label prints the fields required by the NT: the description "DANFE Simplificado – Etiqueta", the access key with its barcode and the authorization protocol; the issuer name, UF, CNPJ and state registration (IE); the operation type (entrada/saída), number, series and issue date; and the recipient name, UF, CNPJ/CPF and IE, when there is one.
- The barcode sits at the top right corner. Its module is 0.25 mm, 2 dots of the 203 dpi thermal printers used for labels, so it is about 74 mm wide. On paper too narrow for that the module shrinks, and below the 6 cm of the MOC a warning is emitted: the barcode may not be read on a 203 dpi printer.
- With less than 70 mm of usable width (paper narrower than 76 mm), each field takes its own row.
- In homologation, or without the authorization protocol, the label prints the "SEM VALOR FISCAL" watermark. In EPEC contingency it also prints the start date and reason of the contingency (`dhCont` and `xJust`).
- The plain DANFE Simplificado (sales outside the establishment, with items) and the DANFE Simplificado Tipo 2 (`tpImp=6`) are different documents and are not covered here.
