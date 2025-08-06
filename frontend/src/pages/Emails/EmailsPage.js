import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import {
  Mail,
  Search,
  Filter,
  RefreshCw,
  Star,
  Archive,
  Trash2,
  Eye,
  EyeOff,
  Reply,
  Forward,
  MoreHorizontal,
  Zap,
  Clock,
  User,
  Calendar
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

// API functions
const fetchEmails = async ({ queryKey }) => {
  const [_key, params] = queryKey;
  const response = await axios.get('/api/emails', { params });
  return response.data;
};

const updateEmailStatus = async ({ emailId, action }) => {
  const response = await axios.patch(`/api/emails/${emailId}`, { action });
  return response.data;
};

const generateDraft = async (emailId) => {
  const response = await axios.post(`/api/ai/generate-draft/${emailId}`);
  return response.data;
};

const syncEmails = async () => {
  const response = await axios.post('/api/emails/sync');
  return response.data;
};

// Email Filter Component
const EmailFilter = ({ filters, setFilters }) => {
  const [showFilters, setShowFilters] = useState(false);

  const priorityOptions = [
    { value: 'all', label: 'All Priority' },
    { value: 'high', label: 'High Priority' },
    { value: 'medium', label: 'Medium Priority' },
    { value: 'low', label: 'Low Priority' },
  ];

  const statusOptions = [
    { value: 'all', label: 'All Status' },
    { value: 'unread', label: 'Unread' },
    { value: 'read', label: 'Read' },
    { value: 'starred', label: 'Starred' },
    { value: 'archived', label: 'Archived' },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setShowFilters(!showFilters)}
        className="btn btn-outline btn-sm"
      >
        <Filter className="w-4 h-4 mr-2" />
        Filters
      </button>

      {showFilters && (
        <div className="absolute top-full left-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-4">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Priority Level
              </label>
              <select
                value={filters.priority}
                onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
                className="w-full input"
              >
                {priorityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full input"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date Range
              </label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                  className="input"
                />
                <input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                  className="input"
                />
              </div>
            </div>

            <div className="flex space-x-2">
              <button
                onClick={() => {
                  setFilters({
                    priority: 'all',
                    status: 'all',
                    dateFrom: '',
                    dateTo: '',
                    search: ''
                  });
                  setShowFilters(false);
                }}
                className="btn btn-outline btn-sm flex-1"
              >
                Clear
              </button>
              <button
                onClick={() => setShowFilters(false)}
                className="btn btn-primary btn-sm flex-1"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Email Item Component
const EmailItem = ({ email, onSelect, isSelected }) => {
  const queryClient = useQueryClient();

  const updateStatusMutation = useMutation(updateEmailStatus, {
    onSuccess: () => {
      queryClient.invalidateQueries('emails');
    },
    onError: (error) => {
      toast.error('Failed to update email status');
    }
  });

  const generateDraftMutation = useMutation(generateDraft, {
    onSuccess: (data) => {
      toast.success('AI draft generated successfully!');
      // You could open a draft modal or redirect to compose page here
    },
    onError: (error) => {
      toast.error('Failed to generate draft');
    }
  });

  const getUrgencyColor = (score) => {
    if (score >= 0.8) return 'border-l-red-500 bg-red-50/50';
    if (score >= 0.6) return 'border-l-orange-500 bg-orange-50/50';
    return 'border-l-green-500 bg-green-50/50';
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment) {
      case 'positive': return '😊';
      case 'negative': return '😔';
      default: return '😐';
    }
  };

  const handleAction = (action, e) => {
    e.stopPropagation();
    updateStatusMutation.mutate({ emailId: email.id, action });
  };

  const handleGenerateDraft = (e) => {
    e.stopPropagation();
    generateDraftMutation.mutate(email.id);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        border-l-4 p-4 cursor-pointer transition-all hover:shadow-md
        ${getUrgencyColor(email.ai_analysis?.urgency_score || 0)}
        ${isSelected ? 'bg-blue-50 border-blue-500' : 'bg-white border-gray-200'}
        ${!email.is_read ? 'font-semibold' : ''}
      `}
      onClick={() => onSelect(email)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center space-x-3 mb-2">
            <div className="flex items-center space-x-2">
              <User className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-900">
                {email.sender?.name || email.sender?.email}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              {email.ai_analysis?.meeting_request && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                  <Calendar className="w-3 h-3 mr-1" />
                  Meeting
                </span>
              )}
              {email.ai_analysis?.action_required && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded-full">
                  Action Required
                </span>
              )}
            </div>
          </div>

          {/* Subject */}
          <h3 className="text-sm text-gray-900 truncate mb-1">
            {email.subject}
          </h3>

          {/* Preview */}
          <p className="text-sm text-gray-600 line-clamp-2 mb-2">
            {email.body_preview}
          </p>

          {/* AI Analysis */}
          {email.ai_analysis && (
            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <span>
                {getSentimentIcon(email.ai_analysis.sentiment)} {email.ai_analysis.sentiment}
              </span>
              <span>
                Priority: {email.ai_analysis.urgency_score >= 0.8 ? 'High' : 
                          email.ai_analysis.urgency_score >= 0.6 ? 'Medium' : 'Low'}
              </span>
              {email.ai_analysis.topics?.length > 0 && (
                <span>
                  Topics: {email.ai_analysis.topics.slice(0, 2).join(', ')}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-2 ml-4">
          <div className="text-xs text-gray-500">
            {new Date(email.created_at).toLocaleDateString()}
          </div>
          
          <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => handleAction(email.is_read ? 'mark_unread' : 'mark_read', e)}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title={email.is_read ? 'Mark as unread' : 'Mark as read'}
            >
              {email.is_read ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>

            <button
              onClick={(e) => handleAction('star', e)}
              className="p-1 text-gray-400 hover:text-yellow-500 rounded"
              title="Star email"
            >
              <Star className={`w-4 h-4 ${email.is_starred ? 'text-yellow-500 fill-current' : ''}`} />
            </button>

            <button
              onClick={handleGenerateDraft}
              disabled={generateDraftMutation.isLoading}
              className="p-1 text-gray-400 hover:text-blue-600 rounded disabled:opacity-50"
              title="Generate AI reply"
            >
              {generateDraftMutation.isLoading ? (
                <div className="animate-spin w-4 h-4 border border-blue-600 border-t-transparent rounded-full"></div>
              ) : (
                <Zap className="w-4 h-4" />
              )}
            </button>

            <button
              onClick={(e) => handleAction('archive', e)}
              className="p-1 text-gray-400 hover:text-green-600 rounded"
              title="Archive email"
            >
              <Archive className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Email Detail View Component
const EmailDetailView = ({ email, onClose }) => {
  if (!email) return null;

  return (
    <div className="bg-white border-l border-gray-200 h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {email.subject}
            </h2>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>From: {email.sender?.name || email.sender?.email}</span>
              <span>•</span>
              <span>{new Date(email.created_at).toLocaleString()}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
          >
            <MoreHorizontal className="w-5 h-5" />
          </button>
        </div>

        {/* AI Analysis Summary */}
        {email.ai_analysis && (
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Zap className="w-4 h-4 text-blue-600" />
              <span className="font-medium text-gray-900">AI Analysis</span>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Sentiment:</span>
                <span className="ml-1 font-medium capitalize">{email.ai_analysis.sentiment}</span>
              </div>
              <div>
                <span className="text-gray-600">Priority:</span>
                <span className="ml-1 font-medium">
                  {email.ai_analysis.urgency_score >= 0.8 ? 'High' : 
                   email.ai_analysis.urgency_score >= 0.6 ? 'Medium' : 'Low'}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Action Required:</span>
                <span className="ml-1 font-medium">{email.ai_analysis.action_required ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="text-gray-600">Meeting Request:</span>
                <span className="ml-1 font-medium">{email.ai_analysis.meeting_request ? 'Yes' : 'No'}</span>
              </div>
            </div>
            
            {email.ai_analysis.suggested_actions?.length > 0 && (
              <div className="mt-3">
                <span className="text-gray-600 text-sm">Suggested Actions:</span>
                <ul className="mt-1 space-y-1">
                  {email.ai_analysis.suggested_actions.map((action, index) => (
                    <li key={index} className="text-sm text-gray-700">• {action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Email Content */}
      <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
        <div 
          className="prose max-w-none"
          dangerouslySetInnerHTML={{ 
            __html: email.body_html || email.body_text?.replace(/\n/g, '<br>') || 'No content'
          }}
        />
      </div>

      {/* Actions */}
      <div className="p-6 border-t border-gray-200">
        <div className="flex items-center space-x-3">
          <button className="btn btn-primary">
            <Reply className="w-4 h-4 mr-2" />
            Reply
          </button>
          <button className="btn btn-outline">
            <Forward className="w-4 h-4 mr-2" />
            Forward
          </button>
          <button className="btn btn-outline">
            <Archive className="w-4 h-4 mr-2" />
            Archive
          </button>
          <button className="btn btn-outline text-red-600 hover:bg-red-50">
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

const EmailsPage = () => {
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [filters, setFilters] = useState({
    search: '',
    priority: 'all',
    status: 'all',
    dateFrom: '',
    dateTo: ''
  });

  const queryClient = useQueryClient();

  // Fetch emails with filters
  const { data: emailData, isLoading, error } = useQuery(
    ['emails', filters],
    fetchEmails,
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      keepPreviousData: true
    }
  );

  // Sync emails mutation
  const syncMutation = useMutation(syncEmails, {
    onSuccess: () => {
      queryClient.invalidateQueries('emails');
      toast.success('Emails synced successfully!');
    },
    onError: () => {
      toast.error('Failed to sync emails');
    }
  });

  const handleSync = () => {
    syncMutation.mutate();
  };

  const handleSearch = (e) => {
    setFilters({ ...filters, search: e.target.value });
  };

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load emails. Please try again.</p>
        <button onClick={() => queryClient.invalidateQueries('emails')} className="btn btn-primary mt-4">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Email Management</h1>
            <p className="text-gray-600">AI-powered email processing and insights</p>
          </div>
          <button
            onClick={handleSync}
            disabled={syncMutation.isLoading}
            className="btn btn-primary"
          >
            {syncMutation.isLoading ? (
              <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full mr-2"></div>
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Sync Emails
          </button>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center space-x-4">
          <div className="flex-1 max-w-lg">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search emails..."
                value={filters.search}
                onChange={handleSearch}
                className="input pl-10 w-full"
              />
            </div>
          </div>
          <EmailFilter filters={filters} setFilters={setFilters} />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Email List */}
        <div className={`${selectedEmail ? 'w-1/2' : 'w-full'} border-r border-gray-200 overflow-y-auto custom-scrollbar`}>
          {isLoading ? (
            <div className="p-4 space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse bg-gray-100 rounded-lg p-4">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-full"></div>
                </div>
              ))}
            </div>
          ) : emailData?.emails?.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {emailData.emails.map((email) => (
                <EmailItem
                  key={email.id}
                  email={email}
                  onSelect={setSelectedEmail}
                  isSelected={selectedEmail?.id === email.id}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Mail className="w-16 h-16 mb-4 text-gray-300" />
              <h3 className="text-lg font-medium mb-2">No emails found</h3>
              <p className="text-sm text-center max-w-sm">
                {filters.search || filters.priority !== 'all' || filters.status !== 'all'
                  ? 'Try adjusting your filters or search terms'
                  : 'Connect your email accounts to start managing your emails with AI'}
              </p>
            </div>
          )}
        </div>

        {/* Email Detail */}
        {selectedEmail && (
          <div className="w-1/2">
            <EmailDetailView
              email={selectedEmail}
              onClose={() => setSelectedEmail(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailsPage;