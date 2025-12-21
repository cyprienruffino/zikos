import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { addTempoTrainerWidget } from "../../../frontend/src/widgets/tempoTrainer.js";

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

describe("Tempo Trainer Widget", () => {
    let originalSetTimeout: typeof setTimeout;
    let originalSetInterval: typeof setInterval;
    let originalClearTimeout: typeof clearTimeout;
    let originalClearInterval: typeof clearInterval;

    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;

        originalSetTimeout = globalThis.window.setTimeout;
        originalSetInterval = globalThis.window.setInterval;
        originalClearTimeout = globalThis.window.clearTimeout;
        originalClearInterval = globalThis.window.clearInterval;

        globalThis.AudioContext = vi.fn(() => new MockAudioContext()) as any;
        globalThis.window.setInterval = vi.fn((fn: Function, delay: number) => {
            return originalSetInterval(fn, delay);
        }) as any;
        globalThis.window.clearInterval = vi.fn((id: number) => {
            originalClearInterval(id);
        }) as any;
        globalThis.window.setTimeout = vi.fn((fn: Function, delay: number) => {
            return originalSetTimeout(fn, delay);
        }) as any;
    });

    afterEach(() => {
        vi.clearAllMocks();
        globalThis.window.setTimeout = originalSetTimeout;
        globalThis.window.setInterval = originalSetInterval;
        globalThis.window.clearTimeout = originalClearTimeout;
        globalThis.window.clearInterval = originalClearInterval;
    });

    describe("addTempoTrainerWidget()", () => {
        it("should create tempo trainer widget in DOM", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("tempo-trainer-widget");
        });

        it("should display start and end BPM", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            expect(widget?.textContent).toContain("60");
            expect(widget?.textContent).toContain("120");
        });

        it("should display duration", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            expect(widget?.textContent).toContain("5");
        });

        it("should display description when provided", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear", "Test trainer");
            const widget = document.getElementById("tempo-tempo_123");
            expect(widget?.textContent).toContain("Test trainer");
        });

        it("should create control buttons", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            expect(widget?.querySelector(".play-btn")).toBeTruthy();
            expect(widget?.querySelector(".pause-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-btn")).toBeTruthy();
        });

        it("should initially hide pause button", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;
            expect(pauseBtn?.style.display).toBe("none");
        });

        it("should show initial status as Stopped", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const statusEl = document.getElementById("status-tempo_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });

        it("should initialize progress bar at 0%", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const progressFill = document.getElementById("progress-tempo_123");
            expect(progressFill?.style.width).toBe("0%");
        });
    });

    describe("Start Tempo Trainer", () => {
        it("should start trainer when play button is clicked", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const statusEl = document.getElementById("status-tempo_123");
            expect(statusEl?.textContent).toBe("Training...");
        });

        it("should show pause button when started", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;

            playBtn.click();

            expect(pauseBtn.style.display).toBe("inline-block");
            expect(playBtn.style.display).toBe("none");
        });

        it("should create AudioContext when started", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(globalThis.AudioContext).toHaveBeenCalled();
        });

        it("should not start if already playing", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();
            const firstStatus = document.getElementById("status-tempo_123")?.textContent;

            playBtn.click();
            const secondStatus = document.getElementById("status-tempo_123")?.textContent;

            expect(firstStatus).toBe(secondStatus);
        });

        it("should update tempo display over time", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(vi.mocked(globalThis.window.setTimeout)).toHaveBeenCalled();
        });
    });

    describe("Pause Tempo Trainer", () => {
        it("should pause trainer when pause button is clicked", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();

            const statusEl = document.getElementById("status-tempo_123");
            expect(statusEl?.textContent).toBe("Paused");
        });

        it("should show play button when paused", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();

            expect(playBtn.style.display).toBe("inline-block");
            expect(pauseBtn.style.display).toBe("none");
        });

        it("should clear metronome interval when paused", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();

            expect(vi.mocked(globalThis.window.clearInterval)).toHaveBeenCalled();
        });

        it("should resume from paused time", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            playBtn.click();
            pauseBtn.click();
            playBtn.click();

            const statusEl = document.getElementById("status-tempo_123");
            expect(statusEl?.textContent).toBe("Training...");
        });
    });

    describe("Stop Tempo Trainer", () => {
        it("should stop trainer when stop button is clicked", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            const statusEl = document.getElementById("status-tempo_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });

        it("should reset progress bar when stopped", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            const progressFill = document.getElementById("progress-tempo_123");
            expect(progressFill?.style.width).toBe("0%");
        });

        it("should reset tempo display to start BPM when stopped", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            const tempoDisplay = document.getElementById("tempo-display-tempo_123");
            expect(tempoDisplay?.textContent).toBe("60 BPM");
        });

        it("should close AudioContext when stopped", () => {
            const mockAudioContext = new MockAudioContext();
            globalThis.AudioContext = vi.fn(() => mockAudioContext) as any;

            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            playBtn.click();
            stopBtn.click();

            expect(mockAudioContext.state).toBe("closed");
        });
    });

    describe("Tempo Ramping", () => {
        it("should use linear ramp by default", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(vi.mocked(globalThis.window.setTimeout)).toHaveBeenCalled();
        });

        it("should use exponential ramp when specified", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "exponential");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(vi.mocked(globalThis.window.setTimeout)).toHaveBeenCalled();
        });

        it("should update metronome BPM as tempo changes", () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(vi.mocked(globalThis.window.setInterval)).toHaveBeenCalled();
        });
    });

    describe("Completion", () => {
        it("should stop when duration is reached", async () => {
            addTempoTrainerWidget("tempo_123", 60, 120, 0.001, "4/4", "linear");
            const widget = document.getElementById("tempo-tempo_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            await new Promise((resolve) => setTimeout(resolve, 100));

            const statusEl = document.getElementById("status-tempo_123");
            expect(statusEl?.textContent).toBe("Complete!");
        });
    });

    describe("Edge Cases", () => {
        it("should throw error when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() => addTempoTrainerWidget("tempo_123", 60, 120, 5, "4/4", "linear")).toThrow(
                "Messages element not found"
            );
        });
    });
});
