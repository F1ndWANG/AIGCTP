"use client";

import {
  useEffect,
  useState,
  type ComponentProps,
  type FormEvent,
  type MouseEvent,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  Coffee,
  CheckCircle2,
  Heart,
  Lock,
  LogIn,
  Map,
  MessageCircle,
  Sparkles,
  Star,
  Store,
  User,
  UserPlus,
} from "lucide-react";

import { useAuth } from "@/components/Layout/AuthProvider";
import PersonalDashboard from "@/components/Home/PersonalDashboard";
import { Button } from "@/components/UI/button";
import { Input } from "@/components/UI/input";
import { Label } from "@/components/UI/label";
import { useToast } from "@/components/UI/Toast";
import { auth } from "@/lib/api";

const companionBadges = [
  { label: "行程灵感", detail: "我会把景点、天气和路线整理成行程卡。", icon: Map, className: "left-8 top-16 bg-teal-50 text-teal-700 border-teal-100" },
  { label: "饮食记录", detail: "我会记住饮食日志和健康目标。", icon: Coffee, className: "right-8 top-24 bg-amber-50 text-amber-700 border-amber-100" },
  { label: "好物清单", detail: "我会把旅行好物和日常商品同步到商品页。", icon: Store, className: "bottom-36 left-10 bg-sky-50 text-sky-700 border-sky-100" },
  { label: "AI 对话", detail: "我会把对话里的计划沉淀到对应功能页。", icon: MessageCircle, className: "bottom-40 right-12 bg-rose-50 text-rose-700 border-rose-100" },
];

