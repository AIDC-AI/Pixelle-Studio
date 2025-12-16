export interface Message {
  type: 'user' | 'system' | 'log' | 'script' | 'result' | 'error' | 'iteration' | 'evaluation' | 'advice';
  content: any;
  timestamp: number;
  iteration?: number;
}