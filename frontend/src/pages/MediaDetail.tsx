import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { mediaApi, MediaDetail as MediaDetailType, Expression } from '/src/api/media';
import VideoPlayer from '../components/VideoPlayer';

const MediaDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [media, setMedia] = useState<MediaDetailType | null>(null);
  const [expressions, setExpressions] = useState<Expression[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    if (id) {
      loadMediaDetail();
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      loadExpressions();
    }
  }, [id, currentPage]);

  const loadMediaDetail = async () => {
    try {
      const response = await mediaApi.getMediaDetail(id!);
      setMedia(response);
    } catch (error) {
      console.error('Failed to load media detail:', error);
    }
  };

  const loadExpressions = async () => {
    try {
      const response = await mediaApi.getMediaExpressions(id!, {
        page: currentPage,
        limit: 12,
      });
      setExpressions(response.expressions);
      setTotalPages(Math.ceil(response.total / 12));
    } catch (error) {
      console.error('Failed to load expressions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!media) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900">Media not found</h2>
        <p className="text-gray-600">The requested media could not be found.</p>
        <Link to="/library" className="btn-primary mt-4">
          Back to Library
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <nav className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
            <Link to="/library" className="hover:text-gray-700">Library</Link>
            <span>/</span>
            <span className="text-gray-900">{media.show_name}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">{media.show_name}</h1>
          <p className="text-xl text-gray-600">{media.episode_name}</p>
        </div>
        <div className="flex space-x-4">
          <button
            onClick={() => {
              // This would open a modal or navigate to video player
              const videoUrl = mediaApi.getFinalVideoUrl(id!);
              window.open(videoUrl, '_blank');
            }}
            className="btn-primary"
          >
            Watch Final Video
          </button>
        </div>
      </div>

      {/* Media Info */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Episode Details</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Show:</span>
                <span className="font-medium">{media.show_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Episode:</span>
                <span className="font-medium">{media.episode_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Language:</span>
                <span className="font-medium">{media.language_code.toUpperCase()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Expressions:</span>
                <span className="font-medium">{media.expression_count}</span>
              </div>
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Files</h3>
            <div className="space-y-2">
              {media.video_file_path && (
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <span className="text-sm text-gray-600">Video file available</span>
                </div>
              )}
              {media.subtitle_file_path && (
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm text-gray-600">Subtitle file available</span>
                </div>
              )}
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Timestamps</h3>
            <div className="space-y-2">
              {media.created_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Created:</span>
                  <span className="text-sm">{new Date(media.created_at).toLocaleDateString()}</span>
                </div>
              )}
              {media.updated_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Updated:</span>
                  <span className="text-sm">{new Date(media.updated_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Expressions */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Expressions</h2>
          <span className="text-sm text-gray-500">
            {expressions.length} of {media.expression_count} expressions
          </span>
        </div>

        {expressions.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {expressions.map((expression) => (
                <Link
                  key={expression.id}
                  to={`/expression/${expression.id}`}
                  className="card hover:shadow-lg transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {expression.expression}
                    </h3>
                    {expression.context_video_path && (
                      <svg className="w-4 h-4 text-primary-600 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    )}
                  </div>
                  
                  {expression.expression_translation && (
                    <p className="text-sm text-gray-600 mb-2">
                      {expression.expression_translation}
                    </p>
                  )}
                  
                  {expression.expression_dialogue && (
                    <p className="text-xs text-gray-500 italic">
                      "{expression.expression_dialogue}"
                    </p>
                  )}
                  
                  <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
                    <span>{expression.scene_type || 'dialogue'}</span>
                    {expression.context_start_time && (
                      <span>{expression.context_start_time}</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-2 mt-6">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                <span className="px-3 py-2 text-sm text-gray-700">
                  Page {currentPage} of {totalPages}
                </span>
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No expressions found</h3>
            <p className="mt-1 text-sm text-gray-500">
              This media doesn't have any expressions yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default MediaDetail;
