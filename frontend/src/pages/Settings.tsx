import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Youtube,
  CheckCircle,
  XCircle,
  ExternalLink,
  Info,
  Link2,
  Unlink,
  Loader2,
} from 'lucide-react';
import api from '../services/api';

interface PlatformInfo {
  connected: boolean;
  oauth_configured: boolean;
  page_name?: string;
  account_name?: string;
}

interface PlatformStatus {
  linkedin: PlatformInfo;
  twitter: PlatformInfo;
  facebook: PlatformInfo;
  instagram_1: PlatformInfo;
  instagram_2: PlatformInfo;
  youtube: PlatformInfo;
}

const platformConfig = [
  {
    id: 'facebook',
    name: 'Facebook Page',
    icon: Facebook,
    color: 'bg-blue-600',
    description: 'Post to your Facebook Page',
  },
  {
    id: 'instagram_1',
    name: 'Instagram Account 1',
    icon: Instagram,
    color: 'bg-gradient-to-r from-purple-500 to-pink-500',
    description: 'Your first Instagram Business account',
  },
  {
    id: 'instagram_2',
    name: 'Instagram Account 2',
    icon: Instagram,
    color: 'bg-gradient-to-r from-pink-500 to-orange-500',
    description: 'Your second Instagram Business account',
  },
  {
    id: 'twitter',
    name: 'Twitter/X',
    icon: Twitter,
    color: 'bg-black',
    description: 'Tweet to your account',
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: Youtube,
    color: 'bg-red-600',
    description: 'Upload videos to your channel',
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    icon: Linkedin,
    color: 'bg-blue-700',
    description: 'Post to your LinkedIn profile',
  },
];

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    // Handle OAuth callback messages
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');

    if (connected) {
      toast.success(`${connected} connected successfully!`);
      setSearchParams({});
      loadStatus();
    }

    if (error) {
      toast.error(`Connection failed: ${error}`);
      setSearchParams({});
    }

    loadStatus();
  }, [searchParams, setSearchParams]);

  async function loadStatus() {
    try {
      const result = await api.get('/platforms/status');
      setPlatformStatus(result.data.platforms);
    } catch (error) {
      console.error('Failed to load platform status:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleConnect(platformId: string) {
    setConnecting(platformId);
    try {
      const response = await api.get(`/auth/${platformId}/connect`);
      const { auth_url } = response.data;

      if (auth_url) {
        // Redirect to OAuth provider
        window.location.href = auth_url;
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to start connection';
      toast.error(message);
      setConnecting(null);
    }
  }

  async function handleDisconnect(platformId: string) {
    if (!confirm(`Are you sure you want to disconnect ${platformId}?`)) return;

    try {
      await api.post(`/auth/${platformId}/disconnect`);
      toast.success(`${platformId} disconnected`);
      loadStatus();
    } catch (error) {
      toast.error('Failed to disconnect');
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Connect your social media accounts</p>
      </div>

      {/* Platform Connections */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold mb-6">Connected Accounts</h2>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : (
          <div className="space-y-4">
            {platformConfig.map((platform) => {
              const status = platformStatus?.[platform.id as keyof PlatformStatus];
              const isConnected = status?.connected;
              const isConfigured = status?.oauth_configured;
              const displayName = status?.page_name || status?.account_name || platform.name;

              return (
                <div
                  key={platform.id}
                  className="flex items-center justify-between p-4 border rounded-xl hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-xl ${platform.color} text-white`}>
                      <platform.icon className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{platform.name}</p>
                      <p className="text-sm text-gray-500">
                        {isConnected
                          ? displayName
                          : platform.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {isConnected ? (
                      <>
                        <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
                          <CheckCircle className="w-4 h-4" />
                          Connected
                        </span>
                        <button
                          onClick={() => handleDisconnect(platform.id)}
                          className="btn btn-secondary text-sm flex items-center gap-1"
                        >
                          <Unlink className="w-4 h-4" />
                          Disconnect
                        </button>
                      </>
                    ) : isConfigured ? (
                      <button
                        onClick={() => handleConnect(platform.id)}
                        disabled={connecting === platform.id}
                        className={`btn ${platform.color} text-white flex items-center gap-2`}
                      >
                        {connecting === platform.id ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          <>
                            <Link2 className="w-4 h-4" />
                            Connect
                          </>
                        )}
                      </button>
                    ) : (
                      <span className="flex items-center gap-1 text-gray-400 text-sm">
                        <XCircle className="w-4 h-4" />
                        Not configured
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Setup Instructions */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Setup Guide</h2>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex gap-3">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-2">How to connect your accounts</p>
              <p>
                Create OAuth apps on each platform and add the credentials to your Vercel environment variables.
                The callback URL pattern is: <code className="bg-blue-100 px-1 rounded">https://your-domain.vercel.app/api/auth/[platform]/callback</code>
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Facebook & Instagram Setup */}
          <div className="border-b pb-6">
            <h3 className="font-medium flex items-center gap-2 mb-3">
              <Facebook className="w-5 h-5 text-blue-600" />
              Facebook & Instagram (Meta)
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
              <li>Go to <a href="https://developers.facebook.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Meta for Developers <ExternalLink className="w-3 h-3 inline" /></a></li>
              <li>Create a new app (type: Business)</li>
              <li>Add Facebook Login product</li>
              <li>Add callback URL: <code className="bg-gray-100 px-1 rounded">https://your-domain/api/auth/facebook/callback</code></li>
              <li>Request permissions: pages_manage_posts, pages_read_engagement, instagram_basic, instagram_content_publish, business_management</li>
              <li>Link your Instagram Business accounts to your Facebook Pages</li>
            </ol>
            <div className="bg-gray-50 rounded-lg p-3 font-mono text-sm mt-3">
              <div>FACEBOOK_APP_ID=your_app_id</div>
              <div>FACEBOOK_APP_SECRET=your_app_secret</div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              Both Instagram accounts will be detected automatically when you connect Facebook.
            </p>
          </div>

          {/* Twitter Setup */}
          <div className="border-b pb-6">
            <h3 className="font-medium flex items-center gap-2 mb-3">
              <Twitter className="w-5 h-5" />
              Twitter/X
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
              <li>Go to <a href="https://developer.twitter.com/en/portal/dashboard" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Twitter Developer Portal <ExternalLink className="w-3 h-3 inline" /></a></li>
              <li>Create a project and app</li>
              <li>Enable OAuth 2.0 with "Read and write" permissions</li>
              <li>Add callback URL: <code className="bg-gray-100 px-1 rounded">https://your-domain/api/auth/twitter/callback</code></li>
            </ol>
            <div className="bg-gray-50 rounded-lg p-3 font-mono text-sm mt-3">
              <div>TWITTER_CLIENT_ID=your_client_id</div>
              <div>TWITTER_CLIENT_SECRET=your_client_secret</div>
            </div>
          </div>

          {/* YouTube Setup */}
          <div className="border-b pb-6">
            <h3 className="font-medium flex items-center gap-2 mb-3">
              <Youtube className="w-5 h-5 text-red-600" />
              YouTube
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
              <li>Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Cloud Console <ExternalLink className="w-3 h-3 inline" /></a></li>
              <li>Create a project and enable YouTube Data API v3</li>
              <li>Create OAuth 2.0 credentials</li>
              <li>Add callback URL: <code className="bg-gray-100 px-1 rounded">https://your-domain/api/auth/youtube/callback</code></li>
            </ol>
            <div className="bg-gray-50 rounded-lg p-3 font-mono text-sm mt-3">
              <div>YOUTUBE_CLIENT_ID=your_client_id</div>
              <div>YOUTUBE_CLIENT_SECRET=your_client_secret</div>
            </div>
          </div>

          {/* LinkedIn Setup */}
          <div className="pb-6">
            <h3 className="font-medium flex items-center gap-2 mb-3">
              <Linkedin className="w-5 h-5 text-blue-700" />
              LinkedIn
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
              <li>Go to <a href="https://www.linkedin.com/developers/apps" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">LinkedIn Developer Portal <ExternalLink className="w-3 h-3 inline" /></a></li>
              <li>Create a new app</li>
              <li>Request "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect" products</li>
              <li>Add callback URL: <code className="bg-gray-100 px-1 rounded">https://your-domain/api/auth/linkedin/callback</code></li>
            </ol>
            <div className="bg-gray-50 rounded-lg p-3 font-mono text-sm mt-3">
              <div>LINKEDIN_CLIENT_ID=your_client_id</div>
              <div>LINKEDIN_CLIENT_SECRET=your_client_secret</div>
            </div>
          </div>
        </div>
      </div>

      {/* Environment Variables Summary */}
      <div className="card mt-8">
        <h2 className="text-lg font-semibold mb-4">All Environment Variables</h2>
        <div className="bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-sm overflow-x-auto">
          <pre>{`# Facebook & Instagram
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret

# Twitter/X
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret

# YouTube
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# LinkedIn
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret`}</pre>
        </div>
      </div>
    </div>
  );
}
