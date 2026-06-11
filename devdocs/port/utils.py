"""
Utilitários de formatação e extração para o DANFSe.

Port (consolidado) dos helpers que no projeto original viviam em ``..utils``:
    format_cep, format_cpf_cnpj, format_number, format_phone,
    get_date_utc, get_tag_text

Todas as funções são tolerantes a None/"" e nunca lançam exceção por
ausência de dado — devolvem string vazia ou o placeholder.

Inclui também:
- truncate_text  -> regra de reticências da NT 008.
- format_cpf_cnpj -> NT 009: CNPJ agora é alfanumérico (Tipo C), tratado
  SEMPRE como string (nunca convertido para int).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from xml.etree.ElementTree import Element


# ---------------------------------------------------------------------------
# Extração de XML
# ---------------------------------------------------------------------------

def get_tag_text(node: Element | None, url: str, tag: str) -> str:
    """Retorna o texto da primeira ocorrência de ``tag`` dentro de ``node``.

    Tolerante a node None e a tag inexistente.
    """
    if node is None:
        return ""
    found = node.find(f"{url}{tag}")
    if found is None or found.text is None:
        return ""
    return found.text.strip()


# ---------------------------------------------------------------------------
# Texto / NT 008
# ---------------------------------------------------------------------------

def truncate_text(text: str | None, max_length: int) -> str:
    """Regra rígida de reticências exigida pela NT 008.

    - Se o texto exceder ``max_length``, corta em ``max_length - 3`` e
      acrescenta "...".
    - Vazio/None retorna "-".
    """
    if text and len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text or "-"


# ---------------------------------------------------------------------------
# Documentos / NT 009
# ---------------------------------------------------------------------------

def format_cpf_cnpj(value: str | None) -> str:
    """Formata CPF (11), CNPJ (14) ou NIF.

    NT 009: o CNPJ passou a ser ALFANUMÉRICO (Tipo C). Por isso o valor é
    tratado sempre como string; nunca convertemos para int. A máscara só é
    aplicada quando o conteúdo couber no padrão esperado; caso contrário,
    devolvemos o valor cru (NIF e outros formatos).
    """
    if not value:
        return ""
    raw = str(value).strip()
    # Remove separadores comuns mantendo alfanuméricos (NT 009).
    cleaned = re.sub(r"[^0-9A-Za-z]", "", raw)

    # CPF: 11 dígitos numéricos -> 000.000.000-00
    if len(cleaned) == 11 and cleaned.isdigit():
        return f"{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}"

    # CNPJ (numérico OU alfanumérico): 14 chars -> 00.000.000/0000-00
    if len(cleaned) == 14:
        return (
            f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}"
            f"/{cleaned[8:12]}-{cleaned[12:]}"
        )

    # NIF ou outro formato: devolve cru.
    return raw


def format_cep(value: str | None) -> str:
    """Formata CEP de 8 dígitos como 00000-000; senão devolve cru/vazio."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return str(value).strip()


def format_phone(value: str | None) -> str:
    """Formata telefone brasileiro (10 ou 11 dígitos)."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return str(value).strip()


# ---------------------------------------------------------------------------
# Números
# ---------------------------------------------------------------------------

def to_float(value, default: float = 0.0) -> float:
    """Conversão segura para float, aceitando vírgula decimal e None."""
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(".", "").replace(",", ".")) \
            if _looks_brazilian(value) else float(value)
    except (ValueError, TypeError):
        return default


def _looks_brazilian(value) -> bool:
    s = str(value)
    return "," in s and s.rfind(",") > s.rfind(".")


def format_number(value, precision: int = 2) -> str:
    """Formata número no padrão brasileiro: 1.234,56.

    Tolerante a None/""/string. Nunca lança.
    """
    num = to_float(value, 0.0)
    formatted = f"{num:,.{precision}f}"
    # en -> pt-BR
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def money(value, precision: int = 2) -> str:
    """Atalho: 'R$ 1.234,56'."""
    return f"R$ {format_number(value, precision)}"


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------

def get_date_utc(date_str: str | None) -> tuple[str, str]:
    """Converte um datetime ISO (com TZ ou não) em (DD/MM/AAAA, hh:mm:ss).

    Retorna ("", "") quando não há data parseável.
    """
    if not date_str:
        return "", ""
    raw = str(date_str).strip()
    # Normaliza 'Z' para offset explícito.
    candidate = raw.replace("Z", "+00:00")
    dt = None
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        # Tenta alguns formatos comuns sem TZ.
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw[: len(fmt) + 2], fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return "", ""
    # Converte para horário local mantendo simples (sem mexer em TZ aqui).
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S")
