interface IProps {
    content?: string
}

const SystemItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div>
        <em>
            {content}
        </em>
    </div>
}

export default SystemItem