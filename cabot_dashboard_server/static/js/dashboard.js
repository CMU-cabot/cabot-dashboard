let isMessageUpdateEnabled = true;
let displayedMessageIds = new Set();

const messagesDiv = document.getElementById('messages');
const cabotsDiv = document.getElementById('cabots');
const connectionStatus = document.getElementById('connection-status');

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

    try {
        const response = await fetch(url, mergedOptions);
        if (!response.ok) {
            throw new Error(`HTTP Error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        if (error.name === 'TimeoutError') {
            addMessage('接続タイムアウト: サーバーに接続できません', "timeout");
        } else {
            addMessage(`接続エラー: ${error.message}`, "error");
        }
        throw error;
    }
}

async function fetchUpdates() {
    try {
        const data = await fetchWithAuth('/receive');
        updateDashboard(data);
    } catch (error) {
        console.error('Error occurred while fetching updates:', error);
    }
}

function updateDashboard(data) {
    updateRobotList(data.robots);
    updateMessages(data.messages);
    // updateEvents(data.events);  // Implement if event updates are needed
}

function updateRobotList(robots) {
    // Use or modify existing updateCabotList function
}

function updateMessages(messages) {
    if (!isMessageUpdateEnabled || !messages || messages.length === 0) return;

    let messageList = messagesDiv.querySelector('ul');
    if (!messageList) {
        messageList = document.createElement('ul');
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

function updateEvents(events) {
    // Update event display
}

function addMessage(message, type) {
    if (!isMessageUpdateEnabled) return;
    const messageList = messagesDiv.querySelector('ul') || (() => {
        const ul = document.createElement('ul');
        messagesDiv.appendChild(ul);
        return ul;
    })();

    const messageText = typeof message === 'object' ? 
        JSON.stringify(message) : message;

    const li = document.createElement('li');
    li.className = type;
    li.textContent = `${new Date().toLocaleString()} - ${messageText}`;
    messageList.appendChild(li);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function fetchConnectedCabots() {
    try {
        const data = await fetchWithAuth('/connected_cabots');
        if (data && data.cabots) {
            updateCabotList(data.cabots);
        }
    } catch (error) {
        console.error('Error occurred while fetching Cabot list:', error);
    }
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
        
        // Status cell
        const statusCell = row.insertCell();
        statusCell.textContent = cabot.connected ? 'Connected' : 'Disconnected';
        statusCell.className = cabot.connected ? 'status-connected' : 'status-disconnected';
        
        // Action buttons cell
        const actionCell = row.insertCell();
        if (cabot.connected) {
            actionCell.innerHTML = `
                <button onclick="sendCommand('${cabot.id}', 'ros-start')">ROS Start</button>
                <button onclick="sendCommand('${cabot.id}', 'ros-stop')">ROS Stop</button>
                <button onclick="sendCommand('${cabot.id}', 'system-reboot')">Reboot</button>
                <button onclick="sendCommand('${cabot.id}', 'system-poweroff')">Power Off</button>
                <button onclick="sendCommand('${cabot.id}', 'debug1')">Debug1</button>
                <button onclick="sendCommand('${cabot.id}', 'debug2')">Debug2</button>
            `;
        } else {
            actionCell.innerHTML = '<span class="disabled">No Actions Available</span>';
        }
        
        // Last poll time cell
        const lastPollCell = row.insertCell();
        lastPollCell.textContent = formatDateTime(cabot.last_poll) || 'Unknown';
        
        // Message cell
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
    try {
        const commandData = {
            command: command,
            commandOption: {}
        };
        
        const options = {
            method: 'POST',
            body: JSON.stringify(commandData)
        };
        
        const data = await fetchWithAuth(`/send_command/${cabotId}`, options);
        console.log('Command sent:', data);
        addMessage(`Command sent: ${cabotId} - ${command}`, "status");
        
        // Update Cabot list after sending command
        await fetchConnectedCabots();
    } catch (error) {
        console.error('Error occurred while sending command:', error);
        addMessage(`Command send error: ${error.message}`, "error");
    }
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

setInterval(fetchConnectedCabots, 5000);
setInterval(fetchUpdates, 7000);