interface IProps {
    content?: string
}

const UserItem: React.FC<IProps> = (props) => {
    const { content = '' } = props

    return <div>
        {content}
    </div>
}

export default UserItem