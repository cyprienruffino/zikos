/**
 * MediaRecorder output helpers. Browsers record WebM/Opus (or Ogg/MP4),
 * never WAV — labeling blobs "audio/wav" produced misnamed uploads.
 */

export interface RecordingType {
    /** Empty string means "let the browser pick its default". */
    mimeType: string;
    extension: string;
}

const CANDIDATES: RecordingType[] = [
    { mimeType: "audio/webm;codecs=opus", extension: "webm" },
    { mimeType: "audio/webm", extension: "webm" },
    { mimeType: "audio/ogg;codecs=opus", extension: "ogg" },
    { mimeType: "audio/mp4", extension: "m4a" },
    { mimeType: "audio/wav", extension: "wav" },
];

/** Pick the best supported recording mime type via MediaRecorder.isTypeSupported. */
export function pickRecordingType(): RecordingType {
    if (
        typeof MediaRecorder !== "undefined" &&
        typeof MediaRecorder.isTypeSupported === "function"
    ) {
        for (const candidate of CANDIDATES) {
            if (MediaRecorder.isTypeSupported(candidate.mimeType)) {
                return candidate;
            }
        }
    }
    return { mimeType: "", extension: "webm" };
}

/** Map a (possibly codec-qualified) mime type to a filename extension. */
export function extensionForMimeType(mimeType: string): string {
    const base = mimeType.split(";")[0].trim().toLowerCase();
    switch (base) {
        case "audio/webm":
            return "webm";
        case "audio/ogg":
            return "ogg";
        case "audio/mp4":
            return "m4a";
        case "audio/mpeg":
            return "mp3";
        case "audio/wav":
        case "audio/x-wav":
            return "wav";
        default:
            return "webm";
    }
}
