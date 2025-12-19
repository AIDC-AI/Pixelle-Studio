from ast import Pass
from ms_agent.agent import AgentSkill
from torch.nn import parameter
from app.skill.skill_retriever import SkillRetriever
from ms_agent.skill.schema import SkillContext, SkillSchema
from typing import Union, List, Optional, Dict, Any, Tuple
from app.skill.prompts import PROMPT_EXTEND_WITH_FILE_PATHS
from app.utils.logger import logger as logger
from pathlib import Path
from ms_agent.skill.prompts import (PROMPT_SKILL_PLAN, PROMPT_SKILL_TASKS, PROMPT_TASKS_IMPLEMENTATION, SCRIPTS_IMPLEMENTATION_FORMAT,
                                    SCRIPTS_IMPLEMENTATION_EXAMPLE)
from ms_agent.utils.utils import str_to_md5
from ms_agent.skill.skill_utils import (extract_implementation, extract_cmd_from_code_blocks, extract_packages_from_code_blocks)
from app.llm.aihub_llm import AihubLLM, LLMMode
from app.llm.components import Message
import json
import sys
import os
import shlex
from ms_agent.utils.utils import install_package
from app.skill.skill_output import SkillOutput, TaskState, Implementation, ImplementationType, ExecutionResult
import traceback
from dataclasses import asdict


