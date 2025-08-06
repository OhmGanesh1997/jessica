import React, { createContext, useContext, useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

const AuthContext = createContext();

// Configure axios defaults
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
axios.defaults.baseURL = API_BASE_URL;

// Axios interceptor for auth token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Axios interceptor for handling auth errors
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Clear auth data
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      
      // Redirect to login
      window.location.href = '/auth/login';
      
      return Promise.reject(error);
    }
    
    return Promise.reject(error);
  }
);

// Auth API functions
const authAPI = {
  login: async (credentials) => {
    const response = await axios.post('/api/auth/login', credentials);
    return response.data;
  },
  
  register: async (userData) => {
    const response = await axios.post('/api/auth/register', userData);
    return response.data;
  },
  
  getCurrentUser: async () => {
    const response = await axios.get('/api/auth/me');
    return response.data;
  },
  
  logout: async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      console.log('Logout error:', error);
    }
  },
  
  refreshToken: async () => {
    const response = await axios.post('/api/auth/refresh-token');
    return response.data;
  },
  
  forgotPassword: async (email) => {
    const response = await axios.post('/api/auth/forgot-password', { email });
    return response.data;
  },
  
  resetPassword: async (token, newPassword) => {
    const response = await axios.post('/api/auth/reset-password', {
      token,
      new_password: newPassword
    });
    return response.data;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const queryClient = useQueryClient();

  // Get current user query
  const { data: userData, isLoading, error } = useQuery(
    ['currentUser'],
    authAPI.getCurrentUser,
    {
      enabled: !!localStorage.getItem('accessToken'),
      retry: false,
      onSuccess: (data) => {
        setUser(data);
        setIsInitialized(true);
      },
      onError: (error) => {
        console.log('Auth error:', error);
        localStorage.removeItem('accessToken');
        setUser(null);
        setIsInitialized(true);
      }
    }
  );

  // Initialize auth state
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setIsInitialized(true);
    }
  }, []);

  // Login mutation
  const loginMutation = useMutation(authAPI.login, {
    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      setUser(data.user);
      queryClient.setQueryData(['currentUser'], data.user);
      toast.success('Welcome back!');
    },
    onError: (error) => {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
    }
  });

  // Register mutation
  const registerMutation = useMutation(authAPI.register, {
    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      setUser(data.user);
      queryClient.setQueryData(['currentUser'], data.user);
      toast.success('Account created successfully!');
    },
    onError: (error) => {
      const message = error.response?.data?.detail || 'Registration failed';
      toast.error(message);
    }
  });

  // Logout mutation
  const logoutMutation = useMutation(authAPI.logout, {
    onSettled: () => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      queryClient.clear();
      toast.success('Logged out successfully');
    }
  });

  // Forgot password mutation
  const forgotPasswordMutation = useMutation(authAPI.forgotPassword, {
    onSuccess: () => {
      toast.success('Password reset email sent!');
    },
    onError: (error) => {
      const message = error.response?.data?.detail || 'Failed to send reset email';
      toast.error(message);
    }
  });

  // Reset password mutation
  const resetPasswordMutation = useMutation(
    ({ token, password }) => authAPI.resetPassword(token, password),
    {
      onSuccess: () => {
        toast.success('Password reset successfully!');
      },
      onError: (error) => {
        const message = error.response?.data?.detail || 'Password reset failed';
        toast.error(message);
      }
    }
  );

  const value = {
    // State
    user,
    isLoading: isLoading || !isInitialized,
    isAuthenticated: !!user,
    
    // Actions
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: logoutMutation.mutate,
    forgotPassword: forgotPasswordMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    
    // Loading states
    isLoginLoading: loginMutation.isLoading,
    isRegisterLoading: registerMutation.isLoading,
    isLogoutLoading: logoutMutation.isLoading,
    isForgotPasswordLoading: forgotPasswordMutation.isLoading,
    isResetPasswordLoading: resetPasswordMutation.isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};