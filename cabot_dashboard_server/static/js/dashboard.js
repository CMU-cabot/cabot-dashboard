// WebSocket connection
let ws = null;
let isConnected = false;
let selectedRobots = new Set();
let currentFilter = 'all';
let robotStateManager = null;
let totalRobots = 0;
let reconnectAttempts = 0;
let connectionTimeout = null;
const MAX_RECONNECT_ATTEMPTS = 3;
const CONNECTION_TIMEOUT_MS = 10000; // 10 seconds

// Dialog related variables
let currentAction = null;
const PLACEHOLDER_TEXT = '+ Click here to set Docker image name';

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing dashboard...');
    
    // Initialize RobotStateManager first
    if (window.RobotStateManager) {
        robotStateManager = new window.RobotStateManager();
    }

    // Initialize UI elements
    initializeUI();

    // Initialize WebSocket with a delay to ensure all components are ready
    console.log('Scheduling WebSocket initialization...');
    setTimeout(() => {
        console.log('Starting WebSocket initialization...');
        initWebSocket();
    }, 1000);
});

// Initialize UI elements
function initializeUI() {
    console.log('Initializing UI elements...');
    
    // Add select all handler
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            toggleAllRobots(e.target.checked);
        });
    }

    // Add event listener for view history buttons
    document.addEventListener('click', (e) => {
        if (e.target.closest('.view-history-btn')) {
            const button = e.target.closest('.view-history-btn');
            const robotId = button.dataset.robotId;
            const messages = JSON.parse(button.dataset.messages);
            showLogDialog(robotId, messages);
        }
    });

    // Add dialog event handlers
    const confirmButton = document.getElementById('confirmAction');
    const cancelButton = document.getElementById('cancelAction');
    const dialog = document.getElementById('confirmDialog');
    const dialogOverlay = document.getElementById('dialogOverlay');

    if (confirmButton) {
        confirmButton.addEventListener('click', executeAction);
    }

    if (cancelButton) {
        cancelButton.addEventListener('click', closeDialog);
    }

    // Add escape key handler for dialog
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && dialog && dialog.style.display === 'block') {
            closeDialog();
        }
    });

    // Add click outside dialog handler
    if (dialogOverlay) {
        dialogOverlay.addEventListener('click', (event) => {
            if (event.target === dialogOverlay) {
                closeDialog();
            }
        });
    }

    // Initialize Docker Hub version items
    initializeDockerVersions();
    addEnvRow()
}

// Initialize WebSocket connection
function initWebSocket() {
    console.log('Initializing WebSocket connection...');
    
    // Get JWT token from cookie
    const token = getCookie('session_token');
    if (!token) {
        console.error('No authentication token found in cookies');
        // Wait a bit before redirecting, in case the cookie is not yet set
        setTimeout(() => {
            if (!getCookie('session_token')) {
                console.error('Still no token found after delay, redirecting to login');
                redirectToLogin();
            }
        }, 2000);
        return;
    }

    // Clear any existing connection timeout
    if (connectionTimeout) {
        clearTimeout(connectionTimeout);
    }

    // Set new connection timeout
    connectionTimeout = setTimeout(() => {
        if (!isConnected) {
            console.error('Connection timeout reached');
            handleConnectionFailure();
        }
    }, CONNECTION_TIMEOUT_MS);

    // Close existing connection if any
    if (ws) {
        console.log('Closing existing WebSocket connection...');
        try {
            ws.close();
            ws = null;
        } catch (error) {
            console.error('Error closing existing connection:', error);
        }
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws?token=${token}`;
    
    try {
        console.log('Creating new WebSocket connection...');
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('WebSocket connection established successfully');
            clearTimeout(connectionTimeout);
            connectionTimeout = null;
            isConnected = true;
            reconnectAttempts = 0;
            updateConnectionStatus();
            // Request initial state
            console.log('Requesting initial state...');
            ws.send(JSON.stringify({ type: 'refresh' }));
        };
        
        ws.onclose = (event) => {
            console.log(`WebSocket connection closed with code: ${event.code}`);
            isConnected = false;
            updateConnectionStatus();
            
            if (event.code === 4001) {
                console.error('WebSocket authentication failed');
                handleConnectionFailure();
                return;
            }
            
            handleConnectionFailure();
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error occurred:', error);
            isConnected = false;
            updateConnectionStatus();
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Received WebSocket message of type:', data.type);

                switch (data.type) {
                    case 'robot_state':
                        if (data.cabots) {
                            updateDashboard(data);
                        }
                        if (data.messages) {
                            updateMessageList(data.messages);
                        }
                        break;
                    case 'refresh_tags_response':
                        handleTagsResponse(data);
                        break;
                    case 'update_image_name_response':
                        handleImageNameResponse(data);
                        break;
                    case 'update_software_response':
                        handleSoftwareUpdateResponse(data);
                        break;
                    case 'refresh_site_response':
                        handleSiteResponse(data);
                        break;
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };
    } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        isConnected = false;
        updateConnectionStatus();
        handleConnectionFailure();
    }
}

// Handle connection failure
function handleConnectionFailure() {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        console.log(`Scheduling reconnect attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
        setTimeout(() => {
            if (!isConnected) {
                console.log('Attempting to reconnect...');
                initWebSocket();
            }
        }, 5000);
    } else {
        console.error('Max reconnection attempts reached');
        if (!isConnected) {
            redirectToLogin();
        }
    }
}

