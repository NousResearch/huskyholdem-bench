import React from "react";
import { useAuth } from "../context/AuthContext";
import { Navigate, useLocation } from "react-router-dom";

interface VerifiedRouteProps {
  children: React.ReactNode;
}

const VerifiedRoute: React.FC<VerifiedRouteProps> = ({ children }) => {
  const { user, isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-white">
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!user?.is_verified) {
    return <Navigate to="/verify-account" replace state={{ from: location }} />;
  }

  return <>{children}</>;
};

export default VerifiedRoute; 