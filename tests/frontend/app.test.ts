import { describe, it, expect, beforeEach, vi } from "vitest";
import * as websocket from "../../frontend/src/websocket.js";

// Mock websocket (needs real WebSocket) and setup (makes HTTP calls).
// Let ui.js run real — assert on DOM state instead of mock calls.
vi.mock("../../frontend/src/websocket.js");
vi.mock("../../frontend/src/widgets/setup.js", () => ({
    checkSystemStatus: vi.fn().mockResolvedValue(null),
    isSetupRequired: vi.fn().mockReturnValue(false),
    showSetupOverlay: vi.fn(),
}));

describe("App Module", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="status"></div>
            <div id="messages"></div>
            <input id="messageInput" />
            <button id="sendButton"></button>
            <button id="settingsBtn"></button>
        `;

        vi.clearAllMocks();
        vi.mocked(websocket.sendMessage).mockReturnValue(true);
        vi.mocked(websocket.getIsProcessing).mockReturnValue(false);
        vi.mocked(websocket.connect).mockImplementation(() => {});
        vi.resetModules();
    });

    describe("Send Button Click", () => {
        it("should add user message to DOM and send via websocket", async () => {
            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;
            const messages = document.getElementById("messages")!;

            input.value = "Hello, world!";
            document.getElementById("sendButton")!.click();

            // Real ui.addMessage should have created a DOM element
            const userMessages = messages.querySelectorAll(".message.user");
            expect(userMessages.length).toBe(1);
            expect(userMessages[0].textContent).toContain("Hello, world!");

            // Websocket should have received the message
            expect(websocket.sendMessage).toHaveBeenCalledWith("Hello, world!");

            // Input should be cleared
            expect(input.value).toBe("");
        });

        it("should not send empty messages", async () => {
            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;
            const messages = document.getElementById("messages")!;

            input.value = "   ";
            document.getElementById("sendButton")!.click();

            expect(messages.querySelectorAll(".message").length).toBe(0);
            expect(websocket.sendMessage).not.toHaveBeenCalled();
        });

        it("should trim message before sending", async () => {
            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;
            const messages = document.getElementById("messages")!;

            input.value = "  Hello  ";
            document.getElementById("sendButton")!.click();

            expect(websocket.sendMessage).toHaveBeenCalledWith("Hello");
            expect(messages.querySelector(".message.user")!.textContent).toContain("Hello");
        });

        it("should show error, remove bubble, and restore input when processing", async () => {
            vi.mocked(websocket.getIsProcessing).mockReturnValue(true);
            vi.mocked(websocket.sendMessage).mockReturnValue(false);

            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;
            const messages = document.getElementById("messages")!;

            input.value = "Test message";
            document.getElementById("sendButton")!.click();

            const errorMessages = messages.querySelectorAll(".message.error");
            expect(errorMessages.length).toBe(1);
            expect(errorMessages[0].textContent).toContain("Please wait");
            // The failed user bubble must not remain
            expect(messages.querySelectorAll(".message.user").length).toBe(0);
            // The input is restored so the user can retry
            expect(input.value).toBe("Test message");
        });

        it("should show error, remove bubble, and restore input when not connected", async () => {
            vi.mocked(websocket.getIsProcessing).mockReturnValue(false);
            vi.mocked(websocket.sendMessage).mockReturnValue(false);

            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;
            const messages = document.getElementById("messages")!;

            input.value = "Test message";
            document.getElementById("sendButton")!.click();

            const errorMessages = messages.querySelectorAll(".message.error");
            expect(errorMessages.length).toBe(1);
            expect(errorMessages[0].textContent).toContain("Not connected");
            expect(messages.querySelectorAll(".message.user").length).toBe(0);
            expect(input.value).toBe("Test message");
        });
    });

    describe("Enter Key", () => {
        it("should send message on Enter keydown", async () => {
            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;
            const messages = document.getElementById("messages")!;

            input.value = "Test message";
            input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

            expect(messages.querySelectorAll(".message.user").length).toBe(1);
            expect(websocket.sendMessage).toHaveBeenCalledWith("Test message");
        });

        it("should not send message for other keys", async () => {
            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;

            input.value = "Test message";
            input.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));

            expect(websocket.sendMessage).not.toHaveBeenCalled();
        });

        it("should not send while composing with an IME", async () => {
            await import("../../frontend/src/app.js");
            const input = document.getElementById("messageInput") as HTMLInputElement;

            input.value = "Test message";
            input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", isComposing: true }));

            expect(websocket.sendMessage).not.toHaveBeenCalled();
        });
    });

    describe("Initialization", () => {
        it("should call connect on module load", async () => {
            vi.resetModules();
            await import("../../frontend/src/app.js");
            await vi.waitFor(() => {
                expect(websocket.connect).toHaveBeenCalled();
            });
        });
    });
});