// Helper function to redirect to login
function redirectToLogin() {
    // Check if we're not already on the login page to prevent redirect loops
    if (!window.location.pathname.includes('/login')) {
        console.log('Redirecting to login page...');
        window.location.href = '/login';
    }
}

// Helper function to get cookie value
function getCookie(name) {
    try {
        console.log('Getting cookie:', name);
        console.log('All cookies:', document.cookie);
        
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        
        console.log('Cookie parts:', parts.length);
        
        if (parts.length === 2) {
            const token = parts.pop().split(';').shift();
            console.log('Found token:', token.substring(0, 10) + '...');
            return token;
        }
        
        // Try alternative method
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [cookieName, cookieValue] = cookie.split('=').map(c => c.trim());
            if (cookieName === name) {
                console.log('Found token (alternative method):', cookieValue.substring(0, 10) + '...');
                return cookieValue;
            }
        }
        
        console.warn('Token not found in cookies');
        return null;
    } catch (error) {
        console.error('Error getting cookie:', error);
        return null;
    }
}

// Update connection status display
function updateConnectionStatus() {
    const statusBadge = document.querySelector('.navbar .badge');
    const actionButtons = document.querySelectorAll('.btn-success, .btn-warning, .btn-primary, .btn-danger, .btn-info');
    const updateSoftwareBtn = document.querySelector('.btn[onclick="updateSoftware()"]');
    
    if (isConnected) {
        statusBadge.classList.remove('bg-danger');
        statusBadge.classList.add('bg-success');
        statusBadge.textContent = 'Connected';
        
        // Enable all action buttons
        actionButtons.forEach(btn => {
            btn.disabled = false;
        });
        if (updateSoftwareBtn) {
            updateSoftwareBtn.disabled = false;
        }
    } else {
        statusBadge.classList.remove('bg-success');
        statusBadge.classList.add('bg-danger');
        statusBadge.textContent = 'Disconnected';
        
        // Disable all action buttons
        actionButtons.forEach(btn => {
            btn.disabled = true;
        });
        if (updateSoftwareBtn) {
            updateSoftwareBtn.disabled = true;
        }
    }
}

