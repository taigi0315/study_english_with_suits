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

// Start app
document.addEventListener('DOMContentLoaded', init);
