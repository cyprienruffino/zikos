# System Prompt Condensation Analysis

## Current State
- **Tokens**: 673
- **Characters**: 3,027
- **For 2K context window**: ~33% of context
- **For 4K context window**: ~17% of context

## Major Redundancies Identified

### 1. "Interpret, Don't Report" Rule (Repeated 4+ times)
- **Lines 10-33**: CRITICAL section with examples
- **Lines 110-172**: Feedback Structure section - REPEATS the same rule with more examples
- **Lines 174-192**: Teaching Approach - repeats again
- **Lines 178, 182**: More repetition

**Condensation opportunity**: Consolidate into ONE clear section with minimal examples. Save ~150-200 tokens.

### 2. Thinking and Reasoning Section (Lines 35-66)
- Very verbose with multiple bullet points
- Example format takes up space
- Could be condensed to: "Always use <thinking> tags. Think before/after tool calls and when analyzing."

**Condensation opportunity**: Reduce from ~200 tokens to ~50 tokens. Save ~150 tokens.

### 3. Example Interactions (Lines 261-296)
- Three detailed examples with step-by-step workflows
- Helpful but not essential for core behavior
- Could be made optional or condensed to one brief example

**Condensation opportunity**: Remove or condense to one example. Save ~100 tokens.

### 4. Interpreting Analysis Results (Lines 89-172)
- Contains the "BAD example" which is very long (lines 153-168)
- Repeats the same message multiple times
- Could be condensed significantly

**Condensation opportunity**: Remove verbose examples, consolidate. Save ~100-150 tokens.

### 5. Practice Widgets Section (Lines 222-242)
- Lists all widget types with descriptions
- Example at end (line 242) could be removed
- Could be condensed to: "Create widgets proactively when they help address analysis issues."

**Condensation opportunity**: Save ~50 tokens.

### 6. Your Capabilities Section (Lines 68-87)
- MIDI workflow is detailed (5 steps)
- Could be more concise

**Condensation opportunity**: Save ~30 tokens.

## Proposed Condensed Version Structure

### Essential Sections (Must Keep)
1. **Core Identity** (2-3 lines)
2. **Critical Rule: Interpret Don't Report** (condensed, ~10 lines)
3. **Thinking Tags** (condensed, ~5 lines)
4. **Capabilities Overview** (condensed, ~10 lines)
5. **Tool Usage** (condensed, ~10 lines)
6. **Teaching Approach** (condensed, ~8 lines)
7. **Limitations** (keep as-is, ~8 lines)

### Optional Sections (Can Remove for Small Context)
- Detailed examples
- Verbose explanations
- Step-by-step workflows
- Multiple examples of same concept

## Target Token Counts

- **Ultra-condensed** (for <2K context): ~200-250 tokens
- **Condensed** (for 2K-4K context): ~350-400 tokens
- **Full** (for >4K context): 673 tokens (current)

## Condensation Strategy

1. **Remove all redundant explanations** of the same rule
2. **Consolidate examples** - one good example instead of multiple
3. **Remove verbose "BAD" examples** - just state what not to do
4. **Shorten thinking section** - keep requirement, remove verbose explanations
5. **Condense widget section** - remove detailed list, keep principle
6. **Merge overlapping sections** - Teaching Approach overlaps with Feedback Structure

## Implementation Approach

Create three prompt variants:
1. **minimal**: Core rules only (~200 tokens)
2. **condensed**: Essential content without examples (~400 tokens)
3. **full**: Current prompt (673 tokens)

Select based on `llm_n_ctx`:
- < 2K: minimal
- 2K-4K: condensed
- > 4K: full
