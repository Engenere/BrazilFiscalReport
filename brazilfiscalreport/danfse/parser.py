"""
DanfseParser — camada de ETL do DANFSe.

Port refatorado do método ``_parse_xml`` do código original. Responsável por
ler o XML da NFS-e e produzir o dicionário ``data`` consumido pela camada de
renderização (FPDF2).

Melhorias em relação ao original:
- Quebrado em métodos por bloco (em vez de um único método de ~300 linhas).
- Acesso defensivo a nós/atributos (sem KeyError/TypeError/NoneType).
- Bug corrigido: tax_regim comparava texto com "3".
- Bug corrigido: soma de retenções misturava número com string "R$ ...".
- NT 009:
    * finNFSe e cStat traduzidos por domínio.
    * CNPJ alfanumérico (via format_cpf_cnpj).
    * vAjusteBCISSQN + vCalcAjusteBCISSQN no lugar de vDedRed/vDR.
    * Grupos IBS/CBS (incl. gTribSN para Simples Nacional).
    * PIS/COFINS apenas para competência <= dez/2026.
    * Truncamentos da NT 008 aplicados.

Esta etapa entrega o PARSER. A renderização (_draw_*) virá na sequência.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from ..utils import (
    format_number,
    format_phone,
    get_date_utc,
    get_tag_text,
)
from . import danfse_conf as K
from .config import DanfseConfig
from .municipios import city_from_ibge, load_municipios
from .nt009_utils import (
    competence_allows_pis_cofins,
    iso2_country,
    to_float,
    truncate_text,
)
from .nt009_utils import (
    format_cep_safe as format_cep,
)
from .nt009_utils import (
    format_cpf_cnpj_nfse as format_cpf_cnpj,
)
from .nt009_utils import (
    money as _money,
)


class DanfseParser:
    def __init__(self, xml, config=None):
        self.config = config or DanfseConfig()
        self.price_precision = self.config.decimal_config.price_precision
        self.municipios = load_municipios()
        self.root = ET.fromstring(xml)

    # -- helpers internos ---------------------------------------------------

    # Valores monetários no DANFSe usam 2 casas (price_precision do config
    # pode ser 4, voltado a preços unitários de outros documentos).
    MONEY_PRECISION = 2

    def _money(self, value):
        """'R$ x' usando o format_number compartilhado do projeto."""
        return _money(value, self.MONEY_PRECISION, format_number)

    def _t(self, node, tag):
        """Atalho para get_tag_text com o namespace padrão.

        O get_tag_text compartilhado pode retornar None/sem strip; garantimos
        string limpa aqui.
        """
        text = get_tag_text(node, K.URL, tag) if node is not None else ""
        return (text or "").strip()

    def _find(self, node, path):
        if node is None:
            return None
        return node.find(f"{K.URL}{path}")

    def _city(self, code: str, fallback: str = "", uf_fallback: str = "") -> str:
        return city_from_ibge(code, self.municipios, fallback, uf_fallback)

    def _address(self, node: Element | None) -> str:
        """Concatena xLgr, nro, xCpl, xBairro (NT: truncar 77 no renderer)."""
        if node is None:
            return K.EMPTY
        parts = [
            self._t(node, "xLgr"),
            self._t(node, "nro"),
            self._t(node, "xCpl"),
            self._t(node, "xBairro"),
        ]
        joined = ", ".join(p for p in parts if p and p.strip())
        return joined or K.EMPTY

    # -- pipeline -----------------------------------------------------------

    def parse(self) -> dict:
        root = self.root
        inf_nfse = self._find(root, "infNFSe")
        dps = self._find(root, "DPS")
        emit = self._find(root, "emit")
        if emit is None:
            emit = self._find(inf_nfse, "emit")
        ender_nac = self._find(emit, "enderNac")
        prest = self._find(dps, "prest")
        reg_trib = self._find(prest, "regTrib")
        serv = self._find(dps, "serv")
        valores = self._find(root, "valores")

        data: dict = {}
        data.update(self._parse_identification(inf_nfse, dps))
        data["issuer"] = self._parse_issuer(emit, inf_nfse, ender_nac, reg_trib)
        data["taker"] = self._parse_taker(dps)
        data["recipient"] = self._parse_recipient(dps, data["taker"])
        data["intermed"] = self._parse_intermediary(dps)
        data["service"] = self._parse_service(serv, inf_nfse)
        data["municipal_taxes"] = self._parse_municipal_taxes(dps, valores, serv)
        data["federal_taxes"] = self._parse_federal_taxes(dps, data)
        data["ibs_cbs_taxes"] = self._parse_ibs_cbs(dps, valores, reg_trib)
        data["total_value"] = self._parse_totals(dps, valores, data)
        data["taxes_amount"] = self._parse_approx_taxes(dps)
        data["complementary_info"] = self._parse_complementary_info(serv, dps, data)
        return data

    # -- 1. Identificação ---------------------------------------------------

    def _parse_identification(self, inf_nfse, dps) -> dict:
        compet_raw = self._t(dps, "dCompet")
        compet, _ = get_date_utc(compet_raw)
        if not compet:
            # dCompet pode vir só como data (AAAA-MM-DD).
            compet = self._format_compet(compet_raw)
        dt_nfse, hr_nfse = get_date_utc(self._t(inf_nfse, "dhProc"))
        dt_dps, hr_dps = get_date_utc(self._t(dps, "dhEmi"))

        tp_amb = self._t(dps, "tpAmb") or self._t(inf_nfse, "tpAmb")
        amb_ger = self._t(inf_nfse, "ambGer")

        # Chave de acesso: remover prefixo "NFS" do atributo Id (defensivo).
        key = ""
        if inf_nfse is not None:
            raw_id = inf_nfse.attrib.get("Id") or ""
            key = raw_id[3:] if raw_id.upper().startswith("NFS") else raw_id

        tp_emit = self._t(dps, "tpEmit")
        c_stat = self._t(inf_nfse, "cStat")
        fin = self._t(dps, "finNFSe")

        # cStat: 101 = Cancelada, 102 = Cancelada por Substituição.
        is_cancelled = c_stat == "101"
        is_replaced = c_stat == "102"

        return {
            "environment": tp_amb,
            "environment_str": K.TP_AMB.get(tp_amb, "Não Informado"),
            "is_homologation": tp_amb == "2",
            "c_stat": c_stat,
            "is_cancelled": is_cancelled,
            "is_replaced": is_replaced,
            "ambiente_gerador": amb_ger or "Não Informado",
            "key_nfse": key,
            "nfse_number": self._t(inf_nfse, "nNFSe"),
            "compet": compet or "-",
            "compet_raw": compet_raw,
            "dt_nfse": dt_nfse,
            "hr_nfse": hr_nfse,
            "dt_dps": dt_dps,
            "hr_dps": hr_dps,
            "dps_number": self._t(dps, "nDPS"),
            "dps_serie": self._t(dps, "serie"),
            "emitente_nfse": K.TP_EMIT.get(tp_emit, "Prestador do Serviço"),
            "situacao_nfse": truncate_text(
                K.C_STAT.get(c_stat, "Normal"), K.Limits.CSTAT
            ),
            "finalidade": truncate_text(
                K.FIN_NFSE.get(fin, "Regular"), K.Limits.FIN_NFSE
            ),
        }

    @staticmethod
    def _format_compet(raw: str) -> str:
        """dCompet costuma vir como AAAA-MM-DD -> DD/MM/AAAA."""
        if not raw:
            return ""
        parts = raw.split("T")[0].split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return raw

    # -- 2. Prestador -------------------------------------------------------

    def _parse_issuer(self, emit, inf_nfse, ender_nac, reg_trib) -> dict:
        op_simp = self._t(reg_trib, "opSimpNac")
        simples = truncate_text(
            K.OP_SIMP_NAC.get(op_simp, "Não Optante"), K.Limits.SIMPLES
        )
        is_optante = op_simp in K.OP_SIMP_NAC_OPTANTES

        reg_ap = self._t(reg_trib, "regApTribSN")
        # BUG FIX: comparar pelo CÓDIGO (não pelo texto já traduzido).
        tax_regim = (
            truncate_text(K.REG_AP_TRIB_SN.get(reg_ap, ""), K.Limits.REG_AP_TRIB_SN)
            if is_optante and reg_ap
            else K.EMPTY
        )

        cep = format_cep(self._t(ender_nac, "CEP"))
        c_mun = self._t(ender_nac, "cMun")
        uf_nac = self._t(ender_nac, "UF")

        return {
            "id": format_cpf_cnpj(self._t(emit, "CNPJ"))
            or format_cpf_cnpj(self._t(emit, "CPF"))
            or self._t(emit, "NIF")
            or K.EMPTY,
            "municipal_registration": self._t(emit, "IM") or K.EMPTY,
            "phone": truncate_text(format_phone(self._t(emit, "fone")), K.Limits.PHONE),
            "name": truncate_text(
                self._t(emit, "xNome") or self._t(emit, "xFant"),
                K.Limits.NAME,
            ),
            "email": self._t(emit, "email") or K.EMPTY,
            "address": truncate_text(self._address(ender_nac), K.Limits.ADDRESS),
            "city": self._city(
                self._t(inf_nfse, "cLocEmi") or c_mun,
                self._t(inf_nfse, "xLocEmi"),
                uf_nac,
            ),
            "cep": cep,
            "ibge_cep": f"{c_mun} / {cep}" if c_mun else (cep or K.EMPTY),
            "simples": simples,
            "tax_regim": tax_regim,
        }

    # -- 3. Tomador ---------------------------------------------------------

    def _empty_entity(self, with_im: bool = True) -> dict:
        base = {
            "id": K.EMPTY,
            "phone": K.EMPTY,
            "name": K.EMPTY,
            "email": K.EMPTY,
            "address": K.EMPTY,
            "city": K.EMPTY,
            "cep": K.EMPTY,
            "ibge_cep": K.EMPTY,
            "present": False,
        }
        if with_im:
            base["municipal_registration"] = K.EMPTY
        return base

    def _parse_party(self, node, with_im: bool = True) -> dict:
        end = self._find(node, "end")
        end_nac = self._find(end, "endNac") if end is not None else None
        # Alguns layouts usam diretamente <end> com cMun/CEP.
        addr_node = end_nac if end_nac is not None else end
        c_mun = self._t(addr_node, "cMun")
        cep = format_cep(self._t(addr_node, "CEP"))
        uf = self._t(addr_node, "UF")

        entity = {
            "id": format_cpf_cnpj(self._t(node, "CNPJ"))
            or format_cpf_cnpj(self._t(node, "CPF"))
            or self._t(node, "NIF")
            or K.EMPTY,
            "phone": truncate_text(format_phone(self._t(node, "fone")), K.Limits.PHONE),
            "name": truncate_text(self._t(node, "xNome"), K.Limits.NAME),
            "email": self._t(node, "email") or K.EMPTY,
            "address": truncate_text(
                self._address(end if end is not None else node),
                K.Limits.ADDRESS,
            ),
            "city": self._city(c_mun, uf_fallback=uf),
            "cep": cep,
            "ibge_cep": f"{c_mun} / {cep}" if c_mun else (cep or K.EMPTY),
            "present": True,
        }
        if with_im:
            entity["municipal_registration"] = self._t(node, "IM") or K.EMPTY
        return entity

    def _parse_taker(self, dps) -> dict:
        toma = self._find(dps, "toma")
        if toma is None:
            return self._empty_entity(with_im=True)
        return self._parse_party(toma, with_im=True)

    # -- 4. Destinatário ----------------------------------------------------

    def _parse_recipient(self, dps, taker: dict) -> dict:
        dest = self._find(dps, "dest")
        if dest is None:
            # NT/spec: se não há destinatário, ele é o próprio tomador.
            return {
                **self._empty_entity(with_im=False),
                "is_taker": True,
                "present": False,
            }
        recipient = self._parse_party(dest, with_im=False)
        recipient["is_taker"] = recipient["id"] == taker.get("id")
        return recipient

    # -- 5. Intermediário ---------------------------------------------------

    def _parse_intermediary(self, dps) -> dict:
        interm = self._find(dps, "interm")
        if interm is None:
            return self._empty_entity(with_im=True)
        return self._parse_party(interm, with_im=True)

    # -- 6. Serviço ---------------------------------------------------------

    def _parse_service(self, serv, inf_nfse) -> dict:
        description = self._t(serv, "xDescServ")

        national_tax = self._t(serv, "cTribNac")
        if len(national_tax) >= 6:
            national_short = (
                f"{national_tax[:2]}.{national_tax[2:4]}.{national_tax[4:]}"
            )
        else:
            national_short = national_tax

        # Descrição da tributação: xTribMun com fallback xTribNac (trunc 167).
        # No layout real essas tags ficam em infNFSe (não dentro de serv);
        # como _t usa busca recursiva, procuramos a partir do root também.
        x_trib = (
            self._t(serv, "xTribMun")
            or self._t(serv, "xTribNac")
            or self._t(self.root, "xTribMun")
            or self._t(self.root, "xTribNac")
        )

        country_code = self._t(serv, "cPaisPrestacao")
        country = iso2_country(country_code, self._t(serv, "xPaisPrestacao"))

        return {
            "national_tax_code_short": national_short or K.EMPTY,
            "municipal_tax_code": self._t(serv, "cTribMun") or K.EMPTY,
            "nbs_code": self._t(serv, "cNBS") or K.EMPTY,
            "place_of_provision": self._city(
                self._t(inf_nfse, "cLocPrestacao"),
                self._t(inf_nfse, "xLocPrestacao"),
                self._t(inf_nfse, "UFLocPrestacao"),
            ),
            "country": country,
            "description": truncate_text(description, K.Limits.SERVICE_DESCRIPTION)
            if description
            else K.EMPTY,
            "short_description": truncate_text(x_trib, K.Limits.SHORT_DESCRIPTION),
        }

    # -- 7. Tributação Municipal (ISSQN) ------------------------------------

    def _parse_municipal_taxes(self, dps, valores, serv) -> dict:
        trib_issqn = self._t(dps, "tribISSQN")
        no_incidence = trib_issqn in K.TRIB_ISSQN_SEM_INCIDENCIA

        # Retenção (com .get para evitar KeyError do original).
        ret_type = self._t(dps, "tpRetISSQN")
        retention = K.TP_RET_ISSQN.get(ret_type, K.TP_RET_ISSQN["1"])

        # NT 009: total de deduções/reduções (substitui vDR).
        ded_red = to_float(self._t(dps, "vAjusteBCISSQN")) + to_float(
            self._t(dps, "vCalcAjusteBCISSQN")
        )

        v_serv = self._t(dps, "vServ")
        v_desc_inc = self._t(dps, "vDescIncond")
        v_bc = self._t(valores, "vBC")
        aliq = self._t(valores, "pAliqAplic")
        v_issqn = self._t(valores, "vISSQN")

        # Suspensão (exigSusp).
        exig = self._find(dps, "exigSusp")
        if exig is not None:
            tp_susp = self._t(exig, "tpSusp")
            suspension = truncate_text(
                K.TP_SUSP.get(tp_susp, "Não"), K.Limits.SUSPENSION
            )
            susp_number = truncate_text(self._t(exig, "nProcesso"), K.Limits.PROCESS)
        else:
            suspension, susp_number = "Não", K.EMPTY

        # Benefício municipal.
        bm = self._find(dps, "BM")
        benefit = self._t(bm, "nBM") if bm is not None else K.EMPTY

        return {
            "no_incidence": no_incidence,
            "issqn_tax": K.TRIB_ISSQN.get(trib_issqn, "Operação Tributável"),
            "issqn_tax_short": truncate_text(
                K.TRIB_ISSQN.get(trib_issqn, "Operação Tributável"),
                K.Limits.TRIB_ISSQN_TYPE,
            ),
            "country": iso2_country(
                self._t(dps, "cPaisResult"), self._t(dps, "xPaisResult")
            ),
            "city": self._city(
                self._t(self._find(self.root, "infNFSe"), "cLocIncid"),
                self._t(self._find(self.root, "infNFSe"), "xLocIncid"),
                self._t(self._find(self.root, "infNFSe"), "UFLocIncid"),
            ),
            "special_tax_regim": truncate_text(
                K.REG_ESP_TRIB.get(
                    self._t(self._find(dps, "prest"), "regEspTrib")
                    or self._t(dps, "regEspTrib"),
                    "Nenhum",
                ),
                K.Limits.REG_ESP_TRIB,
            ),
            "immunity_type": truncate_text(
                self._t(dps, "tpImunidade") or "", K.Limits.IMMUNITY
            ),
            "suspension_issqn": suspension,
            "suspension_number": susp_number or K.EMPTY,
            "municipal_benefit": benefit or K.EMPTY,
            "municipal_benefit_math": self._money(
                self._t(dps, "vCalcBM") or self._t(dps, "vRedBCBM"),
                self.price_precision,
            )
            if (self._t(dps, "vCalcBM") or self._t(dps, "vRedBCBM"))
            else K.EMPTY,
            "deduct_reduc_amount": self._money(ded_red) if ded_red else K.EMPTY,
            "service_amount": self._money(v_serv),
            "discount_unconditioned": self._money(v_desc_inc)
            if v_desc_inc
            else K.EMPTY,
            "calculation_basis": self._money(v_bc),
            "aliq_applied": f"{format_number(aliq, self.price_precision)}%"
            if aliq
            else K.EMPTY,
            "issqn_retention": retention,
            "issqn_cleared": self._money(v_issqn)
            if ret_type == "1"
            else self._money(0),
            # auxiliares para os totais
            "_v_issqn": v_issqn,
            "_ret_type": ret_type,
        }

    # -- 8. Tributação Federal (exceto CBS) ---------------------------------

    def _parse_federal_taxes(self, dps, data) -> dict:
        trib_fed = self._find(dps, "tribFed")
        result = {
            "irrf": K.EMPTY,
            "previdenciary_contribution": K.EMPTY,
            "social_contribution": K.EMPTY,
            "social_description": K.EMPTY,
            "pis_debit": K.EMPTY,
            "cofins_debit": K.EMPTY,
        }
        if trib_fed is None:
            return result

        v_irrf = self._t(trib_fed, "vRetIRRF")
        v_cp = self._t(trib_fed, "vRetCP")
        v_csll = self._t(trib_fed, "vRetCSLL")

        result["irrf"] = self._money(v_irrf) if v_irrf else K.EMPTY
        result["previdenciary_contribution"] = self._money(v_cp) if v_cp else K.EMPTY
        result["social_contribution"] = self._money(v_csll) if v_csll else K.EMPTY
        result["social_description"] = truncate_text(
            self._t(trib_fed, "tpRetPisCofins") or "", K.Limits.PIS_COFINS_DESC
        )

        # NT 009: PIS/COFINS apenas se competência <= dez/2026.
        if competence_allows_pis_cofins(data.get("compet_raw", "")):
            pis_cofins = self._find(trib_fed, "piscofins")
            if pis_cofins is not None:
                pis = self._t(pis_cofins, "vPis")
                cofins = self._t(pis_cofins, "vCofins")
                result["pis_debit"] = self._money(pis)
                result["cofins_debit"] = self._money(cofins)
                result["_pis_cofins_total"] = to_float(pis) + to_float(cofins)
        return result

    # -- 9. IBS / CBS (NT 009) ---------------------------------------------

    def _parse_ibs_cbs(self, dps, valores, reg_trib) -> dict:
        ibs_cbs = self._find(dps, "IBSCBS")
        if ibs_cbs is None:
            ibs_cbs = self._find(valores, "IBSCBS")
        pp = self.MONEY_PRECISION

        # Estrutura default (sem grupo IBS/CBS no XML).
        result = {
            "present": ibs_cbs is not None,
            "cst_cclass": K.EMPTY,
            "ind_oper_ibge_mun_uf": K.EMPTY,
            "excl_red_bc": self._money(0),
            "bc_apos_excl": self._money(0),
            "red_aliq_ibs_cbs": "% / % / %",
            "aliq_ibs_uf_mun": "% / %",
            "aliq_efet_mun_ibs": "%",
            "valor_apurado_mun_ibs": self._money(0),
            "aliq_efet_est_ibs": "%",
            "valor_apurado_est_ibs": self._money(0),
            "valor_total_apurado_ibs": self._money(0),
            "aliq_cbs": "%",
            "aliq_efet_cbs": "%",
            "valor_total_apurado_cbs": self._money(0),
            "_v_ibs_tot": 0.0,
            "_v_cbs": 0.0,
        }
        if ibs_cbs is None:
            return result

        # NT 009: Simples Nacional puxa valores de gTribSN.
        op_simp = self._t(reg_trib, "opSimpNac")
        is_simples = op_simp in K.OP_SIMP_NAC_OPTANTES
        g_trib_sn = self._find(ibs_cbs, "gTribSN")

        cst = self._t(ibs_cbs, "CST")
        cclass = self._t(ibs_cbs, "cClassTrib")
        result["cst_cclass"] = f"{cst} / {cclass}".strip(" /") or K.EMPTY

        ind_op = self._t(ibs_cbs, "cIndOp")
        loc_code = self._t(ibs_cbs, "cLocalidadeIncid")
        loc_name = self._t(ibs_cbs, "xLocalidadeIncid")
        uf = self._t(ibs_cbs, "UF")
        result["ind_oper_ibge_mun_uf"] = (
            " / ".join(p for p in (ind_op, loc_code, loc_name, uf) if p) or K.EMPTY
        )

        # Exclusões/Reduções (NT 009).
        excl = to_float(self._t(ibs_cbs, "vCalcAjusteBCIBSCBS")) + to_float(
            self._t(ibs_cbs, "vCalcAjusteBCLocImoveis")
        )
        result["excl_red_bc"] = self._money(excl)
        result["bc_apos_excl"] = self._money(self._t(ibs_cbs, "vBC"))

        result["red_aliq_ibs_cbs"] = (
            f"{format_number(self._t(ibs_cbs, 'pRedAliqUF'), pp)}% / "
            f"{format_number(self._t(ibs_cbs, 'pRedAliqMun'), pp)}% / "
            f"{format_number(self._t(ibs_cbs, 'pRedAliqCBS'), pp)}%"
        )
        result["aliq_ibs_uf_mun"] = (
            f"{format_number(self._t(ibs_cbs, 'pIBSUF'), pp)}% / "
            f"{format_number(self._t(ibs_cbs, 'pIBSMun'), pp)}%"
        )
        result["aliq_efet_mun_ibs"] = (
            f"{format_number(self._t(ibs_cbs, 'pAliqEfetMun'), pp)}%"
        )
        result["valor_apurado_mun_ibs"] = self._money(self._t(ibs_cbs, "vIBSMun"))
        result["aliq_efet_est_ibs"] = (
            f"{format_number(self._t(ibs_cbs, 'pAliqEfetUF'), pp)}%"
        )
        result["valor_apurado_est_ibs"] = self._money(self._t(ibs_cbs, "vIBSUF"))

        # Totais IBS/CBS — Simples Nacional usa gTribSN.
        if is_simples and g_trib_sn is not None:
            v_ibs = to_float(self._t(g_trib_sn, "vIBSSN"))
            p_cbs = self._t(g_trib_sn, "pCBSSN")
            v_cbs = to_float(self._t(g_trib_sn, "vCBSSN"))
        else:
            v_ibs = to_float(self._t(ibs_cbs, "vIBSTot"))
            p_cbs = self._t(ibs_cbs, "pCBS")
            v_cbs = to_float(self._t(ibs_cbs, "vCBS"))

        result["valor_total_apurado_ibs"] = self._money(v_ibs)
        result["aliq_cbs"] = f"{format_number(p_cbs, pp)}%" if p_cbs else "%"
        result["aliq_efet_cbs"] = (
            f"{format_number(self._t(ibs_cbs, 'pAliqEfetCBS'), pp)}%"
        )
        result["valor_total_apurado_cbs"] = self._money(v_cbs)
        result["_v_ibs_tot"] = v_ibs
        result["_v_cbs"] = v_cbs
        return result

    # -- 10. Totais ---------------------------------------------------------

    def _parse_totals(self, dps, valores, data) -> dict:
        muni = data["municipal_taxes"]
        fed = data["federal_taxes"]
        ibs = data["ibs_cbs_taxes"]

        # NT 009: locação de imóvel multiplica por pCopropriedade.
        copropriedade = to_float(self._t(dps, "pCopropriedade"), 1.0) or 1.0

        v_serv = to_float(self._t(dps, "vServ")) * copropriedade
        v_desc_inc = to_float(self._t(dps, "vDescIncond")) * copropriedade
        v_desc_cond = to_float(self._t(dps, "vDescCond")) * copropriedade
        v_liq = to_float(self._t(valores, "vLiq"))

        # Retenções — BUG FIX: somar números, não strings "R$ ...".
        issqn_value = to_float(muni.get("_v_issqn"))
        issqn_retained = (
            issqn_value if muni.get("_ret_type") in K.TP_RET_ISSQN_RETIDO else 0.0
        )
        total_ret_raw = self._t(valores, "vTotalRet")
        # vTotalRet quando presente; senão, soma defensiva (ISSQN retido).
        total_retentions = to_float(total_ret_raw) if total_ret_raw else issqn_retained
        federal_retentions = max(total_retentions - issqn_retained, 0.0)

        v_ibs_cbs = ibs.get("_v_ibs_tot", 0.0) + ibs.get("_v_cbs", 0.0)
        net_plus_ibs_cbs = v_liq + v_ibs_cbs

        return {
            "service_amount": self._money(v_serv),
            "discount_unconditioned": self._money(v_desc_inc)
            if v_desc_inc
            else K.EMPTY,
            "discount_conditioned": self._money(v_desc_cond)
            if v_desc_cond
            else K.EMPTY,
            "issqn_retained": self._money(issqn_retained),
            "total_federal_retentions": self._money(federal_retentions),
            "total_retentions": self._money(total_retentions),
            "net_value": self._money(v_liq),
            "total_ibs_cbs": self._money(v_ibs_cbs),
            "net_value_ibs_cbs": self._money(net_plus_ibs_cbs),
            "pis_cofins_debit": self._money(fed.get("_pis_cofins_total", 0.0))
            if fed.get("_pis_cofins_total")
            else K.EMPTY,
        }

    # -- Totais aproximados (Lei 12.741/2012) -------------------------------

    def _parse_approx_taxes(self, dps) -> dict:
        fed = self._t(dps, "vTotTribFed")
        est = self._t(dps, "vTotTribEst")
        mun = self._t(dps, "vTotTribMun")
        return {
            "federal_tax": self._money(fed) if fed else K.EMPTY,
            "state_tax": self._money(est) if est else K.EMPTY,
            "municipal_tax": self._money(mun) if mun else K.EMPTY,
        }

    # -- 11. Informações Complementares -------------------------------------

    def _parse_complementary_info(self, serv, dps, data) -> str:
        info_compl = self._find(serv, "infoCompl")

        # Concatenação estruturada por pipe (spec bloco 8).
        segments = [
            ("Inf. Cont.", self._t(info_compl, "xInfComp")),
            ("NFS-e Subst.", self._t(dps, "chSubstda")),
            ("Doc. Ref.", self._t(dps, "docRef")),
            ("Cod. Obra", self._t(self._find(dps, "obra"), "cObra")),
            ("Insc. Imob.", self._t(self._find(dps, "imovel"), "inscImobFisc")),
            ("Cod. Evt.", self._t(dps, "idAtvEvt")),
            ("Doc. Tec.", self._t(dps, "idDocTec")),
            ("Núm. Ped.", self._t(dps, "xPed")),
            ("Item Ped.", self._t(dps, "xItemPed")),
            ("Out. Inf.", self._t(info_compl, "xOutInf")),
        ]
        body = " | ".join(f"{label}: {val}" for label, val in segments if val)

        # NT 008: truncar em 1997 chars SEM apagar a linha fixa final.
        body = body[: K.Limits.COMPLEMENTARY_INFO]

        taxes = data["taxes_amount"]
        fed = taxes["federal_tax"] if taxes["federal_tax"] != K.EMPTY else "R$ ou %"
        est = taxes["state_tax"] if taxes["state_tax"] != K.EMPTY else "R$ ou %"
        mun = taxes["municipal_tax"] if taxes["municipal_tax"] != K.EMPTY else "R$ ou %"
        transparency = (
            "Totais Aproximados dos Tributos cfe. Lei nº 12.741/2012: "
            f"Federais: {fed} | Estaduais: {est} | Municipais: {mun}"
        )

        lines = []
        if body:
            lines.append(body)
        lines.append("")
        lines.append(transparency)
        return "\n".join(lines)
