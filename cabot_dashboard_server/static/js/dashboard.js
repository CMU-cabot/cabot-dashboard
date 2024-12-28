let isMessageUpdateEnabled = true;
let displayedMessageIds = new Set();
let selectedCabots = new Set();
let currentAction = null;
let ws;

const messagesDiv = document.getElementById('messages');
const cabotsDiv = document.getElementById('cabots');

const PLACEHOLDER_TEXT = '+ Click here to set Docker image name';

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        addMessage('WebSocket connection established', 'status');
        requestRefresh();
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    };
    
    ws.onclose = () => {
        addMessage('WebSocket connection closed. Attempting to reconnect...', 'error');
        setTimeout(initWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        addMessage('WebSocket connection error: ' + error.message, 'error');
    };
}

function requestRefresh() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'refresh' }));
    }
}

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
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'command',
            cabotId: cabotId,
            data: commandData
        }));
        addMessage(`Command sent: ${cabotId} - ${command}`, "status");
    } else {
        addMessage('WebSocket connection is not established', 'error');
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

async function refreshTags(repository) {
    const versionItem = document.getElementById(`${repository}-checkbox`).closest('.version-item');
    const button = versionItem.querySelector('.refresh-btn');
    const errorDiv = versionItem.querySelector('.error-message');
    const select = versionItem.querySelector('select');
    const lastUpdated = versionItem.querySelector('.last-updated');

    try {
        button.disabled = true;
        button.querySelector('i').classList.add('fa-spin');
        errorDiv.textContent = '';

        const response = await fetch(`/api/refresh-tags/${repository}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            select.innerHTML = '';
            
            data.tags.forEach(tag => {
                const option = document.createElement('option');
                option.value = tag;
                option.textContent = tag;
                select.appendChild(option);
            });
            
            lastUpdated.textContent = `Last updated: ${new Date().toISOString()}`;
            errorDiv.textContent = '';
        } else {
            errorDiv.textContent = data.message || 'Failed to refresh tags.';
        }
    } catch (error) {
        console.error('Failed to refresh tags:', error);
        errorDiv.textContent = 'An error occurred while refreshing tags.';
    } finally {
        button.disabled = false;
        button.querySelector('i').classList.remove('fa-spin');
    }
}

function startEdit(element, repository) {
    const container = element.closest('.version-name-container');
    const textElement = container.querySelector('.version-name-text');
    const inputElement = container.querySelector('.version-name-input');
    
    const currentText = textElement.textContent.trim();
    inputElement.value = currentText === PLACEHOLDER_TEXT ? '' : currentText;
    
    textElement.style.display = 'none';
    inputElement.style.display = 'block';
    
    inputElement.focus();
    
    if (inputElement.value) {
        inputElement.select();
    }
}

async function updateImageName(repository, newName) {
    try {
        const response = await fetch(`/api/update-image-name/${repository}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify({
                name: newName
            })
        });
        
        let data;
        try {
            data = await response.json();
        } catch (e) {
            console.error('Failed to parse response:', e);
            throw new Error('Invalid server response');
        }
        
        if (!response.ok || data.status === 'error') {
            throw new Error(data?.message || 'Failed to save image name');
        }
        
        return true;
    } catch (error) {
        console.error('Failed to update image name:', error);
        const errorDiv = document.getElementById(`${repository}-error`);
        errorDiv.textContent = error.message || 'Failed to update image name';
        return false;
    }
}

function updateImageControls(imageId, hasName) {
    const checkbox = document.getElementById(`${imageId}-checkbox`);
    const select = document.getElementById(`${imageId}-version`);
    const refreshBtn = checkbox.closest('.version-item').querySelector('.refresh-btn');
    const deleteBtn = checkbox.closest('.version-item').querySelector('.delete-btn');
    const editBtn = checkbox.closest('.version-item').querySelector('.edit-btn');
    const nameText = checkbox.closest('.version-item').querySelector('.version-name-text');

    checkbox.disabled = !hasName;
    select.disabled = !hasName;
    refreshBtn.disabled = !hasName;
    deleteBtn.style.display = hasName ? 'block' : 'none';
    editBtn.style.display = hasName ? 'block' : 'none';
    
    if (!hasName) {
        nameText.textContent = PLACEHOLDER_TEXT;
        nameText.classList.add('empty-name');
        checkbox.checked = false;
    } else {
        nameText.classList.remove('empty-name');
    }
    
    updateUpdateButton();
}

function deleteImageName(imageId) {
    const versionItem = document.getElementById(`${imageId}-checkbox`).closest('.version-item');
    const nameText = versionItem.querySelector('.version-name-text');
    const nameInput = versionItem.querySelector('.version-name-input');
    const errorDiv = versionItem.querySelector('.error-message');

    errorDiv.textContent = '';

    fetch(`/api/update-image-name/${imageId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
        },
        body: JSON.stringify({
            name: '',
            delete: true
        })
    })
    .then(async response => {
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data?.message || 'Failed to delete image name');
        }
        
        nameText.textContent = PLACEHOLDER_TEXT;
        nameText.classList.add('empty-name');
        nameInput.value = '';
        updateImageControls(imageId, false);
    })
    .catch(error => {
        console.error('Error deleting image name:', error);
        errorDiv.textContent = error.message || 'Failed to delete image name';
    });
}

function finishEdit(input, shouldSave = true) {
    const container = input.closest('.version-name-container');
    const textElement = container.querySelector('.version-name-text');
    const errorDiv = container.closest('.version-item').querySelector('.error-message');
    const newName = input.value.trim();
    const repository = input.dataset.original;
    
    errorDiv.textContent = '';
    
    if (!shouldSave || newName === '') {
        const originalText = textElement.textContent.trim();
        input.value = originalText === PLACEHOLDER_TEXT ? '' : originalText;
        textElement.style.display = 'block';
        input.style.display = 'none';
        return;
    }

    updateImageName(repository, newName)
        .then(success => {
            if (success) {
                textElement.textContent = newName;
                textElement.classList.remove('empty-name');
                updateImageControls(repository, true);
            } else {
                const originalText = textElement.textContent.trim();
                input.value = originalText === PLACEHOLDER_TEXT ? '' : originalText;
            }
        })
        .finally(() => {
            textElement.style.display = 'block';
            input.style.display = 'none';
        });
}

function updateUpdateButton() {
    const checkedBoxes = document.querySelectorAll('.version-checkbox:checked');
    const updateButton = document.querySelector('.update-software-btn');
    updateButton.disabled = checkedBoxes.length === 0;
}

function initializeImageNameHandlers() {
    document.querySelectorAll('.version-name-text').forEach(textElement => {
        textElement.addEventListener('click', function() {
            const container = this.closest('.version-name-container');
            const input = container.querySelector('.version-name-input');
            startEdit(this, input.dataset.original);
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    
    document.querySelectorAll('.version-name-input').forEach(input => {
        input.addEventListener('blur', () => finishEdit(input, true));

        input.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                finishEdit(input, true);
            }
        });

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                finishEdit(input, false);
            }
        });
    });

    document.querySelectorAll('.version-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateUpdateButton);
    });

    initializeImageNameHandlers();

    updateUpdateButton();
});

// Initialize WebSocket connection when the page loads
document.addEventListener('DOMContentLoaded', initWebSocket);

setInterval(requestRefresh, 5000);