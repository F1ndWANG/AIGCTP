import { request } from "../api-client";

export interface LlmHealthResponse {
  status: string;
  base_url?: string;
  model?: string;
  error?: string;
}

export const ops = {
  llmHealth: () => request<LlmHealthResponse>("/health/llm"),
};
