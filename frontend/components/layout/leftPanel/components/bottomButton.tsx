import { MouseEventHandler } from "react"

interface IProps {
    text?: string
    icon?: React.ReactNode
    onClick?: MouseEventHandler<HTMLButtonElement>
}

const BottomButton: React.FC<IProps> = (props) => {
    const { text = '', icon, onClick = () => {} } = props

    return <div className="p-4 border-t border-border-default">
        <button 
            onClick={onClick}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-text-default bg-default hover:bg-hover rounded-lg transition-colors"
        >
            {icon}
            <span className="text-sm">{text}</span>
        </button>
    </div>
}

export default BottomButton