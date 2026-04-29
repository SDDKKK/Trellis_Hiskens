# Cross-Layer Check

Check if your changes considered all dimensions. Most bugs come from "didn't think of it", not lack of technical skill.

> **Note**: This is a **post-implementation** safety net. Ideally, read the [Pre-Implementation Checklist](.trellis/spec/guides/pre-implementation-checklist.md) **before** writing code.

---

## Related Documents

| Document | Purpose | Timing |
|----------|---------|--------|
| [Pre-Implementation Checklist](.trellis/spec/guides/pre-implementation-checklist.md) | Questions before coding | **Before** writing code |
| [Code Reuse Thinking Guide](.trellis/spec/guides/code-reuse-thinking-guide.md) | Pattern recognition | During implementation |
| **`/trellis:check-cross-layer`** (this) | Verification check | **After** implementation |

---

## Execution Steps

### 1. Identify Change Scope

```bash
git status
git diff --name-only
```

### 2. Select Applicable Check Dimensions

Based on your change type, execute relevant checks below:

---

## Dimension A: Python↔MATLAB Data Flow (Required when both languages involved)

**Trigger**: Changes involve both Python (.py) and MATLAB (.m) code

| Layer | Common Locations |
|-------|------------------|
| Python data processing | `src/`, `scripts/` (.py files) |
| MATLAB scientific computing | `MATLAB/` (.m files) |
| Data files / interchange | `data/`, `output/` (.mat, .csv, .json, .h5) |
| Configuration | `config/` |

**Checklist**:
- [ ] Read flow: Data files → Python processing → MATLAB computation (or vice versa)
- [ ] Write flow: MATLAB output → Python post-processing → Results
- [ ] Data formats compatible between Python and MATLAB? (.mat, .csv, .json, .h5)
- [ ] Variable naming consistent across languages?
- [ ] Array dimensions/indexing conventions handled? (Python 0-based vs MATLAB 1-based)
- [ ] Errors properly logged on both sides?

**Detailed Guide**: `.trellis/spec/guides/cross-layer-thinking-guide.md`

---

## Dimension B: Code Reuse (Required when modifying constants/config)

**Trigger**: 
- Modifying shared constants or configuration values
- Modifying any hardcoded value
- Seeing similar code in multiple places
- Creating a new utility/helper function
- Just finished batch modifications across files

**Checklist**:
- [ ] Search first: How many places define this value?
  ```bash
  # Search in source files
  grep -r "value-to-change" src/ MATLAB/
  ```
- [ ] If 2+ places define same value -> Should extract to shared config
- [ ] After modification, all usage sites updated?
- [ ] If creating utility: Does similar utility already exist?

**Detailed Guide**: `.trellis/spec/guides/code-reuse-thinking-guide.md`

---

## Dimension B2: New Utility Functions

**Trigger**: About to create a new utility/helper function

**Checklist**:
- [ ] Search for existing similar utilities first
  ```bash
  grep -r "functionNamePattern" src/ MATLAB/
  ```
- [ ] If similar exists, can you extend it instead?
- [ ] If creating new, is it in the right location (shared vs domain-specific)?

---

## Dimension B3: After Batch Modifications

**Trigger**: Just modified similar patterns in multiple files

**Checklist**:
- [ ] Did you check ALL files with similar patterns?
  ```bash
  grep -r "patternYouChanged" src/ MATLAB/
  ```
- [ ] Any files missed that should also be updated?
- [ ] Should this pattern be abstracted to prevent future duplication?

---

## Dimension C: Import/Dependency Paths (Required when creating new files)

**Trigger**: Creating new source files

**Checklist**:
- [ ] Python: Using correct import paths (relative vs absolute)?
- [ ] Python: No circular dependencies?
- [ ] MATLAB: Functions on MATLAB path? (`addpath` if needed)
- [ ] Consistent with project's module organization?

---

## Dimension D: Same-Layer Consistency

**Trigger**: 
- Modifying display logic or formatting
- Same domain concept used in multiple places

**Checklist**:
- [ ] Search for other places using same concept
  ```bash
  grep -r "ConceptName" src/ MATLAB/
  ```
- [ ] Are these usages consistent?
- [ ] Should they share configuration/constants?

---

## Common Issues Quick Reference

| Issue | Root Cause | Prevention |
|-------|------------|------------|
| Changed one place, missed others | Didn't search impact scope | `grep` before changing |
| Data lost between Python↔MATLAB | Format mismatch or index offset | Verify data interchange format |
| Variable naming mismatch | Inconsistent across languages | Use shared naming convention |
| Similar utility exists | Didn't search first | Search before creating |
| Batch fix incomplete | Didn't verify all occurrences | grep after fixing |
| Array index off-by-one | Python 0-based vs MATLAB 1-based | Document index conventions |

---

## Output

Report:
1. Which dimensions your changes involve
2. Check results for each dimension
3. Issues found and fix suggestions
