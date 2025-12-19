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
