DANFE (Documento Auxiliar da Nota Fiscal Eletrônica) é uma representação impressa da NF-e (Nota Fiscal Eletrônica) usada no Brasil. Contém os principais detalhes da transação, como vendedor, comprador, produtos e impostos.

![Exemplo de DANFE gerado a partir do XML de NF-e](assets/screenshots/danfe.png){ width="480" }

## Uso Básico

=== "Python"

    ```python
    from brazilfiscalreport.danfe import Danfe

    # Caminho para o arquivo XML
    xml_file_path = 'nfe.xml'

    # Carregar conteúdo do XML
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instanciar o objeto DANFE com o conteúdo XML carregado
    danfe = Danfe(xml=xml_content)
    danfe.output('output_danfe.pdf')
    ```

=== "CLI"

    ```bash
    bfrep danfe /path/to/nfe.xml
    ```

## Personalizando o DANFE 🎨

Esta seção descreve como personalizar a saída PDF do DANFE usando a classe `DanfeConfig`. Você pode ajustar diversas configurações como margens, fontes e marcas d'água de acordo com suas necessidades.

### Opções de Configuração ⚙️

Aqui está uma descrição de todas as opções de configuração disponíveis em `DanfeConfig`:

---

**Logo**

- **Tipo**: `str`, `BytesIO` ou `bytes`
- **Descrição**: Caminho para o arquivo de logo ou dados binários da imagem a ser incluída no PDF. Você pode usar uma string com o caminho do arquivo ou passar os dados da imagem diretamente.
- **Exemplo**:
    ```python
    config.logo = "path/to/logo.jpg"  # Usando caminho do arquivo
    ```
- **Padrão**: Sem logo.

---

**Margens**

- **Tipo**: `Margins`
- **Campos**: `top`, `right`, `bottom`, `left` (todos do tipo `Number`)
- **Descrição**: Define as margens da página do documento PDF, em milímetros.
- **Exemplo**:
    ```python
    config.margins = Margins(top=5, right=5, bottom=5, left=5)
    ```
- **Padrão**: top, right, bottom e left definidos como 5 mm.

---

**Tipo de Fonte**

- **Tipo**: `FontType` (Enum)
- **Valores**: `COURIER`, `TIMES`
- **Descrição**: Estilo de fonte usado em todo o documento PDF.
- **Exemplo**:
    ```python
    config.font_type = FontType.COURIER
    ```
- **Padrão**: `TIMES`

---

**Tamanho da Fonte**

- **Tipo**: `FontSize` (Enum)
- **Valores**: `BIG`, `SMALL`
- **Descrição**: Tamanho da fonte usado em todo o documento PDF. Os valores são multiplicadores aplicados sobre os tamanhos base (`SMALL` = 1.0, `BIG` = 1.35).
- **Exemplo**:
    ```python
    config.font_size = FontSize.BIG
    ```
- **Padrão**: `SMALL`

!!! note
    `FontSize.BIG` só tem efeito com `FontType.TIMES`; com `COURIER` o tamanho `SMALL` é sempre usado.

---

**Posição do Recibo**

- **Tipo**: `ReceiptPosition` (Enum)
- **Valores**: `TOP`, `BOTTOM`, `LEFT`
- **Descrição**: Posição da seção de recibo no DANFE.
- **Exemplo**:
    ```python
    config.receipt_pos = ReceiptPosition.BOTTOM
    ```
- **Padrão**: `TOP` quando retrato, `LEFT` quando orientação paisagem.

!!! note
    A orientação da página é determinada automaticamente pela tag `tpImp` do XML da NF-e (`1` = retrato, caso contrário paisagem) e não é configurável. Na orientação paisagem, a posição do recibo é forçada para o lado esquerdo; personalização não é permitida.

---

**Configuração Decimal**

- **Tipo**: `DecimalConfig`
- **Campos**: `price_precision`, `quantity_precision` (ambos `int`)
- **Descrição**: Define o número de casas decimais para preços e quantidades.
- **Exemplo**:
    ```python
    config.decimal_config = DecimalConfig(price_precision=2, quantity_precision=2)
    ```
- **Padrão**: `4` para `price_precision` e `quantity_precision`.

---

**Configuração de Impostos**

- **Tipo**: `TaxConfiguration` (Enum)
- **Valores**: `STANDARD_ICMS_IPI`, `ICMS_ST`, `WITHOUT_IPI`
- **Descrição**: Especifica quais campos de impostos exibir.
- **Exemplo**:
    ```python
    config.tax_configuration = TaxConfiguration.WITHOUT_IPI
    ```
- **Padrão**: `STANDARD_ICMS_IPI`

!!! warning
    Este recurso ainda não foi implementado; defini-lo atualmente não tem efeito na saída.

---

**Exibição da Fatura**

- **Tipo**: `InvoiceDisplay` (Enum)
- **Valores**: `DUPLICATES_ONLY`, `FULL_DETAILS`
- **Descrição**: Controla o nível de detalhe na seção de fatura do DANFE.
- **Exemplo**:
    ```python
    config.invoice_display = InvoiceDisplay.FULL_DETAILS
    ```
