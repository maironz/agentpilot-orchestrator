# CLI Options Matrix

This page explains what each main CLI option does in practical terms.

Goal: make it easy to predict behavior before running a command.

## Legend

- Target project path: the folder passed with `--target` (or current folder if omitted).
- Generated orchestration files are usually under `<target>/.github/`.
- "Writes files" means filesystem changes happen.
- "No file writes" means read-only behavior.

## Main command modes (one at a time)

These options are mutually exclusive. Use only one per command.

| Option | What it does (plain language) | File impact |
|---|---|---|
| `--direct` | Generates orchestration assets without interactive questions. | Writes files in `<target>/.github/` (plus backup metadata when needed). |
| `--dry-run` | Simulates generation and shows what would be created. | No file writes. |
| `--check` | Runs integrity checks on an existing project structure. | No file writes. |
| `--update` | Updates core orchestrator files in an existing project. | Writes/overwrites core files in `<target>/.github/`; creates backup in `<target>/.github/.rgen-backups/`. |
| `--update --flat` | Updates core files for legacy flat layout projects. | Writes/overwrites core files in `<target>/`; creates backup in `<target>/.rgen-backups/`. |
| `--update --force` (when `.github` is missing) | Tries self-update of the local tool repository after explicit confirmation. | Updates local repository of the tool; no project generation. |
| `--history` | Shows generation/update history (text or json). | No file writes unless `--history-output` is set. |
| `--rollback --to <generation_id>` | Restores files to a previous generation snapshot. | Writes/restores/removes files based on backup manifest. |
| `--restore` | Restores backup content by timestamp. | Writes restored files to target project path. |
| `--list-patterns` | Lists available local patterns. | No file writes. |
| `--search-patterns <query>` | Searches patterns in local marketplace index. | No file writes. |
| `--download <source>` | Installs a pattern pack from local path/zip/url/registry id. | Writes files into install directory (default knowledge_base). |
| `--suggest-scenarios` | Suggests new routing scenarios from intervention history. | No file writes unless `--suggest-output` is set. |
| `--cost-report` | Estimates monthly token cost by scenario. | No file writes unless `--cost-output` is set. |
| `--roi-benchmark` | Compares no-routing vs free-routing vs paid-routing costs. | No file writes unless `--roi-output` is set. |

## Generation input options

These options shape generation behavior, mainly with `--direct`.

| Option | What it controls | Typical effect |
|---|---|---|
| `--pattern <id>` | Uses a predefined pattern (example: `python_api`). | Produces standard scenario map and agent files from selected pattern. |
| `--name <project_name>` | Project name used by templates/metadata. | Changes generated text/content placeholders. |
| `--target <path>` | Output folder for generated/updated files. | Determines where files are created or updated. |
| `--language it|en|es|fr` | Output language for generated agent content. | Changes language of generated text assets. |
| `--tech a,b,c` | Technology list for generation from scratch (without pattern). | Influences generated guides and routing hints. |
| `--domains a,b,c` | Domain keywords for generation from scratch (without pattern). | Influences generated scenarios and context focus. |
| `--kb <path>` | Custom knowledge base path. | Loads patterns from custom location. |
| `--core <path>` | Custom core files source path. | Copies core files from custom location during generation/update. |

## History, backup, and rollback options

| Option | Used with | Effect |
|---|---|---|
| `--history-format text|json` | `--history` | Chooses output format. |
| `--history-output <file>` | `--history` | Saves history payload to file. |
| `--show-diffs` | `--history` | Adds per-file change details and current state. |
| `--history-limit <n>` | `--history`, `--suggest-scenarios` | Limits number of records processed or shown. |
| `--to <generation_id>` | `--rollback` | Required rollback target generation id. |
| `--force` | `--rollback` | Allows rollback even on manually modified files. |
| `--timestamp <backup_id>` | `--restore` | Restores one specific backup snapshot. |

## Scenario suggestion options

| Option | Used with | Effect |
|---|---|---|
| `--min-cluster-size <n>` | `--suggest-scenarios` | Sets minimum cluster size for candidate scenarios. |
| `--similarity-threshold <0..1>` | `--suggest-scenarios` | Controls semantic grouping strictness. |
| `--min-confidence <0..1>` | `--suggest-scenarios` | Drops suggestions below confidence threshold. |
| `--include-matched` | `--suggest-scenarios` | Includes already-categorized interventions. |
| `--suggest-format json|text` | `--suggest-scenarios` | Chooses output format. |
| `--suggest-output <file>` | `--suggest-scenarios` | Saves suggestions to file. |

## Cost and ROI options

| Option | Used with | Effect |
|---|---|---|
| `--cost-model <model>` | `--cost-report` | Selects pricing model profile. |
| `--cost-monthly-queries <n>` | `--cost-report` | Sets query volume for monthly estimate. |
| `--pricing-db <file>` | `--cost-report` | Uses custom pricing database JSON. |
| `--cost-format json|text` | `--cost-report` | Chooses output format. |
| `--cost-output <file>` | `--cost-report` | Saves report JSON to file. |
| `--roi-format json|text` | `--roi-benchmark` | Chooses output format. |
| `--roi-output <file>` | `--roi-benchmark` | Saves ROI report JSON to file. |
| `--roi-scale <n>` | `--roi-benchmark` | Multiplies benchmark batch size. |

