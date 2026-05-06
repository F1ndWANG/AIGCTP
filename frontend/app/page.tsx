"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import PersonalDashboard from "@/components/Home/PersonalDashboard";
import { auth, setToken } from "@/lib/api";

export default function HomePage() {
  const { user, loading: authLoading, refreshUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  // Logged in — show personalized dashboard
  if (user) {
    return <PersonalDashboard />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (!isLogin) {
        await auth.register(username, password, displayName);
        setPassword("");
        setDisplayName("");
        setIsLogin(true);
        setSubmitting(false);
        toast("注册成功，请登录", "success");
        return;
      }

      const result = await auth.login(username, password);
      setToken(result.access_token);
      await refreshUser?.();
      toast("登录成功", "success");
      router.replace("/");
    } catch (err: any) {
      setError(err.message || "操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  // Not logged in — show login form
  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            AI 生活推荐
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            智能旅行 · 饮食健康 · AI 购物
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="输入用户名"
              required
            />
          </div>

          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                显示名称
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="你的昵称"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="输入密码"
              required
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50"
          >
            {submitting ? "处理中..." : isLogin ? "登录" : "注册"}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-gray-500 dark:text-gray-400">
          {isLogin ? "还没有账号？" : "已有账号？"}
          <button
            onClick={() => { setIsLogin(!isLogin); setError(""); }}
            className="ml-1 text-blue-600 hover:underline"
          >
            {isLogin ? "去注册" : "去登录"}
          </button>
        </p>
      </div>
    </main>
  );
}
