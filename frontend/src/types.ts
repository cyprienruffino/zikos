export interface WebSocketMessage {
    type: string;
    message?: string;
    content?: string;
    session_id?: string;
    tool_name?: string;
    tool_id?: string;
    arguments?: Record<string, unknown>;
    audio_file_id?: string;
    notation_url?: string;
}

export interface MetronomeState {
    bpm: number;
    beats: number;
    widgetEl: HTMLElement | null;
    intervalId: number | null;
    audioContext: AudioContext | null;
    currentBeat: number;
    isPlaying: boolean;
}

export interface TunerState {
    referenceFreq: number;
    widgetEl: HTMLElement;
    analyser: AnalyserNode | null;
    microphone: MediaStreamAudioSourceNode | null;
    audioContext: AudioContext | null;
    isRunning: boolean;
    animationFrame: number | null;
}

export interface ChordProgressionState {
    chords: string[];
    tempo: number;
    timeSignature: string;
    chordsPerBar: number;
    widgetEl: HTMLElement;
    audioContext: AudioContext | null;
    intervalId: number | null;
    currentChordIndex: number;
    isPlaying: boolean;
}

export interface TempoTrainerState {
    startBpm: number;
    endBpm: number;
    durationMinutes: number;
    timeSignature: string;
    rampType: string;
    widgetEl: HTMLElement;
    metronome: {
        bpm: number;
        beats: number;
        audioContext: AudioContext;
        intervalId: number | null;
        currentBeat: number;
    } | null;
    startTime: number | null;
    pausedTime: number;
    isPlaying: boolean;
}

export interface EarTrainerState {
    mode: string;
    difficulty: string;
    rootNote: string;
    intervals: string[];
    widgetEl: HTMLElement;
    currentAnswer: string | null;
    audioContext: AudioContext | null;
}

export interface PracticeTimerState {
    durationMinutes: number | null;
    goal: string | null;
    breakIntervalMinutes: number | null;
    widgetEl: HTMLElement;
    startTime: number | null;
    pausedTime: number;
    elapsedSeconds: number;
    intervalId: number | null;
    breakIntervalId: number | null;
    isRunning: boolean;
}

// System API types
export interface GpuInfo {
    available: boolean;
    device: number | null;
    name: string | null;
    memory_total_gb: number | null;
    memory_free_gb: number | null;
}

export interface RamInfo {
    total_gb: number;
    available_gb: number;
}

export interface GpuHint {
    hint_type: string;
    message: string;
    docs_url: string;
}

export interface HardwareInfo {
    gpu: GpuInfo;
    ram: RamInfo;
    gpu_hint: GpuHint | null;
    tier: string;
}

export interface ModelRecommendation {
    name: string;
    filename: string;
    size_gb: number;
    vram_required_gb: number;
    ram_required_gb: number;
    context_window: number;
    download_url: string;
    description: string;
    tier: string;
}

export interface ModelRecommendationsResponse {
    default_model_path: string;
    primary_recommendation: ModelRecommendation | null;
    all_recommendations: ModelRecommendation[];
}

export interface SystemStatusResponse {
    model_loaded: boolean;
    model_path: string | null;
    initialization_error: string | null;
    hardware: HardwareInfo;
}
