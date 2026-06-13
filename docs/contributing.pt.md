# Contribuindo

Contribuições são bem-vindas! Veja como configurar o projeto para desenvolvimento.

## Configuração do Ambiente de Desenvolvimento

A biblioteca suporta Python 3.8+ (o CI testa do 3.8 ao 3.13), então mantenha o código compatível com 3.8.

1. Clone o repositório:

    ```bash
    git clone https://github.com/Engenere/BrazilFiscalReport.git
    cd BrazilFiscalReport
    ```

2. Crie um ambiente virtual e instale as dependências:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate     # Windows
    pip install -e '.[dacte,damdfe,danfse,cli]'
    pip install pytest pytest-cov ruff
    ```

    !!! note
        O `requirements.txt` da raiz pertence ao app demo Streamlit (`streamlit_app.py`), não ao desenvolvimento da biblioteca — use a instalação editável acima.

3. Instale os hooks do pre-commit:

    ```bash
    pip install pre-commit
    pre-commit install
    ```

## Executando Testes

O projeto usa `pytest` para testes. Instalar o `qpdf` é fortemente recomendado: sem ele, os testes de comparação de PDF caem para comparações por hash, muito mais difíceis de depurar (o CI sempre o instala).

```bash
# Instalar qpdf (Ubuntu/Debian)
sudo apt-get install qpdf

# Executar todos os testes
pytest

# Executar com cobertura
pytest --cov=./brazilfiscalreport --cov-branch

# Executar testes para um tipo específico de documento
pytest tests/test_danfe.py
```

## Estilo de Código

O projeto usa [Ruff](https://github.com/astral-sh/ruff) para linting e formatação. Os hooks do pre-commit verificarão automaticamente seu código antes de cada commit (o hook executa uma versão fixada do Ruff, então a saída dele é a fonte de verdade).

```bash
# Verificação manual
ruff check .
ruff format .
```

## Regenerando PDFs de Referência

Ao fazer alterações na saída PDF, você pode regenerar os PDFs de referência usados nos testes:

```bash
BFR_GENERATE_EXPECTED=1 pytest tests/test_danfe.py
```

!!! warning
    Só regenere PDFs de referência quando você intencionalmente alterou a saída PDF. Sempre revise a diferença visual antes de fazer o commit.

!!! note
    Não defina `generate=True` diretamente no código de teste — um hook do pre-commit (`no-generate-true`) bloqueia isso. Sempre use a variável de ambiente `BFR_GENERATE_EXPECTED=1`.

## Trabalhando na Documentação

O site de documentação usa [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) com o plugin [mkdocs-static-i18n](https://github.com/ultrabug/mkdocs-static-i18n). Cada página é um par de arquivos: `page.md` (inglês) e `page.pt.md` (português) — mantenha os dois em sincronia ao editar.

```bash
pip install mkdocs-material mkdocs-static-i18n
mkdocs serve  # prévia ao vivo em http://127.0.0.1:8000
```

O site é publicado automaticamente quando alterações em `docs/**` chegam ao branch `main`.

As capturas de tela dos documentos em `docs/assets/screenshots/` são geradas a partir das fixtures de teste. Para regenerá-las após uma mudança de leiaute (requer `poppler-utils` para o `pdftoppm`):

```bash
python scripts/generate_screenshots.py
```

## Enviando Alterações

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b minha-feature`)
3. Faça commit das suas alterações
4. Faça push para seu fork e abra um Pull Request

Certifique-se de que todos os testes passam e os hooks do pre-commit estão limpos antes de enviar.
