document.addEventListener("DOMContentLoaded", function () {
    const promptInput = document.getElementById("prompt-input");
    const sendButton = document.getElementById("send-prompt-btn");
    const chatsContainer = document.getElementById("chats-container");
    let isFirstMessage = true;
  
    // Updated function: if it's a bot message, convert newlines to <br> and add smaller text size
    function createMessageElement(text, isBot = false) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", isBot ? "bot-message" : "user-message");
  
        const messageText = document.createElement("p");
        messageText.classList.add("message-text");
        messageText.style.fontSize = isBot ? "0.85rem" : "0.9rem"; // Smaller text for bot responses
        messageText.style.lineHeight = "1.4";
  
        if (isBot) {
            // Convert newlines to <br> tags for proper formatting
            messageText.innerHTML = text.replace(/\n/g, "<br>");
            messageText.style.color = "#e0e0e0"; // Slightly lighter color for better readability
        } else {
            messageText.textContent = text;
            messageText.style.color = "#ffffff"; // Keep user messages in white
        }
  
        messageDiv.appendChild(messageText);
        return messageDiv;
    }
  
    function sendMessage() {
        const userMessage = promptInput.value.trim();
        if (userMessage === "") return;
  
        // Remove welcome message if this is the first message
        if (isFirstMessage) {
            const welcomeHeader = document.querySelector(".chat-header");
            if (welcomeHeader) {
                welcomeHeader.remove();
            }
            isFirstMessage = false;
        }
  
        // Append user message
        const userMessageElement = createMessageElement(userMessage, false);
        chatsContainer.appendChild(userMessageElement);
        promptInput.value = "";
  
        // Disable input while waiting
        promptInput.disabled = true;
        sendButton.disabled = true;
  
        // Send message to Flask server
        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userMessage }),
        })
        .then(response => response.json())
        .then(data => {
            // Create bot message element with dynamic content
            const botMessageElement = createMessageElement(data.response, true);
            chatsContainer.appendChild(botMessageElement);
        })
        .catch(() => {
            const botMessageElement = createMessageElement("Error: AI service unavailable.", true);
            chatsContainer.appendChild(botMessageElement);
        })
        .finally(() => {
            promptInput.disabled = false;
            sendButton.disabled = false;
            promptInput.focus();
            chatsContainer.scrollTop = chatsContainer.scrollHeight;
        });
    }
  
    sendButton.addEventListener("click", sendMessage);
    promptInput.addEventListener("keypress", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
});
  