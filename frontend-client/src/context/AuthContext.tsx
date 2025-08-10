import React, { createContext, useContext, useEffect, useState } from "react";
import {authAPI} from "../api" // Adjust path if needed
import { AxiosError } from "axios";

interface User {
    username: string;
    name: string;
    github: string;
    discord_username: string;
    about: string;
    admin: boolean;
    is_verified: boolean;
}

// Type definition for AuthContext
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credentials: { username: string; password: string }) => Promise<void>;
  register: (data: { username: string; email: string; password: string }) => Promise<AxiosError | void>;
  logout: () => void;
}

// Default context value
const AuthContext = createContext<AuthContextType | null>(null);

// Provider component
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = !!user;

  const fetchUser = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
            setUser(null);
            return;
        }
      const res = await authAPI.verify(token);
      setUser(res);
      } catch (err: AxiosError | unknown) {
          if (err && (err as AxiosError).response) {
              setUser(null);
              localStorage.removeItem("token");
          }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const login = async (credentials: { username: string; password: string }) => {
    const res = await authAPI.login(credentials.username, credentials.password);
    localStorage.setItem("token", res.access_token);
    await fetchUser();
    };
    
    const register = async (data: { username: string; email: string; password: string }) => {
        const res = await authAPI.register(data.username, data.email, data.password);
        localStorage.setItem("token", res.access_token);
        await fetchUser();
    };


  const logout = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;
      await authAPI.logout(token);
      } catch (e) {
      console.log(e);
      console.warn("Logout failed (probably already expired token).");
    }
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook for using auth
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
