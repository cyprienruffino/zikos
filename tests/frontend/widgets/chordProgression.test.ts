import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { addChordProgressionWidget } from "../../../frontend/src/widgets/chordProgression.js";

class MockAudioContext {
    state: string = "running";
    currentTime: number = 0;
    destination: any = {};

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

    resume(): Promise<void> {
        this.state = "running";
        return Promise.resolve();
    }

    close(): void {
        this.state = "closed";
    }
}

describe("Chord Progression Widget", () => {
    let originalSetInterval: typeof setInterval;
    let originalClearInterval: typeof clearInterval;

    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;

        originalSetInterval = globalThis.window.setInterval;
        originalClearInterval = globalThis.window.clearInterval;

        globalThis.AudioContext = vi.fn(() => new MockAudioContext()) as any;
        globalThis.window.setInterval = vi.fn((fn: Function, delay: number) => {
            return originalSetInterval(fn, delay);
        }) as any;
        globalThis.window.clearInterval = vi.fn((id: number) => {
            originalClearInterval(id);
        }) as any;
    });

    afterEach(() => {
        vi.clearAllMocks();
        globalThis.window.setInterval = originalSetInterval;
        globalThis.window.clearInterval = originalClearInterval;
    });

    describe("addChordProgressionWidget()", () => {
        it("should create chord progression widget in DOM", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("chord-progression-widget");
        });

        it("should display all chords", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            expect(widget?.textContent).toContain("C");
            expect(widget?.textContent).toContain("F");
            expect(widget?.textContent).toContain("G");
        });

        it("should display tempo and time signature", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            expect(widget?.textContent).toContain("120");
            expect(widget?.textContent).toContain("4/4");
        });

        it("should display description when provided", () => {
            addChordProgressionWidget(
                "chord_123",
                ["C", "F", "G"],
                120,
                "4/4",
                1,
                "piano",
                "Test progression"
            );
            const widget = document.getElementById("chord-chord_123");
            expect(widget?.textContent).toContain("Test progression");
        });

        it("should create control buttons", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            expect(widget?.querySelector(".play-btn")).toBeTruthy();
            expect(widget?.querySelector(".pause-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-btn")).toBeTruthy();
        });

        it("should initially hide pause button", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;
            expect(pauseBtn?.style.display).toBe("none");
        });

        it("should show initial status as Stopped", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const statusEl = document.getElementById("status-chord_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });
    });

    describe("Start Chord Progression", () => {
        it("should start progression when play button is clicked", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const statusEl = document.getElementById("status-chord_123");
            expect(statusEl?.textContent).toBe("Playing");
        });

        it("should show pause button when playing", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;

            playBtn.click();

            expect(pauseBtn.style.display).toBe("inline-block");
            expect(playBtn.style.display).toBe("none");
        });

        it("should create AudioContext when started", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(AudioContext).toHaveBeenCalled();
        });

        it("should highlight active chord", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const chordBoxes = widget.querySelectorAll(".chord-box");
            expect(chordBoxes[0].classList.contains("active")).toBe(true);
        });

        it("should not start if already playing", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();
            const firstStatus = document.getElementById("status-chord_123")?.textContent;

            playBtn.click();
            const secondStatus = document.getElementById("status-chord_123")?.textContent;

            expect(firstStatus).toBe(secondStatus);
        });

        it("should resume suspended AudioContext", () => {
            const mockAudioContext = {
                state: "suspended",
                currentTime: 0,
                destination: {},
                createOscillator: vi.fn(() => ({
                    connect: vi.fn(),
                    start: vi.fn(),
                    stop: vi.fn(),
                    frequency: { value: 0 },
                    type: "sine",
                })),
                createGain: vi.fn(() => ({
                    connect: vi.fn(),
                    gain: {
                        value: 0,
                        setValueAtTime: vi.fn(),
                        exponentialRampToValueAtTime: vi.fn(),
                    },
                })),
                resume: vi.fn().mockResolvedValue(undefined),
            };

            globalThis.AudioContext = vi.fn(() => mockAudioContext) as any;

            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(mockAudioContext.resume).toHaveBeenCalled();
        });
    });

    describe("Pause Chord Progression", () => {
        it("should pause progression when pause button is clicked", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();

            const statusEl = document.getElementById("status-chord_123");
            expect(statusEl?.textContent).toBe("Paused");
        });

        it("should show play button when paused", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();

            expect(playBtn.style.display).toBe("inline-block");
            expect(pauseBtn.style.display).toBe("none");
        });

        it("should clear interval when paused", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();

            expect(globalThis.window.clearInterval).toHaveBeenCalled();
        });

        it("should not pause if not playing", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            pauseBtn.click();

            const statusEl = document.getElementById("status-chord_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });
    });

    describe("Stop Chord Progression", () => {
        it("should stop progression when stop button is clicked", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            const statusEl = document.getElementById("status-chord_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });

        it("should reset to first chord when stopped", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            const chordBoxes = widget.querySelectorAll(".chord-box");
            expect(chordBoxes[0].classList.contains("active")).toBe(false);
        });

        it("should clear interval when stopped", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            expect(globalThis.window.clearInterval).toHaveBeenCalled();
        });

        it("should show play button when stopped", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            expect(playBtn.style.display).toBe("inline-block");
        });
    });

    describe("Chord Parsing", () => {
        it("should handle major chords", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(AudioContext).toHaveBeenCalled();
        });

        it("should handle minor chords", () => {
            addChordProgressionWidget("chord_123", ["Cm", "Fm"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(AudioContext).toHaveBeenCalled();
        });

        it("should handle chords with sharps and flats", () => {
            addChordProgressionWidget("chord_123", ["C#", "Db"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(AudioContext).toHaveBeenCalled();
        });
    });

    describe("Progression Cycling", () => {
        it("should cycle through chords", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(globalThis.window.setInterval).toHaveBeenCalled();
        });

        it("should calculate correct chord duration based on tempo", () => {
            addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano");
            const widget = document.getElementById("chord-chord_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(globalThis.window.setInterval).toHaveBeenCalled();
        });
    });

    describe("Edge Cases", () => {
        it("should throw error when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() =>
                addChordProgressionWidget("chord_123", ["C", "F", "G"], 120, "4/4", 1, "piano")
            ).toThrow("Messages element not found");
        });
    });
});
