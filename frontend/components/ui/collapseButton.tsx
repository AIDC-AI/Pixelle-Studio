/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { MouseEventHandler } from 'react';

interface IProps {
    isCollapsed?: boolean;
    onClick?: MouseEventHandler<HTMLButtonElement>
}

const CollaspeButton: React.FC<IProps> = (props) => {
    const { isCollapsed = false, onClick = () => {} } = props;

    return <button
        onClick={onClick}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
    >
        {
            isCollapsed ? <ChevronRight className="w-5 h-5 text-gray-600" /> : <ChevronLeft className="w-5 h-5 text-gray-600" />
        } 
    </button>
}

export default CollaspeButton