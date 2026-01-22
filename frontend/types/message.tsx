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
