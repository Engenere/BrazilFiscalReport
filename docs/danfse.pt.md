O DANFSE (Documento Auxiliar da Nota Fiscal de Serviços Eletrônica) é um documento impresso usado no Brasil para acompanhar a nota fiscal de serviços eletrônica (NFS-e). Ele serve como uma versão simplificada da NFS-e, fornecendo os principais detalhes sobre o serviço prestado, como informações do prestador e do tomador, dados de tributos e valores totais.

## Uso Básico

=== "Python"

    ```python
    from brazilfiscalreport.danfse import Danfse

    # Caminho para o arquivo XML
    xml_file_path = 'nfse.xml'

    # Carregar conteúdo do XML
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instanciar o objeto DANFSE com o conteúdo XML carregado
    danfse = Danfse(xml=xml_content)
    danfse.output('output_danfse.pdf')
    ```

=== "CLI"

    ```bash
    bfrep danfse /path/to/nfse.xml
    ```

## Personalizando o DANFSE

Esta seção descreve como personalizar a saída PDF do DANFSE usando a classe `DanfseConfig`. Você pode ajustar diversas configurações como margens e fontes de acordo com suas necessidades.

### Margens

Você pode personalizar as margens da saída PDF fornecendo um objeto `Margins`.

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig, Margins

config = DanfseConfig(
    margins=Margins(top=5, right=5, bottom=5, left=5)
)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

### Cancelamento / Substituição (Eventos)

No modelo nacional da NFS-e, um **XML de NFS-e autorizado é imutável**: ele mantém sua situação original (`cStat` 100/107) para sempre. Cancelamento e substituição são registrados em um **documento de evento separado** (`<evento>`, por exemplo `e101101 - Cancelamento de NFS-e`) que referencia a nota pela chave de acesso (`chNFSe`).

Há duas formas de gerar um DANFSE cancelado/substituído:

**1. Associando o XML do evento (recomendado)**

Passe o XML do evento junto com a NFS-e. A biblioteca lê o evento, associa-o à nota pela chave de acesso e define a situação correspondente — aplicando a marca d'água **"CANCELADA"** ou **"SUBSTITUÍDA"** (NT 008, item 2.5):

```python
from brazilfiscalreport.danfse import Danfse

with open("nfse.xml", encoding="utf8") as f:
    xml_content = f.read()
with open("evento_cancelamento.xml", encoding="utf8") as f:
    event_content = f.read()

danfse = Danfse(xml=xml_content, event_xml=event_content)
danfse.output("output_danfse.pdf")
```

O evento só é aplicado quando seu `chNFSe` corresponde à chave de acesso da NFS-e, de modo que um evento não relacionado é ignorado com segurança. Conforme a NT, um XML de evento não pode ser usado como documento principal — passar um como `xml` levanta um `ValueError`.

A função auxiliar também aceita o evento:

```python
from brazilfiscalreport.danfse import generate_danfse

generate_danfse(xml_content, "output_danfse.pdf", event_xml=event_content)
```

**2. Forçando a marca d'água via configuração**

Quando você já sabe que o documento está cancelado e não tem o XML do evento em mãos, force a marca d'água diretamente:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(watermark_cancelled=True)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

> **Nota:** baixar novamente a NFS-e via `GET /nfse/{chave}` **não** retorna um XML "cancelado" — a nota é imutável. Para saber a situação real é preciso ler os eventos (`GET /nfse/{chave}/eventos`) ou recebê-los pela distribuição de DF-e, e então associar o evento conforme mostrado acima.

### Suporte às NT 008 / NT 009

O gerador do DANFSE segue o leiaute da **NT 008** e as regras tributárias da **NT 009** (LC 214/2025):

**NT 009 (dados / Reforma Tributária):**

- Bloco **IBS/CBS** lido a partir da estrutura oficial aninhada (NT-004): `infNFSe/IBSCBS/valores/{uf,mun,fed}` e `infNFSe/IBSCBS/totCIBS/{gIBS,gCBS}`, incluindo totais e o *Valor Líquido + IBS/CBS*.
- **Simples Nacional** puxa a apuração de IBS/CBS do grupo `gTribSN`.
- **CNPJ alfanumérico** (Tipo C) tratado como string.
- `finNFSe` e `cStat` traduzidos por domínio; `opSimpNac` inclui o novo valor *Optante Pendente*.
- Deduções do ISSQN a partir de `vAjusteBCISSQN + vCalcAjusteBCISSQN`.
- PIS/COFINS impressos apenas para competência até **dez/2026**.
- País em **ISO-2**; informações complementares concatenadas com `|`, truncadas em 1997 caracteres, sempre preservando a linha da Lei 12.741/2012.

**NT 008 (visual):**

- Fontes: **Arial** (rótulos) / **Microsoft Sans Serif** (valores), em preto (K100).
- Sombreamento cinza 5% no cabeçalho, títulos de bloco, *Emitente* e *Valor Líquido + IBS/CBS*.
- QR Code fixo em **1,52 × 1,52 cm**.
- Marca d'água de cancelamento/substituição: diagonal, Arial, ≥ 50pt, cinza **K35**.
- Aviso de homologação **"NFS-e SEM VALIDADE JURÍDICA"** (vermelho) no cabeçalho.
- Blocos: Prestador, Tomador, **Destinatário**, **Intermediário**, com as frases exatas de supressão da NT quando um bloco está ausente.
- Borda da página 1pt / linhas divisórias 0,5pt.

### Recibo (Canhoto)

Para exibir o bloco opcional de recibo (Canhoto) na parte inferior:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(show_receipt=True)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```

### Fontes Personalizadas

A NT 008 exige fontes específicas (Arial para rótulos, Microsoft Sans Serif para os valores). Você pode fornecer o caminho do arquivo TTF da MS Sans Serif caso ela não esteja instalada no sistema:

```python
from brazilfiscalreport.danfse import Danfse, DanfseConfig

config = DanfseConfig(
    custom_font_path='/path/to/micross.ttf'
)

danfse = Danfse(xml=xml_content, config=config)
danfse.output('output_danfse.pdf')
```
