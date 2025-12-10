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
    },

    // Set up event delegation once (called from main.js init)
    setupVideoListEvents() {
        const container = document.getElementById('videosContainer');
        if (!container) return;

        // Use event delegation - single listener on container
        container.addEventListener('click', (e) => {
            const row = e.target.closest('.video-row');
            if (!row) return;

            console.log('Row clicked:', {
                target: e.target,
                isDir: row.dataset.isDir,
                path: row.dataset.path,
                targetTag: e.target.tagName,
                targetClasses: e.target.className
            });

            // Prevent navigation if clicking buttons, checkboxes, or action buttons
            if (e.target.closest('button') ||
                e.target.closest('input[type="checkbox"]') ||
                e.target.classList.contains('video-checkbox') ||
                e.target.classList.contains('action-btn-icon') ||
                e.target.tagName === 'INPUT') {
                console.log('Click ignored - button or checkbox');
                return;
            }

            if (row.dataset.isDir === 'true') {
                console.log('Navigating to directory:', row.dataset.path);
                eventBus.dispatchEvent(new CustomEvent('navigate', { detail: row.dataset.path }));
            } else if (row.dataset.isVideo === 'true') {
                // Play video or action
                console.log('Video clicked:', row.dataset.path);
                // TODO: Implement video player modal trigger
            }
        });
    },

    filterItems(displayItems, files, directories) {
        // Implementation of complex filtering logic
        // This mirrors the logic in the original HTML file
        if (state.currentFilter === 'short-form' || state.currentFilter === 'long-form') {
            const filteredFiles = files.filter(file => {
                if (!file.is_video) return false;
                const matchingVideo = state.allVideos.find(v => v.path === file.absolute_path);

                // If video is not in the database, infer type from path
                if (!matchingVideo) {
                    // Check if path contains 'shorts' or 'short-form' for short-form filter
                    if (state.currentFilter === 'short-form') {
                        return file.path.includes('/shorts/') || file.path.includes('short-form');
                    } else {
                        // For long-form, check for 'final' in path
                        return file.path.includes('/final/') || file.path.includes('long-form');
                    }
                }

                if (state.currentFilter === 'short-form') {
                    return matchingVideo.video_type === 'short-form' || matchingVideo.video_type === 'short';
                } else {
                    return matchingVideo.video_type === 'long-form' || matchingVideo.video_type === 'final';
                }
            });
            return [...directories, ...filteredFiles];
        }

        // For uploaded/not-uploaded filters
        if (state.currentFilter === 'uploaded' || state.currentFilter === 'not-uploaded') {
            const filteredFiles = files.filter(file => {
                if (!file.is_video) return false;
                const matchingVideo = state.allVideos.find(v => v.path === file.absolute_path);
                if (!matchingVideo) return state.currentFilter === 'not-uploaded'; // If not in DB, assume not uploaded

                if (state.currentFilter === 'uploaded') {
                    return matchingVideo.uploaded === true;
                } else {
                    return matchingVideo.uploaded !== true;
                }
            });
            return [...directories, ...filteredFiles];
        }

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

        // Check if video is ready for upload (has metadata)
        const matchingVideo = state.allVideos.find(v => v.path === item.absolute_path);
        const readyForUpload = matchingVideo && matchingVideo.ready_for_upload;
        const isUploaded = matchingVideo && matchingVideo.uploaded;

        return `
        <div class="video-row ${readyForUpload ? 'ready-for-upload' : ''} ${isUploaded ? 'uploaded' : ''}" 
             data-path="${item.path || item.name}" 
             data-is-dir="${item.is_directory}" 
             data-is-video="${item.is_video}"
             style="${item.is_directory ? 'cursor: pointer;' : ''}">
            ${item.is_video ? `
                <div style="margin-right: 10px;">
                    <input type="checkbox" 
                           class="video-checkbox" 
                           data-video-path="${item.absolute_path}"
                           data-video-type="${matchingVideo ? matchingVideo.video_type : 'unknown'}"
                           data-ready-for-upload="${readyForUpload}"
                           style="width: 18px; height: 18px; cursor: pointer;">
                </div>
            ` : ''}
            <div class="video-thumbnail-small">
                ${thumbnailHtml}
            </div>
            <div class="video-info-compact">
                <div class="video-title-compact">${formatters.escapeHtml(item.name)}</div>
                <div class="video-meta-compact">
                    ${item.size ? `<span>${formatters.formatSize(item.size)}</span>` : ''}
                    ${item.modified ? `<span>${new Date(item.modified).toLocaleDateString()}</span>` : ''}
                    ${isUploaded ? '<span style="color: #27ae60; font-weight: 600;">✓ Uploaded</span>' : ''}
                    ${readyForUpload && !isUploaded ? '<span style="color: #f39c12; font-weight: 600;">⚡ Ready</span>' : ''}
                </div>
            </div>
            ${item.is_video ? this.renderVideoActions(item, matchingVideo, readyForUpload, isUploaded) : ''}
        </div>`;
    },

    renderVideoActions(item, matchingVideo, readyForUpload, isUploaded) {
        return `
        <div class="video-actions-compact">
             <button class="action-btn-icon play-video-btn" data-path="${item.absolute_path}" title="Play Video">▶️</button>
             ${readyForUpload && !isUploaded ? `
                <button class="action-btn-icon upload-single-btn" 
                        data-video-path="${item.absolute_path}"
                        data-video-id="${matchingVideo ? matchingVideo.id : ''}"
                        title="Upload to YouTube" 
                        style="color: #27ae60;">📤</button>
             ` : ''}
             <button class="action-btn-icon delete-video-btn" data-path="${item.absolute_path}" title="Delete" style="color: #e74c3c;">🗑️</button>
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
            max-width: 900px;
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
                    <div style="max-height: 300px; overflow-y: auto; margin-bottom: 20px; border: 1px solid #ecf0f1; border-radius: 8px; padding: 10px;">
                        ${mediaFiles.map(media => `
                            <label style="display: flex; align-items: center; padding: 10px; border: 1px solid #ecf0f1; border-radius: 5px; margin-bottom: 10px; cursor: pointer; transition: all 0.2s;">
                                <input type="checkbox" class="media-checkbox" value="${media.video_path}" 
                                    data-video="${media.video_path}" 
                                    data-subtitle="${media.subtitle_path || ''}"
                                    data-episode="${media.episode_name || ''}"
                                    data-show="${media.show_name || 'Suits'}"
                                    style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer;">
                                <div style="flex: 1;">
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
                <h3 style="color: #34495e; margin-bottom: 10px;">Languages & Level</h3>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 10px; font-weight: 500;">Target Languages (Select multiple)</label>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <label class="language-checkbox-label" style="display: flex; align-items: center; cursor: pointer; padding: 10px; border-radius: 5px; transition: all 0.2s; border: 2px solid #e0e0e0;">
                            <input type="checkbox" class="language-checkbox" value="ko" checked style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer; accent-color: #3498db;">
                            <span style="font-weight: 500; color: #2c3e50;">Korean (한국어)</span>
                        </label>
                        <label class="language-checkbox-label" style="display: flex; align-items: center; cursor: pointer; padding: 10px; border-radius: 5px; transition: all 0.2s; border: 2px solid #e0e0e0;">
                            <input type="checkbox" class="language-checkbox" value="ja" style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer; accent-color: #3498db;">
                            <span style="font-weight: 500; color: #2c3e50;">Japanese (日本語)</span>
                        </label>
                        <label class="language-checkbox-label" style="display: flex; align-items: center; cursor: pointer; padding: 10px; border-radius: 5px; transition: all 0.2s; border: 2px solid #e0e0e0;">
                            <input type="checkbox" class="language-checkbox" value="zh" style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer; accent-color: #3498db;">
                            <span style="font-weight: 500; color: #2c3e50;">Chinese (中文)</span>
                        </label>
                        <label class="language-checkbox-label" style="display: flex; align-items: center; cursor: pointer; padding: 10px; border-radius: 5px; transition: all 0.2s; border: 2px solid #e0e0e0;">
                            <input type="checkbox" class="language-checkbox" value="en" style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer; accent-color: #3498db;">
                            <span style="font-weight: 500; color: #2c3e50;">English</span>
                        </label>
                        <label class="language-checkbox-label" style="display: flex; align-items: center; cursor: pointer; padding: 10px; border-radius: 5px; transition: all 0.2s; border: 2px solid #e0e0e0;">
                            <input type="checkbox" class="language-checkbox" value="es" style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer; accent-color: #3498db;">
                            <span style="font-weight: 500; color: #2c3e50;">Spanish (Español)</span>
                        </label>
                        <label class="language-checkbox-label" style="display: flex; align-items: center; cursor: pointer; padding: 10px; border-radius: 5px; transition: all 0.2s; border: 2px solid #e0e0e0;">
                            <input type="checkbox" class="language-checkbox" value="fr" style="margin-right: 10px; width: 20px; height: 20px; cursor: pointer; accent-color: #3498db;">
                            <span style="font-weight: 500; color: #2c3e50;">French (Français)</span>
                        </label>
                    </div>
                    <p style="margin-top: 8px; font-size: 0.9em; color: #7f8c8d;">💡 Tip: Select multiple languages to generate videos for all selected languages at once!</p>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Language Level</label>
                    <select id="languageLevel" style="width: 100%; padding: 10px; border: 1px solid #ecf0f1; border-radius: 6px;">
                        <option value="beginner">Beginner</option>
                        <option value="intermediate">Intermediate</option>
                        <option value="advanced">Advanced</option>
                        <option value="mixed">Mixed</option>
                    </select>
                </div>
            </div>

            <div style="margin-bottom: 20px;">
                <h3 style="color: #34495e; margin-bottom: 10px;">Options</h3>
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin-bottom: 15px;">
                    <input type="checkbox" id="testModeCheckbox" style="width: 18px; height: 18px; cursor: pointer;">
                    <span style="font-weight: 500;">Test Mode (Process only first chunk for testing)</span>
                </label>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Short-form Max Duration (seconds)</label>
                    <input type="number" id="shortFormMaxDuration" value="180" min="60" max="300" step="10" 
                           style="width: 100%; padding: 10px; border: 1px solid #ecf0f1; border-radius: 6px;">
                    <small style="color: #7f8c8d; display: block; margin-top: 5px;">Videos exceeding this duration will be dropped from batching (default: 180)</small>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Video Formats to Create</label>
                    <div style="display: flex; gap: 20px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="createLongFormCheckbox" checked style="width: 18px; height: 18px; cursor: pointer;">
                            <span style="font-weight: 500;">Long Form (Combined)</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="createShortFormCheckbox" checked style="width: 18px; height: 18px; cursor: pointer;">
                            <span style="font-weight: 500;">Short Form (Vertical)</span>
                        </label>
                    </div>
                </div>
            </div>

            <div style="margin-bottom: 20px; border-top: 1px solid #ecf0f1; padding-top: 20px;">
                <h3 style="color: #34495e; margin-bottom: 10px;">Auto Upload</h3>
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin-bottom: 10px;">
                    <input type="checkbox" id="autoUploadCheckbox" style="width: 18px; height: 18px; cursor: pointer;">
                    <span style="font-weight: 500;">Auto Upload to YouTube</span>
                </label>
                
                <div id="uploadOptions" style="display: none; margin-left: 28px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e0e0e0;">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 500;">Timing</label>
                        <div style="display: flex; gap: 20px;">
                            <label style="display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="radio" name="uploadTiming" value="scheduled" checked> 
                                <span>Scheduled (Recommended)</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="radio" name="uploadTiming" value="immediate"> 
                                <span>Immediate (Private)</span>
                            </label>
                        </div>
                    </div>
                    <div>
                        <p style="margin-bottom: 8px; font-weight: 500;">Note: Videos will be uploaded based on "Video Formats to Create" selection above.</p>
                    </div>
                </div>
            </div>

            <div style="margin-bottom: 15px; padding: 15px; background: #f0f9ff; border-radius: 8px; border-left: 3px solid #3498db;">
                <strong>Note:</strong> This will create both a final video and short videos (2-3 minutes each). Expressions will be selected automatically by AI.
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

        // Add CSS for language checkbox hover effects
        const style = document.createElement('style');
        style.textContent = `
            .language-checkbox-label:hover {
                background: #e8f4f8 !important;
                border-color: #3498db !important;
            }
            .language-checkbox-label:has(input:checked) {
                background: #d4edda !important;
                border-color: #27ae60 !important;
            }
        `;
        document.head.appendChild(style);

        modal.appendChild(dialog);
        document.body.appendChild(modal);

        // Setup auto-upload toggle
        const autoUploadCheckbox = dialog.querySelector('#autoUploadCheckbox');
        const uploadOptions = dialog.querySelector('#uploadOptions');
        autoUploadCheckbox.addEventListener('change', () => {
            uploadOptions.style.display = autoUploadCheckbox.checked ? 'block' : 'none';
        });

        // Event listeners
        dialog.querySelector('#cancelBtn').addEventListener('click', () => {
            modal.remove();
            style.remove();
        });

        dialog.querySelector('#createBtn').addEventListener('click', async () => {
            const selectedMedia = Array.from(dialog.querySelectorAll('.media-checkbox:checked'));
            if (selectedMedia.length === 0) {
                alert('Please select at least one media file');
                return;
            }

            const selectedLanguages = Array.from(dialog.querySelectorAll('.language-checkbox:checked')).map(cb => cb.value);
            if (selectedLanguages.length === 0) {
                alert('Please select at least one target language');
                return;
            }

            const languageLevel = dialog.querySelector('#languageLevel').value;
            const testMode = dialog.querySelector('#testModeCheckbox').checked;
            const shortFormMaxDuration = parseFloat(dialog.querySelector('#shortFormMaxDuration').value);
            const createLongForm = dialog.querySelector('#createLongFormCheckbox').checked;
            const createShortForm = dialog.querySelector('#createShortFormCheckbox').checked;
            const autoUpload = dialog.querySelector('#autoUploadCheckbox').checked;
            const uploadTiming = autoUpload ? dialog.querySelector('input[name="uploadTiming"]:checked').value : null;

            // Close modal immediately
            modal.remove();
            style.remove();

            // Show progress panel at bottom
            ui.showProgressPanel(selectedMedia.length);

            // Create content for each selected media
            let successCount = 0;
            let errorCount = 0;

            for (let i = 0; i < selectedMedia.length; i++) {
                const checkbox = selectedMedia[i];
                try {
                    ui.updateProgressPanel(i + 1, selectedMedia.length, `Processing ${checkbox.dataset.episode}...`);

                    const response = await fetch('/api/content/create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            media_id: checkbox.value,
                            video_path: checkbox.dataset.video,
                            subtitle_path: checkbox.dataset.subtitle,
                            language_code: 'en', // Source language
                            target_languages: selectedLanguages,
                            language_level: languageLevel,
                            test_mode: testMode,
                            create_long_form: createLongForm,
                            create_short_form: createShortForm,
                            short_form_max_duration: shortFormMaxDuration,
                            auto_upload_config: autoUpload ? {
                                enabled: true,
                                timing: uploadTiming
                            } : null
                        })
                    });

                    const result = await response.json();
                    if (response.ok) {
                        console.log('Job created:', result.job_id);
                        successCount++;
                        ui.updateProgressPanel(i + 1, selectedMedia.length, `✓ Created job for ${checkbox.dataset.episode}`);
                    } else {
                        console.error('Error creating job:', result.error);
                        errorCount++;
                        ui.updateProgressPanel(i + 1, selectedMedia.length, `✗ Error: ${result.error}`);
                    }
                } catch (error) {
                    console.error('Error:', error);
                    errorCount++;
                    ui.updateProgressPanel(i + 1, selectedMedia.length, `✗ Error: ${error.message}`);
                }
            }

            // Final update
            ui.updateProgressPanel(
                selectedMedia.length,
                selectedMedia.length,
                `Complete! ${successCount} succeeded, ${errorCount} failed.`,
                true
            );
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                style.remove();
            }
        });
    },

    showProgressPanel(totalJobs) {
        // Remove any existing progress panel
        const existing = document.getElementById('progressPanel');
        if (existing) existing.remove();

        // Create progress panel at bottom
        const panel = document.createElement('div');
        panel.id = 'progressPanel';
        panel.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            z-index: 1000;
            padding: 20px;
        `;

        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #2c3e50; font-size: 1.2em;">📦 Creating Content</h3>
                <button id="closeProgressBtn" style="padding: 8px 16px; border: none; border-radius: 6px; background: #ecf0f1; cursor: pointer;">
                    Close
                </button>
            </div>
            <div style="margin-bottom: 10px;">
                <div style="background: #ecf0f1; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div id="progressBar" style="background: #3498db; height: 100%; width: 0%; transition: width 0.3s;"></div>
                </div>
            </div>
            <div id="progressStatus" style="color: #7f8c8d; font-size: 0.9em;">
                Starting...
            </div>
            <div id="progressLog" style="margin-top: 10px; max-height: 200px; overflow-y: auto; font-size: 0.85em; color: #555;">
            </div>
        `;

        document.body.appendChild(panel);

        // Close button handler
        panel.querySelector('#closeProgressBtn').addEventListener('click', () => {
            panel.remove();
        });
    },

    updateProgressPanel(current, total, message, isComplete = false) {
        const panel = document.getElementById('progressPanel');
        if (!panel) return;

        const progressBar = panel.querySelector('#progressBar');
        const progressStatus = panel.querySelector('#progressStatus');
        const progressLog = panel.querySelector('#progressLog');

        // Update progress bar
        const percentage = (current / total) * 100;
        progressBar.style.width = `${percentage}%`;

        if (isComplete) {
            progressBar.style.background = '#27ae60';
        }

        // Update status
        progressStatus.textContent = `${current} / ${total} - ${message}`;

        // Add to log
        const logEntry = document.createElement('div');
        logEntry.style.cssText = 'padding: 4px 0; border-bottom: 1px solid #ecf0f1;';
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        progressLog.appendChild(logEntry);

        // Auto-scroll to bottom
        progressLog.scrollTop = progressLog.scrollHeight;
    }
};
