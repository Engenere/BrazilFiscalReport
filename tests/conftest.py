# Code below is extracted and modified from the fpdf2 project, which is
# distributed under the GNU Lesser General Public License (LGPL). The original
# code can be found at: https://github.com/py-pdf/fpdf2/blob/master/test/conftest.py

import hashlib
import os
import pathlib
import shutil
import warnings
from datetime import datetime, timezone
from pathlib import Path
from subprocess import PIPE, CalledProcessError, check_output

import pytest
from fpdf.template import Template

QPDF_AVAILABLE = bool(shutil.which("qpdf"))
if not QPDF_AVAILABLE:
    warnings.warn(
        "qpdf command not available on the $PATH, falling back to hash-based "
        "comparisons in tests",
        stacklevel=2,
    )

EPOCH = datetime(1969, 12, 31, 19, 00, 00).replace(tzinfo=timezone.utc)
HERE = Path(__file__).resolve().parent


def assert_pdf_equal(
    actual,
    expected,
    tmp_path,
    linearize=False,
    at_epoch=True,
    generate=False,
    ignore_id_changes=False,
    ignore_original_obj_ids=False,
    ignore_xref_offets=False,
):
    """
    This compare the output of a `FPDF` instance (or `Template` instance),
    with the provided PDF file.

    The `CreationDate` of the newly generated PDF is fixed, so that it never triggers
    a diff.

    If the `qpdf` command is available on the `$PATH`, it will be used to perform the
    comparison, as it greatly helps debugging diffs. Otherwise, a hash-based comparison
    logic is used as a fallback.

    Args:
        actual: instance of `FPDF` or `Template`. The `output` or `render` method
          will be called on it.
        expected: instance of `FPDF`, `bytearray` or file path to a PDF file
          matching the expected output
        tmp_path (Path): temporary directory provided by pytest individually to the
          caller test function
        generate (bool): only generate `pdf` output to `rel_expected_pdf_filepath`
          and return. Useful to create new tests.
    """
    if isinstance(actual, Template):
        actual.render()
        actual_pdf = actual.pdf
    else:
        actual_pdf = actual
    if at_epoch:
        actual_pdf.creation_date = EPOCH
    # Allow regeneration via env var without changing tests
    generate = generate or os.environ.get("BFR_GENERATE_EXPECTED") == "1"
    if generate:
        assert isinstance(expected, pathlib.Path), (
            "When passing `True` to `generate`"
            "a pathlib.Path must be provided as the `expected` parameter"
        )
        expected.parent.mkdir(parents=True, exist_ok=True)
        with expected.open("wb") as output_file:
            actual_pdf.output(output_file, linearize=linearize)
        return
    if isinstance(expected, pathlib.Path):
        expected_pdf_path = expected
    else:
        expected_pdf_path = tmp_path / "expected.pdf"
        with expected_pdf_path.open("wb") as pdf_file:
            if isinstance(expected, (bytes, bytearray)):
                pdf_file.write(expected)
            else:
                expected.set_creation_date(EPOCH)
                expected.output(pdf_file, linearize=linearize)
    actual_pdf_path = tmp_path / "actual.pdf"
    with actual_pdf_path.open("wb") as pdf_file:
        actual_pdf.output(pdf_file, linearize=linearize)
    if QPDF_AVAILABLE:  # Favor qpdf-based comparison, as it helps a lot debugging:
        actual_qpdf = _qpdf(actual_pdf_path)
        expected_qpdf = _qpdf(expected_pdf_path)
        (tmp_path / "actual_qpdf.pdf").write_bytes(actual_qpdf)
        (tmp_path / "expected_qpdf.pdf").write_bytes(expected_qpdf)
        actual_lines = actual_qpdf.splitlines()
        expected_lines = expected_qpdf.splitlines()
        if ignore_id_changes:
            actual_lines = filter_out_doc_id(actual_lines)
            expected_lines = filter_out_doc_id(expected_lines)
        if ignore_original_obj_ids:
            actual_lines = filter_out_original_obj_ids(actual_lines)
            expected_lines = filter_out_original_obj_ids(expected_lines)
        if ignore_xref_offets:
            actual_lines = filter_out_xref_offets(actual_lines)
            expected_lines = filter_out_xref_offets(expected_lines)
        if actual_lines != expected_lines:
            # It is important to reduce the size of both list of bytes here,
            # to avoid .assertSequenceEqual to take forever to finish,
            # that itself calls difflib.ndiff, that has cubic complexity from this
            # comment by Tim Peters: https://bugs.python.org/issue6931#msg223459
            actual_lines = subst_streams_with_hashes(actual_lines)
            expected_lines = subst_streams_with_hashes(expected_lines)
        assert actual_lines == expected_lines
        if linearize:
            _run_cmd("qpdf", "--check-linearization", str(actual_pdf_path))
    else:  # Fallback to hash comparison
        actual_hash = hashlib.md5(actual_pdf_path.read_bytes()).hexdigest()
        expected_hash = hashlib.md5(expected_pdf_path.read_bytes()).hexdigest()

        assert actual_hash == expected_hash, f"{actual_hash} != {expected_hash}"


