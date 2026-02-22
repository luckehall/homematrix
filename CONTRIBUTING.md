# Contributing a HomeMatrix

## Flusso di lavoro

1. **Crea un branch** da `develop`
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/nome-feature
   ```

2. **Sviluppa e testa** in locale
   ```bash
   pytest tests/ -v
   ruff check app/
   ```

3. **Apri una Pull Request** verso `develop`  
   Usa il template PR e collega l'issue di riferimento.

4. **Review** — almeno 1 approvazione richiesta per merge su `develop`

5. **Release** — merge da `develop` → `main` attiva il deploy automatico

## Branch naming

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Feature | `feature/*` | `feature/proxy-websocket` |
| Bug fix | `fix/*` | `fix/refresh-token-expiry` |
| Docs | `docs/*` | `docs/adr-auth` |
| Hotfix prod | `hotfix/*` | `hotfix/cors-header` |

## Stile del codice

- Linting: **ruff** (`ruff check app/`)
- Formattazione: **ruff format** (`ruff format app/`)
- Tipo hints obbligatori su tutte le funzioni pubbliche
- Docstring per router e funzioni di servizio

## Commit convention

```
tipo(scope): descrizione breve

feat(auth): aggiungi endpoint refresh token
fix(proxy): correggi timeout WebSocket HA
docs(adr): aggiungi ADR-002 auth JWT
chore(ci): aggiorna action checkout a v4
```

Tipi validi: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`

## Secrets GitHub (per CI/CD)

Configurare in `Settings → Secrets and variables → Actions`:

| Secret | Valore |
|--------|--------|
| `VPS_HOST` | IP o hostname del server di produzione |
| `VPS_USER` | Utente SSH (es. `ubuntu`) |
| `VPS_SSH_KEY` | Chiave privata SSH (PEM, senza passphrase) |
