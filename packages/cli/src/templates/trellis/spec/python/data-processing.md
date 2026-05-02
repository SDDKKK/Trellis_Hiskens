# Python Data Processing

## Core Rule

Use `polars` before `pandas` for tabular processing.

## Expected Patterns

- Use `pl.DataFrame` and `pl.LazyFrame` for transformation pipelines.
- Keep schema assumptions explicit near file load boundaries.
- Prefer vectorized expressions over Python loops when operating on columns.
- Keep I/O and transformation logic separated when the pipeline is non-trivial.

## Avoid

- introducing `pandas` just for convenience
- mixing path discovery, file I/O, and business logic in one large function
- mutating data in place across many steps when an expression pipeline is clearer
