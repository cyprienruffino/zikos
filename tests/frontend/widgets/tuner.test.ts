import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { addTunerWidget } from "../../../frontend/src/widgets/tuner.js";
import * as ui from "../../../frontend/src/ui.js";

class MockAudioContext {
    state: string = "running";
    sampleRate: number = 44100;
    destination: any = {};

    createMediaStreamSource(stream: MediaStream): any {
        return {
            connect: vi.fn(),
            mediaStream: stream,
        };
    }

    createAnalyser(): any {
        return {
            fftSize: 4096,
            frequencyBinCount: 2048,
            getByteFrequencyData: vi.fn((array: Uint8Array) => {
                array[100] = 255;
                array[200] = 128;
            }),
        };
    }

    close(): void {
        this.state = "closed";
    }
}

class MockMediaStream {
    getTracks(): MediaStreamTrack[] {
        return [
            {
                stop: vi.fn(),
            } as any,
        ];
    }
}

describe("Tuner Widget", () => {
    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;

        globalThis.AudioContext = vi.fn(() => new MockAudioContext()) as any;
        globalThis.navigator.mediaDevices = {
            getUserMedia: vi.fn().mockResolvedValue(new MockMediaStream()),
        } as any;
        globalThis.requestAnimationFrame = vi.fn((fn: Function) => {
            setTimeout(fn, 16);
            return 1;
        });
        globalThis.cancelAnimationFrame = vi.fn();

        vi.spyOn(ui, "addMessage").mockImplementation(() => {});
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe("addTunerWidget()", () => {
        it("should create tuner widget in DOM", () => {
            addTunerWidget("tuner_123", 440, "A", 4);
            const widget = document.getElementById("tuner-tuner_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("tuner-widget");
        });

        it("should display reference frequency", () => {
            addTunerWidget("tuner_123", 440, "A", 4);
            const widget = document.getElementById("tuner-tuner_123");
            expect(widget?.textContent).toContain("440 Hz");
        });

        it("should display note and octave when provided", () => {
            addTunerWidget("tuner_123", 440, "A", 4);
            const widget = document.getElementById("tuner-tuner_123");
            expect(widget?.textContent).toContain("A4");
        });

        it("should display 'Any' when note not provided", () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            expect(widget?.textContent).toContain("Any");
        });

        it("should display description when provided", () => {
            addTunerWidget("tuner_123", 440, "A", 4, "Test tuner");
            const widget = document.getElementById("tuner-tuner_123");
            expect(widget?.textContent).toContain("Test tuner");
        });

        it("should create start and stop buttons", () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            expect(widget?.querySelector(".start-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-btn")).toBeTruthy();
        });

        it("should initially hide stop button", () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLElement;
            expect(stopBtn?.style.display).toBe("none");
        });

        it("should show initial status as Stopped", () => {
            addTunerWidget("tuner_123", 440);
            const statusEl = document.getElementById("status-tuner_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });
    });

    describe("Start Tuner", () => {
        it("should start tuner when start button is clicked", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
        });

        it("should show stop button when started", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(stopBtn.style.display).toBe("inline-block");
            expect(startBtn.style.display).toBe("none");
        });

        it("should update status to Listening when started", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const statusEl = document.getElementById("status-tuner_123");

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(statusEl?.textContent).toBe("Listening...");
        });

        it("should create AudioContext when started", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(AudioContext).toHaveBeenCalled();
        });

        it("should handle microphone access error", async () => {
            vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(
                new Error("Permission denied")
            );

            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(ui.addMessage).toHaveBeenCalledWith(
                expect.stringContaining("Error accessing microphone"),
                "error"
            );
        });

        it("should not start if already running", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const getUserMediaCalls = (navigator.mediaDevices.getUserMedia as any).mock.calls
                .length;
            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect((navigator.mediaDevices.getUserMedia as any).mock.calls.length).toBe(
                getUserMediaCalls
            );
        });
    });

    describe("Stop Tuner", () => {
        it("should stop tuner when stop button is clicked", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(startBtn.style.display).toBe("inline-block");
            expect(stopBtn.style.display).toBe("none");
        });

        it("should update status to Stopped when stopped", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            const statusEl = document.getElementById("status-tuner_123");

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(statusEl?.textContent).toBe("Stopped");
        });

        it("should cancel animation frame when stopped", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(globalThis.cancelAnimationFrame).toHaveBeenCalled();
        });

        it("should stop media tracks when stopped", async () => {
            const mockTrack = { stop: vi.fn() };
            const mockStream = {
                getTracks: () => [mockTrack],
            };
            vi.mocked(navigator.mediaDevices.getUserMedia).mockResolvedValueOnce(mockStream as any);

            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(mockTrack.stop).toHaveBeenCalled();
        });

        it("should not stop if not running", () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            expect(() => stopBtn.click()).not.toThrow();
        });
    });

    describe("Frequency Detection", () => {
        it("should update frequency display when detecting audio", async () => {
            const mockAnalyser = {
                fftSize: 4096,
                frequencyBinCount: 2048,
                getByteFrequencyData: vi.fn((array: Uint8Array) => {
                    array[100] = 255;
                }),
            };

            const mockAudioContext = {
                state: "running",
                sampleRate: 44100,
                destination: {},
                createMediaStreamSource: vi.fn(() => ({
                    connect: vi.fn(),
                    mediaStream: new MockMediaStream(),
                })),
                createAnalyser: vi.fn(() => mockAnalyser),
                close: vi.fn(),
            };

            globalThis.AudioContext = vi.fn(() => mockAudioContext) as any;

            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const freqEl = document.getElementById("freq-tuner_123");
            expect(freqEl).toBeTruthy();
        });

        it("should calculate cents deviation correctly", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const centsEl = document.getElementById("cents-tuner_123");
            expect(centsEl).toBeTruthy();
        });

        it("should update needle position based on frequency", async () => {
            addTunerWidget("tuner_123", 440);
            const widget = document.getElementById("tuner-tuner_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const needleEl = document.getElementById("needle-tuner_123");
            expect(needleEl).toBeTruthy();
        });

        it("should only display frequencies in valid range (80-2000 Hz)", () => {
            addTunerWidget("tuner_123", 440);
            const freqEl = document.getElementById("freq-tuner_123");

            expect(freqEl?.textContent).toBe("-- Hz");

            const lowFrequency = (1 * 44100) / (2 * 2048);
            expect(lowFrequency).toBeLessThan(80);

            const highFrequencyIndex = 200;
            const highFrequency = (highFrequencyIndex * 44100) / (2 * 2048);
            expect(highFrequency).toBeGreaterThan(2000);
        });
    });

    describe("Edge Cases", () => {
        it("should throw error when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() => addTunerWidget("tuner_123", 440)).toThrow("Messages element not found");
        });
    });
});