- **Padrão**: `FULL_DETAILS`

---

**Exibir PIS COFINS**

- **Tipo**: `bool`
- **Valores**: `True`, `False`
- **Descrição**: Define se os impostos PIS e COFINS devem ser exibidos nos totais do DANFE.
- **Exemplo**:
    ```python
    config.display_pis_cofins = True
    ```
- **Padrão**: `False`

---

**Quebra de linha nas informações complementares**

- **Tipo**: `bool`
- **Valores**: `True`, `False`
- **Descrição**: Quebra a linha em cada `";"` encontrado nas informações complementares (`infCpl`) do DANFE.
- **Exemplo**:
    ```python
    config.infcpl_semicolon_newline = True
    ```
- **Padrão**: `False`

---

**Configuração da Descrição do Produto**

- **Tipo**: `ProductDescriptionConfig`
- **Campos**: `display_branch` (`bool`), `display_anp` (`bool`), `display_anvisa` (`bool`), `branch_info_prefix` (`str`), `display_additional_info` (`bool`)
- **Descrição**: Controla quais informações adicionais são exibidas na coluna de descrição do produto do DANFE.
- **Exemplo**:
    ```python
    config.product_description_config = ProductDescriptionConfig(
        display_branch=True,
        branch_info_prefix="=>",
        display_additional_info=True,
        display_anp=True,
        display_anvisa=True,
    )
    ```
- **Padrão**:
    ```python
    ProductDescriptionConfig(
        display_branch=False,
        display_anp=False,
        display_anvisa=False,
        branch_info_prefix="",
        display_additional_info=True,
    )
    ```

---

**Marca d'água Cancelada**

- **Tipo**: `bool`
- **Descrição**: Quando definido como `True`, exibe uma marca d'água "CANCELADA" no DANFE para notas fiscais canceladas. Se o XML for do ambiente de homologação, o texto passa a ser "CANCELADA - SEM VALOR FISCAL".
- **Exemplo**:
    ```python
    config.watermark_cancelled = True
    ```
- **Padrão**: `False`

!!! note
    Independentemente desta configuração, uma marca d'água "SEM VALOR FISCAL" é desenhada automaticamente sempre que o XML não tem protocolo de autorização (`protNFe`) ou foi emitido em ambiente de homologação (`tpAmb` = 2). Quando `watermark_cancelled=True`, a marca de cancelamento tem precedência.

---

**Carimbo de Rodapé (Footer Stamp)**

- **Tipo**: `FooterStamp`
- **Campos**:
    - `logo` (`Optional[Union[str, BytesIO, bytes]]`): imagem do logo; padrão `None`.
    - `text` (`str`): texto exibido à esquerda do logo; padrão `""`.
    - `height` (`Number`): área vertical, em mm, reservada para o carimbo; padrão `5`.
    - `logo_max_width` (`Number`): largura, em mm, da caixa usada para encaixar o logo preservando a proporção; padrão `20`.
    - `spacing` (`Number`): espaçamento vertical, em mm, entre a área de conteúdo e o carimbo; padrão `1`.
- **Descrição**: Desenha um carimbo personalizado (logo + texto) em todas as páginas da nota, alinhado à direita na margem da página. A área do carimbo é reservada automaticamente dentro da margem inferior — não é necessário aumentar `Margins.bottom` para abrir espaço.
- **Exemplo**:
    ```python
    config.footer_stamp = FooterStamp(
        logo="path/to/logo.png",
        text="Powered by",
    )
    ```
- **Padrão**: `FooterStamp()` (vazio — nada é desenhado).

---

### Exemplo de Uso com Personalização

Veja como configurar um objeto `DanfeConfig` com um conjunto completo de personalizações:

```python
from brazilfiscalreport.danfe import (
    Danfe,
    DanfeConfig,
    DecimalConfig,
    FontType,
    FooterStamp,
    InvoiceDisplay,
    Margins,
    ProductDescriptionConfig,
    ReceiptPosition,
)

# Caminho para o arquivo XML
xml_file_path = 'nfe.xml'

# Carregar conteúdo do XML
with open(xml_file_path, "r", encoding="utf8") as file:
    xml_content = file.read()

# Criar uma instância de configuração
config = DanfeConfig(
    logo='path/to/logo.png',
    margins=Margins(top=10, right=10, bottom=10, left=10),
    receipt_pos=ReceiptPosition.BOTTOM,
    decimal_config=DecimalConfig(price_precision=2, quantity_precision=2),
    invoice_display=InvoiceDisplay.FULL_DETAILS,
    font_type=FontType.TIMES,
    display_pis_cofins=True,
    product_description_config=ProductDescriptionConfig(
        display_branch=True,
        display_additional_info=True,
    ),
    footer_stamp=FooterStamp(
        logo='path/to/footer_logo.png',
        text='Powered by',
    ),
)

# Usar esta configuração ao criar uma instância do Danfe
danfe = Danfe(xml_content, config=config)
danfe.output('output_danfe.pdf')
```
