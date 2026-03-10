import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Linkedin,
  CheckCircle,
  XCircle,
  Clock,
  Trash2,
  Filter,
  Calendar,
  Send,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { getPosts, deletePost, PostRecord } from '../services/api';
import { format, formatDistanceToNow } from 'date-fns';

const statusFilters = [
  { value: '', label: 'All' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'posted', label: 'Posted' },
  { value: 'failed', label: 'Failed' },
];

export default function PostHistory() {
  const [posts, setPosts] = useState<PostRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedPost, setExpandedPost] = useState<string | null>(null);

  useEffect(() => {
    setPosts(getPosts());
    console.log('[SkynetJoe] Queue loaded. Posts:', getPosts().length);
  }, []);

  const filteredPosts = statusFilter
    ? posts.filter((p) => p.status === statusFilter)
    : posts;

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this post from history?')) return;
    deletePost(id);
    setPosts(getPosts());
    toast.success('Post removed');
  };

  const toggleExpand = (id: string) => {
    setExpandedPost(expandedPost === id ? null : id);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'posted':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'scheduled':
        return <Clock className="w-5 h-5 text-blue-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      posted: 'bg-green-100 text-green-700',
      scheduled: 'bg-blue-100 text-blue-700',
      failed: 'bg-red-100 text-red-700',
      pending: 'bg-gray-100 text-gray-600',
    };
    return (
      <span
        className={`px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const scheduledCount = posts.filter(
    (p) => p.status === 'scheduled'
  ).length;
  const postedCount = posts.filter((p) => p.status === 'posted').length;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Post Queue</h1>
          <p className="text-gray-500 mt-1">
            {posts.length === 0
              ? 'No posts yet'
              : `${postedCount} posted, ${scheduledCount} scheduled`}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-40"
            >
              {statusFilters.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>
          <Link to="/create" className="btn btn-primary flex items-center gap-2">
            <Send className="w-4 h-4" />
            New Post
          </Link>
        </div>
      </div>

      {/* Quick stats */}
      {posts.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="card py-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">
                  {postedCount}
                </p>
                <p className="text-xs text-gray-500">Posted</p>
              </div>
            </div>
          </div>
          <div className="card py-4">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">
                  {scheduledCount}
                </p>
                <p className="text-xs text-gray-500">Scheduled</p>
              </div>
            </div>
          </div>
          <div className="card py-4">
            <div className="flex items-center gap-3">
              <XCircle className="w-5 h-5 text-red-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">
                  {posts.filter((p) => p.status === 'failed').length}
                </p>
                <p className="text-xs text-gray-500">Failed</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {filteredPosts.length === 0 ? (
        <div className="card text-center py-16">
          <Calendar className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <p className="text-gray-500 text-lg mb-2">
            {statusFilter
              ? `No ${statusFilter} posts`
              : 'No posts yet'}
          </p>
          <p className="text-gray-400 text-sm mb-6">
            Create a post and it will show up here
          </p>
          <Link
            to="/create"
            className="btn btn-primary inline-flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            Create Post
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredPosts.map((post) => {
            const isExpanded = expandedPost === post.id;
            return (
              <div
                key={post.id}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => toggleExpand(post.id)}
              >
                <div className="flex gap-4">
                  {post.imagePreview && (
                    <img
                      src={post.imagePreview}
                      alt=""
                      className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-gray-900 text-sm truncate">
                          {post.caption}
                        </p>
                        <div className="flex items-center gap-3 mt-2 flex-wrap">
                          {getStatusIcon(post.status)}
                          {getStatusBadge(post.status)}
                          <div className="flex items-center gap-1">
                            <Linkedin className="w-3.5 h-3.5 text-blue-700" />
                            <span className="text-xs text-gray-500">
                              LinkedIn
                            </span>
                          </div>
                          {post.scheduledDate &&
                            post.status === 'scheduled' && (
                              <span className="text-xs text-blue-600 font-medium">
                                {formatDistanceToNow(
                                  new Date(post.scheduledDate),
                                  { addSuffix: true }
                                )}
                              </span>
                            )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <span className="text-xs text-gray-400">
                          {format(
                            new Date(post.createdAt),
                            'MMM d, h:mm a'
                          )}
                        </span>
                        <button
                          onClick={(e) => handleDelete(post.id, e)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="bg-gray-50 rounded-lg p-4 mb-3">
                      <p className="text-sm text-gray-800 whitespace-pre-wrap">
                        {post.caption}
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Image:</span>{' '}
                        <span className="text-gray-700">
                          {post.imageName || 'N/A'} (
                          {post.imageSize
                            ? `${(post.imageSize / 1024 / 1024).toFixed(1)} MB`
                            : 'N/A'}
                          )
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Platform:</span>{' '}
                        <span className="text-gray-700">LinkedIn</span>
                      </div>
                      {post.scheduledDate && (
                        <div>
                          <span className="text-gray-500">Scheduled:</span>{' '}
                          <span className="text-gray-700">
                            {format(
                              new Date(post.scheduledDate),
                              'MMM d, yyyy h:mm a'
                            )}
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-gray-500">Created:</span>{' '}
                        <span className="text-gray-700">
                          {format(
                            new Date(post.createdAt),
                            'MMM d, yyyy h:mm a'
                          )}
                        </span>
                      </div>
                    </div>
                    {post.webhookResponse && (
                      <div className="mt-3">
                        <span className="text-xs text-gray-500">
                          n8n Response:
                        </span>
                        <pre className="text-xs bg-gray-900 text-green-400 p-2 rounded mt-1 overflow-x-auto">
                          {post.webhookResponse}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
