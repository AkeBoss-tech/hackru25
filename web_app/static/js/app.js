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
let timelineEvents = [];
let timelineStats = {
    totalEvents: 0,
    newObjects: 0,
    snapshots: 0
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    
    // Add keyboard support for fullscreen
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && document.fullscreenElement) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
    });
});

function initializeApp() {
    // Initialize Socket.IO connection
    initializeSocket();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    loadCameras();
    loadConfig();
    loadTimelineEvents();
    loadGeminiStatus();
    
    // Auto-start processing after a short delay
    setTimeout(() => {
        console.log('Auto-starting video processing...');
        startProcessing();
    }, 2000);
    
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
        
        // Throttle frame updates to prevent flashing (less aggressive)
        if (Date.now() - lastFrameUpdate > 50) { // Update max every 50ms (20 FPS)
            updateVideoFeeds(data);
            lastFrameUpdate = Date.now();
        }
        
        // Update timeline statistics if available
        if (data.timeline_stats) {
            updateStatistics(data.timeline_stats);
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
    
    socket.on('timeline_event', function(eventData) {
        addTimelineEvent(eventData);
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

function toggleFullscreen(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (!document.fullscreenElement) {
        // Enter fullscreen
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
        }
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
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
    
    // Update frame counter (less frequently)
    if (data.frame_number && data.frame_number % 10 === 0) {
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
    
    // Update timeline statistics
    if (stats.people_count !== undefined) {
        document.getElementById('people-count').textContent = stats.people_count || 0;
    }
    if (stats.cars_count !== undefined) {
        document.getElementById('vehicles-count').textContent = stats.cars_count || 0;
    }
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

// Timeline Functions
async function loadTimelineEvents() {
    try {
        const response = await fetch('/api/timeline/events?limit=25');
        const data = await response.json();
        
        if (data.events) {
            timelineEvents = data.events;
            renderTimelineEvents();
        }
        
        // Load timeline statistics
        await loadTimelineStatistics();
    } catch (error) {
        console.error('Error loading timeline events:', error);
    }
}

async function loadTimelineStatistics() {
    try {
        const response = await fetch('/api/timeline/statistics');
        const data = await response.json();
        
        if (data) {
            timelineStats = data;
            updateTimelineStats();
        }
    } catch (error) {
        console.error('Error loading timeline statistics:', error);
    }
}

function addTimelineEvent(eventData) {
    // Add to beginning of array (newest first)
    timelineEvents.unshift(eventData);
    
    // Keep only the most recent events (limit by UI setting)
    const limit = parseInt(document.getElementById('timeline-limit').value) || 25;
    if (timelineEvents.length > limit) {
        timelineEvents = timelineEvents.slice(0, limit);
    }
    
    // Update timeline stats
    timelineStats.totalEvents++;
    timelineStats.newObjects++;
    if (eventData.snapshot_path) {
        timelineStats.snapshots++;
    }
    
    // Render the timeline
    renderTimelineEvents();
    updateTimelineStats();
    
    // Auto-load Gemini report for new events after a short delay
    setTimeout(() => {
        loadGeminiReport(eventData.event_id);
    }, 2000); // Wait 2 seconds for Gemini report to be generated
}

function renderTimelineEvents() {
    const container = document.getElementById('timeline-events');
    
    if (timelineEvents.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-history fa-2x mb-2"></i>
                <p>No timeline events yet</p>
                <small>Start processing to see new object detection events</small>
            </div>
        `;
        return;
    }
    
    const eventsHtml = timelineEvents.map(event => createTimelineEventHtml(event)).join('');
    container.innerHTML = eventsHtml;
}

function createTimelineEventHtml(event) {
    const timestamp = new Date(event.timestamp).toLocaleString();
    const source = event.video_source.replace('camera:', 'Camera ').replace('video:', 'Video: ');
    
    let objectsHtml = '';
    if (event.objects && event.objects.length > 0) {
        objectsHtml = event.objects.map(obj => 
            `<span class="timeline-event-object">
                ${obj.class_name} <span class="confidence">(${(obj.confidence * 100).toFixed(0)}%)</span>
            </span>`
        ).join('');
    }
    
    let snapshotHtml = '';
    if (event.snapshot_path) {
        snapshotHtml = `
            <div class="timeline-event-snapshot">
                <div class="snapshot-toggle mb-2">
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="toggleSnapshot('${event.event_id}', true)">
                        <i class="fas fa-eye"></i> Annotated
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="toggleSnapshot('${event.event_id}', false)">
                        <i class="fas fa-image"></i> Raw
                    </button>
                </div>
                <img id="snapshot-${event.event_id}" 
                     src="/api/timeline/snapshots/${encodeURIComponent(event.snapshot_path)}" 
                     alt="Event Snapshot" 
                     onclick="showSnapshotModal('${event.snapshot_path}', '${event.event_id}')">
            </div>
        `;
    }
    
    // Gemini report section
    const geminiReportHtml = `
        <div class="timeline-event-gemini" id="gemini-${event.event_id}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0 text-primary">
                    <i class="fas fa-robot"></i> AI Analysis
                </h6>
                <button class="btn btn-sm btn-outline-primary" onclick="loadGeminiReport('${event.event_id}')">
                    <i class="fas fa-sync"></i> Load Report
                </button>
            </div>
            <div class="gemini-report-content" id="gemini-content-${event.event_id}">
                <div class="text-muted small">
                    <i class="fas fa-spinner fa-spin"></i> Loading AI analysis...
                </div>
            </div>
        </div>
    `;
    
    return `
        <div class="timeline-event new" data-event-id="${event.event_id}">
            <div class="timeline-event-header">
                <span class="timeline-event-time">${timestamp}</span>
                <span class="timeline-event-id">${event.event_id}</span>
            </div>
            <div class="timeline-event-source">${source}</div>
            <div class="timeline-event-objects">${objectsHtml}</div>
            ${snapshotHtml}
            ${geminiReportHtml}
            <div class="timeline-event-meta">
                <span class="timeline-event-frame">Frame: ${event.frame_number}</span>
                <span class="timeline-event-confidence">
                    Avg Confidence: ${(event.confidence_scores.reduce((a, b) => a + b, 0) / event.confidence_scores.length * 100).toFixed(0)}%
                </span>
            </div>
        </div>
    `;
}

function updateTimelineStats() {
    document.getElementById('timeline-total-events').textContent = timelineStats.total_events || 0;
    document.getElementById('timeline-new-objects').textContent = timelineStats.new_object_events || 0;
    document.getElementById('timeline-snapshots').textContent = timelineStats.snapshots_captured || 0;
}

function refreshTimeline() {
    loadTimelineEvents();
}

function filterTimeline() {
    const filter = document.getElementById('timeline-filter').value;
    const limit = parseInt(document.getElementById('timeline-limit').value) || 25;
    
    // Reload with filter
    loadTimelineEventsWithFilter(filter, limit);
}

async function loadTimelineEventsWithFilter(filter, limit) {
    try {
        let url = `/api/timeline/events?limit=${limit}`;
        if (filter) {
            url += `&video_source=${encodeURIComponent(filter)}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.events) {
            timelineEvents = data.events;
            renderTimelineEvents();
        }
    } catch (error) {
        console.error('Error loading filtered timeline events:', error);
    }
}

async function clearTimeline() {
    if (!confirm('Are you sure you want to clear all timeline events?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/timeline/clear', {
            method: 'POST'
        });
        
        if (response.ok) {
            timelineEvents = [];
            timelineStats = {
                totalEvents: 0,
                newObjects: 0,
                snapshots: 0
            };
            renderTimelineEvents();
            updateTimelineStats();
            showSuccess('Timeline events cleared successfully');
        } else {
            throw new Error('Failed to clear timeline events');
        }
    } catch (error) {
        console.error('Error clearing timeline events:', error);
        showError('Failed to clear timeline events');
    }
}

function toggleSnapshot(eventId, showAnnotated) {
    const img = document.getElementById(`snapshot-${eventId}`);
    const event = timelineEvents.find(e => e.event_id === eventId);
    
    if (!event || !event.snapshot_path) return;
    
    let newSrc;
    if (showAnnotated) {
        newSrc = `/api/timeline/snapshots/${encodeURIComponent(event.snapshot_path)}`;
    } else {
        newSrc = `/api/timeline/snapshots/${encodeURIComponent(event.snapshot_path)}/raw`;
    }
    
    img.src = newSrc;
    
    // Update button states
    const buttons = img.parentElement.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.classList.remove('btn-primary', 'btn-secondary');
        btn.classList.add('btn-outline-primary', 'btn-outline-secondary');
    });
    
    if (showAnnotated) {
        buttons[0].classList.remove('btn-outline-primary');
        buttons[0].classList.add('btn-primary');
        buttons[1].classList.remove('btn-outline-secondary');
        buttons[1].classList.add('btn-secondary');
    } else {
        buttons[0].classList.remove('btn-outline-primary');
        buttons[0].classList.add('btn-secondary');
        buttons[1].classList.remove('btn-outline-secondary');
        buttons[1].classList.add('btn-primary');
    }
}

function showSnapshotModal(snapshotPath, eventId) {
    const event = timelineEvents.find(e => e.event_id === eventId);
    
    // Create modal HTML with toggle buttons
    const modalHtml = `
        <div class="modal fade timeline-modal" id="snapshotModal" tabindex="-1">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-camera"></i> Event Snapshot
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <button class="btn btn-sm btn-primary me-2" onclick="toggleModalSnapshot(true)">
                                <i class="fas fa-eye"></i> Annotated
                            </button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="toggleModalSnapshot(false)">
                                <i class="fas fa-image"></i> Raw
                            </button>
                        </div>
                        <img id="modalSnapshot" 
                             src="/api/timeline/snapshots/${encodeURIComponent(snapshotPath)}" 
                             alt="Event Snapshot" 
                             class="img-fluid">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if present
    const existingModal = document.getElementById('snapshotModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add new modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Store the snapshot path and event for the modal
    window.modalSnapshotPath = snapshotPath;
    window.modalEvent = event;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('snapshotModal'));
    modal.show();
    
    // Remove modal from DOM when hidden
    document.getElementById('snapshotModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
        window.modalSnapshotPath = null;
        window.modalEvent = null;
    });
}

function toggleModalSnapshot(showAnnotated) {
    const img = document.getElementById('modalSnapshot');
    const buttons = document.querySelectorAll('#snapshotModal .btn');
    
    if (!window.modalSnapshotPath) return;
    
    let newSrc;
    if (showAnnotated) {
        newSrc = `/api/timeline/snapshots/${encodeURIComponent(window.modalSnapshotPath)}`;
    } else {
        newSrc = `/api/timeline/snapshots/${encodeURIComponent(window.modalSnapshotPath)}/raw`;
    }
    
    img.src = newSrc;
    
    // Update button states
    buttons.forEach((btn, index) => {
        if (index < 2) { // Only the first two buttons are the toggle buttons
            btn.classList.remove('btn-primary', 'btn-secondary');
            btn.classList.add('btn-outline-primary', 'btn-outline-secondary');
        }
    });
    
    if (showAnnotated) {
        buttons[0].classList.remove('btn-outline-primary');
        buttons[0].classList.add('btn-primary');
        buttons[1].classList.remove('btn-outline-secondary');
        buttons[1].classList.add('btn-secondary');
    } else {
        buttons[0].classList.remove('btn-outline-primary');
        buttons[0].classList.add('btn-secondary');
        buttons[1].classList.remove('btn-outline-secondary');
        buttons[1].classList.add('btn-primary');
    }
}


function showSuccess(message) {
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.className = 'alert alert-success alert-dismissible fade show position-fixed';
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        <i class="fas fa-check-circle"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
}

// Gemini Report Functions
async function loadGeminiReport(eventId) {
    const contentDiv = document.getElementById(`gemini-content-${eventId}`);
    if (!contentDiv) return;
    
    try {
        // Show loading state
        contentDiv.innerHTML = `
            <div class="text-muted small">
                <i class="fas fa-spinner fa-spin"></i> Loading AI analysis...
            </div>
        `;
        
        const response = await fetch(`/api/gemini/reports/${eventId}`);
        const report = await response.json();
        
        if (response.ok && report) {
            displayGeminiReport(eventId, report);
        } else {
            // Report not available yet or error
            contentDiv.innerHTML = `
                <div class="text-muted small">
                    <i class="fas fa-clock"></i> AI analysis pending...
                    <br><small>Report may take a few seconds to generate</small>
                </div>
            `;
            
            // Retry after 3 seconds
            setTimeout(() => {
                loadGeminiReport(eventId);
            }, 3000);
        }
    } catch (error) {
        console.error('Error loading Gemini report:', error);
        contentDiv.innerHTML = `
            <div class="text-danger small">
                <i class="fas fa-exclamation-triangle"></i> Failed to load AI analysis
                <br><small>Click "Load Report" to retry</small>
            </div>
        `;
    }
}

function displayGeminiReport(eventId, report) {
    const contentDiv = document.getElementById(`gemini-content-${eventId}`);
    if (!contentDiv) return;
    
    let reportHtml = '';
    
    // Summary
    if (report.summary) {
        reportHtml += `
            <div class="gemini-report-section">
                <strong><i class="fas fa-file-text"></i> Summary:</strong>
                <p class="mb-2">${report.summary}</p>
            </div>
        `;
    }
    
    // Objects detected
    if (report.objects_detected && report.objects_detected.length > 0) {
        const objectsText = report.objects_detected.join(', ');
        reportHtml += `
            <div class="gemini-report-section">
                <strong><i class="fas fa-eye"></i> Objects:</strong>
                <span class="badge bg-info me-1">${objectsText}</span>
            </div>
        `;
    }
    
    // Object IDs
    if (report.object_ids && report.object_ids.length > 0) {
        const idsText = report.object_ids.join(', ');
        reportHtml += `
            <div class="gemini-report-section">
                <strong><i class="fas fa-tag"></i> Object IDs:</strong>
                <code>${idsText}</code>
            </div>
        `;
    }
    
    // Activity
    if (report.activity) {
        reportHtml += `
            <div class="gemini-report-section">
                <strong><i class="fas fa-running"></i> Activity:</strong>
                <span>${report.activity}</span>
            </div>
        `;
    }
    
    // Confidence
    if (report.confidence) {
        const confidenceClass = report.confidence === 'high' ? 'success' : 
                               report.confidence === 'medium' ? 'warning' : 'secondary';
        reportHtml += `
            <div class="gemini-report-section">
                <strong><i class="fas fa-chart-line"></i> Confidence:</strong>
                <span class="badge bg-${confidenceClass}">${report.confidence}</span>
            </div>
        `;
    }
    
    // Metadata
    if (report._metadata) {
        const timestamp = new Date(report._metadata.timestamp).toLocaleString();
        reportHtml += `
            <div class="gemini-report-section">
                <small class="text-muted">
                    <i class="fas fa-robot"></i> Generated by ${report._metadata.model_used}
                    <br><i class="fas fa-clock"></i> ${timestamp}
                </small>
            </div>
        `;
    }
    
    contentDiv.innerHTML = reportHtml || `
        <div class="text-muted small">
            <i class="fas fa-info-circle"></i> No AI analysis available
        </div>
    `;
}

// Auto-load Gemini reports for all timeline events when page loads
async function loadAllGeminiReports() {
    for (const event of timelineEvents) {
        setTimeout(() => {
            loadGeminiReport(event.event_id);
        }, Math.random() * 2000); // Stagger requests to avoid overwhelming the API
    }
}

// Override refreshTimeline to also load Gemini reports
const originalRefreshTimeline = refreshTimeline;
function refreshTimeline() {
    originalRefreshTimeline();
    // Auto-load Gemini reports after timeline loads
    setTimeout(() => {
        loadAllGeminiReports();
    }, 1000);
}

// Gemini Control Functions
function toggleGeminiReporting() {
    const checkbox = document.getElementById('enable-gemini');
    
    if (checkbox.checked) {
        enableGeminiFromEnv();
    } else {
        disableGeminiReporting();
    }
}

async function enableGeminiFromEnv() {
    try {
        // Enable Gemini using the API key from environment variables
        const response = await fetch('/api/gemini/enable', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: 'from_env' }) // Signal to use env var
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('Gemini AI reporting enabled successfully!', 'success');
            updateGeminiStatus(true, result.stats);
            
            // Auto-load existing Gemini reports
            setTimeout(() => {
                loadAllGeminiReports();
            }, 1000);
        } else {
            showToast(`Failed to enable Gemini: ${result.error}`, 'danger');
            // Uncheck the checkbox if enabling failed
            document.getElementById('enable-gemini').checked = false;
        }
    } catch (error) {
        console.error('Error enabling Gemini:', error);
        showToast('Error enabling Gemini reporting', 'danger');
        // Uncheck the checkbox if enabling failed
        document.getElementById('enable-gemini').checked = false;
    }
}

async function disableGeminiReporting() {
    try {
        const response = await fetch('/api/gemini/disable', {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Gemini AI reporting disabled', 'info');
            updateGeminiStatus(false);
        }
    } catch (error) {
        console.error('Error disabling Gemini:', error);
    }
}

function updateGeminiStatus(enabled, stats = null, customMessage = null) {
    const statusDiv = document.getElementById('gemini-status');
    
    if (enabled) {
        statusDiv.innerHTML = `
            <small class="text-success">
                <i class="fas fa-check-circle"></i> Gemini reporting enabled
                ${stats ? `<br><small>Reports: ${stats.successful_reports || 0} | Cost: $${(stats.total_cost_estimate || 0).toFixed(4)}</small>` : ''}
            </small>
        `;
    } else {
        const message = customMessage || 'Gemini reporting disabled';
        const icon = customMessage && customMessage.includes('API key found') ? 'fa-key' : 'fa-info-circle';
        const colorClass = customMessage && customMessage.includes('API key found') ? 'text-warning' : 'text-muted';
        
        statusDiv.innerHTML = `
            <small class="${colorClass}">
                <i class="fas ${icon}"></i> ${message}
            </small>
        `;
    }
}

// Load Gemini status on page load
async function loadGeminiStatus() {
    try {
        const response = await fetch('/api/gemini/stats');
        const stats = await response.json();
        
        if (stats.enabled) {
            document.getElementById('enable-gemini').checked = true;
            updateGeminiStatus(true, stats);
        } else {
            // Check if API key is available in environment
            try {
                const envResponse = await fetch('/api/gemini/check-env');
                const envData = await envResponse.json();
                if (envData.has_api_key) {
                    updateGeminiStatus(false, null, 'API key found in environment. Click to enable.');
                } else {
                    updateGeminiStatus(false, null, 'Add GEMINI_API_KEY to your .env file');
                }
            } catch (envError) {
                updateGeminiStatus(false, null, 'Add GEMINI_API_KEY to your .env file');
            }
        }
    } catch (error) {
        console.error('Error loading Gemini status:', error);
        updateGeminiStatus(false, null, 'Add GEMINI_API_KEY to your .env file');
    }
}
