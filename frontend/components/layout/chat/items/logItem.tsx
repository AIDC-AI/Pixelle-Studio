interface IProps {
    content?: string
}

const LogItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div className="font-mono text-sm text-gray-500 my-0.5">
        {content}
    </div>
}

export default LogItem