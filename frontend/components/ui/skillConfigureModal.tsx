import { useEffect, useState } from 'react'
import { X, Save, Upload, Trash2, FileCode, Link, GripVertical, Plus, ArrowUpRight, Play, XCircle } from 'lucide-react'
import { ToastType, useApp } from '@/context'
import { MCPTool } from '@/types/server'
import { skillAPI } from '@/lib/skillApi'
import { Dialog, Form } from "radix-ui";
import { capitalize, updateOrAddYamlField } from '@/utils/utils'
import FormInput from '@/components/ui/form/input'

interface Script {
  name: string
  server_name?: string
}

interface IProps {
    open: boolean
    skillName: string | null
    mcpTools?: MCPTool[] | null
    onSuccess?: () => void
    onClose?: () => void
}

const SkillConfigureModal: React.FC<IProps> = (props) => {
    const { open, skillName, mcpTools, onSuccess, onClose} = props
    const {  
        user, 
        showToast
    } = useApp()

  // 初始化表单数据
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: ''
  });

  // 脚本列表
  const [scripts, setScripts] = useState<Script[]>([])

  // 拖拽状态
  const [dragOverScript, setDragOverScript] = useState<boolean>(false)
  
  // 保存状态
  const [saving, setSaving] = useState<boolean>(false)
  
  // 只读模式（共享技能）
  const [isReadOnly, setIsReadOnly] = useState<boolean>(false)

  const handleClear = () => {
    setFormData({
      name: "",
      description: "",
      content: ""
    })
    setIsReadOnly(false)
    setScripts([])
  }

  const handleGetSkillData = async () => {
    if (!!skillName) {
      const res = await skillAPI.getSkill(skillName, user?.uid)
      if (!!res) {
        setFormData({
          name: res.name,
          description: res.meta.description,
          content: res.content
        })
        setIsReadOnly(!!res.meta.is_default)
        // 不是default的skill才需要获取scripts
        if (!res.meta.is_default) {
          getScriptsFromSkill(res.content)
        }
      }
    } else {
      handleClear()
    }
  }

  // 从skill中获取scripts
  const getScriptsFromSkill = (content: string) => {
    // 修改正则以支持路径格式，如 # test/i_crop-start #
    const regex = /#\s*([\w\-/]+)-start\s*#/g;
    const matches = [...content.matchAll(regex)];
    if (!!matches?.[0]?.[1]) {
      const splitArr = matches[0][1].split('/')
      setScripts(mcpTools?.filter((tool) => tool.server_name === splitArr?.[0] && tool.name === splitArr?.[1])?.map((tool) => ({
        name: tool.name,
        server_name: tool.server_name
      })) || [])
    }
  }

  // 处理 MCP Tool 拖拽
  const handleToolDragStart = (e: React.DragEvent, tool: MCPTool) => {
    if (isReadOnly)
      return
    e.dataTransfer.setData('application/json', JSON.stringify(tool))
    e.dataTransfer.effectAllowed = 'copy'
  }

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
      
      const tool: MCPTool = JSON.parse(toolData)
  
      const topics = []
      if (!!tool?.inputSchema?.properties) {
        for (const key in tool.inputSchema.properties) {
          if (!!tool.inputSchema.properties[key]) {
            topics.push({
              name: key,
              label: `This Is A ${capitalize(tool.inputSchema.properties[key]?.type)}`
            })
          }
        }
      }
      const topicStr = topics?.length > 0 ? topics.reduce<string>((total, topic) => `${total}${total === "" ? "" : ","}${topic.name}:${topic.label}`, "") : ""
      // 在内容中插入工具占位符
      const placeholderStart = `# ${tool.server_name}/${tool.name}-start #`
      const placeholderEnd = `# ${tool.server_name}/${tool.name}-end #`
      setFormData(prev => ({
        ...prev,
        content:prev.content + `\n\n${placeholderStart}\ncall_tool('${tool.name}', {${topicStr}})\n${placeholderEnd}`
      }))
      setScripts(prev => [...prev, {
        name: tool.name,
        server_name: tool.server_name
      }])
    } catch (e) {
      console.error('处理拖拽失败:', e)
    }
  }

  // 删除脚本
  const handleDeleteScript = async (scriptName: string, scriptServerName?: string) => {
    const name = !!scriptServerName ? `${scriptServerName}/${scriptName}` : scriptName
    // 转义特殊字符（如 /）
    const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    
    // 删除整个块，支持路径格式如 test/i_crop
    const regex = new RegExp(
      `#\\s*${escapedName}-start\\s*#[\\s\\S]*?#\\s*${escapedName}-end\\s*#`,
      'g'
    ); 
    setFormData(prev => ({
        ...prev,
        content: prev.content
        .replace(regex, '')  // 删除块
      })
    );
    setScripts(prev => prev.filter((script) => scriptServerName ? (script.name !== scriptName && script.server_name !== scriptServerName) : script.name !== scriptName))
  }
  
  const handleSubmit = async (data: { [x: string]: FormDataEntryValue; name?: any; description?: any; content?: any }): Promise<string | null> => {
    try {
      setSaving(true)
      if (!!skillName) {
        // 更新：使用原名称作为第一个参数
        await skillAPI.updateSkill(skillName, {
          description: data.description,
          content: data.content
        }, user?.uid)
        showToast(ToastType.SUCCESS, "更新成功！")
      } else {
        // 创建
        await skillAPI.createSkill({
          name: data.name,
          description: data.description,
          content: data.content
        }, user?.uid)
        showToast(ToastType.SUCCESS, "添加成功！")
      }
      onSuccess?.()
      return null
    } catch (e) {
      console.error('保存请求失败:', e)
      showToast(ToastType.ERROR, (e as Error).message || '保存失败！')
      return null
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    handleGetSkillData()
  }, [skillName])

  useEffect(() => {
    let content = formData.content
    if (!!formData.name) {
      content = updateOrAddYamlField(content, 'name', formData.name)
    }
    if (!!formData.description) {
      content = updateOrAddYamlField(content, 'description', formData.description)
    }
    setFormData(prev => ({
      ...prev,
      content
    }))
  }, [formData.name, formData.description])

  return (
    <Dialog.Root
        open={open}
        onOpenChange={(o) => {
            if (!o) {
                onClose?.()
            }
        }}
    >
        <Dialog.Portal>
            <Dialog.Content 
                className="flex flex-col bg-white rounded-md shadow-lg fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] h-[90%] p-6 animate-[contentShow_150ms_cubic-bezier(0.16,1,0.3,1)]"
                aria-describedby={undefined}
            >
                <div className="flex flex-row justify-between items-center">
                    <Dialog.Title className="flex flex-1 font-semibold text-gray-900 text-[17px]">{!skillName ? '新建技能' : isReadOnly ? '查看技能' : '编辑技能'}</Dialog.Title>
                    <div className="flex flex-row gap-4">
                        {!isReadOnly && (
                            <button
                                type="submit"
                                form="skillForm"
                                disabled={saving}
                                className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gray-900 hover:bg-gray-800 rounded-lg disabled:opacity-50 transition-colors"
                            >
                                <Save className="w-4 h-4" />
                                {saving ? '保存中...' : '保存'}
                            </button>
                        )}
                        <Dialog.Close asChild>
                            <button 
                                className="rounded-full flex justify-center items-center text-[rgba(0,0,0,0.45)] hover:text-[rgba(0,0,0,0.6)]" 
                                aria-label="Close"
                            >
                                <XCircle className="w-5 h-5"/>
                            </button>
                        </Dialog.Close>
                    </div>
                </div>
                {/* 主内容区 - 左右分栏 */}
                <div className="flex-1 flex overflow-hidden mt-4 gap-4">
                    {/* 左侧：Markdown 编辑区 */}
                    <Form.Root 
                        id="skillForm"
                        onSubmit={async (e) => {
                            e.preventDefault();
                            const formData = new FormData(e.currentTarget)
                            const data = Object.fromEntries(formData)
                            await handleSubmit(data)
                        }}
                        className="flex flex-col flex-1 gap-4 overflow-auto"
                    >
                        <FormInput 
                            name="name"
                            label="名称（创建后不可修改）"
                            errorMessages={[
                                { match:"valueMissing", content:"请先输入技能名称" }
                            ]}
                            placeholder="技能名称"            
                            value={formData.name}
                            setValue={(value: string) => {
                            setFormData(prev => ({
                                ...prev,
                                name: value
                            }))
                            }}
                            disabled={!!skillName || isReadOnly}
                        />
                        <FormInput 
                            name="description"
                            label="描述"
                            errorMessages={[
                            { match:"valueMissing", content:"请先输入技能描述" }
                            ]}
                            placeholder="技能描述"
                            isTextarea={true}
                            value={formData.description}
                            setValue={(value: string) => {
                            setFormData(prev => ({
                                ...prev,
                                description: value
                            }))
                            }}
                            disabled={isReadOnly}
                        />
                        <FormInput 
                            name="content"
                            label="详细内容（Markdown）"
                            errorMessages={[
                            { match:"valueMissing", content:"请先输入详细内容" }
                            ]}
                            placeholder="详细内容"
                            isTextarea={true}
                            isFlexMax={true}
                            value={formData.content}
                            setValue={(value: string) => {
                            setFormData(prev => ({
                                ...prev,
                                content: value
                            }))
                            }}
                            disabled={isReadOnly}
                        />
                    </Form.Root>

                    {/* 右侧：脚本管理区 */}
                    <div className="w-80 flex flex-col bg-gray-50 overflow-auto">
                        {/* 当前技能的脚本 */}
                        <div className="p-4 border-b border-gray-200">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                <FileCode className="w-4 h-4" />
                                脚本文件
                            </h3>
                            
                            {scripts.length === 0 ? (
                                <p className="text-xs text-gray-500">暂无脚本，可从下方拖拽工具添加</p>
                            ) : (
                            <div className="space-y-2">
                                {/* 已保存的脚本 */}
                                {scripts.map((script) => (
                                    <div
                                        key={`${script.server_name}/${script.name}`}
                                        className="flex items-center gap-2 p-2 rounded-lg bg-white border border-gray-200 group"
                                    >
                                        <FileCode className="w-4 h-4 text-green-600 shrink-0" />
                                        <span className="flex-1 text-sm text-gray-700 truncate">{script.name}</span>
                                        <button
                                            onClick={() => handleDeleteScript(script.name, script.server_name)}
                                            className="p-1.5 hover:bg-red-100 rounded transition-all"
                                            title="删除脚本"
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
                                className={`mb-4 p-4 border-2 border-dashed rounded-lg text-center transition-colors 
                                    ${dragOverScript ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white"}`}
                            >
                                <p className="text-sm text-gray-500">
                                    {dragOverScript ? "释放以添加工具" : "拖拽工具到这里"}
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
                                            draggable={!isReadOnly}
                                            onDragStart={(e) => handleToolDragStart(e, tool)}
                                            className={`flex items-center gap-2 p-2 rounded-lg border border-gray-200 transition-colors group 
                                            ${isReadOnly ? "bg-disabled cursor-not-allowed" : "bg-white cursor-grab hover:border-gray-400"}`}
                                        >
                                            <GripVertical className="w-4 h-4 text-gray-400 shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-gray-700 truncate">{tool.name}</p>
                                                <p className="text-xs text-gray-500 truncate">{tool.server_name}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </Dialog.Content>
        </Dialog.Portal>
	</Dialog.Root>
  )
}

export default SkillConfigureModal
