import { Wrench } from "lucide-react"
import BottomButton from "./components/bottomButton"
import { useEffect, useState } from "react"
import { Skill } from "@/types/skill";
import { api } from "@/lib/api";
import { Skeleton } from "antd";
import ItemWithTrash from "@/components/ui/itemWithTrash";
import Description from "@/components/ui/desctiption";
import SkillConfigureModal from "@/components/ui/skillConfigureModal";

const SkillsPanel = () => {
    const [loading, setLoading] = useState<boolean>(false);
    const [skills, setSkills] = useState<Skill[]>([])
    const [open, setOpen] = useState<boolean>(false);
    const [selectedIndex, setSelectedIndex] = useState<number>(-1)

    const handleGetSkills = async () => {
        setLoading(true);

        try {
            const response = await api.getSkills();
            setSkills(response)
        } catch (error) {
            console.error(`Failed to fetch skills:`, error);
        }

        setLoading(false);
    };

    const handleDeleteSkill = async (name: string) => {
        if (!name || name === '') 
            return
        try {
            const response = await api.deleteSkill(name)
            if (response) {
                handleGetSkills()
            }
        }
        catch (error) {
            console.error(`Failed to delete skill ${name}:`, error);
        }
    }

    useEffect(() => {
        handleGetSkills()
    }, [])

    return <div className="left-panel">
        <div className="flex-1 overflow-y-auto space-y-2 p-4">
            <h3 className="font-title text-text-default">能力列表</h3>
            <div className="flex-1 space-y-2">
                {
                    loading ? <Skeleton /> : <>
                        {
                            skills?.map((skill, index) => (
                                <ItemWithTrash
                                    key={`${skill.name}-${index}`}
                                    // selected={selectedIndex === index}
                                    onItem={(e) => {
                                        e.stopPropagation()
                                        setSelectedIndex(index)
                                        setOpen(true)
                                    }}
                                    onTrash={(e) => {
                                        e.stopPropagation()
                                        handleDeleteSkill(skill.name)
                                    }}
                                >
                                    <div className="flex flex-col">
                                        <span className="font-default text-text-default">{skill.name}</span>
                                        <Description 
                                            description={skill.description} 
                                        />
                                    </div>
                                </ItemWithTrash>
                            ))
                        }
                    </>
                }
            </div>
        </div>

        {/* Footer */}
        <BottomButton 
            text={"能力管理"}
            icon={<Wrench className="w-4 h-4" />}
            onClick={() => {
                    setSelectedIndex(-1)
                    setOpen(true)
                }
            }
        />

        <SkillConfigureModal 
            open={open}
            setOpen={setOpen}
            setSelectedIndex={setSelectedIndex}
            skillName={skills?.[selectedIndex]?.name}
            reload={handleGetSkills}
        />
    </div>
}

export default SkillsPanel