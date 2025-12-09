/**
 * UI Rendering and Interaction
 */
import { state, formatters, eventBus } from './core.js';
import { api } from './api.js';

export const ui = {
    updateBreadcrumb(path) {
        const breadcrumb = document.getElementById('breadcrumbNav');
        const parts = path ? path.split('/').filter(p => p) : [];

        let html = '<a href="#" data-path="" class="nav-link" style="color: #3498db; text-decoration: none; font-weight: 500;">output</a>';

        let currentPath = '';
        parts.forEach((part, index) => {
            currentPath += (currentPath ? '/' : '') + part;
            const isLast = index === parts.length - 1;
            html += '<span style="color: #999; margin: 0 8px;">/</span>';
            if (isLast) {
                html += `<span style="color: #333; font-weight: 500;">${formatters.escapeHtml(part)}</span>`;
            } else {
                html += `<a href="#" data-path="${currentPath}" class="nav-link" style="color: #3498db; text-decoration: none; font-weight: 500;">${formatters.escapeHtml(part)}</a>`;
            }
        });

        breadcrumb.innerHTML = html;

        // Re-attach listeners since we replaced innerHTML
        breadcrumb.querySelectorAll('.nav-link').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                eventBus.dispatchEvent(new CustomEvent('navigate', { detail: el.dataset.path }));
            });
        });
    },

    renderStats(stats) {
        document.getElementById('totalVideos').textContent = stats.total_videos || 0;
        document.getElementById('uploadReady').textContent = stats.upload_ready_count || 0;
        document.getElementById('totalSize').textContent = stats.total_size_mb || 0;
        document.getElementById('totalDuration').textContent = formatters.duration(stats.total_duration_minutes * 60) || '0m';
    },

    renderDirectory(items) {
        const container = document.getElementById('videosContainer');

        if (items.length === 0) {
            container.innerHTML = '<div class="loading">This directory is empty.</div>';
            return;
        }

        // Separate directories and files
        const directories = items.filter(item => item.is_directory).sort((a, b) => a.name.localeCompare(b.name));
        const files = items.filter(item => item.is_file).sort((a, b) => a.name.localeCompare(b.name));
        const sortedItems = [...directories, ...files];

        // Filter items based on current filter
        let displayItems = sortedItems;
        if (state.currentFilter !== 'all') {
            displayItems = this.filterItems(sortedItems, files, directories);
        }

        // Render HTML
        container.innerHTML = `<div class="video-list">
            ${displayItems.map(item => this.renderItemRow(item)).join('')}
        </div>`;

        // Attach click listeners to rows
        container.querySelectorAll('.video-row').forEach(row => {
            row.addEventListener('click', (e) => {
                // Prevent navigation if clicking buttons or checkboxes
                if (e.target.closest('button') || e.target.closest('input[type="checkbox"]')) return;

                if (row.dataset.isDir === 'true') {
                    eventBus.dispatchEvent(new CustomEvent('navigate', { detail: row.dataset.path }));
                } else if (row.dataset.isVideo === 'true') {
                    // Play video or action
                    console.log('Video clicked:', row.dataset.path);
                    // TODO: Implement video player modal trigger
                }
            });
        });
    },

    filterItems(displayItems, files, directories) {
        // Implementation of complex filtering logic
        // This mirrors the logic in the original HTML file
        if (state.currentFilter === 'short-form' || state.currentFilter === 'long-form') {
            const filteredFiles = files.filter(file => {
                if (!file.is_video) return false;
                const matchingVideo = state.allVideos.find(v => v.path === file.absolute_path);
                if (!matchingVideo) return false;

                if (state.currentFilter === 'short-form') {
                    return matchingVideo.video_type === 'short-form' || matchingVideo.video_type === 'short';
                } else {
                    return matchingVideo.video_type === 'long-form' || matchingVideo.video_type === 'final';
                }
            });
            return [...directories, ...filteredFiles];
        }
        // ... (other filters: uploaded, not-uploaded)
        return displayItems; // Fallback
    },

    renderItemRow(item) {
        // Determine icon/thumbnail
        let thumbnailHtml = '';
        if (item.is_directory) {
            thumbnailHtml = '<div style="font-size: 24px;">📁</div>';
        } else if (item.is_video) {
            thumbnailHtml = '<div style="font-size: 24px;">🎬</div>';
        } else {
            thumbnailHtml = '<div style="font-size: 24px;">📄</div>';
        }

        return `
        <div class="video-row" data-path="${item.relative_path}" data-is-dir="${item.is_directory}" data-is-video="${item.is_video}">
            <div class="video-thumbnail-small">
                ${thumbnailHtml}
            </div>
            <div class="video-info-compact">
                <div class="video-title-compact">${formatters.escapeHtml(item.name)}</div>
                <div class="video-meta-compact">
                    ${item.size_mb ? `<span>${item.size_mb} MB</span>` : ''}
                    ${item.modified ? `<span>${new Date(item.modified * 1000).toLocaleDateString()}</span>` : ''}
                </div>
            </div>
            ${item.is_video ? this.renderVideoActions(item) : ''}
        </div>`;
    },

    renderVideoActions(item) {
        return `
        <div class="video-actions-compact">
             <button class="action-btn-icon" title="Play Video">▶️</button>
             <button class="action-btn-icon" title="Delete" style="color: #e74c3c;">🗑️</button>
        </div>
        `;
    }
};
