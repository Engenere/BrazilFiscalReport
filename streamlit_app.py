"""Playground online da BrazilFiscalReport.

Converte XMLs fiscais (NF-e, CT-e, MDF-e, CC-e e NFS-e nacional) em PDF,
expondo todas as opções de geração suportadas pela biblioteca.
"""

import io
import re
import traceback
import xml.etree.ElementTree as ET
import zipfile

import streamlit as st
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring as safe_fromstring

from brazilfiscalreport import __version__, dacte, damdfe, danfe, danfse
from brazilfiscalreport.dacce import DaCCe

REPO_URL = "https://github.com/Engenere/BrazilFiscalReport"
ISSUES_URL = f"{REPO_URL}/issues"

NFE_NS = "{http://www.portalfiscal.inf.br/nfe}"
CCE_TP_EVENTO = "110110"

IMAGE_TYPES = ["png", "jpg", "jpeg"]

ROOT_TAG_TO_DOC = {
    "nfeProc": "DANFE",
    "NFe": "DANFE",
    "cteProc": "DACTE",
    "CTe": "DACTE",
    "mdfeProc": "DAMDFE",
    "MDFe": "DAMDFE",
    "procEventoNFe": "DACCe",
    "NFSe": "DANFSE",
}

DOC_ORDER = ["DANFE", "DACTE", "DAMDFE", "DACCe", "DANFSE"]

DOC_MODEL = {
    "DANFE": "NF-e",
    "DACTE": "CT-e",
    "DAMDFE": "MDF-e",
    "DACCe": "CC-e",
    "DANFSE": "NFS-e",
}

FONTS = {"Times": "TIMES", "Courier": "COURIER"}
ORIENTATIONS = {
    "Automática (XML)": "AUTO",
    "Retrato": "PORTRAIT",
    "Paisagem": "LANDSCAPE",
}
RECEIPT_POSITIONS = {"Topo": "TOP", "Rodapé": "BOTTOM"}
FONT_SIZES = {"Normal": "SMALL", "Grande": "BIG"}
INVOICE_DISPLAYS = {
    "Detalhamento completo": "FULL_DETAILS",
    "Somente duplicatas": "DUPLICATES_ONLY",
}

MARGIN_HELP = "Margens da página em milímetros."


# ---------------------------------------------------------------------------
# Opções de geração (sidebar)
# ---------------------------------------------------------------------------


def margin_inputs(
    prefix,
    left=(0, 50, 5),
    left_help=None,
    right=(0, 50, 5),
    right_help=None,
    top=(0, 50, 5),
    bottom=(0, 50, 5),
):
    """Quatro campos de margem em mm; cada lado pode ter limites próprios."""
    st.markdown("**Margens (mm)**", help=MARGIN_HELP)
    col1, col2 = st.columns(2)
    top_val = col1.number_input("Superior", *top, key=f"{prefix}_margin_top")
    bottom = col2.number_input("Inferior", *bottom, key=f"{prefix}_margin_bottom")
    left_val = col1.number_input(
        "Esquerda", *left, key=f"{prefix}_margin_left", help=left_help
    )
    right_val = col2.number_input(
        "Direita", *right, key=f"{prefix}_margin_right", help=right_help
    )
    return {
        "margin_top": top_val,
        "margin_right": right_val,
        "margin_bottom": bottom,
        "margin_left": left_val,
    }


def font_input(prefix):
    label = st.radio(
        "Fonte",
        list(FONTS),
        horizontal=True,
        key=f"{prefix}_font",
        help="Família tipográfica usada em todo o documento.",
    )
    return FONTS[label]


def logo_input(prefix, help_text):
    # O nonce muda a chave quando o usuário restaura os padrões, pois apagar
    # a chave de um file_uploader não limpa o arquivo enviado.
    nonce = st.session_state.get(f"{prefix}_nonce", 0)
    uploaded = st.file_uploader(
        "Logotipo (PNG/JPG)",
        type=IMAGE_TYPES,
        key=f"{prefix}_logo_{nonce}",
        help=help_text,
    )
    return uploaded.getvalue() if uploaded else None


