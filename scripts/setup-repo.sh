#!/bin/bash
# ─────────────────────────────────────────────────────────────
# setup-repo.sh — Inizializza il repo git e lo pusha su GitHub
# Uso: ./scripts/setup-repo.sh TUO-USERNAME
# ─────────────────────────────────────────────────────────────

set -e

GITHUB_USERNAME="${1:-TUO-USERNAME}"
REPO_NAME="homematrix"

echo "⌂ HomeMatrix — Setup Repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Inizializza git
echo "→ Inizializzazione git..."
git init
git config core.autocrlf false

# 2. Branch main come default
git checkout -b main

# 3. Primo commit
echo "→ Primo commit..."
git add .
git commit -m "chore: initial project structure

- Backend FastAPI skeleton
- GitHub Actions (CI, deploy, docs)
- Issue templates e PR template
- MkDocs per GitHub Pages
- ADR-001: scelta FastAPI"

# 4. Crea branch develop
git checkout -b develop
git checkout main

# 5. Aggiungi remote
echo "→ Collegamento a GitHub..."
git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo ""
echo "✓ Repository configurato!"
echo ""
echo "Prossimi passi:"
echo "  1. Crea il repo su GitHub (PRIVATO):"
echo "     https://github.com/new"
echo "     Nome: ${REPO_NAME} | Visibilità: Private | Nessun file iniziale"
echo ""
echo "  2. Pusha il codice:"
echo "     git push -u origin main"
echo "     git push -u origin develop"
echo ""
echo "  3. Configura i Secrets GitHub:"
echo "     Settings → Secrets and variables → Actions"
echo "     VPS_HOST, VPS_USER, VPS_SSH_KEY"
echo ""
echo "  4. Abilita GitHub Pages:"
echo "     Settings → Pages → Source: GitHub Actions"
echo ""
echo "  5. Proteggi il branch main:"
echo "     Settings → Branches → Add rule → main"
echo "     ✓ Require PR before merging"
echo "     ✓ Require status checks (CI Backend)"
