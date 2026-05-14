import { request } from "../api-client";
import type { TravelNote, TravelNoteCreatePayload } from "../types";

type TravelNoteListParams = {
  destination?: string;
  tag?: string;
  mine?: boolean;
  limit?: number;
  offset?: number;
};

export const shares = {
  listNotes: (params?: TravelNoteListParams) => {
    const qs = new URLSearchParams();
    if (params) {
      (Object.entries(params) as [string, string | number | boolean | undefined][]).forEach(
        ([key, value]) => {
          if (value !== undefined && value !== null && value !== "") qs.set(key, String(value));
        }
      );
    }
    return request<TravelNote[]>(`/shares/notes${qs.toString() ? `?${qs.toString()}` : ""}`);
  },
  recommendedNotes: (limit = 12) =>
    request<TravelNote[]>(`/shares/notes/recommended?limit=${limit}`),
  createNote: (data: TravelNoteCreatePayload) =>
    request<TravelNote>("/shares/notes", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateNote: (id: number, data: Partial<TravelNoteCreatePayload>) =>
    request<TravelNote>(`/shares/notes/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  getNote: (id: number) => request<TravelNote>(`/shares/notes/${id}`),
  deleteNote: (id: number) =>
    request<void>(`/shares/notes/${id}`, {
      method: "DELETE",
    }),
  interact: (id: number, interaction_type: "view" | "like" | "save" | "share", active = true) =>
    request<TravelNote>(`/shares/notes/${id}/interactions`, {
      method: "POST",
      body: JSON.stringify({ interaction_type, active }),
    }),
  comment: (id: number, content: string) =>
    request<TravelNote>(`/shares/notes/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
};
