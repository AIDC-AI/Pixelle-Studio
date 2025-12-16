'use client';

import Left from '@/components/left';
import Chat from '@/components/chat';

export default function Home() {
    return (
        <div className="w-screen h-screen flex">
            <Left />

            <Chat />
        </div>
    );
}
