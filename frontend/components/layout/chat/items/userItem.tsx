'use client';

import { User } from 'lucide-react';

interface IProps {
    content?: string;
}

const UserItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    return (
        <div className="flex gap-3 justify-end">
            {/* Content */}
            <div className="max-w-[80%]">
                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-lg shadow-blue-500/25">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
                </div>
            </div>
            
            {/* Avatar */}
            <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center">
                    <User className="w-5 h-5 text-slate-600" />
                </div>
            </div>
        </div>
    );
};

export default UserItem;