def reset_doc_options(prefix):
    """Restaura os padrões apagando o estado dos widgets do documento."""
    nonce = st.session_state.get(f"{prefix}_nonce", 0)
    for key in list(st.session_state):
        if key.startswith(f"{prefix}_") and key != f"{prefix}_reset":
            del st.session_state[key]
    st.session_state[f"{prefix}_nonce"] = nonce + 1


def danfe_options():
    opts = {}
    opts["logo"] = logo_input(
        "danfe", "Imagem exibida no quadro do emitente, no cabeçalho de cada página."
    )

    st.markdown("**Layout**")
    orientation = st.radio(
        "Orientação",
        list(ORIENTATIONS),
        horizontal=True,
        key="danfe_orientation",
        help="Automática segue a forma de impressão do XML (tpImp: 1=retrato, "
        "2=paisagem); as demais opções forçam a orientação escolhida.",
    )
    opts["orientation"] = ORIENTATIONS[orientation]
    receipt = st.radio(
        "Posição do canhoto",
        list(RECEIPT_POSITIONS),
        horizontal=True,
        key="danfe_receipt_pos",
        disabled=opts["orientation"] == "LANDSCAPE",
        help="Em DANFEs com impressão paisagem o canhoto é sempre "
        "impresso na lateral esquerda, ignorando esta opção.",
    )
    opts["receipt_pos"] = RECEIPT_POSITIONS[receipt]
    opts["font_type"] = font_input("danfe")
    size = st.radio(
        "Tamanho da fonte",
        list(FONT_SIZES),
        horizontal=True,
        key="danfe_font_size",
        disabled=opts["font_type"] == "COURIER",
        help="O tamanho Grande só é aplicado com a fonte Times.",
    )
    opts["font_size"] = FONT_SIZES[size]

    st.markdown("**Conteúdo**")
    invoice = st.selectbox(
        "Exibição da fatura",
        list(INVOICE_DISPLAYS),
        key="danfe_invoice_display",
        help="Nível de detalhe do bloco FATURA/DUPLICATAS; só tem efeito "
        "quando o XML possui dados de cobrança.",
    )
    opts["invoice_display"] = INVOICE_DISPLAYS[invoice]
    opts["display_pis_cofins"] = st.toggle(
        "Exibir PIS/COFINS",
        key="danfe_pis_cofins",
        help="Exibe os valores de PIS e COFINS no bloco de cálculo do imposto.",
    )
    opts["infcpl_semicolon_newline"] = st.toggle(
        "Quebrar linha em ';' nas inf. complementares",
        key="danfe_semicolon",
        help="Cada ';' das informações complementares (infCpl) vira uma "
        "quebra de linha no bloco de dados adicionais.",
    )
    opts["watermark_cancelled"] = st.toggle(
        "Marca d'água CANCELADA",
        key="danfe_cancelled",
        help="O XML autorizado não indica o cancelamento; ative esta "
        "opção para notas canceladas.",
    )

    st.markdown("**Descrição dos produtos**")
    opts["display_branch"] = st.toggle(
        "Exibir lotes (rastreabilidade)",
        key="danfe_branch",
        help="Exibe número do lote, quantidade, fabricação e validade "
        "(grupo rastro) na descrição do produto.",
    )
    opts["branch_info_prefix"] = st.text_input(
        "Prefixo das linhas de lote",
        key="danfe_branch_prefix",
        disabled=not opts["display_branch"],
        help="Texto colocado antes de cada linha de lote (ex.: '=>').",
    )
    opts["display_anp"] = st.toggle(
        "Exibir dados ANP (combustíveis)",
        key="danfe_anp",
        help="Exibe código/descrição ANP e UF de consumo para itens de "
        "combustíveis (grupo comb).",
    )
    opts["display_anvisa"] = st.toggle(
        "Exibir dados ANVISA (medicamentos)",
        key="danfe_anvisa",
        help="Exibe código ANVISA e preço máximo ao consumidor para itens "
        "de medicamentos (grupo med).",
    )
    opts["display_additional_info"] = st.toggle(
        "Exibir inf. adicionais do item",
        value=True,
        key="danfe_add_info",
        help="Exibe o texto de informações adicionais do produto (infAdProd).",
    )

    opts.update(margin_inputs("danfe"))

    st.markdown("**Casas decimais**")
    col1, col2 = st.columns(2)
    opts["price_precision"] = col1.number_input(
        "Preço unit.", 0, 10, 4, key="danfe_price_precision"
    )
    opts["quantity_precision"] = col2.number_input(
        "Quantidade", 0, 10, 4, key="danfe_qty_precision"
    )

    st.markdown(
        "**Carimbo de rodapé**",
        help="Faixa exibida no rodapé de todas as páginas; ativa somente "
        "quando houver texto ou logo.",
    )
    opts["stamp_text"] = st.text_input("Texto do carimbo", key="danfe_stamp_text")
    stamp_logo = st.file_uploader(
        "Logo do carimbo (PNG/JPG)",
        type=IMAGE_TYPES,
        key=f"danfe_stamp_logo_{st.session_state.get('danfe_nonce', 0)}",
    )
    opts["stamp_logo"] = stamp_logo.getvalue() if stamp_logo else None
    stamp_active = bool(opts["stamp_text"] or opts["stamp_logo"])
    col1, col2, col3 = st.columns(3)
    opts["stamp_height"] = col1.number_input(
        "Altura",
        3,
        20,
        5,
        key="danfe_stamp_height",
        disabled=not stamp_active,
        help="Altura da faixa do carimbo, em milímetros.",
    )
    opts["stamp_logo_max_width"] = col2.number_input(
        "Larg. logo",
        5,
        60,
        20,
        key="danfe_stamp_width",
        disabled=not stamp_active,
        help="Largura máxima do logo do carimbo, em milímetros.",
    )
    opts["stamp_spacing"] = col3.number_input(
        "Espaço",
        0,
        10,
        1,
        key="danfe_stamp_spacing",
        disabled=not stamp_active,
        help="Espaçamento vertical entre o conteúdo do documento e o "
        "carimbo, em milímetros.",
    )
    return opts


