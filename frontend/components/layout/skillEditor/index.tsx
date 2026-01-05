import { useState, useEffect, useCallback } from 'react'
import { X, Save, Upload, Trash2, FileCode, Link, GripVertical, Plus, ArrowUpRight, Play } from 'lucide-react'
import { getAuthHeaders } from '@/lib/data'
import { useApp } from '@/context'

interface Script {
  name: string
  path: string
  type: string
}

interface McpToolInputSchema {
  type?: string
  properties?: Record<string, {
    type?: string
    description?: string
  }>
  required?: string[]
}

interface McpTool {
  server_id: string
  server_name: string
  server_url: string
  name: string
  description: string
  inputSchema?: McpToolInputSchema
}

interface PendingMcpTool {
  tool: McpTool
  scriptName: string
}

interface Skill {
  id: string
  name: string
  description: string
  content?: string
  full_content?: string
  folder?: string
  is_global?: boolean
}

interface IProps {
  skill?: Skill | null
  isNew: boolean
  onSave: (skill: Skill, scripts: Script[]) => Promise<void>
  mcpTools: McpTool[]
  onTest?: (skillName: string) => void  // 测试回调
}

const API_BASE = 'http://localhost:8000/api'

const SkillEditor: React.FC<IProps> = (props) => {
    const {
        skill,
        isNew,
        onSave: _onSave, // 保留接口兼容但内部不使用
        mcpTools,
        onTest
    } = props 

    const { setSkillEditored } = useApp()
    
  void _onSave // 消除 TS 警告
  // Skill 表单状态
  const [name, setName] = useState(skill?.name || '')
  const [description, setDescription] = useState(skill?.description || '')
  const [content, setContent] = useState(skill?.content || '')
  
  // 脚本列表
  const [scripts, setScripts] = useState<Script[]>([])
  const [loadingScripts, setLoadingScripts] = useState(false)
  
  // 待创建的 MCP 工具（新建时暂存）
  const [pendingMcpTools, setPendingMcpTools] = useState<PendingMcpTool[]>([])
  
  // 当前技能 ID（保存后更新）
  const [currentSkillId, setCurrentSkillId] = useState<string | undefined>(skill?.id)
  
  // 拖拽状态
  const [dragOverScript, setDragOverScript] = useState(false)
  
  // 保存状态
  const [saving, setSaving] = useState(false)
  
  // 已保存状态（保存后从新建模式切换）
  const [isSaved, setIsSaved] = useState(false)
  
  // 只读模式（共享技能）
  const isReadOnly = !isNew && skill?.is_global === true
  
  // 是否为新建模式（考虑已保存状态）
  const isNewMode = isNew && !isSaved

  const handleClose = () => {
    setSkillEditored(false)
  }

  // 加载脚本列表（接受可选的 skillId 参数，用于立即加载）
  const fetchScripts = useCallback(async (skillIdOverride?: string) => {
    const skillId = skillIdOverride || currentSkillId || skill?.id
    if (!skillId) {
      setScripts([])
      return
    }
    
    setLoadingScripts(true)
    try {
      const res = await fetch(`${API_BASE}/v2/skills/${skillId}/scripts`, {
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const data = await res.json()
        setScripts(data)
      } else {
        setScripts([])
      }
    } catch (e) {
      console.error('获取脚本列表失败:', e)
      setScripts([])
    } finally {
      setLoadingScripts(false)
    }
  }, [currentSkillId, skill?.id, getAuthHeaders])

  // 当 skill 或 isNew 变化时，重置所有状态
  useEffect(() => {
    // 重置状态
    setPendingMcpTools([])
    setScripts([])
    setIsSaved(false)
    
    if (isNew) {
      // 新建模式：清空所有字段
      setName('')
      setDescription('')
      setContent('')
      setCurrentSkillId(undefined)
    } else if (skill) {
      // 编辑模式：加载技能数据
      setName(skill.name || '')
      setDescription(skill.description || '')
      setCurrentSkillId(skill.id)
      
      // 解析 full_content 获取内容部分
      if ((skill as any).full_content) {
        const fullContent = (skill as any).full_content
        // 去除 front matter
        const parts = fullContent.split('---')
        if (parts.length >= 3) {
          setContent(parts.slice(2).join('---').trim())
        } else {
          setContent(fullContent)
        }
      } else {
        setContent(skill.content || '')
      }
      
      // 加载脚本列表（直接传入 skill.id，避免依赖 currentSkillId 的时序问题）
      if (skill.id) {
        fetchScripts(skill.id)
      }
    }
  }, [skill, isNew]) // 移除 fetchScripts 依赖，防止循环

  // 处理文件上传
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    
    const file = e.target.files[0]
    const reader = new FileReader()
    
    reader.onload = (event) => {
      const fileContent = event.target?.result as string
      
      // 如果是 Markdown 文件，解析它
      if (file.name.endsWith('.md')) {
        // 尝试解析 front matter
        if (fileContent.startsWith('---')) {
          const parts = fileContent.split('---')
          if (parts.length >= 3) {
            const frontMatter = parts[1].trim()
            const bodyContent = parts.slice(2).join('---').trim()
            
            // 解析 front matter
            frontMatter.split('\n').forEach(line => {
              const [key, value] = line.split(':').map(s => s.trim())
              if (key === 'name' && !name) setName(value)
              if (key === 'description' && !description) setDescription(value)
            })
            
            setContent(bodyContent)
            return
          }
        }
        setContent(fileContent)
      } else {
        // 其他文件作为内容附加
        setContent(prev => prev + '\n\n```\n' + fileContent + '\n```')
      }
    }
    
    reader.readAsText(file)
    e.target.value = '' // 清空 input
  }

  // 处理 MCP Tool 拖拽
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOverScript(true)
  }

  const handleDragLeave = () => {
    setDragOverScript(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setDragOverScript(false)
    
    try {
      const toolData = e.dataTransfer.getData('application/json')
      if (!toolData) return
      
      const tool: McpTool = JSON.parse(toolData)
      const scriptName = `mcp_${tool.name.replace(/[^a-zA-Z0-9]/g, '_')}.py`
      
      // 在内容中插入工具占位符
      const placeholder = `# ${scriptName} #`
      setContent(prev => prev + `\n\n请调用 ${placeholder} 来执行 ${tool.name} 操作`)
      
      const skillId = currentSkillId || skill?.id
      if (skillId) {
        // 已保存的技能，直接创建脚本
        await createMcpToolScript(tool)
      } else {
        // 新建技能，暂存待创建的脚本（去重）
        setPendingMcpTools(prev => {
          // 检查是否已存在
          if (prev.some(p => p.scriptName === scriptName)) {
            return prev
          }
          return [...prev, { tool, scriptName }]
        })
      }
    } catch (e) {
      console.error('处理拖拽失败:', e)
    }
  }

  // 创建 MCP Tool 脚本
  const createMcpToolScript = async (tool: McpTool, insertReference: boolean = false) => {
    const skillId = currentSkillId || skill?.id
    const scriptName = `mcp_${tool.name.replace(/[^a-zA-Z0-9]/g, '_')}.py`
    
    if (!skillId) {
      // 新建技能，暂存待创建的脚本（去重）
      setPendingMcpTools(prev => {
        if (prev.some(p => p.scriptName === scriptName)) {
          return prev
        }
        return [...prev, { tool, scriptName }]
      })
      if (insertReference) {
        insertScriptReference(scriptName, tool.inputSchema)
      }
      return
    }
    
    try {
      const res = await fetch(`${API_BASE}/v2/skills/${skillId}/scripts/from-mcp-tool`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          tool_name: tool.name,
          server_url: tool.server_url,
          original_tool_name: tool.name,
          input_schema: tool.inputSchema || null
        })
      })
      
      if (res.ok) {
        const newScript = await res.json()
        fetchScripts()
        
        // 如果需要插入引用（使用返回的参数 schema）
        if (insertReference && newScript.name) {
          insertScriptReference(newScript.name, newScript.param_schema || tool.inputSchema)
        }
      } else {
        const data = await res.json()
        alert('创建脚本失败: ' + (data.detail || '未知错误'))
      }
    } catch (e) {
      console.error('创建 MCP 脚本失败:', e)
    }
  }

  // 添加 MCP Tool 并插入引用
  const handleAddMcpTool = async (tool: McpTool) => {
    await createMcpToolScript(tool, true)
  }

  // 生成参数示例字符串
  const generateParamExample = (inputSchema?: McpToolInputSchema): string => {
    if (!inputSchema?.properties) return '{}'
    
    const example: Record<string, unknown> = {}
    const properties = inputSchema.properties
    const required = inputSchema.required || []
    
    for (const [propName, propInfo] of Object.entries(properties)) {
      const isRequired = required.includes(propName)
      const propType = propInfo.type || 'string'
      
      if (propType === 'string') {
        example[propName] = isRequired ? `<${propName}>` : `<可选:${propName}>`
      } else if (propType === 'number' || propType === 'integer') {
        example[propName] = 0
      } else if (propType === 'boolean') {
        example[propName] = true
      } else {
        example[propName] = null
      }
    }
    
    return JSON.stringify(example, null, 2)
  }

  // 插入脚本引用到内容（包含参数示例）
  const insertScriptReference = (scriptName: string, inputSchema?: McpToolInputSchema) => {
    const reference = `# ${scriptName} #`
    const paramExample = generateParamExample(inputSchema)
    
    let instruction = ''
    if (inputSchema?.properties && Object.keys(inputSchema.properties).length > 0) {
      // 有参数的工具，生成详细说明
      const paramDesc = Object.entries(inputSchema.properties)
        .map(([name, info]) => `  - ${name}: ${info.description || '无描述'}`)
        .join('\n')
      
      instruction = `请调用 ${reference} 来执行操作。
        **参数说明:**
        ${paramDesc}

        **参数示例:**
        \`\`\`json
        ${paramExample}
        \`\`\``
    } else {
      // 无参数的工具
      instruction = `请调用 ${reference} 来执行操作（无需参数）`
    }
    
    setContent(prev => {
      if (prev.trim()) {
        return prev + `\n\n${instruction}`
      }
      return instruction
    })
  }

  // 删除脚本
  const handleDeleteScript = async (scriptName: string) => {
    if (!skill?.id) return
    if (!confirm(`确定要删除脚本 "${scriptName}" 吗？`)) return
    
    try {
      const res = await fetch(`${API_BASE}/v2/skills/${skill.id}/scripts/${scriptName}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
      
      if (res.ok) {
        fetchScripts()
        // 从内容中移除对该脚本的引用
        setContent(prev => prev.replace(new RegExp(`#\\s*${scriptName}\\s*#`, 'g'), ''))
      }
    } catch (e) {
      console.error('删除脚本失败:', e)
    }
  }

  // 保存技能
  const handleSave = async () => {
    if (!name.trim()) {
      alert('请输入技能名称')
      return
    }
    
    setSaving(true)
    try {
      // 内容已经包含脚本引用，直接保存
      const finalContent = content
      const skillId = currentSkillId || skill?.id
      
      // 调用保存，但不关闭窗口
      const savedSkillId = await saveSkillToBackend({
        id: skillId || '',
        name,
        description,
        content: finalContent
      })
      
      if (savedSkillId) {
        setCurrentSkillId(savedSkillId)
        
        // 创建待处理的 MCP 工具脚本
        for (const pending of pendingMcpTools) {
          try {
            await fetch(`${API_BASE}/v2/skills/${savedSkillId}/scripts/from-mcp-tool`, {
              method: 'POST',
              headers: getAuthHeaders(),
              body: JSON.stringify({
                tool_name: pending.tool.name,
                server_url: pending.tool.server_url,
                original_tool_name: pending.tool.name
              })
            })
          } catch (e) {
            console.error('创建 MCP 脚本失败:', e)
          }
        }
        setPendingMcpTools([])
        
        // 刷新脚本列表
        fetchScripts()
        
        // 标记为已保存
        setIsSaved(true)
        
        // 通知父组件刷新 sidebar
        if (_onSave) {
          _onSave({
            id: savedSkillId,
            name,
            description,
            content: finalContent
          }, scripts)
        }
        
        alert('保存成功！')
      }
    } catch (e) {
      console.error('保存失败:', e)
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }
  
  // 保存技能到后端（返回技能 ID）
  const saveSkillToBackend = async (skillData: Skill): Promise<string | null> => {
    try {
      let res
      if (skillData.id) {
        // 更新
        res = await fetch(`${API_BASE}/v2/skills/${skillData.id}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            name: skillData.name,
            description: skillData.description,
            content: skillData.content
          })
        })
      } else {
        // 创建
        res = await fetch(`${API_BASE}/v2/skills/`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            name: skillData.name,
            description: skillData.description,
            content: skillData.content
          })
        })
      }
      
      if (res.ok) {
        const data = await res.json()
        return data.id || skillData.id
      } else {
        const data = await res.json()
        alert('保存失败: ' + (data.detail || '未知错误'))
        return null
      }
    } catch (e) {
      console.error('保存请求失败:', e)
      return null
    }
  }
  
  // 测试技能
  const handleTest = () => {
    if (onTest && name.trim()) {
      onTest(name)
    } else if (!name.trim()) {
      alert('请先输入技能名称')
    }
  }

  // 开始拖拽 MCP Tool
  const handleToolDragStart = (e: React.DragEvent, tool: McpTool) => {
    e.dataTransfer.setData('application/json', JSON.stringify(tool))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* 顶部栏 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-800">
            {isNewMode ? '新建技能' : isReadOnly ? '查看技能' : '编辑技能'}
          </h2>
          {isReadOnly && (
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">共享技能（只读）</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* 上传文件 */}
          {!isReadOnly && (
            <label className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer transition-colors">
              <Upload className="w-4 h-4" />
              上传文件
              <input
                type="file"
                accept=".md,.txt,.py,.sh"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          )}
          
          {/* 测试按钮 */}
          <button
            onClick={handleTest}
            disabled={!name.trim() || !onTest}
            className="flex items-center gap-2 px-3 py-2 text-sm text-green-700 bg-green-100 hover:bg-green-200 rounded-lg disabled:opacity-50 transition-colors"
          >
            <Play className="w-4 h-4" />
            测试
          </button>
          
          {!isReadOnly && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gray-900 hover:bg-gray-800 rounded-lg disabled:opacity-50 transition-colors"
            >
              <Save className="w-4 h-4" />
              {saving ? '保存中...' : '保存'}
            </button>
          )}
          
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* 主内容区 - 左右分栏 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：Markdown 编辑区 */}
        <div className="flex-1 flex flex-col p-4 border-r border-gray-200 overflow-auto">
          {/* 名称 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              名称 {currentSkillId && <span className="text-xs text-gray-400">（创建后不可修改）</span>}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入技能名称"
              disabled={isReadOnly || !!currentSkillId}
              className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 ${(isReadOnly || currentSkillId) ? 'bg-gray-100 cursor-not-allowed' : ''}`}
            />
          </div>

          {/* 描述 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="简要描述这个技能的作用"
              disabled={isReadOnly}
              className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 ${isReadOnly ? 'bg-gray-100 cursor-not-allowed' : ''}`}
            />
          </div>

          {/* 详细内容 */}
          <div className="flex-1 flex flex-col">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              详细内容 (Markdown)
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="输入技能的详细说明（支持 Markdown 格式）
                    提示：使用 # script_name.py # 格式引用脚本
                    例如：请调用 # time.py # 来获取当前时间"
              disabled={isReadOnly}
              className={`flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 resize-none font-mono text-sm ${isReadOnly ? 'bg-gray-100 cursor-not-allowed' : ''}`}
            />
          </div>
        </div>

        {/* 右侧：脚本管理区 */}
        <div className="w-80 flex flex-col bg-gray-50 overflow-auto">
          {/* 当前技能的脚本 */}
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <FileCode className="w-4 h-4" />
              脚本文件
            </h3>
            
            {loadingScripts ? (
              <p className="text-xs text-gray-500">加载中...</p>
            ) : scripts.length === 0 && pendingMcpTools.length === 0 ? (
              <p className="text-xs text-gray-500">暂无脚本，可从下方拖拽工具添加</p>
            ) : (
              <div className="space-y-2">
                {/* 已保存的脚本 */}
                {scripts.map((script) => (
                  <div
                    key={script.name}
                    className="flex items-center gap-2 p-2 bg-white rounded-lg border border-gray-200 group"
                  >
                    <FileCode className="w-4 h-4 text-green-600 shrink-0" />
                    <span className="flex-1 text-sm text-gray-700 truncate">{script.name}</span>
                    <button
                      onClick={() => insertScriptReference(script.name)}
                      className="px-2 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-medium flex items-center gap-1 transition-all"
                      title="插入到文档"
                    >
                      <ArrowUpRight className="w-3 h-3" />
                      插入
                    </button>
                    <button
                      onClick={() => handleDeleteScript(script.name)}
                      className="p-1.5 hover:bg-red-100 rounded transition-all"
                      title="删除脚本"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </button>
                  </div>
                ))}
                
                {/* 待保存的脚本（新建时） */}
                {pendingMcpTools.map((pending, index) => (
                  <div
                    key={`pending-${index}`}
                    className="flex items-center gap-2 p-2 bg-yellow-50 rounded-lg border border-yellow-200 group"
                  >
                    <FileCode className="w-4 h-4 text-yellow-600 shrink-0" />
                    <span className="flex-1 text-sm text-gray-700 truncate">{pending.scriptName}</span>
                    <span className="text-xs text-yellow-600 bg-yellow-100 px-1.5 py-0.5 rounded">待保存</span>
                    <button
                      onClick={() => insertScriptReference(pending.scriptName)}
                      className="px-2 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-medium flex items-center gap-1 transition-all"
                      title="插入到文档"
                    >
                      <ArrowUpRight className="w-3 h-3" />
                      插入
                    </button>
                    <button
                      onClick={() => setPendingMcpTools(prev => prev.filter((_, i) => i !== index))}
                      className="p-1.5 hover:bg-red-100 rounded transition-all"
                      title="移除"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* MCP Tools 拖拽区 */}
          <div className="flex-1 p-4 overflow-auto">
            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <Link className="w-4 h-4" />
              可用工具 (MCP)
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              拖拽工具到左侧内容区，自动生成调用脚本
            </p>
            
            {/* 拖拽目标区域 */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`mb-4 p-4 border-2 border-dashed rounded-lg text-center transition-colors ${
                dragOverScript 
                  ? 'border-blue-400 bg-blue-50' 
                  : 'border-gray-300 bg-white'
              }`}
            >
              <p className="text-sm text-gray-500">
                {dragOverScript ? '释放以添加工具' : '拖拽工具到这里'}
              </p>
            </div>
            
            {/* MCP Tools 列表 */}
            {mcpTools?.length === 0 ? (
              <p className="text-xs text-gray-500">暂无可用工具</p>
            ) : (
              <div className="space-y-2">
                {mcpTools?.map((tool, index) => (
                  <div
                    key={`${tool.server_id}-${tool.name}-${index}`}
                    draggable
                    onDragStart={(e) => handleToolDragStart(e, tool)}
                    className="flex items-center gap-2 p-2 bg-white rounded-lg border border-gray-200 cursor-grab hover:border-gray-400 transition-colors group"
                  >
                    <GripVertical className="w-4 h-4 text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-700 truncate">{tool.name}</p>
                      <p className="text-xs text-gray-500 truncate">{tool.server_name}</p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleAddMcpTool(tool); }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded transition-all"
                      title="添加为脚本并插入引用"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SkillEditor
