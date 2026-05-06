"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import ThemeToggle from "@/components/UI/ThemeToggle";
import NotificationBell from "@/components/UI/NotificationBell";
import { chatHref, withSession } from "@/lib/session";

export default function NavBar() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  if (loading || !user) return null;

  const links = [
    { href: chatHref(), label: "AI 对话", match: "/chat" },
    { href: "/plans", label: "行程" },
    { href: "/products", label: "商品" },
    { href: "/restaurants", label: "餐厅" },
    { href: "/diet", label: "饮食健康" },
    { href: "/cart", label: "购物车" },
  ];

  return (
    <nav role="navigation" aria-label="主导航" className="bg-white dark:bg-slate-800 border-b dark:border-slate-700 sticky top-0 z-40">
      <div className="max-w-4xl mx-auto px-4">
        {/* Mobile header row */}
        <div className="sm:hidden flex items-center justify-between py-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">导航</span>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <NotificationBell />
            <a href="/settings" className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.066z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </a>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700"
              aria-label="切换菜单"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {menuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Links: desktop horizontal, mobile dropdown */}
        <div
          className={`${menuOpen ? "block" : "hidden"} sm:flex sm:items-center sm:gap-1 pb-2 sm:pb-0`}
        >
          {links.map((link) => (
            <a
              key={link.href}
              href={link.match === "/chat" ? link.href : withSession(link.href)}
              onClick={() => setMenuOpen(false)}
              className={`block px-4 py-2 text-sm font-medium border-b-2 transition ${
                pathname.startsWith(link.match || link.href)
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              {link.label}
            </a>
          ))}
          <div className="sm:ml-auto flex items-center gap-3 mt-2 sm:mt-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-gray-100 dark:border-slate-700">
            <ThemeToggle />
            <NotificationBell />
            <a
              href="/profile"
              onClick={() => setMenuOpen(false)}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 truncate max-w-[120px]"
              title="个人资料"
            >
              {user.display_name || user.username}
            </a>
            <a
              href="/settings"
              onClick={() => setMenuOpen(false)}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition"
              title="设置"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.066z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </a>
            <a
              href="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition"
              title="数据概览"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </nav>
  );
}
