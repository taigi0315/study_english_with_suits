import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsApi } from '/src/api/jobs';

interface UploadFormData {
  show_name: string;
  episode_name: string;
  language_code: string;
  max_expressions: number;
  language_level: string;
  test_mode: boolean;
  no_shorts: boolean;
}

const Upload: React.FC = () => {
  const [formData, setFormData] = useState<UploadFormData>({
    show_name: '',
    episode_name: '',
    language_code: 'en',
    max_expressions: 10,
    language_level: 'intermediate',
    test_mode: false,
    no_shorts: false,
  });
  
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [subtitleFile, setSubtitleFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  
  const videoInputRef = useRef<HTMLInputElement>(null);
  const subtitleInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }));
  };

  const handleFileSelect = (file: File, type: 'video' | 'subtitle') => {
    if (type === 'video') {
      if (!file.name.toLowerCase().match(/\.(mp4|mkv|avi)$/)) {
        setError('Please select a valid video file (MP4, MKV, or AVI)');
        return;
      }
      setVideoFile(file);
    } else {
      if (!file.name.toLowerCase().endsWith('.srt')) {
        setError('Please select a valid subtitle file (.srt)');
        return;
      }
      setSubtitleFile(file);
    }
    setError('');
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = Array.from(e.dataTransfer.files);
    const videoFile = files.find(f => f.name.toLowerCase().match(/\.(mp4|mkv|avi)$/));
    const subtitleFile = files.find(f => f.name.toLowerCase().endsWith('.srt'));
    
    if (videoFile) handleFileSelect(videoFile, 'video');
    if (subtitleFile) handleFileSelect(subtitleFile, 'subtitle');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!videoFile || !subtitleFile) {
      setError('Please select both video and subtitle files');
      return;
    }

    setIsUploading(true);
    setError('');

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('video_file', videoFile);
      formDataToSend.append('subtitle_file', subtitleFile);
      formDataToSend.append('show_name', formData.show_name);
      formDataToSend.append('episode_name', formData.episode_name);
      formDataToSend.append('language_code', formData.language_code);
      formDataToSend.append('max_expressions', formData.max_expressions.toString());
      formDataToSend.append('language_level', formData.language_level);
      formDataToSend.append('test_mode', formData.test_mode.toString());
      formDataToSend.append('no_shorts', formData.no_shorts.toString());

      const response = await jobsApi.createJob(formDataToSend);
      
      // Redirect to job status page or dashboard
      navigate('/dashboard', { 
        state: { 
          message: 'Upload successful! Processing has started.',
          jobId: response.job_id 
        }
      });
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload Content</h1>
        <p className="text-gray-600">Upload a video and subtitle file to start learning.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload Area */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Files</h3>
          
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive 
                ? 'border-primary-500 bg-primary-50' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
              <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div className="mt-4">
              <p className="text-lg font-medium text-gray-900">Drop files here</p>
              <p className="text-gray-600">or click to select files</p>
            </div>
            <div className="mt-4 flex justify-center space-x-4">
              <button
                type="button"
                onClick={() => videoInputRef.current?.click()}
                className="btn-secondary"
              >
                Select Video
              </button>
              <button
                type="button"
                onClick={() => subtitleInputRef.current?.click()}
                className="btn-secondary"
              >
                Select Subtitle
              </button>
            </div>
            <input
              ref={videoInputRef}
              type="file"
              accept=".mp4,.mkv,.avi"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0], 'video')}
              className="hidden"
            />
            <input
              ref={subtitleInputRef}
              type="file"
              accept=".srt"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0], 'subtitle')}
              className="hidden"
            />
          </div>

          {/* Selected Files */}
          <div className="mt-4 space-y-2">
            {videoFile && (
              <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-md">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <span className="text-sm font-medium text-green-800">{videoFile.name}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setVideoFile(null)}
                  className="text-green-600 hover:text-green-800"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
            
            {subtitleFile && (
              <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-md">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm font-medium text-green-800">{subtitleFile.name}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSubtitleFile(null)}
                  className="text-green-600 hover:text-green-800"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Form Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Content Information</h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="show_name" className="block text-sm font-medium text-gray-700 mb-1">
                  Show Name *
                </label>
                <input
                  id="show_name"
                  name="show_name"
                  type="text"
                  required
                  className="input-field"
                  value={formData.show_name}
                  onChange={handleInputChange}
                  placeholder="e.g., Suits"
                />
              </div>
              
              <div>
                <label htmlFor="episode_name" className="block text-sm font-medium text-gray-700 mb-1">
                  Episode Name *
                </label>
                <input
                  id="episode_name"
                  name="episode_name"
                  type="text"
                  required
                  className="input-field"
                  value={formData.episode_name}
                  onChange={handleInputChange}
                  placeholder="e.g., S01E01"
                />
              </div>
              
              <div>
                <label htmlFor="language_code" className="block text-sm font-medium text-gray-700 mb-1">
                  Language *
                </label>
                <select
                  id="language_code"
                  name="language_code"
                  className="input-field"
                  value={formData.language_code}
                  onChange={handleInputChange}
                >
                  <option value="en">English</option>
                  <option value="ko">Korean</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                </select>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Options</h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="max_expressions" className="block text-sm font-medium text-gray-700 mb-1">
                  Max Expressions
                </label>
                <input
                  id="max_expressions"
                  name="max_expressions"
                  type="number"
                  min="1"
                  max="50"
                  className="input-field"
                  value={formData.max_expressions}
                  onChange={handleInputChange}
                />
              </div>
              
              <div>
                <label htmlFor="language_level" className="block text-sm font-medium text-gray-700 mb-1">
                  Language Level
                </label>
                <select
                  id="language_level"
                  name="language_level"
                  className="input-field"
                  value={formData.language_level}
                  onChange={handleInputChange}
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="test_mode"
                    checked={formData.test_mode}
                    onChange={handleInputChange}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Test Mode (faster processing)</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="no_shorts"
                    checked={formData.no_shorts}
                    onChange={handleInputChange}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Skip Short Videos</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate('/library')}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isUploading || !videoFile || !subtitleFile}
            className="btn-primary"
          >
            {isUploading ? 'Uploading...' : 'Start Processing'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Upload;
