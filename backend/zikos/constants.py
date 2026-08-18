"""Application constants and configuration values

All hardcoded constants should be defined here for easy configuration.
"""

from dataclasses import dataclass


class LLMConstants:
    """Constants for LLM service and conversation management"""

    # Token limits (for 128K context window, dynamically adjusted based on model)
    MAX_TOKENS_PREPARE_MESSAGES: int = 120000
    MAX_TOKENS_SAFETY_CHECK: int = 125000
    TOKENS_RESERVE_RESPONSE: int = 4000
    TOKENS_RESERVE_AUDIO_ANALYSIS: int = 5000

    # Iteration limits
    MAX_ITERATIONS: int = 10

    # Tool calling limits
    MAX_CONSECUTIVE_TOOL_CALLS: int = 5
    RECENT_TOOL_CALLS_WINDOW: int = 10
    REPETITIVE_PATTERN_THRESHOLD: int = 4

    # Response quality checks
    MAX_WORDS_RESPONSE: int = 500
    MIN_UNIQUE_WORD_RATIO: float = 0.15
    MAX_SINGLE_CHAR_RATIO: float = 0.3

    # Default max_tokens for _prepare_messages (legacy, can be overridden)
    DEFAULT_MAX_TOKENS: int = 3000

    # LLM configuration defaults
    DEFAULT_N_CTX: int = 32768
    DEFAULT_N_GPU_LAYERS: int = -1
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.9
    DEFAULT_TOP_K: int = 40
    DEFAULT_MAX_THINKING_TOKENS: int = 0  # 0 = unlimited

    # Default model keys (for download_model.py MODEL_CONFIGS)
    DEFAULT_GPU_MODEL: str = "mistral-7b-instruct-v0.3-q4"
    DEFAULT_CPU_MODEL: str = "phi-3-mini-q4"


class AudioAnalysisConstants:
    """Constants for audio analysis tools"""

    # Minimum audio duration (seconds)
    MIN_AUDIO_DURATION: float = 0.5

    # FFT and spectral analysis
    STFT_N_FFT: int = 2048

    # Frequency thresholds (Hz)
    LOW_FREQ_THRESHOLD: int = 2000
    HIGH_FREQ_THRESHOLD: int = 2000

    # Timbre analysis
    BRIGHTNESS_DIVISOR: float = 5000.0
    SHARPNESS_DIVISOR: float = 8000.0
    TIMBRE_CONSISTENCY_DIVISOR: float = 1500.0

    # Dynamics analysis
    DYNAMIC_CONSISTENCY_DIVISOR: float = 10.0
    PEAK_THRESHOLD_RATIO: float = 0.9
    DYNAMIC_CONSISTENCY_THRESHOLD: float = 0.75

    # Tempo analysis
    TEMPO_STABILITY_THRESHOLD: float = 0.85
    TEMPO_CONFIDENCE: float = 0.9
    TEMPO_RUSHING_THRESHOLD: float = 0.98
    TEMPO_DRAGGING_THRESHOLD: float = 1.02
    TEMPO_WINDOW_SIZE: int = 8

    # Rhythm analysis
    RHYTHM_CONFIDENCE: float = 0.9
    RHYTHM_TIMING_ACCURACY_BASE: float = 0.7
    RHYTHM_TIMING_ACCURACY_DEVIATION_MS: int = 50
    RHYTHM_TIMING_ACCURACY_DIVISOR: float = 500.0

    # Pitch analysis
    PITCH_CONFIDENCE: float = 0.9
    PITCH_VOICED_PROB_THRESHOLD: float = 0.5

    # Groove analysis
    GROOVE_CONSISTENCY: float = 0.90
    GROOVE_RATIO_MIN: float = 0.5
    GROOVE_RATIO_MAX: float = 2.0
    GROOVE_DEFAULT_BEAT_INTERVAL: float = 0.5

    # Phrase segmentation
    PHRASE_CONFIDENCE_DEFAULT: float = 0.5
    PHRASE_CONFIDENCE_ENERGY_BOOST: float = 0.3
    PHRASE_CONFIDENCE_MIN: float = 0.5

    # Repetition detection
    REPETITION_MIN_SIMILARITY: float = 0.75

    # Quality thresholds
    QUALITY_THRESHOLD_LOW: float = 0.75

    # Amplitude envelope sampling
    AMPLITUDE_ENVELOPE_DOWNSAMPLE: int = 10


@dataclass(frozen=True)
class InstrumentDSPProfile:
    """Pitch-tracking parameters for one instrument family.

    fmin_hz/fmax_hz bound pyin's F0 search range; pyin_frame_length is the
    analysis window in samples — low fundamentals need longer windows to
    resolve (pyin's longest detectable period is roughly frame_length/2).
    """

    fmin_hz: float
    fmax_hz: float
    pyin_frame_length: int


# Wide generic range used when the instrument is unknown: C1..C7 with the
# historical 4096-sample window.
DEFAULT_INSTRUMENT_DSP_PROFILE = InstrumentDSPProfile(
    fmin_hz=32.70, fmax_hz=2093.0, pyin_frame_length=4096
)

# fmin sits below each instrument's lowest standard fundamental with margin
# for drop/detuned setups: 5-string bass low B0 = 30.87 Hz, drop-D guitar
# D2 = 73.42 Hz, piano A0 = 27.5 Hz. fmax caps the search near the highest
# playable fundamental so pyin doesn't lock onto harmonics.
INSTRUMENT_DSP_PROFILES: dict[str, InstrumentDSPProfile] = {
    "bass": InstrumentDSPProfile(fmin_hz=25.0, fmax_hz=500.0, pyin_frame_length=8192),
    "guitar": InstrumentDSPProfile(fmin_hz=70.0, fmax_hz=1400.0, pyin_frame_length=4096),
    "piano": InstrumentDSPProfile(fmin_hz=26.0, fmax_hz=4200.0, pyin_frame_length=8192),
    "voice": InstrumentDSPProfile(fmin_hz=60.0, fmax_hz=1500.0, pyin_frame_length=4096),
    "violin": InstrumentDSPProfile(fmin_hz=180.0, fmax_hz=3600.0, pyin_frame_length=2048),
}


class RecordingConstants:
    """Constants for audio recording"""

    DEFAULT_MAX_DURATION: float = 30.0


class UploadConstants:
    """Constants for file uploads"""

    # Maximum upload size in bytes (50 MB)
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024

    # Allowed audio file extensions (lowercase, with leading dot)
    ALLOWED_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
        {".wav", ".mp3", ".ogg", ".flac", ".webm", ".m4a"}
    )

    # Allowed content types for audio uploads. Browsers commonly report
    # webm recordings as video/webm and generic uploads as octet-stream.
    ALLOWED_CONTENT_TYPE_PREFIXES: tuple[str, ...] = ("audio/",)
    ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"video/webm", "application/octet-stream"})


# Convenience access
LLM = LLMConstants()
AUDIO = AudioAnalysisConstants()
RECORDING = RecordingConstants()
