/**
 * Frontend JavaScript for YOLOv8 Video Processing Dashboard
 * Handles real-time communication with the backend via WebSocket
 */

// Global variables
let socket;
let isProcessing = false;
let currentMode = null;
let recentDetections = [];
let lastFrameUpdate = 0;
let lastDetectionUpdate = 0;
let detectionCounts = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize Socket.IO connection
    initializeSocket();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    loadCameras();
    loadConfig();
    
    // Update UI
    updateUI();
}

function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
    });
    
    socket.on('frame_update', function(data) {
        // Close processing modal if it's open
        closeProcessingModal();
        
        // Throttle frame updates to prevent flashing
        if (Date.now() - lastFrameUpdate > 100) { // Update max every 100ms (10 FPS)
            updateVideoFeeds(data);
            lastFrameUpdate = Date.now();
        }
    });
    
    socket.on('detection_update', function(data) {
        // Throttle detection updates to prevent flashing
        if (Date.now() - lastDetectionUpdate > 500) { // Update max every 500ms
            updateDetections(data);
            lastDetectionUpdate = Date.now();
        }
    });
    
    socket.on('stats_update', function(data) {
        updateStatistics(data);
    });
    
    socket.on('processing_error', function(data) {
        showError(data.error);
    });
    
    socket.on('status', function(data) {
        console.log('Status:', data.message);
    });
}

function setupEventListeners() {
    // Mode selection
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            toggleModeControls(this.value);
        });
    });
    
    // Confidence slider
    const confidenceSlider = document.getElementById('confidence-slider');
    confidenceSlider.addEventListener('input', function() {
        document.getElementById('confidence-value').textContent = this.value;
    });
    
    // Video upload
    const videoUpload = document.getElementById('video-upload');
    videoUpload.addEventListener('change', function() {
        if (this.files.length > 0) {
            console.log('Video file selected:', this.files[0].name);
        }
    });
}

function toggleModeControls(mode) {
    const cameraControls = document.getElementById('camera-controls');
    const uploadControls = document.getElementById('upload-controls');
    
    if (mode === 'camera') {
        cameraControls.style.display = 'block';
        uploadControls.style.display = 'none';
    } else if (mode === 'upload') {
        cameraControls.style.display = 'none';
        uploadControls.style.display = 'block';
    }
}

async function loadCameras() {
    try {
        const response = await fetch('/api/cameras');
        const data = await response.json();
        
        if (data.cameras) {
            updateCameraSelect(data.cameras);
        } else {
            console.error('Error loading cameras:', data.error);
        }
    } catch (error) {
        console.error('Error loading cameras:', error);
    }
}

function updateCameraSelect(cameras) {
    const select = document.getElementById('camera-select');
    select.innerHTML = '';
    
    if (cameras.length === 0) {
        select.innerHTML = '<option value="">No cameras found</option>';
        return;
    }
    
    cameras.forEach(camera => {
        const option = document.createElement('option');
        option.value = camera.id;
        option.textContent = `Camera ${camera.id} (${camera.properties.width}x${camera.properties.height})`;
        select.appendChild(option);
    });
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.confidence_threshold) {
            document.getElementById('confidence-slider').value = data.confidence_threshold;
            document.getElementById('confidence-value').textContent = data.confidence_threshold;
        }
        
        if (data.enable_tracking !== undefined) {
            document.getElementById('enable-tracking').checked = data.enable_tracking;
        }
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

async function startProcessing() {
    if (isProcessing) {
        return;
    }
    
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const confidence = parseFloat(document.getElementById('confidence-slider').value);
    const enableTracking = document.getElementById('enable-tracking').checked;
    
    showLoadingModal();
    
    try {
        if (mode === 'camera') {
            await startCameraProcessing(confidence, enableTracking);
        } else if (mode === 'upload') {
            await startVideoUpload(confidence, enableTracking);
        }
    } catch (error) {
        console.error('Error starting processing:', error);
        showError('Failed to start processing: ' + error.message);
    } finally {
        hideLoadingModal();
    }
}

function closeProcessingModal() {
    const processingModal = document.getElementById('loadingModal');
    if (processingModal) {
        const modal = bootstrap.Modal.getInstance(processingModal);
        if (modal) {
            modal.hide();
        }
    }
}

async function startCameraProcessing(confidence, enableTracking) {
    const cameraIndex = parseInt(document.getElementById('camera-select').value);
    
    if (isNaN(cameraIndex)) {
        throw new Error('Please select a camera');
    }
    
    const response = await fetch('/api/start_camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            camera_index: cameraIndex,
            confidence: confidence,
            enable_tracking: enableTracking
        })
    });
    
    const data = await response.json();
    
    if (data.status === 'started') {
        isProcessing = true;
        currentMode = 'camera';
        updateProcessingStatus(true);
        updateUI();
    } else {
        throw new Error(data.error || 'Failed to start camera processing');
    }
}

async function startVideoUpload(confidence, enableTracking) {
    const fileInput = document.getElementById('video-upload');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        throw new Error('Please select a video file');
    }
    
    const formData = new FormData();
    formData.append('video', fileInput.files[0]);
    formData.append('confidence', confidence);
    formData.append('enable_tracking', enableTracking);
    
    const response = await fetch('/api/upload_video', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    if (data.status === 'started') {
        isProcessing = true;
        currentMode = 'upload';
        updateProcessingStatus(true);
        updateUI();
    } else {
        throw new Error(data.error || 'Failed to start video processing');
    }
}

