import { describe, it, expect, beforeEach, vi } from "vitest";
import * as ui from "../../frontend/src/ui.js";
import * as websocket from "../../frontend/src/websocket.js";

// Mock dependencies before importing app
vi.mock("../../frontend/src/ui.js");
vi.mock("../../frontend/src/websocket.js");

describe("App Module", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="status"></div>
            <div id="messages"></div>
            <input id="messageInput" />
            <button id="sendButton"></button>
        `;

        // Reset mocks
        vi.clearAllMocks();
        vi.mocked(websocket.sendMessage).mockReturnValue(true);
        vi.mocked(websocket.getIsProcessing).mockReturnValue(false);
        vi.mocked(websocket.connect).mockImplementation(() => {});

        // Re-import app to set up event listeners
        vi.resetModules();
    });

    describe("Send Button Click", () => {
        it("should send message when button is clicked with valid input", async () => {
            await import("../../frontend/src/app.js");
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;

            messageInput.value = "Hello, world!";
            sendButton.click();

            expect(websocket.sendMessage).toHaveBeenCalledWith("Hello, world!");
            expect(ui.addMessage).toHaveBeenCalledWith("Hello, world!", "user");
            expect(messageInput.value).toBe("");
        });

        it("should not send empty messages", async () => {
            await import("../../frontend/src/app.js");
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;

            messageInput.value = "   ";
            sendButton.click();

            expect(websocket.sendMessage).not.toHaveBeenCalled();
        });

        it("should trim message before sending", async () => {
            await import("../../frontend/src/app.js");
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;

            messageInput.value = "  Hello  ";
            sendButton.click();

            expect(websocket.sendMessage).toHaveBeenCalledWith("Hello");
        });

        it("should show error when processing", async () => {
            vi.mocked(websocket.getIsProcessing).mockReturnValue(true);
            vi.mocked(websocket.sendMessage).mockReturnValue(false);

            await import("../../frontend/src/app.js");
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;

            messageInput.value = "Test message";
            sendButton.click();

            expect(ui.addMessage).toHaveBeenCalledWith(
                "Please wait for the current response to complete",
                "error"
            );
        });

        it("should show error when not connected", async () => {
            vi.mocked(websocket.getIsProcessing).mockReturnValue(false);
            vi.mocked(websocket.sendMessage).mockReturnValue(false);

            await import("../../frontend/src/app.js");
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;

            messageInput.value = "Test message";
            sendButton.click();

            expect(ui.addMessage).toHaveBeenCalledWith(
                "Not connected. Please wait for connection...",
                "error"
            );
        });
    });

    describe("Enter Key Press", () => {
        it("should send message when Enter is pressed", async () => {
            await import("../../frontend/src/app.js");
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const clickSpy = vi.spyOn(sendButton, "click");

            messageInput.value = "Test message";
            const event = new KeyboardEvent("keypress", { key: "Enter" });
            messageInput.dispatchEvent(event);

            expect(clickSpy).toHaveBeenCalled();
        });

        it("should not send message for other keys", async () => {
            await import("../../frontend/src/app.js");
            const messageInput = document.getElementById("messageInput") as HTMLInputElement;
            const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
            const clickSpy = vi.spyOn(sendButton, "click");

            messageInput.value = "Test message";
            const event = new KeyboardEvent("keypress", { key: "a" });
            messageInput.dispatchEvent(event);

            expect(clickSpy).not.toHaveBeenCalled();
        });
    });

    describe("Initialization", () => {
        it("should call connect on module load", async () => {
            vi.resetModules();
            await import("../../frontend/src/app.js");
            expect(websocket.connect).toHaveBeenCalled();
        });
    });
});
