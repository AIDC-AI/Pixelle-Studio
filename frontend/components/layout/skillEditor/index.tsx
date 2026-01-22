// import { useEffect, useState } from 'react'
// import { X, Save, Upload, Trash2, FileCode, Link, GripVertical, Plus, ArrowUpRight, Play } from 'lucide-react'
// import { ToastType, useApp } from '@/context'
// import { MCPTool } from '@/types/server'
// import { skillAPI } from '@/lib/skillApi'
// import { Form } from "radix-ui";
// import { capitalize, updateOrAddYamlField } from '@/utils/utils'
// import FormInput from '@/components/ui/form/input'

// interface Script {
//   name: string
//   server_name?: string
// }

// const SkillEditor = () => {
//   const {  
//     user, 
//     setSkillEditored, 
//     currentSkillName, 
//     setCurrentSkillName,
//     mcpTools, 
//     setIsChangeSkill,
//     showToast
//   } = useApp()

//   // 初始化表单数据
//   const [formData, setFormData] = useState({
//     name: '',
//     description: '',
//     content: ''
//   });

//   // 脚本列表
//   const [scripts, setScripts] = useState<Script[]>([])

//   // 拖拽状态
//   const [dragOverScript, setDragOverScript] = useState<boolean>(false)
  
//   // 保存状态
//   const [saving, setSaving] = useState<boolean>(false)
  
//   // 只读模式（共享技能）
//   const [isReadOnly, setIsReadOnly] = useState<boolean>(false)

//   const handleClose = () => {
//     setSkillEditored(false)
//     setCurrentSkillName(null)
//   }

//   const handleClear = () => {
//     setFormData({
//       name: "",
//       description: "",
//       content: ""
//     })
//     setIsReadOnly(false)
//     setScripts([])
//   }

//   const handleGetSkillData = async () => {
//     if (!!currentSkillName) {
//       const res = await skillAPI.getSkill(currentSkillName, user?.uid)
//       if (!!res) {
//         setFormData({
//           name: res.name,
//           description: res.meta.description,
//           content: res.content
//         })
//         setIsReadOnly(!!res.meta.is_default)
//         // 不是default的skill才需要获取scripts
//         if (!res.meta.is_default) {
//           getScriptsFromSkill(res.content)
//         }
//       }
//     } else {
//       handleClear()
//     }
//   }

//   // 从skill中获取scripts
//   const getScriptsFromSkill = (content: string) => {
//     // 修改正则以支持路径格式，如 # test/i_crop-start #
//     const regex = /#\s*([\w\-/]+)-start\s*#/g;
//     const matches = [...content.matchAll(regex)];
//     if (!!matches?.[0]?.[1]) {
//       const splitArr = matches[0][1].split('/')
//       setScripts(mcpTools?.filter((tool) => tool.server_name === splitArr?.[0] && tool.name === splitArr?.[1])?.map((tool) => ({
//         name: tool.name,
//         server_name: tool.server_name
//       })) || [])
//     }
//   }

//   // 处理文件上传
//   const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
//     // if (!e.target.files || e.target.files.length === 0) return
    
//     // const file = e.target.files[0]
//     // const reader = new FileReader()
    
//     // reader.onload = (event) => {
//     //   const fileContent = event.target?.result as string
      
//     //   // 如果是 Markdown 文件，解析它
//     //   if (file.name.endsWith('.md')) {
//     //     // 尝试解析 front matter
//     //     if (fileContent.startsWith('---')) {
//     //       const parts = fileContent.split('---')
//     //       if (parts.length >= 3) {
//     //         const frontMatter = parts[1].trim()
//     //         const bodyContent = parts.slice(2).join('---').trim()
            
//     //         // 解析 front matter
//     //         frontMatter.split('\n').forEach(line => {
//     //           const [key, value] = line.split(':').map(s => s.trim())
//     //         })
            
