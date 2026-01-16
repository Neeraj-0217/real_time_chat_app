// ========================================
// WEBSOCKET CHAT CLIENT - CLEANED & FIXED
// ========================================

// -------------------- CONSTANTS --------------------
const MAX_RECONNECT_ATTEMPTS = 5;
const PING_INTERVAL_MS = 30000;              // 30 seconds
const TYPING_DEBOUNCE_MS = 2000;             // 2 seconds
const TYPING_INDICATOR_TIMEOUT_MS = 3000;    // 3 seconds
const STATUS_REFRESH_INTERVAL_MS = 30000;    // 30 seconds
const SEARCH_DEBOUNCE_MS = 300;              // 300ms
const MAX_MESSAGE_LENGTH = 1000;             // Maximum message characters
const MAX_FILE_SIZE = 5 * 1024 * 1024;       // 5MB

// -------------------- STATE VARIABLES --------------------
let socket = null;
let currentReceiverId = null;
let reconnectAttempts = 0;
let reconnectTimeout = null;
let pingInterval = null;
let isConnected = false;
let typingTimeout = null;
let lastTypingTime = 0;
let currentChatLanguage = 'en';
let verifiedUserId = null;
let searchTimeout = null;

// ========================================
// WEBSOCKET CONNECTION MANAGEMENT
// ========================================

/**
 * Connect to WebSocket server with verified user ID
 * Only connects if user has been verified
 */
