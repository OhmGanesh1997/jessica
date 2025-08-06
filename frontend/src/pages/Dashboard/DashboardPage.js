import React from 'react';
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import {
  Mail,
  Calendar,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  CreditCard,
  Link2,
  BarChart3,
  Zap,
  Users,
  Target
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';

// API functions
const fetchDashboardStats = async () => {
  const response = await axios.get('/api/analytics/dashboard');
  return response.data;
};

const fetchRecentEmails = async () => {
  const response = await axios.get('/api/emails?limit=5&sort=created_at_desc');
  return response.data;
};

const fetchUpcomingEvents = async () => {
  const response = await axios.get('/api/calendar/events?limit=5&upcoming=true');
  return response.data;
};

// Stats Card Component
const StatsCard = ({ title, value, change, icon: Icon, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="card p-6 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {change && (
            <p className={`text-sm mt-1 ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {change >= 0 ? '+' : ''}{change}% from last week
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </motion.div>
  );
};

// Quick Action Card Component
const QuickActionCard = ({ title, description, icon: Icon, color, onClick }) => {
  const colorClasses = {
    blue: 'hover:bg-blue-50 hover:border-blue-200',
    green: 'hover:bg-green-50 hover:border-green-200',
    orange: 'hover:bg-orange-50 hover:border-orange-200',
    purple: 'hover:bg-purple-50 hover:border-purple-200',
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`card p-4 cursor-pointer transition-all ${colorClasses[color]}`}
    >
      <div className="flex items-center space-x-3">
        <Icon className={`w-5 h-5 text-${color}-600`} />
        <div>
          <h4 className="font-medium text-gray-900">{title}</h4>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
      </div>
    </motion.div>
  );
};

// Recent Email Item Component
const RecentEmailItem = ({ email }) => {
  const getUrgencyColor = (score) => {
    if (score >= 0.8) return 'text-red-600 bg-red-50';
    if (score >= 0.6) return 'text-orange-600 bg-orange-50';
    return 'text-green-600 bg-green-50';
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment) {
      case 'positive': return '😊';
      case 'negative': return '😔';
      default: return '😐';
    }
  };

  return (
    <div className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {email.subject}
        </p>
        <p className="text-sm text-gray-500 truncate">
          From: {email.sender?.name || email.sender?.email}
        </p>
        <div className="flex items-center space-x-2 mt-1">
          <span className="text-xs">{getSentimentIcon(email.ai_analysis?.sentiment)}</span>
          <span className={`px-2 py-1 text-xs rounded-full ${getUrgencyColor(email.ai_analysis?.urgency_score || 0)}`}>
            {email.ai_analysis?.urgency_score >= 0.8 ? 'High' : 
             email.ai_analysis?.urgency_score >= 0.6 ? 'Medium' : 'Low'} Priority
          </span>
        </div>
      </div>
      <div className="text-xs text-gray-500">
        {new Date(email.created_at).toLocaleDateString()}
      </div>
    </div>
  );
};

// Upcoming Event Item Component
const UpcomingEventItem = ({ event }) => (
  <div className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors">
    <div className="flex-1 min-w-0">
      <p className="text-sm font-medium text-gray-900 truncate">{event.title}</p>
      <p className="text-sm text-gray-500">
        {new Date(event.start_datetime).toLocaleString()}
      </p>
      {event.attendees?.length > 0 && (
        <p className="text-xs text-gray-400 mt-1">
          {event.attendees.length} attendee{event.attendees.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
    <div className="text-xs text-gray-500">
      {event.location?.name && <span>📍 {event.location.name}</span>}
    </div>
  </div>
);

const DashboardPage = () => {
  const { user } = useAuth();
  
  // Fetch dashboard data
  const { data: stats, isLoading: statsLoading } = useQuery(
    'dashboardStats', 
    fetchDashboardStats,
    { refetchInterval: 30000 } // Refetch every 30 seconds
  );

  const { data: recentEmails, isLoading: emailsLoading } = useQuery(
    'recentEmails',
    fetchRecentEmails,
    { refetchInterval: 30000 }
  );

  const { data: upcomingEvents, isLoading: eventsLoading } = useQuery(
    'upcomingEvents',
    fetchUpcomingEvents,
    { refetchInterval: 60000 } // Refetch every minute
  );

  // Quick actions
  const quickActions = [
    {
      title: 'Check New Emails',
      description: 'Review and process incoming emails',
      icon: Mail,
      color: 'blue',
      onClick: () => window.location.href = '/emails'
    },
    {
      title: 'Schedule Meeting',
      description: 'Find optimal time slots for meetings',
      icon: Calendar,
      color: 'green',
      onClick: () => window.location.href = '/calendar'
    },
    {
      title: 'View Analytics',
      description: 'Check your productivity insights',
      icon: BarChart3,
      color: 'purple',
      onClick: () => window.location.href = '/analytics'
    },
    {
      title: 'Manage Integrations',
      description: 'Connect your apps and services',
      icon: Link2,
      color: 'orange',
      onClick: () => window.location.href = '/integrations'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-primary rounded-xl p-6 text-white"
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              Welcome back, {user?.profile?.full_name?.split(' ')[0] || 'User'}! 👋
            </h1>
            <p className="text-white/80 mt-1">
              Here's what's happening in your workspace today.
            </p>
          </div>
          <div className="text-right">
            <div className="bg-white/10 backdrop-blur-sm rounded-lg px-4 py-2 border border-white/20">
              <div className="text-sm text-white/80">Available Credits</div>
              <div className="text-xl font-bold">
                {user?.credits?.remaining_credits || 0}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        <StatsCard
          title="Emails Processed"
          value={statsLoading ? '...' : (stats?.emails_processed || user?.activity?.emails_processed || 0)}
          change={statsLoading ? null : (stats?.emails_change || 12)}
          icon={Mail}
          color="blue"
        />
        <StatsCard
          title="Meetings Scheduled"
          value={statsLoading ? '...' : (stats?.meetings_scheduled || user?.activity?.meetings_scheduled || 0)}
          change={statsLoading ? null : (stats?.meetings_change || 8)}
          icon={Calendar}
          color="green"
        />
        <StatsCard
          title="Time Saved"
          value={statsLoading ? '...' : `${Math.floor((user?.activity?.total_time_saved_minutes || 0) / 60)}h`}
          change={statsLoading ? null : (stats?.time_saved_change || 15)}
          icon={Clock}
          color="purple"
        />
        <StatsCard
          title="Productivity Score"
          value={statsLoading ? '...' : (stats?.productivity_score || '85%')}
          change={statsLoading ? null : (stats?.productivity_change || 5)}
          icon={TrendingUp}
          color="orange"
        />
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-1"
        >
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
              <p className="text-sm text-gray-600">Get things done faster</p>
            </div>
            <div className="card-body space-y-3">
              {quickActions.map((action, index) => (
                <QuickActionCard key={index} {...action} />
              ))}
            </div>
          </div>
        </motion.div>

        {/* Recent Emails */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-1"
        >
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Recent Emails</h3>
                  <p className="text-sm text-gray-600">Latest messages requiring attention</p>
                </div>
                <Mail className="w-5 h-5 text-gray-400" />
              </div>
            </div>
            <div className="card-body">
              {emailsLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : recentEmails?.emails?.length > 0 ? (
                <div className="space-y-2">
                  {recentEmails.emails.slice(0, 5).map((email) => (
                    <RecentEmailItem key={email.id} email={email} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Mail className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p>No recent emails</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Upcoming Events */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-1"
        >
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Upcoming Events</h3>
                  <p className="text-sm text-gray-600">Your next meetings and appointments</p>
                </div>
                <Calendar className="w-5 h-5 text-gray-400" />
              </div>
            </div>
            <div className="card-body">
              {eventsLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : upcomingEvents?.events?.length > 0 ? (
                <div className="space-y-2">
                  {upcomingEvents.events.slice(0, 5).map((event) => (
                    <UpcomingEventItem key={event.id} event={event} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Calendar className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p>No upcoming events</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      {/* AI Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <div className="card">
          <div className="card-header">
            <div className="flex items-center space-x-2">
              <Zap className="w-5 h-5 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>
                <p className="text-sm text-gray-600">Personalized recommendations based on your activity</p>
              </div>
            </div>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Target className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-800">Productivity Tip</span>
                </div>
                <p className="text-sm text-blue-700">
                  Schedule your meetings between 10 AM - 12 PM for better engagement rates.
                </p>
              </div>
              
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-medium text-green-800">Achievement</span>
                </div>
                <p className="text-sm text-green-700">
                  You've responded to emails 25% faster this week! Keep it up.
                </p>
              </div>
              
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <AlertCircle className="w-4 h-4 text-orange-600" />
                  <span className="text-sm font-medium text-orange-800">Reminder</span>
                </div>
                <p className="text-sm text-orange-700">
                  You have 3 high-priority emails that need attention today.
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default DashboardPage;