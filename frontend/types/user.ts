// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

export interface User {
  uid: number;
  username: string;
  email: string;
  password: string;
  createdAt: string;
  updatedAt: string;
}

export interface UserResponse extends Omit<User, 'password'> {
  // Password is excluded when returned to the frontend
}

export interface Token {
    access_token: string
    token_type: string
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
  password?: string;
}

// LLM Settings
export interface LLMSettings {
  api_key_set: boolean;
  api_key_masked: string | null;
  base_url: string | null;
  model_name: string | null;
  // Advanced / context management settings (always returned with defaults)
  context_compaction_enabled: boolean;
  context_keep_recent: number;
  context_min_messages: number;
  default_thinking_level: string;
  agent_max_turns: number;
  model_fallbacks: string | null;
}

export interface LLMSettingsUpdate {
  api_key?: string;
  base_url?: string;
  model_name?: string;
  context_compaction_enabled?: boolean;
  context_keep_recent?: number;
  context_min_messages?: number;
  default_thinking_level?: string;
  agent_max_turns?: number;
  model_fallbacks?: string;
}

export interface LLMTestRequest {
  api_key: string;
  base_url?: string;
  model_name?: string;
}

export interface LLMTestResponse {
  success: boolean;
  message: string;
  model_used?: string;
  latency_ms?: number;
}
