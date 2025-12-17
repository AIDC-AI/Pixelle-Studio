from ms_agent.agent import AgentSkill
from app.skill.skill_retriever import SkillRetriever
from ms_agent.skill.schema import ExecutionResult, SkillContext, SkillSchema
from typing import Union, List, Optional, Dict, Any
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
                 use_sandbox: bool = True,
                 **kwargs) -> None:
        super().__init__(skills, model, api_key, base_url, stream, enable_thinking, max_tokens, work_dir, use_sandbox, **kwargs)
        self.llm = AihubLLM(model=model, api_key=api_key, base_url=base_url, mode=LLMMode.SYNC, stream=stream)
        self.retriever = SkillRetriever(skills=self.all_skills)

    def run(self, query: str, file_paths: List[str] = None) -> str:
        #only support single file path now
        if file_paths:
            file_path = file_paths[0]
            query = PROMPT_EXTEND_WITH_FILE_PATHS.format(prompt=query, filename=file_path)
        else:
            query = query
        #skill retrieval
        relevant_skills = self.retriever.retrieve(query=query)
        top_skill_key, top_skill, score = relevant_skills[0]
        logger.info(f'Using skill: {top_skill_key} (score: {score:.2f})')
        skill: SkillSchema = top_skill

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
            '<!-- ' + ref.get('path', '') + ' -->\n' + ref.get('content', '') for ref in skill_context.references if ref.get('name', '') in response_skill_tasks
        ])
        resource_contents: str = '\n\n'.join([
            '<!-- ' + res.get('path', '') + ' -->\n' + res.get('content', '') for res in skill_context.resources if res.get('name', '') in response_skill_tasks
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
        spec_output_path = skill_context.spec.dump(output_dir=str(self.work_dir))
        logger.info(f'Spec files dumped to: {spec_output_path}')
        #for test
        with open(self.work_dir / 'implementation_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(prompt_tasks_implementation)
        # Extract IMPLEMENTATION content and determine execution scenario
        _, implementation_content = extract_implementation(content=response_tasks_implementation)

        if not implementation_content or len(implementation_content) == 0:
            logger.error('No IMPLEMENTATION content extracted from response')
            return 'I was unable to determine the implementation steps required to complete your request.'
        else:
            if isinstance(implementation_content[0], dict):
                execute_results: List[dict] = []
                for _code_block in implementation_content:
                    execute_result: ExecutionResult = self.execute(
                        code_block=_code_block,
                        skill_context=skill_context,
                    )
                    execute_results.append(execute_result.to_dict())

                return json.dumps(execute_results, ensure_ascii=False, indent=2)
            elif isinstance(implementation_content[0], tuple):
                # Dump the generated code content to files
                for _lang, _code in implementation_content:
                    if _lang == 'html':
                        file_ext = 'html'
                    elif _lang == 'javascript':
                        file_ext = 'js'
                    else:
                        file_ext = 'md'

                    output_file_path = self.work_dir / f'{str_to_md5(_code)}.{file_ext}'
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(_code)
                    logger.info(f'Generated {_lang} file saved to: {output_file_path}')
                return f'Generated files have been saved to the working directory: {self.work_dir}'
            elif isinstance(implementation_content[0], str):
                return '\n\n'.join(implementation_content)
            else:
                logger.error('Unknown IMPLEMENTATION content format')
                return 'I encountered an unexpected format in the implementation steps.'

    def execute(self, code_block: Dict[str, Any], skill_context: SkillContext) -> ExecutionResult:
        """
        Execute a code block from a skill context.

        Args:
            code_block: Code block dictionary containing 'script' or 'function' key
                e.g. {{'script': '<script_path>', 'parameters': {{'param1': 'value1', 'param2': 'value2', ...}}}}
            skill_context: SkillContext object

        Returns:
            (ExecutionResult) Dictionary containing execution results
        """
        exec_result = ExecutionResult()
        try:
            executable_code: Dict[str, str] = self._analyse_code_block(
                code_block=code_block,
                skill_context=skill_context,
            )
            code_type: str = executable_code.get('type')
            code_str: str = executable_code.get('code')
            packages: list = executable_code.get('packages', [])

            if not code_str:
                raise RuntimeError('No command to execute extracted from code block')
        except Exception as e:
            logger.error(f'Error analyzing code block: {str(e)}')
            exec_result.success = False
            exec_result.messages = str(e)

            return exec_result

        try:
            if self.use_sandbox:
                if 'script' == code_type:

                    code_split = shlex.split(code_str)
                    new_code_split: List[str] = []
                    for item in code_split[1:]:
                        # All paths should be relative to `self.work_dir`
                        item = os.path.join(str(self.work_dir_in_sandbox), Path(item).as_posix())
                        new_code_split.append(item)
                    code_str = ' '.join(code_split[:1] + new_code_split)

                    results: Dict[str, Any] = self.sandbox.execute(
                        shell_command=code_str,
                        requirements=packages,
                    )
                    return ExecutionResult(
                        success=True,
                        output=results.get('shell_executor', []),
                        messages='Executed in sandbox successfully for script.',
                    )
                elif 'function' == code_type:
                    results: Dict[str, Any] = self.sandbox.execute(
                        python_code=code_str,
                        requirements=packages,
                    )
                    return ExecutionResult(
                        success=True,
                        output=results.get('python_executor', []),
                        messages='Executed in sandbox successfully for function.',
                    )
                else:
                    raise ValueError(f'Unknown code type: {code_type}')

            else:
                # TODO: Add `confirm manually`
                logger.warning('Executing code block in local environment!')

                # Prepare execution environment
                logger.info(f'Installing required packages: {packages}')
                for pack in packages:
                    install_package(package_name=pack)

                if 'script' == code_type:
                    code_split: List[str] = shlex.split(code_str)
                    new_code_split: List[str] = []
                    for i, item in enumerate[str](code_split[1:]):
                        # All paths should be relative to `self.work_dir`
                        item = os.path.join(str(self.work_dir), Path(item).as_posix())
                        new_code_split.append(item)
                        #BUG FIX: if the item is the parameter of the script, can not add the path to the code_str
                        break

                    new_code_split = code_split[:1] + new_code_split
                    code_str = ' '.join(new_code_split)
                    return self._execute_cmd(cmd_str=code_str)

                elif 'function' == code_type:
                    return self._execute_code_block(code=code_str)

                else:
                    raise ValueError(f'Unknown code type: {code_type}')

        except Exception as e:
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

    def _analyse_code_block(self, code_block: dict, skill_context: SkillContext) -> Dict[str, str]:
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
            ptc_mode = script_str.strip() in ('python', 'npm', 'bash', 'sh')
            # Get real script absolute path
            if not ptc_mode:
                script_path: Path = skill_context.root_path / script_str
                if not script_path.exists():
                    script_path: Path = skill_context.root_path / 'scripts' / script_str
                if not script_path.exists():
                    raise FileNotFoundError(f'Script not found: {script_str}')

            # Read the content of script
            try:
                if not ptc_mode:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        script_content = f.read()

                    script_content = script_content.strip()
                    if not script_content:
                        raise RuntimeError(f'Script is empty: {script_str}')
                else:
                    script_content = parameters.pop('code')
                    gen_script_path = os.path.join('.spec', f'gen_impl_{str_to_md5(script_content)}.py')
                    with open(os.path.join(self.work_dir, gen_script_path), 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    script_str = gen_script_path
                # Build command to execute the script with parameters
                prompt: str = (
                    f'According to following script content and parameters, '
                    f'find the usage for script and output the shell command in the form of: '
                    f'```shell\npython {script_str} ...\n``` with python interpreter. '
                    f'the parameters should add to the command when the PARAMETERS is not empty.\n'
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
                cmd_str = cmd_blocks[0]  # TODO: NOTE

                packages = extract_packages_from_code_blocks(response)

                res['type'] = 'script'
                res['code'] = cmd_str
                res['packages'] = packages

            except Exception as e:
                raise RuntimeError(f'Failed to read script {script_str}: {str(e)}')

        elif 'function' in code_block:
            res['type'] = 'function'
            res['code'] = code_block.get('function')

        else:
            raise ValueError("Code block must contain either 'script' or 'function' key")

        return res


def main(query: str, input_file: str, skills_path: str):
    from app.llm_adapter import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
    skill_agent = SkillAgent(skills=skills_path,
                             model="us.anthropic.claude-opus-4-20250514-v1:0",
                             api_key=LLM_API_KEY,
                             base_url=LLM_BASE_URL,
                             stream=False,
                             enable_thinking=False,
                             max_tokens=8192,
                             work_dir='./work_dir',
                             use_sandbox=False)
    skill_result = skill_agent.run(query=query, file_paths=[input_file])
    return skill_result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', type=str, required=True)
    parser.add_argument('--file', type=str, required=True)
    parser.add_argument('--skills', type=str, required=True)
    args = parser.parse_args()
    result = main(args.query, args.file, args.skills)
    print(result)
