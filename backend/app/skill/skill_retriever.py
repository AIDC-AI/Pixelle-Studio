from ms_agent.skill.schema import SkillSchema
from typing import Dict


class SkillRetriever:

    def __init__(self, skills: Dict[str, SkillSchema]) -> None:
        self.skills = skills

    def retrieve(self, query: str) -> Dict[str, SkillSchema]:
        return [(skill_key, skill, 1.0) for skill_key, skill in self.skills.items()]
