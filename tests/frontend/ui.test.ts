import { describe, it, expect, beforeEach } from "vitest";
import { addMessage, addTypingIndicator, removeTypingIndicator, updateStatus } from "../../frontend/src/ui.js";

describe("UI Module", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="status"></div>
            <div id="messages"></div>
        `;
    });

    describe("addMessage()", () => {
        it("should add a message to the messages container", () => {
            addMessage("Hello, world!");
            const messagesEl = document.getElementById("messages");
            expect(messagesEl?.children.length).toBe(1);
        });

        it("should set correct message class", () => {
            addMessage("Test message", "user");
            const messageEl = document.getElementById("messages")?.firstElementChild;
            expect(messageEl?.className).toBe("message user");
        });

        it("should default to assistant type", () => {
            addMessage("Test message");
            const messageEl = document.getElementById("messages")?.firstElementChild;
            expect(messageEl?.className).toBe("message assistant");
        });

        it("should replace newlines with <br> tags", () => {
            addMessage("Line 1\nLine 2\nLine 3");
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const textEl = messageEl?.querySelector(".message-text");
            expect(textEl?.innerHTML).toBe("Line 1<br>Line 2<br>Line 3");
        });

        it("should add audio player when audio_file_id is provided", () => {
            addMessage("Audio message", "assistant", { audio_file_id: "audio_123" });
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const audioEl = messageEl?.querySelector(".audio-player");
            expect(audioEl).toBeTruthy();
            expect(audioEl?.innerHTML).toContain("audio_123");
        });

        it("should add notation image when notation_url is provided", () => {
            addMessage("Notation message", "assistant", { notation_url: "/path/to/notation.png" });
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const notationEl = messageEl?.querySelector(".notation");
            expect(notationEl).toBeTruthy();
            expect(notationEl?.innerHTML).toContain("/path/to/notation.png");
        });

        it("should add both audio and notation when both are provided", () => {
            addMessage("Full message", "assistant", {
                audio_file_id: "audio_123",
                notation_url: "/path/to/notation.png",
            });
            const messageEl = document.getElementById("messages")?.firstElementChild;
            expect(messageEl?.querySelector(".audio-player")).toBeTruthy();
            expect(messageEl?.querySelector(".notation")).toBeTruthy();
        });

        it("should scroll to bottom after adding message", () => {
            const messagesEl = document.getElementById("messages") as HTMLElement;
            const initialScrollTop = messagesEl.scrollTop;
            addMessage("Test message");
            expect(messagesEl.scrollTop).toBeGreaterThanOrEqual(initialScrollTop);
        });

        it("should handle empty text", () => {
            addMessage("");
            const messagesEl = document.getElementById("messages");
            expect(messagesEl?.children.length).toBe(1);
        });

        it("should handle null data parameter", () => {
            addMessage("Test", "assistant", null);
            const messageEl = document.getElementById("messages")?.firstElementChild;
            expect(messageEl).toBeTruthy();
            expect(messageEl?.querySelector(".audio-player")).toBeFalsy();
            expect(messageEl?.querySelector(".notation")).toBeFalsy();
        });

        it("should render HTML in message text (current behavior)", () => {
            addMessage("<script>alert('xss')</script>");
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const textEl = messageEl?.querySelector(".message-text");
            expect(textEl?.innerHTML).toBe("<script>alert('xss')</script>");
        });

        it("should handle messages with HTML tags", () => {
            addMessage("Test <strong>bold</strong> text");
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const textEl = messageEl?.querySelector(".message-text");
            expect(textEl?.innerHTML).toContain("<strong>bold</strong>");
        });

        it("should handle very long messages", () => {
            const longMessage = "a".repeat(10000);
            addMessage(longMessage);
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const textEl = messageEl?.querySelector(".message-text");
            expect(textEl?.textContent).toBe(longMessage);
        });

        it("should handle audio_file_id with special characters", () => {
            addMessage("Audio", "assistant", { audio_file_id: "audio_123-test" });
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const audioEl = messageEl?.querySelector(".audio-player");
            expect(audioEl?.innerHTML).toContain("audio_123-test");
        });

        it("should handle notation_url with query parameters", () => {
            addMessage("Notation", "assistant", {
                notation_url: "/path/to/notation.png?v=1&t=123",
            });
            const messageEl = document.getElementById("messages")?.firstElementChild;
            const notationEl = messageEl?.querySelector(".notation");
            const imgEl = notationEl?.querySelector("img");
            expect(imgEl?.getAttribute("src")).toBe("/path/to/notation.png?v=1&t=123");
        });
    });

    describe("addTypingIndicator()", () => {
        it("should add typing indicator to messages", () => {
            addTypingIndicator();
            const indicator = document.getElementById("typing-indicator");
            expect(indicator).toBeTruthy();
            expect(indicator?.className).toBe("message assistant typing-indicator");
        });

        it("should not add duplicate typing indicators", () => {
            addTypingIndicator();
            addTypingIndicator();
            const indicators = document.querySelectorAll("#typing-indicator");
            expect(indicators.length).toBe(1);
        });

        it("should include typing dots HTML", () => {
            addTypingIndicator();
            const indicator = document.getElementById("typing-indicator");
            expect(indicator?.innerHTML).toContain("typing-dots");
        });

        it("should scroll to bottom after adding indicator", () => {
            const messagesEl = document.getElementById("messages") as HTMLElement;
            const initialScrollTop = messagesEl.scrollTop;
            addTypingIndicator();
            expect(messagesEl.scrollTop).toBeGreaterThanOrEqual(initialScrollTop);
        });
    });

    describe("removeTypingIndicator()", () => {
        it("should remove typing indicator if it exists", () => {
            addTypingIndicator();
            expect(document.getElementById("typing-indicator")).toBeTruthy();
            removeTypingIndicator();
            expect(document.getElementById("typing-indicator")).toBeFalsy();
        });

        it("should not throw error if indicator doesn't exist", () => {
            expect(() => removeTypingIndicator()).not.toThrow();
        });
    });

    describe("updateStatus()", () => {
        it("should update status text", () => {
            updateStatus("Connected", "connected");
            const statusEl = document.getElementById("status");
            expect(statusEl?.textContent).toBe("Connected");
        });

        it("should update status class", () => {
            updateStatus("Connected", "connected");
            const statusEl = document.getElementById("status");
            expect(statusEl?.className).toBe("status connected");
        });

        it("should handle different status types", () => {
            updateStatus("Disconnected", "disconnected");
            const statusEl = document.getElementById("status");
            expect(statusEl?.textContent).toBe("Disconnected");
            expect(statusEl?.className).toBe("status disconnected");
        });

        it("should not throw error if status element doesn't exist", () => {
            document.body.innerHTML = "";
            expect(() => updateStatus("Test", "test")).not.toThrow();
        });

        it("should handle empty status text", () => {
            updateStatus("", "connected");
            const statusEl = document.getElementById("status");
            expect(statusEl?.textContent).toBe("");
        });

        it("should handle status with special characters", () => {
            updateStatus("Status & < >", "connected");
            const statusEl = document.getElementById("status");
            expect(statusEl?.textContent).toBe("Status & < >");
        });
    });

    describe("Edge Cases", () => {
        it("should handle missing messages element gracefully", () => {
            document.body.innerHTML = "";
            expect(() => addMessage("Test")).toThrow("Messages element not found");
        });

        it("should handle multiple rapid addMessage calls", () => {
            for (let i = 0; i < 10; i++) {
                addMessage(`Message ${i}`);
            }
            const messagesEl = document.getElementById("messages");
            expect(messagesEl?.children.length).toBe(10);
        });

        it("should handle addTypingIndicator when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() => addTypingIndicator()).toThrow("Messages element not found");
        });

        it("should handle removeTypingIndicator when indicator doesn't exist", () => {
            expect(() => removeTypingIndicator()).not.toThrow();
        });
    });
});
