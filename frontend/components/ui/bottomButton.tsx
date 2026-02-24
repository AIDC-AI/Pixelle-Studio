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

import { MouseEventHandler } from "react"

interface IProps {
    text?: string
    icon?: React.ReactNode
    onClick?: MouseEventHandler<HTMLButtonElement>
}

const BottomButton: React.FC<IProps> = (props) => {
    const { text = '', icon, onClick = () => {} } = props

    return <div className="p-4 border-t border-gray-200">
        <button 
            onClick={onClick}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-gray-400 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
        >
            {icon}
            <span className="text-sm">{text}</span>
        </button>
    </div>
}

export default BottomButton