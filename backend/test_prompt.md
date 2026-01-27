<!--
 * @Author: ai-business-hql ai.bussiness.hql@gmail.com
 * @Date: 2026-01-21 11:04:06
 * @LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
 * @LastEditTime: 2026-01-26 21:57:50
 * @FilePath: /mcp-workflow/backend/test_prompt.md
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
目的：在触发test运行拿到运行日志后，报错则修改对应的代码，执行效果不好则优化prompt
测试脚本： @backend/test_ws_chat.py
流程：
- 运行一次某个测试脚本
- 如果报错，修改报错
- 如果结果不达预期，复盘原因，优化prompt 
@backend/app/agent.py:181-247
或者优化 tools  @backend/app/tools.py 
在修改代码文件的过程中，需要注意，这个项目是一个通用场景的skills client，[CRITICAL]不要把具体某个场景的prompt写到system prompt里，system prompt和tools只能修改能优化所有通用场景的语句。
- 只要修改了代码，./start_server.sh 使用了--reload参数会自动重新启动服务端，只需要稍作等待即可

- 再运行一次某个测试脚本，循环