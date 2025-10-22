import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { expressionsApi, Expression } from '/src/api/expressions';
import { mediaApi } from '/src/api/media';
import VideoPlayer from '../components/VideoPlayer';

const ExpressionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [expression, setExpression] = useState<Expression | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [mediaId, setMediaId] = useState<string>('');

  useEffect(() => {
    if (id) {
      loadExpression();
    }
  }, [id]);

  const loadExpression = async () => {
    try {
      const response = await expressionsApi.getExpressionDetail(id!);
      setExpression(response);
      // Extract media_id from the expression (assuming it's available in the response)
      if (response.media_id) {
        setMediaId(response.media_id);
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to load expression');
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

  if (error) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900">Error</h2>
        <p className="text-gray-600">{error}</p>
        <Link to="/library" className="btn-primary mt-4">
          Back to Library
        </Link>
      </div>
    );
  }

  if (!expression) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900">Expression not found</h2>
        <p className="text-gray-600">The requested expression could not be found.</p>
        <Link to="/library" className="btn-primary mt-4">
          Back to Library
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <nav className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
            <Link to="/library" className="hover:text-gray-700">Library</Link>
            <span>/</span>
            <span className="text-gray-900">Expression</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">{expression.expression}</h1>
          {expression.expression_translation && (
            <p className="text-xl text-gray-600">{expression.expression_translation}</p>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Expression Details */}
        <div className="space-y-6">
          {/* Expression Info */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Expression Details</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expression</label>
                <p className="text-lg font-semibold text-gray-900">{expression.expression}</p>
              </div>
              
              {expression.expression_translation && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Translation</label>
                  <p className="text-gray-900">{expression.expression_translation}</p>
                </div>
              )}
              
              {expression.expression_dialogue && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Context Dialogue</label>
                  <p className="text-gray-900 italic">"{expression.expression_dialogue}"</p>
                  {expression.expression_dialogue_translation && (
                    <p className="text-sm text-gray-600 mt-1">
                      "{expression.expression_dialogue_translation}"
                    </p>
                  )}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                {expression.scene_type && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Scene Type</label>
                    <p className="text-gray-900 capitalize">{expression.scene_type}</p>
                  </div>
                )}
                
                {expression.context_start_time && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
                    <p className="text-gray-900">
                      {expression.context_start_time}
                      {expression.context_end_time && ` - ${expression.context_end_time}`}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Similar Expressions */}
          {expression.similar_expressions && expression.similar_expressions.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Similar Expressions</h3>
              <div className="space-y-2">
                {expression.similar_expressions.map((similar, index) => (
                  <div key={index} className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-gray-900">{similar}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Videos */}
        <div className="space-y-6">
          {/* Context Video */}
          {expression.context_video_path && mediaId && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Context Video</h3>
              <VideoPlayer
                src={mediaApi.getContextVideoUrl(mediaId, expression.id)}
                className="aspect-video"
                controls={true}
                poster="/api/placeholder/context-video.jpg"
              />
              <div className="mt-4 text-sm text-gray-600">
                <p>
                  <span className="font-medium">Time:</span> {expression.context_start_time} - {expression.context_end_time}
                </p>
              </div>
            </div>
          )}

          {/* Educational Slide */}
          {expression.slide_video_path && mediaId && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Educational Slide</h3>
              <VideoPlayer
                src={mediaApi.getSlideVideoUrl(mediaId, expression.id)}
                className="aspect-video"
                controls={true}
                poster="/api/placeholder/slide-video.jpg"
              />
              <div className="mt-4 text-sm text-gray-600">
                <p>
                  <span className="font-medium">Expression:</span> {expression.expression}
                </p>
                {expression.expression_translation && (
                  <p>
                    <span className="font-medium">Translation:</span> {expression.expression_translation}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Learning Actions */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Learning Actions</h3>
            <div className="space-y-3">
              <button className="btn-primary w-full">
                Add to Study Deck
              </button>
              <button className="btn-secondary w-full">
                Mark as Learned
              </button>
              <button className="btn-secondary w-full">
                Find Similar Expressions
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Study Notes Section */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Study Notes</h3>
        <div className="space-y-4">
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
              Add your notes about this expression
            </label>
            <textarea
              id="notes"
              rows={4}
              className="input-field"
              placeholder="Write your notes about this expression, how to use it, examples, etc."
            />
          </div>
          <div className="flex justify-end">
            <button className="btn-primary">
              Save Notes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExpressionDetail;
