'use client';

import { OutputFile } from '@/types/message';
import { User } from 'lucide-react';
import FilePreview from '@/components/ui/filePreview';

interface IProps {
    content?: string;
    files?: OutputFile[]
}

const UserItem: React.FC<IProps> = (props) => {
    const { content = '', files } = props;
    
    return (
        <div className="flex gap-3 justify-end">
            {/* Content */}
            <div className="max-w-[80%]">
                <div className="bg-gray-700 text-white rounded-2xl rounded-tr-sm px-4 py-3">
                    {content && (
                        <p className="text-sm leading-relaxed">{content}</p>
                    )}
                    {files && files.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                            {files.map((file, index) => (
                                <div key={index} onClick={(e) => e.stopPropagation()}>
                                    <FilePreview url={file.file_url} filename={file.file_name} />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            
            {/* Avatar */}
            <div className="shrink-0">
                <div className="w-8 h-8 rounded-xl bg-gray-700 flex items-center justify-center">
                    <User className="w-5 h-5 text-white" />
                </div>
            </div>
        </div>
    );
};

export default UserItem;
