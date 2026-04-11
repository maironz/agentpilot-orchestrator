#!/bin/bash
# Master skill dispatcher — AgentPilot Orchestrator automation
# Source this: source .github/skills.sh

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Python executable (prefer venv)
if [ -f "$PROJECT_ROOT/.venv/Scripts/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python"
elif [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[rgen-skill]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

# ============================================================================
# BRANCH MANAGEMENT
# ============================================================================

gen-branch() {
    local branch_name="${1:?"Usage: gen-branch <feature-name>"}"

    log_info "Creating branch: $branch_name"

    # Make sure we're on master
    git checkout master 2>/dev/null || true
    git fetch origin master 2>/dev/null || true

    # Create + checkout
    git checkout -b "$branch_name" || git checkout "$branch_name"
    log_success "Branch ready: $(git branch --show-current)"
}

# ============================================================================
# VALIDATION & CHECKS
# ============================================================================

check-routing-integrity() {
    log_info "Checking routing integrity..."

    local errors=0

    # Check router.py exists
    if [ ! -f "$SCRIPT_DIR/router.py" ]; then
        log_error "router.py not found"
        ((errors++))
    fi

    # Check routing-map.json valid JSON
    if [ -f "$SCRIPT_DIR/routing-map.json" ]; then
        if ! $PYTHON -m json.tool "$SCRIPT_DIR/routing-map.json" > /dev/null 2>&1; then
            log_error "routing-map.json is invalid JSON"
            ((errors++))
        fi
    fi

    # Check AGENT_REGISTRY.md exists
    if [ ! -f "$SCRIPT_DIR/AGENT_REGISTRY.md" ]; then
        log_error "AGENT_REGISTRY.md not found"
        ((errors++))
    fi

    if [ $errors -eq 0 ]; then
        log_success "Routing integrity: OK"
        return 0
    else
        log_error "Found $errors routing issues"
        return 1
    fi
}

run-all-tests() {
    log_info "Running all tests..."

    cd "$PROJECT_ROOT"

    if ! $PYTHON -m pytest tests/ -v --tb=short; then
        log_error "Tests failed"
        return 1
    fi

    log_success "All tests passed"
    return 0
}

run-checks() {
    log_info "Running pre-commit checks..."

    check-routing-integrity || return 1
    run-all-tests || return 1

    log_success "All checks passed ✓"
}

# ============================================================================
# GITHUB ISSUE CREATION
# ============================================================================

create-feature-issue() {
    local feature_name="${1:?"Usage: create-feature-issue <feature>"}"
    local roadmap_ref="${2:-".github/ROADMAP.md"}"

    log_info "Creating GitHub issue for: $feature_name"
    log_warn "Note: requires 'gh' CLI tool and proper auth"

    if ! command -v gh &> /dev/null; then
        log_error "gh CLI not found. Install from https://cli.github.com"
        return 1
    fi

    # Extract feature details from ROADMAP.md
    local feature_line=$(grep "| $feature_name " "$roadmap_ref" || echo "")

    if [ -z "$feature_line" ]; then
        log_error "Feature '$feature_name' not found in $roadmap_ref"
        return 1
    fi

    # Create issue (basic, can be enhanced)
    gh issue create \
        --title "feat: $feature_name" \
        --body "See .github/ROADMAP.md for details" \
        --label "enhancement" 2>/dev/null && \
        log_success "Issue created" || \
        log_warn "Issue creation failed (check gh auth)"
}

# ============================================================================
# ROADMAP STATUS UPDATES
# ============================================================================

update-roadmap-status() {
    local feature="${1:?"Usage: update-roadmap-status <feature> <status>"}"
    local status="${2:?"Usage: update-roadmap-status <feature> [in-progress|done|backlog]"}"

    log_info "Updating ROADMAP status: $feature -> $status"

    # Simple sed replacement (crude but functional)
    local status_map
    case "$status" in
        backlog) status_map="❌ Backlog" ;;
        in-progress) status_map="🔄 In Progress" ;;
        done) status_map="✅ Done" ;;
        *) log_error "Unknown status: $status"; return 1 ;;
    esac

    # macOS sed requires -i '', bash on Linux doesn't
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|$feature.*status_map.*|$feature ... | $status_map|" "$SCRIPT_DIR/ROADMAP.md"
    else
        sed -i "s|$feature.*|$feature ... | $status_map|" "$SCRIPT_DIR/ROADMAP.md"
    fi

    log_success "ROADMAP updated"
}

# ============================================================================
# ROUTER MANAGEMENT
# ============================================================================

router-stats() {
    log_info "Router stats:"
    cd "$SCRIPT_DIR"
    $PYTHON router.py --stats 2>/dev/null || log_error "router.py --stats failed"
}

router-dry-run() {
    local query="${1:?"Usage: router-dry-run <query>"}"

    log_info "Router dry-run: $query"
    cd "$SCRIPT_DIR"
    $PYTHON router.py --direct "$query" 2>/dev/null || log_error "router.py failed"
}

# ============================================================================
# BACKUP & RESTORE
# ============================================================================

backup-github() {
    log_info "Creating .github/ backup..."

    local backup_dir="$SCRIPT_DIR/.rgen-backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup key files
    for file in router.py routing-map.json AGENT_REGISTRY.md copilot-instructions.md; do
        if [ -f "$SCRIPT_DIR/$file" ]; then
            cp "$SCRIPT_DIR/$file" "$backup_dir/"
        fi
    done

    cp -r "$SCRIPT_DIR/esperti/" "$backup_dir/esperti/" 2>/dev/null || true

    log_success "Backup created: $backup_dir"
}

# ============================================================================
# HELP & DISCOVERY
# ============================================================================

skill-help() {
    cat <<EOF
🛠️  AgentPilot Orchestrator Skills

BRANCH MANAGEMENT:
  gen-branch <name>              Create + checkout feature branch

VALIDATION:
  check-routing-integrity        Verify .github/ structure
  run-all-tests                  Run pytest suite
  run-checks                     Run pre-commit checks

ROUTER:
  router-stats                   Print router statistics
  router-dry-run <query>         Test router on single query

GITHUB:
  create-feature-issue <name>    Create GitHub issue from ROADMAP entry
  update-roadmap-status <n> <s>  Update feature status (backlog|in-progress|done)

BACKUP:
  backup-github                  Backup .github/ contents

HELP:
  skill-help                     Show this message

EXAMPLES:
  gen-branch feature/live-metrics
  router-stats
  run-checks
  create-feature-issue "Live Router Metrics Dashboard"

📚 See .github/ROADMAP.md for feature details
📋 See .github/plans/ for implementation plans
EOF
}

# ============================================================================
# MAIN DISPATCHER
# ============================================================================

if [ $# -eq 0 ]; then
    skill-help
    exit 0
fi

# Dispatch to function
"$@"
