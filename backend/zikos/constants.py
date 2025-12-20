"""Application constants and configuration values

All hardcoded constants should be defined here for easy configuration.
"""


class LLMConstants:
    """Constants for LLM service and conversation management"""

    # Token limits (for 32K context window)
    MAX_TOKENS_PREPARE_MESSAGES: int = 25000
    MAX_TOKENS_SAFETY_CHECK: int = 28000
    TOKENS_RESERVE_RESPONSE: int = 4000
    TOKENS_RESERVE_AUDIO_ANALYSIS: int = 5000

    # Iteration limits
    MAX_ITERATIONS: int = 10

    # Response quality checks
    MAX_WORDS_RESPONSE: int = 500
    MIN_UNIQUE_WORD_RATIO: float = 0.15
    MAX_SINGLE_CHAR_RATIO: float = 0.3

    # Default max_tokens for _prepare_messages (legacy, can be overridden)
    DEFAULT_MAX_TOKENS: int = 3000


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
    TIMBRE_CONSISTENCY_DIVISOR: float = 500.0

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


class RecordingConstants:
    """Constants for audio recording"""

    DEFAULT_MAX_DURATION: float = 30.0


# Convenience access
LLM = LLMConstants()
AUDIO = AudioAnalysisConstants()
RECORDING = RecordingConstants()