## Practical examples

### Generate a project (non-interactive)

```powershell
python -m rgen.cli --direct --pattern python_api --name my-app --target my-app
```

Expected effect: writes orchestration files in `my-app/.github/` and runs self-check.

### Simulate generation only

```powershell
python -m rgen.cli --dry-run --pattern python_api --name my-app --target my-app
```

Expected effect: prints planned files, no writes.

### Update core files in existing project

```powershell
python -m rgen.cli --update --target my-app
```

Expected effect: updates core files in `my-app/.github/` and stores backup snapshots.

## Extra use cases: folder name and location variations

This section adds many practical examples where only folder name and position change.

### 1) Sibling folder (safe default for beginners)

```powershell
cd ..
python -m rgen.cli --direct --pattern python_api --name shop-api --target shop-api
```

Expected effect: creates `shop-api/.github/` in the parent directory.

### 2) Nested folder inside a workspace area

```powershell
python -m rgen.cli --direct --pattern python_api --name billing --target workspaces/billing
```

Expected effect: creates `workspaces/billing/.github/`.

### 3) Deep nested folder for environment split

```powershell
python -m rgen.cli --direct --pattern python_api --name platform --target environments/dev/platform
```

Expected effect: creates `environments/dev/platform/.github/`.

### 4) Prefix naming convention for teams

```powershell
python -m rgen.cli --direct --pattern python_api --name team-alpha-api --target team-alpha-api
```

Expected effect: target folder uses team naming convention and contains `.github/` routing files.

### 5) Suffix naming convention for stage

```powershell
python -m rgen.cli --direct --pattern python_api --name auth-staging --target auth-staging
```

Expected effect: staging-oriented folder with standard `.github/` layout.

### 6) Monorepo service path

```powershell
python -m rgen.cli --direct --pattern python_api --name gateway --target services/gateway
```

Expected effect: routing files end up in `services/gateway/.github/`.

### 7) Monorepo app path (frontend/backend mixed repo)

```powershell
python -m rgen.cli --direct --pattern node_ts --name dashboard --target apps/dashboard
```

Expected effect: routing files end up in `apps/dashboard/.github/`.

### 8) Infrastructure module path

```powershell
python -m rgen.cli --direct --pattern psm_stack --name infra-core --target infra/infra-core
```

Expected effect: routing files end up in `infra/infra-core/.github/`.

### 9) Current folder generation (advanced users)

```powershell
python -m rgen.cli --direct --pattern python_api --name local-test --target .
```

Expected effect: `.github/` is created in current working directory.

### 10) Absolute path target (Windows)

```powershell
python -m rgen.cli --direct --pattern python_api --name crm-api --target C:/Projects/client-a/crm-api
```

Expected effect: routing files are created under `C:/Projects/client-a/crm-api/.github/`.

### 11) Absolute path target (another drive)

```powershell
python -m rgen.cli --direct --pattern python_api --name data-pipeline --target D:/labs/data-pipeline
```

Expected effect: routing files are created under `D:/labs/data-pipeline/.github/`.

### 12) Dry-run before writing in a sensitive path

```powershell
python -m rgen.cli --dry-run --pattern python_api --name finance-api --target ../finance-api
```

Expected effect: preview only, no file writes.

### 13) Update existing project in nested path

```powershell
python -m rgen.cli --update --target services/payments
```

Expected effect: updates `services/payments/.github/*` with backup snapshots.

### 14) Update existing project in current folder

```powershell
python -m rgen.cli --update --target .
```

Expected effect: updates `./.github/*` if present.

### 15) Legacy flat layout update (no `.github` nesting)

```powershell
python -m rgen.cli --update --flat --target legacy-router
```

Expected effect: core files are written directly in `legacy-router/` and backup is in `legacy-router/.rgen-backups/`.

### 16) Scratch generation from technologies/domains in custom folder

```powershell
python -m rgen.cli --direct --name custom-ops --target experiments/custom-ops --tech python,fastapi,redis --domains api,auth,caching
```

Expected effect: creates `experiments/custom-ops/.github/` based on provided stack/domains.

### 17) Language-specific output in named folder

```powershell
python -m rgen.cli --direct --pattern python_api --name support-it --target support-it --language it
```

Expected effect: same folder behavior, but generated text assets are in Italian.

### 18) Marketplace pattern install to custom folder name

```powershell
python -m rgen.cli --download owner/repo:main --install-dir custom-kb
```

Expected effect: pattern pack is installed under `custom-kb/`.

### 19) Verify structure after generation in custom path

```powershell
python -m rgen.cli --check --target apps/customer-portal
```

Expected effect: read-only validation of `apps/customer-portal` structure.

### 20) Safe rollback in a renamed project folder

```powershell
python -m rgen.cli --history --target renamed-project
python -m rgen.cli --rollback --target renamed-project --to <generation_id>
```

Expected effect: history lookup and selective restore in `renamed-project/`.

## Quick decision guide for folder choice

- Use sibling folder targets (example: `--target my-project`) when starting from scratch.
- Use nested targets (example: `--target services/my-service`) in monorepos.
- Use `--target .` only when you are fully sure about current directory.
- Use `--dry-run` first when target path is sensitive or shared.
- Use `--update --flat` only for legacy projects that keep routing files in root.
