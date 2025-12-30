# Mock Usage Analysis

This document analyzes all tests that use mocks and identifies cases where mocking might be over-zealous.

## Summary

- **Total test files with mocks**: 24
- **Total patch/mock calls**: ~176 (reduced from original analysis)
- **Files with most mocks**: `test_audio_tools.py` (reduced significantly), `test_llm_service.py` (reduced), `test_audio_preprocessing.py` (reduced), `test_audio_service.py` (reduced)

## ✅ Completed Refactorings

The following high-priority refactorings have been completed:

1. **test_llm_service.py** - Replaced Path/file mocking with real file operations using `tmp_path` and `__file__` patching
2. **test_audio_service.py** - Replaced analysis tool mocks with real implementations using synthesized audio
3. **test_audio_preprocessing.py** - Replaced subprocess.run mocks with real ffmpeg calls (ffmpeg is now a required dependency)
4. **test_audio_tools.py** - Significantly reduced mocking by replacing most librosa mocks with real implementations using synthesized audio

## Test Files Using Mocks

### Unit Tests

1. **test_api_chat_streaming.py** (5 patches)
2. **test_chat_service.py** (2 patches)
3. **test_llm_backend_streaming.py** (2 patches)
4. **test_chat_streaming.py** (2 patches)
5. **test_context_optimization.py** (2 patches)
6. **test_llm_streaming.py** (4 patches)
7. **test_audio_preprocessing.py** (7 patches)
8. **test_audio_service.py** (7 patches)
9. **test_llm_service.py** (16 patches)
10. **test_api_chat.py** (1 patch)
11. **test_audio_tools.py** (80 patches) ⚠️ **HIGHEST**
12. **test_groove.py** (4 patches)
13. **test_comprehensive.py** (4 patches)
14. **test_mcp_server.py** (10 patches)
15. **test_mcp_tools.py** (2 patches)
16. **test_phrase_segmentation.py** (5 patches)
17. **test_repetition.py** (4 patches)
18. **test_segmentation.py** (8 patches)
19. **test_time_stretch.py** (6 patches)
20. **test_midi_service.py** (1 patch)
21. **test_midi_tools.py** (1 patch)
22. **test_main.py** (1 patch)
23. **test_api_audio.py** (1 patch)
24. **test_api_midi.py** (1 patch)

## Over-Zealous Mocking Cases

### ✅ Completed Refactorings

#### 1. **test_llm_service.py** - Path and File Operations ✅
**Status**: COMPLETED

**Changes**: Replaced Path/file mocking with real file operations. Tests now create actual directory structures and patch `__file__` to point to temp directories, allowing real path resolution and file reading to be tested.

**Result**: Tests now verify actual path resolution logic and file reading behavior.

---

#### 2. **test_audio_service.py** - Analysis Tools Mocking ✅
**Status**: COMPLETED

**Changes**: Replaced mocked `analyze_tempo`, `detect_pitch`, `analyze_rhythm`, and `get_audio_info` with real implementations using synthesized audio from `create_test_audio_file` helper.

**Result**: Tests now verify actual integration between AudioService and AudioAnalysisTools with real audio processing.

---

#### 3. **test_audio_tools.py** - Extensive Librosa Mocking ✅
**Status**: COMPLETED (Significantly Reduced)

**Changes**: Replaced most librosa mocks with real implementations. Main functional tests now use:
- Real synthesized audio files
- Real librosa calls for tempo, pitch, and rhythm analysis
- Real soundfile calls for audio info

**Remaining Mocks**: Kept only for:
- Specific error cases that are hard to reproduce (e.g., librosa.load raising exceptions)
- Edge cases requiring specific return values that are difficult to generate with real audio
- Comparison tools tests (complex scenarios)

**Result**: Reduced from ~80 patches to significantly fewer, with most functional tests using real implementations.

---

#### 4. **test_audio_preprocessing.py** - FFmpeg Subprocess Mocking ✅
**Status**: COMPLETED

**Changes**: Replaced subprocess.run mocks with real ffmpeg calls. FFmpeg is now treated as a required, non-optional dependency for dev and CI environments.

**Remaining Mocks**: Kept only for error handling tests (ffmpeg errors, ffmpeg not found) which are appropriate for testing error paths.

**Result**: Tests now verify actual ffmpeg integration and audio conversion functionality.

---

### 🟡 Medium Priority - Consider Real Implementations

#### 5. **test_llm_service.py** - MCP Server Mocking
**Location**: Lines 46-59, used throughout

**Issue**: Mocking MCP server extensively, but some tests might benefit from a minimal real implementation.

