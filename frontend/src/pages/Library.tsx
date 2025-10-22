import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { mediaApi, Media } from '/src/api/media';

const Library: React.FC = () => {
  const [media, setMedia] = useState<Media[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedShow, setSelectedShow] = useState('');
  const [shows, setShows] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadMedia();
  }, [currentPage, selectedShow]);

  const loadMedia = async () => {
    try {
      setIsLoading(true);
      const response = await mediaApi.listMedia({
        show_name: selectedShow || undefined,
        page: currentPage,
        limit: 12,
      });
      
      setMedia(response.media);
      setTotalPages(Math.ceil(response.total / 12));
      
      // Extract unique show names
      const uniqueShows = [...new Set(response.media.map(m => m.show_name))];
      setShows(uniqueShows);
    } catch (error) {
      console.error('Failed to load media:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // For now, just reload with current filters
    loadMedia();
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedShow('');
    setCurrentPage(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Media Library</h1>
          <p className="text-gray-600">Browse your uploaded content and expressions.</p>
        </div>
        <Link
          to="/upload"
          className="btn-primary"
        >
          Upload New Content
        </Link>
      </div>

      {/* Filters */}
      <div className="card">
        <form onSubmit={handleSearch} className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-64">
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <input
              id="search"
              type="text"
              placeholder="Search by show or episode name..."
              className="input-field"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div className="min-w-48">
            <label htmlFor="show-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Show
            </label>
            <select
              id="show-filter"
              className="input-field"
              value={selectedShow}
              onChange={(e) => setSelectedShow(e.target.value)}
            >
              <option value="">All Shows</option>
              {shows.map(show => (
                <option key={show} value={show}>{show}</option>
              ))}
            </select>
          </div>
          
          <div className="flex gap-2">
            <button type="submit" className="btn-primary">
              Search
            </button>
            <button type="button" onClick={clearFilters} className="btn-secondary">
              Clear
            </button>
          </div>
        </form>
      </div>

      {/* Media Grid */}
      {media.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {media.map((item) => (
              <Link
                key={item.id}
                to={`/media/${item.id}`}
                className="card hover:shadow-lg transition-shadow"
              >
                <div className="aspect-video bg-gray-100 rounded-lg mb-4 flex items-center justify-center">
                  <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 truncate">{item.show_name}</h3>
                  <p className="text-sm text-gray-600 truncate">{item.episode_name}</p>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-gray-500">{item.language_code.toUpperCase()}</span>
                    <span className="text-xs text-primary-600 font-medium">
                      {item.expression_count} expressions
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center space-x-2">
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No media found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {selectedShow || searchTerm 
              ? 'Try adjusting your filters or search terms.'
              : 'Get started by uploading your first video.'
            }
          </p>
          <div className="mt-6">
            <Link to="/upload" className="btn-primary">
              Upload Content
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default Library;
