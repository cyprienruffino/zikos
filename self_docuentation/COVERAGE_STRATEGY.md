# Coverage Strategy

## Current Status
- **Current Coverage**: 71%
- **Required Coverage**: 75%
- **Gap**: 4 percentage points

## Files Excluded from Coverage

These files are excluded because they require expensive resources or are hard to test in CI:
1. **LLM Service** (`services/llm.py`) - Requires real LLM models and good hardware
2. **LLM Backends** (`llm_backends/*`) - Require real models, good hardware, and are integration-tested
3. **GPU Utils** (`utils/gpu.py`) - Environment-specific, hard to test in CI

**Note**: Audio analysis modules (articulation, chords, dynamics, groove, key, timbre, time_stretch) are included in coverage as they can be tested with real librosa on synthetic audio without requiring expensive resources.

## Test Organization

### Unit Tests (Fast, No External Dependencies)
- Test error handling and edge cases
- Mock external dependencies
- Focus on testable code paths
- Run in CI pre-commit hooks

### Comprehensive Tests (Require Real Dependencies)
- Test with real models, audio processing, etc.
- Located in `tests/comprehensive/`
- Marked with `@pytest.mark.comprehensive`
- Run separately in CI
- Files: `test_llm_backend_streaming.py`, `test_time_stretch.py`

### Integration Tests (Full System)
- Test end-to-end workflows
- Located in `tests/integration/`
- Run separately in CI

## Files Needing More Tests

### High Priority (Low Coverage, Testable)
1. **`mcp/tools/processing/midi/midi.py`** - 48% coverage
   - ✅ Added: Synthesis error cases, SoundFont handling
   - ✅ Added: Notation rendering error cases
   - Remaining: More edge cases for pyfluidsynth fallback

2. **`mcp/tools/analysis/audio/phrase_segmentation.py`** - 79% coverage
   - ✅ Added: Processing failure cases
   - ✅ Added: Energy level detection
   - Remaining: Edge cases for phrase boundary detection

3. **Widget files** - 79% coverage each
   - ✅ Added: Error cases for unknown tools
   - Remaining: Edge cases for parameter validation

## Strategy
1. **Exclude untestable code**: Files that require external tools or real models should be excluded
2. **Add unit tests for testable code**: Focus on error cases and edge cases that can be tested without external dependencies
3. **Comprehensive tests cover the rest**: Comprehensive tests verify full functionality with real dependencies
4. **Integration tests for end-to-end**: Integration tests verify full system workflows

## Future: Integration Tests

Integration tests could be added to cover:
- Full MIDI synthesis workflows with real fluidsynth
- Complete audio analysis pipelines
- End-to-end LLM tool calling workflows
- Real-time audio processing scenarios

These would run separately from unit tests and provide additional confidence in system behavior.
