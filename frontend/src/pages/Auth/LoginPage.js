import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { useAuth } from '../../contexts/AuthContext';
import { Eye, EyeOff, Mail, Lock, Chrome, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

const LoginPage = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isMicrosoftLoading, setIsMicrosoftLoading] = useState(false);
  
  const { login, isLoginLoading } = useAuth();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const onSubmit = async (data) => {
    try {
      await login(data);
      navigate('/dashboard');
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  const handleGoogleLogin = async () => {
    setIsGoogleLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/google/login`);
      const data = await response.json();
      
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      toast.error('Failed to initialize Google login');
      setIsGoogleLoading(false);
    }
  };

  const handleMicrosoftLogin = async () => {
    setIsMicrosoftLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/microsoft/login`);
      const data = await response.json();
      
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      toast.error('Failed to initialize Microsoft login');
      setIsMicrosoftLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-2">
          Welcome back
        </h2>
        <p className="text-white/70">
          Sign in to your Jessica AI account
        </p>
      </div>

      {/* OAuth Login Options */}
      <div className="space-y-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGoogleLogin}
          disabled={isGoogleLoading}
          className="w-full flex items-center justify-center px-4 py-3 border border-white/20 rounded-lg text-white font-medium hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGoogleLoading ? (
            <div className="animate-spin w-5 h-5 border-2 border-white/30 border-t-white rounded-full mr-3"></div>
          ) : (
            <Chrome className="w-5 h-5 mr-3" />
          )}
          Continue with Google
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleMicrosoftLogin}
          disabled={isMicrosoftLoading}
          className="w-full flex items-center justify-center px-4 py-3 border border-white/20 rounded-lg text-white font-medium hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isMicrosoftLoading ? (
            <div className="animate-spin w-5 h-5 border-2 border-white/30 border-t-white rounded-full mr-3"></div>
          ) : (
            <Zap className="w-5 h-5 mr-3" />
          )}
          Continue with Microsoft
        </motion.button>
      </div>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-white/20" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-transparent text-white/60">Or continue with email</span>
        </div>
      </div>

      {/* Login Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Email Field */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-white mb-1">
            Email address
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
            <input
              id="email"
              type="email"
              autoComplete="email"
              className={`
                w-full pl-10 pr-4 py-3 bg-white/10 border rounded-lg text-white placeholder-white/60 
                focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent
                ${errors.email ? 'border-red-400' : 'border-white/20'}
              `}
              placeholder="Enter your email"
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /\S+@\S+\.\S+/,
                  message: 'Please enter a valid email address',
                },
              })}
            />
          </div>
          {errors.email && (
            <p className="mt-1 text-sm text-red-300">{errors.email.message}</p>
          )}
        </div>

        {/* Password Field */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-white mb-1">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              className={`
                w-full pl-10 pr-12 py-3 bg-white/10 border rounded-lg text-white placeholder-white/60 
                focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent
                ${errors.password ? 'border-red-400' : 'border-white/20'}
              `}
              placeholder="Enter your password"
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
              })}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          {errors.password && (
            <p className="mt-1 text-sm text-red-300">{errors.password.message}</p>
          )}
        </div>

        {/* Forgot Password Link */}
        <div className="text-right">
          <Link
            to="/auth/forgot-password"
            className="text-sm text-white/70 hover:text-white transition-colors"
          >
            Forgot your password?
          </Link>
        </div>

        {/* Submit Button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="submit"
          disabled={isLoginLoading}
          className="w-full bg-white text-blue-600 py-3 px-4 rounded-lg font-semibold hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
        >
          {isLoginLoading ? (
            <>
              <div className="animate-spin w-5 h-5 border-2 border-blue-600/30 border-t-blue-600 rounded-full mr-3"></div>
              Signing in...
            </>
          ) : (
            'Sign in'
          )}
        </motion.button>
      </form>

      {/* Register Link */}
      <div className="text-center">
        <p className="text-white/70">
          Don't have an account?{' '}
          <Link
            to="/auth/register"
            className="text-white font-medium hover:text-white/80 transition-colors"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;