import type { Metadata, Viewport } from "next";
import "./globals.css";
import AuthProvider from "@/components/Layout/AuthProvider";
import NavBar from "@/components/Layout/NavBar";
import { ToastProvider } from "@/components/UI/Toast";
import { NotificationProvider } from "@/components/UI/NotificationCenter";
import DietReminder from "@/components/Home/DietReminder";
import { ErrorBoundary } from "@/components/UI/ErrorBoundary";
import OfflineIndicator from "@/components/UI/OfflineIndicator";
import PageTransition from "@/components/Layout/PageTransition";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

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
    <html lang="zh-CN" className={cn("font-sans", inter.variable)}>
      <body>
        <ToastProvider>
          <AuthProvider>
            <NotificationProvider>
              <OfflineIndicator />
              <NavBar />
              <DietReminder />
              <ErrorBoundary>
                <PageTransition>
                  {children}
                </PageTransition>
              </ErrorBoundary>
            </NotificationProvider>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
