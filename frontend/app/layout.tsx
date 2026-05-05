import type { Metadata, Viewport } from "next";
import "./globals.css";
import AuthProvider from "@/components/Layout/AuthProvider";
import NavBar from "@/components/Layout/NavBar";
import { ToastProvider } from "@/components/UI/Toast";
import { ErrorBoundary } from "@/components/UI/ErrorBoundary";

export const metadata: Metadata = {
  title: "AI 生活推荐系统",
  description: "智能旅行规划 · 饮食健康 · AI 购物助手",
  icons: {
    icon: "/icon.svg",
    apple: "/icon-192x192.png",
  },
  other: {
    "manifest": "/manifest.json",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <ToastProvider>
          <AuthProvider>
            <NavBar />
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
