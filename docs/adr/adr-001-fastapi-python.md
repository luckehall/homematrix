# ADR-001 — Scelta FastAPI come framework backend

**Data:** 2026-02-22  
**Stato:** ✅ Accettato

## Contesto

Il backend deve fungere da proxy verso Home Assistant (HTTP + WebSocket), gestire autenticazione JWT e operazioni asincrone verso PostgreSQL e Redis. È richiesta performance su connessioni concorrenti.

## Decisione

Utilizziamo **FastAPI** con **uvicorn** come ASGI server.

## Motivazioni

- Async nativo: gestisce proxy WS e chiamate concorrenti a HA senza bloccare il thread
- Generazione automatica OpenAPI / Swagger — documentazione API sempre aggiornata
- Pydantic integrato — validazione input robusta e type-safe
- Ecosistema Python maturo per integrazione con HA (librerie esistenti)

## Alternative considerate

| Alternativa | Motivo scartato |
|------------|----------------|
| Node.js / Express | Nessun vantaggio rispetto a FastAPI async; team più familiare con Python |
| Django REST | Sincrono per default, overhead per un'app API-only |
| Go (Gin) | Performance superiore ma complessità sviluppo sproporzionata per il progetto |

## Conseguenze

- Richiede Python 3.11+ sul server
- I test devono usare `pytest-asyncio`
- Deployment tramite uvicorn con 4 worker (systemd)