// Show confirmation dialog
function showConfirmDialog(command) {
    const dialog = document.getElementById('confirmDialog');
    const selectedRobotsList = document.getElementById('selectedRobots');
    const confirmButton = document.getElementById('confirmAction');
    const dialogTitle = document.getElementById('dialogTitle');
    const dialogOverlay = document.getElementById('dialogOverlay');
    
    if (!dialog || !selectedRobotsList || !confirmButton || !dialogTitle || !dialogOverlay) {
        console.error('Dialog elements not found');
        return;
    }
    
    // Get only enabled robots
    const enabledRobots = Array.from(selectedRobots).filter(robotId => {
        const checkbox = document.querySelector(`.robot-checkbox[value="${robotId}"]`);
        return checkbox && !checkbox.disabled;
    });

    if (enabledRobots.length === 0) {
        const actionError = document.getElementById('actionError');
        if (actionError) {
            actionError.textContent = 'No enabled robots selected.';
            actionError.style.display = 'block';
        }
        return;
    }
    
    // Update dialog content
    selectedRobotsList.innerHTML = enabledRobots
        .map(robotId => `<li>${robotId}</li>`)
        .join('');
    
    // Set current action
    currentAction = command;
    
    // Update dialog title and button
    dialogTitle.textContent = `Confirm ${command}`;
    confirmButton.textContent = `Execute ${command}`;
    
    // Show overlay and dialog
    dialogOverlay.style.display = 'flex';
    
    // Clear any previous error messages
    const errorDiv = document.getElementById('dialogError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

// Close confirmation dialog
function closeDialog() {
    const dialogOverlay = document.getElementById('dialogOverlay');
    if (dialogOverlay) {
        dialogOverlay.style.display = 'none';
    }
    currentAction = null;
    currentVersions = null;
}

// Execute confirmed action
async function executeAction() {
    if (!currentAction || selectedRobots.size === 0) return;

    try {
        // Get only enabled robots
        const enabledRobots = Array.from(selectedRobots).filter(robotId => {
            const checkbox = document.querySelector(`.robot-checkbox[value="${robotId}"]`);
            return checkbox && !checkbox.disabled;
        });

        if (enabledRobots.length === 0) {
            throw new Error('No enabled robots selected');
        }

        const promises = enabledRobots.map(robotId => {
            return new Promise((resolve, reject) => {
                let commandData = currentAction;
                let commandOption = null;

                if (currentAction === 'software_update') {
                    const selectedImages = [];
                    const versionItems = document.querySelectorAll('.version-item');
                    
                    versionItems.forEach(item => {
                        const checkbox = item.querySelector('input[type="checkbox"].version-checkbox');
                        
                        if (checkbox && checkbox.checked && !checkbox.disabled) {
                            const imageId = checkbox.id.replace('-checkbox', '');
                            const select = document.getElementById(`${imageId}-version`);
                            const nameText = item.querySelector('.version-name-text');
                            
                            if (select && nameText && nameText.textContent && 
                                nameText.textContent !== '+ Click here to set Docker image name') {
                                const imageInfo = {
                                    name: nameText.textContent.trim(),
                                    version: select.value
                                };
                                selectedImages.push(imageInfo);
                            }
                        }
                    });
                    
                    if (selectedImages.length > 0) {
                        commandOption = {
                            images: selectedImages
                        };
                    }
                } else if(currentAction === 'site_update') {
                    commandOption = {
                        'CABOT_SITE_REPO': document.getElementById('CABOT_SITE_REPO').value.trim(),
                        'CABOT_SITE_VERSION': document.getElementById('CABOT_SITE_VERSION').value.trim(),
                        'CABOT_SITE': document.getElementById('CABOT_SITE').value.trim()
                    };
                } else if(currentAction === 'env_update') {
                    commandOption = {};
                    for (const row of document.querySelectorAll('#envTable tbody tr')) {
                        const input = row.querySelectorAll('input[type=text]');
                        commandOption[input[0].value.trim()] = input[1].value.trim();
                    }
                }

                const message = {
                    type: 'command',
                    cabotId: robotId,
                    command: commandData,
                    commandOption: commandOption || {}
                };

                ws.send(JSON.stringify(message));
                resolve();
            });
        });

        await Promise.all(promises);
        closeDialog();
    } catch (error) {
        console.error('Error executing action:', error);
        const errorDiv = document.getElementById('dialogError');
        if (errorDiv) {
            errorDiv.textContent = error.message || 'Failed to execute action';
            errorDiv.style.display = 'block';
        }
    }
}

// Send command to robot
function sendCommand(command) {
    const actionError = document.getElementById('actionError');
    
    // Clear previous error message
    if (actionError) {
        actionError.style.display = 'none';
        actionError.textContent = '';
    }

    if (selectedRobots.size === 0) {
        if (actionError) {
            actionError.textContent = 'Please select at least one robot before executing an action.';
            actionError.style.display = 'block';    
        }
        return;
    }

    showConfirmDialog(command);
}

// Update dashboard with new data
function updateDashboard(data) {
    // Clear any existing error messages
    const actionError = document.getElementById('actionError');
    if (actionError) {
        actionError.style.display = 'none';
        actionError.textContent = '';
    }
    
    const robotList = document.querySelector('.robot-list');
    if (!robotList) {
        console.error('Robot list container not found');
        return;
    }
    robotList.innerHTML = '';

    if (!data.cabots || data.cabots.length === 0) {
        robotList.innerHTML = '<div class="text-center text-muted p-3">No robots connected</div>';
        return;
    }

    // Update total robots count
    totalRobots = data.cabots.length;

    // Filter and display robots
    data.cabots.forEach(robot => {
        if (currentFilter === 'all' ||
            (currentFilter === 'connected' && robot.connected) ||
            (currentFilter === 'disconnected' && !robot.connected)) {
            
            const robotCard = document.createElement('div');
            robotCard.className = 'robot-card mb-3';
            robotCard.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="form-check">
                        <input class="form-check-input robot-checkbox" type="checkbox" value="${robot.id}"
                               ${selectedRobots.has(robot.id) ? 'checked' : ''}
                               ${!robot.connected ? 'disabled' : ''}>
                        <label class="form-check-label fw-bold">${robot.name || robot.id}</label>
                    </div>
                    <div class="text-end">
                        <div>
                            <span class="badge ${robot.connected ? 'bg-success' : 'bg-danger'} me-1">
                                ${robot.connected ? 'Connected' : 'Disconnected'}
                            </span>
                            <span class="badge ${robot.system_status === 'active' ? 'bg-primary' : 
                                               robot.system_status === 'failed' ? 'bg-danger' : 
                                               robot.system_status === 'inactive' ? 'bg-warning' : 
                                               robot.system_status === 'deactivating' ? 'bg-info' : 
                                               'bg-secondary'}">
                                ${robot.system_status ? robot.system_status.charAt(0).toUpperCase() + robot.system_status.slice(1) : 'Unknown'}
                            </span>
                        </div>
                        <div class="text-muted small mt-1">Last Poll: ${formatDateTime(robot.last_poll)}</div>
                    </div>
                </div>
                ${Object.keys(robot.images || {}).length > 0 ? `
                <div class="image-versions mb-2">
                    ${Object.entries(robot.images || {}).map(([name, tag]) => 
                        `<div class="version-tag">${name}: ${tag}</div>`
                    ).join('')}
                </div>
                ` : robot.connected ? `
                <div class="alert alert-info py-1 px-3 mb-2">
                    <i class="bi bi-info-circle me-2"></i>Please execute "Get Image Tags" to retrieve the current software versions.
                </div>
                ` : ''}
                <div class="image-versions mb-2">
                    ${Object.entries(robot.env || {}).map(([name, tag]) => 
                        `<div class="version-tag env-tag">${name}=${tag}</div>`
                    ).join('')}
                </div>
                <div class="robot-info">
                    ${robot.messages && robot.messages.length > 0 ? `
                    <div class="message-area mb-2">
                        ${robot.messages.map(msg => `
                            <div class="alert ${msg.level === 'error' ? 'alert-danger' : 
                                               msg.level === 'success' ? 'alert-success' : 
                                               'alert-info'} py-0 px-3 mb-1">
                                <span class="text-muted me-2" style="font-size: 0.9em;">
                                    ${formatDateTime(msg.timestamp).split(' ')[1]}
                                </span>
                                ${msg.message}
                            </div>
                        `).join('')}
                    </div>
                    ` : ''}
                    ${robot.all_messages && robot.all_messages.length > 0 ? `
                    <div class="text-end mt-2">
                        <button class="btn btn-sm btn-outline-secondary view-history-btn" 
                                data-robot-id="${robot.id}"
                                data-messages='${JSON.stringify(robot.all_messages).replace(/'/g, "&#39;")}'>
                            <i class="bi bi-clock-history"></i> View History
                        </button>
                    </div>
                    ` : ''}
                </div>
            `;

            // Add event listener for checkbox
            const checkbox = robotCard.querySelector('.robot-checkbox');
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    selectedRobots.add(robot.id);
                } else {
                    selectedRobots.delete(robot.id);
                }
                updateSelectAllCheckbox();
                updateSelectedCount();
            });

            robotList.appendChild(robotCard);
        }
    });

    updateSelectedCount();
    updateSelectAllCheckbox();
}

// Format date time
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'Unknown';
    
    try {
        // Convert UTC string to Date object and display in JST
        const date = new Date(dateTimeString + 'Z');
        return date.toLocaleString('en-US', { 
            timeZone: 'Asia/Tokyo',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }).replace(/\//g, '/');
    } catch (error) {
        console.error('Error formatting date:', error);
        return dateTimeString;  // Return original string on error
    }
}

// Handle tags response
function handleTagsResponse(data) {
    const imageId = data.image_id;
    const versionItem = document.querySelector(`#version-${imageId}`);
    if (!versionItem) {
        console.error('Version item not found for image:', imageId);
        return;
    }

    const select = versionItem.querySelector('select');
    const errorDiv = versionItem.querySelector('.error-message');
    const checkbox = versionItem.querySelector('.version-checkbox');
    
    if (data.status === 'error') {
        if (errorDiv) {
            errorDiv.textContent = data.message || 'Failed to fetch tags';
        }
        if (checkbox) {
            checkbox.disabled = true;
        }
        return;
    }

    // Clear and update options
    if (select) {
        select.innerHTML = '';
        data.tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag;
            option.textContent = tag;
            select.appendChild(option);
        });

        if (data.tags.length > 0 && checkbox) {
            checkbox.disabled = false;
        }
    }

    // Update last updated timestamp
    const lastUpdated = versionItem.querySelector('.last-updated');
    if (lastUpdated) {
        lastUpdated.textContent = `Last updated: ${new Date().toLocaleString('ja-JP', { 
            timeZone: 'Asia/Tokyo',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }).replace(/\//g, '/')}`;
    }

    if (errorDiv) {
        errorDiv.textContent = '';
    }
}

// Handle image name response
function handleImageNameResponse(data) {
    const imageId = data.image_id;
    const versionItem = document.querySelector(`#version-${imageId}`);
    if (!versionItem) {
        console.error('Version item not found for image:', imageId);
        return;
    }

    const nameText = versionItem.querySelector('.version-name-text');
    const nameInput = versionItem.querySelector('.version-name-input');
    const select = versionItem.querySelector('select');
    const refreshBtn = versionItem.querySelector('.refresh-btn');
    const errorDiv = versionItem.querySelector('.error-message');
    
    if (data.status === 'success') {
        if (nameText) {
            nameText.textContent = data.image_name;
            nameText.classList.remove('empty-name');
        }
        if (nameInput) {
            nameInput.value = data.image_name;
            nameInput.dataset.original = data.image_name;
        }
        if (select) {
            select.disabled = false;
        }
        if (refreshBtn) {
            refreshBtn.disabled = false;
        }
    } else {
        if (errorDiv) {
            errorDiv.textContent = data.message || 'Failed to update image name';
        }
        if (nameText) {
            nameText.textContent = nameInput.dataset.original || PLACEHOLDER_TEXT;
            if (!nameInput.dataset.original) {
                nameText.classList.add('empty-name');
            }
        }
    }
    
    if (nameInput) {
        nameInput.style.display = 'none';
    }
    if (nameText) {
        nameText.style.display = 'block';
    }
}

// Update image controls visibility and state
function updateImageControls(imageId, hasImageName) {
    const versionItem = document.querySelector(`#version-${imageId}`);
    if (!versionItem) return;

    const select = versionItem.querySelector('select');
    const refreshBtn = versionItem.querySelector('.refresh-btn');
    const nameText = versionItem.querySelector('.version-name-text');
    const checkbox = versionItem.querySelector('.version-checkbox');
    
    if (select) select.disabled = !hasImageName;
    if (refreshBtn) refreshBtn.disabled = !hasImageName;
    if (nameText) nameText.classList.toggle('empty-name', !hasImageName);
    if (checkbox) {
        checkbox.disabled = !hasImageName || (select && select.options.length === 0);
    }
}

// Start editing image name
function startEdit(element) {
    const versionItem = element.closest('.version-item');
    if (!versionItem) return;

    const nameInput = versionItem.querySelector('.version-name-input');
    const nameText = versionItem.querySelector('.version-name-text');
    
    if (nameInput && nameText) {
        nameText.style.display = 'none';
        nameInput.style.display = 'block';
        nameInput.focus();
        
        // Add blur event listener if not already added
        if (!nameInput.dataset.hasBlurListener) {
            nameInput.addEventListener('blur', () => {
                const newName = nameInput.value.trim();
                const originalName = nameInput.dataset.original;
                
                if (newName !== originalName) {
                    // Get image ID from version item ID
                    const imageId = versionItem.id.replace('version-', '');
                    updateImageName(imageId, newName);
                } else {
                    // If no change, just hide input and show text
                    nameInput.style.display = 'none';
                    nameText.style.display = 'block';
                }
            });
            nameInput.dataset.hasBlurListener = 'true';
        }
    }
}

// Update image name
function updateImageName(imageId, newName) {
    if (!ws || !isConnected) {
        console.error('WebSocket not connected');
        return;
    }

    const message = {
        type: 'update_image_name',
        image_id: imageId,
        image_name: newName
    };

    try {
        ws.send(JSON.stringify(message));
    } catch (error) {
        console.error('Error sending update image name message:', error);
    }
}

// Refresh tags for a robot
async function refreshTags(imageId) {
    try {
        ws.send(JSON.stringify({
            type: 'refresh_tags',
            image_id: imageId
        }));
    } catch (error) {
        console.error('Failed to refresh tags:', error);
        const errorDiv = document.querySelector(`#${imageId}-error`);
        if (errorDiv) {
            errorDiv.textContent = error.message || 'Failed to refresh tags';
        }
    }
}

// Toggle all robots
function toggleAllRobots(checked) {
    const checkboxes = document.querySelectorAll('.robot-checkbox:not(:disabled)');
    selectedRobots.clear();
    
    if (checked) {
        checkboxes.forEach(checkbox => {
            selectedRobots.add(checkbox.value);
            checkbox.checked = true;
        });
    } else {
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
    }
    
    updateSelectedCount();
}

// Update select all checkbox state
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.robot-checkbox:not(:disabled)');
    const checkedBoxes = document.querySelectorAll('.robot-checkbox:checked');
    
    if (checkboxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.disabled = true;
    } else {
        selectAllCheckbox.disabled = false;
        selectAllCheckbox.checked = checkboxes.length === checkedBoxes.length;
    }
}

