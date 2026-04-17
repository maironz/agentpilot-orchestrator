"""CLI entry point for AgentPilot Orchestrator."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from rgen import __version__

# ---------------------------------------------------------------------------
# Project-root relative paths (resolved at import time)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_PROJECT_ROOT = _HERE.parent
_DEFAULT_KB = _PROJECT_ROOT / "knowledge_base"
_DEFAULT_CORE = _PROJECT_ROOT / "core"


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``rgen`` command.

    Returns:
        Exit code (0 = success, non-zero = failure).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_patterns:
            return _cmd_list_patterns(args)
        if args.check:
            return _cmd_check(args)
        if args.suggest_scenarios:
            return _cmd_suggest_scenarios(args)
        if args.history:
            return _cmd_history(args)
        if args.rollback:
            return _cmd_rollback(args)
        if args.search_patterns:
            return _cmd_search_patterns(args)
        if args.download:
            return _cmd_download(args)
        if args.restore:
            return _cmd_restore(args)
        if args.update:
            return _cmd_update(args)
        if args.cost_report:
            return _cmd_cost_report(args)
        if args.roi_benchmark:
            return _cmd_roi_benchmark(args)
        if args.direct or args.dry_run:
            return _cmd_direct(args)
        return _cmd_interactive(args)
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.")
        return 1
    except Exception as exc:
        print(f"[ERRORE] {exc}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _cmd_list_patterns(args: argparse.Namespace) -> int:
    from rgen.adapter import PatternLoader

    kb = Path(args.kb or _DEFAULT_KB)
    loader = PatternLoader(kb)
    patterns = loader.list_patterns()
    if not patterns:
        print(f"Nessun pattern trovato in: {kb}")
        return 0
    print(f"Pattern disponibili in {kb}:\n")
    for pid in patterns:
        data = loader.load(pid)
        meta = data["metadata"]
        tech = ", ".join(meta.get("tech_stack", []))
        print(f"  {pid:<25} {meta['name']}")
        print(f"  {'':25} Stack: {tech}\n")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    from rgen.self_checker import SelfChecker

    target = Path(args.target or ".")
    if not target.exists():
        print(f"[ERRORE] Directory non trovata: {target}", file=sys.stderr)
        return 2

    print(f"Self-check su: {target}")
    checker = SelfChecker(target)
    report = checker.run_all()

    for item in report.passed:
        print(f"  [OK] {item}")
    for item in report.warnings:
        print(f"  [WARN] {item}")
    for item in report.errors:
        print(f"  [FAIL] {item}", file=sys.stderr)

    overall = "OK" if report.overall else "FAILED"
    print(f"\nRisultato: {overall} — {len(report.passed)} pass, {len(report.warnings)} warn, {len(report.errors)} errori")
    return 0 if report.overall else 1


def _cmd_suggest_scenarios(args: argparse.Namespace) -> int:
    """Suggests candidate scenarios from intervention history."""
    from rgen.interventions import InterventionStore

    try:
        from rgen.premium_runtime_loader import load_scenario_clusterer
    except ModuleNotFoundError:
        load_scenario_clusterer = None

    if load_scenario_clusterer is None:
        print(
            "[ERRORE] Scenario clustering non disponibile (modulo premium non installato).",
            file=sys.stderr,
        )
        return 2

    ScenarioClusterer = load_scenario_clusterer()
    if ScenarioClusterer is None:
        print("[ERRORE] Scenario clustering non disponibile.", file=sys.stderr)
        return 2

    target = Path(args.target or ".")
    db_path = target / ".github" / "interventions.db"
    store = InterventionStore(db_path=db_path)
    try:
        clusterer = ScenarioClusterer(
            store,
            min_cluster_size=args.min_cluster_size,
            similarity_threshold=args.similarity_threshold,
            min_confidence=args.min_confidence,
        )
        suggestions = clusterer.suggest_scenarios(
            limit=args.history_limit,
            unmatched_only=not args.include_matched,
        )
    finally:
        store.close()

    payload = json.dumps(suggestions, indent=2, ensure_ascii=False)
    if args.suggest_output:
        output_path = Path(args.suggest_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")

    if args.suggest_format == "text":
        print(_render_scenario_suggestions_text(suggestions))
    else:
        print(payload)
    return 0


def _render_scenario_suggestions_text(suggestions: list[dict]) -> str:
    """Render human-friendly preview for scenario suggestions."""
    if not suggestions:
        return "No scenario suggestions found."

    lines = [f"Suggested scenarios: {len(suggestions)}"]
    for idx, suggestion in enumerate(suggestions, 1):
        lines.append(f"{idx}. {suggestion['suggested_scenario']}")
        lines.append(f"   confidence: {suggestion['confidence']:.0%}")
        lines.append(f"   size: {suggestion['size']} queries")
        lines.append(f"   keywords: {', '.join(suggestion['keywords'][:5])}")
    return "\n".join(lines)


def _resolve_backup_root(target: Path) -> Path:
    github_root = target / ".github" / ".rgen-backups"
    if github_root.exists() or (target / ".github").exists():
        return github_root
    return target / ".rgen-backups"


def _cmd_update(args: argparse.Namespace) -> int:
    """Copies updated core files to an existing project without full regeneration.

    Uses ``--flat`` for projects where core files live directly in the target
    directory (not in ``.github/``), as in legacy flat-layout projects.
    """
    import shutil
    from rgen.backup import BackupEngine
    from rgen.writer import Writer

    target = Path(args.target or ".")
    core = Path(args.core or _DEFAULT_CORE)
    flat = getattr(args, "flat", False)

    if flat:
        # Legacy flat layout: core files live directly in target_dir
        backup_engine = BackupEngine(
            target / ".rgen-backups",
            project_root=target,
            command="update-flat",
            target=str(target),
        )
        written, errors = [], []
        for name in Writer.CORE_FILES:
            src = core / name
            if not src.exists():
                print(f"  [SKIP]   {name} (non trovato in core/)")
                continue
            dest = target / name
            try:
                existed_before = dest.exists()
                backup_engine.backup_if_exists(dest)
                shutil.copy2(src, dest)
                backup_engine.record_written_file(dest, existed_before=existed_before)
                written.append(name)
                print(f"  [UPDATE] {name}")
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                print(f"  [ERRORE] {name}: {exc}", file=sys.stderr)
        if errors:
            return 1
        print(f"\n{len(written)} file aggiornati in {target}  (backup in .rgen-backups/)")
        return 0

    github_dir = target / ".github"
    if not github_dir.exists():
        print(
            f"[ERRORE] Nessuna directory .github trovata in: {target}\n"
            "Usa 'rgen --direct' per creare un nuovo progetto, o '--flat' per layout root.",
            file=sys.stderr,
        )
        return 2

    writer = Writer(core)
    result = writer.copy_core_files(target)

    for f in result.files_written:
        print(f"  [UPDATE] {f.name}")
    for f in result.files_skipped:
        print(f"  [SKIP]   {Path(f).name} (non trovato in core/)")
    for err in result.errors:
        print(f"  [ERRORE] {err}", file=sys.stderr)

    if result.errors:
        return 1

    n = len(result.files_written)
    print(f"\n{n} file aggiornati in {github_dir}  (backup in .github/.rgen-backups/)")
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    from rgen.backup import BackupEngine

    target = Path(args.target or ".")
    backup_root = _resolve_backup_root(target)
    engine = BackupEngine(backup_root, project_root=target)
    history = engine.history(limit=args.history_limit if args.history_limit > 0 else None)

    if not history:
        print(f"Nessuna generazione trovata in: {backup_root}")
        return 0

    show_diffs = bool(args.show_diffs)
    if args.history_format == "json":
        payload: list[dict[str, object]] = []
        for item in history:
            entry = dict(item)
            if show_diffs:
                entry["diff"] = engine.describe_generation(str(item["generation_id"]))
            payload.append(entry)
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        if args.history_output:
            output_path = Path(args.history_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0

    print(f"Generazioni disponibili in {backup_root}:\n")
    for item in history:
        generation_id = str(item["generation_id"])
        print(
            f"  {generation_id} | written={item.get('written_count', 0)} | "
            f"updated={item.get('updated_count', 0)} | command={item.get('command') or '-'}"
        )
        if show_diffs:
            for change in engine.describe_generation(generation_id):
                print(
                    f"    - {change['change']}: {change['path']} "
                    f"[{change['current_state']}]"
                )
    if args.history_output:
        output_path = Path(args.history_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(history, indent=2, ensure_ascii=False)
        output_path.write_text(serialized + "\n", encoding="utf-8")
    return 0


def _cmd_rollback(args: argparse.Namespace) -> int:
    from rgen.backup import BackupEngine

    if not args.to:
        print("[ERRORE] --rollback richiede --to <generation_id>", file=sys.stderr)
        return 2

    target = Path(args.target or ".")
    backup_root = _resolve_backup_root(target)
    engine = BackupEngine(backup_root, project_root=target)

    try:
        report = engine.rollback(args.to, force=args.force)
    except FileNotFoundError as exc:
        print(f"[ERRORE] {exc}", file=sys.stderr)
        return 2

    print(f"Rollback completato per {args.to}")
    print(f"  Ripristinati: {len(report['restored'])}")
    print(f"  Rimossi:      {len(report['removed'])}")
    print(f"  Saltati:      {len(report['skipped_manual'])}")
    print(f"  Mancanti:     {len(report['missing'])}")

    for rel_path in report["skipped_manual"]:
        print(f"  [SKIP] {rel_path} (modifica manuale rilevata)")
    return 0


def _cmd_search_patterns(args: argparse.Namespace) -> int:
    from rgen.pattern_registry import PatternRegistry

    registry = PatternRegistry()
    results = registry.search(args.search_patterns)
    if not results:
        print("Nessun pattern trovato.")
        return 0

    for item in results:
        raw_tags = item.get("tags", [])
        tags = ", ".join(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ""
        print(f"  {item.get('id', '-'):<24} {item.get('name', '-')}")
        if tags:
            print(f"  {'':24} Tags: {tags}")
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    from rgen.pattern_registry import PatternRegistry

    install_dir = Path(args.install_dir or _DEFAULT_KB)
    registry = PatternRegistry()
    result = registry.install(args.download, install_dir=install_dir)

    print(f"Pattern installato: {result['id']}@{result['version']}")
    print(f"Destinazione: {result['installed_path']}")
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    from rgen.backup import BackupEngine

    target = Path(args.target or ".")
    backup_root = _resolve_backup_root(target)
    restore_target = target / ".github" if backup_root.parent.name == ".github" else target
    engine = BackupEngine(backup_root, project_root=target)

    if args.timestamp:
        try:
            restored = engine.restore(args.timestamp, restore_target)
            print(f"Ripristinati {len(restored)} file da '{args.timestamp}'")
        except FileNotFoundError as exc:
            print(f"[ERRORE] {exc}", file=sys.stderr)
            return 2
    else:
        backups = engine.list_backups()
        if not backups:
            print(f"Nessun backup trovato in: {backup_root}")
            return 0
        print(f"Backup disponibili in {backup_root}:\n")
        for b in backups:
            files = [f for f in b.rglob("*") if f.is_file()]
            print(f"  {b.name} ({len(files)} file)")
        print(f"\nUso: rgen --restore --target {target} --timestamp <nome>")
    return 0


def _cmd_direct(args: argparse.Namespace) -> int:
    """Non-interactive generation using CLI arguments."""
    from rgen.questionnaire import Questionnaire
    from rgen.language_detector import LanguageDetector

    overrides: dict[str, str] = {"use_pattern": "y" if args.pattern else "n"}
    if args.pattern:
        overrides["pattern_id"] = args.pattern
    if args.name:
        overrides["project_name"] = args.name
    if args.target:
        overrides["target_path"] = args.target
    if args.tech:
        overrides["tech_stack"] = args.tech
    if args.domains:
        overrides["domain_keywords"] = args.domains

    # Detect or use explicit language
    language = args.language
    if not language:
        detector = LanguageDetector()
        # Try to detect from target path if available
        metadata = overrides if args.name else {}
        language = detector.detect(metadata=metadata)

    kb = Path(args.kb or _DEFAULT_KB)
    core = Path(args.core or _DEFAULT_CORE)

    q = Questionnaire(kb)
    profile = q.run_with_defaults(overrides)

    return _run_generation(profile, core, kb=kb, dry_run=args.dry_run, language=language)


def _cmd_interactive(args: argparse.Namespace) -> int:
    """Full interactive interview."""
    from rgen.questionnaire import Questionnaire

    kb = Path(args.kb or _DEFAULT_KB)
    core = Path(args.core or _DEFAULT_CORE)
    language = args.language or "en"  # Default to English if not specified

    q = Questionnaire(kb)
    profile = q.run()

    print(f"\nProfilo raccolto:")
    print(f"  Progetto: {profile.project_name}")
    print(f"  Pattern:  {profile.pattern_id or 'da zero'}")
    print(f"  Output:   {profile.target_path}")
    print(f"  Lingua:   {language.upper()}")

    confirm = input("\nProcedere con la generazione? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        print("Annullato.")
        return 0
    return _run_generation(profile, core, kb=kb, dry_run=False, language=language)


# ---------------------------------------------------------------------------
# Shared generation pipeline
# ---------------------------------------------------------------------------

def _run_generation(profile, core: Path, kb: Path = _DEFAULT_KB, dry_run: bool = False, language: str = "en") -> int:
    from rgen.adapter import Adapter
    from rgen.writer import Writer
    from rgen.self_checker import SelfChecker

    adapter = Adapter(kb, language=language)
    files = adapter.adapt(profile)

    if dry_run:
        from rgen.writer import Writer
        core_files = [f".github/{name}" for name in Writer.CORE_FILES]
        total = len(files) + len(core_files)
        print(f"\n[DRY-RUN] Verrebbero scritti {total} file in: {profile.target_path}")
        print(f"[DRY-RUN] Lingua: {language.upper()}")
        for path in sorted(files):
            size = len(files[path])
            print(f"  {path} ({size} byte)")
        for cf in core_files:
            print(f"  {cf} (core)")
        return 0

    writer = Writer(core)
    result = writer.generate(files, profile.target_path)

    print(f"\nGenerazione completata:")
    print(f"  Scritti:  {len(result.files_written)} file")
    print(f"  Saltati:  {len(result.files_skipped)} file")
    print(f"  Lingua:   {language.upper()}")
    if result.errors:
        for err in result.errors:
            print(f"  [ERRORE] {err}", file=sys.stderr)
        return 1

    # Post-generation self-check
    print("\nSelf-check in corso...")
    checker = SelfChecker(profile.target_path)
    report = checker.run_all()
    for w in report.warnings:
        print(f"  [WARN] {w}")
    for e in report.errors:
        print(f"  [FAIL] {e}", file=sys.stderr)
    overall = "OK" if report.overall else "FAILED"
    print(f"  Risultato: {overall} ({len(report.passed)}/8 check)")

    return 0 if result.success and report.overall else 1


def _cmd_cost_report(args: argparse.Namespace) -> int:
    """Stima il costo mensile per scenario da intervention history."""
    from rgen.cost_estimator import CostEstimator
    from rgen.interventions import InterventionStore

    target = Path(args.target or ".")
    db_path = target / ".github" / "interventions.db"

    store: InterventionStore | None = None
    if db_path.exists():
        store = InterventionStore(db_path=db_path)

    try:
        estimator = CostEstimator(
            store=store,
            model=getattr(args, "cost_model", "gpt-4o-mini"),
            monthly_queries=getattr(args, "cost_monthly_queries", 1000),
            pricing_db_path=getattr(args, "pricing_db", None),
        )
        report = estimator.estimate()
    finally:
        if store is not None:
            store.close()

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    cost_output = getattr(args, "cost_output", None)
    if cost_output:
        output_path = Path(cost_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
        print(f"[OK] Report scritto su: {output_path}")

    cost_format = getattr(args, "cost_format", "json")
    if cost_format == "text":
        print(_render_cost_report_text(report))
    else:
        print(payload)
    return 0


def _cmd_roi_benchmark(args: argparse.Namespace) -> int:
    """Run ROI benchmark for live sales/demo comparison."""
    from rgen.roi_benchmark import compare_roi_strategies

    scale = max(getattr(args, "roi_scale", 1), 1)
    results = compare_roi_strategies()
    base = {k: asdict(v) for k, v in results.items()}

    scaled = {}
    for key, data in base.items():
        scaled[key] = {
            "strategy": data["strategy"],
            "requests": data["requests"] * scale,
            "llm_cost_usd": round(data["llm_cost_usd"] * scale, 4),
            "op_cost_usd": round(data["op_cost_usd"] * scale, 4),
            "total_cost_usd": round(data["total_cost_usd"] * scale, 4),
        }

    deltas = {
        "free_vs_no_routing_usd": round(
            scaled["no_routing"]["total_cost_usd"] - scaled["free_routing"]["total_cost_usd"],
            4,
        ),
        "paid_vs_free_usd": round(
            scaled["free_routing"]["total_cost_usd"] - scaled["paid_routing"]["total_cost_usd"],
            4,
        ),
        "paid_vs_no_routing_usd": round(
            scaled["no_routing"]["total_cost_usd"] - scaled["paid_routing"]["total_cost_usd"],
            4,
        ),
    }

    report = {
        "benchmark_name": "roi_routing_comparison",
        "scale_batches": scale,
        "per_batch_requests": 10,
        "strategies": scaled,
        "deltas": deltas,
    }

    payload = json.dumps(report, indent=2, ensure_ascii=False)

    roi_output = getattr(args, "roi_output", None)
    if roi_output:
        output_path = Path(roi_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
        print(f"[OK] ROI report scritto su: {output_path}")

    roi_format = getattr(args, "roi_format", "json")
    if roi_format == "text":
        print(_render_roi_benchmark_text(report))
    else:
        print(payload)
    return 0


def _render_cost_report_text(report: dict) -> str:
    """Render leggibile del cost report su stdout."""
    lines = [
        f"Cost Report — model: {report['model']} | monthly queries: {report['monthly_queries']}",
        f"Data source: {report['data_source']}",
        f"Total estimated monthly cost: ${report['total_estimated_monthly_cost_usd']:.4f} USD",
        "",
        "Scenarios (sorted by cost):",
    ]
    for s in report["scenarios"]:
        hint = f"  → {s['optimization_hint']}" if s.get("optimization_hint") else ""
        lines.append(
            f"  {s['name']:<30} ${s['estimated_monthly_cost_usd']:.4f} USD"
            f" | {s['estimated_monthly_queries']}q/mo"
            f" | avg {s['avg_input_tokens']}in+{s['avg_output_tokens']}out tok{hint}"
        )
    lines.append("")
    lines.append(f"Note: {report['accuracy_note']}")
    return "\n".join(lines)


def _render_roi_benchmark_text(report: dict) -> str:
    """Render human-friendly ROI benchmark summary."""
    strategies = report["strategies"]
    deltas = report["deltas"]
    lines = [
        "ROI Benchmark - Routing Comparison",
        f"Batches: {report['scale_batches']} | Requests per strategy: {report['per_batch_requests'] * report['scale_batches']}",
        "",
        "Strategies:",
    ]

    for key in ("no_routing", "free_routing", "paid_routing"):
        item = strategies[key]
        lines.append(
            f"  {item['strategy']:<14} total=${item['total_cost_usd']:.4f} "
            f"(llm=${item['llm_cost_usd']:.4f}, ops=${item['op_cost_usd']:.4f})"
        )

    lines.extend(
        [
            "",
            "Savings:",
            f"  free vs no routing: ${deltas['free_vs_no_routing_usd']:.4f}",
            f"  paid vs free:       ${deltas['paid_vs_free_usd']:.4f}",
            f"  paid vs no routing: ${deltas['paid_vs_no_routing_usd']:.4f}",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rgen",
        description="AgentPilot Orchestrator -- genera sistemi di routing AI per qualsiasi progetto",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--direct", action="store_true", help="Generazione non interattiva")
    mode.add_argument("--dry-run", dest="dry_run", action="store_true", help="Mostra cosa verrebbe generato senza scrivere")
    mode.add_argument("--check", action="store_true", help="Esegui self-check su progetto esistente")
    mode.add_argument("--suggest-scenarios", dest="suggest_scenarios", action="store_true", help="Suggerisci nuovi scenari da interventions.db")
    mode.add_argument("--history", action="store_true", help="Mostra lo storico delle generazioni")
    mode.add_argument("--rollback", action="store_true", help="Rollback selettivo di una generazione")
    mode.add_argument("--search-patterns", help="Cerca pattern nel marketplace locale")
    mode.add_argument("--download", help="Installa un pattern pack (id registry, path locale, URL zip o owner/repo[:tag])")
    mode.add_argument("--restore", action="store_true", help="Ripristina da backup")
    mode.add_argument("--update", action="store_true", help="Aggiorna i core files in un progetto esistente (senza rigenerare)")
    mode.add_argument("--list-patterns", dest="list_patterns", action="store_true", help="Mostra pattern disponibili")
    mode.add_argument("--cost-report", dest="cost_report", action="store_true", help="Stima costo mensile per scenario da intervention history")
    mode.add_argument("--roi-benchmark", dest="roi_benchmark", action="store_true", help="Confronta ROI tra no-routing, routing free e routing paid")

    parser.add_argument("--pattern", help="Pattern ID (es: psm_stack)")
    parser.add_argument("--name", help="Nome del progetto")
    parser.add_argument("--target", help="Directory di output")
    parser.add_argument("--language", help="Lingua agenti: it|en|es|fr (default: auto-detect)", choices=["it", "en", "es", "fr"])
    parser.add_argument("--flat", action="store_true", help="Per --update: copia i core files nella root del target (layout piatto, es. progetti legacy)")
    parser.add_argument("--timestamp", help="Timestamp backup per --restore")
    parser.add_argument("--to", help="Generation ID per --rollback")
    parser.add_argument("--force", action="store_true", help="Per --rollback: forza anche su file modificati manualmente")
    parser.add_argument("--history-format", choices=["text", "json"], default="text", help="Per --history: formato output")
    parser.add_argument("--history-output", help="Per --history: salva output JSON su file")
    parser.add_argument("--show-diffs", action="store_true", help="Per --history: include dettaglio file e stato corrente")
    parser.add_argument("--install-dir", help="Per --download: directory installazione pattern")
    parser.add_argument("--tech", help="Tecnologie (virgola-separate) per --direct senza pattern")
    parser.add_argument("--domains", help="Domini (virgola-separati) per --direct senza pattern")
    parser.add_argument("--min-cluster-size", type=int, default=3, help="Per --suggest-scenarios: dimensione minima cluster (default: 3)")
    parser.add_argument("--similarity-threshold", type=float, default=0.35, help="Per --suggest-scenarios: soglia similarita 0..1 (default: 0.35)")
    parser.add_argument("--min-confidence", type=float, default=0.0, help="Per --suggest-scenarios: confidence minima del cluster 0..1")
    parser.add_argument("--history-limit", type=int, default=200, help="Per --suggest-scenarios o --history: numero massimo di elementi")
    parser.add_argument("--include-matched", action="store_true", help="Per --suggest-scenarios: include anche interventi gia categorizzati")
    parser.add_argument("--suggest-format", choices=["json", "text"], default="json", help="Per --suggest-scenarios: formato output stdout")
    parser.add_argument("--suggest-output", help="Per --suggest-scenarios: salva JSON anche su file")
    parser.add_argument("--kb", help=f"Directory knowledge_base (default: {_DEFAULT_KB})")
    parser.add_argument("--core", help=f"Directory core files (default: {_DEFAULT_CORE})")
    parser.add_argument("--cost-model", dest="cost_model", default="gpt-4o-mini", help="Per --cost-report: modello AI per il pricing (default: gpt-4o-mini)")
    parser.add_argument("--cost-monthly-queries", dest="cost_monthly_queries", type=int, default=1000, help="Per --cost-report: stima query mensili (default: 1000)")
    parser.add_argument("--pricing-db", dest="pricing_db", help="Per --cost-report: path a JSON pricing esterno (sovrascrive defaults)")
    parser.add_argument("--cost-format", dest="cost_format", choices=["json", "text"], default="json", help="Per --cost-report: formato output (default: json)")
    parser.add_argument("--cost-output", dest="cost_output", help="Per --cost-report: salva JSON su file")
    parser.add_argument("--roi-format", dest="roi_format", choices=["json", "text"], default="json", help="Per --roi-benchmark: formato output (default: json)")
    parser.add_argument("--roi-output", dest="roi_output", help="Per --roi-benchmark: salva JSON su file")
    parser.add_argument("--roi-scale", dest="roi_scale", type=int, default=1, help="Per --roi-benchmark: moltiplicatore batch da 10 richieste (default: 1)")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
