document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const newChatButton = document.getElementById('new-chat-btn');
    const typingIndicator = document.getElementById('typing-indicator-container');

    let conversation = [];

    const saveHistory = () => {
        sessionStorage.setItem('chatHistory', JSON.stringify(conversation));
    };

    const addCopyButtons = (messageEl) => {
        const codeBlocks = messageEl.querySelectorAll('pre');
        codeBlocks.forEach(block => {
            const btn = document.createElement('button');
            btn.classList.add('copy-btn');
            btn.innerText = 'Copiar';
            btn.addEventListener('click', () => {
                const code = block.querySelector('code').innerText;
                navigator.clipboard.writeText(code).then(() => {
                    btn.innerText = '¡Copiado!';
                    setTimeout(() => { btn.innerText = 'Copiar'; }, 2000);
                });
            });
            block.appendChild(btn);
        });
    };

    const appendMessage = (sender, text, isHtml = false) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        if (isHtml) {
            messageDiv.innerHTML = text;
        } else {
            messageDiv.textContent = text;
        }
        
        chatHistory.appendChild(messageDiv);

        if (sender === 'agent' && isHtml) {
            addCopyButtons(messageDiv);
        }

        chatHistory.scrollTop = chatHistory.scrollHeight;
        return messageDiv;
    };

    const loadHistory = () => {
        const savedHistory = sessionStorage.getItem('chatHistory');
        if (savedHistory) {
            conversation = JSON.parse(savedHistory);
            conversation.forEach(msg => {
                const isHtml = msg.sender === 'agent';
                appendMessage(msg.sender, msg.text, isHtml);
            });
        }
    };

    const sendMessage = async () => {
        const message = userInput.value.trim();
        if (message) {
            appendMessage('user', message);
            conversation.push({ sender: 'user', text: message });
            saveHistory();

            userInput.value = '';
            typingIndicator.style.display = 'block';
            chatHistory.scrollTop = chatHistory.scrollHeight;

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_message: message, history: conversation.slice(0, -1) })
                });

                typingIndicator.style.display = 'none';

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let agentResponseText = '';
                
                const agentMessageDiv = appendMessage('agent', '');

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    agentResponseText += decoder.decode(value, { stream: true });
                    // Just update the text content for live streaming effect
                    agentMessageDiv.textContent = agentResponseText;
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
                
                // Once streaming is complete, parse the full markdown content
                const finalHtml = marked.parse(agentResponseText);
                agentMessageDiv.innerHTML = finalHtml;
                addCopyButtons(agentMessageDiv);

                // Update history with the final rendered HTML
                conversation.push({ sender: 'agent', text: finalHtml });
                saveHistory();

            } catch (error) {
                console.error('Error sending message:', error);
                appendMessage('agent', 'Error: No se pudo conectar con el agente.');
                typingIndicator.style.display = 'none';
            }
        }
    };

    const startNewChat = () => {
        conversation = [];
        sessionStorage.removeItem('chatHistory');
        chatHistory.innerHTML = '';
    };

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    newChatButton.addEventListener('click', startNewChat);

    loadHistory();
});
