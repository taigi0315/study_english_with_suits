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

    // Setup Event Listeners
    setupNavigation();
    setupFilters();
}

async function refreshView() {
    state.currentDirectoryItems = await api.fetchDirectory(state.currentPath);
    state.allVideos = await api.fetchAllVideos(); // Cache for filtering
    ui.renderDirectory(state.currentDirectoryItems.items || []);
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
        });
    });
}

// Start app
document.addEventListener('DOMContentLoaded', init);
