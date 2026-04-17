# Know-How Exposure Audit — 2026-04-11

## Scope

Audit su repository locale per individuare esposizione di know-how operativo e possibili informazioni sensibili.

## Method

- review rapida pattern sensibili (token/password/secret/bearer/url connessione)
- review manuale file knowledge_base e documentazione operativa
- review hygiene branch/remoti su `origin`

## Findings

### 1) Secret leakage hardcoded

Stato: **non rilevato** hardcoded credibile nel workspace analizzato.

Note:
- i match trovati sono in larga parte termini lessicali (`token`, `password`, `secret`) dentro documentazione, mapping o esempi.
- esempi con placeholder (`<MARIADB_ROOT_PASSWORD>`, `<SERVER_IP>`) risultano redatti e non credenziali reali.

### 2) Know-how operativo esposto (infra playbook dettagliato)

Stato: **rischio medio** (non segreti, ma procedure e topologia operativa dettagliata).

Aree principali:
- `knowledge_base/psm_stack/esperti/esperto_orchestratore.md`
- `knowledge_base/psm_stack/esperti/esperto_sistemista.md`

Raccomandazione:
- mantenere pubblico solo contenuto generalizzabile
- spostare in private-core runbook con comandi environment-specific o struttura operativa proprietaria

### 3) Branch hygiene su origin

Stato: **da consolidare**

Esito audit:
- prune refs remoti eseguito (`git fetch --prune origin` e `git remote prune origin`)
- branch remoti non mergeati rispetto a `origin/master` ancora presenti (docs/feature/feat)

Raccomandazione:
- definire policy di retention branch e cancellazione post-merge
- eliminare branch stale solo dopo verifica PR/owner

### 4) Commit accidentali di file locali

Stato: **mitigato parzialmente**

Azione applicata:
- aggiornato `.gitignore` con `.continue/` e `.continuerules`

## Priority Actions

1. Adottare il piano `p0-knowhow-protection.plan`.
2. Creare `OPEN_CORE_BOUNDARY.md` con classificazione asset `public/internal/private`.
3. Introdurre controllo CI (regex secrets + allowlist).
4. Eseguire branch cleanup guidato da PR state (non solo da merge ancestry).

## Audit Confidence

Media: controllo statico locale + review manuale campionata.
Per confidenza alta: aggiungere scan GitHub secret scanning su diff PR e baseline periodica.
