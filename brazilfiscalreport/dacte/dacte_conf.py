URL = ".//{http://www.portalfiscal.inf.br/cte}"

TP_MODAL = {
    "01": "RODOVIÁRIO",
    "02": "AÉREO",
    "03": "AQUAVIÁRIO",
    "04": "FERROVIÁRIO",
    "05": "DUTOVIÁRIO",
    "06": "MULTIMODAL",
}
TP_TOMADOR = {
    "0": "REMETENTE",
    "1": "EXPEDIDOR",
    "2": "RECEBEDOR",
    "3": "DESTINATÁRIO",
    "4": "OUTRO",
}

TP_CTE = {
    "0": "NORMAL",
    "1": "COMPLEMENTAR",
    "2": "ANULADO",
    "3": "SUSBTITUTO",
}

TP_SERVICO = {
    "0": "NORMAL",
    "1": "SUBCONTRATAÇÃO",
    "2": "REDESPACHO",
    "3": "REDESPACHO INTERMEDIÁRIO",
    "4": "MULTIMODAL",
}

TP_CODIGO_MEDIDA = {
    "00": "M3",
    "01": "KG",
    "02": "TON",
    "03": "UNIDADE",
    "04": "LITROS",
    "05": "MMBTU",
}

TP_CODIGO_MEDIDA_REDUZIDO = {
    "00": "M3",
    "01": "KG",
    "02": "TON",
    "03": "UN",
    "04": "LT",
    "05": "MMBTU",
}

TP_MANUSEIO = {
    "01": "Certificado do expedidor para embarque de animal vivo",
    "02": "Artigo perigoso conforme Declaração do Expedidor anexa",
    "03": "Somente em aeronave cargueira",
    "04": "Artigo perigoso - declaração do expedidor não requerida",
    "05": "Artigo perigoso em quantidade isenta",
    "06": "Gelo seco para refrigeração (especificar no campo observações a quantidade)",
    "07": "Não restrito (especificar a Disposição Especial no campo observações)",
    "08": "Artigo perigoso em carga consolidada (especificar a quantidade no campo "
    "observações)",
    "09": "Autorização da autoridade governamental anexa (especificar no campo "
    "observações)",
    "10": "Baterias de íons de lítio em conformidade com a Seção II da PI965 – CAO",
    "11": "Baterias de íons de lítio em conformidade com a Seção II da PI966",
    "12": "Baterias de íons de lítio em conformidade com a Seção II da PI967",
    "13": "Baterias de metal lítio em conformidade com a Seção II da PI968 — CAO",
    "14": "Baterias de metal lítio em conformidade com a Seção II da PI969",
    "15": "Baterias de metal lítio em conformidade com a Seção II da PI970",
    "99": "Outro (especificar no campo observações)",
}

TP_TRAFICO = {
    "0": "PRÓPRIO",
    "1": "MÚTUO",
    "2": "RODOFERROVIÁRIO",
    "3": "RODOVIÁRIO",
}

TP_FERROV_EMITENTE = {
    "1": "FERROVIA DE ORIGEM",
    "2": "FERROVIA DE DESTINO",
}

RESP_FATURAMENTO = {
    "1": "FERROVIA DE ORIGEM",
    "2": "FERROVIA DE DESTINO",
}

TP_ICMS = {
    "00": "TRIBUTAÇÃO NORMAL ICMS",
    "20": "TRIBUTAÇÃO COM BC REDUZIDA DO ICMS",
    "40": "ICMS ISENÇÃO",
    "41": "ICMS NÃO TRIBUTADA",
    "51": "ICMS DIFERIDO",
    "60": "ICMS COBRADO POR SUBSTITUIÇÃO TRIBUTÁRIA",
    "90": "ICMS OUTROS",
}
