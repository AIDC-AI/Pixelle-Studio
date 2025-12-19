export interface Skill {
    name: string;
    path: string;
    has_description: boolean;
    description?: string;
}

export interface SkillFile {
    name: string;
    size: number;
    path: string;
}

export interface SkillDetail {
    name: string;
    metadata: Record<string, string>;
    content: string;
    full_content: string;
    files: SkillFile[];
}