function connectWebSocket() {
    // CRITICAL: Only connect if we have a verified user ID
    if (!verifiedUserId) {
        console.error('❌ Cannot connect: User not verified yet');
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/${verifiedUserId}`;

    console.log(`🔌 Connecting to WebSocket for user ${verifiedUserId}...`);
    socket = new WebSocket(wsUrl);

    socket.onopen = handleWebSocketOpen;
    socket.onmessage = handleWebSocketMessage;
    socket.onerror = handleWebSocketError;
    socket.onclose = handleWebSocketClose;
}

/**
 * Handle WebSocket connection opened
 */
function handleWebSocketOpen() {
    console.log(`✅ WebSocket connected for user ${verifiedUserId}`);
    isConnected = true;
    reconnectAttempts = 0;

    // Start heartbeat ping
    startPingInterval();

    // Refresh current chat if open
    if (currentReceiverId) {
        loadChatHistory(currentReceiverId);
    }

    // Update all contact statuses
    updateAllContactStatuses();
}

/**
 * Handle incoming WebSocket messages
 * @param {MessageEvent} event - WebSocket message event
 */
function handleWebSocketMessage(event) {
    const data = JSON.parse(event.data);
    console.log("📨 Received:", data);

    switch(data.type) {
        case "message":
            handleIncomingMessage(data);
            break;
        case "status_update":
            updateMessageStatus(data.message_id, data.status);
            break;
        case "user_status":
            handleUserStatusChange(data);
            break;
        case "typing":
            handleTypingIndicator(data);
            break;
        case "pong":
            console.log("💓 Pong received");
            break;
        default:
            console.warn("Unknown message type:", data.type);
    }
}

/**
 * Handle incoming chat message
 * @param {Object} data - Message data
 */
function handleIncomingMessage(data) {
    // Only display if message is relevant to current chat or from current user
    if (data.sender_id === currentReceiverId ||
        data.receiver_id === currentReceiverId ||
        data.sender_id === verifiedUserId) {

        displayMessage(data);

        // Send read receipt if receiving message in current open chat
        if (data.sender_id === currentReceiverId && data.receiver_id === verifiedUserId) {
            sendReadReceipt(data.id, data.sender_id);
        }
    }

    updateSidebarForNewMessage(data);
}

/**
 * Handle user online/offline status changes
 * @param {Object} data - Status change data
 */
function handleUserStatusChange(data) {
    console.log(`👤 User ${data.user_id} is now ${data.status}`);

    // Update chat header if viewing this user
    if (currentReceiverId === data.user_id) {
        const statusDiv = document.getElementById("header-status");
        if (statusDiv) {
            statusDiv.innerText = (data.status === "online") ? "Online" : "Offline";
            statusDiv.style.color = (data.status === "online") ? "#06d755" : "#999";
        }
    }

    // Update sidebar contact status indicator
    updateSidebarUserStatus(data.user_id, data.status);
}

/**
 * Handle typing indicator from other user
 * @param {Object} data - Typing indicator data
 */
function handleTypingIndicator(data) {
    // Only show if currently viewing this user's chat
    if (data.sender_id === currentReceiverId) {
        const statusDiv = document.getElementById("header-status");
        const typingDiv = document.getElementById("typing-indicator");

        if (statusDiv) statusDiv.style.display = "none";
        if (typingDiv) typingDiv.style.display = "block";

        // Clear previous timeout
        if (typingTimeout) clearTimeout(typingTimeout);

        // Hide typing indicator after 3 seconds of no activity
        typingTimeout = setTimeout(() => {
            if (typingDiv) typingDiv.style.display = "none";
            if (statusDiv) statusDiv.style.display = "block";
        }, TYPING_INDICATOR_TIMEOUT_MS);
    }
}

/**
 * Handle WebSocket errors
 * @param {Event} error - Error event
 */
function handleWebSocketError(error) {
    console.error("❌ WebSocket error:", error);
    isConnected = false;
}

/**
 * Handle WebSocket connection closed
 * @param {CloseEvent} event - Close event
 */
function handleWebSocketClose(event) {
    console.log("🔌 WebSocket closed:", event.code, event.reason);
    isConnected = false;
    stopPingInterval();

    // Attempt reconnection with exponential backoff
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);

        // Clear any existing reconnection timeout
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
        }

        reconnectTimeout = setTimeout(() => {
            connectWebSocket();
        }, delay);
    } else {
        console.error("💔 Max reconnection attempts reached");
        alert("Connection lost. Please refresh the page.");
    }
}

/**
 * Start heartbeat ping to keep connection alive
 */
function startPingInterval() {
    stopPingInterval(); // Clear any existing interval

    pingInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
        }
    }, PING_INTERVAL_MS);
}

/**
 * Stop heartbeat ping interval
 */
function stopPingInterval() {
    if (pingInterval) {
        clearInterval(pingInterval);
        pingInterval = null;
    }
}

// ========================================
// USER VERIFICATION & INITIALIZATION
// ========================================

/**
 * Verify current user with server before connecting WebSocket
 * @returns {Promise<boolean>} True if verification successful
 */
async function verifyCurrentUser() {
    try {
        const response = await fetch('/auth/verify');

        if (!response.ok) {
            console.error('❌ Not authenticated, redirecting to login');
            window.location.href = '/login';
            return false;
        }

        const userData = await response.json();

        // CRITICAL: Check if page user matches authenticated user
        if (currentUserId !== userData.id) {
            console.error(`🚨 USER MISMATCH DETECTED!`);
            console.error(`   Page rendered for: ${currentUserId} (${expectedUsername})`);
            console.error(`   Server authenticated: ${userData.id} (${userData.username})`);
            console.error(`   → Redirecting to get correct user page...`);

            // Redirect to /chat to get fresh page for authenticated user
            window.location.href = '/chat';
            return false;
        }

        // SUCCESS: Store verified user ID
        verifiedUserId = userData.id;
        sessionStorage.setItem('currentUserId', userData.id);
        sessionStorage.setItem('expectedUsername', userData.username);
        console.log(`✅ User verified: ${userData.username} (ID: ${userData.id})`);

        return true;

    } catch (error) {
        console.error('❌ Verification error:', error);
        alert('Session verification failed. Please login again.');
        window.location.href = '/login';
        return false;
    }
}

/**
 * Initialize chat application
 * Verifies user then connects WebSocket
 */
async function initializeChat() {
    console.log('🚀 Initializing chat...');

    const isValid = await verifyCurrentUser();

    if (isValid) {
        console.log('✅ Verification successful, connecting WebSocket...');
        connectWebSocket();
    } else {
        console.error('❌ User verification failed, WebSocket not initialized');
    }
}

// Start initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChat);
} else {
    initializeChat();
}

// ========================================
// USER SEARCH FUNCTIONALITY
// ========================================

/**
 * Search for users to start new chats
 * Debounced to avoid excessive API calls
 */
async function searchUsers() {
    const query = document.getElementById('searchInput').value.trim();
    const resultsDiv = document.getElementById('search-results');

    // Clear previous timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    // Hide results if query too short
    if (query.length < 2) {
        resultsDiv.style.display = 'none';
        return;
    }

    // Debounce search to avoid excessive requests
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/users/search?query=${encodeURIComponent(query)}`);

            if (!response.ok) {
                throw new Error(`Search failed: ${response.status}`);
            }

            const users = await response.json();

            resultsDiv.innerHTML = '';
            resultsDiv.style.display = 'block';

            if (users.length === 0) {
                resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #999;">No users found</div>';
                return;
            }

            users.forEach(user => {
                const searchItem = createSearchResultItem(user);
                resultsDiv.appendChild(searchItem);
            });
        } catch (error) {
            console.error("❌ Search error:", error);
            resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #f44;">Search failed</div>';
        }
    }, SEARCH_DEBOUNCE_MS);
}