async function stopProcessing() {
    if (!isProcessing) {
        return;
    }
    
    try {
        const response = await fetch('/api/stop_processing', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'stopped') {
            isProcessing = false;
            currentMode = null;
            updateProcessingStatus(false);
            updateUI();
        }
    } catch (error) {
        console.error('Error stopping processing:', error);
        showError('Failed to stop processing: ' + error.message);
    }
}

function updateVideoFeeds(data) {
    // Update raw video feed
    if (data.raw_frame) {
        const rawPlaceholder = document.getElementById('raw-video-placeholder');
        const rawVideoFeed = document.getElementById('raw-video-feed');
        
        rawPlaceholder.style.display = 'none';
        rawVideoFeed.style.display = 'block';
        rawVideoFeed.src = 'data:image/jpeg;base64,' + data.raw_frame;
    }
    
    // Update processed video feed
    if (data.processed_frame) {
        const processedPlaceholder = document.getElementById('processed-video-placeholder');
        const processedVideoFeed = document.getElementById('processed-video-feed');
        
        processedPlaceholder.style.display = 'none';
        processedVideoFeed.style.display = 'block';
        processedVideoFeed.src = 'data:image/jpeg;base64,' + data.processed_frame;
    }
    
    // Update frame counter
    if (data.frame_number) {
        document.getElementById('current-frame').textContent = data.frame_number;
    }
}

function updateDetections(data) {
    // Add to recent detections
    recentDetections.unshift({
        timestamp: data.timestamp,
        frameNumber: data.frame_number,
        detections: data.detections
    });
    
    // Keep only last 50 detections
    if (recentDetections.length > 50) {
        recentDetections = recentDetections.slice(0, 50);
    }
    
    // Update detection counts
    data.detections.forEach(detection => {
        const className = detection.class_name;
        detectionCounts[className] = (detectionCounts[className] || 0) + 1;
    });
    
    // Update UI
    updateRecentDetections();
    updateDetectionCounts();
}

function updateRecentDetections() {
    const container = document.getElementById('recent-detections');
    
    if (recentDetections.length === 0) {
        container.innerHTML = '<div class="text-muted">No recent detections</div>';
        return;
    }
    
    const html = recentDetections.slice(0, 10).map(detection => {
        const time = new Date(detection.timestamp).toLocaleTimeString();
        const objects = detection.detections.map(d => 
            `<span class="detection-object">
                ${d.class_name} 
                <span class="confidence">(${(d.confidence * 100).toFixed(0)}%)</span>
            </span>`
        ).join(' ');
        
        return `
            <div class="detection-entry new">
                <div class="detection-header">
                    <strong>Frame ${detection.frameNumber}</strong>
                    <span class="detection-time">${time}</span>
                </div>
                <div class="detection-objects">${objects}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function updateDetectionCounts() {
    const container = document.getElementById('detection-counts');
    
    if (Object.keys(detectionCounts).length === 0) {
        container.innerHTML = '<div class="text-muted">No detections yet</div>';
        return;
    }
    
    const html = Object.entries(detectionCounts)
        .sort((a, b) => b[1] - a[1])
        .map(([className, count]) => `
            <div class="detection-item">
                <span class="detection-class">${className}</span>
                <span class="detection-count">${count}</span>
            </div>
        `).join('');
    
    container.innerHTML = html;
}

function updateStatistics(stats) {
    document.getElementById('total-frames').textContent = stats.total_frames || 0;
    document.getElementById('total-detections').textContent = stats.total_detections || 0;
    document.getElementById('fps').textContent = (stats.fps || 0).toFixed(1);
    document.getElementById('active-tracks').textContent = stats.active_tracks || 0;
    document.getElementById('processing-time').textContent = formatTime(stats.processing_time || 0);
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    if (connected) {
        status.className = 'badge bg-success me-2';
        status.innerHTML = '<i class="fas fa-circle"></i> Connected';
    } else {
        status.className = 'badge bg-danger me-2 disconnected';
        status.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
    }
}

function updateProcessingStatus(processing) {
    const status = document.getElementById('processing-status');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    if (processing) {
        status.className = 'badge bg-success processing';
        status.innerHTML = '<i class="fas fa-play"></i> Processing';
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        status.className = 'badge bg-warning stopped';
        status.innerHTML = '<i class="fas fa-pause"></i> Stopped';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

function updateUI() {
    document.getElementById('current-mode').textContent = currentMode || 'None';
    
    // Disable/enable controls based on processing state
    const controls = document.querySelectorAll('#camera-select, #video-upload, #confidence-slider, #enable-tracking');
    controls.forEach(control => {
        control.disabled = isProcessing;
    });
}

function showLoadingModal() {
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
    
    // Auto-close modal after 3 seconds as backup
    setTimeout(() => {
        closeProcessingModal();
    }, 3000);
}

function hideLoadingModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
    if (modal) {
        modal.hide();
    }
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    const modal = new bootstrap.Modal(document.getElementById('errorModal'));
    modal.show();
}

function formatTime(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

// Request stats update every 5 seconds
setInterval(() => {
    if (socket && socket.connected) {
        socket.emit('request_stats');
    }
}, 5000);

// Auto-refresh connection status
setInterval(() => {
    if (socket && !socket.connected) {
        console.log('Attempting to reconnect...');
        socket.connect();
    }
}, 10000);