class SkillAgent(AgentSkill):

    def __init__(self,
                 skills: Union[str, List[str], List[SkillSchema]],
                 model: str,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 stream: Optional[bool] = True,
                 enable_thinking: Optional[bool] = False,
                 max_tokens: Optional[int] = 8192,
                 work_dir: str = None,
                 **kwargs) -> None:
        super().__init__(skills, model, api_key, base_url, stream, enable_thinking, max_tokens, work_dir, True, **kwargs)
        self.llm = AihubLLM(model=model, api_key=api_key, base_url=base_url, mode=LLMMode.SYNC, stream=stream)
        self.retriever = SkillRetriever(skills=self.all_skills)

    def generate(self, query: str, file_paths: List[str] = None) -> SkillOutput:
        #only support single file path now
        if file_paths:
            file_path = file_paths[0]
            query = PROMPT_EXTEND_WITH_FILE_PATHS.format(prompt=query, filename=file_path)
        else:
            query = query
        #skill retrieval
        relevant_skills = self.retriever.retrieve(query=query)
        if not relevant_skills:
            return SkillOutput(
                skill_name=None,
                task_id=None,
                state=TaskState.MATCH_FAILED,
                message='No relevant skills found for the query',
                implementations=[],
            )

        skill_name = relevant_skills[0][0]
        task_id = str_to_md5(query)
        task_work_dir = self.get_task_work_dir(task_id)
        top_skill_key, top_skill, score = relevant_skills[0]
        logger.info(f'Using skill: {top_skill_key} (score: {score:.2f})')
        skill: SkillSchema = top_skill
        try:
            # Build skill context
            skill_context: SkillContext = self._build_skill_context(skill)
            skill_md_context: str = '\n\n<!-- SKILL_MD_CONTEXT -->\n' + skill_context.skill.content.strip()
            reference_context: str = '\n\n<!-- REFERENCE_CONTEXT -->\n' + '\n'.join([
                json.dumps({
                    'name': ref.get('name', ''),
                    'path': ref.get('path', ''),
                    'description': ref.get('description', ''),
                }, ensure_ascii=False) for ref in skill_context.references
            ])
            script_context: str = '\n\n<!-- SCRIPT_CONTEXT -->\n' + '\n'.join([
                json.dumps({
                    'name': script.get('name', ''),
                    'path': script.get('path', ''),
                    'description': script.get('description', ''),
                }, ensure_ascii=False) for script in skill_context.scripts
            ])
            resource_context: str = '\n\n<!-- RESOURCE_CONTEXT -->\n' + '\n'.join([
                json.dumps({
                    'name': res.get('name', ''),
                    'path': res.get('path', ''),
                    'description': res.get('description', ''),
                }, ensure_ascii=False) for res in skill_context.resources
            ])

            # PLAN: Analyse the SKILL.md, references, and scripts.
            prompt_skill_plan: str = PROMPT_SKILL_PLAN.format(
                query=query,
                skill_md_context=skill_md_context,
                reference_context=reference_context,
                script_context=script_context,
                resource_context=resource_context,
            )

            response_skill_plan = self._call_llm(
                user_prompt=prompt_skill_plan,
                stream=self.stream,
            )
            skill_context.spec.plan = response_skill_plan
            logger.info('\n======== Completed Skill Plan Response ========\n')

            # TASKS: Get solutions and tasks based on analysis.
            prompt_skill_tasks: str = PROMPT_SKILL_TASKS.format(skill_plan_context=response_skill_plan, )

            response_skill_tasks = self._call_llm(
                user_prompt=prompt_skill_tasks,
                stream=self.stream,
            )
            skill_context.spec.tasks = response_skill_tasks
            logger.info('\n======== Completed Skill Tasks Response ========\n')

            # IMPLEMENTATION & EXECUTION
            script_contents: str = '\n\n'.join([
                '<!-- ' + script.get('path', '') + ' -->\n' + script.get('content', '') for script in skill_context.scripts
                if script.get('name', '') in response_skill_tasks
            ])
            reference_contents: str = '\n\n'.join([
                '<!-- ' + ref.get('path', '') + ' -->\n' + ref.get('content', '') for ref in skill_context.references
                if ref.get('name', '') in response_skill_tasks
            ])
            resource_contents: str = '\n\n'.join([
                '<!-- ' + res.get('path', '') + ' -->\n' + res.get('content', '') for res in skill_context.resources
                if res.get('name', '') in response_skill_tasks
            ])

            prompt_tasks_implementation: str = PROMPT_TASKS_IMPLEMENTATION.format(
                script_contents=script_contents,
                reference_contents=reference_contents,
                resource_contents=resource_contents,
                skill_tasks_context=response_skill_tasks,
                scripts_implementation_format=SCRIPTS_IMPLEMENTATION_FORMAT,
                scripts_implementation_example=SCRIPTS_IMPLEMENTATION_EXAMPLE,
            )

            response_tasks_implementation = self._call_llm(
                user_prompt=prompt_tasks_implementation,
                stream=self.stream,
            )
            skill_context.spec.implementation = response_tasks_implementation

            # Dump the spec files
            spec_output_path = skill_context.spec.dump(output_dir=str(task_work_dir))
            logger.info(f'Spec files dumped to: {spec_output_path}')
            #Dump the prompt files
            self._dump_prompt_files(task_work_dir, prompt_skill_plan, prompt_skill_tasks, prompt_tasks_implementation)
            # Extract IMPLEMENTATION content and determine execution scenario
            _, implementation_content = extract_implementation(content=response_tasks_implementation)
        except Exception as e:
            traceback.print_exc()
            logger.error(f'Error generating skill output: {str(e)}')
            return SkillOutput(
                skill_name=skill_name,
                task_id=task_id,
                state=TaskState.GENERATE_FAILED,
                message=str(f'Error generating skill output: {str(e)}'),
                implementations=[],
            )

        if not implementation_content or len(implementation_content) == 0:
            logger.error('No IMPLEMENTATION content extracted from response')
            return SkillOutput(
                skill_name=skill_name,
                task_id=task_id,
                state=TaskState.NO_IMPLEMENTATION,
                message='No IMPLEMENTATION content extracted from response',
                implementations=[Implementation(type=ImplementationType.CONTENT, content=response_tasks_implementation)],
            )

        else:
            implementations, code_blocks = self._extract_code_blocks(implementation_content, task_id)
            for code_block in code_blocks:
                place_index = implementations.index(None)
                try:
                    executable_code: Dict[str, str] = self._analyse_code_block(
                        code_block=code_block,
                        skill_context=skill_context,
                        task_id=task_id,
                    )
                except Exception as e:
                    traceback.print_exc()
                    logger.error(f'Error analyzing code block: {str(e)}')
                    return SkillOutput(
                        skill_name=skill_name,
                        task_id=task_id,
                        state=TaskState.NON_EXECUTABLE,
                        message=str(f'Analysis code block {code_block} failed: {str(e)}'),
                        implementations=implementations,
                    )
                implementations[place_index] = Implementation(type=ImplementationType.COMMAND,
                                                              command=executable_code.get('code'),
                                                              file_list=[os.path.join(self.work_dir, code_block.get('script'))] +
                                                              [ref.get('path') for ref in skill_context.references if ref.get('name') in response_skill_tasks] +
                                                              [res.get('path') for res in skill_context.resources if res.get('name') in response_skill_tasks],
                                                              package_list=executable_code.get('packages', []))
            return SkillOutput(state=TaskState.ACCEPTABLE, skill_name=skill_name, task_id=task_id, message="", implementations=implementations)
            # if isinstance(implementation_content[0], dict):
            #     execute_results: List[dict] = []
            #     for _code_block in implementation_content:
            #         execute_result: ExecutionResult = self.execute(
            #             code_block=_code_block,
            #             skill_context=skill_context,
            #         )
            #         execute_results.append(execute_result.to_dict())

            #     return json.dumps(execute_results, ensure_ascii=False, indent=2)
            # elif isinstance(implementation_content[0], tuple):
            #     # Dump the generated code content to files
            #     for _lang, _code in implementation_content:
            #         if _lang == 'html':
            #             file_ext = 'html'
            #         elif _lang == 'javascript':
            #             file_ext = 'js'
            #         else:
            #             file_ext = 'md'

            #         output_file_path = self.work_dir / f'{str_to_md5(_code)}.{file_ext}'
            #         with open(output_file_path, 'w', encoding='utf-8') as f:
            #             f.write(_code)
            #         logger.info(f'Generated {_lang} file saved to: {output_file_path}')
            #     return f'Generated files have been saved to the working directory: {self.work_dir}'
            # elif isinstance(implementation_content[0], str):
            #     return '\n\n'.join(implementation_content)
            # else:
            #     logger.error('Unknown IMPLEMENTATION content format')
            #     raise RuntimeError('I encountered an unexpected format in the implementation steps.')

    def _extract_code_blocks(self, implementation_content: List[str], task_id: str) -> Tuple[List[Implementation], List[Dict[str, Any]]]:
        '''
        Extract code blocks from implementation content,convert code blocks to code file
        Returns:
            Tuple first is the Implementations that are not executable,second is the code blocks that are executable
        '''
        code_blocks: List[Dict[str, Any]] = []
        implementations: List[Implementation] = []
        gen_impl_index = 0
        task_work_dir = self.get_task_work_dir(task_id)
        for content in implementation_content:

            if isinstance(content, dict):
                script = content.get('script', '')
                parameters: Dict[str, Any] = content.get('parameters', None)
                if script in ('python', 'npm', 'bash', 'sh'):
                    if parameters:
                        code_block = parameters.get('code', None)
                    if parameters is None or code_block is None:
                        implementations.append(Implementation(type=ImplementationType.INVALID_BLOCK, content=json.dumps(content, ensure_ascii=False)))
                    else:

                        gen_script_path = os.path.join(task_work_dir, f'gen_impl_{gen_impl_index}.py')
                        with open(os.path.join(gen_script_path), 'w', encoding='utf-8') as f:
                            f.write(code_block)
                        gen_impl_index += 1
                        code_blocks.append({
                            'type': 'script',
                            'script': gen_script_path.strip(self.work_dir.as_posix()).lstrip('/'),
                            'parameters': {},
                        })
                        #placeholder for the implementation
                        implementations.append(None)
                else:
                    code_blocks.append(content)
                    #placeholder for the implementation
                    implementations.append(None)
            elif isinstance(content, tuple):
                # Dump the generated code content to files
                for _lang, _code in implementation_content:
                    if _lang == 'html':
                        file_ext = 'html'
                    elif _lang == 'javascript':
                        file_ext = 'js'
                    else:
                        file_ext = 'md'

                    output_file_path: Path = task_work_dir / f'{str_to_md5(_code)}.{file_ext}'
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(_code)
                    implementations.append(Implementation(type=ImplementationType.FILE, file_list=[output_file_path.as_posix()]))
                    logger.info(f'Generated {_lang} file saved to: {output_file_path}')
            elif isinstance(content, str):
                implementations.append(Implementation(type=ImplementationType.CONTENT, content=content))
        return implementations, code_blocks

    @classmethod
    def execute(cls, implementation: Implementation,use_sandbox: bool = False) -> ExecutionResult:
        """
        Execute a code block from a skill context.

        Args:
            code_block: Code block dictionary containing 'script' or 'function' key
                e.g. {{'script': '<script_path>', 'parameters': {{'param1': 'value1', 'param2': 'value2', ...}}}}
            

        Returns:
            (ExecutionResult) Dictionary containing execution results
        """
        exec_result = ExecutionResult()
        try:
            if use_sandbox:
                if ImplementationType.COMMAND == implementation.type:

                    # code_split = shlex.split(code_str)
                    # new_code_split: List[str] = []
                    # for item in code_split[1:]:
                    #     # All paths should be relative to `self.work_dir`
                    #     item = os.path.join(str(self.work_dir_in_sandbox), Path(item).as_posix())
                    #     new_code_split.append(item)
                    # code_str = ' '.join(code_split[:1] + new_code_split)

                    results: Dict[str, Any] = cls.sandbox.execute(
                        shell_command=implementation.command,
                        requirements=implementation.package_list,
                    )
                    return ExecutionResult(
                        success=True,
                        output=results.get('shell_executor', []),
                        messages='Executed in sandbox successfully for script.',
                    )
                elif ImplementationType.FUNCTION == implementation.type:
                    results: Dict[str, Any] = cls.sandbox.execute(
                        python_code=implementation.content,
                        requirements=implementation.package_list,
                    )
                    return ExecutionResult(
                        success=True,
                        output=results.get('python_executor', []),
                        messages='Executed in sandbox successfully for function.',
                    )
                else:
                    raise ValueError(f'Unknown implementation type: {implementation.type}')

            else:
                # TODO: Add `confirm manually`
                logger.warning('Executing code block in local environment!')

                # Prepare execution environment
                logger.info(f'Installing required packages: {implementation.package_list}')
                for pack in implementation.package_list:
                    install_package(package_name=pack)

                if ImplementationType.COMMAND == implementation.type:
                    return ExecutionResult(**asdict(cls._execute_cmd(cmd_str=implementation.command)))

                elif ImplementationType.FUNCTION == implementation.type:
                    return ExecutionResult(**asdict(cls._execute_code_block(code=implementation.content)))

                else:
                    raise ValueError(f'Unknown implementation type: {implementation.type}')

        except Exception as e:
            traceback.print_exc()
            logger.error(f'Error executing code block: {str(e)}')
            exec_result.success = False
            exec_result.messages = str(e)

            return exec_result

    def _call_llm(self, user_prompt: str, system_prompt: str = None, stream: bool = True) -> str:

        default_system: str = 'You are an intelligent assistant that can help users by leveraging specialized skills.'
        system_prompt = system_prompt or default_system

        messages = [
            Message(role='assistant', content=system_prompt),
            Message(role='user', content=user_prompt),
        ]
        resp = self.llm.generate(
            messages=messages,
            stream=stream,
        )

        _content = ''
        is_first = True
        _response_message = None
        if stream:
            for _response_message in resp:
                if is_first:
                    messages.append(_response_message)
                    is_first = False
                new_content = _response_message.content[len(_content):]
                sys.stdout.write(new_content)
                sys.stdout.flush()
                _content = _response_message.content
                messages[-1] = _response_message

            sys.stdout.write('\n')
        else:
            _content = resp.content
            sys.stdout.write(_content)
            sys.stdout.flush()
            messages.append(resp)
        return _content

    def _analyse_code_block(self, code_block: dict, skill_context: SkillContext, task_id: str) -> Dict[str, str]:
        """
        Analyse a code block from a skill context to extract executable command.

        Args:
            code_block: Code block dictionary containing 'script' or 'function' key
                e.g. {{'script': '<script_path>', 'parameters': {{'param1': 'value1', 'param2': 'value2', ...}}}}
            skill_context: SkillContext object

        Returns:
            Dictionary containing:
                'type': 'script' or 'function'
                'code': Executable command string or code block
                'packages': List of required packages
        """
        # type - script or function
        res = {'type': '', 'code': '', 'packages': []}

        # Get the script path
        if 'script' in code_block:
            script_str: str = code_block.get('script')
            parameters: Dict[str, Any] = code_block.get('parameters', {})

            script_path: Path = skill_context.root_path / script_str
            if not script_path.exists():
                script_path: Path = skill_context.root_path / 'scripts' / script_str
            if not script_path.exists():
                script_path: Path = self.get_task_work_dir(task_id) / script_str
            if not script_path.exists():
                raise FileNotFoundError(f'Script not found: {script_str}')

            # Read the content of script
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()

                script_content = script_content.strip()
                if not script_content:
                    raise RuntimeError(f'Script is empty: {script_str}')

                # Build command to execute the script with parameters
                prompt: str = (
                    f'According to following script content and parameters, '
                    f'find the usage for script and output the shell command in the form of: '
                    f'```shell\npython {script_str} ...\n``` with python interpreter. '
                    f'the parameters should add to the command, when the PARAMETERS is not empty or the script need to be set the input parameters.\n'
                    f'\nExtract the packages required by the script and output them in the form of: ```packages\npackage1\npackage2\n...```. '  # noqa
                    f'Note that you need to exclude the build-in standard library packages, and determine the specific PyPI package name according to the import statements in the script. '  # noqa
                    f'you must output the result very concisely and clearly without any extra explanation.'
                    f'\n\nSCRIPT CONTENT:\n{script_content}'
                    f'\n\nPARAMETERS:\n{json.dumps(parameters, ensure_ascii=False)}')
                response: str = self._call_llm(
                    user_prompt=prompt,
                    system_prompt='You are a helpful assistant that extracts the shell command from code blocks.',
                    stream=self.stream,
                )

                cmd_blocks = extract_cmd_from_code_blocks(response)
                if len(cmd_blocks) == 0:
                    raise RuntimeError(f'No shell command found in LLM response for script {script_str}')
                cmd_str = cmd_blocks[0]
                #TODO(lingyue.ly):check the cmd str by regex rules
                #add absolute path for the script
                cmd_list: List[str] = shlex.split(cmd_str)
                for i in range(1, len(cmd_list)):
                    if not os.path.exists(cmd_list[i]):
                        new_cmd = os.path.join(self.work_dir, cmd_list[i])
                        if os.path.exists(new_cmd):
                            cmd_list[i] = new_cmd
                        elif i == 1:
                            raise FileNotFoundError(f'Script which need to be executed is not found: {cmd_list[i]}')
                fixed_cmd_str = " ".join(cmd_list)
                packages = extract_packages_from_code_blocks(response)

                res['type'] = 'script'
                res['code'] = fixed_cmd_str
                res['packages'] = packages

            except Exception as e:
                raise RuntimeError(f'Failed to read script {script_str}: {str(e)}')

        elif 'function' in code_block:
            res['type'] = 'function'
            res['code'] = code_block.get('function')

        else:
            raise ValueError("Code block must contain either 'script' or 'function' key")

        return res

    def get_task_work_dir(self, task_id: str) -> Path:
        return self.work_dir / task_id

    def _dump_prompt_files(self, task_work_dir: Path, prompt_skill_plan: str, prompt_skill_tasks: str, prompt_tasks_implementation: str):
        prompts_dir = task_work_dir / 'prompts'
        prompts_dir.mkdir(parents=True, exist_ok=True)
        with open(prompts_dir / 'prompt_plan.md', 'w', encoding='utf-8') as f:
            f.write(prompt_skill_plan)
        with open(prompts_dir / 'prompt_tasks.md', 'w', encoding='utf-8') as f:
            f.write(prompt_skill_tasks)
        with open(prompts_dir / 'prompt_implementation.md', 'w', encoding='utf-8') as f:
            f.write(prompt_tasks_implementation)


