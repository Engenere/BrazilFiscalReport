"""Generate the documentation screenshots (docs/assets/screenshots/*.png).

Renders one sample PDF per document type from the test fixtures, converts
the first page to PNG with pdftoppm (poppler-utils) and quantizes the image
with Pillow to keep the files small.

Usage, from the repository root:

    python scripts/generate_screenshots.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
OUTPUT_DIR = ROOT / "docs" / "assets" / "screenshots"
LOGO = FIXTURES / "logo-engenere.jpg"
RESOLUTION_DPI = 110

EMITENTE = {
    "nome": "EMPRESA LTDA",
    "end": "AV. TESTE, 100",
    "bairro": "CENTRO",
    "cidade": "SÃO PAULO",
    "uf": "SP",
    "fone": "(11) 1234-5678",
}


def read_fixture(relative_path: str) -> str:
    xml = (FIXTURES / relative_path).read_text(encoding="utf8")
    # Most fixtures are homologation documents; promote them to production so
    # the showcase screenshots come out without the SEM VALOR FISCAL watermark.
    return xml.replace("<tpAmb>2</tpAmb>", "<tpAmb>1</tpAmb>")


def build_danfe():
    from brazilfiscalreport.danfe import Danfe, DanfeConfig

    config = DanfeConfig(logo=str(LOGO))
    return Danfe(
        xml=read_fixture("danfe/nfe_with_production_environment.xml"), config=config
    )


def build_dacce():
    from brazilfiscalreport.dacce import DaCCe

    return DaCCe(xml=read_fixture("dacce/xml_cce_1.xml"), emitente=EMITENTE)


def build_dacte():
    from brazilfiscalreport.dacte import Dacte, DacteConfig

    config = DacteConfig(logo=str(LOGO))
    return Dacte(xml=read_fixture("dacte/dacte_test_1.xml"), config=config)


def build_damdfe():
    from brazilfiscalreport.damdfe import Damdfe, DamdfeConfig

    config = DamdfeConfig(logo=str(LOGO))
    return Damdfe(xml=read_fixture("damdfe/mdf-e_test_1.xml"), config=config)


def build_danfse():
    from brazilfiscalreport.danfse import Danfse

    return Danfse(xml=read_fixture("danfse/nfse_test_prod.xml"))


BUILDERS = {
    "danfe": build_danfe,
    "dacce": build_dacce,
    "dacte": build_dacte,
    "damdfe": build_damdfe,
    "danfse": build_danfse,
}


def pdf_first_page_to_png(pdf_path: Path, png_path: Path) -> None:
    from PIL import Image

    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            str(RESOLUTION_DPI),
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            str(pdf_path),
            str(png_path.with_suffix("")),
        ],
        check=True,
    )
    image = Image.open(png_path)
    image.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(
        png_path, optimize=True
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, builder in BUILDERS.items():
            pdf_path = Path(tmp) / f"{name}.pdf"
            png_path = OUTPUT_DIR / f"{name}.png"
            builder().output(str(pdf_path))
            pdf_first_page_to_png(pdf_path, png_path)
            print(f"{png_path.relative_to(ROOT)} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
