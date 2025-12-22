interface IProps {
    content?: string
}

const IterationItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div>
        <strong>
            {content}
        </strong>
    </div>
}

export default IterationItem