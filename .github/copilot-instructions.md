# Copilot Coding Agent - Maestro Project Instructions

<!-- Managed by Maestro workflow contract. Update `workflow_contract.yaml` instead of editing this file directly. -->

This project is managed by the **Maestro** orchestration system and uses **Squad** for multi-agent coordination.

## Before Starting Work

1. `STATUS.md` - current phase, machine-readable `Next Action`, objective, blockers, and next recommended step
2. `FEEDBACK.md` - human corrections or guidance, if present

If these files or directories exist, read them next:

- `backlog/README.md` - project goals and success criteria
- `backlog/data_sources.md` - known data sources and constraints
- `backlog/tasks/` - discrete task definitions
- `.squad/team.md` - roster and role assignments
- `.squad/routing.md` - routing rules
- `.squad/sprint.md` - ordered execution plan
- `.squad/decisions.md` - shared context, evidence, and decisions

## Work Conventions

- **Branch naming:** `maestro/{phase}-{kebab-case-slug}`
- **Commit messages:** Use one of these phase prefixes: `[Planner]`, `[Squad Init]`, `[Squad Review]`, `[Build]`, `[Validate]`, `[Closeout]`
- **Status updates:** Update `STATUS.md` whenever you change the phase, objective, blockers, or next step. Keep a machine-readable `Next Action` field set to `Build`, `Validate`, `Closeout`, `Complete`, or `Human Blocked`. Use `Complete` only when every `.squad/sprint.md` task is complete.
- **Decisions:** Log significant architectural, data, and validation decisions in `.squad/decisions.md`.

## Phases

This repo follows the Maestro lifecycle:
1. **Planner** - Survey the existing repo, define the deliverable, and create the backlog contract.
2. **Squad Init** - Bootstrap `.squad/`, define the team, and align responsibilities to the backlog.
3. **Squad Review** - Tighten backlog tasks, surface risks, and turn the backlog into an execution plan.
4. **Build** - Execute the next explicitly identified implementation or analysis slice from the sprint plan.
5. **Validate** - Run the right checks, capture evidence, and decide whether the loop advances or returns to build.
6. **Closeout** - Refresh handoff artifacts and decide whether the project is complete, human-blocked, or returns to one explicit task.

Legacy aliases still appear in older repos:

- `coder` maps to `build`
- `reviewer` maps to `closeout`
- `review` maps to `closeout`

## Artifact Contract

### Planner

- `backlog/README.md` - project background, goals, and success criteria
- `backlog/data_sources.md` - source URLs/endpoints and availability status
- `backlog/phases.md` - lifecycle breakdown aligned to Maestro phases
- `backlog/tasks/` - one file per discrete task
- `STATUS.md` - current objective updated to reflect the plan
- `requirements.txt` - created or updated if additional Python packages are needed

### Squad Init

- `.squad/team.md` - full roster with role descriptions
- `.squad/routing.md` - routing rules and ownership
- `.squad/decisions.md` - decision log initialized and useful
- `.squad/agents/*/charter.md` - one charter per agent
- `STATUS.md` - updated to show the team is initialized and ready for `squad-review`

### Squad Review

- `backlog/tasks/` - detailed, fully specified task files
- `.squad/sprint.md` - ordered execution plan with ownership and dependencies
- `STATUS.md` - updated to show review is complete and the repo is ready for `build`

### Build

- Implementation work that materially advances exactly one explicit task from `backlog/tasks/` or one dated `FEEDBACK.md` item
- `STATUS.md` - updated with progress, blockers, task/feedback ID, and machine-readable `Next Action`
- `.squad/decisions.md` - updated with significant implementation decisions and the task/feedback ID behind any new artifact

### Validate

- Tests, lint, type checks, metrics, evals, or data integrity checks run when applicable
- `.squad/validation_report.md` - commands/checks run, results, blocked checks, evidence, and pass/fail recommendation
- `STATUS.md` - updated with pass/fail/blocked outcome and next recommended phase
- `.squad/decisions.md` - updated with validation evidence and rationale

### Closeout

- `STATUS.md` - updated with closeout outcome, remaining blockers, and machine-readable `Next Action`
- `.squad/review_report.md` - final review decision, evidence checked, risks, and explicit `Complete` only when every sprint task is complete, `Human Blocked`, or return-to-build decision with task/feedback ID
- `.squad/decisions.md` - final closeout decisions, handoff notes, and task/feedback ID if returning to build
- Human-facing docs refreshed enough for handoff

## Data Constraints

- Prefer using data already in the repo (`data/`, `cache/`, CSV files) when possible.
- If external data is needed, document the source URL in the backlog and any dependency changes in `requirements.txt`.
- Never hardcode API keys - use environment variables.
