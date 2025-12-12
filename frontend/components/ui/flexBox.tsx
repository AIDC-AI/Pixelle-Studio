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
            className={`p-4 rounded-lg border-1 hover:border-blue-500 cursor-pointer transition-all flex justify-center items-center ${isSelected
                ? isFlex ? 'flex-grow border-blue-500' : 'border-blue-500'
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
                    <div className="flex-1">
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