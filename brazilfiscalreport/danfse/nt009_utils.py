"""Helpers específicos do DANFSe (NT 008 / NT 009).

Estes utilitários ficam LOCAIS ao módulo danfse de propósito: o módulo
compartilhado ``brazilfiscalreport/utils.py`` é usado também por NFe, CTe,
MDFe e CCe, e não deve ser alterado para acomodar regras exclusivas da
NFS-e (ex.: CNPJ alfanumérico da NT 009 quebraria o ``format_cpf_cnpj``
genérico, que assume documento puramente numérico).

Compatível com Python 3.8+ (sem unions ``X | Y``).
"""

import re
import xml.etree.ElementTree as ET
from typing import Optional

# Namespace da NFS-e (igual ao danfse_conf.URL, mas sem o prefixo de busca).
_NS = "{http://www.sped.fazenda.gov.br/nfse}"

# Tipos de evento que alteram a situação da NFS-e.
# A parte específica do evento é uma tag eNNNNNN dentro de infPedReg.
EVENT_CANCEL = "cancelamento"
EVENT_REPLACE = "substituicao"


def parse_event_xml(xml):
    """Lê um XML de EVENTO da NFS-e e retorna um dicionário resumido.

    Os eventos (cancelamento, substituição, etc.) são documentos separados
    cuja raiz é <evento>. Eles referenciam a NFS-e pela chave (chNFSe) e
    podem alterar a situação do documento.

    Retorna None se o XML não for um evento reconhecível, ou um dict:
        {
            "ch_nfse": "...",        # chave da NFS-e referenciada
            "kind": "cancelamento"|"substituicao"|"outro",
            "tp_evento": "101101",   # código do tipo (eNNNNNN)
            "x_desc": "Cancelamento de NFS-e",
            "x_motivo": "Erro na emissão.",
            "ch_subst": "...",       # chave substituta (só em substituição)
        }
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None

    root_tag = root.tag.split("}")[-1]
    inf_evento = root.find(f"{_NS}infEvento")
    if root_tag != "evento" and inf_evento is None:
        return None

    ch_nfse = _deep_text(root, "chNFSe")
    x_desc = _deep_text(root, "xDesc")
    x_motivo = _deep_text(root, "xMotivo")
    ch_subst = _deep_text(root, "chSubstda") or _deep_text(root, "chNFSeSubst")

    # Identifica a tag específica do evento (eNNNNNN) dentro de infPedReg.
    tp_evento = ""
    inf_ped = root.find(f".//{_NS}infPedReg")
    if inf_ped is not None:
        for child in inf_ped:
            local = child.tag.split("}")[-1]
            if re.fullmatch(r"e\d{6}", local):
                tp_evento = local[1:]
                break

    # Classifica o tipo. 101101 = Cancelamento; substituição traz chSubstda
    # ou descrição/código próprios.
    desc = (x_desc or "").lower()
    if ch_subst or "substitu" in desc:
        kind = EVENT_REPLACE
    elif tp_evento.startswith("1011") or "cancel" in desc:
        kind = EVENT_CANCEL
    else:
        kind = "outro"

    return {
        "ch_nfse": ch_nfse,
        "kind": kind,
        "tp_evento": tp_evento,
        "x_desc": x_desc,
        "x_motivo": x_motivo,
        "ch_subst": ch_subst,
    }


def _deep_text(node, tag):
    """Busca recursiva pelo primeiro texto da tag (com namespace)."""
    found = node.find(f".//{_NS}{tag}")
    if found is not None and found.text:
        return found.text.strip()
    return ""


def truncate_text(text: Optional[str], max_length: int) -> str:
    """Regra de reticências da NT 008.

    Corta em ``max_length - 3`` e acrescenta "..."; vazio -> "-".
    """
    if text and len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text or "-"


def format_cpf_cnpj_nfse(value: Optional[str]) -> str:
    """Formata CPF/CNPJ/NIF para a NFS-e.

    NT 009: o CNPJ passou a ser ALFANUMÉRICO (Tipo C). Diferente do
    ``format_cpf_cnpj`` compartilhado (que faz ``re.sub(r"\\D", "")`` e
    descartaria letras), aqui preservamos caracteres alfanuméricos.
    """
    if not value:
        return ""
    raw = str(value).strip()
    cleaned = re.sub(r"[^0-9A-Za-z]", "", raw)

    if len(cleaned) == 11 and cleaned.isdigit():
        return f"{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}"

    if len(cleaned) == 14:
        return (
            f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}"
            f"/{cleaned[8:12]}-{cleaned[12:]}"
        )

    return raw  # NIF ou outro formato


def to_float(value, default: float = 0.0) -> float:
    """Conversão segura para float (aceita None/"" e vírgula decimal)."""
    if value is None or value == "":
        return default
    s = str(value)
    try:
        if "," in s and s.rfind(",") > s.rfind("."):
            return float(s.replace(".", "").replace(",", "."))
        return float(s)
    except (ValueError, TypeError):
        return default


def competence_allows_pis_cofins(compet_raw: Optional[str]) -> bool:
    """NT 009: PIS/COFINS apenas para competência até dez/2026."""
    if not compet_raw:
        return True
    try:
        parts = compet_raw.split("T")[0].split("-")
        year, month = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return True
    return (year, month) <= (2026, 12)


def iso2_country(code: Optional[str], name: Optional[str]) -> str:
    """País em ISO-2 (NT 008). 1058/76 -> 'BR'."""
    if code in ("1058", "76", "BR", "", None):
        return "BR"
    return name or code or "BR"


def money(value, precision: int = 2, format_number=None) -> str:
    """'R$ 1.234,56'. Recebe o ``format_number`` compartilhado por injeção
    para não duplicar a lógica de formatação numérica do projeto."""
    if format_number is not None:
        return f"R$ {format_number(value, precision)}"
    # fallback local (pt-BR) caso não injetado
    num = to_float(value)
    s = f"{num:,.{precision}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def format_cep_safe(cep: Optional[str]) -> str:
    """CEP 00000-000 tolerante a vazio/None (o format_cep compartilhado
    assume string com 8 dígitos e quebra com entrada vazia)."""
    if not cep:
        return ""
    digits = re.sub(r"\D", "", str(cep))
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return str(cep).strip()
