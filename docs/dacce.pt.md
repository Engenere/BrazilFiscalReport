DACCe (Documento Auxiliar da Carta de Correção Eletrônica) é uma representação impressa da CC-e (Carta de Correção Eletrônica) usada no Brasil. Fornece detalhes sobre correções feitas em uma NF-e (Nota Fiscal Eletrônica) emitida anteriormente, incluindo o texto de correção, a chave da nota referenciada e informações do protocolo.

![Exemplo de DACCe gerado a partir do XML de CC-e](assets/screenshots/dacce.png){ width="480" }

## Uso Básico

=== "Python"

    ```python
    from brazilfiscalreport.dacce import DaCCe

    # Caminho para o arquivo XML
    xml_file_path = 'cce.xml'

    # Carregar conteúdo do XML
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instanciar o objeto PDF da CC-e com o conteúdo XML carregado
    cce = DaCCe(xml=xml_content)

    # Salvar o PDF gerado em um arquivo
    cce.output('cce.pdf')
    ```

=== "CLI"

    ```bash
    bfrep dacce /path/to/cce.xml
    ```

    !!! note
        O comando `dacce` lê os dados do emitente da seção `ISSUER` de um `config.yaml` no diretório de trabalho — veja a [documentação do CLI](cli.md). Sem ele, dados fictícios de emitente são impressos no PDF. Adicionar logo via CLI não é suportado para o DACCe; use a API Python.

## Personalizando o DACCe 🎨

A classe `DaCCe` aceita os seguintes parâmetros:

### Parâmetros

---

**xml**

- **Tipo**: `str`
- **Descrição**: O conteúdo XML do evento CC-e.
- **Obrigatório**: Sim.

---

**emitente**

- **Tipo**: `dict` ou `None`
- **Descrição**: Um dicionário contendo as informações do emitente. Quando fornecido, os dados do emitente são exibidos no cabeçalho do DACCe. Todas as seis chaves são obrigatórias quando o dicionário é informado; chaves ausentes geram `KeyError`.
- **Chaves**: `nome`, `end`, `bairro`, `cidade`, `uf`, `fone`
- **Exemplo**:
    ```python
    emitente = {
        "nome": "EMPRESA LTDA",
        "end": "AV. TEST, 100",
        "bairro": "CENTRO",
        "cidade": "SÃO PAULO",
        "uf": "SP",
        "fone": "(11) 1234-5678",
    }
    ```
- **Padrão**: `None` (nenhuma informação do emitente exibida).

---

**image**

- **Tipo**: `str`, `BytesIO`, `bytes` ou `None`
- **Descrição**: Caminho para um arquivo de imagem do logo ou dados binários da imagem a ser exibida no cabeçalho junto com as informações do emitente. O valor é repassado diretamente ao [fpdf2](https://github.com/py-pdf/fpdf2), então URLs e instâncias de `PIL.Image.Image` também são aceitos.
- **Exemplo**:
    ```python
    image = "path/to/logo.jpg"
    ```
- **Padrão**: `None` (sem logo).

---

### Exemplo de Uso com Personalização

```python
from brazilfiscalreport.dacce import DaCCe

# Caminho para o arquivo XML
xml_file_path = 'cce.xml'

# Carregar conteúdo do XML
with open(xml_file_path, "r", encoding="utf8") as file:
    xml_content = file.read()

# Informações do emitente
emitente = {
    "nome": "EMPRESA LTDA",
    "end": "AV. TEST, 100",
    "bairro": "CENTRO",
    "cidade": "SÃO PAULO",
    "uf": "SP",
    "fone": "(11) 1234-5678",
}

# Instanciar com emitente e logo
cce = DaCCe(xml=xml_content, emitente=emitente, image="path/to/logo.png")

# Salvar o PDF gerado em um arquivo
cce.output('cce.pdf')
```
