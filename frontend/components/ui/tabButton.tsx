import { MouseEventHandler, ReactNode } from "react";

interface IProps {
    isCollapsed?: boolean
    isActive?: boolean
    onClick?: MouseEventHandler<HTMLButtonElement>
    children?: ReactNode
    className?: string
}

const TabButton: React.FC<IProps> = (props) => {
    const { isCollapsed = false, isActive = false, onClick = () => {}, children, className } = props;

    return <button
        onClick={onClick}
        className={`${className} ${isCollapsed ? "p-2" : "flex-1 flex items-center justify-center gap-2 px-4 py-2"} rounded-lg transition-colors hover:text-white! hover:bg-red-500! ${
            isActive ? 'bg-black text-white' : 'bg-gray-50 text-gray-600'
        }`}
    >
        {children}
    </button>
}

export default TabButton