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
  Link2,
  Unlink,
  Loader2,
  Save,
  Eye,
  EyeOff,
  Key,
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

interface Credentials {
  [key: string]: { client_id: string; configured: boolean };
}

const platformConfig = [
  {
    id: 'facebook',
    name: 'Facebook & Instagram',
    icon: Facebook,
    color: 'bg-blue-600',
    description: 'Connects Facebook Page + Instagram accounts',
    docsUrl: 'https://developers.facebook.com/',
    envPrefix: 'FACEBOOK',
  },
  {
    id: 'twitter',
    name: 'Twitter/X',
    icon: Twitter,
    color: 'bg-black',
    description: 'Tweet to your account',
    docsUrl: 'https://developer.twitter.com/en/portal/dashboard',
    envPrefix: 'TWITTER',
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: Youtube,
    color: 'bg-red-600',
    description: 'Upload videos to your channel',
    docsUrl: 'https://console.cloud.google.com/',
    envPrefix: 'YOUTUBE',
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    icon: Linkedin,
    color: 'bg-blue-700',
    description: 'Post to your LinkedIn profile',
    docsUrl: 'https://www.linkedin.com/developers/apps',
    envPrefix: 'LINKEDIN',
  },
];

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null);
  const [credentials, setCredentials] = useState<Credentials>({});
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  // Form state for each platform
  const [formData, setFormData] = useState<Record<string, { client_id: string; client_secret: string }>>({
    facebook: { client_id: '', client_secret: '' },
    twitter: { client_id: '', client_secret: '' },
    youtube: { client_id: '', client_secret: '' },
    linkedin: { client_id: '', client_secret: '' },
  });

  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

  useEffect(() => {
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
    loadCredentials();
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

  async function loadCredentials() {
    try {
      const result = await api.get('/credentials');
      setCredentials(result.data.credentials || {});

      // Pre-fill form with existing client IDs (secrets are hidden)
      const newFormData = { ...formData };
      Object.entries(result.data.credentials || {}).forEach(([platform, data]: [string, any]) => {
        if (newFormData[platform]) {
          newFormData[platform].client_id = data.client_id || '';
        }
      });
      setFormData(newFormData);
    } catch (error) {
      console.error('Failed to load credentials:', error);
    }
  }

  async function handleSaveCredentials(platformId: string) {
    const data = formData[platformId];
    if (!data.client_id || !data.client_secret) {
      toast.error('Please fill in both Client ID and Client Secret');
      return;
    }

    setSaving(platformId);
    try {
      await api.post('/credentials', {
        platform: platformId,
        client_id: data.client_id,
        client_secret: data.client_secret,
      });
      toast.success(`${platformId} credentials saved!`);
      loadCredentials();
      loadStatus();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save credentials');
    } finally {
      setSaving(null);
    }
  }

  async function handleConnect(platformId: string) {
    setConnecting(platformId);
    try {
      const response = await api.get(`/auth/${platformId}/connect`);
      const { auth_url } = response.data;

      if (auth_url) {
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

  const updateFormData = (platform: string, field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [platform]: { ...prev[platform], [field]: value }
    }));
  };

  const toggleShowSecret = (platform: string) => {
    setShowSecrets(prev => ({ ...prev, [platform]: !prev[platform] }));
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Add your API credentials and connect accounts</p>
      </div>

      {/* Credentials Setup */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <Key className="w-5 h-5" />
          API Credentials
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          Enter your OAuth credentials from each platform. They'll be saved securely.
        </p>

        <div className="space-y-6">
          {platformConfig.map((platform) => {
            const isConfigured = credentials[platform.id]?.configured;
            const form = formData[platform.id] || { client_id: '', client_secret: '' };

            return (
              <div key={platform.id} className="border rounded-xl p-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2 rounded-lg ${platform.color} text-white`}>
                    <platform.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{platform.name}</p>
                    <p className="text-sm text-gray-500">{platform.description}</p>
                  </div>
                  {isConfigured && (
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <CheckCircle className="w-4 h-4" />
                      Configured
                    </span>
                  )}
                  <a
                    href={platform.docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline text-sm flex items-center gap-1"
                  >
                    Get Keys <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Client ID / App ID
                    </label>
                    <input
                      type="text"
                      className="input"
                      placeholder={`${platform.envPrefix}_CLIENT_ID`}
                      value={form.client_id}
                      onChange={(e) => updateFormData(platform.id, 'client_id', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Client Secret / App Secret
                    </label>
                    <div className="relative">
                      <input
                        type={showSecrets[platform.id] ? 'text' : 'password'}
                        className="input pr-10"
                        placeholder={`${platform.envPrefix}_CLIENT_SECRET`}
                        value={form.client_secret}
                        onChange={(e) => updateFormData(platform.id, 'client_secret', e.target.value)}
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowSecret(platform.id)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showSecrets[platform.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => handleSaveCredentials(platform.id)}
                    disabled={saving === platform.id}
                    className="btn btn-primary text-sm flex items-center gap-2"
                  >
                    {saving === platform.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Save Credentials
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Connected Accounts */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold mb-6">Connected Accounts</h2>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : (
          <div className="space-y-4">
            {[
              { id: 'facebook', name: 'Facebook Page', icon: Facebook, color: 'bg-blue-600' },
              { id: 'instagram_1', name: 'Instagram 1', icon: Instagram, color: 'bg-gradient-to-r from-purple-500 to-pink-500' },
              { id: 'instagram_2', name: 'Instagram 2', icon: Instagram, color: 'bg-gradient-to-r from-pink-500 to-orange-500' },
              { id: 'twitter', name: 'Twitter/X', icon: Twitter, color: 'bg-black' },
              { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'bg-red-600' },
              { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'bg-blue-700' },
            ].map((platform) => {
              const status = platformStatus?.[platform.id as keyof PlatformStatus];
              const isConnected = status?.connected;
              const isConfigured = status?.oauth_configured;
              const displayName = (status as any)?.page_name || (status as any)?.account_name || platform.name;

              return (
                <div
                  key={platform.id}
                  className="flex items-center justify-between p-4 border rounded-xl hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-xl ${platform.color} text-white`}>
                      <platform.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{platform.name}</p>
                      <p className="text-sm text-gray-500">
                        {isConnected ? displayName : 'Not connected'}
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
                        Add credentials above
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Callback URLs */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Callback URLs</h2>
        <p className="text-sm text-gray-500 mb-4">
          Add these URLs to your OAuth app settings on each platform:
        </p>
        <div className="bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-sm overflow-x-auto">
          <pre>{`Facebook:  ${window.location.origin}/api/auth/facebook/callback
Twitter:   ${window.location.origin}/api/auth/twitter/callback
YouTube:   ${window.location.origin}/api/auth/youtube/callback
LinkedIn:  ${window.location.origin}/api/auth/linkedin/callback`}</pre>
        </div>
      </div>
    </div>
  );
}
