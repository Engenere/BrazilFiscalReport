"""Constantes e domínios de tradução do DANFSe (NT 008 / NT 009).

Mantém o ``URL`` original e acrescenta as tabelas de domínio usadas pelo
parser, centralizadas para facilitar manutenção/atualização sem mexer na
lógica.
"""

URL = ".//{http://www.sped.fazenda.gov.br/nfse}"

EMPTY = "-"

# --- Domínios de tradução ------------------------------------------------

TP_AMB = {"1": "Produção", "2": "Homologação"}

TP_EMIT = {
    "1": "Prestador do Serviço",
    "2": "Tomador do Serviço",
    "3": "Intermediário do Serviço",
}

# finNFSe — NT 009: domínios 1 e 2 (notas de ajuste)
FIN_NFSE = {"0": "Regular", "1": "Crédito", "2": "Débito"}

# cStat — subconjunto comum; não mapeados -> "Normal"
C_STAT = {
    "100": "Autorizada",
    "107": "Autorizada",
    "101": "Cancelada",
    "102": "Cancelada por Substituição",
}

# opSimpNac — NT 009: domínio 4
OP_SIMP_NAC = {
    "1": "Não Optante",
    "2": "Optante - Microempreendedor Individual (MEI)",
    "3": "Optante - Microempresa ou Empresa de Pequeno Porte (ME/EPP)",
    "4": "Optante - Pendente de Validação",
}
OP_SIMP_NAC_OPTANTES = {"2", "3", "4"}

REG_AP_TRIB_SN = {
    "1": ("Regime de apuração dos tributos federais e municipal pelo Simples Nacional"),
    "2": (
        "Regime de apuração dos tributos federais pelo SN e o ISSQN "
        "pela NFS-e conforme respectiva legislação municipal do tributo"
    ),
    "3": (
        "Regime de apuração dos tributos federais e municipal pela "
        "NFS-e conforme respectivas legislações federal e municipal "
        "de cada tributo"
    ),
}

REG_ESP_TRIB = {
    "0": "Nenhum",
    "1": "Ato Cooperado (Cooperativa)",
    "2": "Estimativa",
    "3": "Microempresa Municipal",
    "4": "Notário ou Registrador",
    "5": "Profissional Autônomo",
    "6": "Sociedade de Profissionais",
    "9": "Outros",
}

TRIB_ISSQN = {
    "1": "Operação Tributável",
    "2": "Imunidade",
    "3": "Exportação de serviço",
    "4": "Não Incidência",
}
TRIB_ISSQN_SEM_INCIDENCIA = {"2", "3", "4"}

TP_RET_ISSQN = {
    "1": "Não Retido",
    "2": "Retido pelo Tomador",
    "3": "Retido pelo Intermediário",
}
TP_RET_ISSQN_RETIDO = {"2", "3"}

TP_SUSP = {
    "1": "Exigibilidade do ISSQN Suspensa por Decisão Judicial",
    "2": "Exigibilidade do ISSQN Suspensa por Processo Administrativo",
}


# --- Limites de truncamento (NT 008) -------------------------------------


class Limits:
    MUNICIPIO = 37
    CSTAT = 37
    FIN_NFSE = 37
    NAME = 77
    ADDRESS = 77
    PHONE = 20
    SIMPLES = 37
    REG_AP_TRIB_SN = 77
    SHORT_DESCRIPTION = 167
    SERVICE_DESCRIPTION = 1297
    TRIB_ISSQN_TYPE = 21
    REG_ESP_TRIB = 27
    IMMUNITY = 37
    SUSPENSION = 37
    PROCESS = 37
    PIS_COFINS_DESC = 35
    COMPLEMENTARY_INFO = 1997
