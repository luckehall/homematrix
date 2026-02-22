# ⌂ HomeMatrix

> Piattaforma web per il controllo centralizzato di dispositivi domotici multi-host tramite Home Assistant.

[![CI Backend](https://github.com/TUO-USERNAME/homematrix/actions/workflows/ci-backend.yml/badge.svg)](https://github.com/TUO-USERNAME/homematrix/actions)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://TUO-USERNAME.github.io/homematrix)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Panoramica

HomeMatrix è una web app che funge da gateway sicuro tra utenti e istanze Home Assistant remote. Gestisce autenticazione, autorizzazione utenti e proxy verso più host HA tramite long-lived token.

**Flusso principale:**
1. L'utente visita l'URL e si registra → stato *pending*
2. L'admin approva la richiesta dalla dashboard
3. Al successivo accesso, l'utente viene riconosciuto automaticamente (sessione persistente httpOnly)

## Stack

| Layer | Tecnologia |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 15 |
| Cache/Session | Redis 7 |
| Web Server | Nginx + SSL |
| HA Integration | Long-lived token (REST + WebSocket) |
| CI/CD | GitHub Actions |

## Struttura del Repository

```
homematrix/
├── backend/          # FastAPI app
│   ├── app/
│   │   ├── auth/     # Registrazione, login, refresh token
│   │   ├── hosts/    # Proxy verso Home Assistant
│   │   └── admin/    # Gestione utenti e host
│   ├── alembic/      # Migrazioni DB
│   └── tests/
├── frontend/         # UI React/Vue (da sviluppare)
├── docs/             # Documentazione tecnica
│   ├── adr/          # Architecture Decision Records
│   └── api/          # Specifiche OpenAPI
├── .github/
│   ├── workflows/    # CI/CD GitHub Actions
│   └── ISSUE_TEMPLATE/
└── scripts/          # Script di deploy e utilità
```

## Quick Start (Sviluppo Locale)

```bash
# 1. Clona il repo
git clone https://github.com/TUO-USERNAME/homematrix.git
cd homematrix

# 2. Backend
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Compila le variabili

# 3. DB e Redis (Docker per sviluppo locale)
docker compose -f docker-compose.dev.yml up -d

# 4. Migrazioni e avvio
alembic upgrade head
uvicorn app.main:app --reload
```

## Documentazione

- [Architettura Backend](docs/architettura-backend.md)
- [API Reference](docs/api/) — generata da OpenAPI
- [Architecture Decision Records](docs/adr/)
- [Guida al Deploy](docs/deploy.md)
- [Contributing](CONTRIBUTING.md)

## Branching Strategy

```
main          ← produzione (protetto, solo PR)
develop       ← integrazione
feature/*     ← nuove funzionalità
fix/*         ← bug fix
docs/*        ← solo documentazione
```

## Licenza

MIT — vedi [LICENSE](LICENSE)
