# ⚠️ QUICK REFERENCE - PMS Stack Project

**Non toccare `WInApp/`**: progetto gestito separatamente da Visual Studio. Modifiche solo se esplicitamente richiesto.

## 📁 PIANI DI PROGETTO

Tutti i piani (plan mode o equivalente) devono essere salvati nella cartella **`piani_sviluppo/`** nella root del progetto (`e:\VMBackups\proxmoxConfig\piani_sviluppo\`).

- Nome file: `YYYY-MM-DD-descrizione-breve.md`
- Creare il file nella cartella prima di uscire dal plan mode
- Non usare la directory default di Claude Code (`~/.claude/plans/`)

Piani esistenti: vedere [`piani_sviluppo/`](piani_sviluppo/)

## 🧭 Terminologia documentazione (standard progetto)

- Usare la terminologia: **documentazione standard**, **funzione standard**, **schema standard progetto**.
- Evitare termini esterni/non allineati allo standard interno (es. "Docblock", "PHPDoc") nelle risposte utente.
- Per classi/metodi PHP, riferirsi al template interno e alle regole in `.github/esperti/esperto_documentazione.md` e `z:\www\templateDoc.php`.

## 🚧 Metodo Unico Documentazione (vincolante)

- Per richieste di documentazione classe/metodo/README usare esclusivamente il **metodo standard progetto**.
- Percorso obbligatorio: router -> scenario `docs` -> regole `.github/esperti/esperto_documentazione.md` -> template `z:\www\templateDoc.php`.
- Non usare metodi alternativi o stile libero quando la richiesta riguarda documentazione standard.
- Se il routing e ambiguo, privilegiare comunque dominio `docs` per tutto cio che e documentazione.

## 🔀 DISPATCHER (BOOTSTRAP)

### Identificazione (prima risposta della sessione)

> **⛔ MANDATORY — BEFORE ANY OTHER ACTION**  
> Alla **prima risposta** di ogni nuova sessione (o dopo un reset contesto),  
> l'identificazione è il **primo step da eseguire** — prima di leggere file,  
> prima di analizzare la richiesta, prima di qualsiasi tool call operativo.  
> Saltare questo step invalida architetturalmente l'intera risposta.

1. Esegui `python .github/router.py --stats` per ottenere le metriche di salute
2. Mostra l'header identificativo con metriche inline:

```
🤖 **[NomeModello]** | Agente: **[agente]** | Priorità: [priority] | Routing: [stats one-liner]
```

Esempio: `🤖 **Claude Opus 4.6** | Agente: **fullstack** | Priorità: high | Routing: 39scn/330kw | overlap:9.7% | [OK]`

Se lo status è `[!!]` (warn) o `[XX]` (crit), segnala esplicitamente quali metriche hanno superato la soglia.

Nelle risposte successive della stessa sessione non serve ripetere.

### Router — modalità
**Esegui il router per OGNI nuova richiesta** salvo eccezione documentata.

| Modalità | Comando | Quando |
|----------|---------|--------|
| Planner | `python .github/router.py "query"` | Prima richiesta, task complessi |
| Diretto | `python .github/router.py --direct "query"` | Prima richiesta, task semplici |
| Follow-up | `python .github/router.py --follow-up "query"` | Richieste successive nella sessione |
| Subagente | `python .github/router.py --subagent "query"` | Per costruire prompt `runSubagent` |
| Stats | `python .github/router.py --stats` | Prima risposta sessione + post-modifica routing map |
| History | `python .github/router.py --history "query"` | Cercare interventi passati simili |
| Log | `python .github/router.py --log-intervention "..."` | Registrare intervento completato |

**Nota**: `copilot-instructions.md` è auto-caricato da VS Code — il router NON lo include nell'output.

> **Self-check**: Se questa è la prima risposta della sessione e non hai ancora mostrato l'header `🤖 **[Modello]** | Agente: ...`, **fermati** ed esegui prima il bootstrap §Identificazione.

**Una risposta senza routing esplicito (o senza eccezione documentata: §summary / §post-task) è da considerarsi architetturalmente invalida.**

### Motivazione routing
Quando il routing non è banale (più scenari plausibili, query multi-dominio), accompagna la scelta con una motivazione breve: quale scenario ha vinto e perché eventuali alternative sono state scartate.

### Ambiguità di routing
Se il router restituisce scenari con punteggi simili o la query copre più domini, l'agente **orchestratore** viene attivato come meta-router e decide l'agente finale, motivando la scelta.

### Separazione contesto cognitivo vs codice operativo
Il **contesto cognitivo** (policy, regole, istruzioni agente) può essere derivato **solo** dai file dichiarati dal router. Il **codice applicativo** (Z:\, sorgenti PHP/JS/SQL) può essere caricato on-demand come materiale operativo durante il lavoro.

### Postflight check (solo task non banali)
Per task multi-step o non banali, verifica a fine risposta:
1. Router usato (o eccezione §summary / §post-task dichiarata)
2. Agente coerente con il task svolto
3. File di contesto conformi all'output del router
4. **Routing coverage**: se il task ha creato nuovi componenti (classi, namespace, script CLI, tabelle DB), verificare che le relative keywords siano coperte da almeno uno scenario in `routing-map.json`. In caso di gap, proporre aggiornamento.
5. **Health check**: se il task ha modificato `routing-map.json` (aggiunta scenari/keywords), eseguire `python .github/router.py --stats` e segnalare se lo status è cambiato rispetto all'inizio sessione.

**Strumenti**:
- `python .github/router.py --stats` — metriche rapide (scenari, keywords, overlap, dimensioni)
- `python .github/router.py --audit` — scansiona il codebase e segnala concetti non coperti dalla routing map
- `python .github/router.py --history "query"` — cerca interventi passati simili nella memory (SQLite + FTS5)

Se il check fallisce, segnala l'incongruenza e correggi.

### Eccezione: conversation summary presente
Quando la conversazione supera la **finestra di contesto** del modello, VS Code genera automaticamente un **conversation summary** che sintetizza il lavoro svolto. Se questo summary include:
- elenco file coinvolti con stato
- ultimo agente attivo
- continuation plan esplicito

allora il router può essere **saltato** a condizione che:
1. La richiesta sia una **continuazione diretta** del piano documentato nel summary
2. L'agente rimanga lo **stesso** (non serve switch)
3. Si dichiari esplicitamente: *"Continuo dal summary precedente, agente: [X]"*

**Nota**: il summary è il meccanismo di continuità tra sessioni lunghe. Quando appare, significa che il contesto originale è stato compresso — il router non avrebbe accesso ai messaggi precedenti e produrrebbe un routing meno informato del summary stesso.

Se la richiesta è **nuova** o cambia dominio → router obbligatorio.

### Eccezione: documentazione post-task
Se la richiesta di documentazione è una **coda naturale** del task appena completato nella stessa sessione (es. "aggiorna avanzamento-lavori", "documenta il fix"), il router può essere **saltato**:
- L'agente attivo possiede già il contesto completo (root cause, file modificati, numeri)
- La documentazione prodotta dall'agente operativo è più accurata (dati di prima mano)

**Condizioni**: documentazione riguarda solo il lavoro appena svolto, agente resta lo stesso, target è file noto (avanzamento-lavori.md, routing-map.json, checklist, ecc.).

Richiesta documentale isolata senza lavoro pregresso → router obbligatorio.

### Subagenti (`runSubagent`)
I subagenti sono **stateless**. Per dargli contesto:
1. Esegui `python .github/router.py --subagent "sotto-task"`
2. Usa `subagent_prompt_prefix` dal JSON come intestazione del prompt
3. Per task strutturali, aggiungi: "Leggi .github/subagent-brief.md"
4. Non passare MAI copilot-instructions.md ai subagenti

### File dispatcher
- [dispatcher.md](dispatcher.md) - Entry point e istruzioni
- [router.py](router.py) - Router principale (7 modalità CLI, scoring, routing, capability)
- [router_audit.py](router_audit.py) - Audit copertura + health stats
- [router_planner.py](router_planner.py) - Integrazione planner
- [interventions.py](interventions.py) - Intervention memory (SQLite + FTS5)
- [mcp_server.py](mcp_server.py) - MCP server (5 tools per integrazione AI nativa)
- [routing-map.json](routing-map.json) - Scenari configurati (39 scenari, 330 keywords)
- [subagent-brief.md](subagent-brief.md) - Contesto compatto per subagenti
- [AGENT_REGISTRY.md](AGENT_REGISTRY.md) - Registry agenti attivi
- [decision-priority.md](decision-priority.md) - Matrice decisioni
- [token-budget-allocation.md](token-budget-allocation.md) - Budget per priorità
- [requirements.txt](requirements.txt) - Dipendenze Python (mcp SDK)


## 📍 ESSENTIALS - Leggere Prima di Ogni Sessione

### What is This?
Stack Docker per gestione CMS + Gestionale Casse (Joomla) + Database MariaDB su VM Ubuntu (Proxmox 100) condivisa via Samba a Windows. Live production con certificati Let's Encrypt pubblici.

### Where Are Things?
| Path | Purpose | Access | Version Control |
|------|---------|--------|------------------|
| `e:\VMBackups\proxmoxConfig` | Docs, scripts, configs | Windows (Explorer) | ✅ Git (GitHub: PSM_Stack) |
| `Z:\` | Application code (Samba) | Windows + SSH | ❌ No Git (manual backups) |
| `~/pms-stack` | Production on VM | SSH only | ❌ No Git (manual backups) |
| `Y:\` | NAS backup (Synology) | Read-only | N/A |

### Quick Status
- ✅ **VM 192.168.2.253**: Production live (Traefik + Docker)
- ✅ **Let's Encrypt**: Auto-renewal active (psm.farmaciacaputo.it + casse.farmaciacaputo.it)
- ✅ **Database backup**: Automatic daily (14:10, 21:10 UTC)
- ✅ **Fatture sync**: Continuous (every minute from WinFarm)
- ⛔ **Casse sync VM↔NAS**: Disabled (ACTIVE_BACKUP=false)
- 📦 **Version Control**: Repository GitHub SOLO per docs/configs (e:\), app code Z:\ NON tracciato (backup manuali)

### SSH Access (Passwordless)
```powershell
ssh_psm massimo@192.168.2.253 "docker ps"
```

## 🚀 QUICK START - First 5 Minutes

### 1. Connect to Systems
```powershell
# Map network drives (run as Admin)
.\scripts\Connect-NetworkDrives.ps1 -Persistent

# Or manual
net use Z: \\192.168.2.253\pms-stack /persistent:yes
net use Y: \\192.168.2.37\web /persistent:yes

# Test SSH (passwordless)
ssh_psm massimo@192.168.2.253 "docker ps"
```

### 2. Check Status
```bash
# SSH to VM
ssh_psm massimo@192.168.2.253

# View running containers
docker compose ps

# Check latest backup
tail ~/pms-stack/backup/db/backup_job.log

# View fatture sync
tail ~/pms-stack/backup/fatture/copy_sync.log
```

### 3. Access Web Interfaces
- **Traefik Dashboard**: https://traefik.psm.local (LAN)
- **PhpMyAdmin**: https://pma.psm.local (LAN)
- **CMS**: https://cms.psm.local (LAN) or https://psm.farmaciacaputo.it (public)
- **Casses**: https://casse.psm.local (LAN) or https://casse.farmaciacaputo.it (public)

---

## ⚡ COMMON TASKS

### Backup & Restore
```bash
# Manual backup (on VM)
python3 ~/pms-stack/backup/db/backup_job.py

# Verify backup integrity
.\scripts\Verify-BackupIntegrity.ps1 -BackupDir "PATH"
```
👉 See [cron-jobs.md](subdetail/cron-jobs.md) for automation

### Docker Operations
```bash
# SSH to VM first, then:
cd ~/pms-stack
docker compose down && docker compose up -d    # Full restart
docker compose logs -f                          # Follow logs
docker exec joomla-apache bash -lc 'rm -rf /var/www/html/cache/*'  # Clear cache
```
👉 See [commands-quick.md](subdetail/commands-quick.md) for more

### Access Credentials
- Database: See `.env` file on VM (SSH required)
- VM SSH: key-based (passwordless) - key at `C:\Users\Massimo\.ssh\vm_cms_key`
- WinFarm: Mount credentials in `.smbcredentials_winfarm` (chmod 600)
👉 See [credentials.md](subdetail/credentials.md) for full details

---

## 📋 BEFORE MAKING PRODUCTION CHANGES

1. **Backup first**: Run [Backup-TraefikConfig.ps1](../scripts/Backup-TraefikConfig.ps1) or manual `docker compose config > backup.yml`
2. **Timestamp backups**: Use ISO format `YYYY-MM-DD-description.ext`
3. **Document motivation**: Add note to [avanzamento-lavori.md](avanzamento-lavori.md) (what + why + next steps)
4. **Test on staging first**: If possible, test config changes before applying to production
5. **Verify DNS** before changing certificates: `nslookup psm.farmaciacaputo.it`

---

## 🛑 CRITICAL CONSTRAINTS

### Let's Encrypt Must Stay Alive
- ❌ **DO NOT** enable mTLS on public routers (blocks ACME challenge)
- ✅ **DO** keep port 80 open for HTTP-01 validation
- ✅ **DO** whitelist Let's Encrypt IPs (151.101.0.0/16, 151.101.192.0/24, 199.232.0.0/16)

### Sync VM↔NAS is DISABLED
- State file frozen since 30 Dec
- Risk of data loss with current sync logic
- VM is source of truth, NAS is backup only (read-only)
- To re-enable: requires MySQL triggers + transaction logging (future improvement)

### Samba/CIFS First Policy
- Edit files on Windows (Z:\) by default
- Changes sync to VM immediately (no git/rsync needed)
- SSH only for runtime operations or when file not on share
- **Never** use SCP to copy files unnecessarily

---

## 📊 PROJECT PROGRESS

### Completed ✅
- Phase 1: Go-live 21 Dec (all casses operational)
- Phase 2.1: Fatture WinFarm sync (18 Dec, active daily)
- Phase 2.3: Security hardening + DNS setup (4 Jan, completed)
- **Phase 2.4 (PRIORITY)**: Scadenziario + Riconciliazione fatture → **31 Jan 2026**