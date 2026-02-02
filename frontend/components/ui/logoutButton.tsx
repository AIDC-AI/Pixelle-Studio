import { useApp } from "@/context"
import { LogOut } from "lucide-react"

interface IProps {
    buttonClassName?: string
    iconClassName?: string
}

const LogoutButton: React.FC<IProps> = (props) => {
    const { buttonClassName, iconClassName = "w-4 h-4" } = props

    const { logout } = useApp()
    
    return <button
        onClick={logout}
        className={buttonClassName}
    >
        <LogOut className={iconClassName} />
    </button>
}

export default LogoutButton