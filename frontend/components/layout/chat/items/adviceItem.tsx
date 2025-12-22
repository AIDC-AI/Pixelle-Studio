interface IProps {
    content?: string
}

const AdviceItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div className="bg-[#fffacd] p-2 rounded">
        <pre className="whitespace-pre-wrap m-0">
            {content}
        </pre>
    </div>
}

export default AdviceItem