// Update selected robots count
function updateSelectedCount() {
    const selectedCount = document.querySelector('.selected-count');
    if (selectedCount) {
        const visibleRobots = document.querySelectorAll('.robot-card').length;
        selectedCount.textContent = `(${selectedRobots.size}/${visibleRobots})`;
    }
}

// Update message list
function updateMessageList(messages) {
    const messageList = document.querySelector('.message-list');
    if (!messageList) return;

    messageList.innerHTML = '';
    
    if (!messages || messages.length === 0) {
        messageList.innerHTML = '<div class="text-center text-muted p-3">No messages</div>';
        return;
    }

    messages.forEach(msg => {
        const messageItem = document.createElement('div');
        messageItem.className = 'message-item p-2 border-bottom';
        messageItem.innerHTML = `
            <div class="d-flex justify-content-between">
                <span class="text-muted small">${formatDateTime(msg.timestamp)}</span>
                <span class="badge ${msg.level === 'error' ? 'bg-danger' : 'bg-info'}">${msg.level}</span>
            </div>
            <div class="message-content">${msg.message}</div>
        `;
        messageList.appendChild(messageItem);
    });
}

// Update software
function updateSoftware() {
    document.querySelector(".version-checkbox").checked=true
    const updateError = document.getElementById('updateError');
    
    // Clear previous error message
    if (updateError) {
        updateError.style.display = 'none';
        updateError.textContent = '';
    }

    // Get only enabled robots
    const enabledRobots = Array.from(selectedRobots).filter(robotId => {
        const checkbox = document.querySelector(`.robot-checkbox[value="${robotId}"]`);
        return checkbox && !checkbox.disabled;
    });

    // 1. Check robot selection
    if (enabledRobots.length === 0) {
        if (updateError) {
            updateError.textContent = 'Please select at least one enabled robot.';
            updateError.style.display = 'block';
        }
        return;
    }

    // 2. Check image selection
    const selectedImages = [];
    document.querySelectorAll('.version-item').forEach(item => {
        const checkbox = item.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked && !checkbox.disabled) {
            selectedImages.push(checkbox.value);
        }
    });

    if (selectedImages.length === 0) {
        if (updateError) {
            updateError.textContent = 'Please select at least one enabled Docker image.';
            updateError.style.display = 'block';
        }
        return;
    }

    // 3. Check tag selection and collect version information
    const selectedVersions = [];
    let missingTags = false;

    selectedImages.forEach(imageId => {
        const select = document.querySelector(`#${imageId}-version`);
        if (select && select.value) {
            selectedVersions.push({
                image_id: imageId,
                tag: select.value
            });
        } else {
            missingTags = true;
        }
    });

    if (missingTags) {
        if (updateError) {
            updateError.textContent = 'Please ensure all selected images have tags selected.';
            updateError.style.display = 'block';
        }
        return;
    }

    // 4. Show dialog
    showUpdateConfirmDialog(new Set(enabledRobots), selectedVersions);
}

