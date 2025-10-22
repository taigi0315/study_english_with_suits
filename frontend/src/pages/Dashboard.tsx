import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { mediaApi, Media } from '../api/media';
import { expressionsApi, ExpressionStats } from '../api/expressions';

const Dashboard: React.FC = () => {
  const [recentMedia, setRecentMedia] = useState<Media[]>([]);
  const [stats, setStats] = useState<ExpressionStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [mediaResponse, statsResponse] = await Promise.all([
          mediaApi.listMedia({ limit: 5 }),
          expressionsApi.getExpressionStats(),
        ]);
        
        setRecentMedia(mediaResponse.media);
        setStats(statsResponse);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Welcome back! Here's your learning overview.</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Media</p>
                <p className="text-2xl font-semibold text-gray-900">{stats.total_media}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Expressions</p>
                <p className="text-2xl font-semibold text-gray-900">{stats.total_expressions}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Shows</p>
                <p className="text-2xl font-semibold text-gray-900">{Object.keys(stats.expressions_by_show).length}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Link
              to="/upload"
              className="btn-primary w-full text-center block"
            >
              Upload New Content
            </Link>
            <Link
              to="/library"
              className="btn-secondary w-full text-center block"
            >
              Browse Library
            </Link>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Media</h3>
          {recentMedia.length > 0 ? (
            <div className="space-y-3">
              {recentMedia.map((media) => (
                <Link
                  key={media.id}
                  to={`/media/${media.id}`}
                  className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-900">{media.show_name}</p>
                      <p className="text-sm text-gray-600">{media.episode_name}</p>
                    </div>
                    <span className="text-sm text-gray-500">{media.expression_count} expressions</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No media uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Recent Expressions */}
      {stats && stats.recent_expressions.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Expressions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.recent_expressions.slice(0, 6).map((expression) => (
              <div key={expression.id} className="p-4 bg-gray-50 rounded-lg">
                <p className="font-medium text-gray-900">{expression.expression}</p>
                {expression.expression_translation && (
                  <p className="text-sm text-gray-600 mt-1">{expression.expression_translation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