def dacte_options():
    opts = {}
    opts["logo"] = logo_input(
        "dacte", "Imagem exibida no cabeçalho, junto aos dados do emitente."
    )
    opts["font_type"] = font_input("dacte")
    opts["watermark_cancelled"] = st.toggle(
        "Marca d'água CANCELADA",
        key="dacte_cancelled",
        help="O XML autorizado não indica o cancelamento; ative esta "
        "opção para CT-es cancelados.",
    )
    opts["display_ibs_cbs"] = st.toggle(
        "Exibir IBS/CBS (reforma tributária)",
        key="dacte_ibs_cbs",
        help="Adiciona a coluna IBS/CBS no quadro de impostos; exibe 0,00 "
        "se o XML não tiver o grupo IBSCBS.",
    )
    opts.update(
        margin_inputs(
            "dacte",
            left=(2, 10, 5),
            left_help="O DACTE aceita apenas valores inteiros de 2 a 10 "
            "para a margem esquerda.",
        )
    )
    return opts


def damdfe_options():
    opts = {}
    opts["logo"] = logo_input(
        "damdfe", "Imagem exibida no canto superior esquerdo do cabeçalho."
    )
    opts["font_type"] = font_input("damdfe")
    opts["display_origem_destino_prestacao"] = st.toggle(
        "Exibir origem/destino da prestação",
        key="damdfe_origem_destino",
        help="Acrescenta na linha PERCURSO os municípios de carregamento "
        "(origem) e de descarga (destino) extraídos do XML.",
    )
    opts.update(
        margin_inputs(
            "damdfe",
            left=(5, 10, 5),
            left_help="O DAMDFE aceita apenas valores inteiros de 5 a 10 "
            "para a margem esquerda.",
            right=(1, 10, 5),
            right_help="O DAMDFE aceita apenas valores inteiros de 1 a 10 "
            "para a margem direita.",
        )
    )
    return opts


DANFSE_FONTS = {
    "Helvetica (Arial)": "HELVETICA",
    "Times": "TIMES",
    "Courier": "COURIER",
}


