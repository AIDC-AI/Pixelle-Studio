// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useApp } from '@/context';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
    children: React.ReactNode;
}

const PUBLIC_ROUTES = ['/auth']

export default function AuthGuard({ children }: AuthGuardProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { token } = useApp();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        const isAuthRoute = PUBLIC_ROUTES.includes(pathname);
        if (!token && !isAuthRoute) {
            // Token doesn't exist or is invalid, and accessing protected route, redirect to auth page
            router.push('/auth');
        } else if (token && isAuthRoute) {
            // Token is valid and accessing auth page, redirect to home
            router.push('/');
        } else {
            setIsChecking(false);
        }
    }, [token, pathname, router]);

    // Show loading state
    if (isChecking) {
        return (
            <div className="w-screen h-screen flex items-center justify-center bg-gray-50">
                <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
            </div>
        );
    }

    return <>{children}</>;
}
