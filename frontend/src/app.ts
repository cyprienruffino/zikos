import { addMessage } from "./ui.js";
import { connect, sendMessage, getIsProcessing } from "./websocket.js";

const messageInput = document.getElementById("messageInput") as HTMLInputElement;
const sendButton = document.getElementById("sendButton") as HTMLButtonElement;

if (sendButton) {
    sendButton.addEventListener("click", () => {
        const message = messageInput?.value.trim();
        if (message) {
            if (sendMessage(message)) {
                addMessage(message, "user");
                if (messageInput) {
                    messageInput.value = "";
                }
            } else if (getIsProcessing()) {
                addMessage("Please wait for the current response to complete", "error");
            } else {
                addMessage("Not connected. Please wait for connection...", "error");
            }
        }
    });
}

if (messageInput) {
    messageInput.addEventListener("keypress", (e: KeyboardEvent) => {
        if (e.key === "Enter") {
            sendButton?.click();
        }
    });
}

connect();
