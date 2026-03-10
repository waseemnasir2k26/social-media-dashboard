import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import {
  Link2,
  CheckCircle,
  XCircle,
  Save,
  Loader2,
  Zap,
  ExternalLink,
} from 'lucide-react';
import { getWebhookUrl, setWebhookUrl } from '../services/api';

export default function Settings() {
  const [url, setUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'fail' | null>(
    null
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setUrl(getWebhookUrl());
  }, []);

  const handleSave = () => {
    if (!url.trim()) {
      toast.error('Please enter your n8n webhook URL');
      return;
    }
    if (!url.trim().startsWith('http')) {
      toast.error('URL must start with http:// or https://');
      return;
    }
    setWebhookUrl(url.trim());
    setSaved(true);
    setTestResult(null);
    toast.success('Webhook URL saved!');
    console.log('[SkynetJoe] Webhook URL saved:', url.trim());
    setTimeout(() => setSaved(false), 2000);
  };

  const handleTest = async () => {
    if (!url.trim()) {
      toast.error('Please enter and save your webhook URL first');
      return;
    }
    setTesting(true);
    setTestResult(null);
    console.log('[SkynetJoe] Testing webhook connection:', url.trim());

    try {
      // Send a lightweight test POST with a test flag
      // n8n will process it but we just check if it responds
      const testData = new FormData();
      testData.append('test', 'true');
      testData.append('caption', 'Connection test from SkynetJoe dashboard');

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);

      const response = await fetch(url.trim(), {
        method: 'POST',
        body: testData,
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (response.ok) {
        setTestResult('success');
        toast.success('n8n webhook is working! Connection verified.');
        console.log(
          '[SkynetJoe] Webhook test passed. Status:',
          response.status
        );
      } else {
        setTestResult('fail');
        toast.error(
          `Webhook responded with status ${response.status}. Make sure the workflow is active.`
        );
        console.error(
          '[SkynetJoe] Webhook test failed. Status:',
          response.status
        );
      }
    } catch (error: any) {
      setTestResult('fail');
      if (error.name === 'AbortError') {
        toast.error(
          'Connection timed out (10s). Is n8n running?'
        );
        console.error('[SkynetJoe] Webhook test timed out');
      } else {
        toast.error(
          'Cannot reach webhook. Check the URL and make sure n8n is running.'
        );
        console.error('[SkynetJoe] Webhook test error:', error.message);
      }
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">
          Configure your n8n webhook connection
        </p>
      </div>

      {/* Webhook URL */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-500" />
          n8n Webhook URL
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Paste the production webhook URL from your n8n workflow.
        </p>

        <div className="space-y-4">
          <div>
            <input
              type="url"
              className={`input font-mono text-sm ${
                testResult === 'success'
                  ? 'border-green-500 ring-2 ring-green-200'
                  : testResult === 'fail'
                  ? 'border-red-500 ring-2 ring-red-200'
                  : ''
              }`}
              placeholder="https://your-n8n.com/webhook/linkedin-post"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setTestResult(null);
              }}
            />
            <p className="text-xs text-gray-400 mt-1">
              In n8n: click Webhook node &rarr; copy &quot;Production
              URL&quot;
            </p>
          </div>

          {/* Status indicator */}
          {testResult && (
            <div
              className={`flex items-center gap-2 text-sm font-medium ${
                testResult === 'success'
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}
            >
              {testResult === 'success' ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              {testResult === 'success'
                ? 'Connection verified — n8n is responding'
                : 'Connection failed — check URL and n8n status'}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              className="btn btn-primary flex items-center gap-2"
            >
              {saved ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saved ? 'Saved!' : 'Save'}
            </button>
            <button
              onClick={handleTest}
              disabled={testing || !url.trim()}
              className="btn btn-secondary flex items-center gap-2 disabled:opacity-50"
            >
              {testing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Link2 className="w-4 h-4" />
              )}
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-4">How It Works</h2>
        <div className="space-y-4">
          {[
            {
              step: '1',
              title: 'Upload & Write',
              desc: 'Select an image and write your caption',
              color: 'bg-blue-100 text-blue-600',
            },
            {
              step: '2',
              title: 'Sent to n8n',
              desc: 'Image + caption sent via webhook to your n8n workflow',
              color: 'bg-purple-100 text-purple-600',
            },
            {
              step: '3',
              title: 'Archived to Google Drive',
              desc: 'n8n saves the image to your Google Drive for backup',
              color: 'bg-green-100 text-green-600',
            },
            {
              step: '4',
              title: 'Published to LinkedIn',
              desc: 'n8n posts to LinkedIn immediately or at your scheduled time',
              color: 'bg-orange-100 text-orange-600',
            },
          ].map((item) => (
            <div key={item.step} className="flex gap-4">
              <div
                className={`w-8 h-8 rounded-full ${item.color} flex items-center justify-center font-bold text-sm flex-shrink-0`}
              >
                {item.step}
              </div>
              <div>
                <p className="font-medium">{item.title}</p>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* n8n Setup Checklist */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">
          n8n Setup Checklist
        </h2>
        <div className="space-y-3">
          {[
            {
              text: 'Import n8n-linkedin-workflow.json into n8n',
              hint: 'Menu > Import from File',
            },
            {
              text: 'Connect LinkedIn OAuth2 in BOTH LinkedIn nodes',
              hint: 'Click each node > Credential > Create New',
            },
            {
              text: 'Connect Google Drive in the Archive node',
              hint: 'Click node > Credential > Create New > Pick folder',
            },
            {
              text: 'Activate the workflow',
              hint: 'Toggle switch in the top-right corner',
            },
            {
              text: 'Copy the Production URL and paste it above',
              hint: 'Click Webhook node > Production URL > Copy',
            },
          ].map((step, i) => (
            <div key={i} className="flex items-start gap-3 group">
              <div className="w-6 h-6 rounded-full border-2 border-gray-300 flex items-center justify-center text-xs text-gray-400 flex-shrink-0 mt-0.5 group-hover:border-blue-500 group-hover:text-blue-500 transition-colors">
                {i + 1}
              </div>
              <div>
                <p className="text-sm text-gray-700 font-medium">
                  {step.text}
                </p>
                <p className="text-xs text-gray-400">{step.hint}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-gray-200">
          <a
            href="https://docs.n8n.io/integrations/builtin/credentials/linkedin/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
          >
            n8n LinkedIn credential docs
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
