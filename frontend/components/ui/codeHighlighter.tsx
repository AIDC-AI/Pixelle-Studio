import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/prism';

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
        style = vs,
        customStyle = {
            margin: 0,
            padding: '0.75rem',
            background: '#ffffff',
            fontSize: '0.75rem',
            lineHeight: '1.25rem',
            borderRadius: '0.375rem',
        },
        lineNumberStyle = {
            minWidth: '2.5em',
            paddingRight: '0.75em',
            color: '#9ca3af',
            userSelect: 'none',
            fontSize: '0.7rem',
        }
    } = props 

    return <SyntaxHighlighter
        language={language}
        style={style}
        customStyle={customStyle}
        lineNumberStyle={lineNumberStyle}
        showLineNumbers
        wrapLines
    >
        {code}
    </SyntaxHighlighter>
}

export default CodeHighlighter