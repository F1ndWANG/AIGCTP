"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { motion } from "motion/react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  if (!mounted) {
    return <div className="w-5 h-5" />;
  }

  return (
    <button
      onClick={toggle}
      className="relative text-muted-foreground hover:text-foreground transition p-1.5 rounded-lg hover:bg-muted"
      title={dark ? "切换亮色模式" : "切换暗色模式"}
      aria-label={dark ? "切换亮色模式" : "切换暗色模式"}
    >
      <motion.div
        key={dark ? "moon" : "sun"}
        initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
        animate={{ rotate: 0, opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        {dark ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
      </motion.div>
    </button>
  );
}
