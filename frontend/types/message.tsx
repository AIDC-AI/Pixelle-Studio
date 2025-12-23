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

export interface Message {
  type: 'user' | 'system' | 'log' | 'script' | 'result' | 'error' | 'iteration' | 'evaluation' | 'advice' | 'code' | 'execution_result' | 'response' | 'skill_loaded' | 'output_files';
  content: any;
  timestamp: number;
  iteration?: number;
  // For code execution
  executionResult?: ExecutionResult;
  codeData?: CodeMessage;
  skillName?: string;
  // For output files
  outputFiles?: OutputFile[];
}
