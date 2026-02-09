import { FormErrorMessage } from "@/types/form"
import { useMemo } from "react"
import FormBase from "./base"

interface IProps {
    name: string
    label: string
    errorMessages?: FormErrorMessage[]
    required?: boolean
    disabled?: boolean
    placeholder?: string
    isTextarea?: boolean // Whether to render as textarea
    isFlexMax?: boolean // Whether to fill remaining space
    value?: string
    setValue?: (value: string) => void
}

const FormInput: React.FC<IProps> = (props) => {
    const {
        name,
        label,
        errorMessages,
        required = true,
        disabled,
        placeholder = 'Please enter',
        isTextarea = false,
        isFlexMax = false,
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
                value,
                onChange: handleChange
            }
        return null
    }, [placeholder, value, setValue])

    return (
        <FormBase
            name={name}
            label={label}
            errorMessages={errorMessages}
            required={required}
            disabled={disabled}
            isFlexMax={isFlexMax}
        >
            {
                isTextarea ? 
                <textarea {...controlProps} /> :
                <input {...controlProps} />
            }
        </FormBase>
    )
}

export default FormInput