// Show update confirmation dialog
function showUpdateConfirmDialog(robots, versions) {
    const dialog = document.getElementById('confirmDialog');
    const selectedRobotsList = document.getElementById('selectedRobots');
    const confirmButton = document.getElementById('confirmAction');
    const dialogTitle = document.getElementById('dialogTitle');
    const dialogOverlay = document.getElementById('dialogOverlay');
    
    if (!dialog || !selectedRobotsList || !confirmButton || !dialogTitle || !dialogOverlay) {
        console.error('Dialog elements not found');
        return;
    }
    
    // Update dialog content
    let content = '<h6>Selected AI Suitcases:</h6>';
    content += Array.from(robots).map(robotId => `<li>${robotId}</li>`).join('');
    content += '<h6 class="mt-3">Selected Images:</h6>';
    content += versions.map(v => {
        const nameText = document.querySelector(`#version-${v.image_id} .version-name-text`);
        const imageName = nameText ? nameText.textContent.trim() : v.image_id;
        // return `<li>${imageName}: ${v.tag}</li>`;
        return `<li>*: ${v.tag}</li>`;
    }).join('');
    selectedRobotsList.innerHTML = content;
    
    // Set current action and versions
    currentAction = 'software_update';
    currentVersions = versions;
    
    // Update dialog title and button
    dialogTitle.textContent = 'Confirm Software Update';
    confirmButton.textContent = 'Update Software';
    
    // Show overlay and dialog
    dialogOverlay.style.display = 'flex';
    
    // Clear any previous error messages
    const errorDiv = document.getElementById('dialogError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

// Handle software update response
function handleSoftwareUpdateResponse(data) {
    const { status, message } = data;
    const updateError = document.getElementById('updateError');
    
    if (status === 'error' && updateError) {
        updateError.textContent = message || 'Failed to update software';
        updateError.style.display = 'block';
    } else if (status === 'success') {
        // Clear error message on success
        if (updateError) {
            updateError.style.display = 'none';
            updateError.textContent = '';
        }
    }
}

// Filter robots
function filterRobots(filter) {
    currentFilter = filter;
    const robotList = document.querySelector('.robot-list');
    if (!robotList) return;

    // Clear selected robots when filter changes
    selectedRobots.clear();
    updateSelectedCount();
    updateSelectAllCheckbox();

    // Request latest data
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'refresh' }));
    }
}

