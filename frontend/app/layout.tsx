import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context";

export const metadata: Metadata = {
    title: "MCP Workflow Demo",
    description: "MCP Workflow Demo Application",
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
                    {children}
                </AppProvider>
            </body>
        </html>
    );
}
