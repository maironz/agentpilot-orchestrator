# CLI Noob Guide (Step by Step)

This guide is for people starting from zero.

Goal: generate a project with AgentPilot without confusion about paths, options, and the `python -m` command.

## 0) First rule (very important)

`python -m rgen.cli` is not an option of the tool.

- `-m` is a Python option.
- It means: run the `rgen.cli` module.
- It is useful in development to avoid PATH issues with the `rgen` executable.

## 1) Basic setup

Windows (PowerShell):

```powershell
git clone https://github.com/maironz/agentpilot-orchestrator.git
cd agentpilot-orchestrator

python -m venv .venv
.venv\Scripts\activate

pip install -e .
pip install -r requirements-dev.txt
```

Quick check:

```powershell
python -m rgen.cli --help
```

## 2) Recommended noob procedure (without --target .)

Typical scenario: you want to create a new project as a sibling of your current folder.

1. Go to the parent folder of the repo (one level up):

```powershell
cd ..
```

2. Run generation with an explicit folder name:

```powershell
python -m rgen.cli --direct --pattern python_api --name my-project --target my-project
```

Why this is the simplest path:

- you do not use `--target .`
- the final path is immediately clear
- you reduce path mistakes when cloning into subfolders

## 3) If you want to use the current folder

If you want to generate in the directory where you already are:

```powershell
python -m rgen.cli --direct --pattern python_api --name my-project --target .
```

Use this mode only when you are sure about the current directory.

## 4) Minimum commands to know

### Generation

```powershell
python -m rgen.cli --direct --pattern python_api --name my-project --target my-project
```

Effect: creates orchestration files in the target path you provided.

### Simulation without writing files

```powershell
python -m rgen.cli --dry-run --pattern python_api --name my-project --target my-project
```

Effect: shows what would be written, without changing the filesystem.

### Self-check for an existing project

```powershell
python -m rgen.cli --check --target my-project
```

Effect: verifies expected structure and files.

### Core files update

```powershell
python -m rgen.cli --update --target my-project
```

Effect: updates core files with automatic backup.

## 5) Common errors and quick fixes

### I generated in the wrong location

You almost always used the wrong current path.

Fix:

1. `pwd` (or `Get-Location`) to see where you are
2. run the command again with an explicit `--target`

### I do not understand whether to use `rgen` or `python -m rgen.cli`

Practical rule:

- local development: `python -m rgen.cli`
- stable user/CI installation: `rgen` is also fine

## 6) Next step (when you feel ready)

For a complete options/effects reference, use the extended CLI guide (to be added in the docs plan).
