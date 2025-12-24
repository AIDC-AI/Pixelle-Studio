'use client';

import { UserFile } from '@/types/message';
import { User } from 'lucide-react';
import FilePreview from '@/components/ui/filePreview';

interface IProps {
    content?: string;
    files?: UserFile[]
}

const UserItem: React.FC<IProps> = (props) => {
    const { content = '', files } = props;
    
    return (
        <div className="flex gap-3 justify-end">
            {/* Content */}
            <div className="max-w-[80%]">
                <div className="bg-linear-to-br from-blue-500 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-lg shadow-blue-500/25">
                    {content && (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
                    )}
                    {files && files.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                            {files.map((file, index) => (
                                <div key={index} onClick={(e) => e.stopPropagation()}>
                                    <FilePreview url={file.url} filename={file.name} />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            
            {/* Avatar */}
            <div className="shrink-0">
                <div className="w-8 h-8 rounded-xl bg-linear-to-br from-slate-200 to-slate-300 flex items-center justify-center">
                    <User className="w-5 h-5 text-slate-600" />
                </div>
            </div>
        </div>
    );
};

export default UserItem;
