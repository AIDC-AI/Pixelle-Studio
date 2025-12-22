interface IProps {
    content?: string
}

const EvalutaionItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div className="bg-[#f0f8ff] p-2 rounded">
        <pre className="whitespace-pre-wrap m-0">
            {content}
        </pre>
    </div>
}

export default EvalutaionItem