# Token Overflow Diagnostics

## Error Observed

```
ERROR: streaming_error: Error during streaming: Requested tokens (11280) exceed context window of 2048
```

**Problem**: Backend is attempting to process 11,280 tokens when context window is only 2,048 tokens (5.5x overflow).

## Root Cause Analysis

### 1. Context Window Size Detection

**Where it's stored:**
- `settings.llm_n_ctx` - from config (can be None)
- If None, auto-detected during initialization via `detect_context_length()`
- Stored in `self.backend.n_ctx` after initialization

**Current flow:**
```python
# backend/zikos/services/llm.py:131-151
n_ctx = settings.llm_n_ctx
if n_ctx is None:
    n_ctx = detect_context_length(model_path_str, backend_type)
    # ... stores in backend.initialize(n_ctx=n_ctx)
```

**Issue**: The detected context window size is stored in the backend but **not used** by message preparation or validation.

### 2. Message Preparation

**Current implementation:**
```python
# backend/zikos/services/llm.py:342-344
current_messages = self._prepare_messages(
    history, max_tokens=LLM.MAX_TOKENS_PREPARE_MESSAGES, for_user=False
)
```

**Problem**: Uses hardcoded `LLM.MAX_TOKENS_PREPARE_MESSAGES = 120,000` instead of actual context window.

**What happens:**
- `MessagePreparer.prepare()` receives `max_tokens=120,000`
- Calculates `available_tokens = max(120000 - 5000, 120000 // 2) = 60,000`
- Truncates history to fit 60,000 tokens
- But actual context window is only 2,048!

**Result**: Messages prepared for 60K tokens are sent to a 2K context window model.

### 3. Token Validation

**Current implementation:**
```python
# backend/zikos/services/llm.py:346
token_error = self.response_validator.validate_token_limit(current_messages)
```

**What it checks:**
```python
# backend/zikos/services/llm_orchestration/response_validator.py:28
if total_tokens > LLM.MAX_TOKENS_SAFETY_CHECK:  # 125,000
    return error
```

**Problem**: Validates against 125,000 tokens instead of actual context window (2,048).

**Result**: Validation passes even though messages exceed the actual context window by 5.5x.

### 4. Backend Error Handling

**Current flow:**
```python
# backend/zikos/services/llm.py:357-363
try:
    stream = self.backend.stream_chat_completion(
        messages=current_messages,  # 11,280 tokens
        tools=tools_param,
        ...
    )
except Exception as e:
    self._inject_error_system_message(
        history, "streaming_error", f"Error during streaming: {str(e)}"
    )
    continue  # Retries with same oversized messages
```

**Problem**:
- Backend rejects the request (correctly)
- Error is caught and injected as system message
- Loop continues with **same oversized messages**
- Will fail again on next iteration

**Result**: Infinite retry loop with same oversized context.

## Token Count Breakdown

For a 2K context window model, here's what's happening:

1. **System prompt**: ~673 tokens (original) or ~374 tokens (minimal)
2. **Tool schemas**: Variable, can be large (all tool descriptions)
3. **Conversation history**: Growing with each turn
4. **Audio analysis results**: Can be large JSON structures
5. **Reserved tokens**: 5,000 for audio analysis (way too much for 2K window)

**Example calculation for 2K window:**
- System prompt: 374 tokens (minimal)
- Tool schemas: ~500-1000 tokens (estimated)
- Reserved: 5,000 tokens (impossible!)
- Available for conversation: **NEGATIVE** (already exceeded)

## Issues Identified

### Issue 1: Hardcoded Token Limits
- `MAX_TOKENS_PREPARE_MESSAGES = 120,000` (assumes large context)
- `MAX_TOKENS_SAFETY_CHECK = 125,000` (assumes large context)
- `TOKENS_RESERVE_AUDIO_ANALYSIS = 5,000` (too large for small windows)

**Impact**: Message preparation and validation don't respect actual model limits.

### Issue 2: Context Window Not Passed Through
- Context window is detected and stored in backend
- But `MessagePreparer` and `ResponseValidator` don't have access to it
- They use hardcoded constants instead

**Impact**: No awareness of actual model capabilities.

### Issue 3: No Dynamic Truncation
- When backend rejects request, same messages are retried
- No aggressive truncation on retry
- No progressive reduction strategy

**Impact**: Retry loops fail repeatedly with same oversized context.

### Issue 4: Reserve Tokens Too Large
- `TOKENS_RESERVE_AUDIO_ANALYSIS = 5,000` is 2.4x the entire 2K context window
- `available_tokens = max(max_tokens - 5000, max_tokens // 2)` becomes negative

**Impact**: Calculation breaks for small context windows.

### Issue 5: Tool Schemas Not Counted
- Tool schemas are injected but their token count isn't considered
- Can be very large (all tool descriptions in JSON format)
- Added on top of already-prepared messages

**Impact**: Final message size can exceed context even if preparation seemed OK.

## Data Flow

