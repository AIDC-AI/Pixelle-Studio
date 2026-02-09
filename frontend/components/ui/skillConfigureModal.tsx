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

  // Initialize form data
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: ''
  });

  // Script list
  const [scripts, setScripts] = useState<Script[]>([])

  // Drag state
  const [dragOverScript, setDragOverScript] = useState<boolean>(false)
  
  // Save state
  const [saving, setSaving] = useState<boolean>(false)
  
  // Read-only mode (shared skills)
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
        // Only non-default skills need to fetch scripts
        if (!res.meta.is_default) {
          getScriptsFromSkill(res.content)
        }
      }
    } else {
      handleClear()
    }
  }

  // Get scripts from skill
  const getScriptsFromSkill = (content: string) => {
    // Modify regex to support path format, e.g. # test/i_crop-start #
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

  // Handle MCP Tool drag
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
      // Insert tool placeholder in content
      const placeholderStart = `# ${tool.server_name}/${tool.name}-start #`
      const placeholderEnd = `# ${tool.server_name}/${tool.name}-end #`
      
      // Build tool description (if available)
      const descriptionComment = tool.description 
        ? `# ${tool.description}\n` 
        : ''
      
      setFormData(prev => ({
        ...prev,
        content:prev.content + `\n\n${placeholderStart}\n${descriptionComment}call_tool('${tool.name}', {${topicStr}})\n${placeholderEnd}`
      }))
      setScripts(prev => [...prev, {
        name: tool.name,
        server_name: tool.server_name
      }])
    } catch (e) {
      console.error('Drag failed:', e)
    }
  }

  // Delete script
  const handleDeleteScript = async (scriptName: string, scriptServerName?: string) => {
    const name = !!scriptServerName ? `${scriptServerName}/${scriptName}` : scriptName
    // Escape special characters (e.g. /)
    const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    
    // Delete entire block, supports path format like test/i_crop
    const regex = new RegExp(
      `#\\s*${escapedName}-start\\s*#[\\s\\S]*?#\\s*${escapedName}-end\\s*#`,
      'g'
    ); 
    setFormData(prev => ({
        ...prev,
        content: prev.content
        .replace(regex, '')  // Remove block
      })
    );
    setScripts(prev => prev.filter((script) => scriptServerName ? (script.name !== scriptName || script.server_name !== scriptServerName) : script.name !== scriptName))
  }
  
  const handleSubmit = async (data: { [x: string]: FormDataEntryValue; name?: any; description?: any; content?: any }): Promise<string | null> => {
    try {
      setSaving(true)
      if (!!skillName) {
        // Update: use original name as first parameter
        await skillAPI.updateSkill(skillName, {
          description: data.description,
          content: data.content
        }, user?.uid)
        showToast(ToastType.SUCCESS, "Update successful!")
      } else {
        // Create
        await skillAPI.createSkill({
          name: data.name,
          description: data.description,
          content: data.content
        }, user?.uid)
        showToast(ToastType.SUCCESS, "Add success!")
      }
      onSuccess?.()
      return null
    } catch (e) {
      console.error('Save request failed:', e)
      showToast(ToastType.ERROR, (e as Error).message || 'Save failed!')
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
                className="flex flex-col bg-white rounded-md shadow-lg fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] h-[90%] p-6 animate-[contentShow_150ms_cubic-bezier(0.16,1,0.3,1)] z-999"
                aria-describedby={undefined}
            >
                <div className="flex flex-row justify-between items-center">
                    <Dialog.Title className="flex flex-1 font-semibold text-gray-900 text-[17px]">{!skillName ? 'New Skill' : isReadOnly ? 'View Skill' : 'Edit Skill'}</Dialog.Title>
                    <div className="flex flex-row gap-4">
                        {!isReadOnly && (
                            <button
                                type="submit"
                                form="skillForm"
                                disabled={saving}
                                className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gray-900 hover:bg-gray-800 rounded-lg disabled:opacity-50 transition-colors"
                            >
                                <Save className="w-4 h-4" />
                                {saving ? 'Saving...' : 'Save'}
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
                {/* Main content area - left-right split */}
                <div className="flex-1 flex overflow-hidden overscroll-contain mt-4 gap-4">
                    {/* Left: Markdown editor */}
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
                            label="Name (Cannot be modified after creation)"
                            errorMessages={[
                                { match:"valueMissing", content:"Please enter the skill name" }
                            ]}
                            placeholder="Skill Name"            
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
                            label="Description"
                            errorMessages={[
                            { match:"valueMissing", content:"Please enter the skill description" }
                            ]}
                            placeholder="Skill Description"
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
                            label="Detailed Content (Markdown)"
                            errorMessages={[
                            { match:"valueMissing", content:"Please enter the detailed content" }
                            ]}
                            placeholder="Detailed Content"
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

                    {/* Right: Script management area */}
                    <div className="w-80 flex flex-col bg-gray-50 overflow-hidden">
                        {/* Current skill's scripts */}
                        <div className="pl-4 pr-2 pb-2 border-b border-gray-200">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                <FileCode className="w-4 h-4" />
                                Script Files
                            </h3>
                            
                            {scripts.length === 0 ? (
                                <p className="text-xs text-gray-500">No scripts, drag tools from below</p>
                            ) : (
                            <div 
                              className="space-y-2 max-h-[200px] overflow-auto"
                              style={{ scrollbarGutter: 'stable' }}
                            >
                                {/* Saved scripts */}
                                {scripts.map((script, index) => (
                                    <div
                                        key={`${script.server_name}-${script.name}-${index}`}
                                        className="flex items-center gap-2 p-2 rounded-lg bg-white border border-gray-200 group"
                                    >
                                        <FileCode className="w-4 h-4 text-green-600 shrink-0" />
                                        <span className="flex-1 text-sm text-gray-700 truncate">{script.name}</span>
                                        <button
                                            onClick={() => handleDeleteScript(script.name, script.server_name)}
                                            className="p-1.5 hover:bg-red-100 rounded transition-all"
                                            title="Delete script"
                                        >
                                            <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                            )}
                        </div>

                        {/* MCP Tools drag area */}
                        <div className="pt-4 px-4">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                <Link className="w-4 h-4" />
                                Available Tools (MCP)
                            </h3>
                                <p className="text-xs text-gray-500 mb-3">
                                Drag tool to the left content area, automatically generate call script
                            </p>
                            
                            {/* Drag target area */}
                            <div
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                className={`mb-4 p-4 border-2 border-dashed rounded-lg text-center transition-colors 
                                    ${dragOverScript ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white"}`}
                            >
                                <p className="text-sm text-gray-500">
                                    {dragOverScript ? "Release to add tool" : "Drag tool here"}
                                </p>
                            </div>
                      </div>
                      <div 
                        className="pl-4 pr-2 overflow-auto"
                        style={{ scrollbarGutter: 'stable' }}
                      >
                            {/* MCP Tools list */}
                            {mcpTools?.length === 0 ? (
                                <p className="text-xs text-gray-500">No available tools</p>
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
