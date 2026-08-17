import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    addRecordingWidget,
    removeRecordingWidget,
    setWebSocket,
    setSessionId,
    reset,
} from "../../../frontend/src/widgets/recording.js";
import * as ui from "../../../frontend/src/ui.js";

class MockBlobEvent {
    type: string;
    data: Blob;

    constructor(type: string, eventInit: { data: Blob }) {
        this.type = type;
        this.data = eventInit.data;
    }
}

globalThis.BlobEvent = MockBlobEvent as any;

class MockMediaRecorder {
    static isTypeSupported(type: string): boolean {
        return type.startsWith("audio/webm");
    }

    state: string = "inactive";
    stream: MediaStream;
    mimeType: string;
    ondataavailable: ((event: BlobEvent) => void) | null = null;
    onstop: (() => void) | null = null;
    private dataChunks: Blob[] = [];

    constructor(stream: MediaStream, options?: { mimeType?: string }) {
        this.stream = stream;
        this.mimeType = options?.mimeType || "audio/webm";
    }

    start(): void {
        this.state = "recording";
        this.dataChunks = [];
        setTimeout(() => {
            if (this.ondataavailable) {
                const blob = new Blob(["test-audio-data"], { type: "audio/wav" });
                this.ondataavailable(new MockBlobEvent("dataavailable", { data: blob }) as any);
            }
        }, 5);
    }

    stop(): void {
        if (this.state === "recording") {
            this.state = "inactive";
            if (this.onstop) {
                this.onstop();
            }
        }
    }
}

// Mock MediaStream
class MockMediaStream {
    getTracks(): MediaStreamTrack[] {
        return [
            {
                stop: vi.fn(),
            } as any,
        ];
    }
}