def danfse_options():
    opts = {}
    st.caption(
        "O DANFSE usa o brasão oficial da NFS-e nacional; não há opção de logotipo."
    )
    label = st.radio(
        "Fonte",
        list(DANFSE_FONTS),
        horizontal=True,
        key="danfse_font",
        help="A NT 008/2026 exige Arial/Microsoft Sans Serif; a Helvetica é "
        "o equivalente métrico disponível no PDF.",
    )
    opts["font_type"] = DANFSE_FONTS[label]
    opts["watermark_cancelled"] = st.toggle(
        "Marca d'água CANCELADA",
        key="danfse_cancelled",
        help="O XML da nota não indica o cancelamento; ative esta "
        "opção para NFS-es canceladas.",
    )
    opts["watermark_replaced"] = st.toggle(
        "Marca d'água SUBSTITUÍDA",
        key="danfse_replaced",
        help="Para NFS-es substituídas (NT 008/2026, item 2.5.2). "
        "Se CANCELADA também estiver ativa, prevalece CANCELADA.",
    )
    opts["display_canhoto"] = st.toggle(
        "Canhoto de cientificação",
        key="danfse_canhoto",
        help="Bloco opcional na base do documento (NT 008/2026, item 2.1.13).",
    )
    opts["price_precision"] = st.number_input(
        "Casas decimais de valores",
        0,
        10,
        2,
        key="danfse_price_precision",
        help="Casas decimais de valores monetários e alíquotas "
        "(o leiaute v2.0 da NT 008/2026 usa 2 casas).",
    )
    opts.update(
        margin_inputs(
            "danfse",
            top=(0, 50, 2),
            bottom=(0, 50, 2),
            left=(0, 50, 2),
            right=(0, 50, 2),
            left_help="A NT 008/2026 fixa margens entre 1,5 e 2,0 mm.",
        )
    )
    return opts


def dacce_options(cnpj_hints):
    opts = {}
    st.caption(
        "O XML da CC-e não contém os dados cadastrais do emitente. "
        "Preencha-os abaixo para exibi-los no cabeçalho (opcional)."
    )
    if cnpj_hints:
        st.caption("CNPJ do emitente no XML: " + ", ".join(cnpj_hints))
    opts["nome"] = st.text_input("Razão social", key="dacce_nome")
    opts["end"] = st.text_input(
        "Endereço", key="dacce_end", placeholder="AV. EXEMPLO, 100"
    )
    opts["bairro"] = st.text_input("Bairro", key="dacce_bairro")
    col1, col2 = st.columns([3, 1])
    opts["cidade"] = col1.text_input("Cidade", key="dacce_cidade")
    opts["uf"] = col2.text_input(
        "UF", key="dacce_uf", max_chars=2, placeholder="SP"
    ).upper()
    opts["fone"] = st.text_input(
        "Telefone", key="dacce_fone", placeholder="(11) 1234-5678"
    )
    opts["logo"] = logo_input(
        "dacce",
        "Imagem exibida no canto superior esquerdo (12 mm de largura); "
        "prefira imagens aproximadamente quadradas.",
    )
    return opts


SIDEBAR_BUILDERS = {
    "DANFE": danfe_options,
    "DACTE": dacte_options,
    "DAMDFE": damdfe_options,
    "DANFSE": danfse_options,
}


# ---------------------------------------------------------------------------
# Construção das configurações e geração dos PDFs
# ---------------------------------------------------------------------------


def _as_image(data):
    return io.BytesIO(data) if data else None


def _force_orientation(raw_xml: bytes, orientation: str) -> bytes:
    """Sobrescreve o tpImp do XML (1=retrato, 2=paisagem) antes de gerar."""
    value = b"1" if orientation == "PORTRAIT" else b"2"
    return re.sub(
        rb"<tpImp>\s*\d+\s*</tpImp>",
        b"<tpImp>" + value + b"</tpImp>",
        raw_xml,
        count=1,
    )


