export const API_URL = window.location.origin;
export const WS_URL =
    (API_URL.startsWith("https")
        ? API_URL.replace("https", "wss")
        : API_URL.replace("http", "ws")) + "/api/chat/ws";