// Show log dialog
function showLogDialog(robotId, allMessages) {
    const dialog = document.getElementById('logDialog');
    const content = document.getElementById('logContent');
    if (!dialog || !content) return;

    // Clear previous content
    content.innerHTML = '';

    // Sort messages by timestamp in descending order
    const sortedMessages = allMessages.sort((a, b) => {
        return new Date(b.timestamp) - new Date(a.timestamp);
    });

    // Add all messages to dialog
    sortedMessages.forEach(msg => {
        const entry = document.createElement('div');
        entry.className = 'log-entry mb-2';
        entry.innerHTML = `
            <div class="d-flex">
                <span class="log-timestamp me-3">${formatDateTime(msg.timestamp)}</span>
                <div class="log-message ${msg.level === 'error' ? 'text-danger' : 
                                       msg.level === 'success' ? 'text-success' : 
                                       'text-dark'}">${msg.message}</div>
            </div>
        `;
        content.appendChild(entry);
    });

    // Show dialog
    dialog.style.display = 'flex';

    // Add escape key handler
    document.addEventListener('keydown', handleLogDialogEscape);
}

// Close log dialog
function closeLogDialog() {
    const dialog = document.getElementById('logDialog');
    if (dialog) {
        dialog.style.display = 'none';
    }
    document.removeEventListener('keydown', handleLogDialogEscape);
}

// Handle escape key for log dialog
function handleLogDialogEscape(event) {
    if (event.key === 'Escape') {
        closeLogDialog();
    }
}