def build_danfe_config(o):
    return danfe.DanfeConfig(
        logo=_as_image(o["logo"]),
        margins=danfe.Margins(
            top=o["margin_top"],
            right=o["margin_right"],
            bottom=o["margin_bottom"],
            left=o["margin_left"],
        ),
        receipt_pos=danfe.ReceiptPosition[o["receipt_pos"]],
        decimal_config=danfe.DecimalConfig(
            price_precision=o["price_precision"],
            quantity_precision=o["quantity_precision"],
        ),
        invoice_display=danfe.InvoiceDisplay[o["invoice_display"]],
        font_type=danfe.FontType[o["font_type"]],
        font_size=danfe.FontSize[o["font_size"]],
        display_pis_cofins=o["display_pis_cofins"],
        watermark_cancelled=o["watermark_cancelled"],
        infcpl_semicolon_newline=o["infcpl_semicolon_newline"],
        product_description_config=danfe.ProductDescriptionConfig(
            display_branch=o["display_branch"],
            display_anp=o["display_anp"],
            display_anvisa=o["display_anvisa"],
            branch_info_prefix=o["branch_info_prefix"],
            display_additional_info=o["display_additional_info"],
        ),
        footer_stamp=danfe.FooterStamp(
            logo=_as_image(o["stamp_logo"]),
            text=o["stamp_text"],
            height=o["stamp_height"],
            logo_max_width=o["stamp_logo_max_width"],
            spacing=o["stamp_spacing"],
        ),
    )


def build_dacte_config(o):
    return dacte.DacteConfig(
        logo=_as_image(o["logo"]),
        margins=dacte.Margins(
            top=o["margin_top"],
            right=o["margin_right"],
            bottom=o["margin_bottom"],
            left=o["margin_left"],
        ),
        font_type=dacte.FontType[o["font_type"]],
        watermark_cancelled=o["watermark_cancelled"],
        display_ibs_cbs=o["display_ibs_cbs"],
    )


def build_damdfe_config(o):
    return damdfe.DamdfeConfig(
        logo=_as_image(o["logo"]),
        margins=damdfe.Margins(
            top=o["margin_top"],
            right=o["margin_right"],
            bottom=o["margin_bottom"],
            left=o["margin_left"],
        ),
        font_type=damdfe.FontType[o["font_type"]],
        display_origem_destino_prestacao=o["display_origem_destino_prestacao"],
    )


def build_danfse_config(o):
    return danfse.DanfseConfig(
        margins=danfse.Margins(
            top=o["margin_top"],
            right=o["margin_right"],
            bottom=o["margin_bottom"],
            left=o["margin_left"],
        ),
        decimal_config=danfse.DecimalConfig(price_precision=o["price_precision"]),
        font_type=danfse.FontType[o["font_type"]],
        watermark_cancelled=o["watermark_cancelled"],
        watermark_replaced=o["watermark_replaced"],
        display_canhoto=o["display_canhoto"],
    )


@st.cache_data(show_spinner=False, max_entries=64)
def generate_pdf(raw_xml: bytes, doc_type: str, opts: dict) -> bytes:
    """Gera o PDF do documento; cacheado por (XML, tipo, opções)."""
    if doc_type == "DANFE":
        if opts["orientation"] != "AUTO":
            raw_xml = _force_orientation(raw_xml, opts["orientation"])
        document = danfe.Danfe(xml=raw_xml, config=build_danfe_config(opts))
    elif doc_type == "DACTE":
        document = dacte.Dacte(xml=raw_xml, config=build_dacte_config(opts))
    elif doc_type == "DAMDFE":
        document = damdfe.Damdfe(xml=raw_xml, config=build_damdfe_config(opts))
    elif doc_type == "DANFSE":
        document = danfse.Danfse(xml=raw_xml, config=build_danfse_config(opts))
    elif doc_type == "DACCe":
        emitente = {
            key: opts[key].strip()
            for key in ("nome", "end", "bairro", "cidade", "uf", "fone")
        }
        document = DaCCe(xml=raw_xml, emitente=emitente, image=_as_image(opts["logo"]))
    else:  # pragma: no cover - protegido pela detecção de tipo
        raise ValueError(f"Tipo de documento desconhecido: {doc_type}")
    return bytes(document.output())


