O DANFCe (Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica) é o cupom impresso da NFC-e (NF-e modelo 65), emitida na venda presencial ao consumidor. O leiaute é pensado para impressoras térmicas não fiscais e segue o *Manual de Especificações Técnicas do DANFE NFC-e / QR Code*.

## Uso Básico

=== "Python"

    ```python
    from brazilfiscalreport.danfce import Danfce

    # Caminho do arquivo XML
    xml_file_path = 'nfce.xml'

    # Carrega o conteúdo do XML
    with open(xml_file_path, "r", encoding="utf8") as file:
        xml_content = file.read()

    # Instancia o objeto DANFCe com o XML carregado
    danfce = Danfce(xml=xml_content)
    danfce.output('output_danfce.pdf')
    ```

=== "CLI"

    ```bash
    bfrep danfce /caminho/para/nfce.xml
    ```

O QR Code depende do pacote `qrcode`, instalado pelo extra:

```bash
pip install 'brazilfiscalreport[danfce]'
```

## Personalizando o DANFCe

Esta seção descreve como personalizar a saída em PDF do DANFCe usando a classe `DanfceConfig`.

### Tamanho da bobina

A bobina térmica é contínua, então por padrão o DANFCe sai em **uma página só, com a altura do conteúdo** — não existe "página 2 de 2" num cupom.

A bobina padrão tem 80 mm. Para impressoras de 58 mm, ajuste `paper_width`; as colunas dos itens são medidas pelo conteúdo, então se acomodam à bobina menor:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig

config = DanfceConfig(paper_width=58)

danfce = Danfce(xml=xml_content, config=config)
danfce.output('output_danfce.pdf')
```

Informar `paper_height` abre mão disso e quebra o cupom em páginas dessa altura:

```python
config = DanfceConfig(paper_height=300)
```

Isso também acontece sozinho quando o conteúdo passaria do limite de página do PDF, de 200 polegadas (5080 mm) — uma NFC-e aceita até 990 itens, o que daria metros de bobina.

### Margens

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig, Margins

config = DanfceConfig(
    margins=Margins(top=2, right=2, bottom=2, left=2)
)

danfce = Danfce(xml=xml_content, config=config)
```

### Fonte

Times é a fonte padrão. Helvetica e Courier também estão disponíveis:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig, FontType

config = DanfceConfig(font_type=FontType.HELVETICA)
```

### Logo

A logo do emitente é centralizada no topo do cupom, encaixada numa caixa de 14 mm de altura por metade da largura da bobina:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig

config = DanfceConfig(logo='logo.jpg')
```

### Marca d'água de cancelada

```python
config = DanfceConfig(watermark_cancelled=True)
```

### Quebra de linha da mensagem do contribuinte

O emitente costuma mandar o `infAdic/infCpl` numa linha só, separada por `;` ou `|`. Informe qual é o caractere e ele vira quebra de linha:

```python
config = DanfceConfig(line_break_char=';')
```

### Precisão decimal

Valores e quantidades saem com 2 casas decimais por padrão. Produtos vendidos por peso costumam exigir mais:

```python
from brazilfiscalreport.danfce import Danfce, DanfceConfig, DecimalConfig

config = DanfceConfig(
    decimal_config=DecimalConfig(price_precision=2, quantity_precision=3)
)
```

## Notas sobre o leiaute

- Logo abaixo do título vem a ressalva obrigatória "Não permite aproveitamento de crédito de ICMS".
- `tpAmb=2` imprime "EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL", `tpEmis` diferente de `1` imprime "EMITIDA EM CONTINGÊNCIA", e documento sem `protNFe` imprime "Pendente de autorização" — inclusive no lugar do protocolo de autorização.
- O bloco de totais fecha aritmeticamente: `VALOR TOTAL - DESCONTO + ACRÉSCIMO = VALOR A PAGAR`. O "ACRÉSCIMO" soma os componentes que entram no `vNF` (`vST`, `vFCPST`, `vFrete`, `vSeg`, `vOutro`, `vII`, `vIPI`, `vIPIDevol`) e o "DESCONTO" os que abatem (`vDesc`, `vICMSDeson`). As duas linhas são omitidas quando zeradas.
- Os tributos aproximados (Lei nº 12.741/2012) vêm de `ICMSTot/vTotTrib`, com fallback para a soma de `det/imposto/vTotTrib` quando o total não vem informado. Quando nenhum dos dois vem, a linha imprime `-----`, não `0,00`.
- O QR Code ocupa 70% da largura da bobina, para que os módulos fiquem grandes o bastante para leitura em papel térmico.
- O consumidor é identificado por `CPF`, `CNPJ` ou `idEstrangeiro`; sem nenhum deles o documento imprime "CONSUMIDOR NÃO IDENTIFICADO".
- O `infAdic/infCpl` é impresso como mensagem de interesse do contribuinte, entre a linha de tributos e a chave de acesso.
- No fallback paginado, o cabeçalho de colunas é repetido sempre que a lista de itens passa para outra página.