/**
 * Create search result item element
 * @param {Object} user - User data
 * @returns {HTMLElement} Search result div
 */
function createSearchResultItem(user) {
    const div = document.createElement('div');
    div.className = 'search-item';

    const avatarUrl = getAvatarUrl(user.profile_pic, user.display_name);
    const statusColor = user.is_online ? '#06d755' : '#999';

    div.innerHTML = `
        <img src="${avatarUrl}" class="avatar" alt="${escapeHtml(user.display_name)}">
        <div style="flex: 1;">
            <div style="font-weight: 500;">${escapeHtml(user.display_name)}</div>
            <div style="font-size: 12px; color: #666;">@${escapeHtml(user.username)}</div>
        </div>
        <div class="status-indicator" style="background: ${statusColor};"></div>
    `;

    div.onclick = () => {
        openChat(user.id, user.display_name, user.profile_pic, user.is_online);
        resultsDiv.style.display = 'none';
        document.getElementById('searchInput').value = '';
    };

    return div;
}

// ========================================
// CONTACT STATUS MANAGEMENT
// ========================================

/**
 * Update online status for all visible contacts
 */
async function updateAllContactStatuses() {
    const contactItems = document.querySelectorAll('.contact-item');

    for (const item of contactItems) {
        const userId = parseInt(item.dataset.userId);
        if (userId) {
            try {
                const response = await fetch(`/user/status/${userId}`);
                const data = await response.json();
                updateSidebarUserStatus(userId, data.is_online ? "online" : "offline");
            } catch (error) {
                console.error(`Failed to fetch status for user ${userId}:`, error);
            }
        }
    }
}

/**
 * Update user status indicator in sidebar
 * @param {number} userId - User ID
 * @param {string} status - "online" or "offline"
 */
function updateSidebarUserStatus(userId, status) {
    const contactItem = document.querySelector(`.contact-item[data-user-id="${userId}"]`);
    if (contactItem) {
        const statusIndicator = contactItem.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.style.backgroundColor = status === 'online' ? '#06d755' : '#999';
        }
    }
}

// ========================================
// CHAT MANAGEMENT
// ========================================

/**
 * Open chat with a specific user
 * @param {number} id - User ID
 * @param {string} name - User display name
 * @param {string} pic - User profile picture URL
 * @param {boolean} isOnline - User online status
 */
async function openChat(id, name, pic, isOnline) {
    currentReceiverId = parseInt(id);

    // Update active state in sidebar
    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.userId == id) {
            item.classList.add('active');
        }
    });

    // Show chat UI elements
    document.getElementById("chat-header").style.display = "flex";
    document.getElementById("input-area").style.display = "flex";
    document.getElementById("header-name").innerText = name;

    // Update header avatar
    updateChatHeaderAvatar(pic, name);

    // Fetch real-time status from server
    try {
        const statusResponse = await fetch(`/user/status/${id}`);
        const statusData = await statusResponse.json();
        isOnline = statusData.is_online;
    } catch (error) {
        console.error("Failed to fetch user status:", error);
    }

    // Update status text
    const statusDiv = document.getElementById("header-status");
    statusDiv.innerText = isOnline ? "Online" : "Offline";
    statusDiv.style.color = isOnline ? "#06d755" : "#999";

    // Load language preference for this chat
    await loadLanguagePreference(id);

    // Load chat history
    await loadChatHistory(id);
}

/**
 * Update chat header avatar (image or default icon)
 * @param {string} pic - Profile picture URL
 * @param {string} name - Display name for fallback
 */
