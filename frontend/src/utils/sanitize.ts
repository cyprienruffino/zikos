/**
 * Shared sanitization helpers for anything rendered into the DOM.
 * All LLM- and server-supplied strings must pass through these before
 * being interpolated into HTML markup.
 */

/** Escape a value for safe interpolation into HTML markup. */
export function escapeHtml(value: unknown): string {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

const TOOL_ID_PATTERN = /^[A-Za-z0-9_-]+$/;

/** True if the id only contains characters safe for DOM id attributes. */
export function isValidToolId(id: string): boolean {
    return TOOL_ID_PATTERN.test(id);
}

/** Return the tool id when valid, otherwise a generated fallback id. */
export function sanitizeToolId(id: string | undefined, prefix: string): string {
    if (id && isValidToolId(id)) {
        return id;
    }
    return `${prefix}_${Date.now()}`;
}

/** True if the URL is an explicit http(s) URL (safe to assign to href). */
export function isSafeHttpUrl(url: string): boolean {
    return /^https?:\/\//i.test(url);
}
