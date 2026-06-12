DAMDFE (Documento Auxiliar do Manifesto Eletrônico de Documentos Fiscais) é uma representação impressa do MDF-e (Manifesto Eletrônico de Documentos Fiscais) usado no Brasil. Ele consolida informações sobre o transporte de mercadorias, vinculando múltiplos CT-e ou NF-e a uma única operação de transporte, e é obrigatório para acompanhar a carga durante o trânsito. Os modais rodoviário, aéreo, aquaviário e ferroviário são suportados, incluindo emissão em contingência.

![Exemplo de DAMDFE gerado a partir do XML de MDF-e](assets/screenshots/damdfe.png){ width="480" }

## Uso Básico

=== "Python"

    ```python
    from brazilfiscalreport.damdfe import Damdfe

    # Caminho para o arquivo XML
    xml_file_path = 'mdfe.xml'

    # Carregar conteúdo do XML
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instanciar o objeto DAMDFE com o conteúdo XML carregado
    damdfe = Damdfe(xml=xml_content)

    # Salvar o PDF gerado em um arquivo
    damdfe.output('damdfe.pdf')
    ```

=== "CLI"

    ```bash
    bfrep damdfe /path/to/mdfe.xml
    ```

## Personalizando o DAMDFE 🎨

Esta seção descreve como personalizar a saída PDF do DAMDFE usando a classe `DamdfeConfig`. Você pode ajustar diversas configurações como margens e fontes de acordo com suas necessidades.

### Opções de Configuração ⚙️

Aqui está uma descrição de todas as opções de configuração disponíveis em `DamdfeConfig`:

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
    config.margins = Margins(top=10, right=10, bottom=10, left=10)
    ```
- **Padrão**: top, right, bottom e left definidos como 5 mm.

!!! warning
    O leiaute do DAMDFE atualmente suporta apenas margens inteiras: esquerda entre 5 e 10 mm (valores fora da faixa geram erro em documentos do modal rodoviário) e direita entre 1 e 10 mm (valores fora da faixa geram erro em todos os documentos).

---

**Exibir Origem/Destino da Prestação**

- **Tipo**: `bool`
- **Descrição**: Quando definido como `True`, a seção "PERCURSO" também exibe a origem da prestação (município de carregamento, de `infMunCarrega`) e o destino da prestação (municípios de descarregamento, de `infMunDescarga`).
- **Exemplo**:
    ```python
    config.display_origem_destino_prestacao = True
    ```
- **Padrão**: `False`

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
    Esta opção ainda não foi implementada no DAMDFE: os valores são sempre formatados com 2 casas decimais. Defini-la atualmente não tem efeito na saída.

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

### Comportamentos Automáticos

Alguns elementos são desenhados automaticamente com base no conteúdo do XML, sem necessidade de configuração:

- Uma marca d'água "SEM VALOR FISCAL" é desenhada sempre que o XML não tem protocolo de autorização (`protMDFe`) ou foi emitido em ambiente de homologação (`tpAmb` = 2).
- Para emissão em contingência (`tpEmis`), uma marca d'água "EMISSÃO EM CONTINGÊNCIA" é desenhada e o quadro do protocolo exibe o prazo de 168 horas para autorização, calculado a partir da data de emissão.

!!! note
    Diferentemente do DANFE, DACTE e DANFSE, o DAMDFE ainda não oferece a opção `watermark_cancelled`.

---

### Exemplo de Uso com Personalização

Veja como configurar um objeto `DamdfeConfig` com um conjunto completo de personalizações:

```python
from brazilfiscalreport.damdfe import (
    Damdfe,
    DamdfeConfig,
    FontType,
    Margins,
)

# Caminho para o arquivo XML
xml_file_path = 'mdfe.xml'

# Carregar conteúdo do XML
with open(xml_file_path, "r", encoding="utf8") as file:
    xml_content = file.read()

# Criar uma instância de configuração
config = DamdfeConfig(
    logo='path/to/logo.png',
    margins=Margins(top=10, right=10, bottom=10, left=10),
    font_type=FontType.TIMES,
    display_origem_destino_prestacao=True,
)

# Usar esta configuração ao criar uma instância do Damdfe
damdfe = Damdfe(xml_content, config=config)
damdfe.output('output_damdfe.pdf')
```
