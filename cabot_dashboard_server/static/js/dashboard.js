let isMessageUpdateEnabled = true;
let displayedMessageIds = new Set();

const messagesDiv = document.getElementById('messages');
const cabotsDiv = document.getElementById('cabots');

async function fetchWithAuth(url, options = {}) {
    const defaultOptions = {
        headers: {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        },
        timeout: 5000
    };

    const mergedOptions = { 
        ...defaultOptions, 
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };

    const response = await fetch(url, mergedOptions);
    if (!response.ok) {
        throw new Error(`HTTP Error! Status: ${response.status}`);
    }
    return await response.json();
}

async function fetchUpdates() {
    const data = await fetchWithAuth('/receive');
    updateDashboard(data);
}

function updateDashboard(data) {
    messagesDiv.style.display = debugMode ? 'block' : 'none';
    if (data.cabots) {
        updateCabotList(data.cabots);
    }
    if (data.messages) {
        updateMessages(data.messages);
    }
}

function updateMessages(messages) {
    if (!isMessageUpdateEnabled || !messages || messages.length === 0) return;

    let messageList = messagesDiv.querySelector('ul') || document.createElement('ul');
    if (!messagesDiv.contains(messageList)) {
        messagesDiv.appendChild(messageList);
    }

    messages.forEach(message => {
        const messageId = `${message.timestamp}-${message.client_id}`;
        
        if (!displayedMessageIds.has(messageId)) {
            const messageText = typeof message.message === 'object' ? 
                JSON.stringify(message.message) : message.message;

            const li = document.createElement('li');
            li.setAttribute('data-message-id', messageId);
            li.textContent = `${new Date(message.timestamp).toLocaleString()} - ${message.client_id}: ${messageText}`;
            messageList.appendChild(li);
            
            displayedMessageIds.add(messageId);
        }
    });

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addMessage(message, type) {
    if (!isMessageUpdateEnabled) return;
    const messageList = messagesDiv.querySelector('ul') || document.createElement('ul');
    if (!messagesDiv.contains(messageList)) {
        messagesDiv.appendChild(messageList);
    }

    const messageText = typeof message === 'object' ? 
        JSON.stringify(message) : message;

    const li = document.createElement('li');
    li.className = type;
    li.textContent = `${new Date().toLocaleString()} - ${messageText}`;
    messageList.appendChild(li);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateCabotList(cabots) {
    cabotsDiv.innerHTML = '<h2>Connected Cabots</h2>';
    const table = document.createElement('table');
    table.innerHTML = `
        <tr>
            <th>Cabot ID</th>
            <th>Status</th>
            <th>Actions</th>
            <th>Last Poll Time</th>
            <th>Message</th>
        </tr>
    `;
    
    cabots.forEach(cabot => {
        const row = table.insertRow();
        row.insertCell().textContent = cabot.id || 'Unknown';
        
        const statusCell = row.insertCell();
        statusCell.textContent = cabot.connected ? 'Connected' : 'Disconnected';
        statusCell.className = cabot.connected ? 'status-connected' : 'status-disconnected';
        
        const actionCell = row.insertCell();
        if (cabot.connected) {
            actionCell.innerHTML = `
                <button onclick="sendCommand('${cabot.id}', 'ros-start')" ${cabot.processing ? 'disabled' : ''}>ROS Start</button>
                <button onclick="sendCommand('${cabot.id}', 'ros-stop')" ${cabot.processing ? 'disabled' : ''}>ROS Stop</button>
                <button onclick="sendCommand('${cabot.id}', 'system-reboot')" ${cabot.processing ? 'disabled' : ''}>Reboot</button>
                <button onclick="sendCommand('${cabot.id}', 'system-poweroff')" ${cabot.processing ? 'disabled' : ''}>Power Off</button>
                ${debugMode ? `
                    <button onclick="sendCommand('${cabot.id}', 'debug1')" ${cabot.processing ? 'disabled' : ''}>Debug1</button>
                    <button onclick="sendCommand('${cabot.id}', 'debug2')" ${cabot.processing ? 'disabled' : ''}>Debug2</button>
                ` : ''}
            `;
        } else {
            actionCell.innerHTML = '<span class="disabled">No Actions Available</span>';
        }
        
        const lastPollCell = row.insertCell();
        lastPollCell.textContent = formatDateTime(cabot.last_poll) || 'Unknown';
        
        row.insertCell().textContent = cabot.message || '';
    });
    
    cabotsDiv.appendChild(table);
}

function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'Unknown';
    const date = new Date(dateTimeString);
    return date.toLocaleString();
}

async function sendCommand(cabotId, command) {
    const actionButtons = document.querySelectorAll(`button[onclick*="'${cabotId}'"]`);
    actionButtons.forEach(button => {
        button.disabled = true;
    });

    const commandData = {
        command: command,
        commandOption: {}
    };
    
    const options = {
        method: 'POST',
        body: JSON.stringify(commandData)
    };
    
    await fetchWithAuth(`/send_command/${cabotId}`, options);
    addMessage(`Command sent: ${cabotId} - ${command}`, "status");
}

function clearMessages() {
    const messageList = messagesDiv.querySelector('ul');
    if (messageList) {
        messageList.innerHTML = '';
        displayedMessageIds.clear();
    }
}

function toggleMessages() {
    isMessageUpdateEnabled = !isMessageUpdateEnabled;
    const toggleBtn = document.getElementById('toggleMessagesBtn');
    toggleBtn.textContent = isMessageUpdateEnabled ? 'Stop Messages' : 'Resume Messages';
    toggleBtn.classList.toggle('button-disabled', !isMessageUpdateEnabled);
}

setInterval(fetchUpdates, 2000);