def end2end(skill_agent:SkillAgent,query: str, input_file: str):
    skill_output_path = generate_skill(skill_agent, query, input_file)
    execute_results_path = execute_skill(skill_output_path)
    return execute_results_path


def create_skill_agent(skills_path: str) -> SkillAgent:
    from app.llm_adapter import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
    return SkillAgent(skills=skills_path,
                      model="us.anthropic.claude-opus-4-20250514-v1:0",
                      api_key=LLM_API_KEY,
                      base_url=LLM_BASE_URL,
                      stream=False,
                      enable_thinking=False,
                      max_tokens=8192,
                      work_dir='./work_dir')


def execute_skill(skill_output_path: str):
    with open(skill_output_path, 'r', encoding='utf-8') as f:
        skill_output = SkillOutput(**json.load(f))
    execute_results: List[Dict[str, Any]] = []
    for implementation in skill_output.implementations:
        if implementation.type == ImplementationType.COMMAND or implementation.type == ImplementationType.FUNCTION:
            execute_result = SkillAgent.execute(implementation=implementation)
            execute_results.append(execute_result.model_dump())
    print(f"Got execute results")
    print(json.dumps(execute_results, ensure_ascii=False, indent=2))
    execute_results_path = os.path.join(os.path.dirname(skill_output_path), f"execute_results.json")
    with open(execute_results_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(execute_results, ensure_ascii=False, indent=2))
    print(f"Execute results saved to: {execute_results_path}")
    return execute_results_path


