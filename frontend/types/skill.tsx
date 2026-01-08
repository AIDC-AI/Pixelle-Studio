export interface Skill {
    name: string
    meta: SkillMeta
    content: string
    files?: SkillFile[]
}

export interface SkillMeta {
    name: string
    description: string
    path: string
    directory: string
    license?: string
    linked_files?: string[]
    has_scripts?: boolean
    has_resources?: boolean
    is_default?: boolean
}

export interface SkillFile {
    name: string;
    size: number;
    path: string;
}