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

import { MouseEventHandler, ReactNode } from "react";

interface IProps {
    isCollapsed?: boolean
    isActive?: boolean
    onClick?: MouseEventHandler<HTMLButtonElement>
    children?: ReactNode
    className?: string
}

const TabButton: React.FC<IProps> = (props) => {
    const { isCollapsed = false, isActive = false, onClick = () => {}, children, className } = props;

    return <button
        onClick={onClick}
        className={`${className} ${isCollapsed ? "p-2" : "flex-1 flex items-center justify-center gap-2 px-4 py-2"} rounded-lg transition-colors hover:text-white! hover:bg-red-500! ${
            isActive ? 'bg-black text-white' : 'bg-gray-50 text-gray-600'
        }`}
    >
        {children}
    </button>
}

export default TabButton