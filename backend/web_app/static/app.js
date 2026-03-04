// Barcode Job Tracker - Enhanced Frontend JavaScript

let html5QrcodeScanner = null;
let scanHistory = [];
let currentJobId = null;

// DOM Elements
const startScanBtn = document.getElementById('start-scan-btn');
const stopScanBtn = document.getElementById('stop-scan-btn');
const manualJobIdInput = document.getElementById('manual-job-id');
const manualSubmitBtn = document.getElementById('manual-submit-btn');
const autoUpdateToggle = document.getElementById('auto-update-toggle');
const statusMessage = document.getElementById('status-message');
const jobDetails = document.getElementById('job-details');
const historyList = document.getElementById('history-list');
const autocompleteDropdown = document.getElementById('autocomplete-dropdown');

// Autocomplete state
let autocompleteDebounceTimer = null;
let selectedAutocompleteIndex = -1;
let autocompleteResults = [];

// Job details elements
const acknowledgedCheckbox = document.getElementById('acknowledged-checkbox');
const completedCheckbox = document.getElementById('completed-checkbox');
const staffNotesTextarea = document.getElementById('staff-notes-textarea');
const saveNotesBtn = document.getElementById('save-notes-btn');
const updateStatusBtn = document.getElementById('update-status-btn');
const userNotesBox = document.getElementById('user-notes-box');

// Event Listeners
startScanBtn.addEventListener('click', startScanner);
stopScanBtn.addEventListener('click', stopScanner);
manualSubmitBtn.addEventListener('click', handleManualSubmit);
saveNotesBtn.addEventListener('click', saveStaffNotes);
updateStatusBtn.addEventListener('click', updateJobStatus);

manualJobIdInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        if (selectedAutocompleteIndex >= 0 && autocompleteResults.length > 0) {
            // Select the highlighted autocomplete item
            selectAutocompleteItem(autocompleteResults[selectedAutocompleteIndex]);
        } else {
            handleManualSubmit();
        }
    }
});

// Autocomplete event listeners
manualJobIdInput.addEventListener('input', handleAutocompleteInput);
manualJobIdInput.addEventListener('keydown', handleAutocompleteKeydown);

// Click outside to close autocomplete
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        hideAutocomplete();
    }
});

// Initialize
loadScanHistory();
loadAutoUpdateSetting();
ensureInputFocus();
initializeStickyInput();

// Focus management - ensure input stays focused
function ensureInputFocus() {
    // Focus input on page load
    setTimeout(() => {
        manualJobIdInput.focus();
    }, 100);
}

// Refocus input after successful operations
function refocusInput() {
    setTimeout(() => {
        manualJobIdInput.focus();
    }, 300);
}

// Sticky input on scroll
function initializeStickyInput() {
    const manualEntry = document.querySelector('.manual-entry');
    const manualEntryOffset = manualEntry.offsetTop;
    
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > manualEntryOffset) {
            manualEntry.classList.add('sticky');
        } else {
            manualEntry.classList.remove('sticky');
        }
    });
}

// Autocomplete functionality
function handleAutocompleteInput(e) {
    const query = e.target.value.trim();
    
    // Clear previous timer
    if (autocompleteDebounceTimer) {
        clearTimeout(autocompleteDebounceTimer);
    }
    
    // Hide dropdown if query is too short
    if (query.length < 2) {
        hideAutocomplete();
        return;
    }
    
    // Debounce: wait 300ms before searching
    autocompleteDebounceTimer = setTimeout(() => {
        fetchAutocompleteResults(query);
    }, 300);
}

function handleAutocompleteKeydown(e) {
    // Handle arrow keys for navigation
    if (!autocompleteResults.length) return;
    
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedAutocompleteIndex = Math.min(selectedAutocompleteIndex + 1, autocompleteResults.length - 1);
        updateAutocompleteSelection();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedAutocompleteIndex = Math.max(selectedAutocompleteIndex - 1, -1);
        updateAutocompleteSelection();
    } else if (e.key === 'Escape') {
        hideAutocomplete();
    }
}

