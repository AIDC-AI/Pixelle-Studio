interface IProps {
    content?: string
}

const ResultItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div>
        <strong>Result:</strong>
        <pre className="whitespace-pre-wrap break-words overflow-x-auto">
            {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
        </pre>
    </div>
}

export default ResultItem