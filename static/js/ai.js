document.addEventListener("DOMContentLoaded", function () {

    console.log("AI.JS FINAL VERSION LOADED");

    const aiAssistant = document.getElementById("aiAssistant");

    if (!aiAssistant) {
        console.error("AI Assistant container not found.");
        return;
    }

    const chatBox = aiAssistant.querySelector(".chat-box");
    const input = aiAssistant.querySelector(".chat-input input");
    const sendButton = aiAssistant.querySelector(".chat-input button");

    if (!chatBox || !input || !sendButton) {
        console.error("AI chat elements are missing.");
        return;
    }


    // =========================
    // Application Context
    // =========================

    function getApplicationContext() {

        const context = {
            page: window.location.pathname,
            page_name: aiAssistant.dataset.page || "AI Assistant",
            user_role: aiAssistant.dataset.userRole || "unknown",
            current_url: window.location.href
        };


        // Dashboard statistics
        const statCards = document.querySelectorAll(".stat-card");

        if (statCards.length > 0) {

            const dashboardStats = {};

            statCards.forEach(function (card) {

                const titleElement = card.querySelector("h3");
                const valueElement = card.querySelector("h2, .stat-value");

                if (!titleElement || !valueElement) {
                    return;
                }

                const title = titleElement.textContent
                    .trim()
                    .toLowerCase()
                    .replace(/\s+/g, "_");

                const value = valueElement.textContent.trim();

                dashboardStats[title] = value;
            });

            context.dashboard_stats = dashboardStats;
        }


        // Delivery status filter
        const statusFilter = document.getElementById("statusFilter");

        if (statusFilter) {
            context.delivery_status_filter = statusFilter.value;
        }


        // Delivery search
        const deliverySearch =
            document.getElementById("deliverySearch");

        if (deliverySearch) {
            context.delivery_search = deliverySearch.value.trim();
        }


        return context;
    }


    // =========================
    // HTML Protection
    // =========================

    function escapeHtml(value) {

        const div = document.createElement("div");

        div.textContent = value;

        return div.innerHTML;
    }


    // =========================
    // Add User Message
    // =========================

    function addUserMessage(message) {

        const messageElement = document.createElement("div");

        messageElement.className =
            "chat-message user-message";

        messageElement.innerHTML = `
            <div class="message-content">
                <strong>You</strong>
                <p>${escapeHtml(message)}</p>
            </div>
        `;

        chatBox.appendChild(messageElement);

        scrollToBottom();
    }


    // =========================
    // Add AI Message
    // =========================

    function addAIMessage(message) {

        const messageElement = document.createElement("div");

        messageElement.className =
            "chat-message ai-message";

        messageElement.innerHTML = `
            <div class="message-icon">🤖</div>

            <div class="message-content">
                <strong>AI Assistant</strong>
                <p>${escapeHtml(message)}</p>
            </div>
        `;

        chatBox.appendChild(messageElement);

        scrollToBottom();
    }


    // =========================
    // Loading Message
    // =========================

    function addLoadingMessage() {

        const messageElement = document.createElement("div");

        messageElement.className =
            "chat-message ai-message";

        messageElement.id = "aiLoadingMessage";

        messageElement.innerHTML = `
            <div class="message-icon">🤖</div>

            <div class="message-content">
                <strong>AI Assistant</strong>
                <p>Thinking...</p>
            </div>
        `;

        chatBox.appendChild(messageElement);

        scrollToBottom();
    }


    // =========================
    // Remove Loading Message
    // =========================

    function removeLoadingMessage() {

        const loadingMessage =
            document.getElementById("aiLoadingMessage");

        if (loadingMessage) {
            loadingMessage.remove();
        }
    }


    // =========================
    // Scroll Chat
    // =========================

    function scrollToBottom() {

        chatBox.scrollTop = chatBox.scrollHeight;
    }


    // =========================
    // Send Message
    // =========================

    async function sendMessage() {

        const message = input.value.trim();

        if (!message) {
            return;
        }


        // Disable input while processing
        input.disabled = true;
        sendButton.disabled = true;


        addUserMessage(message);

        input.value = "";

        addLoadingMessage();


        try {

            const context =
                getApplicationContext();

            console.log(
                "AI APPLICATION CONTEXT:",
                context
            );


            const formData =
                new URLSearchParams();

            formData.append(
                "message",
                message
            );

            formData.append(
                "context",
                JSON.stringify(context)
            );


            // =========================
            // CSRF Token
            // =========================

            const csrfToken =
                document.querySelector(
                    "[name=csrfmiddlewaretoken]"
                );


            const headers = {
                "X-Requested-With": "XMLHttpRequest"
            };


            if (csrfToken) {

                headers["X-CSRFToken"] =
                    csrfToken.value;
            }


            // =========================
            // Fetch AI
            // =========================

            const response = await fetch(
                "/ai/",
                {
                    method: "POST",
                    headers: headers,
                    body: formData
                }
            );


            console.log(
                "AI STATUS:",
                response.status
            );


            let data;

            try {

                data = await response.json();

            } catch (jsonError) {

                throw new Error(
                    "Invalid response from AI server."
                );
            }


            console.log(
                "AI RESPONSE:",
                data
            );


            removeLoadingMessage();


            if (!response.ok) {

                addAIMessage(
                    data.reply ||
                    "Something went wrong. Please try again."
                );

                return;
            }


            if (data.success) {

                addAIMessage(
                    data.reply ||
                    "I received your request."
                );

            } else {

                addAIMessage(
                    data.reply ||
                    "Something went wrong. Please try again."
                );
            }


        } catch (error) {

            console.error(
                "AI REQUEST ERROR:",
                error
            );

            removeLoadingMessage();

            addAIMessage(
                "Unable to connect to the AI Assistant. Please try again."
            );

        } finally {

            input.disabled = false;
            sendButton.disabled = false;

            input.focus();
        }
    }


    // =========================
    // Send Button
    // =========================

    sendButton.addEventListener(
        "click",
        sendMessage
    );


    // =========================
    // Enter Key
    // =========================

    input.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter"
                && !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();
            }
        }
    );


    console.log(
        "AI Assistant frontend initialized successfully."
    );

});