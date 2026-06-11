"""
Constantes e domínios de tradução do DANFSe v2.0.

Centraliza:
- O namespace XML da NFS-e nacional.
- Todas as tabelas de domínio (de-para de códigos -> texto), já contemplando
  as atualizações da NT 009 (LC 214/2025).

Mantido separado da lógica para facilitar testes e atualização de domínios
sem tocar no parser/renderer.
"""

from __future__ import annotations

# Namespace padrão do XML da NFS-e nacional.
#
# O projeto original define URL com o prefixo ".//" (busca recursiva em
# qualquer descendente). Mantemos a mesma semântica:
#   - NS    -> apenas o namespace entre chaves, p/ montar caminhos relativos
#   - URL   -> prefixo de busca recursiva (compatível com o original)
NS = "{http://www.sped.fazenda.gov.br/nfse}"
URL = f".//{NS}"

# Placeholder usado quando um valor está ausente.
EMPTY = "-"


# ---------------------------------------------------------------------------
# Domínios de tradução
# ---------------------------------------------------------------------------

# Tipo de Ambiente (tpAmb)
TP_AMB = {
    "1": "Produção",
    "2": "Homologação",
}

# Emitente da NFS-e (tpEmit) — NT 009 contempla 3 = Intermediário
TP_EMIT = {
    "1": "Prestador do Serviço",
    "2": "Tomador do Serviço",
    "3": "Intermediário do Serviço",
}

# Finalidade da NFS-e (finNFSe) — NT 009: domínios 1 e 2 (notas de ajuste)
FIN_NFSE = {
    "0": "Regular",
    "1": "Crédito",
    "2": "Débito",
}

# Situação da NFS-e (cStat). Subconjunto dos status mais comuns.
# Para status não mapeados, o parser deve cair em "Normal".
C_STAT = {
    "100": "Autorizada",
    "107": "Autorizada",
    "101": "Cancelada",
    "102": "Cancelada por Substituição",
}

# Optante pelo Simples Nacional (opSimpNac) — NT 009: domínio 4
OP_SIMP_NAC = {
    "1": "Não Optante",
    "2": "Optante - Microempreendedor Individual (MEI)",
    "3": "Optante - Microempresa ou Empresa de Pequeno Porte (ME/EPP)",
    "4": "Optante - Pendente de Validação",
}

# Códigos de opSimpNac que indicam que a empresa é optante do SN
# (relevante para puxar IBS/CBS do grupo gTribSN).
OP_SIMP_NAC_OPTANTES = {"2", "3", "4"}

# Regime de Apuração Tributária pelo SN (regApTribSN)
REG_AP_TRIB_SN = {
    "1": (
        "Regime de apuração dos tributos federais e municipal pelo "
        "Simples Nacional"
    ),
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

# Regime Especial de Tributação do ISSQN (regEspTrib)
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

# Tipo de Tributação do ISSQN (tribISSQN)
TRIB_ISSQN = {
    "1": "Operação Tributável",
    "2": "Imunidade",
    "3": "Exportação de serviço",
    "4": "Não Incidência",
}

# Códigos de tribISSQN que NÃO incidem ISSQN
# (usado para imprimir "OPERAÇÃO NÃO SUJEITA AO ISSQN").
TRIB_ISSQN_SEM_INCIDENCIA = {"2", "3", "4"}

# Retenção do ISSQN (tpRetISSQN)
TP_RET_ISSQN = {
    "1": "Não Retido",
    "2": "Retido pelo Tomador",
    "3": "Retido pelo Intermediário",
}

# Códigos de tpRetISSQN que indicam ISSQN retido.
TP_RET_ISSQN_RETIDO = {"2", "3"}

# Suspensão da Exigibilidade do ISSQN (tpSusp)
TP_SUSP = {
    "1": "Exigibilidade do ISSQN Suspensa por Decisão Judicial",
    "2": "Exigibilidade do ISSQN Suspensa por Processo Administrativo",
}


# ---------------------------------------------------------------------------
# Limites de truncamento (NT 008)
# ---------------------------------------------------------------------------

class Limits:
    """Limites de caracteres exigidos pela NT 008 para cada campo."""

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
