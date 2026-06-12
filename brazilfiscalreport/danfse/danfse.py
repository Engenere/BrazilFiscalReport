import csv
import os
import xml.etree.ElementTree as ET
from functools import lru_cache
from xml.etree.ElementTree import Element

from ..generate_qrcode import draw_qr_code
from ..utils import (
    format_cpf_cnpj,
    format_number,
    format_phone,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DanfseConfig
from .danfse_conf import URL

# Busca por filho direto (sem o prefixo ".//" de URL).
URL_DIRECT = URL.replace(".//", "")


def extract_text(node: Element, tag: str) -> str:
    return get_tag_text(node, URL, tag) or ""


UF_CODE_TO_INITIALS = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}


@lru_cache(maxsize=1)
def _municipios_ibge():
    path = os.path.join(os.path.dirname(__file__), "municipios_ibge.csv")
    table = {}
    with open(path, encoding="utf-8", newline="") as csv_file:
        for code, name, uf in csv.reader(csv_file, delimiter=";"):
            table[code] = (name, uf)
    return table


def municipio_ibge(code: str):
    """Nome e UF do município pela Tabela do IBGE (código de 7 dígitos)."""
    return _municipios_ibge().get((code or "").strip(), ("", ""))


def uf_from_ibge_code(code: str) -> str:
    """UF derivada dos 2 primeiros dígitos do código IBGE do município."""
    return UF_CODE_TO_INITIALS.get((code or "")[:2], "")


def ellipsize(text: str, limit: int) -> str:
    """Reticências quando o texto supera o limite de caracteres (NT 008/2026)."""
    if text and len(text) > limit:
        return f"{text[:limit]}..."
    return text


def to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def join_parts(*parts):
    joined = " / ".join(p for p in parts if p)
    return joined or "-"


def format_cep_nt(cep: str) -> str:
    """Máscara de CEP da NT 008/2026 (nn.nnn-nnn)."""
    digits = "".join(c for c in (cep or "") if c.isdigit())
    if len(digits) == 8:
        return f"{digits[:2]}.{digits[2:5]}-{digits[5:]}"
    return cep or ""


TP_EMIT = {
    "1": "Prestador",
    "2": "Tomador",
    "3": "Intermediário",
}

AMB_GER = {
    "1": "Sistema Próprio do Município",
    "2": "Sefin Nacional NFS-e",
}

TP_AMB = {
    "1": "Produção",
    "2": "Homologação",
}

C_STAT = {
    "100": "NFS-e Gerada",
    "101": "NFS-e de Substituição Gerada",
    "102": "NFS-e de Decisão Judicial ou Administrativa",
    "103": "NFS-e Avulsa",
    "107": "NFS-e MEI",
}

FIN_NFSE = {
    "0": "NFS-e regular",
    "1": "NFS-e de crédito",
    "2": "NFS-e de débito",
}

TRIB_ISSQN = {
    "1": "Operação Tributável",
    "2": "Exportação de serviço",
    "3": "Não Incidência",
    "4": "Imunidade",
}

TP_IMUNIDADE = {
    "0": "Imunidade (tipo não informado na nota de origem)",
    "1": "Patrimônio, renda ou serviços, uns dos outros (CF88, Art 150, VI, a)",
    "2": "Templos de qualquer culto (CF88, Art 150, VI, b)",
    "3": (
        "Patrimônio, renda ou serviços dos partidos políticos, inclusive "
        "suas fundações, das entidades sindicais dos trabalhadores, das "
        "instituições de educação e de assistência social, sem fins "
        "lucrativos, atendidos os requisitos da lei (CF88, Art 150, VI, c)"
    ),
    "4": (
        "Livros, jornais, periódicos e o papel destinado a sua impressão "
        "(CF88, Art 150, VI, d)"
    ),
    "5": (
        "Fonogramas e videofonogramas musicais produzidos no Brasil "
        "contendo obras musicais ou literomusicais de autores brasileiros "
        "e/ou obras em geral interpretadas por artistas brasileiros bem "
        "como os suportes materiais ou arquivos digitais que os contenham "
        "(CF88, Art 150, VI, e)"
    ),
}

TP_SUSP = {
    "1": "Exigibilidade Suspensa por Decisão Judicial",
    "2": "Exigibilidade Suspensa por Processo Administrativo",
}

TP_RET_ISSQN = {
    "1": "Não Retido",
    "2": "Retido pelo Tomador",
    "3": "Retido pelo Intermediário",
}

# Domínio de tpRetPisCofins conforme NT 007/2026 (códigos 0 a 9).
TP_RET_PIS_COFINS = {
    "0": "PIS/COFINS/CSLL Não Retidos",
    "1": "PIS/COFINS Retido",
    "2": "PIS/COFINS Não Retido",
    "3": "PIS/COFINS/CSLL Retidos",
    "4": "PIS/COFINS Retidos, CSLL Não Retido",
    "5": "PIS Retido, COFINS/CSLL Não Retido",
    "6": "COFINS Retido, PIS/CSLL Não Retido",
    "7": "PIS Não Retido, COFINS/CSLL Retidos",
    "8": "PIS/COFINS Não Retidos, CSLL Retido",
    "9": "COFINS Não Retido, PIS/CSLL Retidos",
}

SIMPLES_OP = {
    "1": "Não Optante",
    "2": "Optante - Microempreendedor Individual (MEI)",
    "3": "Optante - Microempresa ou Empresa de Pequeno Porte (ME/EPP)",
}

