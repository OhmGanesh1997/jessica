import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { useAuth } from '../../contexts/AuthContext';
import { Eye, EyeOff, Mail, Lock, User, Building, Chrome, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

const RegisterPage = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isMicrosoftLoading, setIsMicrosoftLoading] = useState(false);
  
  const { register: registerUser, isRegisterLoading } = useAuth();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm();

  const password = watch('password');

  const onSubmit = async (data) => {
    try {
      await registerUser(data);
      navigate('/dashboard');
    } catch (error) {
      console.error('Registration error:', error);
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
          Create your account
        </h2>
        <p className="text-white/70">
          Join Jessica AI and boost your productivity
        </p>
      </div>

      {/* OAuth Registration Options */}
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

      {/* Registration Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Full Name */}
        <div>
          <label htmlFor="full_name" className="block text-sm font-medium text-white mb-1">
            Full name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
            <input
              id="full_name"
              type="text"
              autoComplete="name"
              className={`
                w-full pl-10 pr-4 py-3 bg-white/10 border rounded-lg text-white placeholder-white/60 
                focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent
                ${errors.full_name ? 'border-red-400' : 'border-white/20'}
              `}
              placeholder="Enter your full name"
              {...register('full_name', {
                required: 'Full name is required',
                minLength: {
                  value: 2,
                  message: 'Name must be at least 2 characters',
                },
              })}
            />
          </div>
          {errors.full_name && (
            <p className="mt-1 text-sm text-red-300">{errors.full_name.message}</p>
          )}
        </div>

        {/* Email */}
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

        {/* Job Title (Optional) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="job_title" className="block text-sm font-medium text-white mb-1">
              Job title <span className="text-white/60">(optional)</span>
            </label>
            <input
              id="job_title"
              type="text"
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
              placeholder="e.g. Product Manager"
              {...register('job_title')}
            />
          </div>

          <div>
            <label htmlFor="company" className="block text-sm font-medium text-white mb-1">
              Company <span className="text-white/60">(optional)</span>
            </label>
            <div className="relative">
              <Building className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
              <input
                id="company"
                type="text"
                className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
                placeholder="e.g. Acme Corp"
                {...register('company')}
              />
            </div>
          </div>
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-white mb-1">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              className={`
                w-full pl-10 pr-12 py-3 bg-white/10 border rounded-lg text-white placeholder-white/60 
                focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent
                ${errors.password ? 'border-red-400' : 'border-white/20'}
              `}
              placeholder="Create a password"
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
                pattern: {
                  value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                  message: 'Password must contain uppercase, lowercase, number and special character',
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

        {/* Terms and Conditions */}
        <div className="flex items-center">
          <input
            id="terms"
            type="checkbox"
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-white/20 rounded bg-white/10"
            {...register('terms', {
              required: 'You must agree to the terms and conditions',
            })}
          />
          <label htmlFor="terms" className="ml-2 block text-sm text-white/70">
            I agree to the{' '}
            <Link to="/terms" className="text-white hover:text-white/80">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link to="/privacy" className="text-white hover:text-white/80">
              Privacy Policy
            </Link>
          </label>
        </div>
        {errors.terms && (
          <p className="text-sm text-red-300">{errors.terms.message}</p>
        )}

        {/* Submit Button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="submit"
          disabled={isRegisterLoading}
          className="w-full bg-white text-blue-600 py-3 px-4 rounded-lg font-semibold hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
        >
          {isRegisterLoading ? (
            <>
              <div className="animate-spin w-5 h-5 border-2 border-blue-600/30 border-t-blue-600 rounded-full mr-3"></div>
              Creating account...
            </>
          ) : (
            'Create account'
          )}
        </motion.button>
      </form>

      {/* Login Link */}
      <div className="text-center">
        <p className="text-white/70">
          Already have an account?{' '}
          <Link
            to="/auth/login"
            className="text-white font-medium hover:text-white/80 transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;