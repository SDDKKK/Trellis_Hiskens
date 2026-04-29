# Trellis Check — Hiskens Review Extensions

This guide preserves Hiskens review knowledge for v0.5 without installing a standalone `review` subagent. Use it as an optional checklist for `trellis-check` or human review.

## D0 — Spec Compliance

- Confirm the change matches the active PRD/task acceptance criteria.
- Confirm touched files follow the applicable `.trellis/spec/` package/layer guidance.
- Confirm behavior changes are reflected in specs when they introduce new conventions.

## Scientific Correctness

- Validate units, coordinate systems, sampling rates, dimensions, and boundary assumptions.
- Prefer explicit invariants over implicit domain assumptions.
- Check numerical stability and edge cases for empty, NaN, infinite, or degenerate inputs.

## Python / MATLAB Boundary Consistency

- Verify 0-based Python indexing versus 1-based MATLAB indexing at every boundary.
- Confirm array orientation and shape conventions are documented and tested.
- Check file format, dtype, and column-name compatibility across both sides.

## Data Integrity

- Avoid silent row loss, implicit casts, timezone drift, duplicate IDs, and unvalidated joins.
- Preserve provenance for generated artifacts and intermediate scientific data.
- Validate schema expectations before expensive downstream processing.

## Performance

- Prefer vectorized Polars operations and lazy execution for large tabular workloads.
- Avoid materializing large intermediate data unless required.
- Make algorithmic complexity explicit when data size can grow.

## Code Clarity

- Keep scientific transformations named after the domain concept, not the implementation trick.
- Keep IO, validation, transformation, and reporting responsibilities separated.
- Use concise comments for domain assumptions that are not obvious from code.
