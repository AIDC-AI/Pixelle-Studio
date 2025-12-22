from pydantic import BaseModel, Field
from typing import List, Any
from enum import Enum


class TaskState(Enum):
    ACCEPTABLE = 0  #successfully completed the task,and the implementation is executable or acceptable
    MATCH_FAILED = 1  #no suitable skill found for the query
    GENERATE_FAILED = 2  #failed to generate implementation for the task
    NO_IMPLEMENTATION = 3  #no implementation output for the task
    NON_EXECUTABLE = 4  #the implementation is not executable,something wrong with the command or code of the implementations


class ImplementationType(Enum):
    CONTENT = 0
    FILE = 1
    COMMAND = 2
    FUNCTION = 3
    INVALID_BLOCK = 4

# def enum_dict_factory(data):
#     return {
#         key: value.value if isinstance(value, Enum) else value
#         for key, value in data
#     }



class Implementation(BaseModel):
    type: ImplementationType  #the implementation type
    content: str | None = None  #if type is CONTEXT,content is not None,for example: "The total revenue is 100000"
    command: str | None = None  #if type is COMMAND,command is not None,for example: "python recal.py filename timeout"
    file_list: List[str] | None = None  #the script/reference/resource file path list for implementation
    package_list: List[str] | None = None  #the installation package list for executable scripts



class SkillOutput(BaseModel):
    state: TaskState
    skill_name: str | None = None
    task_id: str | None = None  #task id is decode from md5 of query which contains file paths,task id is not None when skill name is not None
    message: str = ""
    implementations: List[Implementation] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    success: bool = True
    output: Any | None = None
    messages: str = ""
