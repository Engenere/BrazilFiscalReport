import pytest

from brazilfiscalreport.danfce import Danfce, DanfceConfig, Margins
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfce(load_xml):
    def _load_danfce(filename, config=None):
        xml_content = load_xml(f"danfce/{filename}")
        return Danfce(xml=xml_content, config=config)

    return _load_danfce


def test_danfce_default(tmp_path, load_danfce):
    danfce = load_danfce("danfce_default.xml")
    pdf_path = get_pdf_output_path("danfce", "danfce_default")
    assert_pdf_equal(danfce, pdf_path, tmp_path)


def test_danfce_without_consumer(tmp_path, load_danfce):
    danfce = load_danfce("danfce_without_consumer.xml")
    pdf_path = get_pdf_output_path("danfce", "danfce_without_consumer")
    assert_pdf_equal(danfce, pdf_path, tmp_path)


def test_danfce_with_margins(tmp_path, load_danfce):
    config = DanfceConfig(
        margins=Margins(top=4, right=4, bottom=4, left=4),
    )
    danfce = load_danfce("danfce_default.xml", config=config)
    pdf_path = get_pdf_output_path("danfce", "danfce_margin")
    assert_pdf_equal(danfce, pdf_path, tmp_path)


def test_danfce_multi_page(tmp_path, load_danfce):
    danfce = load_danfce("danfce_multi_page.xml")
    pdf_path = get_pdf_output_path("danfce", "danfce_multi_page")
    assert_pdf_equal(danfce, pdf_path, tmp_path)