//     //         setContent(bodyContent)
//     //         return
//     //       }
//     //     }
//     //     setContent(fileContent)
//     //   } else {
//     //     // 其他文件作为内容附加
//     //     setContent(prev => prev + '\n\n```\n' + fileContent + '\n```')
//     //   }
//     // }
    
//     // reader.readAsText(file)
//     // e.target.value = '' // 清空 input
//   }

//   // 处理 MCP Tool 拖拽
//   const handleToolDragStart = (e: React.DragEvent, tool: MCPTool) => {
//     if (isReadOnly)
//       return
//     e.dataTransfer.setData('application/json', JSON.stringify(tool))
//     e.dataTransfer.effectAllowed = 'copy'
//   }

//   const handleDragOver = (e: React.DragEvent) => {
//     e.preventDefault()
//     setDragOverScript(true)
//   }

//   const handleDragLeave = () => {
//     setDragOverScript(false)
//   }

//   const handleDrop = async (e: React.DragEvent) => {
//     e.preventDefault()
//     setDragOverScript(false)
    
//     try {
//       const toolData = e.dataTransfer.getData('application/json')
//       if (!toolData) return
      
//       const tool: MCPTool = JSON.parse(toolData)

//       const topics = []
//       if (!!tool?.inputSchema?.properties) {
//         for (const key in tool.inputSchema.properties) {
//           if (!!tool.inputSchema.properties[key]) {
//             topics.push({
//               name: key,
//               label: `This Is A ${capitalize(tool.inputSchema.properties[key]?.type)}`
//             })
//           }
//         }
//       }
//       const topicStr = topics?.length > 0 ? topics.reduce<string>((total, topic) => `${total}${total === "" ? "" : ","}${topic.name}:${topic.label}`, "") : ""
//       // 在内容中插入工具占位符
//       const placeholderStart = `# ${tool.server_name}/${tool.name}-start #`
//       const placeholderEnd = `# ${tool.server_name}/${tool.name}-end #`
//       setFormData(prev => ({
//         ...prev,
//         content:prev.content + `\n\n${placeholderStart}\ncall_tool('${tool.name}', {${topicStr}})\n${placeholderEnd}`
//       }))
//       setScripts(prev => [...prev, {
//         name: tool.name,
//         server_name: tool.server_name
//       }])
//     } catch (e) {
//       console.error('处理拖拽失败:', e)
//     }
//   }

//   // 删除脚本
//   const handleDeleteScript = async (scriptName: string, scriptServerName?: string) => {
//     const name = !!scriptServerName ? `${scriptServerName}/${scriptName}` : scriptName
//     // 转义特殊字符（如 /）
//     const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    
//     // 删除整个块，支持路径格式如 test/i_crop
//     const regex = new RegExp(
//       `#\\s*${escapedName}-start\\s*#[\\s\\S]*?#\\s*${escapedName}-end\\s*#`,
//       'g'
//     ); 
//     setFormData(prev => ({
//         ...prev,
//         content: prev.content
//         .replace(regex, '')  // 删除块
//       })
//     );
//     setScripts(prev => prev.filter((script) => scriptServerName ? (script.name !== scriptName && script.server_name !== scriptServerName) : script.name !== scriptName))
//   }
  
//   const handleSubmit = async (data: { [x: string]: FormDataEntryValue; name?: any; description?: any; content?: any }): Promise<string | null> => {
//     try {
//       setSaving(true)
//       if (!!currentSkillName) {
//         // 更新：使用原名称作为第一个参数
//         await skillAPI.updateSkill(currentSkillName, {
//           description: data.description,
//           content: data.content
//         }, user?.uid)
//         showToast(ToastType.SUCCESS, "更新成功！")
//       } else {
//         // 创建
//         await skillAPI.createSkill({
//           name: data.name,
//           description: data.description,
//           content: data.content
//         }, user?.uid)
//         showToast(ToastType.SUCCESS, "添加成功！")
//       }
//       setSkillEditored(false)
//       setIsChangeSkill(true)
//       return null
//     } catch (e) {
//       console.error('保存请求失败:', e)
//       showToast(ToastType.ERROR, (e as Error).message || '保存失败！')
//       return null
//     } finally {
//       setSaving(false)
//     }
//   }

