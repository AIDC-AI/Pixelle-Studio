interface IProps {
    content?: string
}

const ErrorItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div className="text-[#ff0000]">
        Error: {content}
    </div>
}

export default ErrorItem