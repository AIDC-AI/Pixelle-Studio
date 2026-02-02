'use client'

import { useState } from 'react'
import { Mail, Lock, User, Loader2, Eye, EyeOff } from 'lucide-react'
import { useApp } from '@/context'
import Logo from '@/components/ui/logo'

type AuthMode = 'login' | 'register'

const AuthPage = () => {
  const { login, register } = useApp()
  
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      if (mode === 'login') {
        await login(email, password)
        // AuthGuard 会自动处理跳转
      } else {
        const res = await register(username, email, password)
        if (!!res) {
          setMode('login')
          setError('')
          setUsername('')
          // setEmail('')
          // setPassword('')
        }
      }
    } catch (err: any) {
      setError(err.message || '操作失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    setError('')
    setUsername('')
    setEmail('')
    setPassword('')
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center itms-center mb-8">
          {/* <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-900 rounded-2xl mb-4">
            <span className="text-2xl font-bold text-white">P</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Pixelle.AI</h1> */}
          <Logo />
        </div>

        {/* Auth Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 text-center">
            {mode === 'login' ? '欢迎回来' : '创建账号'}
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  用户名
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="输入用户名"
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 focus:border-transparent transition-all"
                    required
                    minLength={2}
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                邮箱
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="输入邮箱"
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 focus:border-transparent transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入密码"
                  className="w-full pl-10 pr-12 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 focus:border-transparent transition-all"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {mode === 'register' && (
                <p className="text-xs text-gray-500 mt-1">密码至少 8 个字符</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>处理中...</span>
                </>
              ) : (
                <span>{mode === 'login' ? '登录' : '注册'}</span>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              {mode === 'login' ? '还没有账号？' : '已有账号？'}
              <button
                onClick={switchMode}
                className="ml-1 text-gray-900 font-medium hover:underline"
              >
                {mode === 'login' ? '立即注册' : '立即登录'}
              </button>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-gray-500 mt-6">
          使用即表示同意我们的服务条款和隐私政策
        </p>
      </div>
    </div>
  )
}

export default AuthPage