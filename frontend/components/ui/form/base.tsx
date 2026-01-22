import { FormErrorMessage } from "@/types/form"
import { Form } from "radix-ui"
import React, { useMemo } from "react"

interface IProps {
    name: string
    label: string
    errorMessages?: FormErrorMessage[]
    required?: boolean
    disabled?: boolean
    isFlexMax?: boolean // 是否撑满剩余空间
    children?: React.ReactNode
    className?: string
}

const FormBase: React.FC<IProps> = (props) => {
    const {
        name,
        label,
        errorMessages,
        required = true,
        disabled,
        isFlexMax = false,
        children,
        className
    } = props

    const controlProps = useMemo(() => {
        // 基础样式 + 验证失败时的红色边框
        const baseClassName = `w-full rounded-lg border px-3 py-2 resize-none focus:outline-none! transition-colors
            border-gray-300 focus:ring-0! focus:ring-blue-500 focus:border-blue-500
            data-[invalid]:border-red-500 data-[invalid]:focus:ring-red-500 data-[invalid]:focus:border-red-500
            ${isFlexMax ? "flex-1" : ""} ${disabled ? "bg-disabled cursor-not-allowed" : ""} ${className}`;

        return {
            required,
            disabled,
            className: baseClassName
        }
    }, [required, disabled, isFlexMax, className])
    
    return (
        <Form.Field name={name} className={`${isFlexMax ? "flex flex-col flex-1" : ""}`}>
            <Form.Label className="text-sm font-medium text-gray-700 mb-2">{label}</Form.Label>
            <Form.Control asChild>
                {React.cloneElement(children as React.ReactElement, {
                    ...controlProps
                })}
            </Form.Control>
            {
                errorMessages?.map((message, index) => <Form.Message 
                    key={`error-${index}`}
                    className="text-xs text-red-500 mt-1" 
                    match={message.match}
                >
                    {message.content}
                </Form.Message>)
            }
        </Form.Field>
    )
}

export default FormBase