def extract_cce_cnpj(root):
    """CNPJ do emitente do evento, exibido como dica no formulário da CC-e."""
    element = root.find(f".//{NFE_NS}infEvento/{NFE_NS}CNPJ")
    cnpj = element.text if element is not None and element.text else None
    if cnpj and len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def detect_document(raw: bytes):
    """Detecta o tipo de documento fiscal; retorna (doc, root, erro)."""
    try:
        # defusedxml bloqueia DTD/entidades (amplificação de memória).
        root = safe_fromstring(raw, forbid_dtd=True)
    except ET.ParseError:
        return None, None, "Arquivo XML inválido. Envie um XML fiscal válido."
    except DefusedXmlException:
        return (
            None,
            None,
            (
                "XML com DTD ou entidades não é aceito por segurança. "
                "XMLs fiscais não contêm DOCTYPE."
            ),
        )
    tag = root.tag.split("}")[-1]
    doc = ROOT_TAG_TO_DOC.get(tag)
    if doc == "DACCe":
        element = root.find(f".//{NFE_NS}infEvento/{NFE_NS}tpEvento")
        tp_evento = (element.text or "").strip() if element is not None else ""
        if tp_evento != CCE_TP_EVENTO:
            return (
                None,
                root,
                (
                    f"Evento de NF-e não suportado (tpEvento "
                    f"`{tp_evento or 'ausente'}`). Apenas a Carta de Correção "
                    f"Eletrônica (tpEvento {CCE_TP_EVENTO}) pode ser convertida "
                    "em DACCe."
                ),
            )
    if doc is None:
        return (
            None,
            root,
            (
                f"Documento não reconhecido (tag raiz `<{tag}>`). São aceitos "
                "XMLs de NF-e, CT-e, MDF-e, CC-e (evento processado) e "
                "NFS-e nacional."
            ),
        )
    return doc, root, None


def pdf_file_name(xml_name: str) -> str:
    return xml_name.rsplit(".", 1)[0] + ".pdf"


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Conversor XML Fiscal para PDF",
    page_icon=":page_facing_up:",
    initial_sidebar_state="expanded",
    menu_items={
        "Report a bug": ISSUES_URL,
        "About": (
            "Conversor de XML fiscal para PDF construído com a biblioteca "
            f"open source [Brazil Fiscal Report]({REPO_URL})."
        ),
    },
)

st.title("Conversor de XML Fiscal para PDF")
st.markdown("Transforme seus XMLs fiscais em PDF de forma rápida e gratuita.")
st.markdown(
    "Documentos suportados: "
    ":gray-background[**DANFE** · NF-e] "
    ":gray-background[**DACTE** · CT-e] "
    ":gray-background[**DAMDFE** · MDF-e] "
    ":gray-background[**DACCe** · CC-e] "
    ":gray-background[**DANFSE** · NFS-e]"
)

uploads = (
    st.file_uploader(
        "Envie um ou mais arquivos XML",
        type=["xml"],
        accept_multiple_files=True,
    )
    or []
)

# Primeira passada: detecta o tipo de cada arquivo enviado.
entries = []
for upload in uploads:
    raw = upload.getvalue()
    doc, root, error = detect_document(raw)
    entries.append(
        {"name": upload.name, "raw": raw, "doc": doc, "root": root, "error": error}
    )

detected_docs = [d for d in DOC_ORDER if any(e["doc"] == d for e in entries)]

# Sidebar: opções de geração apenas dos tipos de documento detectados.
opts_by_doc = {}
with st.sidebar:
    st.header("⚙️ Opções de geração")
    if not detected_docs:
        st.caption("Envie um XML para configurar as opções de geração do documento.")
    for doc in detected_docs:
        with st.expander(f"{doc} · {DOC_MODEL[doc]}", expanded=len(detected_docs) == 1):
            st.button(
                "↩️ Restaurar padrões",
                key=f"{doc.lower()}_reset",
                on_click=reset_doc_options,
                args=(doc.lower(),),
            )
            if doc == "DACCe":
                hints = sorted(
                    {
                        cnpj
                        for e in entries
                        if e["doc"] == "DACCe" and (cnpj := extract_cce_cnpj(e["root"]))
                    }
                )
                opts_by_doc[doc] = dacce_options(hints)
            else:
                opts_by_doc[doc] = SIDEBAR_BUILDERS[doc]()