async function fetchAutocompleteResults(query) {
    try {
        const response = await fetch(`/api/search-job-ids?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.job_ids.length > 0) {
            autocompleteResults = data.job_ids;
            selectedAutocompleteIndex = -1;
            displayAutocompleteResults(data.job_ids);
        } else {
            hideAutocomplete();
        }
    } catch (error) {
        console.error('Autocomplete fetch error:', error);
        hideAutocomplete();
    }
}

function displayAutocompleteResults(jobIds) {
    autocompleteDropdown.innerHTML = '';
    
    jobIds.forEach((jobId, index) => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = jobId;
        item.dataset.index = index;
        
        item.addEventListener('click', () => {
            selectAutocompleteItem(jobId);
        });
        
        autocompleteDropdown.appendChild(item);
    });
    
    autocompleteDropdown.classList.remove('hidden');
}

function updateAutocompleteSelection() {
    const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');
    items.forEach((item, index) => {
        if (index === selectedAutocompleteIndex) {
            item.classList.add('selected');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('selected');
        }
    });
}

function selectAutocompleteItem(jobId) {
    manualJobIdInput.value = jobId;
    hideAutocomplete();
    handleManualSubmit();
}

function hideAutocomplete() {
    autocompleteDropdown.classList.add('hidden');
    autocompleteDropdown.innerHTML = '';
    autocompleteResults = [];
    selectedAutocompleteIndex = -1;
}

function loadAutoUpdateSetting() {
    const saved = localStorage.getItem('autoUpdate');
    if (saved !== null) {
        autoUpdateToggle.checked = saved === 'true';
    }
}

function saveAutoUpdateSetting() {
    localStorage.setItem('autoUpdate', autoUpdateToggle.checked);
}

// Listen for auto-update toggle changes
autoUpdateToggle.addEventListener('change', saveAutoUpdateSetting);

function startScanner() {
    console.log("Starting scanner...");
    console.log("Protocol:", window.location.protocol);
    console.log("MediaDevices available:", !!navigator.mediaDevices);
    console.log("getUserMedia available:", !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia));
    
    // Check if we're on HTTPS or localhost
    const isSecureContext = window.isSecureContext || 
                           window.location.protocol === 'https:' || 
                           window.location.hostname === 'localhost' || 
                           window.location.hostname === '127.0.0.1';
    
    if (!isSecureContext) {
        showStatus('Camera requires HTTPS or localhost. Current URL: ' + window.location.protocol + '//' + window.location.host, 'error');
        return;
    }
    
    // Check if camera API is available
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showStatus('Camera API not available in this browser. Try Chrome, Edge, or Safari. Please use manual entry.', 'error');
        return;
    }

    // Show loading state
    showStatus('Requesting camera permission...', 'info');
    
    // Request camera permission explicitly
    navigator.mediaDevices.getUserMedia({ 
        video: { 
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 }
        } 
    })
        .then(stream => {
            console.log("Camera permission granted, got stream:", stream);
            // Stop the test stream immediately
            stream.getTracks().forEach(track => {
                console.log("Stopping track:", track.label);
                track.stop();
            });
            
            showStatus('Camera permission granted. Starting scanner...', 'info');
            
            // Now start Html5Qrcode scanner
            const config = {
                fps: 10,
                qrbox: { width: 250, height: 150 },
                formatsToSupport: [Html5QrcodeSupportedFormats.CODE_128]
            };

            html5QrcodeScanner = new Html5Qrcode("reader");
            
            // Get list of available cameras
            Html5Qrcode.getCameras().then(devices => {
                console.log("Cameras found:", devices);
                if (devices && devices.length) {
                    console.log(`Found ${devices.length} camera(s)`);
                    
                    // Try to find rear camera, otherwise use first camera
                    let cameraId = devices[0].id;
                    for (let device of devices) {
                        if (device.label.toLowerCase().includes('back') || 
                            device.label.toLowerCase().includes('rear')) {
                            cameraId = device.id;
                            break;
                        }
                    }
                    
                    console.log("Using camera:", cameraId);
                    
                    html5QrcodeScanner.start(
                        cameraId,
                        config,
                        onScanSuccess,
                        onScanFailure
                    ).then(() => {
                        console.log("Scanner started successfully");
                        showStatus('Scanner active. Point camera at barcode.', 'success');
                        startScanBtn.style.display = 'none';
                        stopScanBtn.style.display = 'block';
                    }).catch(err => {
                        console.error("Html5Qrcode start error:", err);
                        showStatus(`Scanner failed to start: ${err}. Try manual entry.`, 'error');
                    });
                } else {
                    showStatus('No cameras found on this device. Please use manual entry.', 'error');
                }
            }).catch(err => {
                console.error("Error enumerating cameras:", err);
                showStatus('Cannot access cameras. Check permissions and try again.', 'error');
            });
        })
        .catch(err => {
            console.error("Camera permission error:", err);
            console.error("Error name:", err.name);
            console.error("Error message:", err.message);
            
            if (err.name === 'NotAllowedError') {
                showStatus('❌ Camera permission denied. Click the camera icon in address bar to allow access, then try again.', 'error');
            } else if (err.name === 'NotFoundError') {
                showStatus('❌ No camera found on this device. Please use manual entry below.', 'error');
            } else if (err.name === 'NotReadableError') {
                showStatus('❌ Camera is being used by another application. Close other apps and try again.', 'error');
            } else if (err.name === 'SecurityError') {
                showStatus('❌ Camera access blocked. Must use HTTPS or localhost. Current: ' + window.location.protocol, 'error');
            } else {
                showStatus(`❌ Camera error: ${err.message || err}. Please use manual entry.`, 'error');
            }
        });
}

function stopScanner() {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.stop().then(() => {
            console.log("Scanner stopped");
            startScanBtn.style.display = 'block';
            stopScanBtn.style.display = 'none';
        }).catch(err => {
            console.error("Error stopping scanner:", err);
        });
    }
}

function onScanSuccess(decodedText, decodedResult) {
    console.log(`Scanned: ${decodedText}`);
    
    // Auto-stop scanner after successful scan
    stopScanner();
    
    // Process the scanned job ID
    processJobId(decodedText);
}

function onScanFailure(error) {
    // Ignore scan failures (normal when no barcode in view)
}

function handleManualSubmit() {
    const jobId = manualJobIdInput.value.trim().toUpperCase();
    
    if (!jobId) {
        showStatus('Please enter a Job ID', 'error');
        return;
    }
    
    processJobId(jobId);
    manualJobIdInput.value = '';
    refocusInput();
}

async function processJobId(jobId) {
    try {
        showStatus('Processing...', 'warning');
        
        // Get auto-update setting
        const autoUpdate = autoUpdateToggle.checked;
        
        // Call API to scan barcode
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                job_id: jobId,
                auto_update: autoUpdate
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentJobId = jobId;
            
            if (data.action) {
                showStatus(`✓ ${capitalizeFirst(data.action)}!`, 'success');
                addToHistory(jobId, data.action);
            } else {
                showStatus('✓ Job loaded', 'success');
            }
            
            displayJobDetails(data.job, data.action);
        } else {
            showStatus(`Error: ${data.error}`, 'error');
            jobDetails.classList.add('hidden');
        }
        
    } catch (error) {
        console.error('Error processing job:', error);
        showStatus('Network error. Please try again.', 'error');
        jobDetails.classList.add('hidden');
    }
}

function displayJobDetails(job, action) {
    // Populate job details
    document.getElementById('detail-job-id').textContent = job.job_id || '-';
    document.getElementById('detail-email').textContent = job.email || '-';
    document.getElementById('detail-room').textContent = job.room || '-';
    document.getElementById('detail-quantity').textContent = job.quantity || '-';
    document.getElementById('detail-paper-size').textContent = job.paper_size || '-';
    document.getElementById('detail-two-sided').textContent = job.two_sided || '-';
    document.getElementById('detail-date').textContent = job.date_submitted || '-';
    document.getElementById('detail-deadline').textContent = job.job_deadline || '-';
    
    // Update status badge
    const badge = document.getElementById('job-status-badge');
    if (job.status.completed) {
        badge.textContent = 'Completed';
        badge.className = 'badge completed';
    } else if (job.status.acknowledged) {
        badge.textContent = 'Acknowledged';
        badge.className = 'badge acknowledged';
    } else {
        badge.textContent = 'Pending';
        badge.className = 'badge pending';
    }
    
    // Update checkboxes to reflect current status
    acknowledgedCheckbox.checked = job.status.acknowledged || false;
    completedCheckbox.checked = job.status.completed || false;
    
    // Display user notes with highlight if not NA/N/A
    const userNotes = job.user_notes || '';
    const isImportant = userNotes && !['NA', 'N/A', 'na', 'n/a'].includes(userNotes.trim());
    
    if (userNotes && userNotes.trim()) {
        userNotesBox.textContent = userNotes;
    } else {
        userNotesBox.textContent = 'No notes';
    }
    
    // Add pulsing border class if important
    if (isImportant) {
        userNotesBox.classList.add('has-content');
    } else {
        userNotesBox.classList.remove('has-content');
    }
    
    // Load staff notes
    staffNotesTextarea.value = job.staff_notes || '';
    
    // Show job details card
    jobDetails.classList.remove('hidden');
    
    // Scroll to job details
    jobDetails.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function saveStaffNotes() {
    if (!currentJobId) {
        showStatus('No job loaded', 'error');
        return;
    }
    
    try {
        showStatus('Saving notes...', 'warning');
        
        const notes = staffNotesTextarea.value;
        
        const response = await fetch('/api/update_notes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('✓ Notes saved', 'success');
            // Refresh job details to show updated data
            if (data.job) {
                displayJobDetails(data.job, null);
            }
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error saving notes:', error);
        showStatus('Network error. Please try again.', 'error');
    }
}

async function updateJobStatus() {
    if (!currentJobId) {
        showStatus('No job loaded', 'error');
        return;
    }
    
    try {
        showStatus('Updating status...', 'warning');
        
        const acknowledged = acknowledgedCheckbox.checked;
        const completed = completedCheckbox.checked;
        
        const response = await fetch('/api/update_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                acknowledged: acknowledged,
                completed: completed
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('✓ Status updated', 'success');
            // Refresh job details to show updated status
            if (data.job) {
                displayJobDetails(data.job, null);
            }
            
            // Add to history
            const action = completed ? 'completed' : (acknowledged ? 'acknowledged' : 'reset');
            addToHistory(currentJobId, action);
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error updating status:', error);
        showStatus('Network error. Please try again.', 'error');
    }
}

function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusMessage.classList.add('hidden');
    }, 5000);
}

function addToHistory(jobId, action) {
    const timestamp = new Date().toLocaleTimeString();
    const historyItem = {
        jobId,
        action,
        timestamp
    };
    
    scanHistory.unshift(historyItem);
    
    // Keep only last 10 items
    if (scanHistory.length > 10) {
        scanHistory = scanHistory.slice(0, 10);
    }
    
    saveScanHistory();
    renderHistory();
}

function renderHistory() {
    historyList.innerHTML = '';
    
    if (scanHistory.length === 0) {
        historyList.innerHTML = '<p style="text-align:center; color:#999;">No scans yet</p>';
        return;
    }
    
    scanHistory.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div>
                <div class="job-id">${item.jobId}</div>
                <div class="action">${capitalizeFirst(item.action)}</div>
            </div>
            <div class="timestamp">${item.timestamp}</div>
        `;
        historyList.appendChild(historyItem);
    });
}

function saveScanHistory() {
    try {
        localStorage.setItem('scanHistory', JSON.stringify(scanHistory));
    } catch (e) {
        console.error('Error saving history:', e);
    }
}

function loadScanHistory() {
    try {
        const stored = localStorage.getItem('scanHistory');
        if (stored) {
            scanHistory = JSON.parse(stored);
            renderHistory();
        }
    } catch (e) {
        console.error('Error loading history:', e);
    }
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).replace('_', ' ');
}

// Auto-focus manual input on load
manualJobIdInput.focus();