// Find robot by ID
function findRobotById(robotId) {
    const robotCard = document.querySelector(`.robot-card input[value="${robotId}"]`);
    if (!robotCard) return null;

    const robotData = {
        id: robotId,
        messages: [],
        all_messages: []
    };

    // Get messages from the robot card
    const messageElements = robotCard.closest('.robot-card').querySelectorAll('.message-area .alert');
    messageElements.forEach(msgElement => {
        const timestampElement = msgElement.querySelector('.text-muted');
        const timestamp = timestampElement.textContent.trim();
        const message = msgElement.textContent.replace(timestampElement.textContent, '').trim();
        let level = 'info';
        if (msgElement.classList.contains('alert-danger')) level = 'error';
        else if (msgElement.classList.contains('alert-success')) level = 'success';

        robotData.messages.push({
            timestamp: timestamp,
            message: message,
            level: level
        });
        robotData.all_messages.push({
            timestamp: timestamp,
            message: message,
            level: level
        });
    });

    return robotData;
}

// Show log dialog from button
function showLogDialogFromButton(button) {
    const robotId = button.dataset.robotId;
    const messages = JSON.parse(button.dataset.messages);
    showLogDialog(robotId, messages);
}

// Initialize Docker Hub version items
function initializeDockerVersions() {
    console.log('Initializing Docker Hub versions...');
    
    // Initialize Docker Hub version items
    const dockerVersions = window.dockerVersions || {};
    Object.entries(dockerVersions).forEach(([key, image]) => {
        const versionItem = document.querySelector(`#version-${key}`);
        if (!versionItem) {
            console.log(`Version item not found for key: ${key}`);
            return;
        }

        // Set image name
        const nameText = versionItem.querySelector('.version-name-text');
        const nameInput = versionItem.querySelector('.version-name-input');
        if (nameText && nameInput) {
            nameText.textContent = image.name || PLACEHOLDER_TEXT;
            nameText.classList.toggle('empty-name', !image.name);
            nameInput.value = image.name || '';
            nameInput.dataset.original = image.name || '';
        }

        // Set tags
        const select = versionItem.querySelector('select');
        if (select) {
            select.innerHTML = '';
            (image.tags || []).forEach(tag => {
                const option = document.createElement('option');
                option.value = tag;
                option.textContent = tag;
                select.appendChild(option);
            });
        }

        // Set last updated
        const lastUpdated = versionItem.querySelector('.last-updated');
        if (lastUpdated && image.last_updated) {
            lastUpdated.textContent = `Last updated: ${formatDateTime(image.last_updated)}`;
        }

        // Update controls state
        updateImageControls(key, !!image.name);

        // Add click handlers
        const nameTextElement = versionItem.querySelector('.version-name-text');
        if (nameTextElement) {
            nameTextElement.addEventListener('click', () => {
                startEdit(nameTextElement);
            });
        }
    });
}

// Format date time
function formatDateTime(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (error) {
        console.error('Error formatting date:', error);
        return dateString;
    }
}

async function onSiteUpdate() {
    const repository = document.getElementById('CABOT_SITE_REPO').value.trim();

    console.log('Selected site repository:', repository);
    try {
        ws.send(JSON.stringify({
            type: 'refresh_site',
            repository: repository
        }));
    } catch (error) {
        console.error('Failed to refresh site:', error);
        const errorDiv = document.getElementById('siteError');
        errorDiv.textContent = error.message || 'Failed to refresh site';
        errorDiv.style.display = 'block';
    }
}

function handleSiteResponse(data) {
    console.log(data);
    const repository = data.repository;
    const siteRepo = document.getElementById('CABOT_SITE_REPO');
    const siteVersions = document.getElementById('CABOT_SITE_VERSION');
    const siteName = document.getElementById('CABOT_SITE');
    const errorDiv = document.getElementById('siteError');
    siteVersions.innerHTML = '';

    if (data.status === 'error') {
        siteName.value = '';
        errorDiv.textContent = data.message || 'Failed to fetch site reposiiotry';
        errorDiv.style.display = 'block';
        return;
    }

    errorDiv.style.display = 'none';
    siteRepo.value = data.info.CABOT_SITE_REPO;
    siteName.value = data.info.CABOT_SITE;
    data.info.CABOT_SITE_VERSION.forEach(version => {
        const option = document.createElement('option');
        option.value = version;
        option.textContent = version;
        siteVersions.appendChild(option);
    });
}

function updateSite() {
    const errorDiv = document.getElementById('siteError');

    // Clear previous error message
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';

    // Get only enabled robots
    const enabledRobots = Array.from(selectedRobots).filter(robotId => {
        const checkbox = document.querySelector(`.robot-checkbox[value="${robotId}"]`);
        return checkbox && !checkbox.disabled;
    });

    if (enabledRobots.length === 0) {
        errorDiv.textContent = 'Please select at least one enabled robot.';
        errorDiv.style.display = 'block';
        return;
    }

    const siteRepo = document.getElementById('CABOT_SITE_REPO').value.trim();
    const siteVersion = document.getElementById('CABOT_SITE_VERSION').value.trim();
    const siteName = document.getElementById('CABOT_SITE').value.trim();
    if (!siteRepo || !siteVersion || !siteName) {
        errorDiv.textContent = 'Please fill in all site information.';
        errorDiv.style.display = 'block';
        return;
    }

    showSiteUpdateConfirmDialog(new Set(enabledRobots), siteRepo, siteVersion, siteName);
}

