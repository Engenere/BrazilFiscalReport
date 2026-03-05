import pytest

from brazilfiscalreport.danfce import (
    Danfce,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfce(load_xml):
    def _load_danfce(filename, config=None):
        xml_content = load_xml(filename)
        return Danfce(xml=xml_content, config=config)

    return _load_danfce


def test_danfce_default(tmp_path, load_danfce):
    danfce = load_danfce("nfe_overload.xml")
    pdf_path = get_pdf_output_path("danfce", "danfce_default")
    assert_pdf_equal(danfce, pdf_path, tmp_path)
