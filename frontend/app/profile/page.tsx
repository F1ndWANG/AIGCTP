"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { user as userApi } from "@/lib/api";
import type { User } from "@/lib/types";

export default function ProfilePage() {
  const { user: authUser, loading: authLoading } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!authUser) { router.push("/"); return; }
    userApi.me().then(setProfile).catch(() => {}).finally(() => setLoading(false));
  }, [authUser, authLoading, router]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.back()} className="text-sm text-gray-400 hover:text-gray-600">
            ← 返回
          </button>
          <h1 className="text-lg font-bold text-gray-900">个人资料</h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Avatar & Name */}
        <div className="bg-white rounded-xl border p-6 flex items-center gap-5 mb-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold shrink-0">
            {(profile.display_name || profile.username)[0].toUpperCase()}
          </div>
          <div>
            <h2 className="text-xl font-bold">{profile.display_name || profile.username}</h2>
            <p className="text-sm text-gray-400">@{profile.username}</p>
          </div>
        </div>

        {/* Details */}
        <div className="bg-white rounded-xl border divide-y">
          <div className="px-5 py-4 flex justify-between">
            <span className="text-sm text-gray-500">用户名</span>
            <span className="text-sm font-medium">{profile.username}</span>
          </div>
          <div className="px-5 py-4 flex justify-between">
            <span className="text-sm text-gray-500">显示名称</span>
            <span className="text-sm font-medium">{profile.display_name || "未设置"}</span>
          </div>
          <div className="px-5 py-4 flex justify-between">
            <span className="text-sm text-gray-500">注册时间</span>
            <span className="text-sm font-medium">
              {new Date(profile.created_at).toLocaleDateString("zh-CN", {
                year: "numeric", month: "long", day: "numeric",
              })}
            </span>
          </div>
          <div className="px-5 py-4 flex justify-between">
            <span className="text-sm text-gray-500">用户 ID</span>
            <span className="text-sm font-mono text-gray-400">#{profile.id}</span>
          </div>
        </div>

        {/* Quick Links */}
        <div className="mt-6 grid grid-cols-2 gap-3">
          <a href="/settings" className="bg-white rounded-xl border p-4 hover:bg-gray-50 transition text-center">
            <p className="text-sm font-medium text-gray-700">⚙️ 账号设置</p>
            <p className="text-xs text-gray-400 mt-1">修改名称和密码</p>
          </a>
          <a href="/plans" className="bg-white rounded-xl border p-4 hover:bg-gray-50 transition text-center">
            <p className="text-sm font-medium text-gray-700">🗺️ 我的行程</p>
            <p className="text-xs text-gray-400 mt-1">查看旅行计划</p>
          </a>
        </div>
      </div>
    </div>
  );
}
