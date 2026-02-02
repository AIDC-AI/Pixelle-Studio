// frontend/utils/codeBlockFilter.ts
// 流式输出的时候过滤掉代码块

type ParserState = {
    buffer: string;
    inCodeBlock: boolean;
    codeBlockType: 'execute' | 'json' | 'json_single_quote' | null;
    braceDepth: number;
    lastChar: string;
  };
  
  // Initialize parser state
  export const createParserState = (): ParserState => ({
    buffer: '',
    inCodeBlock: false,
    codeBlockType: null,
    braceDepth: 0,
    lastChar: ''
  });
  
  /**
   * Process streaming content and filter out code blocks
   * @param content Newly received content
   * @param state Current parser state
   * @returns Filtered content and updated state
   */
  export const filterCodeBlocks = (content: string, state: ParserState): { filtered: string; state: ParserState } => {
    let filtered = '';
    let i = 0;
    const newState = { ...state };
  
    while (i < content.length) {
      const char = content[i];
      newState.buffer += char;
  
      if (!newState.inCodeBlock) {
        // Check for code block start
        if (newState.buffer.endsWith('<execute')) {
          newState.inCodeBlock = true;
          newState.codeBlockType = 'execute';
          newState.buffer = '';
          filtered = filtered.replace('<execut', '');
        } else if (newState.buffer.endsWith('{"code') || newState.buffer.endsWith('{ "code')) {
          newState.inCodeBlock = true;
          newState.codeBlockType = 'json';
          newState.braceDepth = 1;
          newState.buffer = '';
          filtered = filtered.replace('{"cod', '');
          filtered = filtered.replace('{ "cod', '');
        } else if (newState.buffer.endsWith('{\'code')) {
          newState.inCodeBlock = true;
          newState.codeBlockType = 'json_single_quote';
          newState.braceDepth = 1;
          newState.buffer = '';
          filtered = filtered.replace('{\'cod', '');
        } else {
          // Not a code block start, add to filtered content
          filtered += char;
          // Keep buffer size manageable
          if (newState.buffer.length > 20) {
            newState.buffer = newState.buffer.slice(-20);
          }
        }
      } else {
        // Inside a code block
        if (newState.codeBlockType === 'execute' && newState.buffer.endsWith('</execute>')) {
          // Execute tag end
          newState.inCodeBlock = false;
          newState.codeBlockType = null;
          newState.buffer = '';
        } else if (newState.codeBlockType === 'json' || newState.codeBlockType === 'json_single_quote') {
          // Handle JSON code blocks
          if (char === '{') newState.braceDepth++;
          if (char === '}') {
            newState.braceDepth--;
            if (newState.braceDepth === 0) {
              // JSON block end
              newState.inCodeBlock = false;
              newState.codeBlockType = null;
              newState.buffer = '';
            }
          }
        }
      }
  
      newState.lastChar = char;
      i++;
    }
  
    return { filtered, state: newState };
  };