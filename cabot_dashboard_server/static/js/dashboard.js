let isMessageUpdateEnabled = true;
let displayedMessageIds = new Set();
let selectedCabots = new Set();
let currentAction = null;

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
    cabotsDiv.innerHTML = '<h2>Connected AI Suitcases</h2>';
    const table = document.createElement('table');
    table.innerHTML = `
        <tr>
            <th><input type="checkbox" id="select-all" onclick="toggleAllCabots(this)"></th>
            <th>ID</th>
            <th>Polling Status</th>
            <th>System Status</th>
            <th>Last Poll Time</th>
            <th>Message</th>
        </tr>
    `;
    
    cabots.forEach(cabot => {
        const row = table.insertRow();
        
        // Checkbox cell
        const checkboxCell = row.insertCell();
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'cabot-checkbox';
        checkbox.value = cabot.id;
        checkbox.checked = selectedCabots.has(cabot.id);
        checkbox.onclick = () => toggleCabot(cabot.id);
        if (!cabot.connected) {
            checkbox.disabled = true;
        }
        checkboxCell.appendChild(checkbox);

        row.insertCell().textContent = cabot.id || 'Unknown';
        
        const pollingStatusCell = row.insertCell();
        pollingStatusCell.textContent = cabot.connected ? 'Connected' : 'Disconnected';
        pollingStatusCell.className = cabot.connected ? 'status-connected' : 'status-disconnected';

        const systemStatusCell = row.insertCell();
        systemStatusCell.textContent = cabot.system_status || 'Unknown';
        systemStatusCell.className = `status-${cabot.system_status ? cabot.system_status.toLowerCase() : 'unknown'}`;
        
        const lastPollCell = row.insertCell();
        lastPollCell.textContent = formatDateTime(cabot.last_poll) || 'Unknown';
        
        row.insertCell().textContent = cabot.message || '';

        if (selectedCabots.has(cabot.id)) {
            row.classList.add('selected-row');
        }
    });
    
    cabotsDiv.appendChild(table);
    updateActionButtons();
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

function toggleCabot(cabotId) {
    if (selectedCabots.has(cabotId)) {
        selectedCabots.delete(cabotId);
    } else {
        selectedCabots.add(cabotId);
    }
    updateActionButtons();
    updateSelectedCount();
    highlightSelectedRows();
}

function toggleAllCabots(checkbox) {
    const cabotCheckboxes = document.querySelectorAll('.cabot-checkbox:not(:disabled)');
    selectedCabots.clear();
    
    if (checkbox.checked) {
        cabotCheckboxes.forEach(cb => {
            selectedCabots.add(cb.value);
        });
    }
    
    updateActionButtons();
    updateSelectedCount();
    highlightSelectedRows();
}

function updateActionButtons() {
    const hasSelection = selectedCabots.size > 0;
    document.querySelectorAll('.action-button').forEach(button => {
        button.disabled = !hasSelection;
    });
}

function updateSelectedCount() {
    document.getElementById('selected-count').textContent = selectedCabots.size;
}

function highlightSelectedRows() {
    document.querySelectorAll('tr').forEach(row => {
        const checkbox = row.querySelector('.cabot-checkbox');
        if (checkbox) {
            row.classList.toggle('selected-row', checkbox.checked);
        }
    });
}

async function executeAction(command) {
    showConfirmDialog(command);
}

async function executeActionWithConfirm() {
    if (!currentAction) return;
    
    const actionToExecute = currentAction;
    const actionButtons = document.querySelectorAll('.action-button');
    actionButtons.forEach(button => button.disabled = true);

    try {
        for (const cabotId of selectedCabots) {
            const commandData = {
                command: actionToExecute,
                commandOption: {}
            };
            
            const options = {
                method: 'POST',
                body: JSON.stringify(commandData)
            };
            
            await fetchWithAuth(`/send_command/${cabotId}`, options);
            addMessage(`Command sent: ${cabotId} - ${actionToExecute}`, "status");
        }
    } catch (error) {
        addMessage(`Error executing command: ${error.message}`, "error");
    } finally {
        updateActionButtons();
    }
}

function showConfirmDialog(command) {
    currentAction = command;
    const dialog = document.getElementById('confirmDialog');
    const dialogTitle = document.getElementById('dialogTitle');
    const robotList = document.getElementById('dialogRobotList');
    const confirmButton = document.getElementById('confirmButton');

    let actionTitle = '';
    let buttonClass = '';
    switch (command) {
        case 'ros-start':
            actionTitle = 'ROS Start';
            buttonClass = 'start';
            break;
        case 'ros-stop':
            actionTitle = 'ROS Stop';
            buttonClass = 'start';
            break;
        case 'system-reboot':
            actionTitle = 'System Reboot';
            buttonClass = 'start';
            break;
        case 'system-poweroff':
            actionTitle = 'System Power Off';
            buttonClass = 'start';
            break;
        default:
            actionTitle = 'Execute Action';
            buttonClass = 'start';
    }

    dialogTitle.textContent = actionTitle;
    confirmButton.className = `dialog-button ${buttonClass}`;

    robotList.innerHTML = '';
    selectedCabots.forEach(cabotId => {
        const div = document.createElement('div');
        div.className = 'robot-list-item';
        div.textContent = cabotId;
        robotList.appendChild(div);
    });

    confirmButton.onclick = () => {
        executeActionWithConfirm();
        closeDialog();
    };

    dialog.style.display = 'flex';

    document.addEventListener('keydown', handleEscKey);
}

function closeDialog() {
    const dialog = document.getElementById('confirmDialog');
    dialog.style.display = 'none';
    currentAction = null;
    document.removeEventListener('keydown', handleEscKey);
}

function handleEscKey(event) {
    if (event.key === 'Escape') {
        closeDialog();
    }
}

setInterval(fetchUpdates, 2000);