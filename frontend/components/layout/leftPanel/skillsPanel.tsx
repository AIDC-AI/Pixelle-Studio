import { Wrench } from "lucide-react"

const SkillsPanel = () => {
    return <div className="p-4 flex flex-col h-full">
        <h3 className="text-xs font-medium text-gray-500 mb-3 px-2">能力列表</h3>
        <div className="flex-1 overflow-y-auto">
            {/* {skill.map((skill) => (
            <div
                key={skill.id}
                className="p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 cursor-pointer transition-all"
            >
                <div className="flex items-start gap-3">
                <span className="text-2xl">{skill.icon}</span>
                <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-800 mb-1">{skill.name}</h4>
                    <p className="text-xs text-gray-500 leading-relaxed">{skill.description}</p>
                </div>
                </div>
            </div>
            ))} */}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
            <button className="w-full flex items-center gap-2 px-4 py-2.5 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors">
                <Wrench className="w-4 h-4" />
                <span className="text-sm">能力管理</span>
            </button>
        </div>
    </div>
}

export default SkillsPanel