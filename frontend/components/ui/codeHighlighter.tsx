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