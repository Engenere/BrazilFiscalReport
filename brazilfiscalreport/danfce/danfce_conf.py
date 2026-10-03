# A NFC-e é a NF-e modelo 65: mesmo namespace, mesmo XSD.
from ..danfe.danfe_conf import URL

# Título obrigatório do DANFE NFC-e e a ressalva que o acompanha.
TITLE = "DANFE NFC-e - Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica"
NO_ICMS_CREDIT_NOTICE = "Não permite aproveitamento de crédito de ICMS"

# Avisos que substituem o valor fiscal do cupom.
HOMOLOGATION_NOTICE = "EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL"
CONTINGENCY_NOTICE = "EMITIDA EM CONTINGÊNCIA"
PENDING_AUTH_NOTICE = "Pendente de autorização"

# Impresso no lugar do valor quando o XML não informa vTotTrib.
UNREPORTED_TAX = "-----"

# tpEmis (NF-e leiaute 4.00). 1 e 6..9 não se aplicam à NFC-e, mas o
# documento pode chegar com qualquer um deles; só o 1 dispensa aviso.
TP_EMISSAO_NORMAL = "1"

# tPag (NF-e leiaute 4.00, grupo YA).
TP_PAGAMENTO = {
    "01": "Dinheiro",
    "02": "Cheque",
    "03": "Cartão de Crédito",
    "04": "Cartão de Débito",
    "05": "Cartão da Loja / Crediário",
    "10": "Vale Alimentação",
    "11": "Vale Refeição",
    "12": "Vale Presente",
    "13": "Vale Combustível",
    "14": "Duplicata Mercantil",
    "15": "Boleto Bancário",
    "16": "Depósito Bancário",
    "17": "PIX Dinâmico",
    "18": "Transferência Bancária / Carteira Digital",
    "19": "Programa de Fidelidade / Cashback / Crédito Virtual",
    "20": "PIX Estático",
    "21": "Crédito em Loja",
    "22": "Pagamento Eletrônico não Informado",
    "90": "Sem Pagamento",
    "91": "Pagamento Posterior",
    "99": "Outros",
}

# Componentes de ICMSTot que somam no vNF, conforme a fórmula do MOC:
# vNF = vProd - vDesc - vICMSDeson + vST + vFCPST + vFrete + vSeg + vOutro
#       + vII + vIPI + vIPIDevol
# O cupom imprime esse bloco como um único "ACRÉSCIMO", para que
# VALOR TOTAL - DESCONTO + ACRÉSCIMO feche exatamente com VALOR A PAGAR.
TOTAL_ADDITIONS = (
    "vST",
    "vFCPST",
    "vFrete",
    "vSeg",
    "vOutro",
    "vII",
    "vIPI",
    "vIPIDevol",
)
TOTAL_DEDUCTIONS = ("vDesc", "vICMSDeson")

__all__ = [
    "CONTINGENCY_NOTICE",
    "HOMOLOGATION_NOTICE",
    "NO_ICMS_CREDIT_NOTICE",
    "PENDING_AUTH_NOTICE",
    "TITLE",
    "TOTAL_ADDITIONS",
    "TOTAL_DEDUCTIONS",
    "TP_EMISSAO_NORMAL",
    "TP_PAGAMENTO",
    "UNREPORTED_TAX",
    "URL",
]
