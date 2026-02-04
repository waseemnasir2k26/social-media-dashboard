import { useEffect, useState } from 'react';
import {
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
} from 'lucide-react';
import { postsApi, Post } from '../services/api';
import { format } from 'date-fns';

const platformIcons: Record<string, typeof Twitter> = {
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook,
  instagram: Instagram,
};

const statusFilters = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'pending_approval', label: 'Pending' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'posted', label: 'Posted' },
  { value: 'failed', label: 'Failed' },
];

export default function PostHistory() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);

  useEffect(() => {
    loadPosts();
  }, [statusFilter]);

  async function loadPosts() {
    setLoading(true);
    try {
      const result = await postsApi.list({
        status: statusFilter || undefined,
        limit: 100,
      });
      setPosts(result.posts);
    } catch (error) {
      console.error('Failed to load posts:', error);
    } finally {
      setLoading(false);
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'posted':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'scheduled':
        return <Clock className="w-5 h-5 text-purple-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Post History</h1>
          <p className="text-gray-500 mt-1">View all your posts and their status</p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input w-40"
          >
            {statusFilters.map((filter) => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      ) : posts.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No posts found</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                  Content
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                  Platforms
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {posts.map((post) => (
                <tr
                  key={post.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedPost(post)}
                >
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(post.status)}
                      <span
                        className={`badge badge-${post.status.replace('_', '-')}`}
                      >
                        {post.status.replace('_', ' ')}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-gray-900 line-clamp-2 max-w-md">
                      {post.content.substring(0, 100)}...
                    </p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-sm text-gray-600 capitalize">
                      {post.content_type}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex gap-1">
                      {post.platforms.map((platform) => {
                        const Icon = platformIcons[platform];
                        const isPosted = post.posted_ids?.[platform];
                        return Icon ? (
                          <div
                            key={platform}
                            className={`p-1 rounded ${
                              isPosted ? 'text-green-600' : 'text-gray-400'
                            }`}
                            title={isPosted ? 'Posted' : 'Not posted'}
                          >
                            <Icon className="w-4 h-4" />
                          </div>
                        ) : null;
                      })}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-gray-600">
                      {format(new Date(post.created_at), 'MMM d, yyyy')}
                    </p>
                    <p className="text-xs text-gray-400">
                      {format(new Date(post.created_at), 'h:mm a')}
                    </p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Post Detail Modal */}
      {selectedPost && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedPost(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold">Post Details</h2>
              <span className={`badge badge-${selectedPost.status.replace('_', '-')}`}>
                {selectedPost.status.replace('_', ' ')}
              </span>
            </div>

            <div className="p-6 space-y-4">
              {/* Content */}
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-2">
                  Content
                </label>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-900 whitespace-pre-wrap text-sm">
                    {selectedPost.content}
                  </p>
                </div>
              </div>

              {/* Image */}
              {selectedPost.image_url && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-2">
                    Image
                  </label>
                  <img
                    src={selectedPost.image_url}
                    alt="Post image"
                    className="max-w-sm rounded-lg shadow-sm"
                  />
                </div>
              )}

              {/* Meta Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Content Type
                  </label>
                  <p className="capitalize">{selectedPost.content_type}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Word Count
                  </label>
                  <p>{selectedPost.word_count} words</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Created
                  </label>
                  <p>
                    {format(new Date(selectedPost.created_at), 'MMM d, yyyy h:mm a')}
                  </p>
                </div>
                {selectedPost.posted_time && (
                  <div>
                    <label className="block text-sm font-medium text-gray-500 mb-1">
                      Posted
                    </label>
                    <p>
                      {format(
                        new Date(selectedPost.posted_time),
                        'MMM d, yyyy h:mm a'
                      )}
                    </p>
                  </div>
                )}
              </div>

              {/* Platform Results */}
              {selectedPost.status === 'posted' && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-2">
                    Platform Results
                  </label>
                  <div className="space-y-2">
                    {selectedPost.platforms.map((platform) => {
                      const Icon = platformIcons[platform];
                      const postId = selectedPost.posted_ids?.[platform];
                      return (
                        <div
                          key={platform}
                          className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg"
                        >
                          {Icon && <Icon className="w-5 h-5" />}
                          <span className="capitalize flex-1">{platform}</span>
                          {postId ? (
                            <span className="text-sm text-green-600">
                              Posted (ID: {postId.substring(0, 20)}...)
                            </span>
                          ) : (
                            <span className="text-sm text-red-600">Failed</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Error Message */}
              {selectedPost.error_message && (
                <div>
                  <label className="block text-sm font-medium text-red-500 mb-2">
                    Error
                  </label>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-red-700 text-sm">
                      {selectedPost.error_message}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 border-t">
              <button
                onClick={() => setSelectedPost(null)}
                className="btn btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
