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

import Logo from "@/components/ui/logo";
import { FileSpreadsheet, Presentation, FileText, Globe, BarChart3, FolderOpen } from "lucide-react";

export interface WelcomePrompt {
    icon: React.ReactNode;
    category: string;
    description: string;
    prompt: string;
    hasFile: boolean;
    fileName?: string;
    fileUrl?: string;
}

export const WELCOME_PROMPTS: WelcomePrompt[] = [
    {
        icon: <FileSpreadsheet className="w-5 h-5" />,
        category: 'Data Analysis',
        description: 'Analyze Excel sales data with visualizations',
        prompt: 'Please analyze the monthly_product_revenue.xlsx file, calculate each product\'s average monthly revenue and growth trends, and generate professional charts including bar charts and trend lines.',
        hasFile: true,
        fileName: 'monthly_product_revenue.xlsx',
        fileUrl: '/assets/monthly_product_revenue.xlsx',
    },
    {
        icon: <Presentation className="w-5 h-5" />,
        category: 'PPT Design',
        description: 'Create professional presentation slides',
        prompt: 'Design a professional PPT presentation about "2024 AI Technology Trends" with a cover page, table of contents, 3 content slides with charts, and a summary page. Use modern, clean design with professional color scheme.',
        hasFile: false,
    },
    {
        icon: <FileText className="w-5 h-5" />,
        category: 'PDF Report',
        description: 'Generate formatted PDF documents',
        prompt: 'Generate a quarterly sales analysis report in PDF format, including a title page, executive summary, data charts with analysis, and conclusion with recommendations. Use professional typography and layout.',
        hasFile: false,
    },
    {
        icon: <Globe className="w-5 h-5" />,
        category: 'API Integration',
        description: 'Connect external APIs & display results',
        prompt: 'Call a map API to query the driving route from West Lake (Hangzhou) to The Bund (Shanghai), and generate an HTML page displaying the route information with an interactive map visualization.',
        hasFile: false,
    },
    {
        icon: <BarChart3 className="w-5 h-5" />,
        category: 'Chart Generation',
        description: 'Create publication-quality charts from data',
        prompt: 'Based on the monthly_product_revenue.xlsx data, create a professional comparison chart showing each product\'s monthly revenue trend using both bar charts and line charts, and export as a high-resolution PNG image.',
        hasFile: true,
        fileName: 'monthly_product_revenue.xlsx',
        fileUrl: '/assets/monthly_product_revenue.xlsx',
    },
    {
        icon: <FolderOpen className="w-5 h-5" />,
        category: 'File Processing',
        description: 'Transform & convert files to new formats',
        prompt: 'Read the monthly_product_revenue.xlsx file and convert the data into a beautifully formatted interactive HTML table page with sorting and filtering capabilities, styled with modern CSS.',
        hasFile: true,
        fileName: 'monthly_product_revenue.xlsx',
        fileUrl: '/assets/monthly_product_revenue.xlsx',
    },
];

interface IProps {
    onPromptClick?: (prompt: WelcomePrompt) => void;
}

const WelcomePrompts: React.FC<IProps> = ({ onPromptClick }) => {
    return (
        <div className="flex flex-col items-center justify-center h-full px-6 py-8 select-none">
            {/* Logo & Greeting */}
            <div className="flex flex-col items-center mb-8">
                <Logo width="180" className="mb-4 opacity-60" />
                <p className="text-sm text-gray-400 mt-1">
                    Click an example below to get started
                </p>
            </div>

            {/* Prompt Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl w-full">
                {WELCOME_PROMPTS.map((prompt, index) => (
                    <button
                        key={index}
                        onClick={() => onPromptClick?.(prompt)}
                        className="group flex flex-col gap-2 p-4 rounded-xl border border-gray-100 bg-white/60 
                            hover:bg-white hover:border-gray-200 hover:shadow-sm
                            transition-all duration-200 text-left cursor-pointer"
                    >
                        {/* Category Header */}
                        <div className="flex items-center gap-2">
                            <span className="text-gray-400 group-hover:text-gray-600 transition-colors">
                                {prompt.icon}
                            </span>
                            <span className="text-sm font-medium text-gray-500 group-hover:text-gray-700 transition-colors">
                                {prompt.category}
                            </span>
                            {prompt.hasFile && (
                                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-400 group-hover:bg-orange-50 group-hover:text-orange-400 transition-colors">
                                    + File
                                </span>
                            )}
                        </div>
                        {/* Description */}
                        <p className="text-xs text-gray-400 group-hover:text-gray-500 leading-relaxed transition-colors line-clamp-2">
                            {prompt.description}
                        </p>
                    </button>
                ))}
            </div>

            {/* Footer hint */}
            <p className="text-xs text-gray-300 mt-6">
                Supports file processing · API integration · Data visualization · Document generation
            </p>
        </div>
    );
};

export default WelcomePrompts;

