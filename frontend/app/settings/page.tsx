"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Save, Lock, User, Info } from "lucide-react";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { user as userApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/UI/card";
import { Input } from "@/components/UI/input";
import { Label } from "@/components/UI/label";
import { Button } from "@/components/UI/button";
import { motion } from "motion/react";

export default function SettingsPage() {
  const { user, loading, refreshUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [changed, setChanged] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (user) setDisplayName(user.display_name || "");
  }, [user]);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen flex items-center justify-center bg-background"
      >
        <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
      </motion.div>
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
      await userApi.changePassword(oldPassword, newPassword);
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
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background"
    >
      <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
        <h1 className="text-xl font-bold text-foreground">设置</h1>

        {/* Profile Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-4 w-4 text-fuchsia-600 dark:text-fuchsia-400" />
              个人资料
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                type="text"
                value={user.username}
                disabled
                className="bg-muted text-muted-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="displayName">显示名称</Label>
              <Input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => { setDisplayName(e.target.value); setChanged(true); }}
                placeholder="输入显示名称"
              />
            </div>
            <Button
              onClick={handleSave}
              disabled={saving || !changed}
              className="w-full"
            >
              <Save className="mr-2 h-4 w-4" />
              {saving ? "保存中..." : "保存"}
            </Button>
          </CardContent>
        </Card>

        {/* Password Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-fuchsia-600 dark:text-fuchsia-400" />
              修改密码
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="oldPassword">原密码</Label>
              <Input
                id="oldPassword"
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                placeholder="输入原密码"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="newPassword">新密码</Label>
              <Input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="至少6个字符"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认新密码</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="再次输入新密码"
              />
            </div>
            <Button
              onClick={handlePasswordChange}
              disabled={changingPassword}
              variant="outline"
              className="w-full"
            >
              <Lock className="mr-2 h-4 w-4" />
              {changingPassword ? "修改中..." : "修改密码"}
            </Button>
          </CardContent>
        </Card>

        {/* Account Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-4 w-4 text-muted-foreground" />
              账号信息
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              注册时间: {new Date(user.created_at).toLocaleDateString("zh-CN")}
            </p>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
