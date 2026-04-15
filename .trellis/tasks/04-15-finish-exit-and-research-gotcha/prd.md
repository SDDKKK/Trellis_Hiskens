# Fix task finish exit code confusion and document research gotcha

## Goal

Eliminate the misleading "task.py finish returned exit code 2" diagnosis by
capturing the actual root cause and adding a regression anchor for task
lifecycle behavior, while also documenting that the research agent
intentionally does not load task jsonl context.

## Requirements

- Confirm the real source of the observed non-zero exit code during smoke
  testing.
- Preserve the existing `task.py finish` lifecycle behavior:
  - clear `.current-task`
  - reset scratchpad for the hiskens overlay flow
- Add a regression test that exercises the task lifecycle script behavior in a
  temporary repo.
- Add a regression test that locks the research-agent context contract:
  research gets project structure plus optional `research.jsonl`, not
  implement/check/debug/review task jsonl.
- Record the research-agent gotcha in project documentation.
- Record the gotcha in memory for future sessions.

## Acceptance Criteria

- [ ] Root cause of the observed exit code `2` is documented with concrete
      evidence.
- [ ] Regression coverage exists for task lifecycle script behavior.
- [ ] Regression coverage exists for research-agent lightweight context
      behavior.
- [ ] Spec/workflow documentation explicitly warns that research-agent hook
      validation must not use implement/check/debug/review expectations.
- [ ] Memory is updated with the research-agent gotcha.
- [ ] Relevant validation passes.

## Technical Notes

- Initial inspection shows `cmd_finish()` itself returns `0`; the suspicious
  symptom is likely outside the command body.
- Offline reproduction should use a temporary repo so the diagnosis does not
  depend on the external Anhui workspace.
- Keep changes scoped; do not refactor unrelated task lifecycle code.

## Out of Scope

- Broad redesign of task lifecycle commands.
- Changing the overall research-agent prompt philosophy.
- Global overhaul of every `uv run python` example in the repo.
