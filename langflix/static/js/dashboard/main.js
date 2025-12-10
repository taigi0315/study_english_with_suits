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

    // Setup Event Listeners
    setupNavigation();
    setupFilters();
    setupAuth();
    setupCreateContent();
    setupBulkActions();
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
    ui.renderAccountInfo(accountData);
}

function setupAuth() {
    eventBus.addEventListener('login', async () => {
        const result = await api.login();
        if (result && result.auth_url) {
            window.location.href = result.auth_url;
        } else {
            console.error('Login returned no auth URL', result);
            alert('Failed to start login process');
        }
    });

    eventBus.addEventListener('logout', async () => {
        await api.logout();
        await loadAccountInfo(); // Refresh state
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

            const response = await fetch('/api/upload/single', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_id: video.id,
                    timing: timing
                })
            });

            if (response.ok) {
                ui.updateProgressPanel(i + 1, videos.length, `✓ Uploaded ${video.path.split('/').pop()}`);
            } else {
                const error = await response.json();
                ui.updateProgressPanel(i + 1, videos.length, `✗ Failed: ${error.error || 'Unknown error'}`);
            }
        } catch (error) {
            ui.updateProgressPanel(i + 1, videos.length, `✗ Error: ${error.message}`);
        }
    }

    ui.updateProgressPanel(videos.length, videos.length, 'Upload complete!', true);

    // Refresh view to update upload status
    setTimeout(() => refreshView(), 2000);
}

// Start app
document.addEventListener('DOMContentLoaded', init);
