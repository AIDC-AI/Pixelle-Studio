'use client'

import { createContext, Dispatch, SetStateAction, useContext, useEffect, useRef, useState } from 'react';
import { sessionAPI } from '@/lib/sessionApi';
import { UserResponse } from '@/types/user';
import { userAPI } from '@/lib/userApi';
import { useRouter, usePathname } from 'next/navigation';
import { MCPTool } from '@/types/server';
import { Toast } from 'radix-ui';
import { Check, Lightbulb, X } from 'lucide-react';

export enum ToastType {
    SUCCESS = 'success',
    ERROR = 'error',
    INFO = 'info'
}

type IProps = {
    user: UserResponse | null
    setUser: Dispatch<SetStateAction<UserResponse | null>>

    token: string | null
    setToken: Dispatch<SetStateAction<string | null>>

    activeSessionId: string
    setActiveSessionId: Dispatch<SetStateAction<string>>

    skillEditored: boolean 
    setSkillEditored: Dispatch<SetStateAction<boolean>>

    currentSkillName: string | null
    setCurrentSkillName: Dispatch<SetStateAction<string | null>>

    mcpTools: MCPTool[] | null
    setMcpTools: Dispatch<SetStateAction<MCPTool[] | null>>

    isChangeSkill: boolean
    setIsChangeSkill: Dispatch<SetStateAction<boolean>>

    login: (email: string, password: string) => Promise<void>
    register: (username: string, email: string, password: string) => Promise<boolean>
    logout: () => void

    showToast: (type: ToastType, text: string) => void
    hideToast: () => void
};

const AppContext = createContext<IProps | null>(null);

const PUBLIC_ROUTES = ['/auth']

export function AppProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();

    const [user, setUser] = useState<UserResponse | null>(null)
    const [token, setToken] = useState<string | null>(null)

    const [activeSessionId, setActiveSessionId] = useState<string>('');

    const [skillEditored, setSkillEditored] = useState<boolean>(false)
    const [currentSkillName, setCurrentSkillName] = useState<string | null>(null)
    const [mcpTools, setMcpTools] = useState<MCPTool[] | null>(null)
    const [isChangeSkill, setIsChangeSkill] = useState<boolean>(false)

    const [toastOpen, setToastOpen] = useState<boolean>(false)
    const [toastType, setToastType] = useState<ToastType>(ToastType.INFO)
    const [toastContent, setToastContent] = useState<string>('')
    const timerRef = useRef<number | null>(null);

    const login = async (email: string, password: string) => {
        try {
            const res = await userAPI.login(email, password)
            if (!!res) {
                userAPI.setToken(res.token.access_token)
                setToken(res.token.access_token)
                setUser(res.user)
            }
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "登录失败！")
        }
    }

    const register = async (username: string, email: string, password: string) => {
        try {
            const res = await userAPI.createUser({
                username,
                email,
                password
            })
            if (!!res) {
                showToast(ToastType.SUCCESS, "注册成功！")
                return true
            }
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "注册失败！")
        }
        return false
    } 

    const logout = () => {
        try {
            setUser(null)
            setToken(null)
            userAPI.logout()
            showToast(ToastType.SUCCESS, "登出成功！")
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "登出失败！")
        }
    }

    const showToast = (type: ToastType, text: string) => {
        setToastOpen(true)
        setToastType(type)
        setToastContent(text)
        clearTimeout()
        timerRef.current = window.setTimeout(hideToast, 2000)
    }

    const hideToast = () => {
        setToastOpen(false)
        setToastType(ToastType.INFO)
        setToastContent('')
    }

    const getCurrentUser = async () => {
        const user = await userAPI.getCurrentUser()
        if (!!user) {
            setUser(user)
            setToken(userAPI.getToken())
        } else {
            userAPI.clearToken()
            setUser(null)
            setToken(null)
        }
    }

    const clearTimeout = () => {
        if (timerRef.current) {
            window.clearTimeout(timerRef.current)
            timerRef.current = null
        }
    }

    const renderToastContent = () => {
        let icon
        let iconColor = ''
        switch (toastType) {
            case ToastType.SUCCESS:
                icon = <Check />
                iconColor = "bg-success"
            break;
            case ToastType.ERROR:
                icon = <X />
                iconColor = "bg-error"
            break;
            case ToastType.INFO:
            default:
                icon = <Lightbulb />
                iconColor = "bg-info"
            break;
        }
        return <div className='flex flex-row gap-2 items-center'>
            <div className={`w-4 h-4 text-white p-0.75 rounded-full flex justify-center items-center ${iconColor}`}>
                {icon}
            </div>
            {toastContent}
        </div>
    }

    useEffect(() => {
        setActiveSessionId(sessionAPI.getActiveSessionId())
        
        // 初始化：如果有token，获取用户信息
        const initAuth = async () => {
            if (userAPI.isAuthenticated() && !user) {
                await getCurrentUser()
            }
        }
        initAuth()
    }, [])
    
    useEffect(() => {
        const isAuthRoute = PUBLIC_ROUTES.includes(pathname);
        
        if (userAPI.isAuthenticated() && user) {
            // 已登录且有用户信息：如果在登录页，跳转到主页
            if (isAuthRoute) {
                router.push('/')
            }
        } else if (!userAPI.isAuthenticated()) {
            // 未登录：如果不在登录页，跳转到登录页
            if (!isAuthRoute) {
                router.push('/auth')
            }
        }
        // 如果isAuthenticated但user为null（正在加载中），不做任何跳转
    }, [pathname, user])

    return <AppContext.Provider
        value={
            {
                user, 
                setUser,
                token, 
                setToken,
                activeSessionId, 
                setActiveSessionId, 
                skillEditored, 
                setSkillEditored,
                currentSkillName, 
                setCurrentSkillName,
                mcpTools, 
                setMcpTools,
                isChangeSkill, 
                setIsChangeSkill,
                login,
                register,
                logout,
                showToast,
                hideToast
            }
        }
    >
        {children}
        <Toast.Provider swipeDirection="up">
			<Toast.Root 
                className="bg-white text-sm text-gray-900 rounded-md px-4 py-2 flex justify-center items-center
                shadow-[0_10px_38px_-10px_hsl(206_22%_7%/35%),0_10px_20px_-15px_hsl(206_22%_7%/20%)]
                data-[state=open]:animate-slideIn data-[state=closed]:animate-hide" 
                open={toastOpen} 
                onOpenChange={setToastOpen}
            >
				{/* <Toast.Title className="ToastTitle">{toastDetail?.title}</Toast.Title> */}
				<Toast.Description asChild>
					{renderToastContent()}
				</Toast.Description>
			</Toast.Root>
			<Toast.Viewport className="fixed top-4 left-1/2 -translate-x-1/2 flex flex-col z-9999 outline-none" />
		</Toast.Provider>
    </AppContext.Provider>;
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be used within AppProvider');
    return ctx;
}