def generate_skill(skill_agent: SkillAgent, query: str, input_file: str) -> str:
    skill_output: SkillOutput = skill_agent.generate(query=query, file_paths=[input_file])
    logger.info("Got skill output")
    print(skill_output.model_dump_json(ensure_ascii=False, indent=2))

    skill_output_path = skill_agent.get_task_work_dir(skill_output.task_id) / "skill_output.json"
    with open(skill_output_path, 'w', encoding='utf-8') as f:
        f.write(skill_output.model_dump_json(ensure_ascii=False, indent=2))
    print(f"Skill output saved to: {skill_output_path}")
    return skill_output_path


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="op")

    all_op = subparsers.add_parser('all', help='Generate skill output and execute skill output')
    all_op.add_argument("--query", type=str, required=True, help="user query string")
    all_op.add_argument("--file", type=str, default=None, help="input file path")
    all_op.add_argument("--skills", type=str, required=True, help="skill set path")

    gen_op = subparsers.add_parser('gen', help='Generate skill output')
    gen_op.add_argument("--query", type=str, required=True, help="user query string")
    gen_op.add_argument("--file", type=str, default=None, help="input file path")
    gen_op.add_argument("--skills", type=str, required=True, help="skill set path")

    exe_op = subparsers.add_parser('exe', help='Execute skill output')
    exe_op.add_argument("--skill_output", type=str, required=True, help="skill output path")

    args = parser.parse_args()
    if hasattr(args, "skills"):
        skill_agent = create_skill_agent(args.skills)

    if args.op == 'gen':
        result = generate_skill(skill_agent, args.query, args.file)
    elif args.op == 'all':
        result = end2end(skill_agent, args.query, args.file)
    elif args.op == 'exe':
        result = execute_skill(args.skill_output)
    else:
        parser.print_help()
        exit(1)
    logger.info(f"Finish to do {args.op},result file path:{result}")
