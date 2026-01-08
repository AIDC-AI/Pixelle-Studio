import { FormErrorMessage } from "@/types/form"
import { Form } from "radix-ui"
import { useMemo } from "react"

interface IProps {
    name: string
    label: string
    errorMessages?: FormErrorMessage[]
    placeholder?: string
    required?: boolean
    isTextarea?: boolean // 是否是textarea
    isFlexMax?: boolean // 是否撑满剩余空间
    disabled?: boolean
    value?: string
    setValue?: (value: string) => void
}

const FormInput: React.FC<IProps> = (props) => {
    const {
        name,
        label,
        errorMessages,
        placeholder = '请输入',
        required = true,
        isTextarea = false,
        isFlexMax = false,
        disabled,
        value,
        setValue
    } = props

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setValue?.(e.target.value)
    }

    const controlProps = useMemo(() => {
        if (value !== null && value !== undefined && !!setValue) 
            return {
                placeholder,
                required,
                disabled,
                className: `w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${isFlexMax ? "flex-1" : ""}`,
                value,
                onChange: handleChange
            }

        return {
            placeholder,
            required,
            disabled,
            className: `w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${isFlexMax ? "flex-1" : ""}`
        }
    }, [placeholder, required, isFlexMax, disabled, value, setValue])

    return (
        <Form.Field name={name} className={`${isFlexMax ? "flex flex-col flex-1" : ""}`}>
            <div className='flex flex-col justify-between items-baseline gap-1 mb-1'>
                <Form.Label className="text-sm font-medium text-gray-700">{label}</Form.Label>
                {
                    errorMessages?.map((message, index) => <Form.Message 
                        key={`error-${index}`}
                        className="text-xs font-medium text-red-500" 
                        match={message.match}
                    >
                        {message.content}
                    </Form.Message>)
                }
            </div>
            <Form.Control asChild>
                {
                    isTextarea ? 
                    <textarea {...controlProps} /> :
                    <input {...controlProps} />
                }
            </Form.Control>
        </Form.Field>
    )
}

export default FormInput