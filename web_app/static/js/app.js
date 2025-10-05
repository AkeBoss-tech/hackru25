/**
 * Frontend JavaScript for Sentri
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

// Notification system variables
let notifications = [];
let notificationStats = {
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0
};
let soundEnabled = true;
let currentPopupNotification = null;

// Sex offender detection variables
let sexOffenderAlerts = [];
let sexOffenderDetectionActive = false;

// Family member management variables
let familyMembers = [];
let familyMemberDetections = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    requestNotificationPermission();
    
    // Add keyboard support for fullscreen and tab navigation
    document.addEventListener('keydown', function(e) {
        // Handle fullscreen escape
        if (e.key === 'Escape' && document.fullscreenElement) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
        
        // Handle tab navigation shortcuts (Ctrl/Cmd + number)
        if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '4') {
            e.preventDefault();
            const tabIndex = parseInt(e.key) - 1;
            const tabButtons = document.querySelectorAll('#mainTabs .nav-link');
            if (tabButtons[tabIndex]) {
                tabButtons[tabIndex].click();
            }
        }
    });
});

// ============================================================================
// AI Summary and Snapshot Management Functions
// ============================================================================

let aiSummaryAutoRefresh = false;
let aiSummaryInterval = null;
let snapshotViewMode = 'text'; // 'text' or 'images'

// Load AI Security Summary
async function loadAISummary() {
    try {
        const response = await fetch('/api/ai/summary');
        const data = await response.json();
        
        if (data) {
            updateAISummaryDisplay(data);
        } else {
            console.error('Error loading AI summary:', data.error);
        }
    } catch (error) {
        console.error('Error loading AI summary:', error);
        updateAISummaryDisplay({
            summary: 'Unable to load security summary',
            security_level: 'unknown',
            recent_events: []
        });
    }
}

// Update AI Summary Display
function updateAISummaryDisplay(data) {
    const container = document.getElementById('ai-summary-content');
    if (!container) return;
    
    const securityLevelClass = getSecurityLevelClass(data.security_level);
    const securityLevelIcon = getSecurityLevelIcon(data.security_level);
    
    let eventsHtml = '';
    if (data.recent_events && data.recent_events.length > 0) {
        eventsHtml = `
            <div class="mt-3">
                <h6 class="text-primary mb-2"><i class="fas fa-list"></i> Recent Security Events</h6>
                <div class="recent-events-list">
                    ${data.recent_events.slice(0, 5).map(event => `
                        <div class="security-event-item mb-2 p-2 border rounded">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <div class="fw-bold small">${new Date(event.timestamp).toLocaleString()}</div>
                                    <div class="small text-muted">${event.summary}</div>
                                    <div class="small">
                                        <span class="badge bg-info me-1">${event.source.replace('camera:', 'Camera ').replace('video:', 'Video: ')}</span>
                                        <span class="text-muted">${event.objects_detected.length} objects</span>
                                    </div>
                                </div>
                                <button class="btn btn-sm btn-outline-primary" onclick="viewSnapshotEvent('${event.event_id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    container.innerHTML = `
        <div class="ai-summary-content">
            <div class="d-flex align-items-center mb-3">
                <div class="security-level-indicator ${securityLevelClass} me-3">
                    <i class="fas ${securityLevelIcon} fa-2x"></i>
                </div>
                <div>
                    <h6 class="mb-1">Security Status: <span class="badge ${securityLevelClass}">${data.security_level.replace('_', ' ').toUpperCase()}</span></h6>
                    <small class="text-muted">Last updated: ${new Date(data.last_updated).toLocaleString()}</small>
                </div>
            </div>
            
            <div class="security-summary-text">
                <p class="mb-3">${data.summary}</p>
            </div>
            
            ${data.total_events ? `
                <div class="row text-center mb-3">
                    <div class="col-4">
                        <div class="stat-item">
                            <div class="stat-value text-primary">${data.total_events}</div>
                            <div class="stat-label">Total Events</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="stat-item">
                            <div class="stat-value text-success">${data.recent_events ? data.recent_events.length : 0}</div>
                            <div class="stat-label">Recent Events</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="stat-item">
                            <div class="stat-value text-info">${data.security_level === 'high_activity' ? 'HIGH' : data.security_level === 'elevated' ? 'MED' : 'LOW'}</div>
                            <div class="stat-label">Alert Level</div>
                        </div>
                    </div>
                </div>
            ` : ''}
            
            ${eventsHtml}
        </div>
    `;
}

// Get security level CSS class
function getSecurityLevelClass(level) {
    switch (level) {
        case 'high_activity': return 'text-danger';
        case 'elevated': return 'text-warning';
        case 'normal': return 'text-success';
        default: return 'text-muted';
    }
}

// Get security level icon
function getSecurityLevelIcon(level) {
    switch (level) {
        case 'high_activity': return 'fa-exclamation-triangle';
        case 'elevated': return 'fa-exclamation-circle';
        case 'normal': return 'fa-check-circle';
        default: return 'fa-question-circle';
    }
}

// Refresh AI Summary
function refreshAISummary() {
    loadAISummary();
}

// Toggle AI Summary Auto-Refresh
function toggleSummaryAutoRefresh() {
    const btn = document.getElementById('summary-auto-refresh-btn');
    const icon = btn.querySelector('i');
    
    if (aiSummaryAutoRefresh) {
        clearInterval(aiSummaryInterval);
        aiSummaryInterval = null;
        aiSummaryAutoRefresh = false;
        icon.className = 'fas fa-play';
        btn.title = 'Start Auto-Refresh';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-info');
    } else {
        aiSummaryInterval = setInterval(() => {
            loadAISummary();
        }, 30000); // 30 seconds
        aiSummaryAutoRefresh = true;
        icon.className = 'fas fa-pause';
        btn.title = 'Stop Auto-Refresh';
        btn.classList.remove('btn-outline-info');
        btn.classList.add('btn-success');
    }
}

// Load Recent Snapshots
async function loadRecentSnapshots() {
    try {
        const response = await fetch('/api/ai/summary');
        const data = await response.json();
        
        if (data && data.recent_events) {
            updateSnapshotsDisplay(data.recent_events);
        } else {
            updateSnapshotsDisplay([]);
        }
    } catch (error) {
        console.error('Error loading recent snapshots:', error);
        updateSnapshotsDisplay([]);
    }
}

// Update Snapshots Display
function updateSnapshotsDisplay(events) {
    const container = document.getElementById('recent-snapshots');
    if (!container) return;
    
    if (!events || events.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-camera fa-2x mb-2"></i>
                <p>No recent snapshots available</p>
                <small>Start processing to see security snapshots</small>
            </div>
        `;
        return;
    }
    
    const snapshotsHtml = events.slice(0, 8).map(event => {
        const timestamp = new Date(event.timestamp).toLocaleString();
        const objects = event.objects_detected.join(', ');
        
        return `
            <div class="snapshot-item mb-3 p-3 border rounded">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <div class="snapshot-description">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="mb-0">
                                    <i class="fas fa-camera text-primary"></i>
                                    Security Event ${event.event_id}
                                </h6>
                                <small class="text-muted">${timestamp}</small>
                            </div>
                            <p class="mb-2 text-muted">${event.summary}</p>
                            <div class="snapshot-meta">
                                <span class="badge bg-info me-2">${event.source.replace('camera:', 'Camera ').replace('video:', 'Video: ')}</span>
                                <span class="badge bg-secondary me-2">${event.objects_detected.length} objects</span>
                                <button class="btn btn-sm btn-outline-primary" onclick="viewSnapshotImage('${event.event_id}', '${event.snapshot_path}')">
                                    <i class="fas fa-image"></i> View Image
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 text-center" id="snapshot-image-${event.event_id}" style="display: none;">
                        <img src="/api/timeline/snapshots/${encodeURIComponent(event.snapshot_path)}" 
                             alt="Security Snapshot" 
                             class="img-fluid rounded snapshot-thumbnail"
                             style="max-height: 120px; cursor: pointer;"
                             onclick="showSnapshotModal('${event.snapshot_path}', '${event.event_id}')">
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = snapshotsHtml;
}

// Toggle Snapshot View Mode
function toggleSnapshotView() {
    const btn = document.getElementById('snapshot-view-toggle');
    const icon = btn.querySelector('i');
    
    if (snapshotViewMode === 'text') {
        // Switch to images
        snapshotViewMode = 'images';
        btn.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Images';
        btn.title = 'Hide Images';
        
        // Show all snapshot images
        document.querySelectorAll('[id^="snapshot-image-"]').forEach(el => {
            el.style.display = 'block';
        });
    } else {
        // Switch to text only
        snapshotViewMode = 'text';
        btn.innerHTML = '<i class="fas fa-eye"></i> Show Images';
        btn.title = 'Show Images';
        
        // Hide all snapshot images
        document.querySelectorAll('[id^="snapshot-image-"]').forEach(el => {
            el.style.display = 'none';
        });
    }
}

// View Snapshot Event (from AI summary)
function viewSnapshotEvent(eventId) {
    // Find the event in timeline events and show its details
    const event = timelineEvents.find(e => e.event_id === eventId);
    if (event && event.snapshot_path) {
        showSnapshotModal(event.snapshot_path, eventId);
    } else {
        showToast('Event details not available', 'warning');
    }
}

// View Snapshot Image (from snapshots section)
function viewSnapshotImage(eventId, snapshotPath) {
    showSnapshotModal(snapshotPath, eventId);
}

function initializeApp() {
    // Initialize Socket.IO connection
    initializeSocket();
    
    // Setup event listeners
    setupEventListeners();
    
    // Setup tab functionality
    setupTabFunctionality();
    
    // Load initial data
    loadCameras();
    loadConfig();
    loadTimelineEvents();
    loadGeminiStatus();
    loadNotifications();
    loadNotificationStats();
    loadDetectionClasses();
    loadDistributedStatus();
    loadRecentDetections();
    refreshStats();
    loadAISummary();
    loadRecentSnapshots();
    
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
    
    // Notification system event handlers
    socket.on('new_notification', function(notificationData) {
        handleNewNotification(notificationData);
    });
    
    // Sex offender detection event handlers
    socket.on('sex_offender_detection_update', function(data) {
        handleSexOffenderDetectionUpdate(data);
    });
    
    socket.on('sex_offender_alert', function(data) {
        console.log('Sex offender alert:', data);
        showNotification(`🚨 SEX OFFENDER ALERT: ${data.offender_info?.name || 'Unknown'}`, 'error');
    });
    
    socket.on('sex_offender_detection_status', function(data) {
        console.log('Sex offender detection status:', data);
        sexOffenderDetectionActive = data.is_running;
        updateSexOffenderDetectionStatus();
    });
    
    // Family member detection event handlers
    socket.on('family_member_detection', function(data) {
        handleFamilyMemberDetection(data);
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

function setupTabFunctionality() {
    // Get all tab buttons (both desktop and mobile)
    const desktopTabButtons = document.querySelectorAll('#mainTabs .nav-link');
    const mobileTabButtons = document.querySelectorAll('#mobileTabs .nav-link');
    
    // Add click event listeners to desktop tab buttons
    desktopTabButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            handleTabSwitch(this, '#mainTabs');
        });
    });
    
    // Add click event listeners to mobile tab buttons
    mobileTabButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            handleTabSwitch(this, '#mobileTabs');
        });
    });
    
    // Initialize with first tab active on both desktop and mobile
    if (desktopTabButtons.length > 0) {
        updateActiveTabIndicator(desktopTabButtons[0], '#mainTabs');
    }
    if (mobileTabButtons.length > 0) {
        updateActiveTabIndicator(mobileTabButtons[0], '#mobileTabs');
    }
}

function handleTabSwitch(clickedButton, tabContainer) {
    const targetTab = clickedButton.getAttribute('data-bs-target');
    
                // Add loading state for timeline and notifications tabs
                if (targetTab === '#timeline-panel') {
                    // Refresh timeline and recent detections when switching to timeline tab
                    setTimeout(() => {
                        refreshTimeline();
                        loadRecentDetections();
                    }, 100);
                } else if (targetTab === '#notifications-panel') {
        // Refresh notifications when switching to notifications tab
        setTimeout(() => {
            loadNotifications();
        }, 100);
    }
    
    // Update active tab indicator for both desktop and mobile
    updateActiveTabIndicator(clickedButton, tabContainer);
    
    // Sync the other tab container
    const otherContainer = tabContainer === '#mainTabs' ? '#mobileTabs' : '#mainTabs';
    syncTabContainers(targetTab, otherContainer);
}

function syncTabContainers(targetTab, otherContainer) {
    const otherButtons = document.querySelectorAll(`${otherContainer} .nav-link`);
    otherButtons.forEach(button => {
        if (button.getAttribute('data-bs-target') === targetTab) {
            updateActiveTabIndicator(button, otherContainer);
        }
    });
}

function updateActiveTabIndicator(activeButton, container) {
    // Remove active class from all tabs in the specified container
    document.querySelectorAll(`${container} .nav-link`).forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
    });
    
    // Add active class to clicked tab
    activeButton.classList.add('active');
    activeButton.setAttribute('aria-selected', 'true');
}

// Tab switching helper functions
function switchToTab(tabName) {
    const tabButton = document.querySelector(`#${tabName}-tab`);
    if (tabButton) {
        tabButton.click();
    }
}

function switchToVideoTab() {
    switchToTab('video');
}

function switchToSettingsTab() {
    switchToTab('settings');
}

function switchToTimelineTab() {
    switchToTab('timeline');
}

function switchToNotificationsTab() {
    switchToTab('notifications');
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
    
    // Get selected target classes
    const classSelect = document.getElementById('class-select');
    const targetClasses = classSelect.value ? classSelect.value.split(',') : null;
    
    const response = await fetch('/api/start_camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            camera_index: cameraIndex,
            confidence: confidence,
            enable_tracking: enableTracking,
            target_classes: targetClasses
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
    
    // Get selected target classes
    const classSelect = document.getElementById('class-select');
    const targetClasses = classSelect.value || '';
    
    const formData = new FormData();
    formData.append('video', fileInput.files[0]);
    formData.append('confidence', confidence);
    formData.append('enable_tracking', enableTracking);
    formData.append('target_classes', targetClasses);
    
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
    const desktopStatus = document.getElementById('connection-status');
    const mobileStatus = document.getElementById('connection-status-mobile');
    
    const statusElements = [desktopStatus, mobileStatus].filter(el => el);
    
    statusElements.forEach(status => {
        if (connected) {
            status.className = 'badge bg-success me-2';
            status.innerHTML = '<i class="fas fa-circle"></i> <span class="d-none d-sm-inline">Connected</span>';
        } else {
            status.className = 'badge bg-danger me-2 disconnected';
            status.innerHTML = '<i class="fas fa-circle"></i> <span class="d-none d-sm-inline">Disconnected</span>';
        }
    });
}

function updateProcessingStatus(processing) {
    const desktopStatus = document.getElementById('processing-status');
    const mobileStatus = document.getElementById('processing-status-mobile');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    const statusElements = [desktopStatus, mobileStatus].filter(el => el);
    
    statusElements.forEach(status => {
        if (processing) {
            status.className = 'badge bg-success processing';
            status.innerHTML = '<i class="fas fa-play"></i> <span class="d-none d-sm-inline">Processing</span>';
        } else {
            status.className = 'badge bg-warning stopped';
            status.innerHTML = '<i class="fas fa-pause"></i> <span class="d-none d-sm-inline">Stopped</span>';
        }
    });
    
    if (startBtn) startBtn.disabled = processing;
    if (stopBtn) stopBtn.disabled = !processing;
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
    renderFilteredTimelineEvents(timelineEvents);
}

function renderFilteredTimelineEvents(events) {
    const container = document.getElementById('timeline-events');
    
    if (!events || events.length === 0) {
        const hasFilters = document.getElementById('timeline-search').value || 
                          document.getElementById('timeline-filter').value || 
                          document.getElementById('timeline-object-filter').value;
        
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-history fa-2x mb-2"></i>
                <p>${hasFilters ? 'No events match your filters' : 'No timeline events yet'}</p>
                <small>${hasFilters ? 'Try adjusting your search or filter criteria' : 'Start processing to see new object detection events'}</small>
            </div>
        `;
        return;
    }
    
    const eventsHtml = events.map(event => createTimelineEventHtml(event)).join('');
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
    
    // Image HTML for horizontal layout
    let imageHtml = '';
    if (event.snapshot_path) {
        imageHtml = `
            <div class="timeline-event-image">
                <img id="snapshot-${event.event_id}" 
                     src="/api/timeline/snapshots/${encodeURIComponent(event.snapshot_path)}" 
                     alt="Event Snapshot" 
                     onclick="showSnapshotModal('${event.snapshot_path}', '${event.event_id}')">
            </div>
        `;
    } else {
        imageHtml = `
            <div class="timeline-event-image">
                <div class="d-flex align-items-center justify-content-center h-100 bg-light text-muted">
                    <i class="fas fa-image fa-2x"></i>
                </div>
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
            ${imageHtml}
            <div class="timeline-event-content">
                <div class="timeline-event-header">
                    <span class="timeline-event-time">${timestamp}</span>
                    <span class="timeline-event-id">${event.event_id}</span>
                </div>
                <div class="timeline-event-source">${source}</div>
                <div class="timeline-event-objects">${objectsHtml}</div>
                ${geminiReportHtml}
                <div class="timeline-event-meta">
                    <span class="timeline-event-frame">Frame: ${event.frame_number || 'N/A'}</span>
                    <span class="timeline-event-confidence">
                        Avg Confidence: ${event.confidence_scores && event.confidence_scores.length > 0 ? 
                            (event.confidence_scores.reduce((a, b) => a + b, 0) / event.confidence_scores.length * 100).toFixed(0) + '%' : 'N/A'}
                    </span>
                </div>
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
    applyTimelineFilters();
}

function searchTimeline() {
    applyTimelineFilters();
}

function clearTimelineFilters() {
    document.getElementById('timeline-search').value = '';
    document.getElementById('timeline-filter').value = '';
    document.getElementById('timeline-object-filter').value = '';
    applyTimelineFilters();
}

function applyTimelineFilters() {
    const searchTerm = document.getElementById('timeline-search').value.toLowerCase();
    const sourceFilter = document.getElementById('timeline-filter').value;
    const objectFilter = document.getElementById('timeline-object-filter').value;
    
    // Filter the existing timeline events
    const filteredEvents = timelineEvents.filter(event => {
        // Search filter
        const matchesSearch = !searchTerm || 
            event.event_id.toLowerCase().includes(searchTerm) ||
            event.video_source.toLowerCase().includes(searchTerm) ||
            (event.objects && event.objects.some(obj => obj.class_name.toLowerCase().includes(searchTerm))) ||
            event.timestamp.toLowerCase().includes(searchTerm);
        
        // Source filter
        const matchesSource = !sourceFilter || event.video_source === sourceFilter;
        
        // Object filter
        const matchesObject = !objectFilter || 
            (event.objects && event.objects.some(obj => obj.class_name === objectFilter));
        
        return matchesSearch && matchesSource && matchesObject;
    });
    
    // Render filtered events
    renderFilteredTimelineEvents(filteredEvents);
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
    
    // Create full-page modal HTML with improved layout
    const modalHtml = `
        <div class="modal fade snapshot-fullscreen-modal" id="snapshotModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-fullscreen">
                <div class="modal-content h-100">
                    <div class="modal-header bg-dark text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-camera"></i> Event Snapshot - ${eventId}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-0 h-100">
                        <div class="row h-100 g-0">
                            <!-- Image Section -->
                            <div class="col-lg-8 col-12 d-flex flex-column">
                                <div class="image-controls p-3 bg-light border-bottom">
                                    <div class="d-flex flex-wrap gap-2 align-items-center">
                                        <button class="btn btn-sm btn-primary" onclick="toggleModalSnapshot(true)">
                                            <i class="fas fa-eye"></i> <span class="d-none d-md-inline">Annotated</span>
                                        </button>
                                        <button class="btn btn-sm btn-outline-secondary" onclick="toggleModalSnapshot(false)">
                                            <i class="fas fa-image"></i> <span class="d-none d-md-inline">Raw</span>
                                        </button>
                                        <div class="ms-auto">
                                            <button class="btn btn-sm btn-outline-info" onclick="downloadSnapshot()">
                                                <i class="fas fa-download"></i> <span class="d-none d-md-inline">Download</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex-grow-1 d-flex align-items-center justify-content-center bg-dark">
                                    <img id="modalSnapshot" 
                                         src="/api/timeline/snapshots/${encodeURIComponent(snapshotPath)}" 
                                         alt="Event Snapshot" 
                                         class="snapshot-fullscreen-img">
                                </div>
                            </div>
                            
                            <!-- Details Section -->
                            <div class="col-lg-4 col-12 bg-light">
                                <div class="h-100 d-flex flex-column">
                                    <!-- Event Info -->
                                    <div class="p-3 border-bottom">
                                        <h6 class="mb-2">
                                            <i class="fas fa-info-circle"></i> Event Information
                                        </h6>
                                        <div class="small text-muted">
                                            <div class="mb-1"><strong>Event ID:</strong> ${eventId}</div>
                                            <div class="mb-1"><strong>Timestamp:</strong> ${event ? new Date(event.timestamp).toLocaleString() : 'N/A'}</div>
                                            <div class="mb-1"><strong>Frame:</strong> ${event ? event.frame_number : 'N/A'}</div>
                                            <div class="mb-1"><strong>Source:</strong> ${event ? event.video_source.replace('camera:', 'Camera ').replace('video:', 'Video: ') : 'N/A'}</div>
                                        </div>
                                    </div>
                                    
                                    <!-- Detected Objects -->
                                    <div class="p-3 border-bottom flex-grow-1">
                                        <h6 class="mb-2">
                                            <i class="fas fa-eye"></i> Detected Objects
                                        </h6>
                                        <div id="modalDetectedObjects" class="objects-list">
                                            ${event && event.objects ? event.objects.map(obj => 
                                                `<div class="object-tag mb-2">
                                                    <span class="badge bg-primary me-1">${obj.class_name}</span>
                                                    <span class="small text-muted">Confidence: ${(obj.confidence * 100).toFixed(1)}%</span>
                                                </div>`
                                            ).join('') : '<div class="text-muted small">No objects detected</div>'}
                                        </div>
                                    </div>
                                    
                                    <!-- AI Analysis -->
                                    <div class="p-3">
                                        <h6 class="mb-2">
                                            <i class="fas fa-robot"></i> AI Analysis
                                        </h6>
                                        <div id="modalGeminiAnalysis" class="gemini-analysis-content">
                                            <div class="text-muted small">
                                                <i class="fas fa-spinner fa-spin"></i> Loading AI analysis...
                                            </div>
                                        </div>
                                        <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadModalGeminiReport('${eventId}')">
                                            <i class="fas fa-sync"></i> Refresh Analysis
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
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
    
    // Load Gemini analysis for this event
    setTimeout(() => {
        loadModalGeminiReport(eventId);
    }, 500);
    
    // Remove modal from DOM when hidden
    document.getElementById('snapshotModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
        window.modalSnapshotPath = null;
        window.modalEvent = null;
    });
}

function toggleModalSnapshot(showAnnotated) {
    const img = document.getElementById('modalSnapshot');
    if (!window.modalSnapshotPath) return;
    
    let newSrc;
    if (showAnnotated) {
        newSrc = `/api/timeline/snapshots/${encodeURIComponent(window.modalSnapshotPath)}`;
    } else {
        newSrc = `/api/timeline/snapshots/${encodeURIComponent(window.modalSnapshotPath)}/raw`;
    }
    
    img.src = newSrc;
    
    // Update button states
    const annotatedBtn = document.querySelector('#snapshotModal button[onclick="toggleModalSnapshot(true)"]');
    const rawBtn = document.querySelector('#snapshotModal button[onclick="toggleModalSnapshot(false)"]');
    
    if (showAnnotated) {
        annotatedBtn.classList.remove('btn-outline-primary');
        annotatedBtn.classList.add('btn-primary');
        rawBtn.classList.remove('btn-secondary');
        rawBtn.classList.add('btn-outline-secondary');
    } else {
        annotatedBtn.classList.remove('btn-primary');
        annotatedBtn.classList.add('btn-outline-primary');
        rawBtn.classList.remove('btn-outline-secondary');
        rawBtn.classList.add('btn-secondary');
    }
}

function downloadSnapshot() {
    if (!window.modalSnapshotPath) return;
    
    const link = document.createElement('a');
    link.href = `/api/timeline/snapshots/${encodeURIComponent(window.modalSnapshotPath)}`;
    link.download = `snapshot_${window.modalEvent?.event_id || 'unknown'}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function loadModalGeminiReport(eventId) {
    const contentDiv = document.getElementById('modalGeminiAnalysis');
    if (!contentDiv) return;
    
    try {
        // Show loading state
        contentDiv.innerHTML = `
            <div class="text-muted small">
                <i class="fas fa-spinner fa-spin"></i> Loading AI analysis...
            </div>
        `;
        
        fetch(`/api/gemini/reports/${eventId}`)
            .then(response => response.json())
            .then(report => {
                if (report && !report.error) {
                    displayModalGeminiReport(report);
                } else {
                    contentDiv.innerHTML = `
                        <div class="text-muted small">
                            <i class="fas fa-clock"></i> AI analysis pending...
                            <br><small>Report may take a few seconds to generate</small>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading Gemini report:', error);
                contentDiv.innerHTML = `
                    <div class="text-danger small">
                        <i class="fas fa-exclamation-triangle"></i> Failed to load AI analysis
                        <br><small>Click "Refresh Analysis" to retry</small>
                    </div>
                `;
            });
    } catch (error) {
        console.error('Error loading Gemini report:', error);
    }
}

function displayModalGeminiReport(report) {
    const contentDiv = document.getElementById('modalGeminiAnalysis');
    if (!contentDiv) return;
    
    let reportHtml = '';
    
    // Summary
    if (report.summary) {
        reportHtml += `
            <div class="mb-3">
                <strong class="small">Summary:</strong>
                <p class="small mb-1">${report.summary}</p>
            </div>
        `;
    }
    
    // Objects detected
    if (report.objects_detected && report.objects_detected.length > 0) {
        const objectsText = report.objects_detected.join(', ');
        reportHtml += `
            <div class="mb-3">
                <strong class="small">Objects:</strong>
                <div class="small">${objectsText}</div>
            </div>
        `;
    }
    
    // Activity
    if (report.activity) {
        reportHtml += `
            <div class="mb-3">
                <strong class="small">Activity:</strong>
                <div class="small">${report.activity}</div>
            </div>
        `;
    }
    
    // Confidence
    if (report.confidence) {
        const confidenceClass = report.confidence === 'high' ? 'success' : 
                               report.confidence === 'medium' ? 'warning' : 'secondary';
        reportHtml += `
            <div class="mb-3">
                <strong class="small">Confidence:</strong>
                <span class="badge bg-${confidenceClass} small">${report.confidence}</span>
            </div>
        `;
    }
    
    contentDiv.innerHTML = reportHtml || `
        <div class="text-muted small">
            <i class="fas fa-info-circle"></i> No AI analysis available
        </div>
    `;
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

// Load detection classes
async function loadDetectionClasses() {
    try {
        const response = await fetch('/api/classes');
        const data = await response.json();
        
        if (data.class_sets) {
            updateClassSelect(data.class_sets, data.default);
        } else {
            console.error('Error loading detection classes:', data.error);
        }
    } catch (error) {
        console.error('Error loading detection classes:', error);
    }
}

function updateClassSelect(classSets, defaultSet) {
    const select = document.getElementById('class-select');
    
    // Clear existing options except the first one
    select.innerHTML = '<option value="">All Classes (80 objects)</option>';
    
    // Add class set options
    Object.entries(classSets).forEach(([name, classes]) => {
        const option = document.createElement('option');
        option.value = classes.join(',');
        option.textContent = `${name.charAt(0).toUpperCase() + name.slice(1)} (${classes.length} objects)`;
        select.appendChild(option);
    });
    
    // Set default selection
    if (defaultSet && classSets[defaultSet]) {
        select.value = classSets[defaultSet].join(',');
    }
    
    // Update filter status
    updateClassFilterStatus();
}

// Update class filter status display
function updateClassFilterStatus() {
    const classSelect = document.getElementById('class-select');
    const filterStatus = document.getElementById('class-filter-status');
    const filterStatusText = document.getElementById('filter-status-text');
    
    if (classSelect.value) {
        const selectedClasses = classSelect.value.split(',');
        filterStatusText.textContent = `Only detecting: ${selectedClasses.join(', ')}`;
        filterStatus.style.display = 'block';
    } else {
        filterStatus.style.display = 'none';
    }
}

// ================================
// NOTIFICATION SYSTEM FUNCTIONS
// ================================

// Load notifications from server
async function loadNotifications() {
    try {
        const response = await fetch('/api/notifications?limit=20');
        const data = await response.json();
        
        if (data.notifications) {
            notifications = data.notifications;
            updateNotificationsDisplay();
        } else {
            console.error('Error loading notifications:', data.error);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

// Load notification statistics
async function loadNotificationStats() {
    try {
        const response = await fetch('/api/notifications/stats');
        const data = await response.json();
        
        if (data) {
            notificationStats = {
                total: data.total_notifications || 0,
                critical: data.by_importance?.critical || 0,
                high: data.by_importance?.high || 0,
                medium: data.by_importance?.medium || 0,
                low: data.by_importance?.low || 0
            };
            updateNotificationStats();
        }
    } catch (error) {
        console.error('Error loading notification stats:', error);
    }
}

// Handle new notification from SocketIO
function handleNewNotification(notificationData) {
    console.log('New notification received:', notificationData);
    
    // Add to notifications array
    notifications.unshift(notificationData);
    
    // Update display
    updateNotificationsDisplay();
    
    // Show popup only for high/critical enter/exit notifications
    if ((notificationData.importance === 'high' || notificationData.importance === 'critical') && 
        (notificationData.event_data?.event_type === 'entered' || notificationData.event_data?.event_type === 'exited')) {
        showNotificationPopup(notificationData);
    }
    
    // Auto-switch to notifications tab for important notifications
    if (notificationData.importance === 'critical' || notificationData.importance === 'high') {
        // Only switch if we're not already on the notifications tab
        const activeTab = document.querySelector('#mainTabs .nav-link.active');
        if (activeTab && activeTab.id !== 'notifications-tab') {
            setTimeout(() => {
                switchToNotificationsTab();
            }, 1000); // Delay to allow popup to show first
        }
    }
    
    // Play sound for important enter/exit notifications
    if (soundEnabled && (notificationData.importance === 'high' || notificationData.importance === 'critical') &&
        (notificationData.event_data?.event_type === 'entered' || notificationData.event_data?.event_type === 'exited')) {
        playNotificationSound(notificationData.importance);
    }
    
    // Update stats
    loadNotificationStats();
}

// Update notifications display
function updateNotificationsDisplay() {
    const container = document.getElementById('notifications-container');
    
    if (!notifications || notifications.length === 0) {
        container.innerHTML = `
            <div class="text-muted text-center">
                <i class="fas fa-bell-slash"></i><br>
                No notifications yet
            </div>
        `;
        return;
    }
    
    const notificationsHtml = notifications.slice(0, 10).map(notif => {
        const timeAgo = getTimeAgo(new Date(notif.timestamp));
        const importanceClass = notif.importance;
        
               const eventType = notif.event_data?.event_type || 'detected';
               const eventTypeIcon = eventType === 'entered' ? '🔽' : eventType === 'exited' ? '🔼' : '📍';
               
               return `
                   <div class="notification-item ${importanceClass}" onclick="viewNotificationDetails('${notif.id}')">
                       <div class="notification-importance-badge ${importanceClass}">
                           ${notif.importance.toUpperCase()}
                       </div>
                       <div class="notification-item-header">
                           <div class="notification-item-title">
                               ${eventTypeIcon} ${notif.title}
                           </div>
                           <div class="notification-item-time">${timeAgo}</div>
                       </div>
                       <div class="notification-item-message">${notif.message}</div>
                <div class="notification-item-actions">
                    ${notif.event_data?.snapshot_path ? 
                        `<button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); viewNotificationImage('${notif.id}')">
                            <i class="fas fa-image"></i> View Image
                        </button>` : ''
                    }
                    <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); viewEventDetails('${notif.event_data?.event_id}')">
                        <i class="fas fa-eye"></i> View Event
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); dismissNotification('${notif.id}')">
                        <i class="fas fa-times"></i> Dismiss
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = notificationsHtml;
}

// Update notification statistics display
function updateNotificationStats() {
    // This would update a stats section if we had one
    // For now, we'll just log the stats
    console.log('Notification Stats:', notificationStats);
}

// Show notification popup
function showNotificationPopup(notificationData) {
    // Dismiss any existing popup
    if (currentPopupNotification) {
        dismissPopup();
    }
    
    const popup = document.getElementById('notification-popup');
    const title = document.getElementById('popup-title');
    const message = document.getElementById('popup-message');
    
    // Update content
    title.textContent = notificationData.title;
    message.textContent = notificationData.message;
    
    // Update styling based on importance
    popup.className = `notification-popup notification-content ${notificationData.importance}`;
    
    // Show popup
    popup.style.display = 'block';
    currentPopupNotification = notificationData;
    
    // Auto-dismiss after 10 seconds for non-critical notifications
    if (notificationData.importance !== 'critical') {
        setTimeout(() => {
            if (currentPopupNotification === notificationData) {
                dismissPopup();
            }
        }, 10000);
    }
}

// Dismiss popup notification
function dismissPopup() {
    const popup = document.getElementById('notification-popup');
    
    if (currentPopupNotification) {
        // Dismiss the notification on the server
        dismissNotification(currentPopupNotification.id);
        currentPopupNotification = null;
    }
    
    popup.classList.add('hiding');
    setTimeout(() => {
        popup.style.display = 'none';
        popup.classList.remove('hiding');
    }, 300);
}

// Play notification sound
function playNotificationSound(importance) {
    if (!soundEnabled) return;
    
    try {
        // Create audio context for different sound patterns
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        let frequency, duration, pattern;
        
        switch (importance) {
            case 'critical':
                frequency = 800;
                duration = 200;
                pattern = [0, 100, 200, 300, 400, 500]; // 6 beeps
                break;
            case 'high':
                frequency = 600;
                duration = 150;
                pattern = [0, 200, 400]; // 3 beeps
                break;
            default:
                frequency = 400;
                duration = 100;
                pattern = [0]; // 1 beep
        }
        
        pattern.forEach((delay, index) => {
            setTimeout(() => {
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
                oscillator.type = 'sine';
                
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + duration / 1000);
            }, delay);
        });
        
        // Show sound indicator
        showSoundIndicator(importance);
        
    } catch (error) {
        console.warn('Could not play notification sound:', error);
    }
}

// Show sound indicator
function showSoundIndicator(importance) {
    const indicator = document.createElement('div');
    indicator.className = 'sound-indicator';
    indicator.innerHTML = `<i class="fas fa-volume-up"></i> ${importance.toUpperCase()} Alert`;
    
    document.body.appendChild(indicator);
    
    // Remove after animation
    setTimeout(() => {
        if (indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }, 2000);
}

// Dismiss notification
async function dismissNotification(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}/dismiss`, {
            method: 'POST'
        });
        
        if (response.ok) {
            // Remove from local array
            notifications = notifications.filter(n => n.id !== notificationId);
            updateNotificationsDisplay();
            loadNotificationStats();
        } else {
            console.error('Failed to dismiss notification');
        }
    } catch (error) {
        console.error('Error dismissing notification:', error);
    }
}

// Clear all notifications
async function clearNotifications() {
    if (!confirm('Are you sure you want to clear all notifications?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/notifications/clear', {
            method: 'POST'
        });
        
        if (response.ok) {
            notifications = [];
            updateNotificationsDisplay();
            loadNotificationStats();
            showToast('All notifications cleared', 'success');
        } else {
            console.error('Failed to clear notifications');
        }
    } catch (error) {
        console.error('Error clearing notifications:', error);
    }
}

// View notification details
function viewNotificationDetails(notificationId) {
    const notification = notifications.find(n => n.id === notificationId);
    if (!notification) return;
    
    // For now, just show an alert with the details
    // In a real app, this might open a modal or navigate to a details page
    const details = `
        Title: ${notification.title}
        Message: ${notification.message}
        Importance: ${notification.importance}
        Time: ${new Date(notification.timestamp).toLocaleString()}
        Event ID: ${notification.event_data?.event_id || 'N/A'}
        Event Type: ${notification.event_data?.event_type || 'detected'}
    `;
    
    alert(details);
}

// View notification image
function viewNotificationImage(notificationId) {
    const notification = notifications.find(n => n.id === notificationId);
    if (!notification || !notification.event_data?.snapshot_path) {
        showToast('No image available for this notification', 'warning');
        return;
    }
    
    // Create a modal to display the image
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${notification.title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="/api/snapshots/${notification.event_data.snapshot_path}" 
                         class="img-fluid" 
                         alt="Notification snapshot"
                         style="max-height: 70vh;">
                    <div class="mt-3">
                        <p><strong>Message:</strong> ${notification.message}</p>
                        <p><strong>Time:</strong> ${new Date(notification.timestamp).toLocaleString()}</p>
                        <p><strong>Event Type:</strong> ${notification.event_data.event_type || 'detected'}</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" onclick="viewEventDetails('${notification.event_data.event_id}')">View Full Event</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Show the modal using Bootstrap
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    // Remove modal from DOM when hidden
    modal.addEventListener('hidden.bs.modal', () => {
        document.body.removeChild(modal);
    });
}

// View event details (same as timeline event viewer)
function viewEventDetails(eventId) {
    if (!eventId) return;
    
    // Find the event in timeline events
    const event = timelineEvents.find(e => e.event_id === eventId);
    if (event) {
        showTimelineEventModal(event);
    } else {
        showToast('Event details not available', 'warning');
    }
}

// Utility function to get time ago
function getTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) {
        return `${diffInSeconds}s ago`;
    } else if (diffInSeconds < 3600) {
        return `${Math.floor(diffInSeconds / 60)}m ago`;
    } else if (diffInSeconds < 86400) {
        return `${Math.floor(diffInSeconds / 3600)}h ago`;
    } else {
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }
}

// Recent Detections Auto-Refresh
let recentDetectionsInterval = null;
let autoRefreshEnabled = false;

// Statistics Auto-Refresh
let statsInterval = null;
let statsAutoRefreshEnabled = false;
let previousStats = {};
let systemStartTime = Date.now();

function toggleAutoRefresh() {
    const btn = document.getElementById('auto-refresh-btn');
    const icon = btn.querySelector('i');
    
    if (autoRefreshEnabled) {
        // Stop auto-refresh
        clearInterval(recentDetectionsInterval);
        recentDetectionsInterval = null;
        autoRefreshEnabled = false;
        icon.className = 'fas fa-play';
        btn.title = 'Start Auto-Refresh';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-info');
    } else {
        // Start auto-refresh
        recentDetectionsInterval = setInterval(() => {
            loadRecentDetections();
        }, 5000); // 5 seconds
        autoRefreshEnabled = true;
        icon.className = 'fas fa-pause';
        btn.title = 'Stop Auto-Refresh';
        btn.classList.remove('btn-outline-info');
        btn.classList.add('btn-success');
    }
}

function loadRecentDetections() {
    fetch('/api/detections/recent?limit=10')
        .then(response => response.json())
        .then(data => {
            updateRecentDetectionsDisplay(data.detections || []);
        })
        .catch(error => {
            console.error('Error loading recent detections:', error);
        });
}

function updateRecentDetectionsDisplay(detections) {
    const container = document.getElementById('recent-detections');
    
    if (!detections || detections.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-eye fa-2x mb-2"></i>
                <p>No recent detections</p>
                <small>Start processing to see new object detection events</small>
            </div>
        `;
        return;
    }
    
    const detectionsHtml = detections.map(detection => {
        const timestamp = new Date(detection.timestamp).toLocaleString();
        const confidence = (detection.confidence * 100).toFixed(0);
        const confidenceClass = confidence >= 80 ? 'success' : confidence >= 60 ? 'warning' : 'danger';
        
        return `
            <div class="detection-entry mb-2 p-2 border rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${detection.class_name}</strong>
                        <span class="badge bg-${confidenceClass} ms-2">${confidence}%</span>
                    </div>
                    <small class="text-muted">${timestamp}</small>
                </div>
                <div class="mt-1">
                    <small class="text-muted">
                        <i class="fas fa-video"></i> ${detection.source} 
                        <span class="ms-2"><i class="fas fa-clock"></i> Frame ${detection.frame_number || 'N/A'}</span>
                    </small>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = detectionsHtml;
}

// Statistics Auto-Refresh Functions
function toggleStatsAutoRefresh() {
    const btn = document.getElementById('stats-auto-refresh-btn');
    const icon = btn.querySelector('i');
    
    if (statsAutoRefreshEnabled) {
        // Stop auto-refresh
        clearInterval(statsInterval);
        statsInterval = null;
        statsAutoRefreshEnabled = false;
        icon.className = 'fas fa-play';
        btn.title = 'Start Auto-Refresh';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-info');
    } else {
        // Start auto-refresh
        statsInterval = setInterval(() => {
            refreshStats();
        }, 3000); // 3 seconds
        statsAutoRefreshEnabled = true;
        icon.className = 'fas fa-pause';
        btn.title = 'Stop Auto-Refresh';
        btn.classList.remove('btn-outline-info');
        btn.classList.add('btn-success');
    }
}

function refreshStats() {
    // Update basic stats
    updateStats();
    
    // Update system status
    updateSystemStatus();
    
    // Update uptime
    updateUptime();
}

function updateStats() {
    // This would normally fetch from the API, but for now we'll update with current values
    const currentStats = {
        totalFrames: parseInt(document.getElementById('total-frames').textContent) || 0,
        totalDetections: parseInt(document.getElementById('total-detections').textContent) || 0,
        fps: parseFloat(document.getElementById('fps').textContent) || 0,
        activeTracks: parseInt(document.getElementById('active-tracks').textContent) || 0,
        peopleCount: parseInt(document.getElementById('people-count').textContent) || 0,
        vehiclesCount: parseInt(document.getElementById('vehicles-count').textContent) || 0
    };
    
    // Calculate changes
    Object.keys(currentStats).forEach(key => {
        const changeElement = document.getElementById(key + '-change');
        if (changeElement && previousStats[key] !== undefined) {
            const change = currentStats[key] - previousStats[key];
            if (change > 0) {
                changeElement.textContent = `+${change}`;
                changeElement.className = 'stat-change';
            } else if (change < 0) {
                changeElement.textContent = `${change}`;
                changeElement.className = 'stat-change negative';
            } else {
                changeElement.textContent = '+0';
                changeElement.className = 'stat-change neutral';
            }
        }
    });
    
    // Store current stats for next comparison
    previousStats = { ...currentStats };
}

function updateSystemStatus() {
    // Update camera status
    const cameraStatus = document.getElementById('camera-status');
    if (cameraStatus) {
        const isConnected = document.getElementById('connection-status').classList.contains('bg-success');
        if (isConnected) {
            cameraStatus.textContent = 'Connected';
            cameraStatus.className = 'badge bg-success';
        } else {
            cameraStatus.textContent = 'Disconnected';
            cameraStatus.className = 'badge bg-danger';
        }
    }
    
    // Update AI processing status
    const aiStatus = document.getElementById('ai-status');
    if (aiStatus) {
        const isProcessing = document.getElementById('processing-status').classList.contains('bg-success');
        if (isProcessing) {
            aiStatus.textContent = 'Active';
            aiStatus.className = 'badge bg-success';
        } else {
            aiStatus.textContent = 'Idle';
            aiStatus.className = 'badge bg-warning';
        }
    }
    
    // Simulate memory and CPU usage (in a real app, this would come from the backend)
    const memoryUsage = document.getElementById('memory-usage');
    const cpuUsage = document.getElementById('cpu-usage');
    
    if (memoryUsage) {
        const memoryPercent = Math.floor(Math.random() * 30) + 40; // 40-70%
        memoryUsage.textContent = `${memoryPercent}%`;
        memoryUsage.className = memoryPercent > 80 ? 'badge bg-danger' : 
                               memoryPercent > 60 ? 'badge bg-warning' : 'badge bg-success';
    }
    
    if (cpuUsage) {
        const cpuPercent = Math.floor(Math.random() * 40) + 20; // 20-60%
        cpuUsage.textContent = `${cpuPercent}%`;
        cpuUsage.className = cpuPercent > 80 ? 'badge bg-danger' : 
                            cpuPercent > 60 ? 'badge bg-warning' : 'badge bg-success';
    }
}

function updateUptime() {
    const uptimeElement = document.getElementById('uptime');
    if (uptimeElement) {
        const uptimeMs = Date.now() - systemStartTime;
        const hours = Math.floor(uptimeMs / (1000 * 60 * 60));
        const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((uptimeMs % (1000 * 60)) / 1000);
        
        uptimeElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Load distributed camera system status
function loadDistributedStatus() {
    fetch('/api/distributed/stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                updateDistributedStatus('error', 'Error loading distributed status');
                return;
            }
            
            const activeClients = data.active_clients || 0;
            const totalCameras = data.total_cameras || 0;
            const framesProcessed = data.frames_processed || 0;
            const detectionsTotal = data.detections_total || 0;
            
            if (activeClients > 0) {
                updateDistributedStatus('active', {
                    clients: activeClients,
                    cameras: totalCameras,
                    frames: framesProcessed,
                    detections: detectionsTotal
                });
            } else {
                updateDistributedStatus('inactive', {
                    clients: 0,
                    cameras: 0,
                    frames: 0,
                    detections: 0
                });
            }
        })
        .catch(error => {
            console.error('Error loading distributed status:', error);
            updateDistributedStatus('error', 'Connection error');
        });
}

// Update distributed status display
function updateDistributedStatus(status, data) {
    const container = document.getElementById('distributed-status');
    if (!container) return;
    
    switch (status) {
        case 'active':
            container.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="fas fa-circle text-success"></i>
                        <strong>${data.clients} Active Camera(s)</strong><br>
                        <small class="text-muted">
                            ${data.cameras} total cameras • ${data.frames.toLocaleString()} frames processed • ${data.detections} detections
                        </small>
                    </div>
                </div>
            `;
            break;
            
        case 'inactive':
            container.innerHTML = `
                <div class="text-center">
                    <i class="fas fa-circle text-muted"></i>
                    <small class="text-muted">
                        No distributed cameras connected<br>
                        Run <code>./run_camera_sender.sh</code> to connect cameras
                    </small>
                </div>
            `;
            break;
            
        case 'error':
            container.innerHTML = `
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                    <small class="text-muted">${data}</small>
                </div>
            `;
            break;
            
        default:
            container.innerHTML = `
                <div class="text-center">
                    <i class="fas fa-info-circle text-muted"></i>
                    <small class="text-muted">Loading distributed cameras...</small>
                </div>
            `;
    }
}

// ============================================================================
// Sex Offender Detection Functions
// ============================================================================

function startSexOffenderDetection() {
    const threshold = parseFloat(document.getElementById('sex-offender-threshold').value);
    const interval = parseFloat(document.getElementById('sex-offender-interval').value);
    
    fetch('/api/sex_offender_detection/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            camera_index: 0,
            confidence_threshold: threshold,
            detection_interval: interval
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'started') {
            sexOffenderDetectionActive = true;
            showNotification('Sex offender detection started', 'success');
            updateSexOffenderDetectionStatus();
        } else {
            showNotification('Failed to start sex offender detection: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error starting sex offender detection:', error);
        showNotification('Error starting sex offender detection', 'error');
    });
}

function stopSexOffenderDetection() {
    fetch('/api/sex_offender_detection/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'stopped') {
            sexOffenderDetectionActive = false;
            showNotification('Sex offender detection stopped', 'info');
            updateSexOffenderDetectionStatus();
        } else {
            showNotification('Failed to stop sex offender detection', 'error');
        }
    })
    .catch(error => {
        console.error('Error stopping sex offender detection:', error);
        showNotification('Error stopping sex offender detection', 'error');
    });
}

function updateSexOffenderDetectionStatus() {
    // Update UI to reflect current status
    const startBtn = document.querySelector('button[onclick="startSexOffenderDetection()"]');
    const stopBtn = document.querySelector('button[onclick="stopSexOffenderDetection()"]');
    
    if (sexOffenderDetectionActive) {
        if (startBtn) startBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;
    } else {
        if (startBtn) startBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
    }
}

function loadSexOffenderAlerts() {
    fetch('/api/sex_offender_detection/recent_detections?limit=20')
    .then(response => response.json())
    .then(data => {
        if (data.detections) {
            sexOffenderAlerts = data.detections;
            renderSexOffenderAlerts();
        }
    })
    .catch(error => {
        console.error('Error loading sex offender alerts:', error);
    });
}

function renderSexOffenderAlerts() {
    const container = document.getElementById('sex-offender-alerts-container');
    if (!container) return;
    
    if (sexOffenderAlerts.length === 0) {
        container.innerHTML = `
            <div class="text-muted text-center">
                <i class="fas fa-shield-alt"></i><br>
                No sex offender alerts yet
            </div>
        `;
        return;
    }
    
    container.innerHTML = sexOffenderAlerts.map(alert => {
        const timestamp = new Date(alert.timestamp).toLocaleString();
        const results = alert.results || [];
        
        return `
            <div class="alert alert-danger mb-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="alert-heading mb-1">
                            <i class="fas fa-exclamation-triangle"></i>
                            Sex Offender Alert
                        </h6>
                        <small class="text-muted">${timestamp}</small>
                        <div class="mt-2">
                            ${results.map(result => `
                                <div class="small">
                                    <strong>${result.offender_info?.name || result.offender_id}</strong>
                                    <span class="badge bg-danger ms-2">${(result.confidence * 100).toFixed(1)}%</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function clearSexOffenderAlerts() {
    sexOffenderAlerts = [];
    renderSexOffenderAlerts();
    showNotification('Sex offender alerts cleared', 'info');
}

// ============================================================================
// Family Member Management Functions
// ============================================================================

function loadFamilyMembers() {
    fetch('/api/family/analysis/members')
    .then(response => response.json())
    .then(data => {
        if (data.family_members) {
            familyMembers = Object.values(data.family_members);
            renderFamilyMembersList();
        }
    })
    .catch(error => {
        console.error('Error loading family members:', error);
    });
}

function renderFamilyMembersList() {
    const container = document.getElementById('family-members-list');
    if (!container) return;
    
    if (familyMembers.length === 0) {
        container.innerHTML = '<div class="text-muted">No family members added yet</div>';
        return;
    }
    
    container.innerHTML = familyMembers.map(member => `
        <div class="d-flex justify-content-between align-items-center mb-1 p-2 border rounded">
            <div>
                <strong>${member.name}</strong>
                <small class="text-muted d-block">Added: ${new Date(member.added_date).toLocaleDateString()}</small>
            </div>
            <button class="btn btn-sm btn-outline-danger" onclick="removeFamilyMember('${member.name}')">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

function addFamilyMember() {
    const nameInput = document.getElementById('family-member-name');
    const photoInput = document.getElementById('family-member-photo');
    
    const name = nameInput.value.trim();
    const photo = photoInput.files[0];
    
    if (!name) {
        showNotification('Please enter a family member name', 'error');
        return;
    }
    
    if (!photo) {
        showNotification('Please select a photo', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('photo', photo);
    
    fetch('/api/family/analysis/members', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'added') {
            showNotification(`Family member ${name} added successfully`, 'success');
            nameInput.value = '';
            photoInput.value = '';
            loadFamilyMembers();
        } else {
            showNotification('Failed to add family member: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error adding family member:', error);
        showNotification('Error adding family member', 'error');
    });
}

function removeFamilyMember(name) {
    if (!confirm(`Are you sure you want to remove ${name}?`)) {
        return;
    }
    
    fetch(`/api/family/analysis/members/${encodeURIComponent(name)}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'removed') {
            showNotification(`Family member ${name} removed`, 'info');
            loadFamilyMembers();
        } else {
            showNotification('Failed to remove family member: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error removing family member:', error);
        showNotification('Error removing family member', 'error');
    });
}

function captureCurrentFrame() {
    const nameInput = document.getElementById('family-member-name');
    const name = nameInput.value.trim();
    
    if (!name) {
        showNotification('Please enter a family member name first', 'error');
        return;
    }
    
    // This would need to be implemented with the current frame capture mechanism
    showNotification('Frame capture feature requires integration with video processor', 'info');
}

function loadFamilyMemberDetections() {
    // This would load recent family member detections
    // For now, we'll show a placeholder
    const container = document.getElementById('family-member-detections-container');
    if (container) {
        container.innerHTML = `
            <div class="text-muted text-center">
                <i class="fas fa-user-friends"></i><br>
                No family member detections yet
            </div>
        `;
    }
}

function clearFamilyMemberDetections() {
    familyMemberDetections = [];
    loadFamilyMemberDetections();
    showNotification('Family member detections cleared', 'info');
}

// ============================================================================
// Snapshot Analysis Functions
// ============================================================================

function analyzeSnapshot(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    
    fetch('/api/snapshot/analyze', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.analysis_status === 'completed') {
            showNotification(`Snapshot analysis complete: ${data.sex_offenders.length} sex offenders, ${data.family_members.length} family members`, 'info');
            
            // Show analysis results
            if (data.sex_offenders.length > 0) {
                showNotification(`🚨 SEX OFFENDER DETECTED: ${data.sex_offenders[0].offender_info?.name || 'Unknown'}`, 'error');
            }
            if (data.family_members.length > 0) {
                showNotification(`👨‍👩‍👧‍👦 FAMILY MEMBER DETECTED: ${data.family_members[0].name}`, 'success');
            }
        } else {
            showNotification('Snapshot analysis failed: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error analyzing snapshot:', error);
        showNotification('Error analyzing snapshot', 'error');
    });
}

// ============================================================================
// WebSocket Event Handlers for Real-time Updates
// ============================================================================

// Handle sex offender detection updates
function handleSexOffenderDetectionUpdate(data) {
    console.log('Sex offender detection update:', data);
    
    if (data.results && data.results.length > 0) {
        // Add to alerts
        sexOffenderAlerts.unshift({
            timestamp: data.timestamp,
            results: data.results
        });
        
        // Keep only recent alerts
        if (sexOffenderAlerts.length > 50) {
            sexOffenderAlerts = sexOffenderAlerts.slice(0, 50);
        }
        
        // Update display
        renderSexOffenderAlerts();
        
        // Show critical alerts
        data.results.forEach(result => {
            if (result.confidence > 0.7) {
                showNotification(`🚨 SEX OFFENDER ALERT: ${result.offender_info?.name || result.offender_id}`, 'error');
            }
        });
    }
}

// Handle family member detection updates
function handleFamilyMemberDetection(data) {
    console.log('Family member detection:', data);
    
    // Add to detections
    familyMemberDetections.unshift({
        timestamp: data.timestamp,
        ...data
    });
    
    // Keep only recent detections
    if (familyMemberDetections.length > 50) {
        familyMemberDetections = familyMemberDetections.slice(0, 50);
    }
    
    // Update display
    loadFamilyMemberDetections();
    
    // Show notification
    showNotification(`👨‍👩‍👧‍👦 FAMILY MEMBER: ${data.name}`, 'success');
}

// ============================================================================
// Initialize enhanced features
// ============================================================================

// Add event listeners for slider updates
document.addEventListener('DOMContentLoaded', function() {
    // Sex offender threshold slider
    const sexOffenderThreshold = document.getElementById('sex-offender-threshold');
    if (sexOffenderThreshold) {
        sexOffenderThreshold.addEventListener('input', function() {
            document.getElementById('sex-offender-threshold-value').textContent = this.value;
        });
    }
    
    // Sex offender interval slider
    const sexOffenderInterval = document.getElementById('sex-offender-interval');
    if (sexOffenderInterval) {
        sexOffenderInterval.addEventListener('input', function() {
            document.getElementById('sex-offender-interval-value').textContent = this.value + 's';
        });
    }
});

// Browser Notification Functions
function requestNotificationPermission() {
    if ('Notification' in window) {
        if (Notification.permission === 'default') {
            Notification.requestPermission().then(function(permission) {
                if (permission === 'granted') {
                    showNotification('Notifications Enabled', 'You will now receive security alerts and updates.', 'info');
                    console.log('Notification permission granted');
                } else {
                    console.log('Notification permission denied');
                }
            });
        } else if (Notification.permission === 'granted') {
            console.log('Notification permission already granted');
        } else {
            console.log('Notification permission denied');
        }
    } else {
        console.log('This browser does not support notifications');
    }
}

function showNotification(title, body, type = 'info') {
    if ('Notification' in window && Notification.permission === 'granted') {
        const notification = new Notification(title, {
            body: body,
            icon: '/static/images/security-icon.png',
            badge: '/static/images/security-badge.png',
            tag: 'security-alert',
            requireInteraction: type === 'critical',
            silent: type === 'info'
        });
        
        // Auto-close after 5 seconds for non-critical notifications
        if (type !== 'critical') {
            setTimeout(() => {
                notification.close();
            }, 5000);
        }
        
        // Handle notification click
        notification.onclick = function() {
            window.focus();
            notification.close();
        };
        
        return notification;
    } else {
        console.log('Cannot show notification: permission not granted or not supported');
        return null;
    }
}

function showSecurityAlert(title, message, severity = 'warning') {
    const alertTypes = {
        'critical': '🚨 CRITICAL ALERT',
        'warning': '⚠️ WARNING',
        'info': 'ℹ️ INFO',
        'success': '✅ SUCCESS'
    };
    
    const fullTitle = alertTypes[severity] || alertTypes['info'];
    const fullMessage = `${title}: ${message}`;
    
    // Show browser notification
    showNotification(fullTitle, fullMessage, severity);
    
    // Also show in-app notification
    addNotification({
        title: fullTitle,
        message: fullMessage,
        severity: severity,
        timestamp: new Date().toISOString()
    });
}

// Test notification function (for testing purposes)
function testNotification() {
    showNotification('Test Alert', 'This is a test notification to verify the system is working correctly.', 'info');
}
