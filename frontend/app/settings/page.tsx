"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { user as userApi } from "@/lib/api";

export default function SettingsPage() {
  const { user, loading, refreshUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [changed, setChanged] = useState(false);

  // Password state
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (user) setDisplayName(user.display_name || "");
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  const handleSave = async () => {
    if (!displayName.trim()) {
      toast("显示名称不能为空", "error");
      return;
    }
    setSaving(true);
    try {
      await userApi.updateProfile({ display_name: displayName.trim() });
      toast("保存成功", "success");
      setChanged(false);
      refreshUser?.();
    } catch {
      toast("保存失败，请重试", "error");
    }
    setSaving(false);
  };

  const handlePasswordChange = async () => {
    if (!oldPassword) { toast("请输入原密码", "error"); return; }
    if (newPassword.length < 6) { toast("新密码至少需要6个字符", "error"); return; }
    if (newPassword !== confirmPassword) { toast("两次输入的密码不一致", "error"); return; }
    setChangingPassword(true);
    try {
      const resp = await userApi.changePassword(oldPassword, newPassword);
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "修改失败" }));
        throw new Error(err.detail || "修改失败");
      }
      toast("密码修改成功", "success");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "修改失败", "error");
    }
    setChangingPassword(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      <div className="max-w-lg mx-auto px-4 py-8">
        <h1 className="text-xl font-bold mb-6">设置</h1>

        {/* Profile Section */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-5 space-y-5">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">个人资料</h2>

          {/* Username (read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">用户名</label>
            <input
              type="text"
              value={user.username}
              disabled
              className="w-full px-3 py-2 text-sm border dark:border-slate-700 rounded-lg bg-gray-50 dark:bg-slate-900 text-gray-400 dark:text-gray-500"
            />
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">显示名称</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => { setDisplayName(e.target.value); setChanged(true); }}
              placeholder="输入显示名称"
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving || !changed}
            className="w-full py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>

        {/* Password Section */}
        <div className="mt-6 bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-5 space-y-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">修改密码</h2>
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">原密码</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="输入原密码"
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">新密码</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="至少6个字符"
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">确认新密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="再次输入新密码"
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
          </div>
          <button
            onClick={handlePasswordChange}
            disabled={changingPassword}
            className="w-full py-2 text-sm font-medium border border-gray-300 dark:border-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 transition"
          >
            {changingPassword ? "修改中..." : "修改密码"}
          </button>
        </div>

        {/* Account info */}
        <div className="mt-6 bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-5">
          <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">账号信息</h2>
          <div className="text-sm text-gray-400 dark:text-gray-500 space-y-1">
            <p>注册时间: {new Date(user.created_at).toLocaleDateString("zh-CN")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
