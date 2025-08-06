import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import { useForm } from 'react-hook-form';
import {
  User,
  Bell,
  Shield,
  Zap,
  Clock,
  Mail,
  Calendar,
  Globe,
  Moon,
  Sun,
  Palette,
  Key,
  Database,
  Download,
  Trash2,
  Save,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';
import toast from 'react-hot-toast';

// Settings API functions
const fetchUserSettings = async () => {
  const response = await axios.get('/api/users/settings');
  return response.data;
};

const updateUserSettings = async (settings) => {
  const response = await axios.put('/api/users/settings', settings);
  return response.data;
};

const updateUserProfile = async (profile) => {
  const response = await axios.put('/api/users/profile', profile);
  return response.data;
};

const changePassword = async (passwordData) => {
  const response = await axios.post('/api/auth/change-password', passwordData);
  return response.data;
};

const deleteAccount = async () => {
  const response = await axios.delete('/api/users/account');
  return response.data;
};

// Settings Section Component
const SettingsSection = ({ title, description, icon: Icon, children }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="card"
  >
    <div className="card-header">
      <div className="flex items-center space-x-3">
        <Icon className="w-5 h-5 text-gray-600" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
      </div>
    </div>
    <div className="card-body space-y-4">
      {children}
    </div>
  </motion.div>
);

// Profile Settings Component
const ProfileSettings = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      full_name: user?.profile?.full_name || '',
      job_title: user?.profile?.job_title || '',
      company: user?.profile?.company || '',
      phone_number: user?.profile?.phone_number || '',
      bio: user?.profile?.bio || '',
    }
  });

  const updateProfileMutation = useMutation(updateUserProfile, {
    onSuccess: () => {
      queryClient.invalidateQueries('currentUser');
      toast.success('Profile updated successfully!');
    },
    onError: () => {
      toast.error('Failed to update profile');
    }
  });

  const onSubmit = (data) => {
    updateProfileMutation.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Full Name *
          </label>
          <input
            type="text"
            className={`input ${errors.full_name ? 'border-red-300' : ''}`}
            {...register('full_name', { required: 'Full name is required' })}
          />
          {errors.full_name && (
            <p className="text-sm text-red-600 mt-1">{errors.full_name.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Job Title
          </label>
          <input
            type="text"
            className="input"
            {...register('job_title')}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Company
          </label>
          <input
            type="text"
            className="input"
            {...register('company')}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Phone Number
          </label>
          <input
            type="tel"
            className="input"
            {...register('phone_number')}
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Bio
        </label>
        <textarea
          rows={3}
          className="input"
          placeholder="Tell us about yourself..."
          {...register('bio')}
        />
      </div>

      <button
        type="submit"
        disabled={updateProfileMutation.isLoading}
        className="btn btn-primary"
      >
        {updateProfileMutation.isLoading ? (
          <>
            <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full mr-2"></div>
            Saving...
          </>
        ) : (
          <>
            <Save className="w-4 h-4 mr-2" />
            Save Changes
          </>
        )}
      </button>
    </form>
  );
};

// Notification Settings Component
const NotificationSettings = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [settings, setSettings] = useState({
    email_notifications: true,
    sms_notifications: false,
    push_notifications: true,
    urgent_only: false,
    quiet_hours_enabled: true,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00',
    notification_categories: {
      email_alerts: true,
      meeting_reminders: true,
      calendar_updates: true,
      ai_insights: false,
      system_updates: true,
    }
  });

  const updateSettingsMutation = useMutation(updateUserSettings, {
    onSuccess: () => {
      queryClient.invalidateQueries('userSettings');
      toast.success('Notification settings updated!');
    },
    onError: () => {
      toast.error('Failed to update settings');
    }
  });

  const handleToggle = (key, category = null) => {
    if (category) {
      setSettings(prev => ({
        ...prev,
        [category]: {
          ...prev[category],
          [key]: !prev[category][key]
        }
      }));
    } else {
      setSettings(prev => ({
        ...prev,
        [key]: !prev[key]
      }));
    }
  };

  const handleSave = () => {
    updateSettingsMutation.mutate({ notifications: settings });
  };

  const Toggle = ({ checked, onChange, label, description }) => (
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <div className="text-sm font-medium text-gray-900">{label}</div>
        {description && <div className="text-xs text-gray-500">{description}</div>}
      </div>
      <button
        type="button"
        onClick={onChange}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full transition-colors
          ${checked ? 'bg-blue-600' : 'bg-gray-200'}
        `}
      >
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white transition-transform
            ${checked ? 'translate-x-6' : 'translate-x-1'}
          `}
        />
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-md font-medium text-gray-900 mb-3">Delivery Methods</h4>
        <div className="space-y-3">
          <Toggle
            checked={settings.email_notifications}
            onChange={() => handleToggle('email_notifications')}
            label="Email Notifications"
            description="Receive notifications via email"
          />
          <Toggle
            checked={settings.sms_notifications}
            onChange={() => handleToggle('sms_notifications')}
            label="SMS Notifications"
            description="Receive urgent notifications via SMS"
          />
          <Toggle
            checked={settings.push_notifications}
            onChange={() => handleToggle('push_notifications')}
            label="Push Notifications"
            description="Receive browser push notifications"
          />
        </div>
      </div>

      <div>
        <h4 className="text-md font-medium text-gray-900 mb-3">Notification Categories</h4>
        <div className="space-y-3">
          {Object.entries(settings.notification_categories).map(([key, value]) => (
            <Toggle
              key={key}
              checked={value}
              onChange={() => handleToggle(key, 'notification_categories')}
              label={key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
            />
          ))}
        </div>
      </div>

      <div>
        <h4 className="text-md font-medium text-gray-900 mb-3">Quiet Hours</h4>
        <div className="space-y-3">
          <Toggle
            checked={settings.quiet_hours_enabled}
            onChange={() => handleToggle('quiet_hours_enabled')}
            label="Enable Quiet Hours"
            description="Silence non-urgent notifications during specified times"
          />
          {settings.quiet_hours_enabled && (
            <div className="grid grid-cols-2 gap-4 pl-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                <input
                  type="time"
                  value={settings.quiet_hours_start}
                  onChange={(e) => setSettings(prev => ({ ...prev, quiet_hours_start: e.target.value }))}
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                <input
                  type="time"
                  value={settings.quiet_hours_end}
                  onChange={(e) => setSettings(prev => ({ ...prev, quiet_hours_end: e.target.value }))}
                  className="input"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={handleSave}
        disabled={updateSettingsMutation.isLoading}
        className="btn btn-primary"
      >
        {updateSettingsMutation.isLoading ? (
          <>
            <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full mr-2"></div>
            Saving...
          </>
        ) : (
          <>
            <Save className="w-4 h-4 mr-2" />
            Save Settings
          </>
        )}
      </button>
    </div>
  );
};

// AI Preferences Component
const AIPreferences = () => {
  const [preferences, setPreferences] = useState({
    auto_reply_enabled: true,
    draft_generation: true,
    smart_scheduling: true,
    priority_detection: true,
    learning_enabled: true,
    communication_style: 'professional',
    response_length: 'medium',
    creativity_level: 0.7,
  });

  const handleSliderChange = (key, value) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-md font-medium text-gray-900 mb-3">AI Features</h4>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-900">Auto-Reply Generation</div>
              <div className="text-xs text-gray-500">Automatically generate email replies</div>
            </div>
            <button
              type="button"
              onClick={() => setPreferences(prev => ({ ...prev, auto_reply_enabled: !prev.auto_reply_enabled }))}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${preferences.auto_reply_enabled ? 'bg-blue-600' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${preferences.auto_reply_enabled ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-md font-medium text-gray-900 mb-3">Communication Style</h4>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tone</label>
            <select
              value={preferences.communication_style}
              onChange={(e) => setPreferences(prev => ({ ...prev, communication_style: e.target.value }))}
              className="input"
            >
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="formal">Formal</option>
              <option value="friendly">Friendly</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Response Length</label>
            <select
              value={preferences.response_length}
              onChange={(e) => setPreferences(prev => ({ ...prev, response_length: e.target.value }))}
              className="input"
            >
              <option value="brief">Brief</option>
              <option value="medium">Medium</option>
              <option value="detailed">Detailed</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Creativity Level: {Math.round(preferences.creativity_level * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={preferences.creativity_level}
              onChange={(e) => handleSliderChange('creativity_level', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Conservative</span>
              <span>Creative</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Security Settings Component
const SecuritySettings = () => {
  const [showChangePassword, setShowChangePassword] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch
  } = useForm();

  const newPassword = watch('newPassword');

  const changePasswordMutation = useMutation(changePassword, {
    onSuccess: () => {
      toast.success('Password changed successfully!');
      reset();
      setShowChangePassword(false);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    }
  });

  const onSubmit = (data) => {
    changePasswordMutation.mutate({
      current_password: data.currentPassword,
      new_password: data.newPassword
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <button
          onClick={() => setShowChangePassword(!showChangePassword)}
          className="btn btn-outline"
        >
          <Key className="w-4 h-4 mr-2" />
          Change Password
        </button>

        {showChangePassword && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 p-4 border border-gray-200 rounded-lg"
          >
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  className={`input ${errors.currentPassword ? 'border-red-300' : ''}`}
                  {...register('currentPassword', { required: 'Current password is required' })}
                />
                {errors.currentPassword && (
                  <p className="text-sm text-red-600 mt-1">{errors.currentPassword.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  className={`input ${errors.newPassword ? 'border-red-300' : ''}`}
                  {...register('newPassword', {
                    required: 'New password is required',
                    minLength: { value: 8, message: 'Password must be at least 8 characters' },
                    pattern: {
                      value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                      message: 'Password must contain uppercase, lowercase, number and special character'
                    }
                  })}
                />
                {errors.newPassword && (
                  <p className="text-sm text-red-600 mt-1">{errors.newPassword.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  className={`input ${errors.confirmPassword ? 'border-red-300' : ''}`}
                  {...register('confirmPassword', {
                    required: 'Please confirm your new password',
                    validate: value => value === newPassword || 'Passwords do not match'
                  })}
                />
                {errors.confirmPassword && (
                  <p className="text-sm text-red-600 mt-1">{errors.confirmPassword.message}</p>
                )}
              </div>

              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={changePasswordMutation.isLoading}
                  className="btn btn-primary"
                >
                  {changePasswordMutation.isLoading ? (
                    <>
                      <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full mr-2"></div>
                      Changing...
                    </>
                  ) : (
                    'Change Password'
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowChangePassword(false);
                    reset();
                  }}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </div>

      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-md font-medium text-gray-900 mb-3 text-red-600">Danger Zone</h4>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <div className="flex-1">
              <h5 className="font-medium text-red-800">Delete Account</h5>
              <p className="text-sm text-red-700 mt-1">
                Permanently delete your account and all associated data. This action cannot be undone.
              </p>
              <button className="mt-3 btn btn-outline text-red-600 border-red-300 hover:bg-red-50">
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Account
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'ai', label: 'AI Preferences', icon: Zap },
    { id: 'security', label: 'Security', icon: Shield },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileSettings />;
      case 'notifications':
        return <NotificationSettings />;
      case 'ai':
        return <AIPreferences />;
      case 'security':
        return <SecuritySettings />;
      default:
        return <ProfileSettings />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600">Manage your account preferences and AI behavior</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.2 }}
      >
        <SettingsSection
          title={tabs.find(tab => tab.id === activeTab)?.label}
          description={
            activeTab === 'profile' ? 'Manage your personal information and preferences' :
            activeTab === 'notifications' ? 'Control how and when you receive notifications' :
            activeTab === 'ai' ? 'Customize AI behavior and automation preferences' :
            'Manage your account security and privacy settings'
          }
          icon={tabs.find(tab => tab.id === activeTab)?.icon}
        >
          {renderTabContent()}
        </SettingsSection>
      </motion.div>
    </div>
  );
};

export default SettingsPage;