function updateChatHeaderAvatar(pic, name) {
    const imgEl = document.getElementById("header-pic");
    const defaultEl = document.getElementById("header-pic-default");

    // Check if profile picture is valid
    const isValidPic = pic &&
                       String(pic).trim() !== "" &&
                       String(pic) !== "null" &&
                       String(pic) !== "None" &&
                       String(pic).toLowerCase() !== "none" &&
                       !String(pic).includes("placeholder");

    if (isValidPic) {
        // Show real image
        if (imgEl) {
            imgEl.src = pic;
            imgEl.style.display = "block";
            imgEl.onerror = function() {
                // Fallback to default icon if image fails to load
                this.style.display = "none";
                if (defaultEl) defaultEl.style.display = "flex";
            };
        }
        if (defaultEl) defaultEl.style.display = "none";
    } else {
        // Show default icon
        if (imgEl) {
            imgEl.src = "";
            imgEl.style.display = "none";
        }
        if (defaultEl) defaultEl.style.display = "flex";
    }
}

/**
 * Load chat history for a specific friend
 * @param {number} friendId - Friend's user ID
 */
async function loadChatHistory(friendId) {
    const container = document.getElementById("messages");

    // Show loading state
    container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;"><i class="fas fa-spinner fa-spin"></i> Loading messages...</div>';

    try {
        const response = await fetch(`/chat/history/${friendId}`);

        if (!response.ok) {
            throw new Error(`Failed to load chat history: ${response.status}`);
        }

        const messages = await response.json();

        // Clear loading state
        container.innerHTML = "";

        // Display all messages
        messages.forEach(msg => {
            displayMessage(msg);

            // Send read receipt for unread received messages
            if (msg.receiver_id === verifiedUserId && msg.status !== 'read') {
                sendReadReceipt(msg.id, msg.sender_id);
            }
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error("❌ Error loading chat history:", error);
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44;">Failed to load messages. Please try again.</div>';
    }
}

// ========================================
// MESSAGE SENDING & DISPLAY
// ========================================

/**
 * Send a text message via WebSocket
 * Validates message before sending
 */
function sendMessage() {
    const input = document.getElementById("messageInput");
    const content = input.value.trim();

    // Validation checks
    if (!content) return;

    if (!currentReceiverId) {
        alert("Please select a contact first");
        return;
    }

    // Check message length
    if (content.length > MAX_MESSAGE_LENGTH) {
        alert(`Message too long! Maximum ${MAX_MESSAGE_LENGTH} characters allowed.`);
        return;
    }

    // Check WebSocket connection
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        alert("Connection lost. Reconnecting...");
        connectWebSocket();
        return;
    }

    // Send message
    const payload = {
        receiver_id: currentReceiverId,
        content: content
    };

    socket.send(JSON.stringify(payload));
    input.value = "";
}

/**
 * Display a message in the chat container
 * @param {Object} data - Message data
 */
function displayMessage(data) {
    const container = document.getElementById("messages");

    // Prevent duplicate messages
    if (document.getElementById(`msg-${data.id}`)) {
        return;
    }

    const div = document.createElement("div");
    const isMine = data.sender_id === verifiedUserId;

    div.className = `message ${isMine ? 'sent' : 'received'}${data.is_translated ? ' translated' : ''}`;
    div.id = `msg-${data.id}`;

    // Store translation data for toggle functionality
    if (data.is_translated) {
        div.setAttribute('data-original', data.original_content || '');
        div.setAttribute('data-translated', data.content || '');
        div.setAttribute('data-is-showing-original', 'false');
        div.style.cursor = 'pointer';
        div.onclick = function() {
            toggleTranslation(this);
        };
    }

    // Format timestamp
    const timestamp = new Date(data.timestamp);
    const timeStr = timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    // Create message content based on media type
    const contentHtml = createMessageContent(data);
    const ticksHtml = createMessageTicks(data, isMine, timeStr);

    div.innerHTML = `${contentHtml}${ticksHtml}`;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

/**
 * Create message content HTML based on media type
 * @param {Object} data - Message data
 * @returns {string} HTML content
 */
function createMessageContent(data) {
    if (data.media_type === "image" && data.media_url) {
        return `
            <div style="margin-bottom: 5px;">
                <img src="${data.media_url}" alt="Image"
                     style="max-width: 100%; width: 200px; border-radius: 8px; cursor: pointer; display: block;"
                     onclick="window.open('${data.media_url}', '_blank')">
            </div>
            ${data.content ? `<span class="msg-content">${escapeHtml(data.content)}</span>` : ''}
        `;
    }
    else if (data.media_type === "document" && data.media_url) {
        return `
            <div style="display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.05); padding: 10px; border-radius: 6px; margin-bottom: 5px;">
                <i class="fas fa-file-alt" style="font-size: 24px; color: #555;"></i>
                <div style="overflow: hidden;">
                    <a href="${data.media_url}" target="_blank" style="text-decoration: none; color: #333; font-weight: 500; font-size: 14px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px;">
                        ${escapeHtml(data.content || 'Download Attachment')}
                    </a>
                    <div style="font-size: 11px; color: #777;">Document</div>
                </div>
                <a href="${data.media_url}" download target="_blank" style="color: #777;"><i class="fas fa-download"></i></a>
            </div>
        `;
    }
    else {
        return `<span class="msg-content">${escapeHtml(data.content || "")}</span>`;
    }
}

/**
 * Create message metadata (timestamp and status ticks)
 * @param {Object} data - Message data
 * @param {boolean} isMine - Whether message is from current user
 * @param {string} timeStr - Formatted time string
 * @returns {string} HTML for ticks/metadata
 */
function createMessageTicks(data, isMine, timeStr) {
    if (isMine) {
        let tickClass = "tick-sent";
        let icon = "fa-check";

        if (data.status === "delivered") {
            tickClass = "tick-delivered";
            icon = "fa-check-double";
        } else if (data.status === "read") {
            tickClass = "tick-read";
            icon = "fa-check-double";
        }

        return `<span class="msg-meta">
            ${timeStr}
            <i class="fas ${icon} ${tickClass} tick-icon" id="tick-${data.id}"></i>
        </span>`;
    } else {
        const translationIcon = data.is_translated ?
            '<i class="fas fa-language" style="margin-right: 4px; opacity: 0.7;" title="Translated"></i>' : '';
        return `<span class="msg-meta">${translationIcon}${timeStr}</span>`;
    }
}

/**
 * Update message status ticks (sent/delivered/read)
 * @param {number} msgId - Message ID
 * @param {string} status - New status
 */
function updateMessageStatus(msgId, status) {
    const tickIcon = document.getElementById(`tick-${msgId}`);
    if (!tickIcon) return;

    if (status === 'delivered') {
        tickIcon.className = "fas fa-check-double tick-delivered tick-icon";
    } else if (status === 'read') {
        tickIcon.className = "fas fa-check-double tick-read tick-icon";
    }
}

// ========================================
// MESSAGE RECEIPTS
// ========================================

/**
 * Send read receipt to sender
 * @param {number} msgId - Message ID
 * @param {number} senderId - Sender's user ID
 */
function sendReadReceipt(msgId, senderId) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    socket.send(JSON.stringify({
        type: "read_receipt",
        message_id: msgId,
        sender_id: senderId
    }));
}

// ========================================
// FILE UPLOAD HANDLING
// ========================================

/**
 * Handle file upload with progress tracking
 * @param {HTMLInputElement} inputElement - File input element
 */
function handleFileUpload(inputElement) {
    const file = inputElement.files[0];
    if (!file) return;

    // Client-side size validation
    if (file.size > MAX_FILE_SIZE) {
        alert(`File is too large! Maximum allowed size is ${MAX_FILE_SIZE / 1024 / 1024}MB.`);
        inputElement.value = "";
        return;
    }

    // UI elements
    const progressContainer = document.getElementById("uploadProgress");
    const progressBar = document.getElementById("uploadProgressBar");
    const attachBtn = document.getElementById("attachBtn");

    // Show progress UI
    progressContainer.style.display = "block";
    progressBar.style.width = "0%";
    attachBtn.classList.add("btn-uploading");

    const formData = new FormData();
    formData.append("file", file);

    // Use XMLHttpRequest for progress tracking
    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBar.style.width = percentComplete + "%";
        }
    };

    // Handle successful upload
    xhr.onload = function() {
        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);

            // Send message with uploaded file URL
            if (socket && socket.readyState === WebSocket.OPEN) {
                const payload = {
                    receiver_id: currentReceiverId,
                    content: "",
                    media_url: data.url,
                    media_type: data.type
                };
                socket.send(JSON.stringify(payload));
            }
        } else {
            // Handle HTTP errors
            try {
                const err = JSON.parse(xhr.responseText);
                alert(`Upload failed: ${err.detail}`);
            } catch (e) {
                alert("Upload failed. Server error.");
            }
        }
        cleanupUploadUI();
    };

    // Handle network errors
    xhr.onerror = function() {
        alert("Network error during upload.");
        cleanupUploadUI();
    };

    /**
     * Clean up upload UI after completion
     */
    function cleanupUploadUI() {
        setTimeout(() => {
            progressContainer.style.display = "none";
            progressBar.style.width = "0%";
            attachBtn.classList.remove("btn-uploading");
            inputElement.value = "";
        }, 500);
    }

    // Execute upload
    xhr.open("POST", "/chat/upload", true);
    xhr.send(formData);
}