//   useEffect(() => {
//     handleGetSkillData()
//   }, [currentSkillName])

//   useEffect(() => {
//     let content = formData.content
//     if (!!formData.name) {
//       content = updateOrAddYamlField(content, 'name', formData.name)
//     }
//     if (!!formData.description) {
//       content = updateOrAddYamlField(content, 'description', formData.description)
//     }
//     setFormData(prev => ({
//       ...prev,
//       content
//     }))
//   }, [formData.name, formData.description])

//   return (
//     <div className="flex flex-col min-w-150 max-w-150 shrink-0 h-full bg-white">
//       {/* 顶部栏 */}
//       <div className="flex items-center justify-between p-4 border-b border-gray-200">
//         <div className="flex items-center gap-2">
//           <h2 className="text-lg font-semibold text-gray-800">
//             {!currentSkillName ? '新建技能' : isReadOnly ? '查看技能' : '编辑技能'}
//           </h2>
//           {isReadOnly && (
//             <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">共享技能（只读）</span>
//           )}
//         </div>
//         <div className="flex items-center gap-2">
//           {/* 上传文件 */}
//           {/* {!isReadOnly && (
//             <label className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer transition-colors">
//               <Upload className="w-4 h-4" />
//               上传文件
//               <input
//                 type="file"
//                 accept=".md,.txt,.py,.sh"
//                 onChange={handleFileUpload}
//                 className="hidden"
//               />
//             </label>
//           )} */}
          
//           {/* 测试按钮 */}
//           {/* <button
//             onClick={handleTest}
//             disabled={!name.trim() || !onTest}
//             className="flex items-center gap-2 px-3 py-2 text-sm text-green-700 bg-green-100 hover:bg-green-200 rounded-lg disabled:opacity-50 transition-colors"
//           >
//             <Play className="w-4 h-4" />
//             测试
//           </button> */}
          
        //   {!isReadOnly && (
        //     <button
        //       type="submit"
        //       form="skillForm"
        //       disabled={saving}
        //       className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gray-900 hover:bg-gray-800 rounded-lg disabled:opacity-50 transition-colors"
        //     >
        //       <Save className="w-4 h-4" />
        //       {saving ? '保存中...' : '保存'}
        //     </button>
        //   )}
          
//           <button
//             onClick={handleClose}
//             className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
//           >
//             <X className="w-5 h-5 text-gray-500" />
//           </button>
//         </div>
//       </div>

//       {/* 主内容区 - 左右分栏 */}
//       <div className="flex-1 flex overflow-hidden">
//         {/* 左侧：Markdown 编辑区 */}
//         <Form.Root 
//           id="skillForm"
//           onSubmit={async (e) => {
//             e.preventDefault();
//             const formData = new FormData(e.currentTarget)
//             const data = Object.fromEntries(formData)
//             await handleSubmit(data)
//           }}
//           className="flex flex-col flex-1 gap-4 p-4 border-r border-gray-200 overflow-auto"
//         >
//           <FormInput 
//             name="name"
//             label="名称（创建后不可修改）"
//             errorMessages={[
//               { match:"valueMissing", content:"请先输入技能名称" }
//             ]}
//             placeholder="技能名称"            
//             value={formData.name}
//             setValue={(value: string) => {
//               setFormData(prev => ({
//                 ...prev,
//                 name: value
//               }))
//             }}
//             disabled={!!currentSkillName || isReadOnly}
//           />
//           <FormInput 
//             name="description"
//             label="描述"
//             errorMessages={[
//               { match:"valueMissing", content:"请先输入技能描述" }
//             ]}
//             placeholder="技能描述"
//             isTextarea={true}
//             value={formData.description}
//             setValue={(value: string) => {
//               setFormData(prev => ({
//                 ...prev,
//                 description: value
//               }))
//             }}
//             disabled={isReadOnly}
//           />
//           <FormInput 
//             name="content"
//             label="详细内容（Markdown）"
//             errorMessages={[
//               { match:"valueMissing", content:"请先输入详细内容" }
//             ]}
//             placeholder="详细内容"
//             isTextarea={true}
//             isFlexMax={true}
//             value={formData.content}
//             setValue={(value: string) => {
//               setFormData(prev => ({
//                 ...prev,
//                 content: value
//               }))
//             }}
//             disabled={isReadOnly}
//           />
//         </Form.Root>

