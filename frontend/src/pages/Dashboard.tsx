import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PlusCircle,
  CheckCircle,
  Clock,
  Send,
  AlertCircle,
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Youtube,
} from 'lucide-react';
import { postsApi, platformsApi, Post, PlatformStatus, PlatformInfo } from '../services/api';

const platformIcons: Record<string, typeof Twitter> = {
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook,
  instagram_1: Instagram,
  instagram_2: Instagram,
  youtube: Youtube,
};

const platformLabels: Record<string, string> = {
  twitter: 'Twitter/X',
  linkedin: 'LinkedIn',
  facebook: 'Facebook',
  instagram_1: 'Instagram 1',
  instagram_2: 'Instagram 2',
  youtube: 'YouTube',
};

export default function Dashboard() {
  const [stats, setStats] = useState({
    draft: 0,
    scheduled: 0,
    posted: 0,
    failed: 0,
  });
  const [recentPosts, setRecentPosts] = useState<Post[]>([]);
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [postsData, platformData] = await Promise.all([
        postsApi.list({ limit: 10 }),
        platformsApi.getStatus(),
      ]);

      setRecentPosts(postsData.posts);
      setPlatformStatus(platformData.platforms);

      // Calculate stats
      const posts = postsData.posts as Post[];
      setStats({
        draft: posts.filter((p) => p.status === 'draft').length,
        scheduled: posts.filter((p) => p.status === 'scheduled').length,
        posted: posts.filter((p) => p.status === 'posted').length,
        failed: posts.filter((p) => p.status === 'failed').length,
      });
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }

  const statCards = [
    { label: 'Drafts', value: stats.draft, icon: Clock, color: 'text-gray-600', bg: 'bg-gray-50' },
    { label: 'Scheduled', value: stats.scheduled, icon: CheckCircle, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Posted', value: stats.posted, icon: Send, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Failed', value: stats.failed, icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
  ];

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  const connectedCount = platformStatus
    ? Object.values(platformStatus).filter((p) => p.connected).length
    : 0;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Your social media command center</p>
        </div>
        <Link to="/create" className="btn btn-primary flex items-center gap-2">
          <PlusCircle className="w-5 h-5" />
          Create Post
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => (
          <div key={stat.label} className="card">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.bg}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Platform Status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Connected Platforms</h2>
            <span className="text-sm text-gray-500">{connectedCount}/6</span>
          </div>
          <div className="space-y-3">
            {platformStatus &&
              Object.entries(platformStatus).map(([platform, info]) => {
                const Icon = platformIcons[platform] || CheckCircle;
                const platformInfo = info as PlatformInfo;
                const isConnected = platformInfo?.connected;
                const label = platformLabels[platform] || platform;

                return (
                  <div
                    key={platform}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5 text-gray-600" />
                      <span>{label}</span>
                    </div>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        isConnected
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {isConnected ? 'Connected' : 'Not connected'}
                    </span>
                  </div>
                );
              })}
          </div>
          <Link
            to="/settings"
            className="block text-center text-blue-600 text-sm mt-4 hover:underline"
          >
            Manage connections
          </Link>
        </div>

        {/* Recent Posts */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Posts</h2>
            <Link to="/history" className="text-blue-600 text-sm hover:underline">
              View all
            </Link>
          </div>
          <div className="space-y-4">
            {recentPosts.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">No posts yet. Create your first post!</p>
                <Link to="/create" className="btn btn-primary">
                  Create Post
                </Link>
              </div>
            ) : (
              recentPosts.slice(0, 5).map((post) => (
                <div
                  key={post.id}
                  className="flex items-start gap-4 py-3 border-b border-gray-100 last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 line-clamp-2">
                      {post.content.substring(0, 120)}
                      {post.content.length > 120 && '...'}
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          post.status === 'posted'
                            ? 'bg-green-100 text-green-700'
                            : post.status === 'failed'
                            ? 'bg-red-100 text-red-700'
                            : post.status === 'scheduled'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {post.status}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(post.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {post.platforms.map((platform) => {
                      const Icon = platformIcons[platform];
                      return Icon ? (
                        <Icon key={platform} className="w-4 h-4 text-gray-400" />
                      ) : null;
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Quick Tips */}
      {connectedCount === 0 && (
        <div className="card mt-6 bg-yellow-50 border-yellow-200">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
            <div>
              <p className="font-medium text-yellow-800">No platforms connected</p>
              <p className="text-sm text-yellow-700 mt-1">
                Go to <Link to="/settings" className="underline">Settings</Link> to connect your social media accounts and start posting.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
