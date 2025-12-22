'use client';

import { BookOpen, Zap } from 'lucide-react';

interface IProps {
    skillName: string;
}

const SkillLoadedItem: React.FC<IProps> = (props) => {
    const { skillName } = props;

    return (
        <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500/20 text-amber-600">
                <BookOpen className="w-4 h-4" />
            </div>
            <div className="flex-1">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-amber-800">
                        技能已加载
                    </span>
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-200/60 text-amber-700 text-xs font-medium">
                        <Zap className="w-3 h-3" />
                        {skillName}
                    </span>
                </div>
                <p className="text-xs text-amber-600 mt-0.5">
                    正在使用专业技能指导执行任务
                </p>
            </div>
        </div>
    );
};

export default SkillLoadedItem;

