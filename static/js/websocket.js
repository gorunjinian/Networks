// WebSocket connection for file transfer progress updates
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadForm = document.getElementById('upload-form');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressSpeed = document.getElementById('progress-speed');

    // Only proceed if we're on a page with the upload form
    if (!uploadForm) return;

    // Get the user ID from a data attribute
    const userId = uploadForm.dataset.userId;
    if (!userId) return;

    // Connect to WebSocket
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsScheme}://${window.location.host}/ws/progress/${userId}/`;
    let websocket = new WebSocket(wsUrl);

    // Connection opened
    websocket.onopen = function(e) {
        console.log("WebSocket connection established");
    };

    // Listen for messages
    websocket.onmessage = function(e) {
        const data = JSON.parse(e.data);

        if (data.type === 'progress_update') {
            // Show progress container if hidden
            progressContainer.style.display = 'block';

            // Update progress bar
            const progress = data.progress;
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            progressBar.textContent = `${progress}%`;

            // Update status and speed
            progressStatus.textContent = `${data.action} ${data.filename}...`;
            progressSpeed.textContent = data.speed;

            // If complete, hide after a delay
            if (progress === 100) {
                setTimeout(function() {
                    progressContainer.style.display = 'none';
                    // Reload the page to show the new file
                    window.location.reload();
                }, 2000);
            }
        }
    };

    // Connection closed
    websocket.onclose = function(e) {
        console.log("WebSocket connection closed", e.code, e.reason);

        // Try to reconnect if it was not a normal closure
        if (e.code !== 1000) {
            console.log("Attempting to reconnect...");
            setTimeout(function() {
                // Create a new WebSocket connection
                const newWebsocket = new WebSocket(wsUrl);
                websocket = newWebsocket;
            }, 5000);  // Try to reconnect every 5 seconds
        }
    };

    // Connection error
    websocket.onerror = function(e) {
        console.error("WebSocket error:", e);
    };

    // Show progress when upload begins
    uploadForm.addEventListener('submit', function() {
        progressContainer.style.display = 'block';
        progressStatus.textContent = 'Preparing upload...';
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
    });

    // Send ping every 30 seconds to keep connection alive
    setInterval(function() {
        if (websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'ping',
                timestamp: Date.now()
            }));
        }
    }, 30000);
});