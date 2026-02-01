/**
 * Main application entry point
 */
import { state, eventBus } from './core.js';
import { api } from './api.js';
import { ui } from './ui.js';

async function init() {
    // Initial Load
    await refreshView();
    loadStats();
    loadAccountInfo();
    loadQueueStatus(); // Load initial queue status

    // Start Polling for Queue Status (every 5 seconds)
    setInterval(loadQueueStatus, 5000);

    // Setup Event Listeners
    setupNavigation();
    setupFilters();
    setupAuth();
    setupCreateContent();
    setupVideoActions(); // New handler for individual video actions
    setupBulkActions();
    ui.setupVideoListEvents(); // Set up event delegation for video list
}

async function refreshView() {
    state.currentDirectoryItems = await api.fetchDirectory(state.currentPath);
    state.allVideos = await api.fetchAllVideos(); // Cache for filtering
    ui.updateBreadcrumb(state.currentPath); // Update breadcrumb
    ui.renderDirectory(state.currentDirectoryItems.items || []);
    updateBulkActionsVisibility();
}

async function loadStats() {
    const stats = await api.fetchStatistics();
    ui.renderStats(stats);
}

function setupNavigation() {
    eventBus.addEventListener('navigate', async (e) => {
        const path = e.detail;
        state.currentPath = path;
        ui.updateBreadcrumb(path);
        await refreshView();
    });
}

function setupFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');

            state.currentFilter = e.target.dataset.filter;
            ui.renderDirectory(state.currentDirectoryItems.items || []);
            updateBulkActionsVisibility();
        });
    });
}

async function loadAccountInfo() {
    const accountData = await api.fetchAccountInfo();
    await ui.renderAccountInfo(accountData);
}

async function loadQueueStatus() {
    const statusData = await api.fetchQueueStatus();
    if (statusData) {
        ui.renderQueueStatus(statusData);
    }
}

function setupAuth() {
    eventBus.addEventListener('login', async () => {
        try {
            // Request auth URL from backend
            const result = await api.login();
            
            if (result && result.auth_url) {
                // Open popup window
                const width = 600;
                const height = 700;
                const left = (window.screen.width / 2) - (width / 2);
                const top = (window.screen.height / 2) - (height / 2);
                
                window.open(
                    result.auth_url, 
                    'youtube_auth', 
                    `width=${width},height=${height},top=${top},left=${left},scrollbars=yes,status=yes`
                );
            } else {
                console.error('Login returned no auth URL', result);
                alert('Failed to start login process');
            }
        } catch (e) {
            console.error('Login error:', e);
            alert('Failed to initialize login');
        }
    });

    eventBus.addEventListener('logout', async () => {
        await api.logout();
        await loadAccountInfo(); // Refresh state
        window.location.reload(); // Reload to clear any stale state
    });
    
    // Listen for auth messages from popup
    window.addEventListener('message', async (event) => {
        if (event.data.type === 'youtube-auth-success') {
            console.log('Authentication successful:', event.data.channel);
            // Refresh account info
            await loadAccountInfo();
            // Show success notification if needed
             // Reload page to reflect new account in dropdown immediately
            window.location.reload();
        } else if (event.data.type === 'youtube-auth-error') {
            console.error('Authentication error:', event.data.error);
            alert(`Authentication failed: ${event.data.details || event.data.error}`);
        }
    });
}

function setupCreateContent() {
    const btn = document.getElementById('createContentBtn');
    if (btn) {
        btn.addEventListener('click', async () => {
            await ui.showCreateContentModal();
        });
    }
}

