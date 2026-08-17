import { describe, it, expect, afterEach, vi } from "vitest";
import { pickRecordingType, extensionForMimeType } from "../../frontend/src/utils/media.js";

describe("media helpers", () => {
    const originalMediaRecorder = globalThis.MediaRecorder;

    afterEach(() => {
        globalThis.MediaRecorder = originalMediaRecorder;
        vi.restoreAllMocks();
    });

    describe("pickRecordingType()", () => {
        it("should pick webm/opus when supported", () => {
            globalThis.MediaRecorder = {
                isTypeSupported: vi.fn((type: string) => type.startsWith("audio/webm")),
            } as unknown as typeof MediaRecorder;

            const picked = pickRecordingType();
            expect(picked.mimeType).toBe("audio/webm;codecs=opus");
            expect(picked.extension).toBe("webm");
        });

        it("should fall back to mp4 when webm/ogg unsupported (Safari)", () => {
            globalThis.MediaRecorder = {
                isTypeSupported: vi.fn((type: string) => type === "audio/mp4"),
            } as unknown as typeof MediaRecorder;

            const picked = pickRecordingType();
            expect(picked.mimeType).toBe("audio/mp4");
            expect(picked.extension).toBe("m4a");
        });

        it("should return browser-default type when isTypeSupported is missing", () => {
            globalThis.MediaRecorder = {} as unknown as typeof MediaRecorder;
            const picked = pickRecordingType();
            expect(picked.mimeType).toBe("");
            expect(picked.extension).toBe("webm");
        });
    });

    describe("extensionForMimeType()", () => {
        it("should strip codec parameters", () => {
            expect(extensionForMimeType("audio/webm;codecs=opus")).toBe("webm");
            expect(extensionForMimeType("audio/ogg;codecs=opus")).toBe("ogg");
        });

        it("should map known types", () => {
            expect(extensionForMimeType("audio/mp4")).toBe("m4a");
            expect(extensionForMimeType("audio/wav")).toBe("wav");
            expect(extensionForMimeType("audio/mpeg")).toBe("mp3");
        });

        it("should default to webm for unknown types", () => {
            expect(extensionForMimeType("application/octet-stream")).toBe("webm");
        });
    });
});
