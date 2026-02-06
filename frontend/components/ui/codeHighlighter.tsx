/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight} from 'react-syntax-highlighter/dist/esm/styles/prism';

interface IProps {
    language?: string
    code?: string
    style?: { [key: string]: React.CSSProperties }
    customStyle?: React.CSSProperties
    lineNumberStyle?: React.CSSProperties
}

const CodeHighlighter: React.FC<IProps> = (props) => {
    const {
        language = "python",
        code = "",
        style = oneLight,
        customStyle,
        lineNumberStyle
    } = props 
    
    return <SyntaxHighlighter
        language={language}
        style={style}
        customStyle={{
            margin: 0,
            background: '#fff',
            fontSize: '16px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            ...customStyle
        }}
        lineNumberStyle={{
            color: '#6e7681',
            userSelect: 'none',
            ...lineNumberStyle
        }}
        codeTagProps={{
            style: {
                whiteSpace: 'pre-wrap !important'
            }
        }}
        showLineNumbers
    >
        {code}
    </SyntaxHighlighter>
}

export default CodeHighlighter