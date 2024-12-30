// WebSocket connection
let ws = null;
let isConnected = false;
let selectedRobots = new Set();
let currentFilter = 'all';
let robotStateManager = null;
let totalRobots = 0;  // Add total robots counter

// Dialog related variables
let currentAction = null;
const PLACEHOLDER_TEXT = '+ Click here to set Docker image name';

// Initialize WebSocket connection
function initWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = () => {
        isConnected = true;
        updateConnectionStatus();
    };
    
    ws.onclose = () => {
        isConnected = false;
        updateConnectionStatus();
        setTimeout(initWebSocket, 5000);
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

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
            }
        } catch (error) {
            console.error('WebSocket message processing error:', error);
        }
    };
}

// Update connection status display
function updateConnectionStatus() {
    const statusBadge = document.querySelector('.navbar .badge');
    if (isConnected) {
        statusBadge.classList.remove('bg-danger');
        statusBadge.classList.add('bg-success');
        statusBadge.textContent = 'Connected';
    } else {
        statusBadge.classList.remove('bg-success');
        statusBadge.classList.add('bg-danger');
        statusBadge.textContent = 'Disconnected';
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
    
    // Update dialog content
    selectedRobotsList.innerHTML = Array.from(selectedRobots)
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
        const promises = Array.from(selectedRobots).map(robotId => {
            return new Promise((resolve, reject) => {
                let commandData = currentAction;
                let commandOption = null;

                if (currentAction === 'software_update') {
                    const selectedImages = [];
                    const versionItems = document.querySelectorAll('.version-item');
                    
                    versionItems.forEach(item => {
                        const checkbox = item.querySelector('input[type="checkbox"].version-checkbox');
                        
                        if (checkbox && checkbox.checked) {
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
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="form-check">
                        <input class="form-check-input robot-checkbox" type="checkbox" value="${robot.id}"
                               ${selectedRobots.has(robot.id) ? 'checked' : ''}
                               ${!robot.connected ? 'disabled' : ''}>
                        <label class="form-check-label fw-bold">${robot.id}</label>
                    </div>
                    <div>
                        <span class="badge ${robot.connected ? 'bg-success' : 'bg-danger'} me-1">
                            ${robot.connected ? 'Connected' : 'Disconnected'}
                        </span>
                        <span class="badge bg-primary">Running</span>
                    </div>
                </div>
                <div class="robot-info">
                    <p class="text-muted mb-2">Last Poll: ${formatDateTime(robot.last_poll)}</p>
                    <p class="mb-2">System operational</p>
                    <div class="d-flex justify-content-between">
                        <span class="version-tag">docker: ${robot.docker_version || 'N/A'}</span>
                        <span class="version-tag">sites: ${robot.sites_version || 'N/A'}</span>
                        <span class="version-tag">map: ${robot.map_version || 'N/A'}</span>
                    </div>
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

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', () => {
    if (window.RobotStateManager) {
        robotStateManager = new window.RobotStateManager();
    }
    
    initWebSocket();
    
    // Add select all handler
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            toggleAllRobots(e.target.checked);
        });
    }
    
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
    const dockerVersions = window.dockerVersions || {};
    Object.entries(dockerVersions).forEach(([key, image]) => {
        const versionItem = document.querySelector(`#version-${key}`);
        if (!versionItem) return;

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
});

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
    const textElement = versionItem.querySelector('.version-name-text');
    const inputElement = versionItem.querySelector('.version-name-input');
    
    // Get current text
    const currentText = textElement.textContent.trim();
    inputElement.value = currentText === PLACEHOLDER_TEXT ? '' : currentText;
    
    // Toggle display
    textElement.style.display = 'none';
    inputElement.style.display = 'block';
    inputElement.focus();
    
    if (inputElement.value) {
        inputElement.select();
    }

    // Add event listeners
    function handleBlur() {
        finishEdit(inputElement);
        inputElement.removeEventListener('blur', handleBlur);
        inputElement.removeEventListener('keypress', handleKeyPress);
        inputElement.removeEventListener('keydown', handleKeyDown);
    }

    function handleKeyPress(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            finishEdit(inputElement);
            inputElement.removeEventListener('blur', handleBlur);
            inputElement.removeEventListener('keypress', handleKeyPress);
            inputElement.removeEventListener('keydown', handleKeyDown);
        }
    }

    function handleKeyDown(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            textElement.style.display = 'block';
            inputElement.style.display = 'none';
            inputElement.removeEventListener('blur', handleBlur);
            inputElement.removeEventListener('keypress', handleKeyPress);
            inputElement.removeEventListener('keydown', handleKeyDown);
        }
    }

    inputElement.addEventListener('blur', handleBlur);
    inputElement.addEventListener('keypress', handleKeyPress);
    inputElement.addEventListener('keydown', handleKeyDown);
}

// Finish editing image name
async function finishEdit(input) {
    const versionItem = input.closest('.version-item');
    const imageId = input.dataset.imageId;
    const textElement = versionItem.querySelector('.version-name-text');
    const errorDiv = versionItem.querySelector('.error-message');
    const newName = input.value.trim();
    
    errorDiv.textContent = '';
    
    if (newName === '') {
        textElement.textContent = PLACEHOLDER_TEXT;
        textElement.classList.add('empty-name');
        updateImageControls(imageId, false);
        textElement.style.display = 'block';
        input.style.display = 'none';
        return;
    }

    try {
        ws.send(JSON.stringify({
            type: 'update_image_name',
            image_id: imageId,
            image_name: newName
        }));

        textElement.textContent = newName;
        textElement.classList.remove('empty-name');
        updateImageControls(imageId, true);
        input.dataset.original = newName;
    } catch (error) {
        console.error('Failed to update image name:', error);
        errorDiv.textContent = error.message || 'Failed to update image name';
        textElement.textContent = input.dataset.original || PLACEHOLDER_TEXT;
        if (!input.dataset.original) {
            textElement.classList.add('empty-name');
            updateImageControls(imageId, false);
        }
    } finally {
        textElement.style.display = 'block';
        input.style.display = 'none';
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
    const updateError = document.getElementById('updateError');
    
    // Clear previous error message
    if (updateError) {
        updateError.style.display = 'none';
        updateError.textContent = '';
    }

    // 1. Check robot selection
    if (selectedRobots.size === 0) {
        if (updateError) {
            updateError.textContent = 'Please select at least one robot.';
            updateError.style.display = 'block';
        }
        return;
    }

    // 2. Check image selection
    const selectedImages = [];
    document.querySelectorAll('.version-item').forEach(item => {
        const checkbox = item.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) {
            selectedImages.push(checkbox.value);
        }
    });

    if (selectedImages.length === 0) {
        if (updateError) {
            updateError.textContent = 'Please select at least one Docker image.';
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
    showUpdateConfirmDialog(selectedRobots, selectedVersions);
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
    let content = '<h6>Selected Robots:</h6>';
    content += Array.from(robots).map(robotId => `<li>${robotId}</li>`).join('');
    content += '<h6 class="mt-3">Selected Images:</h6>';
    content += versions.map(v => {
        const nameText = document.querySelector(`#version-${v.image_id} .version-name-text`);
        const imageName = nameText ? nameText.textContent.trim() : v.image_id;
        return `<li>${imageName}: ${v.tag}</li>`;
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