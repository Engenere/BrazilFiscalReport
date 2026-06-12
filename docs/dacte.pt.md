DACTE (Documento Auxiliar do Conhecimento de Transporte Eletrônico) é um documento impresso usado no Brasil para acompanhar o conhecimento de transporte eletrônico (CT-e). Ele serve como uma versão simplificada do CT-e, fornecendo os principais detalhes sobre o embarque, como informações da carga, remetente e destinatário, e dados da transportadora. Todos os modais de transporte são suportados — rodoviário, aéreo, aquaviário, ferroviário, dutoviário e multimodal.

![Exemplo de DACTE gerado a partir do XML de CT-e](assets/screenshots/dacte.png){ width="480" }

## Uso Básico

=== "Python"

    ```python
    from brazilfiscalreport.dacte import Dacte

    # Caminho para o arquivo XML
    xml_file_path = 'cte.xml'

    # Carregar conteúdo do XML
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instanciar o objeto DACTE com o conteúdo XML carregado
    dacte = Dacte(xml=xml_content)
    dacte.output('output_dacte.pdf')
    ```

=== "CLI"

    ```bash
    bfrep dacte /path/to/cte.xml
    ```

## Personalizando o DACTE 🎨

Esta seção descreve como personalizar a saída PDF do DACTE usando a classe `DacteConfig`. Você pode ajustar diversas configurações como margens, fontes e outras opções de acordo com suas necessidades.

### Opções de Configuração ⚙️

Aqui está uma descrição de todas as opções de configuração disponíveis em `DacteConfig`:

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

**Exibir IBS/CBS**

- **Tipo**: `bool`
- **Descrição**: Quando definido como `True`, adiciona a coluna "IBS E CBS" ao bloco de informações relativas ao imposto, exibindo alíquotas e valores do IBS estadual, IBS municipal e CBS extraídos do grupo `IBSCBS` do XML do CT-e (Reforma Tributária).
- **Exemplo**:
    ```python
    config.display_ibs_cbs = True
    ```
- **Padrão**: `False`

---

**Posição do Recibo**

- **Tipo**: `ReceiptPosition` (Enum)
- **Valores**: `TOP`, `BOTTOM`, `LEFT`
- **Exemplo**:
    ```python
    config.receipt_pos = ReceiptPosition.BOTTOM
    ```
- **Padrão**: `TOP`

!!! warning
    Esta opção ainda não foi implementada no DACTE: o recibo é sempre desenhado no topo, e o leiaute é determinado automaticamente pela orientação de impressão (`tpImp`) do XML do CT-e. Defini-la atualmente não tem efeito na saída.

---

**Configuração Decimal**

- **Tipo**: `DecimalConfig`
- **Campos**: `price_precision`, `quantity_precision` (ambos `int`)
- **Exemplo**:
    ```python
    config.decimal_config = DecimalConfig(price_precision=2, quantity_precision=2)
    ```
- **Padrão**: `4` para ambos os campos.

!!! warning
    Esta opção ainda não foi implementada no DACTE: os valores monetários são sempre formatados com 2 casas decimais. Defini-la atualmente não tem efeito na saída.

---

**Marca d'água Cancelada**

- **Tipo**: `bool`
- **Descrição**: Quando definido como `True`, exibe uma marca d'água "CANCELADA" no DACTE para documentos cancelados. Se o XML for do ambiente de homologação, o texto passa a ser "CANCELADA - SEM VALOR FISCAL".
- **Exemplo**:
    ```python
    config.watermark_cancelled = True
    ```
- **Padrão**: `False`

!!! note
    Independentemente desta configuração, uma marca d'água "SEM VALOR FISCAL" é desenhada automaticamente sempre que o XML não tem protocolo de autorização (`protCTe`) ou foi emitido em ambiente de homologação (`tpAmb` = 2). Quando `watermark_cancelled=True`, a marca de cancelamento tem precedência.

---

### Exemplo de Uso com Personalização

Veja como configurar um objeto `DacteConfig` com um conjunto completo de personalizações:

```python
from brazilfiscalreport.dacte import (
    Dacte,
    DacteConfig,
    FontType,
    Margins,
)

# Caminho para o arquivo XML
xml_file_path = 'cte.xml'

# Carregar conteúdo do XML
with open(xml_file_path, "r", encoding="utf8") as file:
    xml_content = file.read()

# Criar uma instância de configuração
config = DacteConfig(
    logo='path/to/logo.png',
    margins=Margins(top=10, right=10, bottom=10, left=10),
    font_type=FontType.TIMES,
    display_ibs_cbs=True,
)

# Usar esta configuração ao criar uma instância do Dacte
dacte = Dacte(xml_content, config=config)
dacte.output('output_dacte.pdf')
```
