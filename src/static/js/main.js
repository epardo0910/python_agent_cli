document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    const appendMessage = (sender, text) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.textContent = text;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    const sendMessage = async () => {
        const message = userInput.value.trim();
        if (message) {
            appendMessage('user', message);
            userInput.value = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': 'b2474a8cb27f146a0c40199ff16887328735eeb4a3fa920d1998b0f2e2894da8'
                    },
                    body: JSON.stringify({ user_message: message }),
                });
                const data = await response.json();
                appendMessage('agent', data.agent_response);
            } catch (error) {
                console.error('Error sending message:', error);
                appendMessage('agent', 'Error: No se pudo conectar con el agente.');
            }
        }
    };

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
