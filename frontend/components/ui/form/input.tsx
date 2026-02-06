/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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
    isTextarea?: boolean // 是否是textarea
    isFlexMax?: boolean // 是否撑满剩余空间
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
        placeholder = '请输入',
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