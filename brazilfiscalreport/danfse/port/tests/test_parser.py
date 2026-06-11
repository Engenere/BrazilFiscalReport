"""
Testes do DanfseParser.

Focam nos pontos críticos do port:
- Correção dos 2 bugs do código original (tax_regim e soma de retenções).
- Comportamentos novos da NT 009.
- Robustez (XML mínimo não deve quebrar).

Rodar:  python3 -m pytest danfse/port/tests/test_parser.py -v
   ou:  python3 danfse/port/tests/test_parser.py   (modo standalone)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from danfse.port.parser import DanfseParser  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name="sample_nfse.xml"):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return DanfseParser(f.read()).parse()


def test_cnpj_alfanumerico_nt009():
    """NT 009: CNPJ alfanumérico deve ser mascarado como string."""
    data = _load()
    assert data["issuer"]["id"] == "12.ABC.345/01DE-35"


def test_bugfix_tax_regim_aparece():
    """Bug original: comparava texto com '3' e nunca exibia o regime."""
    data = _load()
    assert data["issuer"]["tax_regim"].startswith("Regime de apuração")


def test_bugfix_retencoes_nao_zeram():
    """Bug original: somava número com string 'R$ ...' e zerava tudo."""
    data = _load()
    assert data["total_value"]["total_retentions"] == "R$ 450,00"
    assert data["total_value"]["total_federal_retentions"] == "R$ 450,00"


def test_nt009_finalidade_traduzida():
    data = _load()
    assert data["finalidade"] == "Regular"


def test_nt009_deducoes_ajustebc():
    """NT 009: vAjusteBCISSQN + vCalcAjusteBCISSQN (substitui vDR)."""
    data = _load()
    assert data["municipal_taxes"]["deduct_reduc_amount"] == "R$ 150,00"


def test_nt009_pis_cofins_dentro_do_prazo():
    """Competência 05/2026 <= dez/2026 -> PIS/COFINS presentes."""
    data = _load()
    assert data["federal_taxes"]["pis_debit"] == "R$ 65,00"
    assert data["federal_taxes"]["cofins_debit"] == "R$ 300,00"


def test_pais_iso2():
    data = _load()
    assert data["service"]["country"] == "BR"


def test_chave_sem_prefixo_nfs():
    data = _load()
    assert not data["key_nfse"].upper().startswith("NFS")
    assert len(data["key_nfse"]) == 47  # tamanho do sample (após remover NFS)


def test_complementary_info_pipe_e_transparencia():
    data = _load()
    info = data["complementary_info"]
    assert "Inf. Cont.:" in info
    assert "Lei nº 12.741/2012" in info


def test_xml_minimo_nao_quebra():
    """Robustez: XML quase vazio não deve lançar exceção."""
    minimal = (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        '<infNFSe Id="NFS123"></infNFSe><DPS></DPS><valores></valores></NFSe>'
    )
    data = DanfseParser(minimal).parse()
    assert data["issuer"]["id"] == "-"
    assert data["taker"]["present"] is False


def test_pis_cofins_apos_2026_some():
    """NT 009: competência 01/2027 -> sem PIS/COFINS."""
    xml = (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        '<infNFSe Id="NFS1"><cStat>100</cStat></infNFSe>'
        '<DPS><dCompet>2027-01-01</dCompet>'
        '<tribFed><piscofins><vPis>10</vPis><vCofins>20</vCofins></piscofins></tribFed>'
        '</DPS><valores></valores></NFSe>'
    )
    data = DanfseParser(xml).parse()
    assert data["federal_taxes"]["pis_debit"] == "-"
    assert data["federal_taxes"]["cofins_debit"] == "-"


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in funcs:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(funcs)} testes passaram.")
