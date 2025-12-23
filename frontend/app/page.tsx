/*
 * @Author: ai-business-hql ai.bussiness.hql@gmail.com
 * @Date: 2025-12-22 15:36:20
 * @LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
 * @LastEditTime: 2025-12-23 13:17:52
 * @FilePath: /mcp-workflow/frontend/app/page.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
'use client';

import Chat from '@/components/layout/chat';
import LeftPanel from '@/components/layout/leftPanel';

export default function Home() {
    return (
        <div className="w-screen h-screen flex">
            <LeftPanel />

            <Chat />
        </div>
    );
}
