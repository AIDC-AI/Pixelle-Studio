'use client'

interface IProps {
    width?: number | string
    className?: string
}

const Logo: React.FC<IProps> = ({ width = "232", className = "" }) => {
    return (
        <img 
            src="/logo.png"
            alt="Pixelle.Studio"
            className={`w-[${width}px] h-auto object-contain ${className}`}
        />
    )
}

export default Logo;