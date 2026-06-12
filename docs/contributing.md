# Contributing

Contributions are welcome! Here's how to set up the project for development.

## Development Setup

The library supports Python 3.8+ (the CI tests 3.8 through 3.13), so keep the code compatible with 3.8.

1. Clone the repository:

    ```bash
    git clone https://github.com/Engenere/BrazilFiscalReport.git
    cd BrazilFiscalReport
    ```

2. Create a virtual environment and install dependencies:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate     # Windows
    pip install -e '.[dacte,damdfe,danfse,cli]'
    pip install pytest pytest-cov ruff
    ```

    !!! note
        The root `requirements.txt` belongs to the Streamlit demo app (`streamlit_app.py`), not to library development — use the editable install above.

3. Install pre-commit hooks:

    ```bash
    pip install pre-commit
    pre-commit install
    ```

## Running Tests

The project uses `pytest` for testing. Installing `qpdf` is strongly recommended: without it, the PDF comparison tests fall back to opaque hash-based comparisons that are much harder to debug (the CI always installs it).

```bash
# Install qpdf (Ubuntu/Debian)
sudo apt-get install qpdf

# Run all tests
pytest

# Run with coverage
pytest --cov=./brazilfiscalreport --cov-branch

# Run tests for a specific document type
pytest tests/test_danfe.py
```

## Code Style

The project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting. Pre-commit hooks will automatically check your code before each commit (the hook runs a pinned Ruff version, so its output is the source of truth).

```bash
# Manual check
ruff check .
ruff format .
```

## Regenerating Reference PDFs

When making changes to PDF output, you can regenerate the reference PDFs used in tests:

```bash
BFR_GENERATE_EXPECTED=1 pytest tests/test_danfe.py
```

!!! warning
    Only regenerate reference PDFs when you intentionally changed the PDF output. Always review the visual diff before committing.

!!! note
    Do not set `generate=True` directly in test code — a pre-commit hook (`no-generate-true`) blocks it. Always use the `BFR_GENERATE_EXPECTED=1` environment variable instead.

## Working on Documentation

The documentation site uses [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) with the [mkdocs-static-i18n](https://github.com/ultrabug/mkdocs-static-i18n) plugin. Every page is a pair of files: `page.md` (English) and `page.pt.md` (Portuguese) — keep both in sync when editing.

```bash
pip install mkdocs-material mkdocs-static-i18n
mkdocs serve  # live preview at http://127.0.0.1:8000
```

The site is deployed automatically when changes to `docs/**` reach the `main` branch.

The document screenshots in `docs/assets/screenshots/` are generated from the test fixtures. To regenerate them after a layout change (requires `poppler-utils` for `pdftoppm`):

```bash
python scripts/generate_screenshots.py
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b my-feature`)
3. Commit your changes
4. Push to your fork and open a Pull Request

Make sure all tests pass and pre-commit hooks are clean before submitting.
