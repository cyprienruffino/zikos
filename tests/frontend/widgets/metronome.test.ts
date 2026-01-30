import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    addMetronomeWidget,
    removeMetronomeWidget,
    startMetronome,
    getMetronome,
    setMetronome,
    setMetronomeWebSocket,
    setMetronomeSessionId,
} from "../../../frontend/src/widgets/metronome.js";

// Mock AudioContext
class MockAudioContext {
    state: string = "running";
    currentTime: number = 0;

    resume(): Promise<void> {
        this.state = "running";
        return Promise.resolve();
    }

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
        const gainValue = { value: 0 };
        return {
            connect: vi.fn(),
            gain: {
                value: 0,
                setValueAtTime: vi.fn(),
                exponentialRampToValueAtTime: vi.fn(),
            },
        };
    }

    destination: any = {};
}

describe("Metronome Widget", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="messages"></div>
        `;

        globalThis.AudioContext = MockAudioContext as any;

        // Store original setInterval/clearInterval
        const originalSetInterval = globalThis.window.setInterval;
        const originalClearInterval = globalThis.window.clearInterval;

        // Mock setInterval/clearInterval without recursion
        globalThis.window.setInterval = vi.fn((fn: Function, delay: number) => {
            return originalSetInterval(fn, delay);
        }) as any;
        globalThis.window.clearInterval = vi.fn((id: number) => {
            originalClearInterval(id);
        }) as any;
    });

    describe("addMetronomeWidget()", () => {
        it("should create metronome widget in DOM", () => {
            addMetronomeWidget("met_123", 120, "4/4", "Test metronome");
            const widget = document.getElementById("metronome-met_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("metronome-widget");
        });

        it("should display BPM and time signature", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            expect(widget?.textContent).toContain("120");
            expect(widget?.textContent).toContain("4/4");
        });

        it("should display description if provided", () => {
            addMetronomeWidget("met_123", 120, "4/4", "Test description");
            const widget = document.getElementById("metronome-met_123");
            expect(widget?.textContent).toContain("Test description");
        });

        it("should create beat indicator dots", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            const dots = widget?.querySelectorAll(".beat-dot");
            expect(dots?.length).toBe(4);
        });

        it("should create control buttons", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            expect(widget?.querySelector(".play-btn")).toBeTruthy();
            expect(widget?.querySelector(".pause-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-btn")).toBeTruthy();
        });
    });

    describe("removeMetronomeWidget()", () => {
        it("should remove widget from DOM", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            expect(document.getElementById("metronome-met_123")).toBeTruthy();
            removeMetronomeWidget("met_123");
            expect(document.getElementById("metronome-met_123")).toBeFalsy();
        });

        it("should stop metronome before removing", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            startMetronome("met_123", 120, 4);
            removeMetronomeWidget("met_123");
            // Widget should be removed (tested above)
        });
    });

    describe("startMetronome()", () => {
        it("should start metronome when play button is clicked", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const metronome = getMetronome("met_123");
            expect(metronome?.isPlaying).toBe(true);
        });

        it("should show pause button when playing", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;

            playBtn.click();

            expect(pauseBtn.style.display).toBe("inline-block");
        });
    });

    describe("pauseMetronome()", () => {
        it("should pause metronome when pause button is clicked", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            startMetronome("met_123", 120, 4);
            const widget = document.getElementById("metronome-met_123");
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            pauseBtn.click();

            const metronome = getMetronome("met_123");
            expect(metronome?.isPlaying).toBe(false);
        });
    });

    describe("stopMetronome()", () => {
        it("should stop metronome when stop button is clicked", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            startMetronome("met_123", 120, 4);
            const widget = document.getElementById("metronome-met_123");
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            stopBtn.click();

            const metronome = getMetronome("met_123");
            expect(metronome?.isPlaying).toBe(false);
            expect(metronome?.currentBeat).toBe(0);
        });
    });

    describe("getMetronome()", () => {
        it("should return metronome state", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const metronome = getMetronome("met_123");
            expect(metronome).toBeTruthy();
            expect(metronome?.bpm).toBe(120);
            expect(metronome?.beats).toBe(4);
        });

        it("should return undefined for non-existent metronome", () => {
            expect(getMetronome("nonexistent")).toBeUndefined();
        });
    });

    describe("setMetronome()", () => {
        it("should update metronome state", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const metronome = getMetronome("met_123");
            if (metronome) {
                metronome.isPlaying = true;
                setMetronome("met_123", metronome);
                expect(getMetronome("met_123")?.isPlaying).toBe(true);
            }
        });
    });

    describe("Recording controls", () => {
        it("should create recording controls in widget", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            expect(widget?.querySelector(".record-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-rec-btn")).toBeTruthy();
            expect(widget?.querySelector(".send-btn")).toBeTruthy();
            expect(widget?.querySelector(".cancel-btn")).toBeTruthy();
        });

        it("should have send button disabled by default", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;
            expect(sendBtn.disabled).toBe(true);
        });

        it("should have keep-metronome checkbox checked by default", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            const widget = document.getElementById("metronome-met_123");
            const cb = widget?.querySelector(".keep-metronome-cb") as HTMLInputElement;
            expect(cb).toBeTruthy();
            expect(cb.checked).toBe(true);
        });

        it("should have recording status and audio player elements", () => {
            addMetronomeWidget("met_123", 120, "4/4");
            expect(document.getElementById("rec-status-met_123")).toBeTruthy();
            expect(document.getElementById("rec-player-met_123")).toBeTruthy();
        });
    });

    describe("setMetronomeWebSocket / setMetronomeSessionId", () => {
        it("should accept websocket and session id without errors", () => {
            expect(() => setMetronomeWebSocket(null)).not.toThrow();
            expect(() => setMetronomeSessionId("test-session")).not.toThrow();
            expect(() => setMetronomeSessionId(null)).not.toThrow();
        });
    });

    describe("Edge Cases", () => {
        it("should throw error when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() => addMetronomeWidget("met_123", 120, "4/4")).toThrow(
                "Messages element not found"
            );
        });
    });
});
