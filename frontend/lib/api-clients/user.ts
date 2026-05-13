import { request } from "../api-client";
import type { User } from "../types";

export const user = {
  me: () => request<User>("/users/me"),
  updateProfile: (data: { display_name?: string; avatar_url?: string }) =>
    request<User>("/users/me", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  updatePreferences: (preferences: Record<string, unknown>) =>
    request<User>("/users/me/preferences", {
      method: "PUT",
      body: JSON.stringify({ preferences }),
    }),
  changePassword: (old_password: string, new_password: string) =>
    request<{ status: string }>("/users/me/password", {
      method: "PUT",
      body: JSON.stringify({ old_password, new_password }),
    }),
};
