import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from ..dacte.generate_qrcode import draw_qr_code
from ..utils import (
    format_cep,
    format_cpf_cnpj,
    format_number,
    format_phone,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DanfseConfig
from .danfse_conf import URL


def extract_text(node: Element, tag: str) -> str:
    return get_tag_text(node, URL, tag)


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
        self.root = ET.fromstring(xml)
        self.add_page(self.orientation)
        self.data = self._parse_xml()
        self._draw_void_watermark()
        self._draw_header()
        self._draw_issuer()
        self._draw_taker()
        self._draw_service_provided()
        self._draw_taxes()
        self._draw_amount()
        self._draw_complementary_info()

        self.set_dash_pattern(dash=0, gap=0)
        self.rect(x=self.l_margin, y=self.t_margin, w=self.epw, h=self.eph)

    def _parse_xml(self):
        """Centralize all XML tags here."""

        def get_val(node, tag):
            return extract_text(node, tag) if node is not None else ""

        def format_address(tag):
            address_fields = [
                extract_text(tag, "xLgr"),
                extract_text(tag, "nro"),
                extract_text(tag, "xCpl"),
                extract_text(tag, "xBairro"),
            ]
            address_formated = ", ".join(
                [str(c) for c in address_fields if c and str(c).strip()]
            )
            return address_formated

        inf_nfse = self.root.find(f"{URL}infNFSe")
        dps = self.root.find(f"{URL}DPS")
        emit = self.root.find(f"{URL}emit")
        enderNac = emit.find(f"{URL}enderNac")
        prest = dps.find(f"{URL}prest")
        regTrib = prest.find(f"{URL}regTrib")
        serv = dps.find(f"{URL}serv")
        valores = self.root.find(f"{URL}valores")

        compet = extract_text(dps, "dCompet")
        compet, hr = get_date_utc(compet)
        dt_nfse, hr_nfse = get_date_utc(extract_text(inf_nfse, "dhProc"))
        dt_dps, hr_dps = get_date_utc(extract_text(dps, "dhEmi"))

        simples_op = {
            "1": "Não Optante",
            "2": "Optante - Microempreendedor Individual (MEI)",
            "3": "Optante - Microempresa ou Empresa de Pequeno Porte (ME/EPP)",
        }
        opSimpNac = extract_text(regTrib, "opSimpNac")
        simples = simples_op.get(opSimpNac, "Não Optante")

        tax_regim_op = {
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
        reg_ap_trib = extract_text(regTrib, "regApTribSN")
        tax_regim = tax_regim_op.get(reg_ap_trib, "")

        special_tax_type = {
            "0": "Nenhum",
            "1": "Ato Cooperado (Cooperativa)",
            "2": "Estimativa",
            "3": "Microempresa Municipal",
            "4": "Notário ou Registrador",
            "5": "Profissional Autônomo",
            "6": "Sociedade de Profissionais",
            "9": "Outros",
        }
        reg_esp_trib = extract_text(regTrib, "regEspTrib")
        special_tax_regim = special_tax_type.get(reg_esp_trib, "Nenhum")

        description = extract_text(serv, "xDescServ") or ""

        if " - " in description:
            parts = description.split(" - ", 1)
            format_description = parts[1].strip()
        else:
            format_description = description.strip()

        national_tax = extract_text(serv, "cTribNac")
        if len(national_tax) >= 6:
            national_tax_formated = (
                f"{national_tax[:2]}.{national_tax[2:4]}.{national_tax[4:]}"
            )
        else:
            national_tax_formated = national_tax

        national_tax_code = f"{national_tax_formated} - {format_description}"

        issqn_tax = {
            "1": "Operação Tributável",
            "2": "Imunidade",
            "3": "Exportação de serviço",
            "4": "Não Incidência",
        }
        trib_issqn = extract_text(dps, "tribISSQN")
        issqn = issqn_tax.get(trib_issqn, "Operação Tributável")

        issqn_retention_type = {
            "1": "Não Retido",
            "2": "Retido pelo Tomador",
            "3": "Retido pelo Intermediario",
        }
        issqn_type = extract_text(dps, "tpRetISSQN")
        issqn_type_val = issqn_retention_type.get(issqn_type)

        issqn_value = extract_text(valores, "vISSQN")
        issqn_retained = issqn_value if issqn_type_val in ["2", "3"] else 0

        total_federal_retentions = 0
        total_retentions = extract_text(valores, "vTotalRet")
        if total_retentions:
            total_federal_retentions = float(total_retentions) - float(
                issqn_retained or 0
            )
            total_federal_retentions = (
                f"R$ {format_number(total_federal_retentions, self.price_precision)}"
            )

        _bc = format_number(extract_text(valores, "vBC"), self.price_precision)
        _aliq_val = extract_text(valores, "pAliqAplic")
        _vserv = format_number(extract_text(dps, "vServ"), self.price_precision)
        _issqn_ret = format_number(issqn_retained, self.price_precision)
        _vliq = format_number(extract_text(valores, "vLiq"), self.price_precision)
        _fed_tax = extract_text(dps, "vTotTribFed")
        _est_tax = extract_text(dps, "vTotTribEst")
        _mun_tax = extract_text(dps, "vTotTribMun")
        _issqn_clear = format_number(issqn_value, self.price_precision)
        _vdesc_inc = format_number(
            extract_text(dps, "vDescIncond"), self.price_precision
        )
        _vdesc_cond = format_number(
            extract_text(dps, "vDescCond"), self.price_precision
        )

        data = {
            "environment": extract_text(dps, "tpAmb"),
            "key_nfse": inf_nfse.attrib.get("Id")[3:],
            "nfse_number": get_val(inf_nfse, "nNFSe"),
            "compet": compet,
            "dt_nfse": dt_nfse,
            "hr_nfse": hr_nfse,
            "dt_dps": dt_dps,
            "hr_dps": hr_dps,
            "dps_number": extract_text(dps, "nDPS"),
            "dps_serie": extract_text(dps, "serie"),
            "issuer": {
                "id": format_cpf_cnpj(extract_text(emit, "CNPJ"))
                or format_cpf_cnpj(extract_text(emit, "CPF")),
                "municipal_registration": extract_text(emit, "IM") or "-",
                "phone": format_phone(extract_text(emit, "fone")) or "-",
                "name": extract_text(emit, "xNome")
                or extract_text(emit, "xFant")
                or "-",
                "email": extract_text(emit, "email") or "-",
                "address": format_address(enderNac),
                "city": (
                    f"{extract_text(inf_nfse, 'xLocEmi')} - "
                    f"{extract_text(emit, 'UF')}"
                ),
                "cep": format_cep(extract_text(enderNac, "CEP")),
                "simples": simples,
                "tax_regim": tax_regim if simples == "3" else "-",
            },
            "service": {
                "national_tax_code": national_tax_code,
                "municipal_tax_code": extract_text(serv, "cTribMun") or "-",
                "place_of_provision": extract_text(serv, "cLocPrestacao") or "-",
                "country": extract_text(serv, "cPaisPrestacao") or "-",
                "description": description,
            },
            "municipal_taxes": {
                "issqn_tax": issqn,
                "country": extract_text(dps, "cPaisResult") or "-",
                "city": (
                    f"{extract_text(inf_nfse, 'cLocIncid')} - "
                    f"{extract_text(emit, 'UF')}"
                    or "Nenhum"
                ),
                "special_tax_regim": special_tax_regim,
                "immunity_type": extract_text(dps, "tpImunidade") or "-",
                "suspension_issqn": "Não",
                "suspension_number": "-",
                "municipal_benefit": "-",
                "service_amount": f"R$ {_vserv}",
                "discount_unconditioned": "-",
                "deduct_reduc_amount": "-",
                "municipal_benefit_math": "-",
                "calculation_basis": f"R$ {_bc}",
                "aliq_applied": f"{format_number(_aliq_val, self.price_precision)}%"
                if _aliq_val
                else "-",
                "issqn_retention": issqn_retention_type[issqn_type],
                "issqn_cleared": f"R$ {_issqn_clear}"
                if issqn_type == "1"
                else f"R$ {format_number(0, self.price_precision)}",
            },
            "total_value": {
                "service_amount": f"R$ {_vserv}",
                "discount_conditioned": "-",
                "discount_unconditioned": "-",
                "issqn_retained": f"R$ {_issqn_ret}",
                "total_federal_retentions": total_federal_retentions
                if total_federal_retentions
                else f"R$ {format_number(0, self.price_precision)}",
                "pis_cofins_debit": "-",
                "net_value": f"R$ {_vliq}",
            },
            "taxes_amount": {
                "federal_tax": f"R$ {format_number(_fed_tax, self.price_precision)}"
                if _fed_tax
                else "-",
                "state_tax": f"R$ {format_number(_est_tax, self.price_precision)}"
                if _est_tax
                else "-",
                "municipal_tax": f"R$ {format_number(_mun_tax, self.price_precision)}"
                if _mun_tax
                else "-",
            },
        }

        toma = dps.find(f"{URL}toma")
        if toma is not None:
            data["taker"] = {
                "id": format_cpf_cnpj(extract_text(toma, "CNPJ"))
                or format_cpf_cnpj(extract_text(toma, "CPF")),
                "municipal_registration": extract_text(toma, "IM") or "-",
                "phone": format_phone(extract_text(toma, "fone")) or "-",
                "name": extract_text(toma, "xNome"),
                "email": extract_text(toma, "email") or "-",
                "address": format_address(toma),
                "city": "-",
                "cep": format_cep(extract_text(toma, "CEP")),
            }
        else:
            data["taker"] = {
                "id": "-",
                "municipal_registration": "-",
                "phone": "-",
                "name": "-",
                "email": "-",
                "address": "-",
                "city": "-",
                "cep": "-",
            }

        intermed = dps.find(f"{URL}interm")
        if intermed is not None:
            data["intermed"] = {
                "id": format_cpf_cnpj(extract_text(intermed, "CNPJ"))
                or format_cpf_cnpj(extract_text(intermed, "CPF")),
                "municipal_registration": extract_text(intermed, "IM") or "-",
                "phone": extract_text(intermed, "phone") or "-",
                "name": extract_text(intermed, "xNome") or "-",
                "email": extract_text(intermed, "email") or "-",
                "address": format_address(intermed),
                "city": "",
                "cep": format_cep(extract_text(intermed, "CEP")),
            }
        else:
            data["intermed"] = {
                "id": "-",
                "municipal_registration": "-",
                "phone": "-",
                "name": "-",
                "email": "-",
                "address": "-",
                "city": "-",
                "cep": "-",
            }

        exigSusp = dps.find(f"{URL}exigSusp")
        if exigSusp is not None:
            issqn_suspension_exigibility = {
                "1": "Exigibilidade do ISSQN Suspensa por Decisão Judicial",
                "2": "Exigibilidade do ISSQN Suspensa por Processo Administrativo",
            }
            iss_susp = extract_text(exigSusp, "tpSusp")
            issqn_suspension = issqn_suspension_exigibility[iss_susp]

            data["municipal_taxes"]["suspension_issqn"] = issqn_suspension
            data["municipal_taxes"]["suspension_number"] = extract_text(
                exigSusp, "nProcesso"
            )

        bm = dps.find(f"{URL}BM")
        if bm is not None:
            data["municipal_taxes"]["municipal_benefit"] = extract_text(bm, "nBM")

        vDescCondIncond = dps.find(f"{URL}vDescCondIncond")
        if vDescCondIncond is not None:
            data["municipal_taxes"]["discount_unconditioned"] = f"R$ {_vdesc_inc}"
            data["total_value"]["discount_conditioned"] = f"R$ {_vdesc_cond}"

            data["total_value"]["discount_unconditioned"] = f"R$ {_vdesc_inc}"

        vDedRed = dps.find(f"{URL}vDedRed")
        if vDedRed is not None:
            data["municipal_taxes"]["deduct_reduc_amount"] = (
                f"R$ {format_number(extract_text(dps, 'vDR'), self.price_precision)}"
            )

        tribFed = dps.find(f"{URL}tribFed")
        if tribFed is not None:
            _vcp = extract_text(tribFed, "vRetCP") if tribFed else None
            _csll = extract_text(tribFed, "vRetCSLL") if tribFed else None
            data["federal_taxes"] = {
                "irrf": extract_text(tribFed, "vRetIRRF") or "-",
                "previdenciary_contribution": (
                    f"R$ {format_number(_vcp, self.price_precision)}" if _vcp else "-"
                ),
                "social_contribution": (
                    f"R$ {format_number(_csll, self.price_precision)}" if _csll else "-"
                ),
                "social_description": "-",
                "pis_debit": "-",
                "cofins_debit": "-",
            }

            piscofins = tribFed.find(f"{URL}piscofins")
            if piscofins is not None:
                pis = extract_text(piscofins, "vPis")
                cofins = extract_text(piscofins, "vCofins")
                pis_cofins_debit = float(pis) + float(cofins)
                data["federal_taxes"]["pis_debit"] = (
                    f"R$ {format_number(pis, self.price_precision)}"
                )
                data["federal_taxes"]["cofins_debit"] = (
                    f"R$ {format_number(cofins, self.price_precision)}"
                )
                data["total_value"]["pis_cofins_debit"] = (
                    f"R$ {format_number(pis_cofins_debit, self.price_precision)}"
                )
        else:
            data["federal_taxes"] = {
                "irrf": "-",
                "previdenciary_contribution": "-",
                "social_contribution": "-",
                "social_description": "-",
                "pis_debit": "-",
                "cofins_debit": "-",
            }

        infoCompl = serv.find(f"{URL}infoCompl")
        if infoCompl is not None:
            data["complementary_info"] = extract_text(infoCompl, "xInfComp") or "-"
        else:
            data["complementary_info"] = "-"
        return data

    def _draw_void_watermark(self):
        """
        Draw a watermark on the DANFSE when the protocol is not available or
        when the environment is homologation.
        """
        is_production_environment = self.data["environment"] == "1"
        watermark_text = None
        font_size = 60
        if self.watermark_cancelled:
            if is_production_environment:
                watermark_text = "CANCELADA"
            else:
                watermark_text = "CANCELADA - SEM VALOR FISCAL"
                font_size = 45

        elif not is_production_environment:
            watermark_text = "SEM VALOR FISCAL"

        if watermark_text:
            self.set_font(self.default_font, "B", font_size)

            width = self.get_string_width(watermark_text)
            self.set_text_color(r=220, g=150, b=150)
            height = font_size * 0.25
            page_width = self.w
            page_height = self.h
            x_center = (page_width - width) / 2
            y_center = (page_height + height) / 2
            with self.rotation(55, x_center + (width / 2), y_center - (height / 2)):
                self.text(x_center, y_center, watermark_text)
            self.set_text_color(r=0, g=0, b=0)

    def _draw_header(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        col_width = self.epw / 4
        section_start_y = y_margin + 12

        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "nfse_logo.png")
        self.image(logo_path, x=x_margin + 2, y=y_margin + 2, w=42)

        self.set_font(self.default_font, "B", 10)
        self.set_xy(x=x_margin, y=y_margin + 4)
        self.multi_cell(
            w=page_width,
            h=2.5,
            text="DANFSe v1.0\nDocumento Auxiliar da NFS-e",
            align="C",
        )

        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 13,
            x2=x_margin + page_width - 2,
            y2=y_margin + 13,
        )

        # Chave de Acesso da NFS-e
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 2)
        self.cell(w=col_width, h=3, text="Chave de Acesso da NFS-e", align="L")

        # Chave - VALOR
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 2)
        self.cell(w=col_width, h=8, text=self.data["key_nfse"], align="L")

        # Número da NFS-e
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 9)
        self.cell(w=col_width, h=3, text="Número da NFS-e", align="L")

        # Número da NF-se - VALOR
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 9)
        self.cell(w=col_width, h=8, text=self.data["nfse_number"], align="L")

        # Competência
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 9)
        self.cell(w=col_width, h=3, text="Competência da NFS-e", align="L")

        # Competência - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 9)
        self.cell(w=col_width, h=8, text=self.data["compet"], align="L")

        # Data e Hora da emissão da NFS-e
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 9)
        self.cell(w=col_width, h=3, text="Data e Hora da emissão da NFS-e", align="L")

        # Data e Hora da emissão da NFS-e - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 9)
        self.cell(
            w=col_width,
            h=8,
            text=f"{self.data['dt_nfse']} {self.data['hr_nfse']}",
            align="L",
        )

        # Número da DPS
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 16)
        self.cell(w=col_width, h=3, text="Número da DPS", align="L")

        # Número da DPS - VALOR
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 16)
        self.cell(w=col_width, h=8, text=self.data["dps_number"], align="L")

        # Serie da DPS
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 16)
        self.cell(w=col_width, h=3, text="Série da DPS", align="L")

        # Serie da DPS - VALOR
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 16)
        self.cell(w=col_width, h=8, text=self.data["dps_serie"], align="L")

        # Data e Hora da emissão da DPS
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 16)
        self.cell(w=col_width, h=3, text="Data e Hora da emissão da DPS", align="L")

        # Data e Hora da emissão da DPS -Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 16)
        self.cell(
            w=col_width,
            h=8,
            text=f"{self.data['dt_dps']} {self.data['hr_dps']}",
            align="L",
        )
        num_x = 170
        num_y = 13
        qr_code = f"https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave={self.data['key_nfse']}"
        draw_qr_code(self, qr_code, 0, num_x, num_y, box_size=15, border=3)

        self.set_font(self.default_font, "", 7)

        self.set_xy(x=x_margin + (col_width * 3) - 2, y=section_start_y + 18)
        text = (
            "A autenticidade desta NFS-e pode ser verificada pela leitura "
            "deste código QR ou pela consulta da chave de acesso no portal "
            "nacional da NFS-e"
        )
        self.multi_cell(w=col_width, h=3, text=text, align="L")

        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 40,
            x2=x_margin + page_width - 2,
            y2=y_margin + 40,
        )

    def _draw_issuer(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        col_width = self.epw / 4
        section_start_y = y_margin + 2

        # EMITENTE DA NFS-e
        self.set_font(self.default_font, "B", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=col_width, h=3, text="EMITENTE DA NFS-e", align="L")

        # Prestador do Servico
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=col_width, h=8, text="Prestador do Serviço", align="L")

        # CNPJ / CPF / NIF
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y)
        self.cell(w=col_width, h=2, text="CNPJ / CPF / NIF", align="L")

        # CNPJ / CPF / NIF - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["id"], align="L")

        # Inscrição Municipal
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y)
        self.cell(w=col_width, h=2, text="Inscrição Municipal", align="L")

        # Inscrição Municipal - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y)
        self.cell(
            w=col_width,
            h=7,
            text=self.data["issuer"]["municipal_registration"],
            align="L",
        )

        # Telefone
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y)
        self.cell(w=col_width, h=2, text="Telefone", align="L")

        # Telefone - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["phone"], align="L")

        # Nome / Nome Empresarial
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 7)
        self.cell(w=col_width, h=2, text="Nome / Nome Empresarial", align="L")

        # Nome / Nome Empresarial - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 7)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["name"], align="L")

        # E-mail
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 7)
        self.cell(w=col_width, h=2, text="E-mail", align="L")

        # E-mail - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 7)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["email"], align="L")

        # Endereço
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 14)
        self.cell(w=col_width, h=2, text="Endereço", align="L")

        # Endereço - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 14)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["address"], align="L")

        # Município
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 14)
        self.cell(w=col_width, h=2, text="Município", align="L")

        # Município - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 14)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["city"], align="L")

        # CEP
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 14)
        self.cell(w=col_width, h=2, text="CEP", align="L")

        # CEP - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 14)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["cep"], align="L")

        # Simples Nacional na Data de Competência
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 21)
        self.cell(
            w=col_width, h=2, text="Simples Nacional na Data de Competência", align="L"
        )

        # Simples Nacional na Data de Competência - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 21)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["simples"], align="L")

        # Regime de Apuração Tributária pelo SN
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 21)
        self.cell(
            w=col_width, h=2, text="Regime de Apuração Tributária pelo SN", align="L"
        )

        # Regime de Apuração Tributária pelo SN - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 21)
        self.cell(w=col_width, h=7, text=self.data["issuer"]["tax_regim"], align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 30,
            x2=x_margin + page_width - 2,
            y2=y_margin + 30,
        )

    def _draw_taker(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        col_width = self.epw / 4
        section_start_y = y_margin + 9

        # TOMADOR DO SERVIÇO
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=col_width, h=1, text="TOMADOR DO SERVIÇO", align="L")

        # CNPJ / CPF / NIF
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y)
        self.cell(w=col_width, h=1, text="CNPJ / CPF / NIF", align="L")

        # CNPJ / CPF / NIF - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y)
        self.cell(w=col_width, h=7, text=self.data["taker"]["id"], align="L")

        # Inscrição Municipal
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y)
        self.cell(w=col_width, h=1, text="Inscrição Municipal", align="L")

        # Inscrição Municipal - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y)
        self.cell(
            w=col_width,
            h=7,
            text=self.data["taker"]["municipal_registration"],
            align="L",
        )

        # Telefone
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y)
        self.cell(w=col_width, h=1, text="Telefone", align="L")

        # Telefone - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y)
        self.cell(w=col_width, h=7, text=self.data["taker"]["phone"], align="L")

        # Nome / Nome Empresarial
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 6)
        self.cell(w=col_width, h=2, text="Nome / Nome Empresarial", align="L")

        # Nome / Nome Empresarial - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 6)
        self.cell(w=col_width, h=7, text=self.data["taker"]["name"], align="L")

        # E-mail
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 6)
        self.cell(w=col_width, h=2, text="E-mail", align="L")

        # E-mail - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 6)
        self.cell(w=col_width, h=7, text=self.data["taker"]["email"], align="L")

        # Endereço
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 13)
        self.cell(w=col_width, h=2, text="Endereço", align="L")

        # Endereço - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 13)
        self.cell(w=col_width, h=7, text=self.data["taker"]["address"], align="L")

        # Município
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 13)
        self.cell(w=col_width, h=2, text="Município", align="L")

        # Município - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 13)
        self.cell(w=col_width, h=7, text=self.data["taker"]["city"], align="L")

        # CEP
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 13)
        self.cell(w=col_width, h=2, text="CEP", align="L")

        # CEP - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 13)
        self.cell(w=col_width, h=7, text=self.data["taker"]["cep"], align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 28,
            x2=x_margin + page_width - 2,
            y2=y_margin + 28,
        )

        if self.data["intermed"]["id"]:
            self.set_font(self.default_font, "", 8)
            self.set_xy(x=x_margin + 3, y=section_start_y + 19)
            self.cell(
                w=0,
                h=3,
                text="INTERMEDIÁRIO DO SERVIÇO NÃO IDENTIFICADO NA NFS-e",
                align="C",
            )

        self.line(
            x1=x_margin + 2,
            y1=y_margin + 31,
            x2=x_margin + page_width - 2,
            y2=y_margin + 31,
        )

    def _draw_service_provided(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        col_width = self.epw / 4
        section_start_y = y_margin + 5

        # SERVIÇO PRESTADO
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=col_width, h=1, text="SERVIÇO PRESTADO", align="L")

        # Código de Tributação Nacional
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Código de Tributação Nacional", align="L")

        # Código de Tributação Nacional - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 7)
        self.multi_cell(
            w=col_width,
            h=2.5,
            text=self.long_field(
                text=self.data["service"]["national_tax_code"],
                limit=col_width,
            ),
            align="L",
        )

        # Código de Tributação Municipal
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Código de Tributação Municipal", align="L")

        # Código de Tributação Municipal - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["service"]["municipal_tax_code"], align="L"
        )

        # Local da Prestação
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Local da Prestação", align="L")

        # Local da Prestação - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["service"]["place_of_provision"], align="L"
        )

        # País da Prestação
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="País da Prestação", align="L")

        # País da Prestação - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 4)
        self.cell(w=col_width, h=8, text=self.data["service"]["country"], align="L")

        # Descrição do Serviço
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 14)
        self.cell(w=col_width, h=3, text="Descrição do Serviço", align="L")

        # Descrição do Serviço - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 14)
        self.cell(
            w=col_width,
            h=8,
            text=self.long_field(
                text=self.data["service"]["description"],
                limit=page_width,
            ),
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 25,
            x2=x_margin + page_width - 2,
            y2=y_margin + 25,
        )

    def _draw_taxes(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        col_width = self.epw / 4
        section_start_y = y_margin + 8

        # TRIBUTAÇÃO MUNICIPAL
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=col_width, h=1, text="TRIBUTAÇÃO MUNICIPAL", align="L")

        # Tributação do ISSQN
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Tributação do ISSQN", align="L")

        # Tributação do ISSQN - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["municipal_taxes"]["issqn_tax"], align="L"
        )

        # País Resultado da Prestação do Serviço
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 4)
        self.cell(
            w=col_width, h=3, text="País Resultado da Prestação do Serviço", align="L"
        )

        # País Resultado da Prestação do Serviço - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["municipal_taxes"]["country"], align="L"
        )

        # Município de Incidência do ISSQN
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Município de Incidência do ISSQN", align="L")

        # Município de Incidência do ISSQN - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["municipal_taxes"]["city"], align="L"
        )

        # Regime Especial de Tributação
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Regime Especial de Tributação", align="L")

        # Regime Especial de Tributação - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 4)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["special_tax_regim"],
            align="L",
        )

        # Tipo de Imunidade
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 11)
        self.cell(w=col_width, h=3, text="Tipo de Imunidade", align="L")

        # Tipo de Imunidade - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 11)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["immunity_type"],
            align="L",
        )

        # Suspensão da Exigibilidade do ISSQN
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 11)
        self.cell(
            w=col_width, h=3, text="Suspensão da Exigibilidade do ISSQN", align="L"
        )

        # Suspensão da Exigibilidade do ISSQN - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 11)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["suspension_issqn"],
            align="L",
        )

        # Número Processo Suspensão
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 11)
        self.cell(w=col_width, h=3, text="Número Processo Suspensão", align="L")

        # Número Processo Suspensão - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 11)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["suspension_number"],
            align="L",
        )

        # Benefício Municipal
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 11)
        self.cell(w=col_width, h=3, text="Benefício Municipal", align="L")

        # Benefício Municipal - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 11)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["municipal_benefit"],
            align="L",
        )

        # Valor do Serviço
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 18)
        self.cell(w=col_width, h=3, text="Valor do Serviço", align="L")

        # Valor do Serviço - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 18)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["service_amount"],
            align="L",
        )

        # Desconto Incondicionado
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 18)
        self.cell(w=col_width, h=3, text="Desconto Incondicionado", align="L")

        # Desconto Incondicionado - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 18)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["discount_unconditioned"],
            align="L",
        )

        # Total Deduções/Reduções
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 18)
        self.cell(w=col_width, h=3, text="Total Deduções/Reduções", align="L")

        # Total Deduções/Reduções - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 18)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["deduct_reduc_amount"],
            align="L",
        )

        # Cálculo do BM
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 18)
        self.cell(w=col_width, h=3, text="Cálculo do BM", align="L")

        # Cálculo do BM - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 18)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["municipal_benefit_math"],
            align="L",
        )

        # BC ISSQN
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="BC ISSQN", align="L")

        # BC ISSQN - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 25)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["calculation_basis"],
            align="L",
        )

        # Alíquota Aplicada
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="Alíquota Aplicada", align="L")

        # Alíquota Aplicada - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 25)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["aliq_applied"],
            align="L",
        )

        # Retenção do ISSQN
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="Retenção do ISSQN", align="L")

        # Retenção do ISSQN - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 25)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["issqn_retention"],
            align="L",
        )

        # ISSQN Apurado
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="ISSQN Apurado", align="L")

        # ISSQN Apurado - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 25)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["municipal_taxes"]["issqn_cleared"],
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 40,
            x2=x_margin + page_width - 2,
            y2=y_margin + 40,
        )

        # TRIBUTAÇÃO FEDERAL
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y + 34)
        self.cell(w=col_width, h=1, text="TRIBUTAÇÃO FEDERAL", align="L")

        # IRRF
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 37)
        self.cell(w=col_width, h=3, text="IRRF", align="L")

        # IRRF - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 37)
        self.cell(w=col_width, h=8, text=self.data["federal_taxes"]["irrf"], align="L")

        # Contribuição Previdenciária - Retida
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 37)
        self.cell(
            w=col_width, h=3, text="Contribuição Previdenciária - Retida", align="L"
        )

        # Contribuição Previdenciária - Retida - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 37)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["federal_taxes"]["previdenciary_contribution"],
            align="L",
        )

        # Contribuições Sociais - Retidas
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 37)
        self.cell(w=col_width, h=3, text="Contribuições Sociais - Retidas", align="L")

        # Contribuições Sociais - Retidas - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 37)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["federal_taxes"]["social_contribution"],
            align="L",
        )

        # Descrição Contrib. Sociais - Retidas
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 37)
        self.cell(
            w=col_width, h=3, text="Descrição Contrib. Sociais - Retidas", align="L"
        )

        # Descrição Contrib. Sociais - Retidas - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 37)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["federal_taxes"]["social_description"],
            align="L",
        )

        # PIS - Débito Apuração Própria
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 44)
        self.cell(w=col_width, h=3, text="PIS - Débito Apuração Própria", align="L")

        # PIS - Débito Apuração Própria - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 44)
        self.cell(
            w=col_width, h=8, text=self.data["federal_taxes"]["pis_debit"], align="L"
        )

        # COFINS - Débito Apuração Própria
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 44)
        self.cell(w=col_width, h=3, text="COFINS - Débito Apuração Própria", align="L")

        # COFINS - Débito Apuração Própria - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 44)
        self.cell(
            w=col_width, h=8, text=self.data["federal_taxes"]["cofins_debit"], align="L"
        )

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 59,
            x2=x_margin + page_width - 2,
            y2=y_margin + 59,
        )

    def _draw_amount(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        col_width = self.epw / 4
        section_start_y = y_margin + 9

        # VALOR TOTAL DA NFS-E
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=col_width, h=1, text="VALOR TOTAL DA NFS-E", align="L")

        # Valor do Serviço
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Valor do Serviço", align="L")

        # Valor do Serviço - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["total_value"]["service_amount"], align="L"
        )

        # Desconto Condicionado
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Desconto Condicionado", align="L")

        # Desconto Condicionado - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 4)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["total_value"]["discount_conditioned"],
            align="L",
        )

        # Desconto Incondicionado
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="Desconto Incondicionado", align="L")

        # Desconto Incondicionado - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 4)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["total_value"]["discount_unconditioned"],
            align="L",
        )

        # ISSQN Retido
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 4)
        self.cell(w=col_width, h=3, text="ISSQN Retido", align="L")

        # ISSQN Retido - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 4)
        self.cell(
            w=col_width, h=8, text=self.data["total_value"]["issqn_retained"], align="L"
        )

        # Total das Retenções Federais
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 11)
        self.cell(w=col_width, h=3, text="Total das Retenções Federais", align="L")

        # Total das Retenções Federais - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 11)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["total_value"]["total_federal_retentions"],
            align="L",
        )

        # PIS/COFINS - Débito Apur. Própria
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 11)
        self.cell(w=col_width, h=3, text="PIS/COFINS - Débito Apur. Própria", align="L")

        # PIS/COFINS - Débito Apur. Própria - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 11)
        self.cell(
            w=col_width,
            h=8,
            text=self.data["total_value"]["pis_cofins_debit"],
            align="L",
        )

        # Valor Líquido da NFS-e
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 11)
        self.cell(w=col_width, h=3, text="Valor Líquido da NFS-e", align="L")

        # Valor Líquido da NFS-e - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 3), y=section_start_y + 11)
        self.cell(
            w=col_width, h=8, text=self.data["total_value"]["net_value"], align="L"
        )

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 28,
            x2=x_margin + page_width - 2,
            y2=y_margin + 28,
        )

        col_width = self.epw / 3
        # TOTAIS APROXIMADOS DOS TRIBUTOS
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y + 21)
        self.cell(w=col_width, h=2, text="TOTAIS APROXIMADOS DOS TRIBUTOS", align="L")

        # Federais
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 3, y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="Federais", align="C")

        # Federais - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 25)
        self.cell(
            w=col_width, h=8, text=self.data["taxes_amount"]["federal_tax"], align="C"
        )

        # Estaduais
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="Estaduais", align="C")

        # Estaduais - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + col_width, y=section_start_y + 25)
        self.cell(
            w=col_width, h=8, text=self.data["taxes_amount"]["state_tax"], align="C"
        )

        # Municipais
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 25)
        self.cell(w=col_width, h=3, text="Municipais", align="C")

        # Municipais - Valor
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + (col_width * 2), y=section_start_y + 25)
        self.cell(
            w=col_width, h=8, text=self.data["taxes_amount"]["municipal_tax"], align="C"
        )

        self.set_font(self.default_font, "B", 7)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(
            x1=x_margin + 2,
            y1=y_margin + 42,
            x2=x_margin + page_width - 2,
            y2=y_margin + 42,
        )

    def _draw_complementary_info(self):
        x_margin = self.l_margin
        y_margin = self.y

        section_start_y = y_margin + 10

        # INFORMAÇÕES COMPLEMENTARES
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_margin + 3, y=section_start_y)
        self.cell(w=0, h=2, text="INFORMAÇÕES COMPLEMENTARES", align="L")

        # INFORMAÇÕES COMPLEMENTARES
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_margin + 3, y=section_start_y + 4)
        self.multi_cell(w=0, h=2.5, text=self.data["complementary_info"], align="L")
