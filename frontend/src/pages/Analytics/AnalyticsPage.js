import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import {
  BarChart3,
  TrendingUp,
  Mail,
  Calendar,
  Clock,
  Target,
  Zap,
  Users,
  ChevronDown,
  Download,
  RefreshCw,
  Filter
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';
import axios from 'axios';

// Analytics API functions
const fetchAnalytics = async ({ queryKey }) => {
  const [_key, params] = queryKey;
  const response = await axios.get('/api/analytics/insights', { params });
  return response.data;
};

const fetchProductivityMetrics = async ({ queryKey }) => {
  const [_key, params] = queryKey;
  const response = await axios.get('/api/analytics/productivity', { params });
  return response.data;
};

const fetchUsageStats = async ({ queryKey }) => {
  const [_key, params] = queryKey;
  const response = await axios.get('/api/analytics/usage', { params });
  return response.data;
};

// Metric Card Component
const MetricCard = ({ title, value, change, icon: Icon, color = 'blue', trend = [] }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
    red: 'bg-red-50 text-red-600 border-red-200',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-6 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        {trend.length > 0 && (
          <div className="w-16 h-8">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={color === 'green' ? '#10b981' : color === 'red' ? '#ef4444' : '#3b82f6'}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      
      <div>
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
        {change !== undefined && (
          <p className={`text-sm mt-1 flex items-center ${
            change >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            <TrendingUp className={`w-4 h-4 mr-1 ${change < 0 ? 'rotate-180' : ''}`} />
            {change >= 0 ? '+' : ''}{change}% from last period
          </p>
        )}
      </div>
    </motion.div>
  );
};

// Time Period Selector
const TimePeriodSelector = ({ selectedPeriod, onChange }) => {
  const periods = [
    { value: '7d', label: 'Last 7 days' },
    { value: '30d', label: 'Last 30 days' },
    { value: '90d', label: 'Last 90 days' },
    { value: '1y', label: 'Last year' },
  ];

  return (
    <div className="relative">
      <select
        value={selectedPeriod}
        onChange={(e) => onChange(e.target.value)}
        className="input pr-8 appearance-none cursor-pointer"
      >
        {periods.map((period) => (
          <option key={period.value} value={period.value}>
            {period.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
    </div>
  );
};

// Activity Chart Component
const ActivityChart = ({ data, title }) => {
  if (!data || data.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>No data available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <button className="btn btn-outline btn-sm">
          <Download className="w-4 h-4 mr-2" />
          Export
        </button>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" stroke="#6b7280" fontSize={12} />
            <YAxis stroke="#6b7280" fontSize={12} />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#1f2937',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 10px 25px rgba(0, 0, 0, 0.2)'
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              fill="url(#colorGradient)"
              strokeWidth={2}
            />
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Email Analysis Chart
const EmailAnalysisChart = ({ data }) => {
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  if (!data || data.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Email Analysis</h3>
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <Mail className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>No email data available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Email Analysis</h3>
      <div className="flex flex-col lg:flex-row items-center">
        <div className="w-full lg:w-1/2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="w-full lg:w-1/2 mt-4 lg:mt-0 lg:ml-6">
          <div className="space-y-3">
            {data.map((item, index) => (
              <div key={item.name} className="flex items-center">
                <div
                  className="w-4 h-4 rounded-full mr-3"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                ></div>
                <div className="flex-1">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-900">{item.name}</span>
                    <span className="text-sm text-gray-600">{item.value}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Productivity Score Component
const ProductivityScore = ({ score, breakdown }) => {
  const getScoreColor = (score) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-blue-600 bg-blue-100';
    if (score >= 50) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getScoreLabel = (score) => {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Average';
    return 'Needs Improvement';
  };

  return (
    <div className="card p-6">
      <div className="text-center mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Productivity Score</h3>
        <div className={`inline-flex items-center px-4 py-2 rounded-full ${getScoreColor(score)}`}>
          <Target className="w-5 h-5 mr-2" />
          <span className="text-2xl font-bold">{score}</span>
          <span className="ml-1">/100</span>
        </div>
        <p className="text-sm text-gray-600 mt-2">{getScoreLabel(score)}</p>
      </div>

      {breakdown && (
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Score Breakdown</h4>
          {breakdown.map((item, index) => (
            <div key={index}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">{item.category}</span>
                <span className="font-medium">{item.score}/100</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${item.score}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const AnalyticsPage = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('30d');

  // Fetch analytics data
  const { data: analyticsData, isLoading: analyticsLoading, error: analyticsError } = useQuery(
    ['analytics', { period: selectedPeriod }],
    fetchAnalytics,
    {
      refetchInterval: 300000, // Refetch every 5 minutes
    }
  );

  const { data: productivityData, isLoading: productivityLoading } = useQuery(
    ['productivity', { period: selectedPeriod }],
    fetchProductivityMetrics
  );

  const { data: usageData, isLoading: usageLoading } = useQuery(
    ['usage', { period: selectedPeriod }],
    fetchUsageStats
  );

  // Sample data for development
  const sampleActivityData = [
    { date: '2024-01-01', value: 45 },
    { date: '2024-01-02', value: 52 },
    { date: '2024-01-03', value: 61 },
    { date: '2024-01-04', value: 48 },
    { date: '2024-01-05', value: 67 },
    { date: '2024-01-06', value: 73 },
    { date: '2024-01-07', value: 58 },
  ];

  const sampleEmailData = [
    { name: 'High Priority', value: 15 },
    { name: 'Medium Priority', value: 35 },
    { name: 'Low Priority', value: 50 },
    { name: 'Urgent', value: 8 },
    { name: 'Action Required', value: 22 },
  ];

  const sampleMetrics = [
    {
      title: 'Emails Processed',
      value: analyticsData?.emails_processed || '127',
      change: analyticsData?.emails_change || 15,
      icon: Mail,
      color: 'blue',
      trend: sampleActivityData.slice(0, 7)
    },
    {
      title: 'Time Saved',
      value: analyticsData?.time_saved || '4.2h',
      change: analyticsData?.time_saved_change || 23,
      icon: Clock,
      color: 'green',
      trend: sampleActivityData.slice(0, 7).map(d => ({ ...d, value: d.value + 10 }))
    },
    {
      title: 'Meetings Scheduled',
      value: analyticsData?.meetings_scheduled || '18',
      change: analyticsData?.meetings_change || -5,
      icon: Calendar,
      color: 'purple',
      trend: sampleActivityData.slice(0, 7).map(d => ({ ...d, value: d.value - 10 }))
    },
    {
      title: 'AI Actions Taken',
      value: analyticsData?.ai_actions || '89',
      change: analyticsData?.ai_actions_change || 31,
      icon: Zap,
      color: 'orange',
      trend: sampleActivityData.slice(0, 7).map(d => ({ ...d, value: d.value + 5 }))
    }
  ];

  if (analyticsError) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load analytics data. Please try again.</p>
        <button onClick={() => window.location.reload()} className="btn btn-primary mt-4">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics & Insights</h1>
          <p className="text-gray-600">Track your productivity and AI automation performance</p>
        </div>
        <div className="flex items-center space-x-3">
          <TimePeriodSelector
            selectedPeriod={selectedPeriod}
            onChange={setSelectedPeriod}
          />
          <button className="btn btn-outline">
            <Filter className="w-4 h-4 mr-2" />
            Filter
          </button>
          <button className="btn btn-primary">
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {sampleMetrics.map((metric, index) => (
          <MetricCard
            key={index}
            title={metric.title}
            value={analyticsLoading ? '...' : metric.value}
            change={analyticsLoading ? undefined : metric.change}
            icon={metric.icon}
            color={metric.color}
            trend={metric.trend}
          />
        ))}
      </motion.div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <ActivityChart
            data={analyticsLoading ? [] : (analyticsData?.activity_data || sampleActivityData)}
            title="Daily Activity Overview"
          />
        </motion.div>

        {/* Productivity Score */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <ProductivityScore
            score={productivityLoading ? 0 : (productivityData?.overall_score || 82)}
            breakdown={productivityData?.breakdown || [
              { category: 'Email Efficiency', score: 88 },
              { category: 'Calendar Optimization', score: 76 },
              { category: 'Response Time', score: 91 },
              { category: 'AI Utilization', score: 79 }
            ]}
          />
        </motion.div>

        {/* Email Analysis */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-1"
        >
          <EmailAnalysisChart
            data={analyticsLoading ? [] : (analyticsData?.email_analysis || sampleEmailData)}
          />
        </motion.div>

        {/* Usage Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-2"
        >
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Feature Usage</h3>
              <RefreshCw className="w-5 h-5 text-gray-400" />
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={usageData?.feature_usage || [
                  { feature: 'Email Analysis', usage: 85 },
                  { feature: 'Draft Generation', usage: 67 },
                  { feature: 'Calendar Sync', usage: 92 },
                  { feature: 'Smart Scheduling', usage: 74 },
                  { feature: 'Notifications', usage: 81 }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="feature" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="usage" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
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
        <div className="card p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Zap className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">AI-Generated Insights</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-800">Performance Trend</span>
              </div>
              <p className="text-sm text-blue-700">
                Your email response time has improved by 35% this month, with AI assistance handling 67% of routine replies.
              </p>
            </div>
            
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Target className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-green-800">Optimization Opportunity</span>
              </div>
              <p className="text-sm text-green-700">
                Schedule meetings between 10-11 AM for 15% better attendance rates based on your historical data.
              </p>
            </div>
            
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Users className="w-4 h-4 text-purple-600" />
                <span className="text-sm font-medium text-purple-800">Collaboration Pattern</span>
              </div>
              <p className="text-sm text-purple-700">
                You communicate most effectively with your team on Tuesdays and Wednesdays, with 40% faster response rates.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default AnalyticsPage;