import { useApp } from "@/context"
import { Avatar, DropdownMenu } from "radix-ui"

const User = () => {
    const { user, logout } = useApp()

    return (
        <DropdownMenu.Root>
			<DropdownMenu.Trigger asChild>
				<Avatar.Root className="inline-flex items-center justify-center align-middle overflow-hidden select-none w-7 h-7 rounded-full bg-gray-100">
                    <Avatar.Fallback className="text-gray-900 text-xs">{user?.username?.[0]}</Avatar.Fallback>
                </Avatar.Root>
			</DropdownMenu.Trigger>

			<DropdownMenu.Portal>
				<DropdownMenu.Content 
                    className="w-40 bg-white border border-gray-300 rounded-md p-2 shadow-[0px_10px_38px_-10px_rgba(22,23,24,0.35),0px_10px_20px_-15px_rgba(22,23,24,0.2)] animate-up-fade will-change-[transform,opacity]"
                    sideOffset={5}
                >
                    <span
                        className="text-xs text-gray-900 truncate cursor-default"
                    >
						{`用户名：${user?.username}`}
					</span>
					<span
                        className="text-xs text-gray-900 truncate cursor-default"
                    >
						{`邮箱：${user?.email}`}
					</span>
                    <button
                        className="border border-gray-400 hover:border-gray-800 hover:bg-gray-100 text-xs text-gray-900 w-full rounded-sm px-2"
                        onClick={logout}
                    >
                        登出
                    </button>
					<DropdownMenu.Arrow              
                        className="fill-gray-300 translate-x-0.5" 
                        width={14} 
                        height={6}  
                    />
                    <DropdownMenu.Arrow              
                        className="fill-white" 
                        width={10} 
                        height={5}  
                    />
				</DropdownMenu.Content>
			</DropdownMenu.Portal>
		</DropdownMenu.Root>
    )
}

export default User