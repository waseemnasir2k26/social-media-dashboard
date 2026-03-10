import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PlusCircle,
  CheckCircle,
  Clock,
  Send,
  Linkedin,
  AlertCircle,
  Zap,
} from 'lucide-react';
import { getPosts, getWebhookUrl, PostRecord } from '../services/api';

export default function Dashboard() {
  const [posts, setPosts] = useState<PostRecord[]>([]);
  const webhookUrl = getWebhookUrl();
  const webhookConfigured = !!webhookUrl;

  useEffect(() => {
    setPosts(getPosts());
    console.log(
      '[SkynetJoe] Dashboard loaded. Posts:',
      getPosts().length,
      '| Webhook:',
      webhookConfigured ? 'configured' : 'not set'
    );
  }, []);

  const stats = {
    total: posts.length,
    scheduled: posts.filter((p) => p.status === 'scheduled').length,
    posted: posts.filter((p) => p.status === 'posted').length,
    failed: posts.filter((p) => p.status === 'failed').length,
  };

  const statCards = [
    {
      label: 'Total Posts',
      value: stats.total,
      icon: Send,
      color: 'text-gray-600',
      bg: 'bg-gray-50',
    },
    {
      label: 'Scheduled',
      value: stats.scheduled,
      icon: Clock,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Posted',
      value: stats.posted,
      icon: CheckCircle,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Failed',
      value: stats.failed,
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ];

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">SkynetJoe Social Media Hub</p>
        </div>
        <Link
          to="/create"
          className="btn btn-primary flex items-center gap-2"
        >
          <PlusCircle className="w-5 h-5" />
          Create Post
        </Link>
      </div>

      {/* Webhook Warning */}
      {!webhookConfigured && (
        <div className="card mb-6 bg-yellow-50 border-yellow-200">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
            <div>
              <p className="font-medium text-yellow-800">
                n8n Webhook not configured
              </p>
              <p className="text-sm text-yellow-700 mt-1">
                Go to{' '}
                <Link to="/settings" className="underline font-medium">
                  Settings
                </Link>{' '}
                and paste your n8n webhook URL to start posting.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Platform Card */}
      <div className="card mb-6">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-blue-700 text-white">
            <Linkedin className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <p className="font-semibold text-gray-900">LinkedIn</p>
            <p className="text-sm text-gray-500">
              Connected via n8n automation
            </p>
          </div>
          {webhookConfigured && (
            <div className="flex items-center gap-2 text-green-600">
              <Zap className="w-4 h-4" />
              <span className="text-sm font-medium">Webhook active</span>
            </div>
          )}
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              webhookConfigured
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {webhookConfigured ? 'Ready' : 'Setup needed'}
          </span>
        </div>
        {webhookConfigured && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-400 font-mono truncate">
              {webhookUrl}
            </p>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {statCards.map((stat) => (
          <div key={stat.label} className="card hover:shadow-md transition-shadow">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.bg}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Posts */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Posts</h2>
          {posts.length > 0 && (
            <Link
              to="/history"
              className="text-blue-600 text-sm hover:underline"
            >
              View all ({posts.length})
            </Link>
          )}
        </div>
        {posts.length === 0 ? (
          <div className="text-center py-10">
            <Send className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-4">
              No posts yet. Create your first post!
            </p>
            <Link to="/create" className="btn btn-primary">
              Create Post
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {posts.slice(0, 5).map((post) => (
              <Link
                key={post.id}
                to="/history"
                className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {post.imagePreview && (
                  <img
                    src={post.imagePreview}
                    alt=""
                    className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 truncate">
                    {post.caption}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <Linkedin className="w-3 h-3 text-blue-700" />
                    <span className="text-xs text-gray-500">
                      {new Date(post.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ${
                    post.status === 'posted'
                      ? 'bg-green-100 text-green-700'
                      : post.status === 'scheduled'
                      ? 'bg-blue-100 text-blue-700'
                      : post.status === 'failed'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {post.status}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