def filter_out_doc_id(lines):
    return [line for line in lines if not line.startswith(b"  /ID [<")]


def filter_out_original_obj_ids(lines):
    return [line for line in lines if not line.startswith(b"%% Original object ID: ")]


def filter_out_xref_offets(lines):
    return [line for line in lines if not line.endswith(b" 00000 n ")]


def subst_streams_with_hashes(in_lines):
    """
    This utility function reduce the length of `in_lines`, a list of bytes,
    by replacing multi-lines streams looking like this:

        stream
        {non-printable-binary-data}endstream

    by a single line with this format:

        <stream with MD5 hash: abcdef0123456789>
    """
    out_lines, stream = [], None
    for line in in_lines:
        if line == b"stream":
            assert stream is None
            stream = bytearray()
        elif stream == b"stream":
            # First line of stream, we check if it is binary or not:
            try:
                line.decode("latin-1")
                if not (b"\0" in line or b"\xff" in line):
                    # It's likely to be text! No need to compact stream
                    stream = None
            except UnicodeDecodeError:
                pass
        if stream is None:
            out_lines.append(line)
        else:
            stream += line
        if line.endswith(b"endstream") and stream:
            stream_hash = hashlib.md5(stream).hexdigest()
            out_lines.append(f"<stream with MD5 hash: {stream_hash}>\n".encode())
            stream = None
    return out_lines


def _qpdf(input_pdf_filepath):
    return _run_cmd(
        "qpdf",
        "--deterministic-id",
        "--password=fpdf2",
        "--qdf",
        str(input_pdf_filepath),
        "-",
    )


def _run_cmd(*args):
    try:
        return check_output(args, stderr=PIPE)
    except CalledProcessError as error:
        print(f"\nqpdf STDERR: {error.stderr.decode().strip()}")
        raise


def pytest_configure(config):
    config.addinivalue_line(
        "filterwarnings",
        'ignore:<svg> has no "viewBox", using its "width" & "height"'
        ' as default "viewBox":UserWarning',
    )


@pytest.fixture(scope="function")
def load_xml():
    def _load_xml(filename):
        xml_file_path = os.path.join(HERE, "fixtures", filename)
        with open(xml_file_path, encoding="utf8") as file:
            return file.read()

    return _load_xml


@pytest.fixture(scope="module")
def logo_path():
    """
    Provides the file path for the logo used in DANFE configurations.
    """
    return os.path.join(HERE, "fixtures", "logo-engenere.jpg")


def get_pdf_output_path(doc_type, test_identifier):
    return HERE / f"generated/{doc_type}/{test_identifier}.pdf"
