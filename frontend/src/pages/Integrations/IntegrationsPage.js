import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import {
  Link2,
  Plus,
  Settings,
  Trash2,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Chrome,
  Zap,
  Mail,
  Calendar,
  DollarSign,
  MessageSquare,
  Shield,
  Activity,
  Clock
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

// Integrations API functions
const fetchIntegrations = async () => {
  const response = await axios.get('/api/integrations/status');
  return response.data;
};

const connectIntegration = async (provider) => {
  const response = await axios.post(`/api/integrations/${provider}/connect`);
  return response.data;
};

const disconnectIntegration = async (provider) => {
  const response = await axios.delete(`/api/integrations/${provider}/disconnect`);
  return response.data;
};

const testIntegration = async (provider) => {
  const response = await axios.post(`/api/integrations/${provider}/test`);
  return response.data;
};

const syncIntegration = async (provider) => {
  const response = await axios.post(`/api/integrations/${provider}/sync`);
  return response.data;
};

// Integration Card Component
const IntegrationCard = ({ integration, onConnect, onDisconnect, onTest, onSync }) => {
  const [isLoading, setIsLoading] = useState(false);

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'text-green-600 bg-green-100 border-green-200';
      case 'disconnected': return 'text-gray-600 bg-gray-100 border-gray-200';
      case 'error': return 'text-red-600 bg-red-100 border-red-200';
      default: return 'text-yellow-600 bg-yellow-100 border-yellow-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return <CheckCircle className="w-4 h-4" />;
      case 'disconnected': return <XCircle className="w-4 h-4" />;
      case 'error': return <AlertCircle className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  const handleAction = async (action, provider) => {
    setIsLoading(true);
    try {
      switch (action) {
        case 'connect':
          await onConnect(provider);
          break;
        case 'disconnect':
          await onDisconnect(provider);
          break;
        case 'test':
          await onTest(provider);
          break;
        case 'sync':
          await onSync(provider);
          break;
      }
    } catch (error) {
      console.error('Integration action failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-6 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-gray-100 border">
            <integration.icon className="w-6 h-6 text-gray-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{integration.name}</h3>
            <p className="text-sm text-gray-600">{integration.description}</p>
          </div>
        </div>
        
        <div className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(integration.status)}`}>
          {getStatusIcon(integration.status)}
          <span className="ml-1 capitalize">{integration.status}</span>
        </div>
      </div>

      {/* Features */}
      <div className="mb-4">
        <div className="flex flex-wrap gap-2">
          {integration.features?.map((feature, index) => (
            <span
              key={index}
              className="inline-flex items-center px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded-full"
            >
              {feature}
            </span>
          ))}
        </div>
      </div>

      {/* Connection Details */}
      {integration.status === 'connected' && integration.lastSync && (
        <div className="text-xs text-gray-500 mb-4">
          Last synced: {new Date(integration.lastSync).toLocaleString()}
        </div>
      )}

      {/* Error Details */}
      {integration.status === 'error' && integration.errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <p className="text-sm text-red-700">{integration.errorMessage}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center space-x-3">
        {integration.status === 'disconnected' ? (
          <button
            onClick={() => handleAction('connect', integration.provider)}
            disabled={isLoading}
            className="btn btn-primary btn-sm"
          >
            {isLoading ? (
              <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full mr-2"></div>
            ) : (
              <Plus className="w-4 h-4 mr-2" />
            )}
            Connect
          </button>
        ) : (
          <>
            <button
              onClick={() => handleAction('test', integration.provider)}
              disabled={isLoading}
              className="btn btn-outline btn-sm"
            >
              {isLoading ? (
                <div className="animate-spin w-4 h-4 border-2 border-gray-600/30 border-t-gray-600 rounded-full mr-2"></div>
              ) : (
                <Activity className="w-4 h-4 mr-2" />
              )}
              Test
            </button>
            
            {integration.supportSync && (
              <button
                onClick={() => handleAction('sync', integration.provider)}
                disabled={isLoading}
                className="btn btn-outline btn-sm"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Sync
              </button>
            )}
            
            <button
              onClick={() => handleAction('disconnect', integration.provider)}
              disabled={isLoading}
              className="btn btn-outline btn-sm text-red-600 border-red-300 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Disconnect
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
};

// Integration Stats Component
const IntegrationStats = ({ stats }) => {
  const statCards = [
    {
      title: 'Connected Services',
      value: stats?.connectedCount || 0,
      icon: CheckCircle,
      color: 'green'
    },
    {
      title: 'Total Integrations',
      value: stats?.totalCount || 0,
      icon: Link2,
      color: 'blue'
    },
    {
      title: 'Active Syncs',
      value: stats?.activeSyncs || 0,
      icon: RefreshCw,
      color: 'purple'
    },
    {
      title: 'Failed Connections',
      value: stats?.errorCount || 0,
      icon: AlertCircle,
      color: 'red'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {statCards.map((stat, index) => {
        const Icon = stat.icon;
        const colorClasses = {
          green: 'bg-green-50 text-green-600 border-green-200',
          blue: 'bg-blue-50 text-blue-600 border-blue-200',
          purple: 'bg-purple-50 text-purple-600 border-purple-200',
          red: 'bg-red-50 text-red-600 border-red-200',
        };

        return (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-lg border ${colorClasses[stat.color]}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};

const IntegrationsPage = () => {
  const queryClient = useQueryClient();

  // Available integrations
  const availableIntegrations = [
    {
      provider: 'google',
      name: 'Google Workspace',
      description: 'Connect Gmail and Google Calendar for email management and scheduling',
      icon: Chrome,
      features: ['Gmail sync', 'Calendar access', 'Contact management'],
      status: 'disconnected',
      supportSync: true
    },
    {
      provider: 'microsoft',
      name: 'Microsoft 365',
      description: 'Integrate with Outlook and Microsoft Calendar',
      icon: Zap,
      features: ['Outlook sync', 'Teams integration', 'Calendar access'],
      status: 'disconnected',
      supportSync: true
    },
    {
      provider: 'stripe',
      name: 'Stripe',
      description: 'Payment processing for credit purchases',
      icon: DollarSign,
      features: ['Payment processing', 'Subscription management', 'Invoice handling'],
      status: 'connected',
      supportSync: false,
      lastSync: new Date().toISOString()
    },
    {
      provider: 'twilio',
      name: 'Twilio',
      description: 'SMS and WhatsApp notifications',
      icon: MessageSquare,
      features: ['SMS notifications', 'WhatsApp messaging', 'Phone verification'],
      status: 'connected',
      supportSync: false,
      lastSync: new Date().toISOString()
    },
    {
      provider: 'openai',
      name: 'OpenAI',
      description: 'AI-powered email analysis and draft generation',
      icon: Zap,
      features: ['Email analysis', 'Draft generation', 'Smart scheduling'],
      status: 'connected',
      supportSync: false,
      lastSync: new Date().toISOString()
    }
  ];

  // Fetch integrations data
  const { data: integrationsData, isLoading, error } = useQuery(
    'integrations',
    fetchIntegrations,
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      initialData: {
        integrations: availableIntegrations,
        stats: {
          connectedCount: 3,
          totalCount: 5,
          activeSyncs: 2,
          errorCount: 0
        }
      }
    }
  );

  // Connect integration mutation
  const connectMutation = useMutation(connectIntegration, {
    onSuccess: (data, provider) => {
      if (data.auth_url) {
        // Redirect to OAuth flow
        window.location.href = data.auth_url;
      } else {
        queryClient.invalidateQueries('integrations');
        toast.success(`${provider} connected successfully!`);
      }
    },
    onError: (error, provider) => {
      toast.error(`Failed to connect ${provider}: ${error.response?.data?.detail || error.message}`);
    }
  });

  // Disconnect integration mutation
  const disconnectMutation = useMutation(disconnectIntegration, {
    onSuccess: (data, provider) => {
      queryClient.invalidateQueries('integrations');
      toast.success(`${provider} disconnected successfully!`);
    },
    onError: (error, provider) => {
      toast.error(`Failed to disconnect ${provider}: ${error.response?.data?.detail || error.message}`);
    }
  });

  // Test integration mutation
  const testMutation = useMutation(testIntegration, {
    onSuccess: (data, provider) => {
      toast.success(`${provider} connection test successful!`);
    },
    onError: (error, provider) => {
      toast.error(`${provider} connection test failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  // Sync integration mutation
  const syncMutation = useMutation(syncIntegration, {
    onSuccess: (data, provider) => {
      queryClient.invalidateQueries('integrations');
      toast.success(`${provider} sync completed successfully!`);
    },
    onError: (error, provider) => {
      toast.error(`${provider} sync failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  const handleConnect = async (provider) => {
    await connectMutation.mutateAsync(provider);
  };

  const handleDisconnect = async (provider) => {
    if (window.confirm(`Are you sure you want to disconnect ${provider}?`)) {
      await disconnectMutation.mutateAsync(provider);
    }
  };

  const handleTest = async (provider) => {
    await testMutation.mutateAsync(provider);
  };

  const handleSync = async (provider) => {
    await syncMutation.mutateAsync(provider);
  };

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load integrations. Please try again.</p>
        <button onClick={() => queryClient.invalidateQueries('integrations')} className="btn btn-primary mt-4">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-gray-600">Connect your favorite tools and services to automate your workflow</p>
      </div>

      {/* Integration Stats */}
      <IntegrationStats stats={integrationsData?.stats} />

      {/* AI Integration Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6"
      >
        <div className="flex items-center space-x-3 mb-4">
          <Zap className="w-6 h-6 text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-900">Integration Health</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="flex items-center space-x-2 mb-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-green-800">All Systems Operational</span>
            </div>
            <p className="text-sm text-green-700">All connected services are functioning properly</p>
          </div>
          
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="flex items-center space-x-2 mb-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-800">Sync Status</span>
            </div>
            <p className="text-sm text-blue-700">Last full sync completed 2 minutes ago</p>
          </div>
          
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="flex items-center space-x-2 mb-2">
              <Shield className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium text-purple-800">Security Status</span>
            </div>
            <p className="text-sm text-purple-700">All connections are encrypted and secure</p>
          </div>
        </div>
      </motion.div>

      {/* Integrations Grid */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Available Integrations</h2>
          <button className="btn btn-outline">
            <Settings className="w-4 h-4 mr-2" />
            Manage All
          </button>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="animate-pulse card p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-gray-200 rounded-lg"></div>
                  <div className="space-y-2 flex-1">
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {integrationsData?.integrations?.map((integration) => (
              <IntegrationCard
                key={integration.provider}
                integration={integration}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
                onTest={handleTest}
                onSync={handleSync}
              />
            ))}
          </div>
        )}
      </div>

      {/* Integration Benefits */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6"
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Why Connect Your Services?</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="flex items-start space-x-3">
            <Mail className="w-6 h-6 text-blue-600 mt-1" />
            <div>
              <h4 className="font-medium text-gray-900">Smart Email Management</h4>
              <p className="text-sm text-gray-600">AI analyzes your emails and generates intelligent responses</p>
            </div>
          </div>
          
          <div className="flex items-start space-x-3">
            <Calendar className="w-6 h-6 text-green-600 mt-1" />
            <div>
              <h4 className="font-medium text-gray-900">Optimal Scheduling</h4>
              <p className="text-sm text-gray-600">Find the best meeting times automatically across calendars</p>
            </div>
          </div>
          
          <div className="flex items-start space-x-3">
            <MessageSquare className="w-6 h-6 text-purple-600 mt-1" />
            <div>
              <h4 className="font-medium text-gray-900">Multi-Channel Notifications</h4>
              <p className="text-sm text-gray-600">Receive important alerts via SMS, WhatsApp, or email</p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default IntegrationsPage;