import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import {
  CreditCard,
  Zap,
  TrendingUp,
  Calendar,
  Check,
  Star,
  Gift,
  History,
  Download,
  AlertCircle,
  Info
} from 'lucide-react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import axios from 'axios';
import toast from 'react-hot-toast';

// Initialize Stripe
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY);

// Credits API functions
const fetchCreditsInfo = async () => {
  const response = await axios.get('/api/payments/credits');
  return response.data;
};

const fetchUsageHistory = async ({ queryKey }) => {
  const [_key, params] = queryKey;
  const response = await axios.get('/api/payments/usage-history', { params });
  return response.data;
};

const purchaseCredits = async (packageData) => {
  const response = await axios.post('/api/payments/purchase-credits', packageData);
  return response.data;
};

const createPaymentIntent = async (amount, packageId) => {
  const response = await axios.post('/api/payments/create-payment-intent', {
    amount,
    package_id: packageId
  });
  return response.data;
};

// Credit Package Card Component
const CreditPackageCard = ({ package: pkg, isPopular, onSelect, isSelected }) => (
  <motion.div
    whileHover={{ scale: 1.02 }}
    whileTap={{ scale: 0.98 }}
    className={`
      relative card p-6 cursor-pointer transition-all
      ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:shadow-lg'}
      ${isPopular ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50' : ''}
    `}
    onClick={() => onSelect(pkg)}
  >
    {isPopular && (
      <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
        <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center">
          <Star className="w-3 h-3 mr-1" />
          Most Popular
        </div>
      </div>
    )}

    <div className="text-center">
      <div className="mb-4">
        <div className={`inline-flex p-3 rounded-full ${
          isPopular ? 'bg-blue-600' : 'bg-gray-100'
        }`}>
          <Zap className={`w-8 h-8 ${
            isPopular ? 'text-white' : 'text-gray-600'
          }`} />
        </div>
      </div>

      <h3 className="text-xl font-bold text-gray-900 mb-2">{pkg.name}</h3>
      <p className="text-gray-600 text-sm mb-4">{pkg.description}</p>

      <div className="mb-4">
        <div className="text-3xl font-bold text-gray-900">
          {pkg.credits.toLocaleString()}
        </div>
        <div className="text-sm text-gray-500">credits</div>
      </div>

      <div className="mb-4">
        <div className="text-2xl font-bold text-blue-600">
          ${pkg.price}
        </div>
        <div className="text-sm text-gray-500">
          ${(pkg.price / pkg.credits).toFixed(3)} per credit
        </div>
      </div>

      {pkg.savings > 0 && (
        <div className="mb-4">
          <div className="inline-flex items-center px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
            <TrendingUp className="w-3 h-3 mr-1" />
            Save {pkg.savings}%
          </div>
        </div>
      )}

      <div className="space-y-2 text-sm text-gray-600">
        {pkg.features.map((feature, index) => (
          <div key={index} className="flex items-center">
            <Check className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" />
            <span>{feature}</span>
          </div>
        ))}
      </div>
    </div>
  </motion.div>
);

