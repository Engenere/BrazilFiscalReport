DANFCe (Auxiliary Document of the Electronic Consumer Invoice) is the receipt printed for the NFC-e (NF-e model 65), the invoice issued in over-the-counter retail sales. It is laid out for non-fiscal thermal printers, following the *Manual de Especificações Técnicas do DANFE NFC-e / QR Code*.

## Basic Usage

=== "Python"

    ```python
    from brazilfiscalreport.danfce import Danfce

    # Path to the XML file
    xml_file_path = 'nfce.xml'

    # Load XML Content
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instantiate the DANFCe object with the loaded XML content
    danfce = Danfce(xml=xml_content)
    danfce.output('output_danfce.pdf')
    ```

=== "CLI"

    ```bash
    bfrep danfce /path/to/nfce.xml
    ```

The QR Code requires the `qrcode` package, installed with the extra:

```bash
pip install 'brazilfiscalreport[danfce]'
```

## Customizing DANFCe

This section describes how to customize the PDF output of the DANFCe using the `DanfceConfig` class.

### Paper size

A thermal roll is continuous, so by default the DANFCe is **a single page as tall as its content** — there is no "page 2 of 2" on a receipt.

The default roll is 80 mm wide. For 58 mm printers, set `paper_width`; the item columns are measured from their contents, so they adapt to the narrower roll:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig

config = DanfceConfig(paper_width=58)

danfce = Danfce(xml=xml_content, config=config)
danfce.output('output_danfce.pdf')
```

Setting `paper_height` opts out and breaks the receipt into pages of that height instead:

```python
config = DanfceConfig(paper_height=300)
```

This also happens automatically when the content would exceed the PDF page limit of 200 inches (5080 mm) — an NFC-e accepts up to 990 items, which is several metres of roll.

### Margins

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig, Margins

config = DanfceConfig(
    margins=Margins(top=2, right=2, bottom=2, left=2)
)

danfce = Danfce(xml=xml_content, config=config)
```

### Font

Times is used by default. Helvetica and Courier are also available:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig, FontType

config = DanfceConfig(font_type=FontType.HELVETICA)
```

### Logo

The issuer logo is centred at the top of the receipt, scaled to fit a box of 14 mm in height by half the roll width:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig

config = DanfceConfig(logo='logo.jpg')
```

### Cancelled watermark

```python
config = DanfceConfig(watermark_cancelled=True)
```

### Taxpayer message line breaks

Issuers usually pack `infAdic/infCpl` into a single line separated by `;` or `|`. Tell the DANFCe which character that is and it becomes a line break:

```python
config = DanfceConfig(line_break_char=';')
```

### Decimal precision

Prices and quantities are printed with 2 decimal places by default. Retail quantities sold by weight usually need more:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig, DecimalConfig

config = DanfceConfig(
    decimal_config=DecimalConfig(price_precision=2, quantity_precision=3)
)
```

## Layout notes

- The title is followed by the mandatory "Não permite aproveitamento de crédito de ICMS" notice.
- `tpAmb=2` prints "EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL", a `tpEmis` other than `1` prints "EMITIDA EM CONTINGÊNCIA", and a document with no `protNFe` prints "Pendente de autorização" — in place of the authorization protocol as well.
- The totals block closes arithmetically: `VALOR TOTAL - DESCONTO + ACRÉSCIMO = VALOR A PAGAR`. "ACRÉSCIMO" sums the components that add to `vNF` (`vST`, `vFCPST`, `vFrete`, `vSeg`, `vOutro`, `vII`, `vIPI`, `vIPIDevol`) and "DESCONTO" the ones that subtract (`vDesc`, `vICMSDeson`). Both lines are omitted when zero.
- The approximate taxes (Lei nº 12.741/2012) come from `ICMSTot/vTotTrib`, falling back to the sum of `det/imposto/vTotTrib` when the total is absent. When neither is informed the line prints `-----`, not `0,00`.
- The QR Code takes 70% of the roll width, so its modules stay large enough to scan on thermal paper.
- The consumer is identified by `CPF`, `CNPJ` or `idEstrangeiro`; without any of them the document prints "CONSUMIDOR NÃO IDENTIFICADO".
- `infAdic/infCpl` is printed as the taxpayer's message, between the taxes line and the access key.
- In the paginated fallback, the column header is repeated whenever the item list spills over a page.
