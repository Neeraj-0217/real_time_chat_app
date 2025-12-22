let socket = null;
let currentReceiverId = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let reconnectTimeout = null;
let pingInterval = null;
let isConnected = false;
let typingTimeout = null;
let lastTypingTime = 0;

// Connect to WebSocket with reconnection logic
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/${currentUserId}`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = function() {
        console.log("WebSocket connected");
        isConnected = true;
        reconnectAttempts = 0;
        
        // Start heartbeat ping
        startPingInterval();
        
        // If we were viewing a chat, reload it to update statuses
        if (currentReceiverId) {
            loadChatHistory(currentReceiverId);
        }
        
        // Request status updates for all visible contacts
        updateAllContactStatuses();
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === "message") {
            // Display message if it's for current chat or from current user
            if (data.sender_id === currentReceiverId || 
                data.receiver_id === currentReceiverId || 
                data.sender_id === currentUserId) {
                displayMessage(data);
                
                // If receiving a message in current chat, send read receipt
                if (data.sender_id === currentReceiverId && data.receiver_id === currentUserId) {
                    sendReadReceipt(data.id, data.sender_id);
                }
            }
            
            // Update sidebar to show new message indicator (optional enhancement)
            updateSidebarForNewMessage(data);
        } 
        else if (data.type === "status_update") {
            // Update message ticks
            updateMessageStatus(data.message_id, data.status);
        }
        else if (data.type === "user_status") {
            
            // Update header if viewing this user's chat
            if (currentReceiverId === data.user_id) {
                const statusDiv = document.getElementById("header-status");
                if (statusDiv) {
                    statusDiv.innerText = (data.status === "online") ? "Online" : "Offline";
                    statusDiv.style.color = (data.status === "online") ? "#06d755" : "#999";
                }
            }
            
            // Update sidebar contact status
            updateSidebarUserStatus(data.user_id, data.status);
        }
        else if (data.type === "typing") {
            // Only show if we are currently looking at this user's chat
            if (data.sender_id === currentReceiverId) {
                const statusDiv = document.getElementById("header-status");
                const typingDiv = document.getElementById("typing-indicator");
                
                // Hide "Online/Offline" and show "typing..."
                if (statusDiv) statusDiv.style.display = "none";
                if (typingDiv) typingDiv.style.display = "block";
                
                // Clear previous timeout (so it stays visible if they keep typing)
                if (typingTimeout) clearTimeout(typingTimeout);
                
                // Hide it after 3 seconds of silence
                typingTimeout = setTimeout(() => {
                    if (typingDiv) typingDiv.style.display = "none";
                    if (statusDiv) statusDiv.style.display = "block";
                }, 3000);
            }
        }
        else if (data.type === "pong") {
            // Heartbeat response received
            console.log("Pong received");
        }
    };

    socket.onerror = function(error) {
        console.error("❌ WebSocket error:", error);
        isConnected = false;
    };

    socket.onclose = function(event) {
        console.log("WebSocket closed:", event.code, event.reason);
        isConnected = false;
        stopPingInterval();
        
        // Attempt to reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
            
            reconnectTimeout = setTimeout(() => {
                connectWebSocket();
            }, delay);
        } else {
            console.error("Max reconnection attempts reached");
            alert("Connection lost. Please refresh the page.");
        }
    };
}

// Heartbeat to keep connection alive and detect dead connections
function startPingInterval() {
    stopPingInterval(); // Clear any existing interval
    
    pingInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
        }
    }, 30000); // Ping every 30 seconds
}

function stopPingInterval() {
    if (pingInterval) {
        clearInterval(pingInterval);
        pingInterval = null;
    }
}

// Initialize connection
connectWebSocket();

// --- SEARCH LOGIC ---
let searchTimeout = null;
async function searchUsers() {
    const query = document.getElementById('searchInput').value.trim();
    const resultsDiv = document.getElementById('search-results');
    
    // Clear previous timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    if (query.length < 2) {
        resultsDiv.style.display = 'none';
        return;
    }

    // Debounce search
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/users/search?query=${encodeURIComponent(query)}`);
            const users = await response.json();
            
            resultsDiv.innerHTML = '';
            resultsDiv.style.display = 'block';
            
            if (users.length === 0) {
                resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #999;">No users found</div>';
                return;
            }
            
            users.forEach(user => {
                const div = document.createElement('div');
                div.className = 'search-item';
                
                const statusColor = user.is_online ? '#06d755' : '#999';
                
                div.innerHTML = `
                    <img src="${user.profile_pic || 'https://via.placeholder.com/45'}" class="avatar">
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
                resultsDiv.appendChild(div);
            });
        } catch (error) {
            console.error("❌ Search error:", error);
        }
    }, 300);
}

// --- UPDATE ALL CONTACT STATUSES ---
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

// --- OPEN CHAT ---
async function openChat(id, name, pic, isOnline) {
    currentReceiverId = parseInt(id);
    
    // Update active state in sidebar
    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.userId == id) {
            item.classList.add('active');
        }
    });
    
    // Update Header
    document.getElementById("chat-header").style.display = "flex";
    document.getElementById("input-area").style.display = "flex";
    document.getElementById("header-name").innerText = name;
    document.getElementById("header-pic").src = pic || 'https://via.placeholder.com/45';
    
    // Fetch real-time status
    try {
        const statusResponse = await fetch(`/user/status/${id}`);
        const statusData = await statusResponse.json();
        isOnline = statusData.is_online;
    } catch (error) {
        console.error("Failed to fetch user status:", error);
    }
    
    const statusDiv = document.getElementById("header-status");
    statusDiv.innerText = isOnline ? "Online" : "Offline";
    statusDiv.style.color = isOnline ? "#06d755" : "#999";
    
    // Load chat history
    await loadChatHistory(id);
}

// --- LOAD CHAT HISTORY ---
async function loadChatHistory(friendId) {
    try {
        const response = await fetch(`/chat/history/${friendId}`);
        const messages = await response.json();
        
        const container = document.getElementById("messages");
        container.innerHTML = "";
        
        messages.forEach(msg => {
            displayMessage(msg);

            if (msg.receiver_id === currentUserId && msg.status !== 'read') {
                sendReadReceipt(msg.id, msg.sender_id);
            }
        });
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error("❌ Error loading chat history:", error);
    }
}

// --- SEND MESSAGE ---
function sendMessage() {
    const input = document.getElementById("messageInput");
    const content = input.value.trim();
    
    if (!content || !currentReceiverId) return;
    
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        alert("Connection lost. Reconnecting...");
        connectWebSocket();
        return;
    }

    const payload = {
        receiver_id: currentReceiverId,
        content: content
    };
    
    socket.send(JSON.stringify(payload));
    input.value = "";
}

// Initialize Event Listeners
document.addEventListener('DOMContentLoaded', function() {

    const msgInput = document.getElementById('messageInput');
    
    if (msgInput) {
        // 1. Send Message on ENTER key (Using 'keydown' is better)
        msgInput.addEventListener('keydown', function(e) {
            // Check for Enter key (and ensure Shift isn't held down)
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); 
                sendMessage();
            }
        });

        // 2. Send Typing Indicator
        msgInput.addEventListener('input', function() {
            if (!currentReceiverId) return;
            
            const now = Date.now();
            if (now - lastTypingTime > 2000) {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({
                        type: "typing",
                        receiver_id: currentReceiverId
                    }));
                    lastTypingTime = now;
                }
            }
        });
    }
});

// --- SEND DELIVERED RECEIPT ---
function sendDeliveredReceipt(msgId, senderId) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    
    socket.send(JSON.stringify({
        type: "delivered_receipt",
        message_id: msgId,
        sender_id: senderId
    }));
}

// --- SEND READ RECEIPT ---
function sendReadReceipt(msgId, senderId) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    
    socket.send(JSON.stringify({
        type: "read_receipt",
        message_id: msgId,
        sender_id: senderId
    }));
}

// --- RENDER MESSAGE ---
function displayMessage(data) {
    const container = document.getElementById("messages");
    
    // Check if message already exists (prevent duplicates)
    if (document.getElementById(`msg-${data.id}`)) {
        return;
    }
    
    const div = document.createElement("div");
    const isMine = data.sender_id === currentUserId;
    
    div.classList.add("message", isMine ? "sent" : "received");
    div.id = `msg-${data.id}`;

    // Format timestamp
    const timestamp = new Date(data.timestamp);
    const timeStr = timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    // Ticks for sent messages
    let ticksHtml = "";
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
        
        ticksHtml = `<span class="msg-meta">
            ${timeStr}
            <i class="fas ${icon} ${tickClass} tick-icon" id="tick-${data.id}"></i>
        </span>`;
    } else {
        ticksHtml = `<span class="msg-meta">${timeStr}</span>`;
    }


    // Generate Content HTML based on Media Type
    let contentHtml = "";

    if (data.media_type === "image") {
        // IMAGE PREVIEW
        contentHtml = `
            <div style="margin-bottom: 5px;">
                <img src="${data.media_url}" alt="Image" 
                     style="max-width: 100%; width: 200px; border-radius: 8px; cursor: pointer; display: block;" 
                     onclick="window.open('${data.media_url}', '_blank')">
            </div>
            ${data.content ? `<span>${escapeHtml(data.content)}</span>` : ''} 
        `;
    } 
    else if (data.media_type === "document") {
        // DOWNLOADABLE LINK (PDF/DOC)
        contentHtml = `
            <div style="display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.05); padding: 10px; border-radius: 6px; margin-bottom: 5px;">
                <i class="fas fa-file-alt" style="font-size: 24px; color: #555;"></i>
                <div style="overflow: hidden;">
                    <a href="${data.media_url}" target="_blank" style="text-decoration: none; color: #333; font-weight: 500; font-size: 14px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px;">
                        Download Attachment
                    </a>
                    <div style="font-size: 11px; color: #777;">Document</div>
                </div>
                <a href="${data.media_url}" download target="_blank" style="color: #777;"><i class="fas fa-download"></i></a>
            </div>
            ${data.content ? `<span>${escapeHtml(data.content)}</span>` : ''}
        `;
    } 
    else {
        // STANDARD TEXT
        contentHtml = `<span class="msg-content">${escapeHtml(data.content || "")}</span>`;
    }

    // Combine with Ticks
    div.innerHTML = `${contentHtml}${ticksHtml}`;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// --- UPDATE MESSAGE STATUS (TICKS) ---
function updateMessageStatus(msgId, status) {
    const tickIcon = document.getElementById(`tick-${msgId}`);
    if (!tickIcon) return;
    
    if (status === 'delivered') {
        tickIcon.className = "fas fa-check-double tick-delivered tick-icon";
    } else if (status === 'read') {
        tickIcon.className = "fas fa-check-double tick-read tick-icon";
    }
}

// --- UPDATE SIDEBAR USER STATUS ---
function updateSidebarUserStatus(userId, status) {
    const contactItem = document.querySelector(`.contact-item[data-user-id="${userId}"]`);
    if (contactItem) {
        const statusIndicator = contactItem.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.style.backgroundColor = status === 'online' ? '#06d755' : '#999';
        }
    }
}

// --- UPDATE SIDEBAR FOR NEW MESSAGE ---
function updateSidebarForNewMessage(data) {
    // Add visual indicator for new messages (optional enhancement)
   
}

// --- UTILITY: ESCAPE HTML ---
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
    stopPingInterval();
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
    }
});

// Periodically refresh contact statuses (every 30 seconds)
setInterval(() => {
    if (isConnected) {
        updateAllContactStatuses();
    }
}, 30000);

// --- HANDLE FILE UPLOAD WITH PROGRESS ---
function handleFileUpload(inputElement) {
    const file = inputElement.files[0];
    if (!file) return;

    // 1. Client-Side Size Validation (Instant Fail)
    const MAX_SIZE = 5 * 1024 * 1024; // 5MB
    if (file.size > MAX_SIZE) {
        alert("File is too large. Maximum allowed size is 5MB.");
        inputElement.value = ""; // Reset
        return;
    }

    // UI Elements
    const progressContainer = document.getElementById("uploadProgress");
    const progressBar = document.getElementById("uploadProgressBar");
    const attachBtn = document.getElementById("attachBtn");
    
    // Reset UI
    progressContainer.style.display = "block";
    progressBar.style.width = "0%";
    attachBtn.classList.add("btn-uploading");

    const formData = new FormData();
    formData.append("file", file);

    // 2. Use XMLHttpRequest for Progress Tracking
    const xhr = new XMLHttpRequest();
    
    // Progress Event
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBar.style.width = percentComplete + "%";
        }
    };

    // Success/Load Event
    xhr.onload = function() {
        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            
            // Send WebSocket Message with URL
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
            // Handle HTTP Errors
            try {
                const err = JSON.parse(xhr.responseText);
                alert(`Upload failed: ${err.detail}`);
            } catch (e) {
                alert("Upload failed. Server error.");
            }
        }
        cleanupUI();
    };

    // Error Event
    xhr.onerror = function() {
        alert("Network error during upload.");
        cleanupUI();
    };

    // Cleanup Helper
    function cleanupUI() {
        // Hide progress bar after a short delay (for visual smoothness)
        setTimeout(() => {
            progressContainer.style.display = "none";
            progressBar.style.width = "0%";
            attachBtn.classList.remove("btn-uploading");
            inputElement.value = ""; // Allow re-uploading same file
        }, 500);
    }

    // Execute
    xhr.open("POST", "/chat/upload", true);
    xhr.send(formData);
}
