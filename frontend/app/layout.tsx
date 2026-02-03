import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context";
import AuthGuard from "@/components/auth/AuthGuard";

export const metadata: Metadata = {
    title: "Pixelle Studio",
    description: "Pixelle Studio Application",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body>
                <AppProvider>
                    <AuthGuard>
                        {children}
                    </AuthGuard>
                </AppProvider>
            </body>
        </html>
    );
}
