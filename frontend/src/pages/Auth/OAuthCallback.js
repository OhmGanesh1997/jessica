import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

const OAuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get('token');
      const error = searchParams.get('error');

      if (error) {
        toast.error('Authentication failed: ' + error);
        navigate('/auth/login');
        return;
      }

      if (token) {
        // Store the token
        localStorage.setItem('accessToken', token);
        
        // Redirect to dashboard
        toast.success('Successfully signed in!');
        navigate('/dashboard');
      } else {
        toast.error('No authentication token received');
        navigate('/auth/login');
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-gradient-primary flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20"
      >
        <div className="animate-spin w-12 h-12 border-4 border-white/30 border-t-white rounded-full mx-auto mb-4"></div>
        <h3 className="text-white text-lg font-semibold mb-2">
          Completing Sign In
        </h3>
        <p className="text-white/70">
          Please wait while we set up your account...
        </p>
      </motion.div>
    </div>
  );
};

export default OAuthCallback;