export default function HomePage() {
  const { user, loading: authLoading, refreshUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const passwordRules = [
    { label: "至少 8 位", passed: password.length >= 8 },
    { label: "包含大写字母", passed: /[A-Z]/.test(password) },
    { label: "包含小写字母", passed: /[a-z]/.test(password) },
    { label: "包含数字", passed: /\d/.test(password) },
  ];

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      if (!isLogin) {
        await auth.register(username, password, displayName || undefined);
        await refreshUser?.();
        toast("注册成功", "success");
        router.replace("/");
        return;
      }

      await auth.login(username, password);
      await refreshUser?.();
      toast("登录成功", "success");
      router.replace("/");
    } catch (err: any) {
      setError(err?.message || "操作失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  if (!mounted || authLoading) {
    return <AuthLoadingScreen />;
  }

  if (user) {
    return <PersonalDashboard />;
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#f6f3ee] text-slate-950">
      <div className="absolute inset-0 opacity-[0.42] [background-image:linear-gradient(#d8d0c4_1px,transparent_1px),linear-gradient(90deg,#d8d0c4_1px,transparent_1px)] [background-size:28px_28px]" />
      <div className="relative grid min-h-screen items-center justify-center gap-10 px-5 py-8 sm:px-8 lg:grid-cols-[420px_minmax(420px,560px)]">
        <section className="w-full max-w-[420px]">
          <div className="mb-7 flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-lg bg-slate-950 text-white">
              <Sparkles className="size-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">AI 生活推荐系统</p>
              <h1 className="text-2xl font-semibold tracking-normal text-slate-950">
                请先完成身份验证
              </h1>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
              <div className="mb-6">
                <p className="text-sm font-medium text-slate-500">
                  {isLogin ? "欢迎回来" : "创建账号"}
                </p>
                <h2 className="mt-2 text-2xl font-semibold tracking-normal text-slate-950">
                  {isLogin ? "登录" : "注册"}
                </h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <InputWithIcon
                  id="username"
                  label="用户名"
                  icon={<User className="size-4" />}
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="输入用户名"
                  autoComplete="username"
                  required
                />

                {!isLogin && (
                  <InputWithIcon
                    id="displayName"
                    label="显示名称"
                    icon={<UserPlus className="size-4" />}
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="输入显示名称"
                    autoComplete="name"
                  />
                )}

                <InputWithIcon
                  id="password"
                  label="密码"
                  icon={<Lock className="size-4" />}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="至少 8 位"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  required
                  minLength={8}
                />

                {!isLogin && <PasswordRequirementList rules={passwordRules} />}

                {error && (
                  <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {error}
                  </p>
                )}

                <Button
                  type="submit"
                  disabled={submitting}
                  className="h-11 w-full gap-2 rounded-lg bg-slate-950 text-base font-medium text-white hover:bg-slate-800"
                >
                  <LogIn className="size-4" />
                  {submitting ? "处理中..." : isLogin ? "登录" : "注册"}
                </Button>
              </form>

              <div className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-500">
                <span>{isLogin ? "还没有账号？" : "已有账号？"}</span>
                <Button
                  type="button"
                  variant="link"
                  onClick={() => {
                    setIsLogin(!isLogin);
                    setError("");
                  }}
                  className="h-auto p-0 text-sm font-medium text-teal-700 hover:text-teal-800"
                >
                  {isLogin ? "去注册" : "去登录"}
                </Button>
              </div>
          </div>
        </section>

        <CompanionScene />
      </div>
    </main>
  );
}

function PasswordRequirementList({
  rules,
}: {
  rules: Array<{ label: string; passed: boolean }>;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5">
      <p className="mb-2 text-xs font-medium text-slate-500">密码要求</p>
      <div className="grid gap-1.5 sm:grid-cols-2">
        {rules.map((rule) => (
          <div
            key={rule.label}
            className={rule.passed ? "flex items-center gap-1.5 text-xs text-teal-700" : "flex items-center gap-1.5 text-xs text-slate-500"}
          >
            <CheckCircle2
              className={rule.passed ? "size-3.5 text-teal-600" : "size-3.5 text-slate-300"}
            />
            <span>{rule.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompanionScene() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [activeBadge, setActiveBadge] = useState(companionBadges[0]);
  const [tapCount, setTapCount] = useState(0);

  const handleMove = (event: MouseEvent<HTMLElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
    setTilt({ x, y });
  };

  return (
    <aside
      className="group relative hidden h-[560px] w-full max-w-[560px] overflow-hidden rounded-lg border border-slate-200 bg-white/72 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur lg:block"
      onMouseMove={handleMove}
      onMouseLeave={() => {
        setTilt({ x: 0, y: 0 });
      }}
      aria-label="AI 生活推荐系统动态插画"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,184,166,0.18),transparent_28%),radial-gradient(circle_at_82%_22%,rgba(251,146,60,0.16),transparent_30%),radial-gradient(circle_at_50%_82%,rgba(217,70,239,0.10),transparent_34%),linear-gradient(135deg,rgba(255,255,255,0.9),rgba(248,250,252,0.68))]" />
      <div className="absolute inset-x-10 top-10 flex items-center justify-between text-sm text-slate-500">
        <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-1.5">
          <Heart className="size-4 text-rose-500" />
          可爱生活助手
        </span>
        <span className="rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 font-medium text-teal-700">
          {tapCount > 0 ? `互动 ${tapCount}` : "待命中"}
        </span>
      </div>

      <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-teal-200/90 animate-[spin_18s_linear_infinite]" />
      <div className="absolute left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-amber-200/80 animate-[spin_26s_linear_infinite_reverse]" />
      <div className="absolute left-[22%] top-[42%] size-2 rounded-full bg-teal-300 animate-[ping_2.8s_ease-in-out_infinite]" />
      <div className="absolute right-[22%] top-[54%] size-2 rounded-full bg-fuchsia-300 animate-[ping_3.2s_ease-in-out_infinite]" />
      <div className="absolute left-[48%] bottom-[24%] size-2 rounded-full bg-amber-300 animate-[ping_3.6s_ease-in-out_infinite]" />

      {companionBadges.map(({ label, icon: Icon, className }) => (
        <button
          key={label}
          type="button"
          onMouseEnter={() => setActiveBadge(companionBadges.find((item) => item.label === label) || companionBadges[0])}
          onFocus={() => setActiveBadge(companionBadges.find((item) => item.label === label) || companionBadges[0])}
          onClick={() => {
            setActiveBadge(companionBadges.find((item) => item.label === label) || companionBadges[0]);
            setTapCount((count) => count + 1);
          }}
          className={`absolute z-20 flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${className}`}
        >
          <Icon className="size-4" />
          {label}
        </button>
      ))}

      <div
        className="absolute left-1/2 top-[48%] z-10 h-64 w-64 -translate-x-1/2 -translate-y-1/2 transition-transform duration-150"
        style={{
          transform: `translate(-50%, -50%) rotateX(${-tilt.y * 7}deg) rotateY(${tilt.x * 9}deg)`,
        }}
      >
        <div className="absolute inset-x-8 bottom-0 h-8 rounded-full bg-slate-950/10 blur-md" />
        <div className="relative mx-auto h-56 w-52 animate-[companion-bob_3.6s_ease-in-out_infinite] rounded-[32px] border border-slate-200 bg-[#fffaf0] shadow-[0_20px_50px_rgba(15,23,42,0.16)]">
          <div className="absolute -top-8 left-1/2 h-12 w-12 -translate-x-1/2 rounded-full border border-slate-200 bg-white shadow-sm animate-[companion-pop_2.8s_ease-in-out_infinite]">
            <Star className="absolute left-1/2 top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 text-amber-500" />
          </div>
          <div className="absolute -top-12 left-1/2 h-8 w-px -translate-x-1/2 bg-slate-300" />
          <div className="absolute left-8 top-12 h-20 w-36 rounded-[28px] bg-slate-950">
            <div
              className="absolute left-8 top-7 size-3 rounded-full bg-teal-200 transition-transform duration-150"
              style={{ transform: `translate(${tilt.x * 5}px, ${tilt.y * 4}px)` }}
            />
            <div
              className="absolute right-8 top-7 size-3 rounded-full bg-teal-200 transition-transform duration-150"
              style={{ transform: `translate(${tilt.x * 5}px, ${tilt.y * 4}px)` }}
            />
            <div
              className="absolute bottom-5 left-1/2 h-2 -translate-x-1/2 rounded-full bg-teal-200/80 transition-all duration-300"
              style={{ width: activeBadge.label === "AI 对话" ? 52 : 40 }}
            />
          </div>
          <div className="absolute left-7 top-36 h-3 w-16 rounded-full bg-teal-200" />
          <div className="absolute left-7 top-44 h-3 w-24 rounded-full bg-amber-200" />
          <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
            <span className="size-4 rounded-full bg-teal-500" />
            <span className="size-4 rounded-full bg-amber-400" />
            <span className="size-4 rounded-full bg-sky-500" />
          </div>
        </div>
      </div>

      <div className="absolute inset-x-8 bottom-8 z-20 rounded-lg border border-slate-200 bg-white/86 p-4 shadow-sm">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-semibold text-slate-950">{activeBadge.label}</p>
          <Sparkles className="size-4 text-teal-600" />
        </div>
        <p className="text-sm leading-6 text-slate-600">
          {activeBadge.detail}
        </p>
      </div>

      <style jsx>{`
        @keyframes companion-bob {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        @keyframes companion-pop {
          0%, 100% { transform: translateX(-50%) scale(1); }
          50% { transform: translateX(-50%) scale(1.08); }
        }
      `}</style>
    </aside>
  );
}

function InputWithIcon({
  label,
  icon,
  className,
  id,
  ...props
}: ComponentProps<typeof Input> & {
  label: string;
  icon: ReactNode;
  id: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 flex size-4 -translate-y-1/2 items-center justify-center text-slate-400">
          {icon}
        </span>
        <Input
          id={id}
          className={["pl-10", className].filter(Boolean).join(" ")}
          {...props}
        />
      </div>
    </div>
  );
}

function AuthLoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f6f3ee]">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-slate-950" />
    </main>
  );
}
