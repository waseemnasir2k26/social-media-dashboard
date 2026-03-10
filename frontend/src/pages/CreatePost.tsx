import { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Send,
  Linkedin,
  Loader2,
  Image as ImageIcon,
  Calendar,
  Clock,
  Upload,
  X,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowRight,
  Terminal,
} from 'lucide-react';
import {
  submitPost,
  savePost,
  getWebhookUrl,
  PostRecord,
  LogEntry,
} from '../services/api';

export default function CreatePost() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');
  const [caption, setCaption] = useState('');
  const [isScheduled, setIsScheduled] = useState(false);
  const [scheduledDate, setScheduledDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [step, setStep] = useState<
    'idle' | 'preparing' | 'sending' | 'done' | 'error'
  >('idle');

  const webhookConfigured = !!getWebhookUrl();

  const addLog = (entry: LogEntry) => {
    setLogs((prev) => [...prev, entry]);
    setTimeout(
      () => logEndRef.current?.scrollIntoView({ behavior: 'smooth' }),
      50
    );
  };

  const handleImageSelect = (file: File) => {
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file (PNG, JPG, WEBP)');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image must be under 10MB');
      return;
    }
    setImage(file);
    const reader = new FileReader();
    reader.onloadend = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
    console.log(
      `[SkynetJoe] Image selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`
    );
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleImageSelect(e.dataTransfer.files[0]);
    }
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async () => {
    if (!webhookConfigured) {
      toast.error('Set up your n8n webhook URL in Settings first');
      return;
    }
    if (!image) {
      toast.error('Please upload an image');
      return;
    }
    if (!caption.trim()) {
      toast.error('Please write a caption');
      return;
    }
    if (isScheduled && !scheduledDate) {
      toast.error('Please select a date and time');
      return;
    }
    if (isScheduled && new Date(scheduledDate) <= new Date()) {
      toast.error('Scheduled time must be in the future');
      return;
    }

    // Reset logs and show log panel
    setLogs([]);
    setShowLogs(true);
    setSubmitting(true);
    setStep('preparing');

    try {
      setStep('sending');

      const result = await submitPost(
        {
          image,
          caption,
          scheduledDate: isScheduled
            ? new Date(scheduledDate).toISOString()
            : undefined,
        },
        addLog
      );

      setStep('done');

      // Save to local history
      const post: PostRecord = {
        id: crypto.randomUUID(),
        caption,
        imagePreview,
        imageName: image.name,
        imageSize: image.size,
        status: isScheduled ? 'scheduled' : 'posted',
        scheduledDate: isScheduled ? scheduledDate : undefined,
        createdAt: new Date().toISOString(),
        platform: 'linkedin',
        webhookResponse: JSON.stringify(result),
      };
      savePost(post);

      toast.success(
        isScheduled
          ? 'Post scheduled successfully!'
          : 'Posted to LinkedIn!',
        { duration: 4000 }
      );

      // Navigate after a short delay so user can see the success state
      setTimeout(() => navigate('/history'), 1500);
    } catch (error: any) {
      setStep('error');
      addLog({
        time: new Date().toLocaleTimeString(),
        message: error.message,
        type: 'error',
      });
      toast.error(error.message || 'Failed to submit post');
    } finally {
      setSubmitting(false);
    }
  };

  const getStepIndicator = () => {
    if (step === 'idle') return null;

    const stepKeys = ['preparing', 'sending', 'done'] as const;
    const stepLabels: Record<string, string> = {
      preparing: 'Preparing',
      sending: 'Sending to n8n',
      done: isScheduled ? 'Scheduled' : 'Posted',
    };
    const currentIndex = stepKeys.indexOf(step as typeof stepKeys[number]);
    const isDone = step === 'done';
    const isError = step === 'error';

    return (
      <div className="card mb-6 border-blue-200 bg-blue-50">
        <div className="flex items-center gap-6">
          {stepKeys.map((key, i) => {
            const isPast = isDone || currentIndex > i;
            const isCurrent = key === step && !isDone;

            return (
              <div key={key} className="flex items-center gap-2">
                {isPast ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                )}
                <span
                  className={`text-sm font-medium ${
                    isPast
                      ? 'text-green-700'
                      : isCurrent
                      ? 'text-blue-700'
                      : 'text-gray-400'
                  }`}
                >
                  {stepLabels[key]}
                </span>
                {i < stepKeys.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-gray-300 ml-2" />
                )}
              </div>
            );
          })}
        </div>
        {isError && (
          <div className="flex items-center gap-2 mt-3 text-red-600">
            <XCircle className="w-5 h-5" />
            <span className="text-sm font-medium">
              Failed — check the logs below
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create Post</h1>
        <p className="text-gray-500 mt-1">
          Upload an image and post to LinkedIn
        </p>
      </div>

      {/* Webhook not configured warning */}
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
                and paste your n8n webhook URL before creating a post.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Step Progress Indicator */}
      {getStepIndicator()}

      <div className="space-y-6">
        {/* Platform Badge */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-4 py-2 bg-blue-700 text-white rounded-lg">
            <Linkedin className="w-5 h-5" />
            <span className="font-medium">LinkedIn</span>
          </div>
          <span className="text-sm text-gray-500">
            Posting via n8n automation
          </span>
        </div>

        {/* Image Upload */}
        <div className="card">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <ImageIcon className="w-5 h-5" />
            Image
          </h2>

          {imagePreview ? (
            <div className="relative">
              <img
                src={imagePreview}
                alt="Preview"
                className="max-h-80 rounded-lg mx-auto"
              />
              <button
                onClick={removeImage}
                disabled={submitting}
                className="absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-full hover:bg-red-600 disabled:opacity-50"
              >
                <X className="w-4 h-4" />
              </button>
              <p className="text-sm text-gray-500 mt-3 text-center">
                {image?.name} (
                {((image?.size || 0) / 1024 / 1024).toFixed(1)} MB)
              </p>
            </div>
          ) : (
            <div
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                dragActive
                  ? 'border-blue-500 bg-blue-50 scale-[1.02]'
                  : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 font-medium">
                Drop your image here or click to browse
              </p>
              <p className="text-sm text-gray-400 mt-2">
                PNG, JPG, WEBP up to 10MB
              </p>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/webp"
            className="hidden"
            onChange={(e) =>
              e.target.files?.[0] && handleImageSelect(e.target.files[0])
            }
          />
        </div>

        {/* Caption */}
        <div className="card">
          <h2 className="font-semibold mb-4">Caption</h2>
          <textarea
            className="textarea h-40 text-base"
            placeholder="Write your LinkedIn post caption..."
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            maxLength={3000}
            disabled={submitting}
          />
          <div className="flex justify-between items-center mt-2 text-sm text-gray-500">
            <span>
              {caption.split(/\s+/).filter(Boolean).length} words
            </span>
            <span
              className={caption.length > 2800 ? 'text-orange-500 font-medium' : ''}
            >
              {caption.length}/3,000
            </span>
          </div>
        </div>

        {/* Schedule Toggle */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Schedule
            </h2>
            <button
              onClick={() => setIsScheduled(!isScheduled)}
              disabled={submitting}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isScheduled ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isScheduled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {isScheduled ? (
            <div>
              <input
                type="datetime-local"
                className="input max-w-xs"
                value={scheduledDate}
                min={new Date().toISOString().slice(0, 16)}
                onChange={(e) => setScheduledDate(e.target.value)}
                disabled={submitting}
              />
              <p className="text-sm text-gray-500 mt-2 flex items-center gap-1">
                <Clock className="w-4 h-4" />
                n8n will hold and publish at the selected time
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Post will be published immediately via n8n
            </p>
          )}
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={
            submitting || !image || !caption.trim() || !webhookConfigured
          }
          className="btn btn-primary w-full py-4 text-lg flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <Loader2 className="w-6 h-6 animate-spin" />
              {step === 'preparing'
                ? 'Preparing...'
                : step === 'sending'
                ? 'Sending to n8n...'
                : 'Finishing...'}
            </>
          ) : (
            <>
              <Send className="w-6 h-6" />
              {isScheduled ? 'Schedule Post' : 'Post Now'}
            </>
          )}
        </button>

        {/* Activity Log */}
        {(showLogs || logs.length > 0) && (
          <div className="card bg-gray-900 text-gray-100 border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold flex items-center gap-2 text-sm">
                <Terminal className="w-4 h-4" />
                Activity Log
              </h3>
              <button
                onClick={() => {
                  setShowLogs(false);
                  setLogs([]);
                }}
                className="text-gray-500 hover:text-gray-300 text-xs"
              >
                Clear
              </button>
            </div>
            <div className="space-y-1 font-mono text-xs max-h-60 overflow-y-auto">
              {logs.map((log, i) => (
                <div
                  key={i}
                  className={`flex gap-2 ${
                    log.type === 'error'
                      ? 'text-red-400'
                      : log.type === 'success'
                      ? 'text-green-400'
                      : log.type === 'sending'
                      ? 'text-yellow-400'
                      : 'text-gray-400'
                  }`}
                >
                  <span className="text-gray-600 flex-shrink-0">
                    {log.time}
                  </span>
                  <span>
                    {log.type === 'sending' && '>> '}
                    {log.type === 'error' && 'ERR '}
                    {log.type === 'success' && 'OK  '}
                    {log.message}
                  </span>
                </div>
              ))}
              {submitting && (
                <div className="flex gap-2 text-yellow-400 animate-pulse">
                  <span className="text-gray-600">
                    {new Date().toLocaleTimeString()}
                  </span>
                  <span>Waiting for response...</span>
                </div>
              )}
              <div ref={logEndRef} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
