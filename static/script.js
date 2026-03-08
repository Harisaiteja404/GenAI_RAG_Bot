document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    const sessionTag = document.getElementById('session-tag');
    const ragStatus = document.getElementById('rag-status');

    // Initialize or retrieve Session ID
    let sessionId = localStorage.getItem('chatSessionId');
    if (!sessionId) {
        sessionId = 'sess-' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chatSessionId', sessionId);
    }
    sessionTag.textContent = `Session: ${sessionId}`;

    const addMessage = (role, text) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const sendMessage = async () => {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to UI
        addMessage('user', message);
        userInput.value = '';
        
        // Show typing indicator
        typingIndicator.classList.remove('hidden');
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sessionId: sessionId,
                    message: message
                })
            });

            const data = await response.json();
            
            // Hide typing indicator
            typingIndicator.classList.add('hidden');

            if (!response.ok) {
                const errMsg = data.error || "An unexpected error occurred.";
                addMessage('assistant', `Error: ${errMsg}`);
                ragStatus.style.color = '#ef4444';
            } else {
                addMessage('assistant', data.reply);
                // Update status if context was found
                if (data.retrievedChunks > 0) {
                    ragStatus.textContent = "Context: Verified";
                    ragStatus.style.color = '#4ade80';
                } else {
                    ragStatus.textContent = "Context: General";
                    ragStatus.style.color = '#94a3b8';
                }
            }
        } catch (error) {
            typingIndicator.classList.add('hidden');
            addMessage('assistant', "Connection error. Please ensure the server is running.");
            console.error('Fetch error:', error);
        }
    };

    sendBtn.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    newChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
        sessionId = 'sess-' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chatSessionId', sessionId);
        sessionTag.textContent = `Session: ${sessionId}`;
        ragStatus.textContent = 'Context: Active';
        ragStatus.style.color = '#94a3b8';
        
        addMessage('assistant', "New session started. How can I help you?");
    });
});