// ========================================
// TRANSLATION FEATURES
// ========================================

/**
 * Set language preference for current chat
 * @param {string} language - Language code (e.g., 'en', 'hi', 'es')
 */
async function setLanguagePreference(language) {
    if (!currentReceiverId) {
        console.error('No chat selected');
        return;
    }

    try {
        const response = await fetch('/chat/language-preference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                friend_id: currentReceiverId,
                language: language
            })
        });

        if (response.ok) {
            const data = await response.json();
            currentChatLanguage = language;
            console.log(`✅ Language set to: ${language}`);

            // Visual feedback
            const selector = document.getElementById('languageSelector');
            if (selector) {
                selector.style.borderColor = '#06d755';
                setTimeout(() => {
                    selector.style.borderColor = '';
                }, 1000);
            }

            // Reload chat to show translations
            await loadChatHistory(currentReceiverId);
        } else {
            const error = await response.json();
            console.error('Failed to set language:', error);
            alert(`Failed to set language: ${error.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Network error setting language:', error);
        alert('Network error. Please try again.');
    }
}

/**
 * Load language preference for a specific chat
 * @param {number} friendId - Friend's user ID
 */
async function loadLanguagePreference(friendId) {
    try {
        const response = await fetch(`/chat/language-preference/${friendId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        currentChatLanguage = data.preferred_language || 'en';

        // Update and show language selector
        const selector = document.getElementById('languageSelector');
        if (selector) {
            // Clear existing options
            selector.innerHTML = '';

            // Populate with available languages
            const languages = data.available_languages || {
                'en': 'English',
                'hi': 'Hindi',
                'es': 'Spanish'
            };

            for (const [code, name] of Object.entries(languages)) {
                const option = document.createElement('option');
                option.value = code;
                option.textContent = `${getFlagEmoji(code)} ${name}`;
                if (code === currentChatLanguage) {
                    option.selected = true;
                }
                selector.appendChild(option);
            }

            selector.style.display = 'block';
        }

    } catch (error) {
        console.error('Failed to load language preference:', error);
        currentChatLanguage = 'en';

        // Still show selector with default options
        const selector = document.getElementById('languageSelector');
        if (selector) {
            selector.value = 'en';
            selector.style.display = 'block';
        }
    }
}

// Helper function to get flag emoji
function getFlagEmoji(languageCode) {
    const flags = {
        'en': '🇬🇧',
        'hi': '🇮🇳',
        'es': '🇪🇸',
        'fr': '🇫🇷',
        'de': '🇩🇪',
        'pt': '🇧🇷',
        'ar': '🇸🇦',
        'zh': '🇨🇳',
        'ja': '🇯🇵',
        'ko': '🇰🇷'
    };
    return flags[languageCode] || '🌐';
}

// Toggle between original and translated message
function toggleTranslation(messageDiv) {
    const isShowingOriginal = messageDiv.getAttribute('data-is-showing-original') === 'true';
    const original = messageDiv.getAttribute('data-original');
    const translated = messageDiv.getAttribute('data-translated');

    const contentSpan = messageDiv.querySelector('.msg-content');

    // Add flip animation
    messageDiv.style.animation = 'flipMessage 0.4s ease';

    setTimeout(() => {
        if (isShowingOriginal) {
            // Show translation
            contentSpan.textContent = translated;
            messageDiv.setAttribute('data-is-showing-original', 'false');
        } else {
            // Show original
            contentSpan.textContent = original;
            messageDiv.setAttribute('data-is-showing-original', 'true');
        }
        messageDiv.style.animation = '';
    }, 200);

    // Better: Use transitioned event
    messageDiv.addEventListener('animationend', function handler() {
        messageDiv.style.animation = '';
        messageDiv.removeEventListener('animationend', handler); // Clean up!
    }, { once: true });
}
