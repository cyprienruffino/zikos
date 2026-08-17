import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
    getAudioContext,
    resetAudioEngine,
    createBeatScheduler,
    scheduleClick,
} from "../../../frontend/src/widgets/audioEngine.js";

class MockAudioContext {
    state: string = "running";
    currentTime: number = 0;
    destination: any = {};
    resume = vi.fn(() => {
        this.state = "running";
        return Promise.resolve();
    });

    createOscillator(): any {
        return {
            connect: vi.fn(),
            start: vi.fn(),
            stop: vi.fn(),
            frequency: { value: 0 },
            type: "sine",
        };
    }

    createGain(): any {
        return {
            connect: vi.fn(),
            gain: {
                value: 0,
                setValueAtTime: vi.fn(),
                exponentialRampToValueAtTime: vi.fn(),
            },
        };
    }
}

describe("audioEngine", () => {
    beforeEach(() => {
        globalThis.AudioContext = vi.fn(() => new MockAudioContext()) as any;
        resetAudioEngine();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe("getAudioContext()", () => {
        it("should lazily create one shared context", () => {
            const first = getAudioContext();
            const second = getAudioContext();
            expect(first).toBe(second);
            expect(globalThis.AudioContext).toHaveBeenCalledTimes(1);
        });

        it("should resume a suspended context", () => {
            const ctx = getAudioContext() as unknown as MockAudioContext;
            ctx.state = "suspended";
            getAudioContext();
            expect(ctx.resume).toHaveBeenCalled();
        });

        it("should recreate the context if it was closed", () => {
            const first = getAudioContext() as unknown as MockAudioContext;
            first.state = "closed";
            const second = getAudioContext();
            expect(second).not.toBe(first);
        });

        it("should reset for tests via resetAudioEngine()", () => {
            const first = getAudioContext();
            resetAudioEngine();
            const second = getAudioContext();
            expect(second).not.toBe(first);
        });
    });

    describe("scheduleClick()", () => {
        it("should schedule an oscillator at the given time", () => {
            const ctx = new MockAudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            vi.spyOn(ctx, "createOscillator").mockReturnValue(osc);
            vi.spyOn(ctx, "createGain").mockReturnValue(gain);

            scheduleClick(ctx as unknown as AudioContext, 1.5, 800);

            expect(osc.frequency.value).toBe(800);
            expect(gain.gain.setValueAtTime).toHaveBeenCalledWith(0.3, 1.5);
            expect(osc.start).toHaveBeenCalledWith(1.5);
            expect(osc.stop).toHaveBeenCalledWith(1.6);
        });
    });

    describe("createBeatScheduler()", () => {
        it("should run a lookahead timer instead of a per-beat interval", () => {
            const setIntervalSpy = vi.spyOn(window, "setInterval");
            const scheduler = createBeatScheduler({ bpm: 120, beats: 4 });
            scheduler.start();

            const call = setIntervalSpy.mock.calls[setIntervalSpy.mock.calls.length - 1];
            // ~25ms lookahead timer, not the 500ms beat interval of 120 BPM
            expect(call[1]).toBeLessThan(100);
            scheduler.stop();
            setIntervalSpy.mockRestore();
        });

        it("should schedule audio ahead on the context clock", () => {
            const ctx = getAudioContext() as unknown as MockAudioContext;
            const scheduled: number[] = [];
            const scheduler = createBeatScheduler({
                bpm: 120,
                beats: 4,
                scheduleAudio: (_ctx, time) => scheduled.push(time),
            });
            ctx.currentTime = 10;
            scheduler.start();
            // First beat scheduled at/after currentTime
            expect(scheduled.length).toBeGreaterThan(0);
            expect(scheduled[0]).toBeGreaterThanOrEqual(10);
            scheduler.stop();
        });

        it("should advance beats modulo the cycle length", () => {
            const ctx = getAudioContext() as unknown as MockAudioContext;
            const beatsSeen: number[] = [];
            const scheduler = createBeatScheduler({
                // 2400 BPM (0.025s beats) so several beats fall inside the
                // 0.1s lookahead window of the first tick
                bpm: 2400,
                beats: 3,
                scheduleAudio: (_ctx, _time, beat) => beatsSeen.push(beat),
            });
            ctx.currentTime = 0;
            scheduler.start();
            scheduler.stop();
            expect(beatsSeen.slice(0, 3)).toEqual([0, 1, 2]);
        });

        it("should stop scheduling when stopped", () => {
            const clearIntervalSpy = vi.spyOn(window, "clearInterval");
            const scheduler = createBeatScheduler({ bpm: 120, beats: 4 });
            scheduler.start();
            expect(scheduler.isRunning()).toBe(true);
            scheduler.stop();
            expect(scheduler.isRunning()).toBe(false);
            expect(clearIntervalSpy).toHaveBeenCalled();
            clearIntervalSpy.mockRestore();
        });

        it("should change tempo in place via setBpm", () => {
            const ctx = getAudioContext() as unknown as MockAudioContext;
            const scheduled: number[] = [];
            const scheduler = createBeatScheduler({
                bpm: 60,
                beats: 4,
                scheduleAudio: (_ctx, time) => scheduled.push(time),
            });
            scheduler.setBpm(1200); // 0.05s per beat
            ctx.currentTime = 0;
            scheduler.start();
            scheduler.stop();
            // With 0.05s beats the first two land inside the 0.1s lookahead
            expect(scheduled.length).toBeGreaterThanOrEqual(2);
            expect(scheduled[1] - scheduled[0]).toBeCloseTo(0.05, 5);
        });

        it("should ignore invalid bpm values in setBpm", () => {
            const scheduler = createBeatScheduler({ bpm: 120, beats: 4 });
            expect(() => {
                scheduler.setBpm(0);
                scheduler.setBpm(NaN);
                scheduler.setBpm(-10);
            }).not.toThrow();
        });
    });
});
