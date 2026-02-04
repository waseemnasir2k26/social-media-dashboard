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
} from 'lucide-react';
import { postsApi, platformsApi, Post, PlatformStatus, PlatformInfo } from '../services/api';

const platformIcons: Record<string, typeof Twitter> = {
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook,
  instagram: Instagram,
};

export default function Dashboard() {
  const [stats, setStats] = useState({
    pending: 0,
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
        pending: posts.filter((p) => p.status === 'pending_approval').length,
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
    { label: 'Pending Approval', value: stats.pending, icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
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

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Manage your social media content</p>
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
          <h2 className="text-lg font-semibold mb-4">Platform Status</h2>
          <div className="space-y-3">
            {platformStatus &&
              Object.entries(platformStatus).map(([platform, info]) => {
                const Icon = platformIcons[platform] || CheckCircle;
                const platformInfo = info as PlatformInfo;
                const isConnected = platformInfo?.connected;
                return (
                  <div
                    key={platform}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5 text-gray-600" />
                      <span className="capitalize">{platform}</span>
                    </div>
                    <span
                      className={`badge ${isConnected ? 'badge-posted' : 'badge-failed'}`}
                    >
                      {isConnected ? 'Connected' : 'Not configured'}
                    </span>
                  </div>
                );
              })}
          </div>
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
              <p className="text-gray-500 text-center py-8">
                No posts yet. Create your first post!
              </p>
            ) : (
              recentPosts.slice(0, 5).map((post) => (
                <div
                  key={post.id}
                  className="flex items-start gap-4 py-3 border-b border-gray-100 last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 line-clamp-2">
                      {post.content.substring(0, 120)}...
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className={`badge badge-${post.status.replace('_', '-')}`}>
                        {post.status.replace('_', ' ')}
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
    </div>
  );
}
