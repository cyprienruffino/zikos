import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    escapeHtml,
    isValidToolId,
    sanitizeToolId,
    isSafeHttpUrl,
} from "../../frontend/src/utils/sanitize.js";
import { addRecordingWidget } from "../../frontend/src/widgets/recording.js";
import { addMetronomeWidget } from "../../frontend/src/widgets/metronome.js";
import { addTunerWidget } from "../../frontend/src/widgets/tuner.js";
import { addChordProgressionWidget } from "../../frontend/src/widgets/chordProgression.js";
import { addTempoTrainerWidget } from "../../frontend/src/widgets/tempoTrainer.js";
import { addEarTrainerWidget } from "../../frontend/src/widgets/earTrainer.js";
import { addPracticeTimerWidget } from "../../frontend/src/widgets/practiceTimer.js";

const XSS = '<img src=x onerror="window.__pwned = true">';

describe("sanitize helpers", () => {
    describe("escapeHtml()", () => {
        it("should escape HTML special characters", () => {
            expect(escapeHtml('<script>"a" & \'b\'</script>')).toBe(
                "&lt;script&gt;&quot;a&quot; &amp; &#39;b&#39;&lt;/script&gt;"
            );
        });

        it("should stringify non-string values", () => {
            expect(escapeHtml(120)).toBe("120");
            expect(escapeHtml(undefined)).toBe("undefined");
        });
    });

    describe("isValidToolId()", () => {
        it("should accept alphanumeric ids with dashes and underscores", () => {
            expect(isValidToolId("rec_123-abc")).toBe(true);
        });

        it("should reject ids with markup or spaces", () => {
            expect(isValidToolId('a"><img>')).toBe(false);
            expect(isValidToolId("a b")).toBe(false);
            expect(isValidToolId("")).toBe(false);
        });
    });

    describe("sanitizeToolId()", () => {
        it("should keep valid ids", () => {
            expect(sanitizeToolId("tool_1", "rec")).toBe("tool_1");
        });

        it("should generate a fallback for invalid ids", () => {
            const id = sanitizeToolId('"><script>', "rec");
            expect(id).toMatch(/^rec_\d+$/);
        });

        it("should generate a fallback for missing ids", () => {
            expect(sanitizeToolId(undefined, "met")).toMatch(/^met_\d+$/);
        });
    });

    describe("isSafeHttpUrl()", () => {
        it("should accept http and https URLs", () => {
            expect(isSafeHttpUrl("https://example.com/x")).toBe(true);
            expect(isSafeHttpUrl("http://example.com")).toBe(true);
        });

        it("should reject javascript: and data: URLs", () => {
            expect(isSafeHttpUrl("javascript:alert(1)")).toBe(false);
            expect(isSafeHttpUrl("data:text/html,<script>")).toBe(false);
            expect(isSafeHttpUrl("//example.com")).toBe(false);
        });
    });
});

describe("widget XSS escaping", () => {
    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;
        globalThis.AudioContext = vi.fn(() => ({})) as unknown as typeof AudioContext;
        delete (window as unknown as Record<string, unknown>).__pwned;
    });

    function expectNoInjectedImg(): void {
        const messages = document.getElementById("messages") as HTMLElement;
        expect(messages.querySelector("img")).toBeNull();
        expect((window as unknown as Record<string, unknown>).__pwned).toBeUndefined();
    }

    it("recording widget escapes the prompt", () => {
        addRecordingWidget("rec_1", XSS, 60);
        expectNoInjectedImg();
        expect(document.querySelector(".prompt")?.textContent).toBe(XSS);
    });

    it("recording widget rejects malicious tool ids", () => {
        addRecordingWidget('"><img src=x onerror=alert(1)>', "prompt", 60);
        expectNoInjectedImg();
    });

    it("metronome widget escapes the description", () => {
        addMetronomeWidget("met_1", 120, "4/4", XSS);
        expectNoInjectedImg();
    });

    it("tuner widget escapes description and note", () => {
        addTunerWidget("tuner_1", 440, XSS, 4, XSS);
        expectNoInjectedImg();
    });

    it("chord progression widget escapes chord names and description", () => {
        addChordProgressionWidget("chord_1", [XSS, "F"], 120, "4/4", 1, "piano", XSS);
        expectNoInjectedImg();
        expect(document.querySelector(".chord-box")?.textContent).toBe(XSS);
    });

    it("tempo trainer widget escapes the description", () => {
        addTempoTrainerWidget("tempo_1", 60, 120, 5, "4/4", "linear", XSS);
        expectNoInjectedImg();
    });

    it("ear trainer widget escapes the description", () => {
        addEarTrainerWidget("ear_1", "intervals", "easy", "C", XSS);
        expectNoInjectedImg();
    });

    it("practice timer widget escapes goal and description", () => {
        addPracticeTimerWidget("timer_1", 30, XSS, 5, XSS);
        expectNoInjectedImg();
    });
});
