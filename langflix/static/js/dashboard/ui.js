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
    },

    renderAccountInfo(accountData) {
        const container = document.getElementById('youtubeAccountSection');
        if (!accountData || !accountData.authenticated) {
            container.innerHTML = `
                <div class="youtube-login-prompt">
                    <p>Connect your YouTube account to upload videos</p>
                    <button class="btn-login" id="btnLogin">Connect YouTube</button>
                </div>
            `;
            const btn = document.getElementById('btnLogin');
            if (btn) btn.addEventListener('click', () => eventBus.dispatchEvent(new CustomEvent('login')));
            return;
        }

        // Assuming accountData structure matches: { authenticated: true, channel: { title: "...", thumbnail_url: "..." } }
        // We handle fallback if structure is flat for some reason, but backend sends nested 'channel'.
        const channel = accountData.channel || accountData;

        container.innerHTML = `
            <div class="youtube-account-info">
                <div class="account-details">
                    <img src="${channel.thumbnail_url || '/static/css/default-user.png'}" class="channel-thumbnail" alt="Channel">
                    <div class="account-text">
                        <div class="channel-title">${formatters.escapeHtml(channel.title || 'Unknown Channel')}</div>
                        <div class="channel-email">${formatters.escapeHtml(channel.custom_url || '')}</div>
                    </div>
                </div>
                <button class="btn-logout" id="btnLogout">Disconnect</button>
            </div>
        `;
        const btn = document.getElementById('btnLogout');
        if (btn) btn.addEventListener('click', () => eventBus.dispatchEvent(new CustomEvent('logout')));
    },

    async showCreateContentModal() {
        // Create modal overlay
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            backdrop-filter: blur(5px);
        `;

        // Create modal dialog
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 800px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        `;

        // Fetch available media
        let mediaHTML = '<div class="loading">Loading available media...</div>';
        try {
            const response = await fetch('/api/media/scan');
            const mediaFiles = await response.json();

            if (mediaFiles.length === 0) {
                mediaHTML = '<p style="color: #e74c3c;">No media files found. Please add video files to your media directory.</p>';
            } else {
                mediaHTML = `
                    <div style="max-height: 300px; overflow-y: auto; margin-bottom: 20px;">
                        ${mediaFiles.map(media => `
                            <label style="display: flex; align-items: center; padding: 10px; border: 1px solid #ecf0f1; border-radius: 5px; margin-bottom: 10px; cursor: pointer;">
                                <input type="checkbox" class="media-checkbox" value="${media.video_path}" 
                                    data-video="${media.video_path}" 
                                    data-subtitle="${media.subtitle_path || ''}"
                                    data-episode="${media.episode_name || ''}"
                                    data-show="${media.show_name || 'Suits'}"
                                    style="margin-right: 10px;">
                                <div>
                                    <div style="font-weight: 500;">${formatters.escapeHtml(media.episode_name || media.video_path)}</div>
                                    <div style="font-size: 0.9em; color: #7f8c8d;">${formatters.escapeHtml(media.show_name || '')}</div>
                                </div>
                            </label>
                        `).join('')}
                    </div>
                `;
            }
        } catch (error) {
            mediaHTML = `<p style="color: #e74c3c;">Error loading media: ${error.message}</p>`;
        }

        dialog.innerHTML = `
            <h2 style="margin-bottom: 20px; color: #2c3e50;">Create Content</h2>
            
            <div style="margin-bottom: 20px;">
                <h3 style="color: #34495e; margin-bottom: 10px;">Select Media</h3>
                ${mediaHTML}
            </div>

            <div style="margin-bottom: 20px;">
                <h3 style="color: #34495e; margin-bottom: 10px;">Language Settings</h3>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Source Language</label>
                    <select id="languageCode" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                        <option value="en">English</option>
                        <option value="ko">Korean</option>
                        <option value="ja">Japanese</option>
                    </select>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Language Level</label>
                    <select id="languageLevel" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                        <option value="beginner">Beginner</option>
                        <option value="intermediate">Intermediate</option>
                        <option value="advanced">Advanced</option>
                    </select>
                </div>
            </div>

            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="cancelBtn" style="padding: 12px 24px; border: none; border-radius: 6px; background: #ecf0f1; cursor: pointer;">
                    Cancel
                </button>
                <button id="createBtn" style="padding: 12px 24px; border: none; border-radius: 6px; background: #27ae60; color: white; cursor: pointer;">
                    Create Content
                </button>
            </div>
        `;

        modal.appendChild(dialog);
        document.body.appendChild(modal);

        // Event listeners
        dialog.querySelector('#cancelBtn').addEventListener('click', () => modal.remove());
        dialog.querySelector('#createBtn').addEventListener('click', async () => {
            const selectedMedia = Array.from(dialog.querySelectorAll('.media-checkbox:checked'));
            if (selectedMedia.length === 0) {
                alert('Please select at least one media file');
                return;
            }

            const languageCode = dialog.querySelector('#languageCode').value;
            const languageLevel = dialog.querySelector('#languageLevel').value;

            // Create content for each selected media
            for (const checkbox of selectedMedia) {
                try {
                    const response = await fetch('/api/content/create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            media_id: checkbox.value,
                            video_path: checkbox.dataset.video,
                            subtitle_path: checkbox.dataset.subtitle,
                            language_code: languageCode,
                            language_level: languageLevel,
                            create_long_form: true,
                            create_short_form: true
                        })
                    });

                    const result = await response.json();
                    if (response.ok) {
                        console.log('Job created:', result.job_id);
                    } else {
                        console.error('Error creating job:', result.error);
                    }
                } catch (error) {
                    console.error('Error:', error);
                }
            }

            modal.remove();
            alert('Content creation started! Check the job status for progress.');
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }
};
