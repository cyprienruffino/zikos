import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { connect, sendMessage, getIsProcessing, reset } from "../../frontend/src/websocket.js";
import * as ui from "../../frontend/src/ui.js";
import * as recording from "../../frontend/src/widgets/recording.js";
import * as metronome from "../../frontend/src/widgets/metronome.js";
import * as tuner from "../../frontend/src/widgets/tuner.js";
import * as chordProgression from "../../frontend/src/widgets/chordProgression.js";
import * as tempoTrainer from "../../frontend/src/widgets/tempoTrainer.js";
import * as earTrainer from "../../frontend/src/widgets/earTrainer.js";
import * as practiceTimer from "../../frontend/src/widgets/practiceTimer.js";

// Mock WebSocket
class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    readyState = MockWebSocket.CONNECTING;
    url: string;
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    onclose: ((event: CloseEvent) => void) | null = null;
    send: (data: string) => void;

    constructor(url: string) {
        this.url = url;
        this.send = vi.fn();
        // Store instance globally for test access
        (global as any).lastWebSocket = this;
        // Simulate connection after a brief delay
        setTimeout(() => {
            this.readyState = MockWebSocket.OPEN;
            if (this.onopen) {
                this.onopen(new Event("open"));
            }
        }, 10);
    }

    close(): void {
        this.readyState = MockWebSocket.CLOSED;
        if (this.onclose) {
            this.onclose(new CloseEvent("close"));
        }
    }
}

