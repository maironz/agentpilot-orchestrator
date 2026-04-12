#!/bin/bash
# Master skill dispatcher - AgentPilot Orchestrator automation
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
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $*"
}

log_error() {
    echo -e "${RED}[X]${NC} $*"
}

# ============================================================================
# ANTHROPIC SKILLS BOOTSTRAP
# ============================================================================

setup-anthropic-skills() {
    local skills_slug="${ANTHROPIC_SKILLS_SLUG:-anthropics/skills}"
    local skills_repo="${ANTHROPIC_SKILLS_REPO:-https://github.com/anthropics/skills.git}"
    local skills_ref="${ANTHROPIC_SKILLS_REF:-}"
    local skills_cli_timeout="${ANTHROPIC_SKILLS_CLI_TIMEOUT:-90}"
    local target_dir="$PROJECT_ROOT/.claude/skills"
    local tmp_dir=""
    local source_dir=""
    local force=0
    local git_bin="${GIT_BIN:-git}"
    local npx_bin="${NPX_BIN:-npx}"
    local timeout_bin=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f)
                force=1
                ;;
            *)
                log_error "Unknown option: $1"
                log_error "Usage: setup-anthropic-skills [--force]"
                return 1
                ;;
        esac
        shift
    done

    if [ "$force" -eq 0 ] && [ -d "$target_dir" ] && find "$target_dir" -type f -name "SKILL.md" | grep -q .; then
        log_success "Anthropic skills already configured in $target_dir"
        return 0
    fi

    if [ "$force" -eq 1 ]; then
        log_warn "Force refresh enabled: existing skills directory will be replaced"
        rm -rf "$target_dir"
    fi

    mkdir -p "$PROJECT_ROOT/.claude"

    if command -v timeout > /dev/null 2>&1; then
        timeout_bin="timeout"
    elif command -v gtimeout > /dev/null 2>&1; then
        timeout_bin="gtimeout"
    fi

    # Preferred path: official skills.sh CLI workflow.
    if command -v "$npx_bin" > /dev/null 2>&1; then
        log_info "Trying official installer: $npx_bin skills add $skills_slug"
        if [ -n "$timeout_bin" ]; then
            if (
                cd "$PROJECT_ROOT" && \
                npm_config_yes=true "$timeout_bin" "${skills_cli_timeout}s" "$npx_bin" -y skills add "$skills_slug" < /dev/null > /dev/null 2>&1
            ); then
                if [ -d "$target_dir" ] && find "$target_dir" -type f -name "SKILL.md" | grep -q .; then
                    log_success "Anthropic skills installed via skills.sh into $target_dir"
                    return 0
                fi
                log_warn "skills CLI completed but no SKILL.md found in $target_dir"
            else
                log_warn "skills CLI install failed or timed out, falling back to git clone"
            fi
        elif (
            cd "$PROJECT_ROOT" && \
            npm_config_yes=true "$npx_bin" -y skills add "$skills_slug" < /dev/null > /dev/null 2>&1
        ); then
            if [ -d "$target_dir" ] && find "$target_dir" -type f -name "SKILL.md" | grep -q .; then
                log_success "Anthropic skills installed via skills.sh into $target_dir"
                return 0
            fi
            log_warn "skills CLI completed but no SKILL.md found in $target_dir"
        else
            log_warn "skills CLI install failed, falling back to git clone"
        fi
    else
        log_warn "npx not found, using git fallback"
    fi

    if ! command -v "$git_bin" > /dev/null 2>&1; then
        log_error "Neither skills CLI nor git fallback is available"
        return 1
    fi

    if ! tmp_dir="$(mktemp -d 2>/dev/null)"; then
        log_error "Unable to create temporary directory"
        return 1
    fi

    if [ -n "$skills_ref" ]; then
        log_info "Bootstrapping Anthropic skills from $skills_repo@$skills_ref (fallback)"
    else
        log_info "Bootstrapping Anthropic skills from $skills_repo (fallback)"
    fi

    if [ -n "$skills_ref" ]; then
        if ! "$git_bin" clone --depth 1 --branch "$skills_ref" "$skills_repo" "$tmp_dir" > /dev/null 2>&1; then
            rm -rf "$tmp_dir"
            log_error "Failed to clone Anthropic skills repository at ref $skills_ref"
            return 1
        fi
    elif ! "$git_bin" clone --depth 1 "$skills_repo" "$tmp_dir" > /dev/null 2>&1; then
        rm -rf "$tmp_dir"
        log_error "Failed to clone Anthropic skills repository"
        return 1
    fi

    for candidate in "$tmp_dir/.claude/skills" "$tmp_dir/skills" "$tmp_dir/.github/skills"; do
        if [ -d "$candidate" ]; then
            source_dir="$candidate"
            break
        fi
    done

    if [ -z "$source_dir" ]; then
        rm -rf "$tmp_dir"
        log_error "No skills directory found in $skills_repo"
        log_warn "Set ANTHROPIC_SKILLS_REPO to a repository containing .claude/skills"
        return 1
    fi

    mkdir -p "$target_dir"
    cp -R "$source_dir"/. "$target_dir"/
    rm -rf "$tmp_dir"

    log_success "Anthropic skills bootstrapped into $target_dir"
    return 0
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

    log_success "All checks passed"
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
        backlog) status_map="Backlog" ;;
        in-progress) status_map="In Progress" ;;
        done) status_map="Done" ;;
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
AgentPilot Orchestrator Skills

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
    setup-anthropic-skills         Download and configure Anthropic skills if missing

EXAMPLES:
  gen-branch feature/live-metrics
  router-stats
  run-checks
  setup-anthropic-skills
    setup-anthropic-skills --force
  create-feature-issue "Live Router Metrics Dashboard"

See .github/ROADMAP.md for feature details
See .github/plans/ for implementation plans
EOF
}

# ============================================================================
# MAIN DISPATCHER
# ============================================================================

# If sourced, do not execute the dispatcher.
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    return 0
fi

if [ $# -eq 0 ]; then
    skill-help
    exit 0
fi

# Dispatch to function
"$@"
