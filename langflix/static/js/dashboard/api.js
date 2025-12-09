/**
 * API interaction layer
 */
import { API_BASE, state, formatters } from './core.js';

export const api = {
    async fetchDirectory(path) {
        const url = `${API_BASE}/explore${path ? '?path=' + encodeURIComponent(path) : ''}`;
        const response = await fetch(url);
        return await response.json();
    },

    async fetchAllVideos() {
        const response = await fetch(`${API_BASE}/videos`);
        return await response.json();
    },

    async fetchStatistics() {
        const response = await fetch(`${API_BASE}/statistics`);
        return await response.json();
    },

    async fetchQuotaStatus() {
        try {
            const response = await fetch(`${API_BASE}/quota-status`);
            return await response.json();
        } catch (e) {
            console.warn("Failed to fetch quota", e);
            return null;
        }
    },

    async createJob(formData) {
        const response = await fetch(`${API_BASE}/jobs`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create job');
        }

        return await response.json();
    },

    async getJobStatus(jobId) {
        const response = await fetch(`${API_BASE}/jobs/${jobId}`);
        return await response.json();
    },

    async deleteVideo(path) {
        const response = await fetch(`${API_BASE}/video?path=${encodeURIComponent(path)}`, {
            method: 'DELETE'
        });
        return await response.json();
    },

    async batchDelete(paths) {
        const response = await fetch(`${API_BASE}/videos/batch/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths })
        });
        return await response.json();
    }
};
