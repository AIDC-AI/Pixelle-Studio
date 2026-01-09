import { FormErrorMessage } from "@/types/form"
import FormBase from "./base"

type SelectItem = {
    value: string
    label: string
}

interface IProps {
    name: string
    label: string
    errorMessages?: FormErrorMessage[]
    selectOptions?: SelectItem[]
    required?: boolean
    disabled?: boolean
    isFlexMax?: boolean // 是否撑满剩余空间
    setValue?: (value: string) => void
}

const FormSelect: React.FC<IProps> = (props) => {
    const {
        name,
        label,
        errorMessages,
        required,
        disabled,
        selectOptions,
        isFlexMax = false,
        setValue
    } = props

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setValue?.(e.target.value)
    }

    return (
        <FormBase
            name={name}
            label={label}
            errorMessages={errorMessages}
            required={required}
            disabled={disabled}
            isFlexMax={isFlexMax}
            className="appearance-none 
            bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjNkI3MjgwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==')] 
            bg-position-[right_1rem_center] bg-no-repeat pr-10"
        >
            <select onChange={handleChange}>
                {selectOptions?.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
        </FormBase>
    )
}

export default FormSelect