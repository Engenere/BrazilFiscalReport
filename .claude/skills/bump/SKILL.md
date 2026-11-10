---
name: bump
description: Sobe a versão do BrazilFiscalReport (PR de bump) e, depois do merge, cria a tag e o release no GitHub, que dispara a publicação no PyPI. Usar quando o usuário pedir para bumpar versão, lançar/publicar uma versão ou criar o release.
argument-hint: "[patch|minor|major|X.Y.Z]"
disable-model-invocation: true
---

# Bump de versão e release

A versão vive em um único lugar: `__version__` em `brazilfiscalreport/__init__.py`
(o `pyproject.toml` lê de lá). O release no GitHub dispara
`.github/workflows/publish.yml`, que publica no TestPyPI e no PyPI.

Argumento recebido: `$ARGUMENTS`

## 1. Descobrir em que fase está

```bash
git fetch origin --tags
git show origin/main:brazilfiscalreport/__init__.py | head -1   # versão no main
git tag --sort=-v:refname | head -1                             # último release
gh pr list --search "bump in:title" --state open                # bump em aberto?
```

- Versão do main **igual** à última tag → **Fase A** (abrir a PR de bump).
- Já existe PR de bump aberta → informar o estado dela (CI, review) e parar.
- Versão do main **maior** que a última tag → **Fase B** (tag + release).

## Fase A — PR de bump

1. Definir a nova versão:
   - `X.Y.Z` explícito → usar como veio (precisa ser maior que a atual).
   - `patch` / `minor` / `major` → incrementar a partir da versão do main.
   - Sem argumento → listar o que entrou desde a última tag
     (`git log vA.B.C..origin/main --oneline --no-merges`), recomendar um nível
     (só fix/CI/docs → patch; funcionalidade nova → minor; quebra de API → major)
     e confirmar com o usuário antes de seguir.
2. Criar a branch `bump-X.Y.Z` a partir de `origin/main` e alterar apenas a
   linha do `__version__`.
3. Commit: `chore: sobe a versão para X.Y.Z` — sem co-autoria do Claude.
4. Push e PR com o mesmo título. Corpo curto em pt-br: o que esta versão leva
   ao PyPI (PRs relevantes desde a última tag, por número) e a nota
   "depois do merge, criar o release `vX.Y.Z`".
5. Passar o link da PR e parar. Não fazer o merge sem o usuário pedir.

## Fase B — tag e release

1. Conferir antes de qualquer coisa:
   - a PR de bump está mergeada e a versão em `origin/main` é a esperada;
   - a tag `vX.Y.Z` ainda não existe (local nem remoto);
   - o CI do commit do topo do main está verde
     (`gh run list --branch main --limit 5`). Logo depois do merge ele ainda
     está rodando: esperar terminar (`gh run watch <run-id> --exit-status`).
2. Mostrar a prévia das notas, sem criar nada:
   ```bash
   gh api repos/Engenere/BrazilFiscalReport/releases/generate-notes \
     -f tag_name=vX.Y.Z -f target_commitish=main -f previous_tag_name=vA.B.C \
     --jq .body
   ```
3. **Pedir confirmação explícita.** Criar o release publica no PyPI, e uma
   versão publicada no PyPI não pode ser substituída. O pedido de bump não
   vale como autorização para esta etapa.
4. Criar o release (a tag é criada junto, apontando para o main):
   ```bash
   gh release create vX.Y.Z --target main --title vX.Y.Z --generate-notes
   ```
5. Acompanhar a publicação:
   ```bash
   gh run list --workflow publish.yml --limit 1
   gh run watch <run-id> --exit-status
   ```
   O job usa o environment `release`; se ficar aguardando aprovação, avisar o
   usuário. Se falhar, mostrar o log (`gh run view <run-id> --log-failed`) e
   não recriar tag nem release por conta própria.
6. Confirmar que a versão apareceu:
   ```bash
   curl -s https://pypi.org/pypi/brazilfiscalreport/json | jq -r .info.version
   ```
7. Voltar o checkout local para o `main` atualizado e apagar a branch
   `bump-X.Y.Z` local (`git branch -d`).
8. Reportar: link do release, resultado do workflow e versão no PyPI. Lembrar
   que o demo (`Engenere/bfrep-demo`) fixa a versão da lib em
   `requirements.txt` e oferecer a PR que sobe o pin. O índice do PyPI usado
   pelo `pip` pode demorar alguns minutos a listar a versão nova
   (`pip install --no-cache-dir`).
