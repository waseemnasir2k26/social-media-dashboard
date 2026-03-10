// ============================================
// SkynetJoe LinkedIn Poster - API Service
// Talks to n8n webhook, stores history locally
// ============================================

// --- Webhook Config ---

export const getWebhookUrl = (): string => {
  return localStorage.getItem('n8n_webhook_url') || '';
};

export const setWebhookUrl = (url: string): void => {
  localStorage.setItem('n8n_webhook_url', url);
};

// --- Types ---

export interface PostRecord {
  id: string;
  caption: string;
  imagePreview: string;
  imageName: string;
  imageSize: number;
  status: 'scheduled' | 'posted' | 'failed' | 'pending';
  scheduledDate?: string;
  createdAt: string;
  platform: string;
  webhookResponse?: string;
}

export interface LogEntry {
  time: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'sending';
}

// --- Submit to n8n ---

export const submitPost = async (
  data: {
    image: File;
    caption: string;
    scheduledDate?: string;
  },
  onLog?: (entry: LogEntry) => void
): Promise<{ status: string; [key: string]: unknown }> => {
  const log = (message: string, type: LogEntry['type'] = 'info') => {
    const entry: LogEntry = { time: new Date().toLocaleTimeString(), message, type };
    console.log(`[SkynetJoe ${type.toUpperCase()}] ${message}`);
    onLog?.(entry);
  };

  const webhookUrl = getWebhookUrl();
  if (!webhookUrl) {
    log('Webhook URL not configured', 'error');
    throw new Error('Webhook URL not configured. Go to Settings to add your n8n webhook URL.');
  }

  log(`Webhook URL: ${webhookUrl}`, 'info');
  log(`Image: ${data.image.name} (${(data.image.size / 1024 / 1024).toFixed(2)} MB)`, 'info');
  log(`Caption: ${data.caption.length} characters`, 'info');
  if (data.scheduledDate) {
    log(`Scheduled for: ${new Date(data.scheduledDate).toLocaleString()}`, 'info');
  }

  // Build FormData
  const formData = new FormData();
  formData.append('image', data.image, data.image.name);
  formData.append('caption', data.caption);
  if (data.scheduledDate) {
    formData.append('scheduledDate', data.scheduledDate);
  }

  log('Sending to n8n webhook...', 'sending');

  try {
    const startTime = Date.now();
    const response = await fetch(webhookUrl, {
      method: 'POST',
      body: formData,
    });
    const elapsed = Date.now() - startTime;

    log(`Response received in ${elapsed}ms (status ${response.status})`, 'info');

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'No response body');
      log(`n8n error: ${response.status} - ${errorText}`, 'error');
      throw new Error(
        response.status === 404
          ? 'Webhook not found. Make sure the n8n workflow is active.'
          : response.status === 500
          ? 'n8n workflow error. Check n8n execution logs for details.'
          : `Request failed (${response.status}): ${errorText}`
      );
    }

    // Parse response
    const contentType = response.headers.get('content-type');
    let result: { status: string; [key: string]: unknown };

    if (contentType?.includes('application/json')) {
      result = await response.json();
      log(`n8n response: ${JSON.stringify(result)}`, 'success');
    } else {
      const text = await response.text();
      log(`n8n response (text): ${text}`, 'success');
      result = { status: 'ok', body: text };
    }

    if (data.scheduledDate) {
      log('Post scheduled — n8n will publish at the scheduled time', 'success');
    } else {
      log('Post sent to LinkedIn via n8n', 'success');
    }

    return result;
  } catch (error: any) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      log('Network error — cannot reach n8n. Is it running?', 'error');
      throw new Error('Cannot reach n8n. Make sure your n8n instance is running and the URL is correct.');
    }
    throw error;
  }
};

// --- Local Post History (localStorage) ---

const STORAGE_KEY = 'skynetjoe_post_history';

export const savePost = (post: PostRecord): void => {
  const posts = getPosts();
  posts.unshift(post);
  // Keep only last 100 posts to avoid localStorage bloat
  const trimmed = posts.slice(0, 100);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  console.log(`[SkynetJoe] Post saved to history: ${post.id} (${post.status})`);
};

export const getPosts = (): PostRecord[] => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    console.error('[SkynetJoe] Failed to parse post history from localStorage');
    return [];
  }
};

export const deletePost = (id: string): void => {
  const posts = getPosts().filter((p) => p.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(posts));
  console.log(`[SkynetJoe] Post deleted: ${id}`);
};

export const updatePostStatus = (id: string, status: PostRecord['status']): void => {
  const posts = getPosts();
  const post = posts.find((p) => p.id === id);
  if (post) {
    post.status = status;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(posts));
    console.log(`[SkynetJoe] Post ${id} status updated to: ${status}`);
  }
};
