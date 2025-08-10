import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { authAPI } from "../api";
import { Mail, Clock, RefreshCw, CheckCircle } from "lucide-react";

const VerifyAccount: React.FC = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cooldownTime, setCooldownTime] = useState(0);

  // Initialize cooldown from localStorage on component mount
  useEffect(() => {
    const savedCooldownEnd = localStorage.getItem('verification_cooldown_end');
    if (savedCooldownEnd) {
      const endTime = parseInt(savedCooldownEnd);
      const now = Date.now();
      const remainingTime = Math.max(0, Math.ceil((endTime - now) / 1000));
      
      if (remainingTime > 0) {
        setCooldownTime(remainingTime);
      } else {
        // Cooldown has expired, clean up localStorage
        localStorage.removeItem('verification_cooldown_end');
      }
    }
  }, []);

  // Cooldown timer effect
  useEffect(() => {
    if (cooldownTime > 0) {
      const timer = setInterval(() => {
        setCooldownTime((prev) => {
          const newTime = prev - 1;
          if (newTime <= 0) {
            // Cooldown finished, clean up localStorage
            localStorage.removeItem('verification_cooldown_end');
          }
          return newTime;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [cooldownTime]);

  const handleResendVerification = async () => {
    if (cooldownTime > 0) return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await authAPI.resendVerification();
      setMessage(response.message || "Verification email sent successfully!");
      
      // Store cooldown end time in localStorage
      const cooldownEndTime = Date.now() + (60 * 1000); // 1 minute from now
      localStorage.setItem('verification_cooldown_end', cooldownEndTime.toString());
      setCooldownTime(60); // 1 minute cooldown
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        "Failed to send verification email. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen text-white px-4 py-12 flex items-center justify-center">
      <div className="max-w-md w-full bg-white/5 backdrop-blur-md rounded-xl border border-white/10 shadow-lg p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-gradient-to-r from-[#ff00cc] to-[#39ff14] rounded-full flex items-center justify-center mb-4">
            <Mail className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold mb-2 font-glitch">
            Account Verification Required
          </h1>
          <p className="text-gray-400 text-sm">
            Please verify your email address to access all features
          </p>
        </div>

        {/* User Info */}
        <div className="bg-black bg-opacity-30 border border-[#ff00cc] rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Logged in as:</p>
              <p className="text-[#ff00cc] font-semibold">{user?.username}</p>
            </div>
            <div className="text-right">
              <div className="flex items-center text-yellow-400">
                <Clock className="h-4 w-4 mr-1" />
                <span className="text-xs">Unverified</span>
              </div>
            </div>
          </div>
        </div>

        {/* Instructions */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-[#39ff14] mb-3 flex items-center">
            <CheckCircle className="h-5 w-5 mr-2" />
            Next Steps
          </h3>
          <div className="space-y-2 text-sm text-gray-300">
            <p>1. Check your email inbox for a verification message</p>
            <p>2. Click the verification link in the email</p>
            <p>3. Return here and refresh the page</p>
            <p className="text-xs text-gray-400 mt-3">
              Don't see the email? Check your spam folder or request a new one below.
            </p>
          </div>
        </div>

        {/* Messages */}
        {message && (
          <div className="bg-green-900/30 border border-green-500 text-green-400 p-3 rounded mb-4 text-sm">
            {message}
          </div>
        )}
        
        {error && (
          <div className="bg-red-900/30 border border-red-500 text-red-400 p-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Resend Button */}
        <button
          onClick={handleResendVerification}
          disabled={loading || cooldownTime > 0}
          className={`w-full py-3 border rounded-lg font-medium transition-all duration-200 flex items-center justify-center ${
            cooldownTime > 0
              ? "border-gray-600 text-gray-500 cursor-not-allowed"
              : loading
              ? "border-[#39ff14] text-[#39ff14] opacity-50 cursor-not-allowed"
              : "border-[#39ff14] text-[#39ff14] hover:bg-[#39ff14] hover:text-black"
          }`}
        >
          {loading ? (
            <>
              <RefreshCw className="animate-spin h-4 w-4 mr-2" />
              Sending...
            </>
          ) : cooldownTime > 0 ? (
            <>
              <Clock className="h-4 w-4 mr-2" />
              Resend in {formatTime(cooldownTime)}
            </>
          ) : (
            <>
              <Mail className="h-4 w-4 mr-2" />
              Resend Verification Email
            </>
          )}
        </button>

        {/* Logout Option */}
        <div className="mt-6 pt-4 border-t border-gray-700">
          <p className="text-center text-sm text-gray-400 mb-3">
            Need to use a different account?
          </p>
          <button
            onClick={logout}
            className="w-full py-2 border border-red-500 text-red-500 rounded hover:bg-red-500 hover:text-white transition-colors duration-200 text-sm"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyAccount; 