function setupVideoActions() {
    // Play Video
    eventBus.addEventListener('play-video', (e) => {
        const path = e.detail.path;
        ui.showVideoPlayerModal(path);
    });

    // Upload Single Video
    eventBus.addEventListener('upload-video', async (e) => {
        const { path, id, type } = e.detail;
        console.log('Uploading single video:', path);
        // Reuse the upload logic
        // Default to scheduled as it's the recommended path
        await uploadSelectedVideos([{
            path: path,
            id: id,
            type: type || 'unknown'
        }], 'scheduled');
    });

    // Delete Video
    eventBus.addEventListener('delete-video', async (e) => {
        const path = e.detail.path;
        if (!confirm('Are you sure you want to delete this video?\nThis cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/videos/batch/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ videos: [path] })
            });

            const result = await response.json();
            if (response.ok && (result.success || result.deleted_count > 0)) {
                // visual feedback?
                await refreshView();
                // update stats
                loadStats();
            } else {
                alert(`Failed to delete video: ${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error deleting video:', error);
            alert('An error occurred while deleting the video');
        }
    });
}

function setupBulkActions() {
    // Select All button
    document.getElementById('selectAllVideosBtn')?.addEventListener('click', () => {
        document.querySelectorAll('.video-checkbox').forEach(cb => {
            const row = cb.closest('.video-row');
            if (row && row.style.display !== 'none') {
                cb.checked = true;
            }
        });
        updateSelectionCount();
    });

    // Deselect All button
    document.getElementById('deselectAllVideosBtn')?.addEventListener('click', () => {
        document.querySelectorAll('.video-checkbox').forEach(cb => cb.checked = false);
        updateSelectionCount();
    });

    // Upload Immediate button
    document.getElementById('uploadImmediateBtn')?.addEventListener('click', async () => {
        const selected = getSelectedVideos();
        if (selected.length === 0) {
            alert('Please select at least one video');
            return;
        }
        await uploadSelectedVideos(selected, 'immediate');
    });

    // Upload Schedule button
    document.getElementById('uploadScheduleBtn')?.addEventListener('click', async () => {
        const selected = getSelectedVideos();
        if (selected.length === 0) {
            alert('Please select at least one video');
            return;
        }
        await uploadSelectedVideos(selected, 'scheduled');
    });

    // Listen for checkbox changes
    document.addEventListener('change', (e) => {
        if (e.target.classList.contains('video-checkbox')) {
            updateSelectionCount();
        }
    });
}

function updateBulkActionsVisibility() {
    const bulkActionsBar = document.getElementById('bulkActionsBar');
    const hasVideos = document.querySelectorAll('.video-checkbox').length > 0;
    if (bulkActionsBar) {
        bulkActionsBar.style.display = hasVideos ? 'block' : 'none';
    }
}

function updateSelectionCount() {
    const selected = document.querySelectorAll('.video-checkbox:checked').length;
    const total = document.querySelectorAll('.video-checkbox').length;
    const countEl = document.getElementById('selectionCount');
    if (countEl) {
        countEl.textContent = `${selected} of ${total} videos selected`;
    }
}

function getSelectedVideos() {
    return Array.from(document.querySelectorAll('.video-checkbox:checked')).map(cb => ({
        path: cb.dataset.videoPath,
        type: cb.dataset.videoType,
        id: cb.dataset.videoId
    }));
}

async function uploadSelectedVideos(videos, timing) {
    if (!confirm(`Upload ${videos.length} video(s) with ${timing} timing?`)) {
        return;
    }

    ui.showProgressPanel(videos.length);

    for (let i = 0; i < videos.length; i++) {
        const video = videos[i];
        try {
            ui.updateProgressPanel(i + 1, videos.length, `Uploading ${video.path.split('/').pop()}...`);

            // Use batch endpoints with a single item to support the existing progress UI
            // and prevent timeouts on large immediate batches.
            const endpoint = timing === 'immediate'
                ? '/api/upload/batch/immediate'
                : '/api/upload/batch/schedule';

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    videos: [{
                        video_path: video.path,
                        video_type: video.type || 'unknown'
                    }]
                })
            });

            const result = await response.json();

            if (response.ok) {
                // Batch endpoint returns { success: bool, results: [...] }
                // We sent 1 video, so check results[0]
                if (result.results && result.results.length > 0) {
                    const videoResult = result.results[0];
                    if (videoResult.success) {
                        ui.updateProgressPanel(i + 1, videos.length, `✓ Uploaded ${video.path.split('/').pop()}`);
                    } else {
                        ui.updateProgressPanel(i + 1, videos.length, `✗ Failed: ${videoResult.error || 'Unknown error'}`);
                    }
                } else {
                    // Fallback if results are empty but request was ok (unlikely)
                    ui.updateProgressPanel(i + 1, videos.length, `✓ Uploaded ${video.path.split('/').pop()}`);
                }
            } else {
                ui.updateProgressPanel(i + 1, videos.length, `✗ Failed: ${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Upload error:', error);
            ui.updateProgressPanel(i + 1, videos.length, `✗ Error: ${error.message}`);
        }
    }

    ui.updateProgressPanel(videos.length, videos.length, 'Upload complete!', true);

    // Refresh view to update upload status
    setTimeout(() => refreshView(), 2000);
}

// Start app
document.addEventListener('DOMContentLoaded', init);
