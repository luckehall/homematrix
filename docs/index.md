# HomeMatrix

Piattaforma web per il controllo centralizzato di dispositivi domotici multi-host tramite Home Assistant.

## Funzionalità principali

- **Multi-host**: gestisce più istanze Home Assistant da un'unica interfaccia
- **Auth sicura**: JWT + refresh token httpOnly, sessione persistente senza password
- **Approvazione utenti**: flusso registrazione → pending → approvazione admin
- **Proxy sicuro**: il browser non contatta mai direttamente HA

## Navigazione rapida

| Sezione | Contenuto |
|---------|-----------|
| [Architettura](architettura-backend.md) | Stack, struttura directory, flusso dati |
| [Deploy](deploy.md) | Guida installazione su Ubuntu/Debian |
| [API Reference](api/index.md) | Endpoint FastAPI documentati |
| [ADR](adr/index.md) | Decisioni architetturali motivate |
