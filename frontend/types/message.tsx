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

export interface OutputFile {
  file_name: string;
  file_url: string;
  file_size: number;
}

export interface ExecutionResult {
  status: string;
  stdout: string;
  stderr: string;
  result: any;
  output_files?: OutputFile[];
}

export interface CodeMessage {
  code: string;
  executionCount: number;
  reasoning?: string;  // LLM's reasoning for generating this code
}

// Tool call information
export interface ToolCallInfo {
  name: string;
  arguments: Record<string, any>;
  call_id?: string;
}

// Tool result information
export interface ToolResultInfo {
  name: string;
  result: string;
  call_id?: string;
}

export interface Message {
  type: 
    | 'user' 
    | 'system' 
    | 'log' 
    | 'script' 
    | 'result' 
    | 'error' 
    | 'iteration' 
    | 'evaluation' 
    | 'advice' 
    | 'code' 
    | 'execution_result' 
    | 'response'
    | 'response_delta'  // Streaming text delta
    | 'skill_loaded' 
    | 'output_files'
    | 'thinking'
    | 'tool_call'       // Tool call started
    | 'tool_result';    // Tool execution completed
  content: any;
  timestamp: number;
  iteration?: number;
  // For code execution
  executionResult?: ExecutionResult;
  codeData?: CodeMessage;
  skillName?: string;
  // For output files
  outputFiles?: OutputFile[];
  // For tool calls
  toolCall?: ToolCallInfo;
  // For tool results
  toolResult?: ToolResultInfo;
}
