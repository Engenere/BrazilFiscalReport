import re
import warnings
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

import phonenumbers
from phonenumbers import PhoneNumberFormat


def get_tag_text(node=None, url="", tag=None):
    try:
        text = node.find(f"{url}{tag}").text
    except Exception:
        text = ""
    return text


def format_phone(phone):
    if not phone:
        return ""
    try:
        phone_number = phonenumbers.parse(phone, "BR")
        if phonenumbers.region_code_for_number(phone_number) == "BR":
            formatted_number = phonenumbers.format_number(
                phone_number, PhoneNumberFormat.NATIONAL
            )
        else:
            formatted_number = phonenumbers.format_number(
                phone_number, PhoneNumberFormat.INTERNATIONAL
            )
    except Exception as e:
        warnings.warn(f"An error occurred: {e}", UserWarning, stacklevel=2)
        formatted_number = phone
    return formatted_number


def format_cep(cep):
    return f"{cep[:5]}-{cep[5:8]}"


def get_date_utc(date_utc):
    dt = date_utc[0:10].split("-")
    dt.reverse()
    return "/".join(dt), date_utc[11:19]


def number_filter(doc):
    """
    Remove all characters that are not digits
    """
    return re.sub(r"\D", "", doc)


def format_cpf_cnpj(doc):
    doc = re.sub(r"[^0-9A-Za-z]", "", doc).upper()
    if doc:
        if len(doc) > 11:
            doc = f"{doc:0>14.14}"
            doc = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[-2:]}"
        else:
            doc = number_filter(doc)
            doc = f"{doc:0>11.11}"
            doc = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    return doc


def chunks(cString, nLen):
    for start in range(0, len(cString), nLen):
        yield cString[start : start + nLen]


def to_float(value):
    """Converte valor numérico cru do XML, tolerando ausência/formato inválido."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class VolumesSummary(NamedTuple):
    q_vol: str
    esp: str
    marca: str
    n_vol: str
    peso_b: str
    peso_l: str


def summarize_volumes(volumes, url=""):
    """Reúne os grupos ``vol`` da NF-e na única linha de volumes do DANFE.

    O leiaute permite vários ``vol`` em ``transp``, mas o DANFE tem uma linha
    só (MOC 7.0, campos X27 a X32). ``qVol``, ``pesoB`` e ``pesoL`` são
    somados; ``esp``, ``marca`` e ``nVol`` repetem o valor quando ele é o mesmo
    em todos os volumes e listam os valores distintos, separados por vírgula,
    quando diferem. Só o que consta do XML é impresso (MOC 7.0, item 3.1). Com
    um único ``vol`` o resultado é o conteúdo dele, sem alteração.
    """

    def distinct(tag):
        values = []
        for volume in volumes:
            text = get_tag_text(volume, url, tag)
            if text and text not in values:
                values.append(text)
        return ", ".join(values)

    def total(tag, precision):
        amounts = []
        for volume in volumes:
            try:
                amounts.append(Decimal(get_tag_text(volume, url, tag)))
            except InvalidOperation:
                continue
        if not amounts:
            return ""
        return f"{sum(amounts):.{precision}f}"

    return VolumesSummary(
        q_vol=total("qVol", 0),
        esp=distinct("esp"),
        marca=distinct("marca"),
        n_vol=distinct("nVol"),
        peso_b=total("pesoB", 3),
        peso_l=total("pesoL", 3),
    )


def format_number(cNumber, precision=0, group_sep=".", decimal_sep=","):
    if not cNumber:
        cNumber = "0"
    try:
        number = (
            ("{:,." + str(precision) + "f}")
            .format(float(cNumber))
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except Exception:
        number = ""
    return number


def format_rate(rate, suffix="%"):
    """Format a tax rate with 2 to 4 decimals, e.g. 12,00% or 8,6625%."""
    formatted = format_number(rate, precision=4) if rate else ""
    if not formatted:
        return ""
    integer, decimals = formatted.split(",")
    return f"{integer},{decimals.rstrip('0'):0<2}{suffix}"


def merge_if_different(value1, value2):
    str_val1 = str(value1).lower()
    str_val2 = str(value2).lower()
    if str_val1 != str_val2:
        return f"{value1}\n{value2}"
    else:
        return value1


def format_xDime(value):
    if value and "X" in value:
        parts = value.split("X")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return f"{value} (cm)"
    return value


def limit_text(text, max_len=None):
    words = text.split()
    result = []
    length = 0

    for word in words:
        extra_space = 1 if result else 0
        if length + len(word) + extra_space > max_len:
            break
        result.append(word)
        length += len(word) + extra_space

    return " ".join(result)
