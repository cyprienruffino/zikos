/**
 * Shared Web Audio engine.
 *
 * - One lazily-created AudioContext for the whole app (browsers cap the
 *   number of concurrent contexts; widgets previously created one each,
 *   or even one per ear-trainer question, and never closed them).
 * - A lookahead beat scheduler: a ~25ms JS timer schedules oscillator
 *   audio ~100ms ahead on AudioContext.currentTime, so playback neither
 *   drifts nor stutters when background tabs throttle timers, unlike the
 *   previous setInterval-per-beat approach.
 */

let sharedContext: AudioContext | null = null;

export function getAudioContext(): AudioContext {
    if (!sharedContext || sharedContext.state === "closed") {
        sharedContext = new AudioContext();
    }
    if (sharedContext.state === "suspended") {
        void sharedContext.resume();
    }
    return sharedContext;
}

/** Test hook: forget the shared context so mocks can be swapped per test. */
export function resetAudioEngine(): void {
    sharedContext = null;
}

/** Schedule a short metronome-style click at an exact context time. */
export function scheduleClick(
    ctx: AudioContext,
    time: number,
    frequency: number,
    gainValue: number = 0.3
): void {
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    oscillator.frequency.value = frequency;
    oscillator.type = "sine";
    gainNode.gain.setValueAtTime(gainValue, time);
    gainNode.gain.exponentialRampToValueAtTime(0.01, time + 0.1);
    oscillator.start(time);
    oscillator.stop(time + 0.1);
}

export interface BeatSchedulerOptions {
    bpm: number;
    /** Number of beats per cycle (beat indexes are 0..beats-1). */
    beats: number;
    /** Called near the audible time of each beat (for visuals). */
    onBeat?: (beatIndex: number) => void;
    /**
     * Schedule the audio for a beat at an exact context time.
     * Defaults to a click (800 Hz downbeat, 600 Hz otherwise).
     */
    scheduleAudio?: (ctx: AudioContext, time: number, beatIndex: number) => void;
}

export interface BeatScheduler {
    start(): void;
    stop(): void;
    setBpm(bpm: number): void;
    resetBeat(): void;
    getCurrentBeat(): number;
    isRunning(): boolean;
}

const LOOKAHEAD_MS = 25;
const SCHEDULE_AHEAD_SEC = 0.1;
// Safety valve against pathological beat intervals / frozen clocks.
const MAX_EVENTS_PER_TICK = 16;

export function createBeatScheduler(options: BeatSchedulerOptions): BeatScheduler {
    let bpm = options.bpm;
    let beatIndex = 0;
    let nextNoteTime = 0;
    let timerId: number | null = null;
    const visualTimeouts = new Set<number>();

    const scheduleAudio =
        options.scheduleAudio ??
        ((ctx: AudioContext, time: number, beat: number): void =>
            scheduleClick(ctx, time, beat === 0 ? 800 : 600));

    function tick(): void {
        const ctx = getAudioContext();
        let scheduled = 0;
        while (
            nextNoteTime < ctx.currentTime + SCHEDULE_AHEAD_SEC &&
            scheduled < MAX_EVENTS_PER_TICK
        ) {
            const beat = beatIndex;
            const time = nextNoteTime;
            scheduleAudio(ctx, time, beat);
            if (options.onBeat) {
                const delayMs = Math.max(0, (time - ctx.currentTime) * 1000);
                const handle = window.setTimeout(() => {
                    visualTimeouts.delete(handle);
                    options.onBeat?.(beat);
                }, delayMs);
                visualTimeouts.add(handle);
            }
            nextNoteTime += 60 / bpm;
            beatIndex = (beatIndex + 1) % options.beats;
            scheduled++;
        }
    }

    return {
        start(): void {
            if (timerId !== null) return;
            const ctx = getAudioContext();
            nextNoteTime = ctx.currentTime;
            tick();
            timerId = window.setInterval(tick, LOOKAHEAD_MS);
        },
        stop(): void {
            if (timerId !== null) {
                window.clearInterval(timerId);
                timerId = null;
            }
            visualTimeouts.forEach((handle) => window.clearTimeout(handle));
            visualTimeouts.clear();
        },
        setBpm(newBpm: number): void {
            if (Number.isFinite(newBpm) && newBpm > 0) {
                bpm = newBpm;
            }
        },
        resetBeat(): void {
            beatIndex = 0;
        },
        getCurrentBeat(): number {
            return beatIndex;
        },
        isRunning(): boolean {
            return timerId !== null;
        },
    };
}
