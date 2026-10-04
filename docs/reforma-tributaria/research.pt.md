# Pesquisa

Resultado da leitura das normas em 04/10/2026. Cada item diz se está **confirmado** (texto da norma
lido) ou **a confirmar**. Os leiautes de impressão referem-se à representação em papel e PDF; os
campos continuam definidos pelo MOC e pelos schemas da NF-e.

## DANFE da NF-e (modelo 55): NT 2026.010 v1.00

- **Fonte:** [NT 2026.010 (Portal NF-e)](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=ugn4MYF5PLg=),
  publicada em 01/10/2026 e aprovada pelo Ato Técnico Conjunto RFB/CGIBS 8/2026. sha256 do PDF lido:
  `eadc5246235f37a55f8140ddcf84595c8ce77f2d760f111f7b85ddf389b8f484`.
- **Produção:** 01/12/2026. Não há fase de teste informada.
- **Diretrizes da NT:** mínima ruptura com o modelo atual, legibilidade e compatibilidade com o A4.
  Define um leiaute de referência em **retrato** e um alternativo em **paisagem**, com os mesmos campos.

### 4.1 Novo bloco "Total do IBS/CBS/IS"

Inserido logo após o bloco "Total do ICMS/IPI".

| Campo impresso | Tag (ID) |
|---|---|
| Valor da CBS | `vCBS` (W56) |
| Valor do IBS UF | `vIBSUF` (W41) |
| Valor do IBS Município | `vIBSMun` (W46) |
| Valor do Imposto Seletivo | `vIS` (W33) |
| Valor do IBS Monofásico | `vIBSMono` (W58) |
| Valor da CBS Monofásica | `vCBSMono` (W59) |
| Valor do IBS Monofásico por Retenção | `vIBSMonoReten` (W59a) |
| Valor da CBS Monofásica por Retenção | `vCBSMonoReten` (W59b) |

### 4.2 Quadro do emitente

- **Código do Regime Tributário** (`CRT`, C21): passa a ser impresso.
- **Tipo de Regime de Apuração do IBS e da CBS:** a NT reserva a área, mas a tag ainda será publicada
  em NT futura. Enquanto não houver definição da origem, **não imprimir conteúdo** nesse campo.

### 4.3 Itens ("Dados dos Produtos/Serviços")

| Campo impresso | Tag (ID) |
|---|---|
| Classificação Tributária do IBS/CBS | `cClassTrib` (UB14) |
| Base de Cálculo IBS/CBS | `vBC` (UB16) |
| Alíquota IBS UF / valor | `pIBSUF` (UB18) ou `pAliqEfet` (UB28) / `vIBSUF` (UB35) |
| Alíquota IBS Município / valor | `pIBSMun` (UB37) ou `pAliqEfet` (UB47) / `vIBSMun` (UB54) |
| Alíquota CBS / valor | `pCBS` (UB56) ou `pAliqEfet` (UB66) / `vCBS` (UB67) |
| Base, alíquota e valor do IS | `vBCIS` (UB05), `pIS` (UB06), `vIS` (UB11) |

**Regra de impressão das alíquotas:** quando houver redução de alíquota (`gRed`) ou compra
governamental (`gCompraGov`), imprimir a alíquota efetiva (`pAliqEfet`) para IBS UF, IBS Município e
CBS; sem `gRed`, imprimir a alíquota vigente (`pIBSUF`, `pIBSMun`, `pCBS`).

### 4.4 Campos e quadros facultativos

Exibição facultativa ou condicionada à existência da informação no XML, por exemplo canhoto,
fatura/duplicatas, `vFCP`, `vFCPST`, `vICMSUFDest`, `vFCPUFDest` e a base quantitativa do ICMS
monofásico. A NT é explícita: a faculdade de exibição **não autoriza criar, inferir ou imprimir
informação inexistente no XML**.

## DACTE (CT-e)

- **Hoje:** o DACTE da biblioteca já tem a opção `display_ibs_cbs`, com colunas de IBS UF, IBS
  Município e CBS (`brazilfiscalreport/dacte/dacte.py`).
- **Norma:** NT 2026.004 v1.00 (CT-e, NFCom, BP-e, NF3e, NFAg, NFGas), homologação 13/10/2026 e
  produção 16/11/2026 (CT-e Simplificado: 14/12/2026). Regra do total: `vTotDFe` repete `vTPrest`, e a
  partir de 2027 IBS e CBS ficam dentro do `vTPrest`; entra o campo `vTPrestLiq`.
  Fonte: [NT 2026.004 (Portal CT-e)](https://www.cte.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=r9eZhnUIcAk=).
- **A confirmar:** se a NT altera o leiaute de impressão do DACTE ou só o XML.

## DANFSe (NFS-e)

- **Norma:** NT SE/CGNFS-e 008 v1.02 (leiaute do DANFSe, 20/07/2026) e NT 009 v1.01 (aprovada pelo
  Ato Técnico Conjunto 7/2026, publicada em 01/10/2026), que traz o grupo de IBS/CBS da DPS. A NT 009
  **não tem data de produção**. Fonte: [Portal NFS-e](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc).
- **A confirmar:** quais campos de IBS/CBS o DANFSe deve imprimir.

## Demais documentos

- **DAMDFE:** o leiaute do MDF-e não tem campos de IBS/CBS; sem mudança prevista.
- **DANFCe:** há o PR #202 (em aberto) e a issue #122 na biblioteca. Não encontrei NT de impressão do
  DANFCe com IBS/CBS.
- **DANFE simplificado:** a NT 2026.003 define o DANFE Simplificado Tipo 2 (etiqueta); a issue #115
  da biblioteca trata do tema. A relação direta com a reforma não está clara.
- **NFCom, BP-e, NF3e, NFAg, NFGas e NF-e ABI:** têm datas de obrigatoriedade no
  [Ato Conjunto RFB/CGIBS 4/2026](https://www.cgibs.gov.br/atos-conjuntos) (NFCom em 01/10/2026; os
  demais em 01/12/2026), mas não encontrei NT de impressão para eles. São documentos novos na
  biblioteca.

## Fontes e acesso

Todas as fontes são normas e portais oficiais, acessadas em 04/10/2026: Portal NF-e, Portal CT-e,
Portal NFS-e e CGIBS. A lista de atos técnicos está em <https://www.cgibs.gov.br/atos-tecnicos-conjuntos>.
