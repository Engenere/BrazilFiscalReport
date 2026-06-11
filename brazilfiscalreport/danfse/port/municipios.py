"""
De-Para de código IBGE (7 dígitos) -> "Nome - UF".

Carrega de um municipios.json (mesmo formato do projeto original, vindo da
API de localidades do IBGE). O carregamento é tolerante: se o arquivo não
existir, devolve um mapa vazio e o parser cai nos fallbacks.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_municipios(path: str | None = None) -> dict[str, str]:
    """Retorna {codigo_ibge: "Nome - UF"}.

    Procura o arquivo em ``path`` ou, por padrão, em municipios.json ao lado
    deste módulo.
    """
    if path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(current_dir, "municipios.json")

    municipios: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for m in json.load(f):
                uf = _extract_uf(m)
                nome = m.get("nome", "")
                municipios[str(m["id"])] = f"{nome} - {uf}" if uf else nome
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return municipios


def _extract_uf(m: dict) -> str:
    """Extrai a sigla da UF lidando com os dois formatos da API do IBGE."""
    for path in (
        ("microrregiao", "mesorregiao", "UF", "sigla"),
        ("regiao-imediata", "regiao-intermediaria", "UF", "sigla"),
    ):
        node = m
        try:
            for key in path:
                node = node[key]
            if node:
                return node
        except (KeyError, TypeError):
            continue
    return ""


def city_from_ibge(
    code: str | None,
    municipios: dict[str, str],
    fallback_name: str = "",
) -> str:
    """Resolve o nome da cidade a partir do código IBGE.

    - Sem código: usa o fallback (xLoc...) ou "-".
    - Com código não encontrado: usa o fallback formatado.
    """
    if not code:
        return f"{fallback_name} - " if fallback_name else "-"
    return municipios.get(str(code), f"{fallback_name} - " if fallback_name else "-")
