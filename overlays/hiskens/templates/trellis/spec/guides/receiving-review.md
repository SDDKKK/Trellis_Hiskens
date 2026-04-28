# Receiving Review Feedback

> Adapted from [Superpowers](https://github.com/obra/superpowers) for Trellis agent interactions.

## Response Protocol

WHEN receiving feedback from check/review agent:

1. **READ** -- Read the complete feedback, do not react immediately
2. **UNDERSTAND** -- Restate the problem in your own words (or ask for clarification)
3. **VERIFY** -- Check the code to confirm the issue actually exists
4. **EVALUATE** -- Will the fix break existing functionality?
5. **IMPLEMENT** -- Fix one item at a time, verify after each fix

## Prohibited Behaviors

- "You're absolutely right!" -- performative agreement without verification
- Fixing without understanding -- blindly applying suggestions
- Batch fixing without testing -- changing multiple things then hoping it works
- Jumping to implementation -- skipping the verify step

## Correct Behaviors

- "Fixed. Changed `calculate_rate()` return type from float to Decimal at line 42."
- "Checked: this issue doesn't apply because the input is already validated at line 30."
- "Need clarification on item 3 before proceeding -- does this apply to the batch path too?"
- "Disagree: removing this check would break the empty-input edge case. Keeping it."

## YAGNI Check

IF a reviewer suggests adding a feature or abstraction:

1. Search the codebase for actual usage of the proposed pattern
2. IF unused anywhere: push back with reasoning ("No current consumers; adding when needed")
3. IF used elsewhere: implement following the existing pattern

## Verification After Each Fix

After implementing each piece of feedback:

1. Run the relevant verification command (ruff, pytest, getDiagnostics)
2. Confirm the fix resolves the reported issue
3. Confirm no new issues were introduced
4. Only then move to the next feedback item

## When to Push Back

You SHOULD push back when:

- The suggestion would change scientific computation results
- The suggestion removes error handling for a real edge case
- The suggestion adds complexity without clear benefit
- The suggestion contradicts an architecture decision in `decisions.md`
- The suggestion is based on a misunderstanding of the code's purpose

Push back format: "Disagree with [item]: [specific reason]. [What would break or degrade]."

## Core Principle

> Understand first, verify second, implement third. Never skip steps.
