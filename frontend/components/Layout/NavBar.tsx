"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  MessageCircle,
  Map,
  ShoppingBag,
  UtensilsCrossed,
  Apple,
  ShoppingCart,
  Settings,
  LayoutDashboard,
  Menu,
  User,
  LogOut,
} from "lucide-react";

import { useAuth } from "@/components/Layout/AuthProvider";
import ThemeToggle from "@/components/UI/ThemeToggle";
import NotificationBell from "@/components/UI/NotificationBell";
import { chatHref, withSession } from "@/lib/session";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/UI/avatar";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/UI/sheet";

const navLinks = [
  { href: "/chat", label: "AI 对话", icon: MessageCircle },
  { href: "/plans", label: "行程", icon: Map },
  { href: "/products", label: "商品", icon: ShoppingBag },
  { href: "/restaurants", label: "餐厅", icon: UtensilsCrossed },
  { href: "/diet", label: "饮食健康", icon: Apple },
  { href: "/cart", label: "购物车", icon: ShoppingCart },
];

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (!userMenuRef.current?.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setUserMenuOpen(false);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  if (loading || !user) return null;

  const isActive = (href: string) => {
    if (href === "/chat") return pathname.startsWith("/chat");
    return pathname.startsWith(href);
  };

  const userInitial = (user.display_name || user.username || "U")[0].toUpperCase();
  const navigateTo = (href: string) => {
    setUserMenuOpen(false);
    router.push(href);
  };

  return (
    <nav
      role="navigation"
      aria-label="主导航"
      className="sticky top-0 z-40 border-b border-border/50 bg-background/80 backdrop-blur-lg supports-[backdrop-filter]:bg-background/60"
    >
      <div className="max-w-4xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Left: Logo + Desktop nav */}
          <div className="flex items-center gap-1">
            <a
              href="/"
              className="text-sm font-bold bg-gradient-to-r from-fuchsia-500 to-pink-500 bg-clip-text text-transparent mr-4 hidden sm:block"
            >
              AI 生活推荐
            </a>
            <div className="hidden sm:flex items-center gap-0.5">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href === "/chat" ? link.href : withSession(link.href)}
                  className={`relative flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                    isActive(link.href)
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  <link.icon className="h-4 w-4" />
                  <span>{link.label}</span>
                  {isActive(link.href) && (
                    <motion.div
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-full bg-primary/10 -z-10"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                    />
                  )}
                </a>
              ))}
            </div>
          </div>

          {/* Right: ThemeToggle + Notif + User menu */}
          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            <NotificationBell />

            {/* Desktop user menu */}
            <div className="relative hidden sm:block" ref={userMenuRef}>
              <button
                type="button"
                aria-label="打开用户菜单"
                aria-expanded={userMenuOpen}
                onClick={() => setUserMenuOpen((open) => !open)}
                className="inline-flex h-9 max-w-[180px] items-center gap-2 rounded-lg border border-border bg-background px-2.5 text-left shadow-sm transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <Avatar className="h-6 w-6 shrink-0 bg-background">
                  <AvatarImage src="/icon.svg" alt="AI 生活推荐" />
                  <AvatarFallback className="bg-gradient-to-br from-fuchsia-400 to-pink-500 text-xs font-medium text-white">
                    {userInitial}
                  </AvatarFallback>
                </Avatar>
                <span className="min-w-0 hidden lg:block">
                  <span className="block truncate text-xs font-medium leading-4 text-foreground">
                    {user.display_name || user.username}
                  </span>
                  <span className="block truncate text-[10px] leading-3 text-muted-foreground">
                    ID #{user.id}
                  </span>
                </span>
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 top-10 z-50 w-48 rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-lg">
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                    <div className="truncate">{user.display_name || user.username}</div>
                  </div>
                  <div className="-mx-1 my-1 h-px bg-border" />
                  <button
                    type="button"
                    onClick={() => navigateTo("/settings")}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    设置
                  </button>
                  <button
                    type="button"
                    onClick={() => navigateTo("/dashboard")}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                  >
                    <LayoutDashboard className="mr-2 h-4 w-4" />
                    数据概览
                  </button>
                  <div className="-mx-1 my-1 h-px bg-border" />
                  <button
                    type="button"
                    onClick={() => navigateTo("/profile")}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                  >
                    <User className="mr-2 h-4 w-4" />
                    个人资料
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      logout();
                    }}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-destructive hover:bg-destructive/10"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    退出登录
                  </button>
                </div>
              )}
            </div>

            {/* Mobile sheet trigger */}
            <div className="sm:hidden">
              <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
                <SheetTrigger className="inline-flex items-center justify-center rounded-lg h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer outline-none">
                  <Menu className="h-5 w-5" />
                </SheetTrigger>
                <SheetContent side="left" className="w-64 p-0">
                  <SheetHeader className="px-4 py-4 border-b">
                    <SheetTitle className="text-left text-base bg-gradient-to-r from-fuchsia-500 to-pink-500 bg-clip-text text-transparent">
                      AI 生活推荐
                    </SheetTitle>
                  </SheetHeader>
                  <div className="flex flex-col p-2">
                    {navLinks.map((link) => (
                      <a
                        key={link.href}
                        href={link.href === "/chat" ? link.href : withSession(link.href)}
                        onClick={() => setSheetOpen(false)}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                          isActive(link.href)
                            ? "bg-primary/10 text-primary"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted"
                        }`}
                      >
                        <link.icon className="h-4 w-4" />
                        {link.label}
                      </a>
                    ))}
                    <hr className="my-2 border-border" />
                    <a
                      href="/settings"
                      onClick={() => setSheetOpen(false)}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted"
                    >
                      <Settings className="h-4 w-4" />
                      设置
                    </a>
                    <a
                      href="/dashboard"
                      onClick={() => setSheetOpen(false)}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted"
                    >
                      <LayoutDashboard className="h-4 w-4" />
                      数据概览
                    </a>
                    <div className="mt-2 px-3 py-2 flex items-center gap-3 text-sm text-muted-foreground border-t border-border pt-3">
                      <Avatar className="h-6 w-6 bg-background">
                        <AvatarImage src="/icon.svg" alt="AI 生活推荐" />
                        <AvatarFallback className="bg-gradient-to-br from-fuchsia-400 to-pink-500 text-xs font-medium text-white">
                          {userInitial}
                        </AvatarFallback>
                      </Avatar>
                      <span className="truncate">{user.display_name || user.username}</span>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