describe("Recording Widget", () => {
    let mockWs: any;

    beforeEach(() => {
        document.body.innerHTML = `
            <div id="messages"></div>
        `;

        mockWs = {
            readyState: 1, // WebSocket.OPEN
            send: vi.fn(),
        };

        globalThis.MediaRecorder = MockMediaRecorder as any;
        Object.defineProperty(globalThis.navigator, "mediaDevices", {
            value: {
                getUserMedia: vi.fn().mockResolvedValue(new MockMediaStream()),
            } as any,
            configurable: true,
        });
        globalThis.URL.createObjectURL = vi.fn(() => "blob:test-url");
        globalThis.URL.revokeObjectURL = vi.fn();
        globalThis.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue({ audio_file_id: "audio_123" }),
        });

        vi.spyOn(ui, "addMessage").mockImplementation(() => document.createElement("div"));
        vi.spyOn(ui, "addTypingIndicator").mockImplementation(() => {});

        setWebSocket(mockWs);
        setSessionId("test_session");
        reset();
    });

    describe("addRecordingWidget()", () => {
        it("should create recording widget in DOM", () => {
            addRecordingWidget("rec_123", "Please record audio", 60);
            const widget = document.getElementById("recording-rec_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("recording-widget");
        });

        it("should display prompt text", () => {
            addRecordingWidget("rec_123", "Test prompt", 60);
            const widget = document.getElementById("recording-rec_123");
            const promptEl = widget?.querySelector(".prompt");
            expect(promptEl?.textContent).toBe("Test prompt");
        });

        it("should create all required buttons", () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            expect(widget?.querySelector(".record-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-btn")).toBeTruthy();
            expect(widget?.querySelector(".send-btn")).toBeTruthy();
            expect(widget?.querySelector(".cancel-btn")).toBeTruthy();
        });

        it("should initially hide stop button", () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLElement;
            expect(stopBtn?.style.display).toBe("none");
        });

        it("should initially disable send button", () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;
            expect(sendBtn?.disabled).toBe(true);
        });
    });

    describe("removeRecordingWidget()", () => {
        it("should remove widget from DOM", () => {
            addRecordingWidget("rec_123", "Test", 60);
            expect(document.getElementById("recording-rec_123")).toBeTruthy();
            removeRecordingWidget("rec_123");
            expect(document.getElementById("recording-rec_123")).toBeFalsy();
        });

        it("should not throw error if widget doesn't exist", () => {
            expect(() => removeRecordingWidget("nonexistent")).not.toThrow();
        });
    });

    describe("setWebSocket()", () => {
        it("should store WebSocket instance", () => {
            const newWs = { readyState: 1, send: vi.fn() };
            setWebSocket(newWs as any);
            // Tested via behavior in other tests
        });
    });

    describe("setSessionId()", () => {
        it("should store session ID", () => {
            setSessionId("session_456");
            // Tested via behavior in other tests
        });
    });

    describe("Recording Flow", () => {
        it("should start recording when record button is clicked", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
        });

        it("should show stop button when recording starts", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(stopBtn.style.display).toBe("inline-block");
        });

        it("should update status when recording", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const statusEl = document.getElementById("status-rec_123");

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(statusEl?.textContent).toBe("Recording...");
        });

        it("should handle microphone access error", async () => {
            vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValue(
                new Error("Permission denied")
            );

            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(ui.addMessage).toHaveBeenCalledWith(
                expect.stringContaining("Error accessing microphone"),
                "error"
            );
        });
    });

    describe("Stop Recording Flow", () => {
        it("should stop recording when stop button is clicked", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            const statusEl = document.getElementById("status-rec_123");
            expect(statusEl?.textContent).toBe("Recording complete");
        });

        it("should show record button after stopping", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(recordBtn.style.display).toBe("inline-block");
            expect(stopBtn.style.display).toBe("none");
        });

        it("should handle stop when not recording", () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            expect(() => stopBtn.click()).not.toThrow();
        });
    });

    describe("Send Recording Flow", () => {
        it("should send recording when send button is clicked", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            sendBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(globalThis.fetch).toHaveBeenCalled();
            const fetchCall = (globalThis.fetch as any).mock.calls[0];
            expect(fetchCall[0]).toContain("/api/audio/upload");
            expect(fetchCall[1].method).toBe("POST");
        });

        it("should upload with the real recorder mime type and matching extension", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            sendBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const fetchCall = (globalThis.fetch as any).mock.calls[0];
            const formData = fetchCall[1].body as FormData;
            const file = formData.get("file") as File;
            expect(file.name).toBe("recording.webm");
            expect(file.type).toContain("audio/webm");
        });

        it("should show error when no audio recorded", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            sendBtn.disabled = false;
            sendBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(ui.addMessage).toHaveBeenCalledWith("No audio recorded", "error");
        });

        it("should handle upload error", async () => {
            vi.mocked(globalThis.fetch).mockResolvedValueOnce({
                ok: false,
                statusText: "Server Error",
                text: vi.fn().mockResolvedValue("Error details"),
            } as any);

            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            sendBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(ui.addMessage).toHaveBeenCalledWith(
                expect.stringContaining("Error uploading audio"),
                "error"
            );
        });

        it("should send audio_ready message when upload succeeds", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            sendBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining("audio_ready"));
            const sentMessage = JSON.parse(mockWs.send.mock.calls[0][0]);
            expect(sentMessage.type).toBe("audio_ready");
            expect(sentMessage.audio_file_id).toBe("audio_123");
        });

        it("should handle connection lost during upload", async () => {
            mockWs.readyState = 3;

            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            sendBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(ui.addMessage).toHaveBeenCalledWith(
                "Connection lost. Please reconnect and try again.",
                "error"
            );
        });
    });

    describe("Microphone Lifecycle", () => {
        it("should not acquire two streams on rapid double-click", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            recordBtn.click(); // second click before getUserMedia resolves
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);
        });

        it("should not acquire another stream while already recording", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));
            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);
        });

        it("should stop active recorder and media tracks when widget is removed", async () => {
            const mockTrack = { stop: vi.fn() };
            vi.mocked(navigator.mediaDevices.getUserMedia).mockResolvedValueOnce({
                getTracks: () => [mockTrack],
            } as any);

            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            removeRecordingWidget("rec_123");

            expect(mockTrack.stop).toHaveBeenCalled();
            expect(document.getElementById("recording-rec_123")).toBeFalsy();
        });

        it("should auto-stop recording after max_duration seconds", async () => {
            addRecordingWidget("rec_123", "Test", 0.05);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));
            const statusEl = document.getElementById("status-rec_123");
            expect(statusEl?.textContent).toBe("Recording...");

            await new Promise((resolve) => setTimeout(resolve, 80));
            expect(statusEl?.textContent).toBe("Recording complete");
        });

        it("should revoke the previous object URL when re-recording", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith("blob:test-url");
        });

        it("should revoke object URL when widget is removed", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 10));

            removeRecordingWidget("rec_123");
            expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith("blob:test-url");
        });
    });

    describe("Cancel Flow", () => {
        it("should remove widget when cancel is clicked", () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const cancelBtn = widget?.querySelector(".cancel-btn") as HTMLButtonElement;

            cancelBtn.click();

            expect(document.getElementById("recording-rec_123")).toBeFalsy();
        });

        it("should send cancel message to WebSocket", () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const cancelBtn = widget?.querySelector(".cancel-btn") as HTMLButtonElement;

            cancelBtn.click();

            expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining("cancel_recording"));
        });

        it("should stop recording when canceling during recording", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const cancelBtn = widget?.querySelector(".cancel-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            cancelBtn.click();

            expect(document.getElementById("recording-rec_123")).toBeFalsy();
        });
    });

    describe("MediaRecorder Callbacks", () => {
        it("should handle onstop callback and enable send button", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const sendBtn = widget?.querySelector(".send-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(sendBtn.disabled).toBe(false);
        });

        it("should create audio player on stop", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const playerEl = document.getElementById("player-rec_123");
            expect(playerEl?.innerHTML).toContain("<audio");
        });

        it("should update status to complete on stop", async () => {
            addRecordingWidget("rec_123", "Test", 60);
            const widget = document.getElementById("recording-rec_123");
            const recordBtn = widget?.querySelector(".record-btn") as HTMLButtonElement;
            const statusEl = document.getElementById("status-rec_123");

            recordBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;
            stopBtn.click();
            await new Promise((resolve) => setTimeout(resolve, 20));

            expect(statusEl?.textContent).toBe("Recording complete");
        });
    });
});
