import { describe, it, expect } from "vitest";
import { API_URL, WS_URL } from "../../frontend/src/config.js";

describe("Config", () => {
    describe("API_URL", () => {
        it("should use window.location.origin", () => {
            expect(API_URL).toBe(window.location.origin);
        });
    });

    describe("WS_URL", () => {
        it("should append /api/chat/ws to API_URL", () => {
            expect(WS_URL).toContain("/api/chat/ws");
        });

        it("should convert https protocol to wss", () => {
            if (window.location.origin.startsWith("https")) {
                expect(WS_URL).toMatch(/^wss:\/\//);
            }
        });

        it("should convert http protocol to ws", () => {
            if (window.location.origin.startsWith("http://")) {
                expect(WS_URL).toMatch(/^ws:\/\//);
            }
        });

        it("should have correct format", () => {
            const expectedPattern = /^(ws|wss):\/\/.+\/api\/chat\/ws$/;
            expect(WS_URL).toMatch(expectedPattern);
        });
    });
});