# Segunda passada: gera os PDFs.
results = []
for entry in entries:
    result = {
        "name": entry["name"],
        "doc": entry["doc"],
        "pdf": None,
        "error": entry["error"],
        "traceback": None,
    }
    if not result["error"]:
        try:
            result["pdf"] = generate_pdf(
                entry["raw"], entry["doc"], opts_by_doc[entry["doc"]]
            )
        except Exception:
            result["error"] = "Não foi possível gerar o PDF deste arquivo."
            result["traceback"] = traceback.format_exc()
    results.append(result)

succeeded = [r for r in results if r["pdf"]]
failed = [r for r in results if not r["pdf"]]

if results:
    if succeeded and not failed:
        st.success(
            f"{len(succeeded)} PDF{'s' if len(succeeded) > 1 else ''} "
            f"gerado{'s' if len(succeeded) > 1 else ''} com sucesso!"
        )
    elif succeeded:
        verb = "foi gerado" if len(succeeded) == 1 else "foram gerados"
        st.warning(
            f"{len(succeeded)} de {len(results)} PDFs {verb} com sucesso. "
            "Veja os erros abaixo."
        )
    elif len(results) > 1:
        st.error("Nenhum PDF pôde ser gerado. Veja os erros abaixo.")

    if len(succeeded) > 1:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            used_names = set()
            for result in succeeded:
                name = pdf_file_name(result["name"])
                base, counter = name, 1
                while name in used_names:
                    counter += 1
                    name = base[:-4] + f"_{counter}.pdf"
                used_names.add(name)
                zip_file.writestr(name, result["pdf"])
        st.download_button(
            "📦 Baixar todos (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="documentos_fiscais.zip",
            mime="application/zip",
            type="primary",
        )

    for index, result in enumerate(results):
        if result["pdf"]:
            col_name, col_btn = st.columns([3, 1], vertical_alignment="center")
            doc_badge = f" · :gray-background[{result['doc']}]" if result["doc"] else ""
            col_name.markdown(f"📄 **{result['name']}**{doc_badge}")
            col_btn.download_button(
                "Baixar PDF",
                data=result["pdf"],
                file_name=pdf_file_name(result["name"]),
                mime="application/pdf",
                key=f"download_{index}",
                width="stretch",
            )
        else:
            st.error(f"**{result['name']}** — {result['error']}", icon="❌")
            if result["traceback"]:
                with st.expander("Detalhes técnicos"):
                    st.code(result["traceback"])
                    st.markdown(
                        "Acha que é um problema na biblioteca? "
                        f"[Reporte aqui]({ISSUES_URL})."
                    )

    if succeeded:
        st.subheader("Pré-visualização")
        if len(succeeded) == 1:
            preview = succeeded[0]
        else:
            names = [r["name"] for r in succeeded]
            has_dupes = len(set(names)) != len(names)
            preview_index = st.selectbox(
                "Arquivo",
                range(len(succeeded)),
                format_func=lambda i: (
                    f"{names[i]} ({i + 1})" if has_dupes else names[i]
                ),
                label_visibility="collapsed",
            )
            preview = succeeded[preview_index]
        try:
            st.pdf(preview["pdf"], height=700)
        except Exception:
            # Ambientes sem o componente opcional (pip install streamlit[pdf])
            st.info(
                "Pré-visualização indisponível neste ambiente. "
                "Use o botão de download acima."
            )
        if preview["doc"] not in ("DACCe", "DANFSE"):
            st.caption(
                "NF-e, CT-e e MDF-e de homologação ou sem protocolo "
                'de autorização recebem a marca d\'água "SEM VALOR FISCAL" '
                "automaticamente."
            )
        elif preview["doc"] == "DANFSE":
            st.caption(
                "NFS-e de homologação (tpAmb=2) recebe a expressão "
                '"NFS-e SEM VALIDADE JURÍDICA" no cabeçalho, conforme '
                "a NT 008/2026."
            )

st.divider()
st.caption(
    "Desenvolvido com "
    f"[Brazil Fiscal Report]({REPO_URL}) v{__version__}"
    " — biblioteca open source para geração de documentos fiscais em PDF."
)
