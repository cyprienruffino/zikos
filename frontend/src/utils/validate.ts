/**
 * Validation/clamping helpers for LLM-supplied tool-call arguments.
 * Widgets must never receive unvalidated numbers or format strings.
 */

export const BPM_MIN = 20;
export const BPM_MAX = 400;

export function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
}

/** Coerce to a finite number, clamped to the playable BPM range. */
export function clampBpm(value: unknown, fallback: number = 120): number {
    const n = typeof value === "number" ? value : Number(value);
    if (Number.isNaN(n)) {
        return clamp(fallback, BPM_MIN, BPM_MAX);
    }
    return clamp(n, BPM_MIN, BPM_MAX);
}

const TIME_SIGNATURE_PATTERN = /^\d{1,2}\/\d{1,2}$/;

/** Validate a "beats/division" time signature; junk falls back to 4/4. */
export function validateTimeSignature(value: unknown, fallback: string = "4/4"): string {
    if (typeof value !== "string" || !TIME_SIGNATURE_PATTERN.test(value)) {
        return fallback;
    }
    const [beats, division] = value.split("/").map(Number);
    if (beats < 1 || division < 1) {
        return fallback;
    }
    return value;
}

/** Coerce to a finite positive number, otherwise return the fallback. */
export function positiveNumber(value: unknown, fallback: number): number {
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n) || n <= 0) {
        return fallback;
    }
    return n;
}

/** Like positiveNumber but preserves "not provided" as undefined. */
export function optionalPositiveNumber(value: unknown): number | undefined {
    if (value === undefined || value === null) {
        return undefined;
    }
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n) || n <= 0) {
        return undefined;
    }
    return n;
}

/** Enharmonic flats normalized to the sharp names used by the audio tables. */
const FLAT_TO_SHARP: Record<string, string> = {
    Db: "C#",
    Eb: "D#",
    Fb: "E",
    Gb: "F#",
    Ab: "G#",
    Bb: "A#",
    Cb: "B",
};

const NOTE_NAMES = new Set(["C", "C#", "D", "D#", "E", "E#", "F", "F#", "G", "G#", "A", "A#", "B", "B#"]);

/** Whitelist note names; flats are normalized, unknown values fall back. */
export function validateNoteName(value: unknown, fallback: string = "C"): string {
    if (typeof value !== "string") {
        return fallback;
    }
    const normalized = value.trim();
    if (normalized in FLAT_TO_SHARP) {
        return FLAT_TO_SHARP[normalized];
    }
    if (NOTE_NAMES.has(normalized)) {
        return normalized === "E#" ? "F" : normalized === "B#" ? "C" : normalized;
    }
    return fallback;
}
