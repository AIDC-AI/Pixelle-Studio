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
            background: '#fff',
            fontSize: '16px'
        },
        lineNumberStyle = {
            color: '#6e7681',
            userSelect: 'none',
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