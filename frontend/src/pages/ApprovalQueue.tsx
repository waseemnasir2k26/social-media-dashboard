import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  CheckCircle,
  Send,
  Clock,
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Loader2,
  Edit,
  Trash2,
} from 'lucide-react';
import { postsApi, Post } from '../services/api';
import { format } from 'date-fns';

const platformIcons: Record<string, typeof Twitter> = {
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook,
  instagram: Instagram,
};

export default function ApprovalQueue() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [editContent, setEditContent] = useState('');
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');

  useEffect(() => {
    loadPosts();
  }, []);

  async function loadPosts() {
    try {
      const result = await postsApi.list({ status: 'pending_approval' });
      setPosts(result.posts);
    } catch (error) {
      toast.error('Failed to load posts');
    } finally {
      setLoading(false);
    }
  }

  const handlePublishNow = async (post: Post) => {
    setActionLoading(post.id);
    try {
      const result = await postsApi.publish(post.id);
      if (result.success) {
        toast.success('Post published successfully!');
      } else {
        const errorMsg = result.post?.error_message || 'Some platforms failed';
        toast.error(errorMsg);
      }
      loadPosts();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to publish post';
      if (errorMessage.includes('not connected') || errorMessage.includes('not configured')) {
        toast.error('No platforms connected. Configure platforms in Settings first.');
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setActionLoading(null);
    }
  };

  const handleSchedule = async (post: Post) => {
    if (!scheduleDate || !scheduleTime) {
      toast.error('Please select date and time');
      return;
    }

    const scheduledTime = new Date(`${scheduleDate}T${scheduleTime}`).toISOString();

    setActionLoading(post.id);
    try {
      await postsApi.update(post.id, {
        status: 'scheduled',
        scheduled_time: scheduledTime,
      });
      toast.success('Post scheduled!');
      loadPosts();
      setSelectedPost(null);
    } catch (error) {
      toast.error('Failed to schedule post');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (post: Post) => {
    if (!confirm('Are you sure you want to delete this post?')) return;

    setActionLoading(post.id);
    try {
      await postsApi.delete(post.id);
      toast.success('Post deleted');
      loadPosts();
    } catch (error) {
      toast.error('Failed to delete post');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedPost) return;

    setActionLoading(selectedPost.id);
    try {
      await postsApi.update(selectedPost.id, { content: editContent });
      toast.success('Post updated!');
      loadPosts();
      setSelectedPost(null);
    } catch (error) {
      toast.error('Failed to update post');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Approval Queue</h1>
        <p className="text-gray-500 mt-1">
          Review and approve posts before publishing ({posts.length} pending)
        </p>
      </div>

      {posts.length === 0 ? (
        <div className="card text-center py-12">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900">All caught up!</h3>
          <p className="text-gray-500 mt-1">No posts pending approval</p>
        </div>
      ) : (
        <div className="space-y-6">
          {posts.map((post) => (
            <div key={post.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  {/* Content Preview */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <p className="text-gray-900 whitespace-pre-wrap text-sm">
                      {post.content}
                    </p>
                  </div>

                  {/* Meta Info */}
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="badge badge-pending">
                      {post.content_type}
                    </span>
                    <span>{post.word_count} words</span>
                    <span>
                      Created {format(new Date(post.created_at), 'MMM d, h:mm a')}
                    </span>
                    <div className="flex gap-1">
                      {post.platforms.map((platform) => {
                        const Icon = platformIcons[platform];
                        return Icon ? (
                          <Icon key={platform} className="w-4 h-4" />
                        ) : null;
                      })}
                    </div>
                  </div>

                  {/* Image Preview */}
                  {post.image_url && (
                    <div className="mt-4">
                      <img
                        src={post.image_url}
                        alt="Post image"
                        className="max-w-xs rounded-lg shadow-sm"
                      />
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => handlePublishNow(post)}
                    disabled={actionLoading === post.id}
                    className="btn btn-success flex items-center gap-2"
                  >
                    {actionLoading === post.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    Publish Now
                  </button>

                  <button
                    onClick={() => {
                      setSelectedPost(post);
                      setEditContent(post.content);
                      setScheduleDate('');
                      setScheduleTime('');
                    }}
                    className="btn btn-secondary flex items-center gap-2"
                  >
                    <Clock className="w-4 h-4" />
                    Schedule
                  </button>

                  <button
                    onClick={() => {
                      setSelectedPost(post);
                      setEditContent(post.content);
                    }}
                    className="btn btn-secondary flex items-center gap-2"
                  >
                    <Edit className="w-4 h-4" />
                    Edit
                  </button>

                  <button
                    onClick={() => handleDelete(post)}
                    disabled={actionLoading === post.id}
                    className="btn btn-danger flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit/Schedule Modal */}
      {selectedPost && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-auto">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold">Edit & Schedule Post</h2>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block font-medium mb-2">Content</label>
                <textarea
                  className="textarea h-48"
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-medium mb-2">Schedule Date</label>
                  <input
                    type="date"
                    className="input"
                    value={scheduleDate}
                    onChange={(e) => setScheduleDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
                <div>
                  <label className="block font-medium mb-2">Schedule Time</label>
                  <input
                    type="time"
                    className="input"
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="p-6 border-t flex gap-4 justify-end">
              <button
                onClick={() => setSelectedPost(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={actionLoading === selectedPost.id}
                className="btn btn-secondary"
              >
                Save Changes
              </button>
              <button
                onClick={() => handleSchedule(selectedPost)}
                disabled={actionLoading === selectedPost.id || !scheduleDate || !scheduleTime}
                className="btn btn-primary flex items-center gap-2"
              >
                {actionLoading === selectedPost.id ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Clock className="w-4 h-4" />
                )}
                Schedule Post
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