//         {/* 右侧：脚本管理区 */}
//         <div className="w-80 flex flex-col bg-gray-50 overflow-auto">
//           {/* 当前技能的脚本 */}
//           <div className="p-4 border-b border-gray-200">
//             <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
//               <FileCode className="w-4 h-4" />
//               脚本文件
//             </h3>
            
//             {scripts.length === 0 ? (
//               <p className="text-xs text-gray-500">暂无脚本，可从下方拖拽工具添加</p>
//             ) : (
//               <div className="space-y-2">
//                 {/* 已保存的脚本 */}
//                 {scripts.map((script) => (
//                   <div
//                     key={`${script.server_name}/${script.name}`}
//                     className="flex items-center gap-2 p-2 rounded-lg bg-white border border-gray-200 group"
//                   >
//                     <FileCode className="w-4 h-4 text-green-600 shrink-0" />
//                     <span className="flex-1 text-sm text-gray-700 truncate">{script.name}</span>
//                     <button
//                       onClick={() => handleDeleteScript(script.name, script.server_name)}
//                       className="p-1.5 hover:bg-red-100 rounded transition-all"
//                       title="删除脚本"
//                     >
//                       <Trash2 className="w-3.5 h-3.5 text-red-500" />
//                     </button>
//                   </div>
//                 ))}
//               </div>
//             )}
//           </div>

//           {/* MCP Tools 拖拽区 */}
//           <div className="flex-1 p-4 overflow-auto">
//             <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
//               <Link className="w-4 h-4" />
//               可用工具 (MCP)
//             </h3>
//             <p className="text-xs text-gray-500 mb-3">
//               拖拽工具到左侧内容区，自动生成调用脚本
//             </p>
            
//             {/* 拖拽目标区域 */}
//             <div
//               onDragOver={handleDragOver}
//               onDragLeave={handleDragLeave}
//               onDrop={handleDrop}
//               className={`mb-4 p-4 border-2 border-dashed rounded-lg text-center transition-colors 
//                 ${dragOverScript ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white"}`}
//             >
//               <p className="text-sm text-gray-500">
//                 {dragOverScript ? "释放以添加工具" : "拖拽工具到这里"}
//               </p>
//             </div>
            
//             {/* MCP Tools 列表 */}
//             {mcpTools?.length === 0 ? (
//               <p className="text-xs text-gray-500">暂无可用工具</p>
//             ) : (
//               <div className="space-y-2">
//                 {mcpTools?.map((tool, index) => (
//                   <div
//                     key={`${tool.server_id}-${tool.name}-${index}`}
//                     draggable={!isReadOnly}
//                     onDragStart={(e) => handleToolDragStart(e, tool)}
//                     className={`flex items-center gap-2 p-2 rounded-lg border border-gray-200 transition-colors group 
//                       ${isReadOnly ? "bg-disabled cursor-not-allowed" : "bg-white cursor-grab hover:border-gray-400"}`}
//                   >
//                     <GripVertical className="w-4 h-4 text-gray-400 shrink-0" />
//                     <div className="flex-1 min-w-0">
//                       <p className="text-sm text-gray-700 truncate">{tool.name}</p>
//                       <p className="text-xs text-gray-500 truncate">{tool.server_name}</p>
//                     </div>
//                   </div>
//                 ))}
//               </div>
//             )}
//           </div>
//         </div>
//       </div>
//     </div>
//   )
// }

// export default SkillEditor
