import { request } from "../api-client";
import type { AuthResponse, User } from "../types";

export const auth = {
  login: (username: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  register: (username: string, password: string, display_name?: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, display_name }),
    }),
  logout: () => request<{ message: string }>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
};