REG_AP_TRIB_SN = {
    "1": (
        "Regime de apuração dos tributos federais e municipal pelo " "Simples Nacional"
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

TXT_TAKER_NOT_IDENTIFIED = "TOMADOR/ADQUIRENTE DA OPERAÇÃO NÃO IDENTIFICADO NA NFS-e"
TXT_DEST_NOT_IDENTIFIED = "DESTINATÁRIO DA OPERAÇÃO NÃO IDENTIFICADO NA NFS-e"
TXT_DEST_IS_TAKER = "O DESTINATÁRIO É O PRÓPRIO TOMADOR/ADQUIRENTE DA OPERAÇÃO"
TXT_INTERM_NOT_IDENTIFIED = "INTERMEDIÁRIO DA OPERAÇÃO NÃO IDENTIFICADO NA NFS-e"
TXT_NO_ISSQN = "TRIBUTAÇÃO MUNICIPAL (ISSQN) - OPERAÇÃO NÃO SUJEITA AO ISSQN"
TXT_NO_LEGAL_VALIDITY = "NFS-e SEM VALIDADE JURÍDICA"
TXT_QR_CODE = (
    "A autenticidade desta NFS-e pode ser verificada pela leitura "
    "deste código QR ou pela consulta da chave de acesso no portal "
    "nacional da NFS-e"
)

# Espessuras de linha da NT 008/2026, item 2.2.3 (0,5pt e 1pt, em mm).
LINE_DIVIDER = 0.176
LINE_BORDER = 0.353
SHADE_GRAY = 242  # cinza claro ~5% de densidade

ROW_H = 6.4  # altura padrão das linhas de campos
STRIP_H = 3.4  # altura das linhas de supressão (mín. 0,32 cm)


class Danfse(xFPDF):
    def __init__(self, xml, config: DanfseConfig = None):
        super().__init__(unit="mm", format="A4")
        config = config if config is not None else DanfseConfig()
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        self.set_auto_page_break(auto=False, margin=config.margins.bottom)
        self.set_title("DANFSE")
        self.default_font = config.font_type.value
        self.price_precision = config.decimal_config.price_precision
        self.quantity_precision = config.decimal_config.quantity_precision
        self.orientation = "P"
        self.watermark_cancelled = config.watermark_cancelled
        self.watermark_replaced = config.watermark_replaced
        self.display_canhoto = config.display_canhoto
        self.root = ET.fromstring(xml)
        self.add_page(self.orientation)

        # Grade do leiaute: blocos com 1 mm de folga em relação à moldura.
        self.bx = self.l_margin + 1
        self.bw = self.epw - 2
        self.colw = self.bw / 4

        self.data = self._parse_xml()
        self._draw_header()
        self._draw_identification()
        self._draw_provider()
        self._draw_taker()
        self._draw_dest()
        self._draw_intermediary()
        self._draw_service()
        self._draw_municipal_taxes()
        self._draw_federal_taxes()
        self._draw_ibscbs_taxes()
        self._draw_totals()
        self._draw_complementary_info()
        self._draw_canhoto()

        self.set_dash_pattern(dash=0, gap=0)
        self.set_line_width(LINE_BORDER)
        self.rect(x=self.l_margin, y=self.t_margin, w=self.epw, h=self.eph)
        self.set_line_width(LINE_DIVIDER)

        # Por último, acima dos quadros sombreados; a transparência preserva
        # a leitura do conteúdo sob a marca d'água.
        self._draw_watermark()

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------
    def _money(self, value):
        if value:
            return f"R$ {format_number(value, self.price_precision)}"
        return "-"

    def _pct(self, value):
        if value:
            return f"{format_number(value, self.price_precision)}%"
        return "-"

    @staticmethod
    def _format_address(tag):
        address_fields = [
            extract_text(tag, "xLgr"),
            extract_text(tag, "nro"),
            extract_text(tag, "xCpl"),
            extract_text(tag, "xBairro"),
        ]
        return ", ".join(str(c) for c in address_fields if c and str(c).strip())

    def _parse_person(self, node, inscricao=True):
        """Campos cadastrais de tomador/destinatário/intermediário."""
        if node is None:
            return None
        c_mun = extract_text(node, "cMun")
        mun_name, mun_uf = municipio_ibge(c_mun)
        mun_name = (
            mun_name or extract_text(node, "xMun") or extract_text(node, "xCidade")
        )
        mun_uf = (
            mun_uf
            or uf_from_ibge_code(c_mun)
            or extract_text(node, "UF")
            or extract_text(node, "xEstProvReg")
        )
        c_end_post = extract_text(node, "cEndPost")
        if c_end_post:
            ibge_cep = f"{c_end_post} (ext)"
        else:
            ibge_cep = join_parts(c_mun, format_cep_nt(extract_text(node, "CEP")))
        person = {
            "id": format_cpf_cnpj(extract_text(node, "CNPJ"))
            or format_cpf_cnpj(extract_text(node, "CPF"))
            or extract_text(node, "NIF")
            or "-",
            "phone": format_phone(extract_text(node, "fone")) or "-",
            "name": ellipsize(extract_text(node, "xNome"), 77) or "-",
            "email": extract_text(node, "email") or "-",
            "address": ellipsize(self._format_address(node), 77) or "-",
            "city": join_parts(mun_name, mun_uf),
            "ibge_cep": ibge_cep,
        }
        if inscricao:
            person["municipal_registration"] = extract_text(node, "IM") or "-"
        return person

    def _parse_xml(self):
        """Centralize all XML tags here."""
        inf_nfse = self.root.find(f"{URL}infNFSe")
        dps = self.root.find(f"{URL}DPS")
        if inf_nfse is None or dps is None:
            raise ValueError(
                "XML inválido para o DANFSe: os grupos NFSe/infNFSe e "
                "NFSe/infNFSe/DPS são obrigatórios."
            )
        inf_dps = dps.find(f"{URL}infDPS") if dps is not None else None
        emit = self.root.find(f"{URL}emit")
        enderNac = emit.find(f"{URL}enderNac") if emit is not None else None
        prest = dps.find(f"{URL}prest")
        prest_end = prest.find(f"{URL}end") if prest is not None else None
        regTrib = prest.find(f"{URL}regTrib") if prest is not None else None
        serv = dps.find(f"{URL}serv")
        trib_mun = dps.find(f"{URL}tribMun")
        # "valores" e "IBSCBS" existem em mais de um nível do XML: ancorar
        # a leitura nos filhos diretos para não capturar o grupo errado.
        valores = inf_nfse.find(f"{URL_DIRECT}valores")
        dps_ibscbs = (
            inf_dps.find(f"{URL_DIRECT}IBSCBS") if inf_dps is not None else None
        )
        nfse_ibscbs = inf_nfse.find(f"{URL_DIRECT}IBSCBS")

        compet = extract_text(dps, "dCompet")
        compet_fmt, _ = get_date_utc(compet)
        dt_nfse, hr_nfse = get_date_utc(extract_text(inf_nfse, "dhProc"))
        dt_dps, hr_dps = get_date_utc(extract_text(dps, "dhEmi"))

        opSimpNac = extract_text(regTrib, "opSimpNac")
        simples = ellipsize(SIMPLES_OP.get(opSimpNac, "-"), 37)

        reg_ap_trib = extract_text(regTrib, "regApTribSN")
        tax_regim = ellipsize(REG_AP_TRIB_SN.get(reg_ap_trib, ""), 77)

        reg_esp_trib = extract_text(regTrib, "regEspTrib")
        special_tax_regim = REG_ESP_TRIB.get(reg_esp_trib, "-")

        description = extract_text(serv, "xDescServ")

        national_tax = extract_text(serv, "cTribNac")
        if len(national_tax) >= 6:
            national_tax = f"{national_tax[:2]}.{national_tax[2:4]}.{national_tax[4:]}"
        municipal_tax = extract_text(serv, "cTribMun")
        nbs = extract_text(serv, "cNBS")
        if len(nbs) == 9:
            nbs = f"{nbs[:1]}.{nbs[1:5]}.{nbs[5:7]}.{nbs[7:]}"

        # Descrição do código de tributação: municipal quando houver,
        # senão nacional (tabela 2.4.5 da NT 008/2026).
        tax_code_description = ellipsize(
            extract_text(inf_nfse, "xTribMun") or extract_text(inf_nfse, "xTribNac"),
            167,
        )

        trib_issqn = extract_text(dps, "tribISSQN")
        issqn = TRIB_ISSQN.get(trib_issqn, "-")

        issqn_type = extract_text(dps, "tpRetISSQN")
        issqn_retention = TP_RET_ISSQN.get(issqn_type, "-")

        issqn_value = extract_text(valores, "vISSQN")

        _aliq_val = extract_text(valores, "pAliqAplic")
        _vserv = extract_text(dps, "vServ")
        _fed_tax = extract_text(dps, "vTotTribFed")
        _est_tax = extract_text(dps, "vTotTribEst")
        _mun_tax = extract_text(dps, "vTotTribMun")
        _fed_tax_pct = extract_text(dps, "pTotTribFed")
        _est_tax_pct = extract_text(dps, "pTotTribEst")
        _mun_tax_pct = extract_text(dps, "pTotTribMun")
        _vdesc_inc = extract_text(dps, "vDescIncond")
        _vdesc_cond = extract_text(dps, "vDescCond")

        # Benefício Municipal: descrição de tpBM (NFSe/infNFSe/valores),
        # textos do leiaute ADN da NFS-e nacional.
        bm = dps.find(f"{URL}BM")
        p_red_bcbm = extract_text(bm, "pRedBCBM") if bm is not None else ""
        v_red_bcbm = extract_text(bm, "vRedBCBM") if bm is not None else ""
        municipal_benefit_type = {
            "1": "Isenção",
            "2": f"Redução da BC em {format_number(p_red_bcbm, self.price_precision)}%"
            if p_red_bcbm
            else "Redução da Base de Cálculo",
            "3": f"Redução da BC em R$ "
            f"{format_number(v_red_bcbm, self.price_precision)}"
            if v_red_bcbm
            else "Redução da Base de Cálculo",
            "4": "Alíquota Diferenciada",
        }
        tp_bm = extract_text(valores, "tpBM")
        municipal_benefit = ellipsize(municipal_benefit_type.get(tp_bm, "-"), 37)

        v_calc_bm = extract_text(valores, "vCalcBM") or v_red_bcbm

        # Total Deduções/Reduções: vDR (DPS/infDPS/valores/vDedRed) ou
        # vCalcDR (infNFSe/valores), somado a vCalcReeRepRes
        # (infNFSe/IBSCBS/valores) quando presente.
        vDedRed = dps.find(f"{URL}vDedRed")
        ded_red_value = extract_text(vDedRed, "vDR") if vDedRed is not None else ""
        if not ded_red_value:
            ded_red_value = extract_text(valores, "vCalcDR")
        v_calc_ree = (
            extract_text(nfse_ibscbs, "vCalcReeRepRes")
            if nfse_ibscbs is not None
            else ""
        )
        if ded_red_value or v_calc_ree:
            total_dr = to_float(ded_red_value) + to_float(v_calc_ree)
            deduct_reduc_amount = self._money(str(total_dr))
        else:
            deduct_reduc_amount = "-"

        # Dados cadastrais do prestador: NFSe/infNFSe/DPS/infDPS/prest/, com
        # fallback para infNFSe/emit quando a tag não consta de prest/ e o
        # emitente é o próprio prestador (tpEmit=1 ou ausente).
        tp_emit = extract_text(dps, "tpEmit")
        emit_fb = emit if tp_emit in ("", "1") else None
        if prest_end is not None:
            prest_cmun = extract_text(prest_end, "cMun")
            issuer_address = self._format_address(prest_end)
            issuer_cep = extract_text(prest_end, "CEP")
            mun_name, mun_uf = municipio_ibge(prest_cmun)
            mun_name = (
                mun_name
                or extract_text(prest_end, "xMun")
                or extract_text(prest_end, "xCidade")
                or extract_text(inf_nfse, "xLocEmi")
            )
            mun_uf = (
                mun_uf or uf_from_ibge_code(prest_cmun) or extract_text(prest_end, "UF")
            )
            c_end_post = extract_text(prest_end, "cEndPost")
            if c_end_post:
                issuer_ibge_cep = f"{c_end_post} (ext)"
            else:
                issuer_ibge_cep = join_parts(prest_cmun, format_cep_nt(issuer_cep))
        else:
            prest_cmun = extract_text(enderNac, "cMun") if emit_fb is not None else ""
            issuer_address = (
                self._format_address(enderNac) if emit_fb is not None else ""
            )
            issuer_cep = extract_text(enderNac, "CEP") if emit_fb is not None else ""
            mun_name, mun_uf = municipio_ibge(prest_cmun)
            mun_name = mun_name or extract_text(inf_nfse, "xLocEmi")
            mun_uf = (
                mun_uf
                or uf_from_ibge_code(prest_cmun)
                or (extract_text(emit_fb, "UF") if emit_fb is not None else "")
            )
            issuer_ibge_cep = join_parts(prest_cmun, format_cep_nt(issuer_cep))

        emit_uf = extract_text(emit, "UF") if emit is not None else ""

        c_stat = extract_text(inf_nfse, "cStat")
        fin_nfse = extract_text(dps_ibscbs, "finNFSe") if dps_ibscbs is not None else ""

        data = {
            "environment": extract_text(dps, "tpAmb"),
            "key_nfse": (inf_nfse.attrib.get("Id") or "")[3:],
            "nfse_number": extract_text(inf_nfse, "nNFSe"),
            "compet": compet,
            "compet_fmt": compet_fmt,
            "dt_nfse": dt_nfse,
            "hr_nfse": hr_nfse,
            "dt_dps": dt_dps,
            "hr_dps": hr_dps,
            "dps_number": extract_text(dps, "nDPS"),
            "dps_serie": extract_text(dps, "serie"),
            "header": {
                # Não exibir o município quando o item do código de
                # tributação nacional for 99 (tabela 2.4.5 da NT 008/2026).
                "city": ""
                if extract_text(serv, "cTribNac")[:2] == "99"
                else join_parts(extract_text(inf_nfse, "xLocEmi"), emit_uf),
                "amb_ger": AMB_GER.get(
                    extract_text(inf_nfse, "ambGer"),
                    extract_text(inf_nfse, "ambGer"),
                )
                or "-",
                "tp_amb": TP_AMB.get(
                    extract_text(dps, "tpAmb"), extract_text(dps, "tpAmb")
                )
                or "-",
            },
            "emitter_type": TP_EMIT.get(tp_emit, "-"),
            "status": ellipsize(C_STAT.get(c_stat, c_stat), 37) or "-",
            "purpose": ellipsize(FIN_NFSE.get(fin_nfse, fin_nfse), 37) or "-",
            "issuer": {
                "id": format_cpf_cnpj(extract_text(prest, "CNPJ"))
                or format_cpf_cnpj(extract_text(prest, "CPF"))
                or extract_text(prest, "NIF")
                or format_cpf_cnpj(extract_text(emit_fb, "CNPJ"))
                or format_cpf_cnpj(extract_text(emit_fb, "CPF"))
                or "-",
                "municipal_registration": extract_text(prest, "IM")
                or extract_text(emit_fb, "IM")
                or "-",
                "phone": format_phone(
                    extract_text(prest, "fone") or extract_text(emit_fb, "fone")
                )
                or "-",
                "name": ellipsize(
                    extract_text(prest, "xNome") or extract_text(emit_fb, "xNome"),
                    77,
                )
                or "-",
                "email": extract_text(prest, "email")
                or extract_text(emit_fb, "email")
                or "-",
                "address": ellipsize(issuer_address, 77) or "-",
                "city": join_parts(mun_name, mun_uf),
                "ibge_cep": issuer_ibge_cep,
                "simples": simples,
                "tax_regim": tax_regim or "-",
            },
            "service": {
                "tax_code": join_parts(national_tax, municipal_tax),
                "nbs": nbs or "-",
                "place_of_provision": join_parts(
                    extract_text(inf_nfse, "xLocPrestacao"),
                    uf_from_ibge_code(extract_text(serv, "cLocPrestacao")),
                    extract_text(serv, "cPaisPrestacao") or "BR",
                ),
                "tax_code_description": tax_code_description,
                "description": ellipsize(description, 1297) or "-",
            },
            "municipal_taxes": {
                "suppressed": trib_mun is None,
                "issqn_tax": issqn,
                "city": join_parts(
                    extract_text(inf_nfse, "xLocIncid"),
                    uf_from_ibge_code(extract_text(inf_nfse, "cLocIncid")),
                    extract_text(dps, "cPaisResult") or "BR",
                ),
                "special_tax_regim": special_tax_regim,
                "immunity_type": ellipsize(
                    TP_IMUNIDADE.get(
                        extract_text(dps, "tpImunidade"),
                        extract_text(dps, "tpImunidade"),
                    ),
                    37,
                )
                or "-",
                "suspension_issqn": "-",
                "suspension_number": "-",
                "municipal_benefit": municipal_benefit,
                "municipal_benefit_math": self._money(v_calc_bm),
                "deduct_reduc_amount": deduct_reduc_amount,
                "discount_unconditioned": "-",
                "calculation_basis": self._money(extract_text(valores, "vBC")),
                "aliq_applied": self._pct(_aliq_val),
                "issqn_retention": issqn_retention,
                "issqn_cleared": self._money(issqn_value),
            },
            "total_value": {
                "service_amount": self._money(_vserv),
                "discount_conditioned": "-",
                "discount_unconditioned": "-",
                "total_retentions": self._money(extract_text(valores, "vTotalRet")),
                "net_value": self._money(extract_text(valores, "vLiq")),
                "total_ibscbs": "-",
                "net_value_ibscbs": "-",
            },
        }

        data["taker"] = self._parse_person(dps.find(f"{URL}toma"))
        data["intermed"] = self._parse_person(dps.find(f"{URL}interm"))
        dest = dps_ibscbs.find(f"{URL}dest") if dps_ibscbs is not None else None
        data["dest"] = self._parse_person(dest, inscricao=False)

        exigSusp = dps.find(f"{URL}exigSusp")
        if exigSusp is not None:
            issqn_suspension = TP_SUSP.get(extract_text(exigSusp, "tpSusp"))
            if issqn_suspension:
                data["municipal_taxes"]["suspension_issqn"] = ellipsize(
                    issqn_suspension, 37
                )
            n_processo = extract_text(exigSusp, "nProcesso")
            if n_processo:
                data["municipal_taxes"]["suspension_number"] = n_processo

        vDescCondIncond = dps.find(f"{URL}vDescCondIncond")
        if vDescCondIncond is not None:
            data["municipal_taxes"]["discount_unconditioned"] = self._money(_vdesc_inc)
            data["total_value"]["discount_unconditioned"] = self._money(_vdesc_inc)
            data["total_value"]["discount_conditioned"] = self._money(_vdesc_cond)

        # Tributação federal (exceto CBS). A linha PIS/COFINS/Descrição é
        # impressa somente até o ano-calendário de 2026 (Nota 6).
        data["federal_taxes"] = {
            "irrf": "-",
            "previdenciary_contribution": "-",
            "social_contribution": "-",
            "social_description": "-",
            "pis_debit": "-",
            "cofins_debit": "-",
            "show_pis_cofins": (compet[:4] or "0000") <= "2026",
        }
        pis = cofins = ""
        tribFed = dps.find(f"{URL}tribFed")
        if tribFed is not None:
            federal_taxes = data["federal_taxes"]
            federal_taxes["irrf"] = self._money(extract_text(tribFed, "vRetIRRF"))
            federal_taxes["previdenciary_contribution"] = self._money(
                extract_text(tribFed, "vRetCP")
            )
            federal_taxes["social_contribution"] = self._money(
                extract_text(tribFed, "vRetCSLL")
            )
            tp_ret_pis_cofins = extract_text(tribFed, "tpRetPisCofins")
            if tp_ret_pis_cofins in TP_RET_PIS_COFINS:
                federal_taxes["social_description"] = ellipsize(
                    TP_RET_PIS_COFINS[tp_ret_pis_cofins], 35
                )
            pis = extract_text(tribFed, "vPis")
            cofins = extract_text(tribFed, "vCofins")
            federal_taxes["pis_debit"] = self._money(pis)
            federal_taxes["cofins_debit"] = self._money(cofins)

        # Tributação IBS/CBS: grupos da DPS (CST/cClassTrib/cIndOp) e da
        # NFS-e (valores e totais calculados).
        def _node_text(node, tag):
            return extract_text(node, tag) if node is not None else ""

        cst = _node_text(dps_ibscbs, "CST")
        c_class_trib = _node_text(dps_ibscbs, "cClassTrib")
        c_ind_op = _node_text(dps_ibscbs, "cIndOp")
        ibs_valores = (
            nfse_ibscbs.find(f"{URL_DIRECT}valores")
            if nfse_ibscbs is not None
            else None
        )
        ibs_uf = ibs_valores.find(f"{URL}uf") if ibs_valores is not None else None
        ibs_mun = ibs_valores.find(f"{URL}mun") if ibs_valores is not None else None
        ibs_fed = ibs_valores.find(f"{URL}fed") if ibs_valores is not None else None
        tot_cibs = (
            nfse_ibscbs.find(f"{URL}totCIBS") if nfse_ibscbs is not None else None
        )
        c_loc_incid = _node_text(nfse_ibscbs, "cLocalidadeIncid")
        x_loc_incid = _node_text(nfse_ibscbs, "xLocalidadeIncid")

        exclusion_parts = [_vdesc_inc, v_calc_ree, issqn_value, pis, cofins]
        if any(exclusion_parts):
            exclusions = self._money(str(sum(to_float(p) for p in exclusion_parts)))
        else:
            exclusions = "-"

        p_red_uf = _node_text(ibs_uf, "pRedAliqUF")
        p_red_mun = _node_text(ibs_mun, "pRedAliqMun")
        p_red_cbs = _node_text(ibs_fed, "pRedAliqCBS")
        p_ibs_uf = _node_text(ibs_uf, "pIBSUF")
        p_ibs_mun = _node_text(ibs_mun, "pIBSMun")
        v_ibs_tot = _node_text(tot_cibs, "vIBSTot")
        v_cbs = _node_text(tot_cibs, "vCBS")

        if v_ibs_tot or v_cbs:
            data["total_value"]["total_ibscbs"] = self._money(
                str(to_float(v_ibs_tot) + to_float(v_cbs))
            )
        data["total_value"]["net_value_ibscbs"] = self._money(
            _node_text(tot_cibs, "vTotNF")
        )

        data["ibscbs"] = {
            "cst_cclasstrib": join_parts(cst, c_class_trib),
            "ind_op": join_parts(
                c_ind_op,
                c_loc_incid,
                x_loc_incid,
                uf_from_ibge_code(c_loc_incid),
            ),
            "exclusions": exclusions,
            "bc_after": self._money(_node_text(ibs_valores, "vBC")),
            "red_aliq": join_parts(
                self._pct(p_red_uf), self._pct(p_red_mun), self._pct(p_red_cbs)
            )
            if (p_red_uf or p_red_mun or p_red_cbs)
            else "-",
            "aliq_ibs": join_parts(self._pct(p_ibs_uf), self._pct(p_ibs_mun))
            if (p_ibs_uf or p_ibs_mun)
            else "-",
            "aliq_efet_mun": self._pct(_node_text(ibs_mun, "pAliqEfetMun")),
            "v_ibs_mun": self._money(_node_text(tot_cibs, "vIBSMun")),
            "aliq_efet_uf": self._pct(_node_text(ibs_uf, "pAliqEfetUF")),
            "v_ibs_uf": self._money(_node_text(tot_cibs, "vIBSUF")),
            "v_ibs_tot": self._money(v_ibs_tot),
            "aliq_cbs": self._pct(_node_text(ibs_fed, "pCBS")),
            "aliq_efet_cbs": self._pct(_node_text(ibs_fed, "pAliqEfetCBS")),
            "v_cbs": self._money(v_cbs),
        }

        # Informações complementares: união dos campos na ordem da tabela
        # 2.4.5, separados por pipes, encerrada pela linha fixa dos Totais
        # Aproximados dos Tributos (Nota 10).
        info_compl = serv.find(f"{URL}infoCompl") if serv is not None else None
        segments = []

        def add_segment(label, value):
            if value:
                segments.append(f"{label} {value}")

        add_segment("Inf. Cont.:", _node_text(info_compl, "xInfComp"))
        add_segment("NFS-e Subst.:", extract_text(dps, "chSubstda"))
        add_segment("Doc. Ref.:", _node_text(info_compl, "docRef"))
        add_segment("Cod. Obra:", extract_text(serv, "cObra"))
        add_segment("Insc. Imob.:", _node_text(dps_ibscbs, "inscImobFisc"))
        add_segment("Cod. Evt.:", extract_text(serv, "idAtvEvt"))
        add_segment("Doc. Tec.:", _node_text(info_compl, "idDocTec"))
        add_segment("Núm. Ped.:", _node_text(info_compl, "xPed"))
        if info_compl is not None:
            itens_ped = [
                el.text for el in info_compl.findall(f"{URL}xItemPed") if el.text
            ]
            add_segment("Item Ped.:", "; ".join(itens_ped))
        add_segment("Inf. A. T. Mun.:", extract_text(inf_nfse, "xOutInf"))

        def tax_total(value, pct):
            if value:
                return f"R$ {format_number(value, self.price_precision)}"
            if pct:
                return f"{format_number(pct, self.price_precision)}%"
            return "-"

        approx_taxes = (
            "Totais Aproximados dos Tributos cfe. Lei nº 12.741/2012: "
            f"Federais: {tax_total(_fed_tax, _fed_tax_pct)} ; "
            f"Estaduais: {tax_total(_est_tax, _est_tax_pct)} ; "
            f"Municipais: {tax_total(_mun_tax, _mun_tax_pct)}"
        )
        data["complementary_info"] = {
            "segments": segments,
            "approx_taxes": approx_taxes,
        }
        return data

    # ------------------------------------------------------------------
    # Primitivas de desenho
    # ------------------------------------------------------------------
    def _col(self, index):
        return self.bx + index * self.colw

    def _hline(self, y):
        self.set_dash_pattern(dash=0, gap=0)
        self.set_line_width(LINE_DIVIDER)
        self.line(x1=self.bx, y1=y, x2=self.bx + self.bw, y2=y)

    def _shade(self, x, y, w, h):
        self.set_fill_color(SHADE_GRAY, SHADE_GRAY, SHADE_GRAY)
        self.rect(x=x, y=y, w=w, h=h, style="F")

    def _block_title(self, y, text):
        self._shade(self._col(0), y, self.colw, ROW_H)
        self.set_font(self.default_font, "B", 7)
        self.set_xy(self._col(0) + 0.8, y)
        self.cell(w=self.colw - 1.6, h=ROW_H, text=text, align="L")

    def _title_strip(self, text):
        y = self.get_y()
        h = STRIP_H + 0.5
        self._shade(self.bx, y, self.bw, h)
        self.set_font(self.default_font, "B", 7)
        self.set_xy(self.bx + 0.8, y)
        self.cell(w=self.bw - 1.6, h=h, text=text, align="L")
        self.set_y(y + h)

    def _field(self, col, span, y, label, value, shaded=False):
        x = self._col(col)
        w = span * self.colw
        if shaded:
            self._shade(x, y, w, ROW_H)
        self.set_font(self.default_font, "B", 6)
        self.set_xy(x + 0.8, y + 0.5)
        self.cell(
            w=w - 1.6,
            h=2.2,
            text=self.long_field(text=label, limit=w - 1.6),
            align="L",
        )
        self.set_font(self.default_font, "", 7)
        self.set_xy(x + 0.8, y + 3.0)
        self.cell(
            w=w - 1.6,
            h=2.6,
            text=self.long_field(text=value or "-", limit=w - 1.6),
            align="L",
        )

    def _strip(self, text):
        y = self.get_y()
        self.set_font(self.default_font, "B", 7)
        self.set_xy(self.bx, y)
        self.cell(w=self.bw, h=STRIP_H, text=text, align="C")
        self.set_y(y + STRIP_H)
        self._hline(self.get_y())

    def _person_rows(self, title, person, inscricao=True):
        y = self.get_y()
        self._block_title(y, title)
        self._field(1, 1, y, "CNPJ / CPF / NIF", person["id"])
        if inscricao:
            self._field(
                2,
                1,
                y,
                "Indicador Municipal (Inscrição)",
                person["municipal_registration"],
            )
        self._field(3, 1, y, "Telefone", person["phone"])
        y += ROW_H
        self._field(0, 2, y, "Nome / Nome Empresarial", person["name"])
        self._field(2, 1, y, "Município / Sigla UF", person["city"])
        self._field(3, 1, y, "Código IBGE / CEP", person["ibge_cep"])
        y += ROW_H
        self._field(0, 2, y, "Endereço", person["address"])
        self._field(2, 2, y, "E-mail", person["email"])
        y += ROW_H
        self.set_y(y)
        self._hline(y)

    # ------------------------------------------------------------------
    # Blocos
    # ------------------------------------------------------------------
    def _draw_watermark(self):
        if self.watermark_cancelled:
            watermark_text = "CANCELADA"
        elif self.watermark_replaced:
            watermark_text = "SUBSTITUÍDA"
        else:
            return
        # NT 008/2026, §2.5: diagonal, formato normal, mínimo 50pt, Arial
        # (Helvetica como equivalente métrico), cinza K35 — obtido com preto
        # a 35% de opacidade, que sobre o papel equivale ao K35 e mantém o
        # conteúdo legível sob a marca d'água.
        font_size = 60
        self.set_font("Helvetica", "", font_size)
        width = self.get_string_width(watermark_text)
        height = font_size * 0.25
        x_center = (self.w - width) / 2
        y_center = (self.h + height) / 2
        with self.local_context(fill_opacity=0.35), self.rotation(
            55, x_center + (width / 2), y_center - (height / 2)
        ):
            self.text(x_center, y_center, watermark_text)

    def _draw_header(self):
        y0 = self.t_margin + 1
        band_h = 11.6
        self._shade(self.bx, y0, self.bw, band_h)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "nfse_logo.png")
        self.image(logo_path, x=self.bx + 2, y=y0 + 1.8, h=8)

        self.set_font(self.default_font, "B", 9)
        self.set_xy(self._col(1), y0 + 1.6)
        self.multi_cell(
            w=self.colw * 2,
            h=3.6,
            text="DANFSe v2.0\nDocumento Auxiliar da NFS-e",
            align="C",
        )
        if self.data["environment"] == "2":
            self.set_font(self.default_font, "B", 9)
            self.set_text_color(255, 0, 0)
            self.set_xy(self._col(1), y0 + 8.8)
            self.cell(w=self.colw * 2, h=2.6, text=TXT_NO_LEGAL_VALIDITY, align="C")
            self.set_text_color(0, 0, 0)

        header = self.data["header"]
        x_right = self._col(3) + 0.8
        w_right = self.colw - 1.6
        if header["city"]:
            self.set_font(self.default_font, "", 8)
            self.set_xy(x_right, y0 + 1.2)
            self.cell(
                w=w_right,
                h=3,
                text=self.long_field(
                    text=f"Município: {header['city']}", limit=w_right
                ),
                align="L",
            )
        self.set_font(self.default_font, "", 6)
        self.set_xy(x_right, y0 + 6.4)
        self.cell(
            w=w_right,
            h=2.2,
            text=f"Ambiente Gerador: {header['amb_ger']}",
            align="L",
        )
        self.set_xy(x_right, y0 + 9.0)
        self.cell(
            w=w_right,
            h=2.2,
            text=f"Tipo de Ambiente: {header['tp_amb']}",
            align="L",
        )

        self.set_y(y0 + band_h)
        self._hline(self.get_y())

    def _id_field(self, col, y, label, value, shaded=False):
        x = self._col(col)
        w = self.colw
        if shaded:
            self._shade(x, y, w, 6.9)
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x + 0.8, y + 0.6)
        self.cell(
            w=w - 1.6,
            h=2.4,
            text=self.long_field(text=label, limit=w - 1.6),
            align="L",
        )
        self.set_font(self.default_font, "", 7)
        self.set_xy(x + 0.8, y + 3.6)
        self.cell(
            w=w - 1.6,
            h=2.8,
            text=self.long_field(text=value or "-", limit=w - 1.6),
            align="L",
        )

    def _draw_identification(self):
        data = self.data
        y0 = self.get_y()

        # Chave de acesso (linha de largura ampla)
        self.set_font(self.default_font, "B", 7)
        self.set_xy(self.bx + 0.8, y0 + 0.8)
        self.cell(w=self.colw * 3, h=2.4, text="CHAVE DE ACESSO DA NFS-e", align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(self.bx + 0.8, y0 + 3.8)
        self.cell(w=self.colw * 3, h=2.8, text=data["key_nfse"], align="L")

        rows_y = y0 + 7.9
        self._id_field(0, rows_y, "NÚMERO DA NFS-e", data["nfse_number"])
        self._id_field(1, rows_y, "COMPETÊNCIA DA NFS-e", data["compet_fmt"])
        self._id_field(
            2,
            rows_y,
            "DATA E HORA DA EMISSÃO DA NFS-e",
            f"{data['dt_nfse']} {data['hr_nfse']}".strip(),
        )
        rows_y += 6.9
        self._id_field(0, rows_y, "NÚMERO DA DPS", data["dps_number"])
        self._id_field(1, rows_y, "SÉRIE DA DPS", data["dps_serie"])
        self._id_field(
            2,
            rows_y,
            "DATA E HORA DA EMISSÃO DA DPS",
            f"{data['dt_dps']} {data['hr_dps']}".strip(),
        )
        rows_y += 6.9
        self._id_field(0, rows_y, "EMITENTE DA NFS-e", data["emitter_type"], True)
        self._id_field(1, rows_y, "SITUAÇÃO DA NFS-e", data["status"])
        self._id_field(2, rows_y, "FINALIDADE", data["purpose"])

        # QR Code (item 2.4.3: área útil mínima de 1,52 x 1,52 cm)
        qr_url = (
            "https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave="
            f"{data['key_nfse']}"
        )
        # Posição fixa do §2.4.3 (X=17,48 / Y=1,67 cm para a área útil),
        # independente das margens configuradas.
        draw_qr_code(
            self,
            qr_url,
            0,
            172.87,
            14.77 - self.t_margin,
            box_size=19,
            border=2,
        )
        self.set_font(self.default_font, "", 6)
        self.set_xy(158, 34.3)
        self.multi_cell(w=49, h=2.1, text=TXT_QR_CODE, align="L")

        self.set_y(rows_y + 6.9)
        self._hline(self.get_y())

    def _draw_provider(self):
        issuer = self.data["issuer"]
        y = self.get_y()
        self._block_title(y, "PRESTADOR / FORNECEDOR")
        self._field(1, 1, y, "CNPJ / CPF / NIF", issuer["id"])
        self._field(
            2,
            1,
            y,
            "Indicador Municipal (Inscrição)",
            issuer["municipal_registration"],
        )
        self._field(3, 1, y, "Telefone", issuer["phone"])
        y += ROW_H
        self._field(0, 2, y, "Nome / Nome Empresarial", issuer["name"])
        self._field(2, 1, y, "Município / Sigla UF", issuer["city"])
        self._field(3, 1, y, "Código IBGE / CEP", issuer["ibge_cep"])
        y += ROW_H
        self._field(0, 2, y, "Endereço", issuer["address"])
        self._field(2, 2, y, "E-mail", issuer["email"])
        y += ROW_H
        self._field(
            0, 2, y, "Simples Nacional na Data de Competência", issuer["simples"]
        )
        self._field(
            2, 2, y, "Regime de Apuração Tributária pelo SN", issuer["tax_regim"]
        )
        y += ROW_H
        self.set_y(y)
        self._hline(y)

    def _draw_taker(self):
        taker = self.data["taker"]
        if taker is None:
            self._strip(TXT_TAKER_NOT_IDENTIFIED)
            return
        self._person_rows("TOMADOR / ADQUIRENTE", taker)

    def _draw_dest(self):
        dest = self.data["dest"]
        if dest is None:
            # O grupo IBSCBS/dest só é informado quando o destinatário
            # difere do tomador (Notas 2 e 3 da NT 008/2026).
            if self.data["taker"] is not None:
                self._strip(TXT_DEST_IS_TAKER)
            else:
                self._strip(TXT_DEST_NOT_IDENTIFIED)
            return
        self._person_rows("DESTINATÁRIO DA OPERAÇÃO", dest, inscricao=False)

    def _draw_intermediary(self):
        intermed = self.data["intermed"]
        if intermed is None:
            self._strip(TXT_INTERM_NOT_IDENTIFIED)
            return
        self._person_rows("INTERMEDIÁRIO DA OPERAÇÃO", intermed)

    def _draw_service(self):
        service = self.data["service"]
        y = self.get_y()
        self._block_title(y, "SERVIÇO PRESTADO")
        self._field(
            1,
            1,
            y,
            "Código de Tributação Nacional / Municipal",
            service["tax_code"],
        )
        self._field(2, 1, y, "Código da NBS", service["nbs"])
        self._field(
            3,
            1,
            y,
            "Local da Prestação / Sigla UF / País",
            service["place_of_provision"],
        )
        y += ROW_H

        # Descrição do código de tributação (sem label, cf. tabela 2.4.5)
        self.set_font(self.default_font, "", 7)
        self.set_xy(self.bx + 0.8, y + 0.5)
        self.cell(
            w=self.bw - 1.6,
            h=2.8,
            text=self.long_field(
                text=service["tax_code_description"] or "-", limit=self.bw - 1.6
            ),
            align="L",
        )
        y += 3.8

        self.set_font(self.default_font, "B", 6)
        self.set_xy(self.bx + 0.8, y + 0.5)
        self.cell(w=self.bw - 1.6, h=2.2, text="Descrição do Serviço", align="L")

        # A descrição pode ter múltiplas linhas; limitar à altura disponível
        # para preservar a página única (NT 008/2026, §2.2).
        self.set_font(self.default_font, "", 7)
        description = service["description"]
        available = (
            self.t_margin + self.eph - self._reserved_below_service() - (y + 3.0)
        )
        max_lines = max(int(available // 2.6), 1)
        lines = self.multi_cell(
            w=self.bw - 1.6,
            h=2.6,
            text=description,
            align="L",
            dry_run=True,
            output="LINES",
        )
        if len(lines) > max_lines:
            kept = lines[:max_lines]
            kept[-1] = f"{kept[-1][: max(len(kept[-1]) - 4, 0)]}..."
            description = "\n".join(kept)
        self.set_xy(self.bx + 0.8, y + 3.0)
        self.multi_cell(w=self.bw - 1.6, h=2.6, text=description, align="L")
        y = max(self.get_y(), y + 5.6) + 0.6
        self.set_y(y)
        self._hline(y)

    def _reserved_below_service(self):
        """Altura mínima dos blocos abaixo de SERVIÇO PRESTADO."""
        height = 0.0
        if self.data["municipal_taxes"]["suppressed"]:
            height += STRIP_H
        else:
            height += STRIP_H + 0.5 + 4 * ROW_H
        height += ROW_H  # tributação federal, linha 1
        if self.data["federal_taxes"]["show_pis_cofins"]:
            height += ROW_H
        height += 4 * ROW_H  # tributação IBS/CBS
        height += 2 * ROW_H  # valor total
        height += STRIP_H + 0.5 + 6.0  # inf. complementares (título + mínimo)
        if self.display_canhoto:
            height += 6.9
        return height + 1.0

    def _draw_municipal_taxes(self):
        taxes = self.data["municipal_taxes"]
        if taxes["suppressed"]:
            self._strip(TXT_NO_ISSQN)
            return
        self._title_strip("TRIBUTAÇÃO MUNICIPAL (ISSQN)")
        y = self.get_y()
        self._field(0, 1, y, "Tipo de Tributação do ISSQN", taxes["issqn_tax"])
        self._field(
            1,
            2,
            y,
            "Município / Sigla UF / País da Incidência do ISSQN",
            taxes["city"],
        )
        y += ROW_H
        self._field(
            0,
            1,
            y,
            "Regime Especial de Tributação do ISSQN",
            taxes["special_tax_regim"],
        )
        self._field(1, 1, y, "Tipo de Imunidade do ISSQN", taxes["immunity_type"])
        self._field(
            2, 1, y, "Suspensão da Exigibilidade do ISSQN", taxes["suspension_issqn"]
        )
        self._field(3, 1, y, "Número Processo Suspensão", taxes["suspension_number"])
        y += ROW_H
        self._field(0, 1, y, "Benefício Municipal", taxes["municipal_benefit"])
        self._field(1, 1, y, "Cálculo do BM", taxes["municipal_benefit_math"])
        self._field(2, 1, y, "Total Deduções/Reduções", taxes["deduct_reduc_amount"])
        self._field(3, 1, y, "Desconto Incondicionado", taxes["discount_unconditioned"])
        y += ROW_H
        self._field(0, 1, y, "BC ISSQN", taxes["calculation_basis"])
        self._field(1, 1, y, "Alíquota Aplicada", taxes["aliq_applied"])
        self._field(2, 1, y, "Retenção do ISSQN", taxes["issqn_retention"])
        self._field(3, 1, y, "ISSQN Apurado", taxes["issqn_cleared"])
        y += ROW_H
        self.set_y(y)
        self._hline(y)

    def _draw_federal_taxes(self):
        taxes = self.data["federal_taxes"]
        y = self.get_y()
        self._block_title(y, "TRIBUTAÇÃO FEDERAL (EXCETO CBS)")
        self._field(1, 1, y, "IRRF", taxes["irrf"])
        self._field(
            2,
            1,
            y,
            "Contribuição Previdenciária - Retida",
            taxes["previdenciary_contribution"],
        )
        self._field(
            3, 1, y, "Contribuições Sociais - Retidas", taxes["social_contribution"]
        )
        y += ROW_H
        if taxes["show_pis_cofins"]:
            self._field(0, 1, y, "PIS - Débito Apuração Própria", taxes["pis_debit"])
            self._field(
                1, 1, y, "COFINS - Débito Apuração Própria", taxes["cofins_debit"]
            )
            self._field(
                2,
                2,
                y,
                "Descrição Contrib. Sociais - Retidas",
                taxes["social_description"],
            )
            y += ROW_H
        self.set_y(y)
        self._hline(y)

    def _draw_ibscbs_taxes(self):
        ibscbs = self.data["ibscbs"]
        y = self.get_y()
        self._block_title(y, "TRIBUTAÇÃO IBS / CBS")
        self._field(1, 1, y, "CST / CCLASSTRIB", ibscbs["cst_cclasstrib"])
        self._field(
            2,
            2,
            y,
            "Indicador de Operação / Código IBGE Incidência / "
            "Município Incidência / Sigla UF",
            ibscbs["ind_op"],
        )
        y += ROW_H
        self._field(
            0, 1, y, "Exclusões e Reduções da Base de Cálculo", ibscbs["exclusions"]
        )
        self._field(
            1, 1, y, "Base de Cálculo Após Exclusões e Reduções", ibscbs["bc_after"]
        )
        self._field(
            2, 1, y, "Red. Alíquota IBS / Red. Alíquota CBS", ibscbs["red_aliq"]
        )
        self._field(3, 1, y, "Alíquota - IBS UF / IBS Mun", ibscbs["aliq_ibs"])
        y += ROW_H
        self._field(0, 1, y, "Alíq. Efetiva Municipal - IBS", ibscbs["aliq_efet_mun"])
        self._field(1, 1, y, "Valor Apurado Municipal - IBS", ibscbs["v_ibs_mun"])
        self._field(2, 1, y, "Alíq. Efetiva Estadual - IBS", ibscbs["aliq_efet_uf"])
        self._field(3, 1, y, "Valor Apurado Estadual - IBS", ibscbs["v_ibs_uf"])
        y += ROW_H
        self._field(0, 1, y, "Valor Total Apurado - IBS", ibscbs["v_ibs_tot"])
        self._field(1, 1, y, "Alíquota - CBS", ibscbs["aliq_cbs"])
        self._field(2, 1, y, "Alíquota Efetiva - CBS", ibscbs["aliq_efet_cbs"])
        self._field(3, 1, y, "Valor Total Apurado - CBS", ibscbs["v_cbs"])
        y += ROW_H
        self.set_y(y)
        self._hline(y)

    def _draw_totals(self):
        totals = self.data["total_value"]
        y = self.get_y()
        self._block_title(y, "VALOR TOTAL DA NFS-E")
        self._field(1, 1, y, "Valor da Operação / Serviço", totals["service_amount"])
        self._field(
            2, 1, y, "Desconto Incondicionado", totals["discount_unconditioned"]
        )
        self._field(3, 1, y, "Desconto Condicionado", totals["discount_conditioned"])
        y += ROW_H
        self._field(
            0,
            1,
            y,
            "Total das Retenções (ISSQN / Federais)",
            totals["total_retentions"],
        )
        self._field(1, 1, y, "Valor Líquido da NFS-e", totals["net_value"])
        self._field(2, 1, y, "Total do IBS/CBS", totals["total_ibscbs"])
        self._field(
            3,
            1,
            y,
            "Valor Líquido da NFS-e + IBS/CBS",
            totals["net_value_ibscbs"],
            shaded=True,
        )
        y += ROW_H
        self.set_y(y)
        self._hline(y)

    def _draw_complementary_info(self):
        info = self.data["complementary_info"]
        bottom = self.t_margin + self.eph
        if self.display_canhoto:
            bottom -= 6.9
        self._title_strip("INFORMAÇÕES COMPLEMENTARES")
        y = self.get_y()

        # O bloco absorve a altura restante da página (§2.3 da NT 008/2026);
        # o conteúdo variável é truncado com reticências para preservar a
        # linha fixa dos Totais Aproximados e a página única.
        self.set_font(self.default_font, "", 7)
        available = bottom - y - 1.0
        max_lines = max(int(available // 2.6), 1)
        var_limit = 1997
        while True:
            variable = ellipsize(" | ".join(info["segments"]), var_limit)
            text = (
                f"{variable} | {info['approx_taxes']}"
                if variable
                else info["approx_taxes"]
            )
            lines = self.multi_cell(
                w=self.bw - 1.6,
                h=2.6,
                text=text,
                align="L",
                dry_run=True,
                output="LINES",
            )
            if len(lines) <= max_lines or var_limit <= 100:
                break
            var_limit = max(var_limit - 200, 100)

        self.set_xy(self.bx + 0.8, y + 0.5)
        self.multi_cell(w=self.bw - 1.6, h=2.6, text=text, align="L")
        self.set_y(bottom)
        if self.display_canhoto:
            self._hline(bottom)

    def _draw_canhoto(self):
        if not self.display_canhoto:
            return
        data = self.data
        y = self.get_y()
        self.set_font(self.default_font, "B", 6)
        self.set_xy(self._col(0) + 0.8, y + 0.6)
        self.cell(w=self.colw - 1.6, h=2.2, text="DATA CIENTIFICAÇÃO", align="L")
        self.set_xy(self._col(1) + 0.8, y + 0.6)
        self.cell(
            w=self.colw - 1.6, h=2.2, text="IDENTIFICAÇÃO E ASSINATURA", align="L"
        )
        self.set_xy(self._col(2) + 0.8, y + 0.6)
        self.cell(
            w=self.colw * 2 - 1.6, h=2.2, text="Nº NFS-E / CHAVE NFS-E", align="L"
        )
        self.set_font(self.default_font, "", 7)
        self.set_xy(self._col(2) + 0.8, y + 3.4)
        self.cell(
            w=self.colw * 2 - 1.6,
            h=2.8,
            text=f"{data['nfse_number']} / {data['key_nfse']}",
            align="L",
        )