```
1. LLMService.generate_response_stream()
   └─> history = conversation_manager.get_history()
   └─> tool_injector.inject_if_needed()  # Adds tool schemas to history
   └─> _prepare_messages(history, max_tokens=120000)  # Uses hardcoded limit
       └─> MessagePreparer.prepare()
           └─> available_tokens = max(120000 - 5000, 120000 // 2) = 60,000
           └─> Truncates to fit 60K tokens
           └─> Returns messages (may still be 11K+ tokens)
   └─> validate_token_limit(messages)  # Checks against 125K
       └─> Passes (11K < 125K)
   └─> backend.stream_chat_completion(messages)  # Backend has 2K limit
       └─> ERROR: 11,280 > 2,048
   └─> Catch exception, inject error message, retry with same messages
```

## Solution: Proportional Reserve Calculation

**Created**: `backend/zikos/utils/token_budget.py` with utility functions:

1. **`calculate_reserve_tokens(context_window)`**: Returns 10% of context window (min 200 tokens)
2. **`calculate_available_tokens(context_window, system_prompt_tokens, tool_schemas_tokens)`**: Calculates available tokens for conversation
3. **`get_max_tokens_for_preparation(context_window)`**: Returns 95% of context window for message prep
4. **`get_max_tokens_for_validation(context_window)`**: Returns context window minus reserve for validation

**Results for different context windows:**
- 2K window: 204 tokens reserve (10%), 970 tokens available (47% of window)
- 4K window: 409 tokens reserve (10%), 2,813 tokens available (69% of window)
- 32K window: 3,276 tokens reserve (10%), 28,618 tokens available (87% of window)

**Comparison**: Old system tried to use 60,000 tokens for a 2K window. New system uses 1,945 tokens (95% of 2K).

## What Needs to Change

### 1. Pass Context Window to Components
- `MessagePreparer` needs actual context window size
- `ResponseValidator` needs actual context window size
- Both should receive it from `LLMService` (which can access via `self.backend.get_context_window()`)

### 2. Use Context Window for Limits
- Replace hardcoded `MAX_TOKENS_PREPARE_MESSAGES` with `get_max_tokens_for_preparation(context_window)`
- Replace hardcoded `MAX_TOKENS_SAFETY_CHECK` with `get_max_tokens_for_validation(context_window)`
- Use `calculate_reserve_tokens(context_window)` instead of fixed 5,000 + 4,000 reserves

### 3. Count Tool Schemas
- Calculate token count of tool schemas before injection
- Include in available token calculation
- Or inject tools separately and count them

### 4. Aggressive Truncation on Retry
- When backend rejects for context overflow, aggressively truncate
- Remove older messages first
- Reduce system prompt size if possible
- Retry with smaller context

### 5. Proportional Reserves
- For 2K window: reserve ~200 tokens (10%)
- For 32K window: reserve ~3,200 tokens (10%)
- Don't use fixed 5,000 token reserve

## Mathematical Proof of the Problem

For a 2K context window model:

```
Context window: 2,048 tokens
System prompt (minimal): 374 tokens
Reserve for audio: 5,000 tokens
Reserve for response: 4,000 tokens

Available = 2,048 - 374 - 5,000 - 4,000 = -7,326 tokens
```

**The reserve tokens alone (9,000) exceed the entire context window (2,048) by 4.4x!**

**Current code calculation:**
```python
max_tokens = 120,000  # Hardcoded!
available = max(120000 - 5000, 120000 // 2) = 60,000 tokens
```

**Result**: Code tries to fit 60,000 tokens into a 2,048 token window.

**What it should be (using new utility functions):**
```python
from zikos.utils.token_budget import (
    get_max_tokens_for_preparation,
    calculate_available_tokens,
)

context_window = 2,048  # From backend.get_context_window()
max_tokens = get_max_tokens_for_preparation(context_window)  # 1,945 tokens (95%)
available = calculate_available_tokens(context_window, 374, 500)  # 970 tokens
```

**Implementation**: See `backend/zikos/utils/token_budget.py` for the utility functions.

## Questions to Answer

1. **Should we store context window in LLMService?**
   - Currently only in backend
   - Need to pass to preparer/validator

2. **How to handle tool schema injection?**
   - Count tokens before injection?
   - Inject conditionally based on available space?
   - Use condensed tool descriptions for small windows?

3. **What's the truncation strategy?**
   - Remove oldest messages first?
   - Summarize old messages?
   - Remove thinking messages?
   - Reduce system prompt size?

4. **How many retries with truncation?**
   - Current: 10 iterations (MAX_ITERATIONS)
   - Should we have separate retry limit for context overflow?

5. **Should we detect context overflow before backend call?**
   - Count tokens of final messages (including tool schemas)
   - Truncate proactively instead of reactively

6. **Proportional reserves?**
   - Current: Fixed 5,000 + 4,000 = 9,000 tokens
   - Should be: 10% of context window (204 for 2K, 3,200 for 32K)
   - Or: Minimum threshold (e.g., 200 tokens) for very small windows
