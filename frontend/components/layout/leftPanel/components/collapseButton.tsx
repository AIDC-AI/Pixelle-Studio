import { ChevronLeft, ChevronRight } from 'lucide-react';

interface IProps {
    isCollapsed?: boolean;
    onClick?: () => void
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