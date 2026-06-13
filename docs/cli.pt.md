Gere documentos DANFE, DACCe, DACTE, DAMDFE e DANFSe diretamente pelo terminal.
O PDF é salvo no diretório de trabalho atual com o mesmo nome base do arquivo
XML (ex.: `nfe.xml` → `nfe.pdf`), e você pode criar um arquivo `config.yaml`
com detalhes do emitente e outras configurações.

## Instalação

O CLI requer dependências adicionais. Instale-as com:

```bash
pip install 'brazilfiscalreport[cli]'
```

## Versão

Use a opção `--version` ou `-v` para verificar a versão instalada:

```bash
bfrep --version
```

## Comandos

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

### [DANFSe](danfse.md)

```bash
bfrep danfse /path/to/nfse.xml
```

## Arquivo de Configuração ⚙️

Crie um arquivo `config.yaml` no diretório onde você executa o comando. Este arquivo permite configurar detalhes do emitente, logo e margens.

#### Exemplo de `config.yaml`

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

Cada configuração se aplica a um conjunto diferente de comandos:

| Configuração | Aplica-se a |
|--------------|-------------|
| `ISSUER` | apenas `dacce` |
| `LOGO` | `danfe`, `dacte`, `damdfe` |
| `TOP/RIGHT/BOTTOM/LEFT_MARGIN` | `danfe`, `dacte`, `damdfe`, `danfse` |

Se nenhum `config.yaml` for encontrado, os valores padrão são utilizados. Se o caminho do `LOGO` não existir, ele é ignorado com um aviso no console e o documento é gerado sem logo.

!!! warning
    Para o `dacce`, configurar a seção `ISSUER` é na prática obrigatório — sem um `config.yaml`, dados fictícios de emitente ("EMPRESA LTDA" / "AV. TEST, 100") são impressos no PDF.
