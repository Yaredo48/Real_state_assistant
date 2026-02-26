'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import Cookies from 'js-cookie';
import { useRouter, usePathname } from 'next/navigation';
import { authApi } from '@/lib/api';
import { User, LoginCredentials, RegisterData } from '@/types';

const TOKEN_KEY = process.env.NEXT_PUBLIC_TOKEN_KEY || 'deallens_access_token';
const REFRESH_TOKEN_KEY = process.env.NEXT_PUBLIC_REFRESH_TOKEN_KEY || 'deallens_refresh_token';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const refreshUser = useCallback(async () => {
    try {
      const token = Cookies.get(TOKEN_KEY);
      if (!token) {
        setUser(null);
        return;
      }
      const userData = await authApi.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user:', error);
      Cookies.remove(TOKEN_KEY);
      Cookies.remove(REFRESH_TOKEN_KEY);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      await refreshUser();
      setIsLoading(false);
    };
    initAuth();
  }, [refreshUser]);

  // Handle protected routes
  useEffect(() => {
    if (!isLoading) {
      const token = Cookies.get(TOKEN_KEY);
      const isAuthPage = pathname?.startsWith('/login') || pathname?.startsWith('/register');
      
      if (!token && !isAuthPage && pathname !== '/') {
        router.push('/login');
      } else if (token && isAuthPage) {
        router.push('/dashboard');
      }
    }
  }, [isLoading, pathname, router]);

  const login = async (credentials: LoginCredentials) => {
    const response = await authApi.login(credentials.email, credentials.password);
    Cookies.set(TOKEN_KEY, response.access_token);
    Cookies.set(REFRESH_TOKEN_KEY, response.refresh_token);
    await refreshUser();
    router.push('/dashboard');
  };

  const register = async (data: RegisterData) => {
    await authApi.register(data);
    // Auto-login after registration
    await login({ email: data.email, password: data.password });
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      Cookies.remove(TOKEN_KEY);
      Cookies.remove(REFRESH_TOKEN_KEY);
      setUser(null);
      router.push('/login');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Protected route wrapper
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
