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
