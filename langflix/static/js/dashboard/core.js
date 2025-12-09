/**
 * Config and State Management
 */

// Application State
export const state = {
    allVideos: [],
    currentDirectoryItems: [],
    currentFilter: 'all',
    currentPath: '',
    languageNames: {
        'ko': 'Korean',
        'ja': 'Japanese',
        'zh': 'Chinese',
        'es': 'Spanish',
        'fr': 'French',
        'en': 'English',
        'unknown': 'Unknown'
    }
};

// Formatting Utilities
export const formatters = {
    duration: (seconds) => {
        if (!seconds) return '0m';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    },

    size: (mb) => {
        if (!mb) return '0 MB';
        if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
        return `${Math.round(mb)} MB`;
    },

    escapeHtml: (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    getLanguageDisplayName: (code) => {
        return state.languageNames[code] || code;
    }
};

// Event Bus for component communication
export const eventBus = new EventTarget();

// Constants
export const API_BASE = '/api';