**Current**:
```python
@pytest.fixture
def mock_mcp_server():
    server = MagicMock()
    server.get_tools.return_value = [...]
    return server
```

**Recommendation**: Consider creating a minimal test MCP server implementation for some tests, especially those testing tool calling logic.

**Rationale**: While mocking is reasonable for external dependencies, some tool calling logic might benefit from testing with a real (but minimal) server.

---

#### 6. **test_api_audio.py** and **test_api_midi.py** - Service Mocking
**Location**: Throughout both files

**Issue**: These are API layer unit tests that mock the entire service layer.

**Current Pattern**:
```python
@pytest.fixture
def mock_audio_service():
    with patch("zikos.api.audio.audio_service") as mock:
        yield mock
```

**Recommendation**: These are actually appropriate for unit tests of the API layer. However, consider adding integration tests that use real services to test the full stack.

**Rationale**: API layer unit tests should mock services (good separation of concerns), but integration tests would catch real integration issues.

---

### ✅ Appropriate Mocking (Good Examples)

#### 1. **test_audio_preprocessing.py** - Error Handling
**Location**: Error handling tests only

**Rationale**: Mocking is kept only for error cases (ffmpeg errors, ffmpeg not found) because:
- These are specific error scenarios that are hard to reproduce reliably
- Testing error paths is important but doesn't require real ffmpeg failures
- Real ffmpeg calls are used for all functional tests

**Note**: All functional tests now use real ffmpeg calls with real audio files.

---

#### 2. **test_llm_service.py** - Backend Mocking
**Location**: Throughout

**Rationale**: Mocking LLM backends is appropriate because:
- LLM inference is expensive and slow
- Tests would require model files
- Backend is an external dependency
- Mocking allows testing various response scenarios

---

#### 3. **test_api_chat_streaming.py** - WebSocket Mocking
**Location**: Lines 11-18

**Rationale**: Mocking WebSocket is appropriate because:
- WebSocket is a complex async protocol
- Real WebSocket tests would require network setup
- Mocking allows testing various message/error scenarios

---

#### 4. **test_llm_backend_streaming.py** - Backend Interface Mocking
**Location**: Lines 13-33

**Rationale**: Using a `MockBackend` class that implements the interface is good design:
- Tests the base streaming implementation
- Doesn't require real backends
- Still tests real code paths in the base class

---

## Recommendations Summary

### ✅ Completed Actions

1. ✅ **test_audio_tools.py**: Significantly reduced mocking by using real librosa with synthesized audio for most tests. Kept mocks only for edge cases and error handling.

2. ✅ **test_llm_service.py**: Replaced Path/file mocking with real file operations using `tmp_path` and `__file__` patching.

3. ✅ **test_audio_service.py**: Replaced analysis tool mocks with real implementations using synthesized audio.

4. ✅ **test_audio_preprocessing.py**: Replaced ffmpeg subprocess mocks with real ffmpeg calls (ffmpeg is now a required dependency).

### Remaining Medium-term Improvements

1. Add integration tests for API endpoints that use real services (complement the existing unit tests).

2. Consider creating a minimal test MCP server implementation for some tool calling tests.

3. Review remaining test files for similar patterns where real implementations would be more valuable.

### Testing Philosophy

The codebase already shows good judgment in some areas:
- Integration tests exist alongside unit tests
- Real audio synthesis helpers are available
- Some tests already use real implementations

The main issue is that unit tests are defaulting to mocks even when real implementations would be:
- Fast enough
- Easy to set up (helpers exist)
- More valuable (test real behavior)

## Key Takeaways

### Philosophy Applied

The refactoring followed these principles:
1. **Use real implementations when they're fast and easy to set up** - Audio synthesis helpers make real audio testing straightforward
2. **FFmpeg is a required dependency** - No need to mock it; tests should verify real integration
3. **Keep mocks for error cases** - Specific error scenarios that are hard to reproduce are appropriate to mock
4. **Test real behavior** - Real implementations catch integration issues that mocks might miss

### Impact

- **Reduced mocking significantly** in the highest-priority files
- **Improved test reliability** by testing actual code paths
- **Better integration coverage** by using real libraries and tools
- **Maintained test speed** - Real implementations are fast enough for unit tests

### Remaining Work

Some test files still use mocks appropriately (LLM backends, WebSockets, etc.) where real implementations would be:
- Too slow (LLM inference)
- Too complex to set up (WebSocket servers)
- External dependencies that are appropriately abstracted

The goal is not to eliminate all mocks, but to use real implementations where they provide more value.
