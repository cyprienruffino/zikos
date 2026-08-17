import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    clamp,
    clampBpm,
    validateTimeSignature,
    positiveNumber,
    optionalPositiveNumber,
    validateNoteName,
    BPM_MIN,
    BPM_MAX,
} from "../../frontend/src/utils/validate.js";
import { addMetronomeWidget, getMetronome } from "../../frontend/src/widgets/metronome.js";
import { addChordProgressionWidget } from "../../frontend/src/widgets/chordProgression.js";

describe("validate helpers", () => {
    describe("clamp()", () => {
        it("should clamp to bounds", () => {
            expect(clamp(5, 0, 10)).toBe(5);
            expect(clamp(-1, 0, 10)).toBe(0);
            expect(clamp(11, 0, 10)).toBe(10);
        });
    });

    describe("clampBpm()", () => {
        it("should pass through valid bpm", () => {
            expect(clampBpm(120)).toBe(120);
        });

        it("should clamp bpm of 0 (avoids Infinity interval)", () => {
            expect(clampBpm(0)).toBe(BPM_MIN);
        });

        it("should clamp negative bpm (avoids machine-gun interval)", () => {
            expect(clampBpm(-15000)).toBe(BPM_MIN);
        });

        it("should clamp absurdly high bpm", () => {
            expect(clampBpm(99999)).toBe(BPM_MAX);
        });

        it("should fall back for NaN/non-numeric input", () => {
            expect(clampBpm("fast", 120)).toBe(120);
            expect(clampBpm(NaN, 90)).toBe(90);
            expect(clampBpm(Infinity)).toBe(BPM_MAX);
        });
    });

    describe("validateTimeSignature()", () => {
        it("should accept valid time signatures", () => {
            expect(validateTimeSignature("4/4")).toBe("4/4");
            expect(validateTimeSignature("7/8")).toBe("7/8");
            expect(validateTimeSignature("12/16")).toBe("12/16");
        });

        it("should reject junk and fall back to 4/4", () => {
            expect(validateTimeSignature("waltz")).toBe("4/4");
            expect(validateTimeSignature("4-4")).toBe("4/4");
            expect(validateTimeSignature("")).toBe("4/4");
            expect(validateTimeSignature(undefined)).toBe("4/4");
            expect(validateTimeSignature(44)).toBe("4/4");
            expect(validateTimeSignature("0/4")).toBe("4/4");
            expect(validateTimeSignature("4/0")).toBe("4/4");
            expect(validateTimeSignature("123/4")).toBe("4/4");
        });
    });

    describe("positiveNumber()", () => {
        it("should pass through positive values", () => {
            expect(positiveNumber(2.5, 1)).toBe(2.5);
        });

        it("should fall back for zero, negative, and NaN", () => {
            expect(positiveNumber(0, 7)).toBe(7);
            expect(positiveNumber(-3, 7)).toBe(7);
            expect(positiveNumber("junk", 7)).toBe(7);
        });
    });

    describe("optionalPositiveNumber()", () => {
        it("should preserve undefined", () => {
            expect(optionalPositiveNumber(undefined)).toBeUndefined();
        });

        it("should return undefined for invalid values", () => {
            expect(optionalPositiveNumber(-1)).toBeUndefined();
            expect(optionalPositiveNumber("junk")).toBeUndefined();
        });

        it("should pass through valid values", () => {
            expect(optionalPositiveNumber(30)).toBe(30);
        });
    });

    describe("validateNoteName()", () => {
        it("should accept sharp note names", () => {
            expect(validateNoteName("C#")).toBe("C#");
            expect(validateNoteName("A")).toBe("A");
        });

        it("should normalize flats to sharps", () => {
            expect(validateNoteName("Bb")).toBe("A#");
            expect(validateNoteName("Db")).toBe("C#");
        });

        it("should fall back for unknown notes instead of NaN paths", () => {
            expect(validateNoteName("H")).toBe("C");
            expect(validateNoteName("do")).toBe("C");
            expect(validateNoteName(undefined)).toBe("C");
        });
    });
});

describe("widget-level validation", () => {
    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;
        globalThis.AudioContext = vi.fn(() => ({
            state: "running",
            currentTime: 0,
            destination: {},
            resume: vi.fn(),
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
        })) as unknown as typeof AudioContext;
    });

    it("metronome widget should not throw RangeError on junk time signature", () => {
        expect(() => addMetronomeWidget("met_junk", 120, "not-a-signature")).not.toThrow();
        const widget = document.getElementById("metronome-met_junk");
        expect(widget?.querySelectorAll(".beat-dot").length).toBe(4);
    });

    it("metronome widget should clamp out-of-range bpm", () => {
        addMetronomeWidget("met_neg", -50, "4/4");
        expect(getMetronome("met_neg")?.bpm).toBe(BPM_MIN);
    });

    it("chord progression should not crash when chords list is empty", () => {
        addChordProgressionWidget("chord_empty", [], 120, "4/4", 1, "piano");
        const widget = document.getElementById("chord-chord_empty");
        const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

        expect(() => playBtn.click()).not.toThrow();
        // Should not have started playing
        expect(document.getElementById("status-chord_empty")?.textContent).toBe("Stopped");
    });
});
