"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getToken, setToken, user as userApi } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => void;
  refreshUser?: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      router.push("/");
      return;
    }
    userApi
      .me()
      .then((u) => {
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        setToken(null);
        setLoading(false);
        router.push("/");
      });
  }, []); // 仅在挂载时请求用户信息，避免页面切换时反复获取导致竞态

  const logout = () => {
    setToken(null);
    setUser(null);
    window.location.href = "/";
  };

  const refreshUser = async () => {
    try {
      const u = await userApi.me();
      setUser(u);
    } catch { /* ignore */ }
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}
