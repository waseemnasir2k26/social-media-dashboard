import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Sparkles,
  ImagePlus,
  Send,
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Loader2,
} from 'lucide-react';
import { postsApi } from '../services/api';

const contentTypes = [
  { value: 'educational', label: 'Educational', description: 'How-to guides, tips, frameworks' },
  { value: 'motivation', label: 'Motivation', description: 'Founder wisdom, quotes, insights' },
  { value: 'promotional', label: 'Promotional', description: 'Product/service promotion' },
  { value: 'engagement', label: 'Engagement', description: 'Questions, polls, discussions' },
  { value: 'custom', label: 'Custom', description: 'Write your own content' },
];

const platforms = [
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin },
  { id: 'twitter', label: 'Twitter/X', icon: Twitter },
  { id: 'facebook', label: 'Facebook', icon: Facebook },
  { id: 'instagram', label: 'Instagram', icon: Instagram },
];

export default function CreatePost() {
  const navigate = useNavigate();
  const [contentType, setContentType] = useState('educational');
  const [topic, setTopic] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [content, setContent] = useState('');
  const [imagePrompt, setImagePrompt] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['linkedin']);
  const [autoPost, setAutoPost] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [saving, setSaving] = useState(false);

  const togglePlatform = (platformId: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platformId)
        ? prev.filter((p) => p !== platformId)
        : [...prev, platformId]
    );
  };

  const handleGenerate = async () => {
    if (contentType === 'custom' && !customPrompt.trim()) {
      toast.error('Please enter a custom prompt');
      return;
    }

    setGenerating(true);
    try {
      const result = await postsApi.generate({
        content_type: contentType,
        topic: topic || undefined,
        platforms: selectedPlatforms,
        custom_prompt: contentType === 'custom' ? customPrompt : undefined,
        auto_post: autoPost,
      });

      if (result.success) {
        setContent(result.generation_result.content);
        setImagePrompt(result.generation_result.image_prompt || '');
        toast.success('Content generated! Review and edit as needed.');
      }
    } catch (error) {
      toast.error('Failed to generate content');
      console.error(error);
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateImage = async () => {
    if (!imagePrompt.trim()) {
      toast.error('Please enter an image prompt');
      return;
    }

    setGeneratingImage(true);
    try {
      const result = await postsApi.generateImage(imagePrompt);
      if (result.success) {
        setImageUrl(result.image_url);
        toast.success('Image generated!');
      }
    } catch (error) {
      toast.error('Failed to generate image');
      console.error(error);
    } finally {
      setGeneratingImage(false);
    }
  };

  const handleSave = async (status: 'draft' | 'pending_approval') => {
    if (!content.trim()) {
      toast.error('Please generate or write some content first');
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
        image_prompt: imagePrompt || undefined,
        content_type: contentType,
        topic: topic || undefined,
        platforms: selectedPlatforms,
        auto_post: autoPost,
      });

      toast.success(status === 'draft' ? 'Draft saved!' : 'Post sent for approval!');
      navigate('/queue');
    } catch (error) {
      toast.error('Failed to save post');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create Post</h1>
        <p className="text-gray-500 mt-1">Generate AI-powered content for your social media</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Generation Options */}
        <div className="lg:col-span-1 space-y-6">
          {/* Content Type */}
          <div className="card">
            <h2 className="font-semibold mb-4">Content Type</h2>
            <div className="space-y-2">
              {contentTypes.map((type) => (
                <label
                  key={type.value}
                  className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer border-2 transition-colors ${
                    contentType === type.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="contentType"
                    value={type.value}
                    checked={contentType === type.value}
                    onChange={(e) => setContentType(e.target.value)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-medium">{type.label}</p>
                    <p className="text-sm text-gray-500">{type.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Topic Input */}
          <div className="card">
            <h2 className="font-semibold mb-4">Topic (Optional)</h2>
            <input
              type="text"
              className="input"
              placeholder="e.g., AI automation, founder lessons..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>

          {/* Custom Prompt (for custom type) */}
          {contentType === 'custom' && (
            <div className="card">
              <h2 className="font-semibold mb-4">Custom Prompt</h2>
              <textarea
                className="textarea h-32"
                placeholder="Describe what you want to post about..."
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
              />
            </div>
          )}

          {/* Platforms */}
          <div className="card">
            <h2 className="font-semibold mb-4">Platforms</h2>
            <div className="grid grid-cols-2 gap-2">
              {platforms.map((platform) => (
                <button
                  key={platform.id}
                  onClick={() => togglePlatform(platform.id)}
                  className={`flex items-center gap-2 p-3 rounded-lg border-2 transition-colors ${
                    selectedPlatforms.includes(platform.id)
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <platform.icon className="w-5 h-5" />
                  <span className="text-sm font-medium">{platform.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn btn-primary w-full flex items-center justify-center gap-2 py-3"
          >
            {generating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Generate Content
              </>
            )}
          </button>
        </div>

        {/* Right: Preview & Edit */}
        <div className="lg:col-span-2 space-y-6">
          {/* Content Preview */}
          <div className="card">
            <h2 className="font-semibold mb-4">Post Content</h2>
            <textarea
              className="textarea h-64 font-mono text-sm"
              placeholder="Your generated content will appear here. You can also write or edit directly."
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <div className="flex justify-between items-center mt-2 text-sm text-gray-500">
              <span>{content.split(/\s+/).filter(Boolean).length} words</span>
              <span>{content.length} characters</span>
            </div>
          </div>

          {/* Image Generation */}
          <div className="card">
            <h2 className="font-semibold mb-4">Image (Optional)</h2>
            <div className="space-y-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input flex-1"
                  placeholder="Image prompt (e.g., Premium LinkedIn carousel...)"
                  value={imagePrompt}
                  onChange={(e) => setImagePrompt(e.target.value)}
                />
                <button
                  onClick={handleGenerateImage}
                  disabled={generatingImage || !imagePrompt.trim()}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  {generatingImage ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <ImagePlus className="w-5 h-5" />
                  )}
                  Generate
                </button>
              </div>
              {imageUrl && (
                <div className="relative">
                  <img
                    src={imageUrl}
                    alt="Generated"
                    className="w-full max-w-md rounded-lg shadow-md"
                  />
                  <button
                    onClick={() => setImageUrl('')}
                    className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full hover:bg-red-600"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Auto Post Toggle */}
          <div className="card">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="font-semibold">Auto-post when scheduled</p>
                <p className="text-sm text-gray-500">
                  Skip approval queue and post automatically
                </p>
              </div>
              <input
                type="checkbox"
                checked={autoPost}
                onChange={(e) => setAutoPost(e.target.checked)}
                className="w-5 h-5 rounded text-blue-600"
              />
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={() => handleSave('draft')}
              disabled={saving}
              className="btn btn-secondary flex-1 py-3"
            >
              Save as Draft
            </button>
            <button
              onClick={() => handleSave('pending_approval')}
              disabled={saving}
              className="btn btn-primary flex-1 py-3 flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  Send for Approval
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
