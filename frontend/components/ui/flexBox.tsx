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

interface IProps {
    title?: string;
    isFlex?: boolean;
    isSelected?: boolean;
    onSelect?: () => void;
    children?: React.ReactNode;
}

const FlexBox: React.FC<IProps> = (props) => {
    const { title = '', isFlex = true, isSelected = false, onSelect, children } = props;

    return (
        <div
            onClick={() => {
                onSelect?.();
            }}
            className={`p-4 rounded-lg border hover:border-blue-500 cursor-pointer transition-all flex justify-center items-center ${isSelected
                ? isFlex ? 'grow border-blue-500' : 'border-blue-500'
                : 'border-gray-300'
                }`}
        >
            {
                isFlex && isSelected ? <div className="w-full h-full flex flex-col gap-8 justify-start items-center">
                    <div className="text-lg font-bold">
                        {
                            title
                        }
                    </div>
                    <div className="flex-1 w-full">
                        {
                            children
                        }
                    </div>
                </div> : <div className="text-lg font-bold">{title}</div>
            }
        </div>
    )
}

export default FlexBox;