// Payment Form Component
const PaymentForm = ({ selectedPackage, onSuccess, onCancel }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsLoading(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);

    try {
      // Create payment intent
      const { client_secret } = await createPaymentIntent(
        selectedPackage.price * 100, // Convert to cents
        selectedPackage.id
      );

      // Confirm payment
      const { error, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
        payment_method: {
          card: cardElement,
        }
      });

      if (error) {
        setError(error.message);
        toast.error(error.message);
      } else if (paymentIntent.status === 'succeeded') {
        onSuccess(paymentIntent);
        toast.success('Payment successful! Credits added to your account.');
      }
    } catch (err) {
      setError(err.message);
      toast.error('Payment failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl max-w-md w-full p-6"
      >
        <div className="text-center mb-6">
          <h3 className="text-xl font-semibold text-gray-900">Complete Payment</h3>
          <p className="text-gray-600 mt-1">
            Purchase {selectedPackage.credits.toLocaleString()} credits for ${selectedPackage.price}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Card Information
            </label>
            <div className="p-3 border border-gray-300 rounded-lg">
              <CardElement
                options={{
                  style: {
                    base: {
                      fontSize: '16px',
                      color: '#424770',
                      '::placeholder': {
                        color: '#aab7c4',
                      },
                    },
                  },
                }}
              />
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center">
                <AlertCircle className="w-4 h-4 text-red-600 mr-2" />
                <p className="text-sm text-red-600">{error}</p>
              </div>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="btn btn-outline flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!stripe || isLoading}
              className="btn btn-primary flex-1"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full mr-2"></div>
                  Processing...
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4 mr-2" />
                  Pay ${selectedPackage.price}
                </>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

// Usage History Component
const UsageHistory = ({ history }) => {
  if (!history || history.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <History className="w-12 h-12 mx-auto mb-2 text-gray-300" />
        <p>No usage history available</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {history.map((item, index) => (
        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${
              item.type === 'purchase' ? 'bg-green-100 text-green-600' :
              item.type === 'usage' ? 'bg-blue-100 text-blue-600' :
              'bg-gray-100 text-gray-600'
            }`}>
              {item.type === 'purchase' ? <Gift className="w-4 h-4" /> :
               item.type === 'usage' ? <Zap className="w-4 h-4" /> :
               <History className="w-4 h-4" />}
            </div>
            <div>
              <div className="font-medium text-gray-900">{item.description}</div>
              <div className="text-sm text-gray-500">
                {new Date(item.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
          <div className={`font-semibold ${
            item.type === 'purchase' ? 'text-green-600' : 'text-red-600'
          }`}>
            {item.type === 'purchase' ? '+' : '-'}{item.credits}
          </div>
        </div>
      ))}
    </div>
  );
};

const CreditsPage = () => {
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const queryClient = useQueryClient();

  // Credit packages
  const creditPackages = [
    {
      id: 'starter',
      name: 'Starter Pack',
      description: 'Perfect for light usage',
      credits: 100,
      price: 9.99,
      savings: 0,
      features: [
        '100 AI email analyses',
        '50 draft generations',
        '25 calendar optimizations',
        'Basic support'
      ]
    },
    {
      id: 'professional',
      name: 'Professional',
      description: 'Best for regular users',
      credits: 500,
      price: 39.99,
      savings: 20,
      features: [
        '500 AI email analyses',
        '250 draft generations',
        '125 calendar optimizations',
        'Priority support',
        'Advanced analytics'
      ]
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      description: 'For power users',
      credits: 1500,
      price: 99.99,
      savings: 33,
      features: [
        '1500 AI email analyses',
        '750 draft generations',
        '375 calendar optimizations',
        '24/7 priority support',
        'Advanced analytics',
        'Custom integrations'
      ]
    }
  ];

  // Fetch credits info
  const { data: creditsInfo, isLoading: creditsLoading } = useQuery(
    'creditsInfo',
    fetchCreditsInfo,
    {
      refetchInterval: 30000, // Refetch every 30 seconds
    }
  );

  // Fetch usage history
  const { data: usageHistory, isLoading: historyLoading } = useQuery(
    ['usageHistory', { limit: 20 }],
    fetchUsageHistory,
    {
      enabled: showHistory,
    }
  );

  const handlePackageSelect = (pkg) => {
    setSelectedPackage(pkg);
    setShowPaymentForm(true);
  };

  const handlePaymentSuccess = (paymentIntent) => {
    setShowPaymentForm(false);
    setSelectedPackage(null);
    queryClient.invalidateQueries('creditsInfo');
    queryClient.invalidateQueries('currentUser');
  };

  const handlePaymentCancel = () => {
    setShowPaymentForm(false);
    setSelectedPackage(null);
  };

  return (
    <Elements stripe={stripePromise}>
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Credits & Billing</h1>
          <p className="text-gray-600">Manage your credits and purchase additional AI processing power</p>
        </div>

        {/* Current Credits Status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-primary rounded-xl p-6 text-white text-center"
        >
          <div className="flex items-center justify-center space-x-3 mb-4">
            <Zap className="w-8 h-8" />
            <h2 className="text-2xl font-bold">Current Balance</h2>
          </div>
          
          <div className="text-4xl font-bold mb-2">
            {creditsLoading ? '...' : (creditsInfo?.remaining_credits || 0).toLocaleString()}
          </div>
          <div className="text-white/80">credits remaining</div>
          
          {creditsInfo?.usage_this_month && (
            <div className="mt-4 text-white/80">
              Used {creditsInfo.usage_this_month} credits this month
            </div>
          )}
        </motion.div>

        {/* Usage Insights */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="card p-6 text-center">
            <div className="p-3 bg-blue-100 rounded-full w-12 h-12 mx-auto mb-3 flex items-center justify-center">
              <Zap className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {creditsLoading ? '...' : (creditsInfo?.total_used || 0)}
            </div>
            <div className="text-sm text-gray-600">Total Credits Used</div>
          </div>
          
          <div className="card p-6 text-center">
            <div className="p-3 bg-green-100 rounded-full w-12 h-12 mx-auto mb-3 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {creditsLoading ? '...' : (creditsInfo?.efficiency_score || 85)}%
            </div>
            <div className="text-sm text-gray-600">Usage Efficiency</div>
          </div>
          
          <div className="card p-6 text-center">
            <div className="p-3 bg-purple-100 rounded-full w-12 h-12 mx-auto mb-3 flex items-center justify-center">
              <Calendar className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {creditsLoading ? '...' : (creditsInfo?.days_remaining || 30)}
            </div>
            <div className="text-sm text-gray-600">Est. Days Remaining</div>
          </div>
        </motion.div>

        {/* Credit Packages */}
        <div className="space-y-6">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Choose Your Credit Package</h2>
            <p className="text-gray-600">Select the perfect amount of AI processing credits for your needs</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {creditPackages.map((pkg, index) => (
              <CreditPackageCard
                key={pkg.id}
                package={pkg}
                isPopular={index === 1}
                onSelect={handlePackageSelect}
                isSelected={selectedPackage?.id === pkg.id}
              />
            ))}
          </div>
        </div>

        {/* Usage Information */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6"
        >
          <div className="flex items-center space-x-3 mb-4">
            <Info className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">How Credits Work</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="font-semibold text-2xl text-blue-600 mb-1">1</div>
              <div className="font-medium text-gray-900 mb-1">Email Analysis</div>
              <div className="text-sm text-gray-600">Per email analyzed by AI</div>
            </div>
            
            <div className="text-center">
              <div className="font-semibold text-2xl text-green-600 mb-1">2</div>
              <div className="font-medium text-gray-900 mb-1">Draft Generation</div>
              <div className="text-sm text-gray-600">Per AI-generated email draft</div>
            </div>
            
            <div className="text-center">
              <div className="font-semibold text-2xl text-purple-600 mb-1">3</div>
              <div className="font-medium text-gray-900 mb-1">Smart Scheduling</div>
              <div className="text-sm text-gray-600">Per calendar optimization</div>
            </div>
            
            <div className="text-center">
              <div className="font-semibold text-2xl text-orange-600 mb-1">1</div>
              <div className="font-medium text-gray-900 mb-1">Priority Analysis</div>
              <div className="text-sm text-gray-600">Per priority classification</div>
            </div>
          </div>
        </motion.div>

        {/* Usage History */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Usage History</h3>
                <p className="text-sm text-gray-600">Track your credit usage and purchases</p>
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className="btn btn-outline btn-sm"
                >
                  <History className="w-4 h-4 mr-2" />
                  {showHistory ? 'Hide' : 'Show'} History
                </button>
                <button className="btn btn-outline btn-sm">
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </button>
              </div>
            </div>
          </div>
          
          {showHistory && (
            <div className="card-body">
              {historyLoading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="animate-pulse flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gray-200 rounded-lg"></div>
                        <div className="space-y-2">
                          <div className="h-4 bg-gray-200 rounded w-40"></div>
                          <div className="h-3 bg-gray-200 rounded w-24"></div>
                        </div>
                      </div>
                      <div className="h-4 bg-gray-200 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <UsageHistory history={usageHistory?.transactions || []} />
              )}
            </div>
          )}
        </div>

        {/* Payment Modal */}
        {showPaymentForm && selectedPackage && (
          <PaymentForm
            selectedPackage={selectedPackage}
            onSuccess={handlePaymentSuccess}
            onCancel={handlePaymentCancel}
          />
        )}
      </div>
    </Elements>
  );
};

export default CreditsPage;