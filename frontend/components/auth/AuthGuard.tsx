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
