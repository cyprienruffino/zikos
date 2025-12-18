# Implementation Notes & Questions

## MIDI Format Considerations

### Decision: LLM generates General MIDI data, tools handle metadata

**Approach**:
- LLM outputs General MIDI data (musical content: notes, timing, velocities)
- Tools handle technical parts (file headers, track structure, metadata)
- Simplified text format for LLM to generate
- Tools parse and convert to standard MIDI for synthesis/rendering

**Format**:
```
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
[/MIDI]
```

**Tool Responsibilities**:
- Parse simplified format
- Add MIDI file headers
- Handle track structure
- Add metadata (tempo, time signature, key)
- Convert to standard MIDI file format
- Validate final MIDI file

## Audio Recording Tool Flow

### Decision: Pause conversation, show recording widget

**UX Flow**:
1. LLM calls `request_audio_recording(prompt="Play C major scale")`
2. Backend receives tool call, sends event to frontend (WebSocket)
3. **Conversation pauses** - LLM waits for audio
4. Frontend shows recording widget in chat with:
   - Prompt text displayed
   - "Record" button
   - "Send" button (disabled until recording complete)
5. User clicks "Record" → records audio
6. User clicks "Send" → uploads audio to backend
7. Backend stores audio, returns `audio_file_id` to LLM context
8. Baseline tools automatically run
9. LLM receives analysis results and continues conversation

**State Management**:
- Backend stores pending recording requests with session ID
- Recording state: `pending` → `recording` → `completed` → `uploaded`
- If user cancels: Send cancellation event, LLM receives notification

**Upload Mechanism** (To be decided):
- Option A: HTTP POST to `/api/audio/upload` with recording_id
- Option B: WebSocket message with audio data
- Option C: FormData upload with multipart/form-data

**Recommendation**: HTTP POST for simplicity in POC, can switch to WebSocket later if needed.

## Baseline Tools Execution

### Question: When/how do baseline tools run automatically?

**Options**:
1. **Backend automatically runs** when audio is uploaded
   - Pros: Always available, no LLM overhead
   - Cons: May run unnecessary analysis

2. **LLM must call them explicitly first**
   - Pros: LLM controls what runs
   - Cons: More tool calls, slower

**Decision**: Backend automatically runs baseline tools when audio is uploaded. Results are injected into LLM context before LLM processes the turn.

## MIDI Validation Strategy

### Decision: Strict validation - reject invalid MIDI, let LLM correct

**Approach**:
- Validate MIDI strictly
- If invalid: Return error message to LLM with details
- LLM receives error, corrects MIDI, tries again
- No auto-fixing - LLM must generate valid MIDI

**Error Format**:
```json
{
  "valid": false,
  "errors": [
    "Invalid note format at line 5: 'C5' should be 'C5 velocity=60 duration=0.5'",
    "Missing tempo marker"
  ],
  "line_number": 5,
  "suggestion": "Use format: NOTE velocity=VELOCITY duration=DURATION"
}
```

**Benefits**:
- LLM learns correct format
- Cleaner MIDI output
- No ambiguous fixes

## Tool Call Format

### Decision: Function calling format (llama-cpp-python supports it)

**Approach**:
- Use function calling format supported by llama-cpp-python
- Define tool schemas (name, description, parameters)
- LLM calls functions naturally
- System handles execution and result injection

**Reference**: https://github.com/abetlen/llama-cpp-python#function-calling

**Implementation**:
- Define tools as function schemas
- Pass schemas to llama-cpp-python
- LLM generates function calls automatically
- Backend executes and returns results

## Context Management

### Question: How to track multiple audio submissions in conversation?

**Approach**:
- Each audio gets unique `audio_file_id`
- LLM receives audio IDs in context
- Tools accept `audio_file_id` parameter
- Conversation history includes audio references

**Implementation**: Store audio files with session ID, track which audio belongs to which conversation turn.

## Error Handling

### Question: What happens when tools fail?

**Strategy**:
- Tools return structured errors
- LLM receives error messages in context
- LLM can reason about errors and adapt
- System prompt instructs LLM on handling errors gracefully

## Performance Considerations

### Baseline Tools
- Run in parallel when possible
- Cache results if audio hasn't changed
- Timeout after reasonable duration (e.g., 10 seconds)

### MIDI Processing
- Validation should be fast (< 100ms)
- Synthesis can be slower (1-2 seconds acceptable)
- Rendering can be async, return URL when ready

## Testing Strategy

### Unit Tests
- Each tool independently
- MIDI validation with various formats
- Error cases

### Integration Tests
- Full flow: recording → analysis → LLM response → MIDI generation
- Multiple audio submissions
- Tool call chaining

### Manual Testing
- Real conversations with LLM
- Various audio types (scales, songs, exercises)
- MIDI generation quality

## Open Implementation Questions

1. **Audio Upload Mechanism**: HTTP POST vs WebSocket for audio upload? (Recommendation: HTTP POST for POC)
2. **Recording Cancellation**: How to handle user canceling recording? Send event to LLM?
3. **MIDI Parser**: Need to implement parser for simplified format → standard MIDI conversion
4. **Audio Storage**: Local filesystem vs object storage for POC? (Decision: Local filesystem for POC)
5. **Tool Schema Definition**: How to define tool schemas for llama-cpp-python function calling?