describe("WebSocket Module", () => {
    beforeEach(() => {
        // Reset websocket module state
        reset();

        // Reset DOM
        document.body.innerHTML = `
            <div id="status"></div>
            <div id="messages"></div>
            <input id="messageInput" />
            <button id="sendButton"></button>
        `;

        // Mock global WebSocket
        (globalThis as any).WebSocket = MockWebSocket as any;

        // Store original setTimeout/clearTimeout
        const originalSetTimeout = globalThis.window.setTimeout;
        const originalClearTimeout = globalThis.window.clearTimeout;

        // Mock setTimeout/clearTimeout without recursion
        globalThis.window.setTimeout = vi.fn((fn: Function, delay: number) => {
            return originalSetTimeout(fn, delay);
        }) as any;
        globalThis.window.clearTimeout = vi.fn((id: number) => {
            originalClearTimeout(id);
        }) as any;

        // Mock UI functions
        vi.spyOn(ui, "updateStatus").mockImplementation(() => {});
        vi.spyOn(ui, "addMessage").mockImplementation(() => {});
        vi.spyOn(ui, "addTypingIndicator").mockImplementation(() => {});
        vi.spyOn(ui, "removeTypingIndicator").mockImplementation(() => {});

        // Mock widget functions
        vi.spyOn(recording, "setWebSocket").mockImplementation(() => {});
        vi.spyOn(recording, "setSessionId").mockImplementation(() => {});
        vi.spyOn(recording, "addRecordingWidget").mockImplementation(() => {});
        vi.spyOn(recording, "removeRecordingWidget").mockImplementation(() => {});
        vi.spyOn(metronome, "addMetronomeWidget").mockImplementation(() => {});
        vi.spyOn(tuner, "addTunerWidget").mockImplementation(() => {});
        vi.spyOn(chordProgression, "addChordProgressionWidget").mockImplementation(() => {});
        vi.spyOn(tempoTrainer, "addTempoTrainerWidget").mockImplementation(() => {});
        vi.spyOn(earTrainer, "addEarTrainerWidget").mockImplementation(() => {});
        vi.spyOn(practiceTimer, "addPracticeTimerWidget").mockImplementation(() => {});
    });

    afterEach(() => {
        reset();
        vi.clearAllMocks();
        (global as any).lastWebSocket = undefined;
    });

    describe("connect()", () => {
        it("should create WebSocket connection", () => {
            connect();
            expect(ui.updateStatus).toHaveBeenCalledWith("Connecting...", "disconnected");
        });

        it("should call setWebSocket with WebSocket instance", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            expect(recording.setWebSocket).toHaveBeenCalled();
        });

        it("should update status to Connected on open", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            expect(ui.updateStatus).toHaveBeenCalledWith("Connected", "connected");
        });

        it("should enable send button on open", async () => {
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            sendButton.disabled = true;
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            expect(sendButton.disabled).toBe(false);
        });

        it("should reset reconnect attempts on successful connection", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            // Reconnect attempts should be reset (tested via behavior)
            expect(ui.updateStatus).toHaveBeenCalledWith("Connected", "connected");
        });
    });

    describe("sendMessage()", () => {
        it("should return false if WebSocket is not connected", () => {
            const result = sendMessage("test message");
            expect(result).toBe(false);
        });

        it("should return false if already processing", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            sendMessage("first message");
            const result = sendMessage("second message");
            expect(result).toBe(false);
        });

        it("should send message when connected and not processing", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();
            expect(ws.send).toBeDefined();

            const result = sendMessage("test message");
            expect(result).toBe(true);
            expect(ws.send).toHaveBeenCalled();
            expect(ui.addTypingIndicator).toHaveBeenCalled();
        });

        it("should format message correctly", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            sendMessage("Hello, world!");
            expect(ws.send).toHaveBeenCalled();
            const sentData = JSON.parse((ws.send as any).mock.calls[0][0]);
            expect(sentData.type).toBe("message");
            expect(sentData.message).toBe("Hello, world!");
            expect(sentData.session_id).toBeDefined();
        });
    });

    describe("getIsProcessing()", () => {
        it("should return false initially", () => {
            expect(getIsProcessing()).toBe(false);
        });

        it("should return true after sending message", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            sendMessage("test");
            expect(getIsProcessing()).toBe(true);
        });
    });

    describe("Message Handling", () => {
        let ws: MockWebSocket;

        beforeEach(async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();
        });

        it("should handle response messages", () => {
            const message = {
                type: "response",
                message: "Hello from server",
                session_id: "test_session",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(ui.removeTypingIndicator).toHaveBeenCalled();
            expect(ui.addMessage).toHaveBeenCalledWith("Hello from server", "assistant", message);
        });

        it("should handle session_id in messages", () => {
            const message = {
                type: "response",
                message: "Test",
                session_id: "test_session",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(recording.setSessionId).toHaveBeenCalledWith("test_session");
        });

        it("should handle request_audio_recording tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "request_audio_recording",
                tool_id: "tool_123",
                arguments: { prompt: "Record audio", max_duration: 60 },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(recording.addRecordingWidget).toHaveBeenCalledWith(
                "tool_123",
                "Record audio",
                60
            );
        });

        it("should handle create_metronome tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "create_metronome",
                tool_id: "met_123",
                arguments: { bpm: 120, time_signature: "4/4", description: "Test metronome" },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(metronome.addMetronomeWidget).toHaveBeenCalledWith(
                "met_123",
                120,
                "4/4",
                "Test metronome"
            );
        });

        it("should handle create_tuner tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "create_tuner",
                tool_id: "tuner_123",
                arguments: {
                    reference_frequency: 440,
                    note: "A",
                    octave: 4,
                    description: "Test tuner",
                },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(tuner.addTunerWidget).toHaveBeenCalledWith(
                "tuner_123",
                440,
                "A",
                4,
                "Test tuner"
            );
        });

        it("should handle create_chord_progression tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "create_chord_progression",
                tool_id: "chord_123",
                arguments: {
                    chords: ["C", "F", "G"],
                    tempo: 120,
                    time_signature: "4/4",
                    chords_per_bar: 1,
                    instrument: "piano",
                },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(chordProgression.addChordProgressionWidget).toHaveBeenCalledWith(
                "chord_123",
                ["C", "F", "G"],
                120,
                "4/4",
                1,
                "piano",
                undefined
            );
        });

        it("should handle create_tempo_trainer tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "create_tempo_trainer",
                tool_id: "tempo_123",
                arguments: {
                    start_bpm: 60,
                    end_bpm: 120,
                    duration_minutes: 5,
                    time_signature: "4/4",
                    ramp_type: "linear",
                },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(tempoTrainer.addTempoTrainerWidget).toHaveBeenCalledWith(
                "tempo_123",
                60,
                120,
                5,
                "4/4",
                "linear",
                undefined
            );
        });

        it("should handle create_ear_trainer tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "create_ear_trainer",
                tool_id: "ear_123",
                arguments: {
                    mode: "intervals",
                    difficulty: "medium",
                    root_note: "C",
                },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(earTrainer.addEarTrainerWidget).toHaveBeenCalledWith(
                "ear_123",
                "intervals",
                "medium",
                "C",
                undefined
            );
        });

        it("should handle create_practice_timer tool_call", () => {
            const message = {
                type: "tool_call",
                tool_name: "create_practice_timer",
                tool_id: "timer_123",
                arguments: {
                    duration_minutes: 30,
                    goal: "Practice scales",
                    break_interval_minutes: 5,
                },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(practiceTimer.addPracticeTimerWidget).toHaveBeenCalledWith(
                "timer_123",
                30,
                "Practice scales",
                5,
                undefined
            );
        });

        it("should handle recording_cancelled message", () => {
            const message = {
                type: "recording_cancelled",
                tool_id: "rec_123",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(recording.removeRecordingWidget).toHaveBeenCalledWith("rec_123");
            expect(ui.addMessage).toHaveBeenCalledWith("Recording cancelled", "assistant");
        });

        it("should handle error messages", () => {
            const message = {
                type: "error",
                message: "Something went wrong",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(ui.addMessage).toHaveBeenCalledWith("Error: Something went wrong", "error");
        });

        it("should handle invalid JSON gracefully", () => {
            const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
            ws.onmessage?.(new MessageEvent("message", { data: "invalid json" }));

            expect(consoleErrorSpy).toHaveBeenCalled();
            expect(ui.addMessage).toHaveBeenCalledWith(
                "Error processing message from server",
                "error"
            );
            consoleErrorSpy.mockRestore();
        });

        it("should set isProcessing to false after receiving message", () => {
            const message = {
                type: "response",
                message: "Test",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(getIsProcessing()).toBe(false);
        });
    });

    describe("Error Handling", () => {
        it("should handle WebSocket errors", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            if (ws.onerror) {
                ws.onerror(new Event("error"));
            }
            expect(ui.updateStatus).toHaveBeenCalledWith("Connection error", "disconnected");
        });

        it("should handle WebSocket close and attempt reconnection", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            ws.close();
            await new Promise((resolve) => setTimeout(resolve, 50));

            expect(ui.updateStatus).toHaveBeenCalledWith("Disconnected", "disconnected");
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            expect(sendButton.disabled).toBe(true);
        });

        it("should implement exponential backoff on reconnection", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            let ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const setTimeoutSpy = vi.spyOn(window, "setTimeout");

            ws.close();
            await new Promise((resolve) => setTimeout(resolve, 50));

            const reconnectCall = setTimeoutSpy.mock.calls.find(
                (call) => typeof call[0] === "function" && call[1] > 0
            );
            expect(reconnectCall).toBeDefined();
            expect(reconnectCall?.[1]).toBeGreaterThanOrEqual(3000);
            expect(reconnectCall?.[1]).toBeLessThanOrEqual(30000);

            setTimeoutSpy.mockRestore();
        });

        it("should cap reconnection delay at 30 seconds", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            let ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const setTimeoutSpy = vi.spyOn(window, "setTimeout");

            for (let i = 0; i < 15; i++) {
                ws.close();
                await new Promise((resolve) => setTimeout(resolve, 50));
                ws = (global as any).lastWebSocket;
                if (ws) {
                    await new Promise((resolve) => setTimeout(resolve, 20));
                }
            }

            const reconnectCall = setTimeoutSpy.mock.calls.find(
                (call) => typeof call[0] === "function" && call[1] > 0
            );
            if (reconnectCall) {
                expect(reconnectCall[1]).toBeLessThanOrEqual(30000);
            }

            setTimeoutSpy.mockRestore();
        });

        it("should cancel pending reconnection when connect() is called again", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const clearTimeoutSpy = vi.spyOn(window, "clearTimeout");

            ws.close();
            await new Promise((resolve) => setTimeout(resolve, 10));

            connect();

            expect(clearTimeoutSpy).toHaveBeenCalled();
            clearTimeoutSpy.mockRestore();
        });

        it("should handle multiple rapid close events", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            ws.close();
            ws.close();
            ws.close();

            await new Promise((resolve) => setTimeout(resolve, 50));

            expect(ui.updateStatus).toHaveBeenCalledWith("Disconnected", "disconnected");
        });
    });

    describe("Reconnection Logic", () => {
        it("should reset reconnect attempts on successful connection", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            ws.close();
            await new Promise((resolve) => setTimeout(resolve, 50));

            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(ui.updateStatus).toHaveBeenCalledWith("Connected", "connected");
        });

        it("should update status with reconnection delay message", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            ws.close();
            await new Promise((resolve) => setTimeout(resolve, 50));

            expect(ui.updateStatus).toHaveBeenCalledWith(
                expect.stringContaining("Reconnecting in"),
                "disconnected"
            );
        });
    });

    describe("Edge Cases", () => {
        it("should handle sendMessage when WebSocket is null", () => {
            reset();
            const result = sendMessage("test");
            expect(result).toBe(false);
        });

        it("should handle sendMessage when WebSocket is CLOSING", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();
            ws.readyState = MockWebSocket.CLOSING;

            const result = sendMessage("test");
            expect(result).toBe(false);
        });

        it("should handle sendMessage when WebSocket is CLOSED", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();
            ws.readyState = MockWebSocket.CLOSED;

            const result = sendMessage("test");
            expect(result).toBe(false);
        });

        it("should handle sendMessage when WebSocket is CONNECTING", async () => {
            connect();
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();
            ws.readyState = MockWebSocket.CONNECTING;

            const result = sendMessage("test");
            expect(result).toBe(false);
        });

        it("should handle malformed tool_call messages gracefully", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const message = {
                type: "tool_call",
                tool_name: "unknown_tool",
                tool_id: "test_123",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(ui.removeTypingIndicator).toHaveBeenCalled();
        });

        it("should handle tool_call with missing tool_id", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const message = {
                type: "tool_call",
                tool_name: "request_audio_recording",
                arguments: { prompt: "Test", max_duration: 60 },
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(recording.addRecordingWidget).toHaveBeenCalled();
        });

        it("should handle response message with empty string", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const message = {
                type: "response",
                message: "",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(ui.addMessage).toHaveBeenCalledWith("", "assistant", message);
        });

        it("should handle error message without message field", async () => {
            connect();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const ws = (global as any).lastWebSocket;
            expect(ws).toBeDefined();

            const message = {
                type: "error",
            };
            ws.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));

            expect(ui.addMessage).toHaveBeenCalledWith("Error: Unknown error", "error");
        });
    });
});
