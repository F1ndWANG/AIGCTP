export const ACTIVE_SESSION_KEY = "active_session_id";

export function getActiveSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_SESSION_KEY);
}

export function setActiveSessionId(sessionId: string | null | undefined) {
  if (typeof window === "undefined") return;
  if (sessionId) localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
  else localStorage.removeItem(ACTIVE_SESSION_KEY);
}

export function chatHref(sessionId?: string | null): string {
  const sid = sessionId || getActiveSessionId();
  return sid ? `/chat?session=${encodeURIComponent(sid)}` : "/chat";
}

export function withSession(path: string, sessionId?: string | null): string {
  const sid = sessionId || getActiveSessionId();
  if (!sid) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}session=${encodeURIComponent(sid)}`;
}
