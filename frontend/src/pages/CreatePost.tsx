import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Send,
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Loader2,
  Image as ImageIcon,
  Video,
  Calendar,
  Youtube,
} from 'lucide-react';
import { postsApi, platformsApi } from '../services/api';

const platforms = [
  { id: 'facebook', label: 'Facebook Page', icon: Facebook, color: 'bg-blue-600' },
  { id: 'instagram_1', label: 'Instagram 1', icon: Instagram, color: 'bg-gradient-to-r from-purple-500 to-pink-500' },
  { id: 'instagram_2', label: 'Instagram 2', icon: Instagram, color: 'bg-gradient-to-r from-pink-500 to-orange-500' },
  { id: 'twitter', label: 'Twitter/X', icon: Twitter, color: 'bg-black' },
  { id: 'youtube', label: 'YouTube', icon: Youtube, color: 'bg-red-600' },
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin, color: 'bg-blue-700' },
];

export default function CreatePost() {
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [scheduledTime, setScheduledTime] = useState('');
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [connectedPlatforms, setConnectedPlatforms] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadPlatformStatus();
  }, []);

  async function loadPlatformStatus() {
    try {
      const result = await platformsApi.getStatus();
      const connected: Record<string, boolean> = {};
      Object.entries(result.platforms).forEach(([key, value]: [string, any]) => {
        connected[key] = value.connected;
      });
      setConnectedPlatforms(connected);
    } catch (error) {
      console.error('Failed to load platform status:', error);
    }
  }

  const togglePlatform = (platformId: string) => {
    if (!connectedPlatforms[platformId]) {
      toast.error(`${platformId} is not connected. Go to Settings to connect it.`);
      return;
    }
    setSelectedPlatforms((prev) =>
      prev.includes(platformId)
        ? prev.filter((p) => p !== platformId)
        : [...prev, platformId]
    );
  };

  const handleSaveDraft = async () => {
    if (!content.trim()) {
      toast.error('Please write some content first');
      return;
    }

    if (selectedPlatforms.length === 0) {
      toast.error('Please select at least one platform');
      return;
    }

    setSaving(true);
    try {
      await postsApi.create({
        content,
        image_url: imageUrl || undefined,
        video_url: videoUrl || undefined,
        platforms: selectedPlatforms,
        scheduled_time: scheduledTime || undefined,
      });

      toast.success('Post saved!');
      navigate('/history');
    } catch (error) {
      toast.error('Failed to save post');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  const handlePublishNow = async () => {
    if (!content.trim()) {
      toast.error('Please write some content first');
      return;
    }

    if (selectedPlatforms.length === 0) {
      toast.error('Please select at least one platform');
      return;
    }

    // Check if Instagram is selected but no media
    const instagramSelected = selectedPlatforms.some(p => p.startsWith('instagram'));
    if (instagramSelected && !imageUrl && !videoUrl) {
      toast.error('Instagram requires an image or video');
      return;
    }

    setPublishing(true);
    try {
      // First create the post
      const createResult = await postsApi.create({
        content,
        image_url: imageUrl || undefined,
        video_url: videoUrl || undefined,
        platforms: selectedPlatforms,
      });

      // Then publish it
      const publishResult = await postsApi.publish(createResult.post.id);

      if (publishResult.success) {
        toast.success('Posted successfully to all platforms!');
      } else {
        const successPlatforms = Object.entries(publishResult.platform_results)
          .filter(([_, r]: [string, any]) => r.success)
          .map(([p]) => p);
        const failedPlatforms = Object.entries(publishResult.platform_results)
          .filter(([_, r]: [string, any]) => !r.success)
          .map(([p, r]: [string, any]) => `${p}: ${r.error}`);

        if (successPlatforms.length > 0) {
          toast.success(`Posted to: ${successPlatforms.join(', ')}`);
        }
        if (failedPlatforms.length > 0) {
          toast.error(`Failed: ${failedPlatforms.join('; ')}`);
        }
      }

      navigate('/history');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to publish');
      console.error(error);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create Post</h1>
        <p className="text-gray-500 mt-1">Compose and publish to multiple platforms</p>
      </div>

      <div className="space-y-6">
        {/* Content */}
        <div className="card">
          <h2 className="font-semibold mb-4">Post Content</h2>
          <textarea
            className="textarea h-40 text-base"
            placeholder="What do you want to share today?"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="flex justify-between items-center mt-2 text-sm text-gray-500">
            <span>{content.split(/\s+/).filter(Boolean).length} words</span>
            <span className={content.length > 280 ? 'text-orange-500' : ''}>
              {content.length} characters {content.length > 280 && '(Twitter will truncate)'}
            </span>
          </div>
        </div>

        {/* Media */}
        <div className="card">
          <h2 className="font-semibold mb-4">Media (Optional)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <ImageIcon className="w-4 h-4" />
                Image URL
              </label>
              <input
                type="url"
                className="input"
                placeholder="https://example.com/image.jpg"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">Must be publicly accessible</p>
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <Video className="w-4 h-4" />
                Video URL
              </label>
              <input
                type="url"
                className="input"
                placeholder="https://example.com/video.mp4"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">For Reels/Shorts (MP4 format)</p>
            </div>
          </div>
          {(imageUrl || videoUrl) && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                {imageUrl && <span className="block">Image: {imageUrl.substring(0, 50)}...</span>}
                {videoUrl && <span className="block">Video: {videoUrl.substring(0, 50)}...</span>}
              </p>
            </div>
          )}
        </div>

        {/* Platforms */}
        <div className="card">
          <h2 className="font-semibold mb-4">Select Platforms</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {platforms.map((platform) => {
              const isConnected = connectedPlatforms[platform.id];
              const isSelected = selectedPlatforms.includes(platform.id);

              return (
                <button
                  key={platform.id}
                  onClick={() => togglePlatform(platform.id)}
                  disabled={!isConnected}
                  className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    !isConnected
                      ? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
                      : isSelected
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className={`p-2 rounded-lg ${platform.color} text-white`}>
                    <platform.icon className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <p className="font-medium text-sm">{platform.label}</p>
                    <p className="text-xs text-gray-500">
                      {isConnected ? (isSelected ? 'Selected' : 'Click to select') : 'Not connected'}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Schedule (Optional) */}
        <div className="card">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Schedule (Optional)
          </h2>
          <input
            type="datetime-local"
            className="input max-w-xs"
            value={scheduledTime}
            onChange={(e) => setScheduledTime(e.target.value)}
          />
          <p className="text-sm text-gray-500 mt-2">
            Leave empty to publish immediately or save as draft
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={handleSaveDraft}
            disabled={saving || publishing}
            className="btn btn-secondary flex-1 py-3"
          >
            {saving ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              'Save Draft'
            )}
          </button>
          <button
            onClick={handlePublishNow}
            disabled={saving || publishing}
            className="btn btn-primary flex-1 py-3 flex items-center justify-center gap-2"
          >
            {publishing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Publishing...
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Publish Now
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