// Show update confirmation dialog
function showSiteUpdateConfirmDialog(robots, siteRepo, siteVersion, siteName) {
    const dialog = document.getElementById('confirmDialog');
    const selectedRobotsList = document.getElementById('selectedRobots');
    const confirmButton = document.getElementById('confirmAction');
    const dialogTitle = document.getElementById('dialogTitle');
    const dialogOverlay = document.getElementById('dialogOverlay');

    if (!dialog || !selectedRobotsList || !confirmButton || !dialogTitle || !dialogOverlay) {
        console.error('Dialog elements not found');
        return;
    }

    // Update dialog content
    let content = '<h6>Selected AI Suitcases:</h6>';
    content += Array.from(robots).map(robotId => `<li>${robotId}</li>`).join('');
    content += '<h6 class="mt-3">Site Parameters:</h6>';
    content += `<li>Site Repository: ${siteRepo}</li>`;
    content += `<li>Version: ${siteVersion}</li>`;
    content += `<li>Package Name: ${siteName}</li>`;
    selectedRobotsList.innerHTML = content;

    // Set current action and versions
    currentAction = 'site_update';

    // Update dialog title and button
    dialogTitle.textContent = 'Confirm Site Update';
    confirmButton.textContent = 'Update Site';

    // Show overlay and dialog
    dialogOverlay.style.display = 'flex';

    // Clear any previous error messages
    const errorDiv = document.getElementById('dialogError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

function addEnvRow() {
    var newRow = `<tr>
        <td><input type="text" class="form-control" name="key[]"></td>
        <td><input type="text" class="form-control" name="value[]"></td>
        <td><button type="button" class="btn btn-outline-danger btn-sm refresh-btn remove-row"><i class="bi bi-trash"></i></button></td>
    </tr>`;
    document.querySelector('#envTable tbody').insertAdjacentHTML('beforeend', newRow);
    const buttons = document.querySelectorAll('.remove-row');
    buttons[buttons.length - 1].addEventListener('click', function() {
        this.closest('tr').remove()
    });
}

function updateEnv() {
    const errorDiv = document.getElementById('envError');

    // Clear previous error message
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';

    // Get only enabled robots
    const enabledRobots = Array.from(selectedRobots).filter(robotId => {
        const checkbox = document.querySelector(`.robot-checkbox[value="${robotId}"]`);
        return checkbox && !checkbox.disabled;
    });

    if (enabledRobots.length === 0) {
        errorDiv.textContent = 'Please select at least one enabled robot.';
        errorDiv.style.display = 'block';
        return;
    }

    const envList = {};
    for (const row of document.querySelectorAll('#envTable tbody tr')) {
        const input = row.querySelectorAll('input[type=text]');
        const key = input[0].value.trim();
        if (key) {
            envList[key] = input[1].value.trim();
        } else {
            errorDiv.textContent = 'Environment key should not be empty.';
            errorDiv.style.display = 'block';
            return;
        }
    }
    if (Object.keys(envList).length === 0) {
        errorDiv.textContent = 'Please add at least one environment variable.';
        errorDiv.style.display = 'block';
        return;
    }

    showEnvUpdateConfirmDialog(new Set(enabledRobots), envList);
}

// Show update confirmation dialog
function showEnvUpdateConfirmDialog(robots, envList) {
    const dialog = document.getElementById('confirmDialog');
    const selectedRobotsList = document.getElementById('selectedRobots');
    const confirmButton = document.getElementById('confirmAction');
    const dialogTitle = document.getElementById('dialogTitle');
    const dialogOverlay = document.getElementById('dialogOverlay');

    if (!dialog || !selectedRobotsList || !confirmButton || !dialogTitle || !dialogOverlay) {
        console.error('Dialog elements not found');
        return;
    }

    // Update dialog content
    let content = '<h6>Selected AI Suitcases:</h6>';
    content += Array.from(robots).map(robotId => `<li>${robotId}</li>`).join('');
    content += '<h6 class="mt-3">Environment Variables:</h6>';
    for (const [key, value] of Object.entries(envList)) {
        content += `<li>${key}=${value}</li>`;
    }
    selectedRobotsList.innerHTML = content;

    // Set current action and versions
    currentAction = 'env_update';

    // Update dialog title and button
    dialogTitle.textContent = 'Confirm Environment Variable Update';
    confirmButton.textContent = 'Update Environment Variables';

    // Show overlay and dialog
    dialogOverlay.style.display = 'flex';

    // Clear any previous error messages
    const errorDiv = document.getElementById('dialogError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}
