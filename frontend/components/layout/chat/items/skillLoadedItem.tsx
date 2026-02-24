// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client';

import { BookOpen, Zap } from 'lucide-react';

interface IProps {
    skillName: string;
}

const SkillLoadedItem: React.FC<IProps> = (props) => {
    const { skillName } = props;

    return (
        <div 
            className="flex items-center gap-2 px-3 py-2 bg-gray-100 border border-gray-200 rounded-lg"
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)' }}
        >
            <div className="flex items-center justify-center w-6 h-6 rounded bg-gray-300 text-gray-600">
                <BookOpen className="w-3 h-3" />
            </div>
            <div className="flex-1">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-600">
                        Skill Loaded
                    </span>
                    <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 text-xs">
                        <Zap className="w-2.5 h-2.5" />
                        {skillName}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default SkillLoadedItem;
