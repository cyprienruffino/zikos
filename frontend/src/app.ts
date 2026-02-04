import { addMessage } from "./ui.js";
import { connect, sendMessage, getIsProcessing } from "./websocket.js";
import { checkSystemStatus, isSetupRequired, showSetupOverlay } from "./widgets/setup.js";

const messageInput = document.getElementById("messageInput") as HTMLInputElement;
const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
const settingsBtn = document.getElementById("settingsBtn") as HTMLButtonElement;

// Check system status on startup
async function initializeApp(): Promise<void> {
    const status = await checkSystemStatus();

    if (status && isSetupRequired(status)) {
        showSetupOverlay(status);
    }

    // Connect to WebSocket regardless of model status
    // (allows viewing hardware info and recommendations)
    connect();
}

if (sendButton) {
    sendButton.addEventListener("click", () => {
        const message = messageInput?.value.trim();
        if (message) {
            addMessage(message, "user");
            if (messageInput) {
                messageInput.value = "";
            }
            if (!sendMessage(message)) {
                if (getIsProcessing()) {
                    addMessage("Please wait for the current response to complete", "error");
                } else {
                    addMessage("Not connected. Please wait for connection...", "error");
                }
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

// Settings button - show setup overlay on demand
if (settingsBtn) {
    settingsBtn.addEventListener("click", async () => {
        const status = await checkSystemStatus();
        if (status) {
            showSetupOverlay(status);
        }
    });
}

// Initialize the app
initializeApp();
