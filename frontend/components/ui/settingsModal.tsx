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

import { useEffect, useState } from "react";
import { ToastType, useApp } from "@/context";
import { userAPI } from "@/lib/userApi";
import { LLMSettings, LLMTestResponse } from "@/types/user";
import { Dialog } from "radix-ui";
import {
    XCircle, Eye, EyeOff, Trash2, Save, Loader2, ShieldCheck,
    Zap, Settings2, ChevronDown, ChevronUp, CheckCircle2, XOctagon
} from "lucide-react";

interface IProps {
    open: boolean;
    onClose?: () => void;
}

const THINKING_LEVELS = ["high", "medium", "low", "off"] as const;

const SettingsModal: React.FC<IProps> = (props) => {
    const { open, onClose } = props;
    const { showToast } = useApp();

    // ===== LLM Credentials =====
    const [apiKey, setApiKey] = useState<string>("");
    const [baseUrl, setBaseUrl] = useState<string>("");
    const [modelName, setModelName] = useState<string>("");

    // ===== Advanced Settings =====
    const [contextCompactionEnabled, setContextCompactionEnabled] = useState<boolean>(true);
    const [contextKeepRecent, setContextKeepRecent] = useState<number>(10);
    const [contextMinMessages, setContextMinMessages] = useState<number>(15);
    const [defaultThinkingLevel, setDefaultThinkingLevel] = useState<string>("medium");
    const [agentMaxTurns, setAgentMaxTurns] = useState<number>(50);
    const [modelFallbacks, setModelFallbacks] = useState<string>("");

    // ===== UI State =====
    const [showApiKey, setShowApiKey] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(false);
    const [saving, setSaving] = useState<boolean>(false);
    const [testing, setTesting] = useState<boolean>(false);
    const [testResult, setTestResult] = useState<LLMTestResponse | null>(null);
    const [currentSettings, setCurrentSettings] = useState<LLMSettings | null>(null);
    const [apiKeyModified, setApiKeyModified] = useState<boolean>(false);
    const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

    // Load existing settings when dialog opens
    useEffect(() => {
        if (open) {
            loadSettings();
            setTestResult(null);
        }
    }, [open]);

    const loadSettings = async () => {
        setLoading(true);
        try {
            const settings = await userAPI.getLLMSettings();
            setCurrentSettings(settings);
            setApiKey("");
            setBaseUrl(settings.base_url || "");
            setModelName(settings.model_name || "");
            setApiKeyModified(false);
            // Advanced settings
            setContextCompactionEnabled(settings.context_compaction_enabled);
            setContextKeepRecent(settings.context_keep_recent);
            setContextMinMessages(settings.context_min_messages);
            setDefaultThinkingLevel(settings.default_thinking_level);
            setAgentMaxTurns(settings.agent_max_turns);
            setModelFallbacks(settings.model_fallbacks || "");
        } catch (error) {
            showToast(ToastType.ERROR, "Failed to load settings");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const updateData: Record<string, unknown> = {};

            // Only send api_key if user has modified it
            if (apiKeyModified) {
                updateData.api_key = apiKey;
            }
            updateData.base_url = baseUrl;
            updateData.model_name = modelName;
            // Advanced settings
            updateData.context_compaction_enabled = contextCompactionEnabled;
            updateData.context_keep_recent = contextKeepRecent;
            updateData.context_min_messages = contextMinMessages;
            updateData.default_thinking_level = defaultThinkingLevel;
            updateData.agent_max_turns = agentMaxTurns;
            updateData.model_fallbacks = modelFallbacks;

            const result = await userAPI.updateLLMSettings(updateData);
            setCurrentSettings(result);
            setApiKey("");
            setApiKeyModified(false);
            showToast(ToastType.SUCCESS, "Settings saved successfully!");
            // Auto-close the modal after successful save
            onClose?.();
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    const handleTestConnection = async () => {
        // Determine which API key to test with
        const testApiKey = apiKeyModified && apiKey.trim()
            ? apiKey.trim()
            : null;

        if (!testApiKey && !currentSettings?.api_key_set) {
            showToast(ToastType.ERROR, "Please enter an API Key first");
            return;
        }

        if (!testApiKey) {
            showToast(ToastType.ERROR, "Please enter a new API Key to test, or re-enter your existing key");
            return;
        }

        setTesting(true);
        setTestResult(null);
        try {
            const result = await userAPI.testLLMConnection({
                api_key: testApiKey,
                base_url: baseUrl.trim() || undefined,
                model_name: modelName.trim() || undefined,
            });
            setTestResult(result);
        } catch (error) {
            setTestResult({
                success: false,
                message: (error as Error)?.message || "Connection test failed",
            });
        } finally {
            setTesting(false);
        }
    };

    const handleClearAll = async () => {
        setSaving(true);
        try {
            await userAPI.deleteLLMSettings();
            setCurrentSettings(null);
            setApiKey("");
            setBaseUrl("");
            setModelName("");
            setApiKeyModified(false);
            setTestResult(null);
            // Reset advanced to defaults
            setContextCompactionEnabled(true);
            setContextKeepRecent(10);
            setContextMinMessages(15);
            setDefaultThinkingLevel("medium");
            setAgentMaxTurns(50);
            setModelFallbacks("");
            showToast(ToastType.SUCCESS, "Settings cleared. Using system defaults.");
        } catch (error) {
            showToast(ToastType.ERROR, "Failed to clear settings");
        } finally {
            setSaving(false);
        }
    };

    const handleClose = () => {
        setApiKey("");
        setShowApiKey(false);
        setApiKeyModified(false);
        setTestResult(null);
        onClose?.();
    };

    return (
        <Dialog.Root
            open={open}
            onOpenChange={(o) => {
                if (!o) handleClose();
            }}
        >
            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/30 z-998 animate-[overlayShow_150ms_cubic-bezier(0.16,1,0.3,1)]" />
                <Dialog.Content
                    className="bg-white rounded-xl shadow-2xl fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[520px] max-h-[85vh] overflow-y-auto p-6 animate-[contentShow_150ms_cubic-bezier(0.16,1,0.3,1)] z-999"
                    aria-describedby={undefined}
                >
                    {/* Header */}
                    <div className="flex flex-row justify-between items-center mb-5">
                        <div className="flex items-center gap-2">
                            <ShieldCheck className="w-5 h-5 text-blue-600" />
                            <Dialog.Title className="font-semibold text-gray-900 text-[17px]">
                                LLM Settings
                            </Dialog.Title>
                        </div>
                        <Dialog.Close asChild>
                            <button
                                className="rounded-full flex justify-center items-center text-[rgba(0,0,0,0.45)] hover:text-[rgba(0,0,0,0.6)]"
                                aria-label="Close"
                            >
                                <XCircle className="w-5 h-5" />
                            </button>
                        </Dialog.Close>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                        </div>
                    ) : (
                        <div className="flex flex-col gap-4">
                            {/* Info banner */}
                            <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                                <ShieldCheck className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                                <p className="text-xs text-blue-700 leading-relaxed">
                                    Your API key is encrypted and stored securely on the server.
                                    It is never exposed to the frontend after saving.
                                    Leave the API Key field empty to keep your existing key unchanged.
                                </p>
                            </div>

                            {/* ========== LLM Credentials Section ========== */}
                            <div className="flex items-center gap-1.5 mt-1">
                                <Zap className="w-4 h-4 text-amber-500" />
                                <h3 className="text-sm font-semibold text-gray-800">API Configuration</h3>
                            </div>

                            {/* API Key Field */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-sm font-medium text-gray-700">
                                    API Key
                                    {currentSettings?.api_key_set && !apiKeyModified && (
                                        <span className="ml-2 text-xs text-green-600 font-normal">
                                            ✓ Configured ({currentSettings.api_key_masked})
                                        </span>
                                    )}
                                </label>
                                <div className="relative">
                                    <input
                                        type={showApiKey ? "text" : "password"}
                                        value={apiKey}
                                        onChange={(e) => {
                                            setApiKey(e.target.value);
                                            setApiKeyModified(true);
                                            setTestResult(null);
                                        }}
                                        placeholder={
                                            currentSettings?.api_key_set
                                                ? "Enter new key to replace, or leave empty to keep"
                                                : "sk-xxxxxxxxxxxxxxxx"
                                        }
                                        className="w-full px-3 py-2 pr-10 rounded-lg border border-gray-300 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                        autoComplete="off"
                                        spellCheck={false}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowApiKey(!showApiKey)}
                                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        {showApiKey ? (
                                            <EyeOff className="w-4 h-4" />
                                        ) : (
                                            <Eye className="w-4 h-4" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Base URL Field */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-sm font-medium text-gray-700">
                                    Base URL
                                    <span className="ml-1 text-xs text-gray-400 font-normal">(Optional)</span>
                                </label>
                                <input
                                    type="text"
                                    value={baseUrl}
                                    onChange={(e) => { setBaseUrl(e.target.value); setTestResult(null); }}
                                    placeholder="https://api.openai.com/v1"
                                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                />
                                <p className="text-xs text-gray-400">
                                    Custom OpenAI-compatible API endpoint. Leave empty to use the system default.
                                </p>
                            </div>

                            {/* Model Name Field */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-sm font-medium text-gray-700">
                                    Model Name
                                    <span className="ml-1 text-xs text-gray-400 font-normal">(Optional)</span>
                                </label>
                                <input
                                    type="text"
                                    value={modelName}
                                    onChange={(e) => { setModelName(e.target.value); setTestResult(null); }}
                                    placeholder="gpt-4o"
                                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                />
                                <p className="text-xs text-gray-400">
                                    e.g. gpt-4o, claude-3-5-sonnet, deepseek-chat, qwen-max
                                </p>
                            </div>

                            {/* ===== Connectivity Test ===== */}
                            <div className="flex flex-col gap-2">
                                <button
                                    onClick={handleTestConnection}
                                    disabled={testing || saving}
                                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 hover:border-blue-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                >
                                    {testing ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Zap className="w-4 h-4" />
                                    )}
                                    {testing ? "Testing..." : "Test Connection"}
                                </button>

                                {/* Test Result */}
                                {testResult && (
                                    <div
                                        className={`flex items-start gap-2 p-3 rounded-lg border text-xs leading-relaxed ${
                                            testResult.success
                                                ? "bg-green-50 border-green-200 text-green-700"
                                                : "bg-red-50 border-red-200 text-red-700"
                                        }`}
                                    >
                                        {testResult.success ? (
                                            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-green-500" />
                                        ) : (
                                            <XOctagon className="w-4 h-4 mt-0.5 shrink-0 text-red-500" />
                                        )}
                                        <div>
                                            <p className="font-medium">{testResult.message}</p>
                                            {testResult.success && testResult.model_used && (
                                                <p className="mt-0.5 opacity-80">
                                                    Model: {testResult.model_used}
                                                    {testResult.latency_ms !== undefined && ` · Latency: ${testResult.latency_ms}ms`}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* ========== Advanced Settings Section (Collapsible) ========== */}
                            <div className="border-t border-gray-100 pt-3 mt-1">
                                <button
                                    type="button"
                                    onClick={() => setShowAdvanced(!showAdvanced)}
                                    className="flex items-center gap-1.5 text-sm font-semibold text-gray-600 hover:text-gray-800 transition-colors w-full"
                                >
                                    <Settings2 className="w-4 h-4" />
                                    Advanced Settings
                                    {showAdvanced ? (
                                        <ChevronUp className="w-4 h-4 ml-auto" />
                                    ) : (
                                        <ChevronDown className="w-4 h-4 ml-auto" />
                                    )}
                                </button>

                                {showAdvanced && (
                                    <div className="flex flex-col gap-4 mt-3">
                                        {/* Thinking Level */}
                                        <div className="flex flex-col gap-1.5">
                                            <label className="text-sm font-medium text-gray-700">
                                                Thinking Level
                                            </label>
                                            <div className="flex gap-2">
                                                {THINKING_LEVELS.map((level) => (
                                                    <button
                                                        key={level}
                                                        type="button"
                                                        onClick={() => setDefaultThinkingLevel(level)}
                                                        className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium border transition-all ${
                                                            defaultThinkingLevel === level
                                                                ? "bg-gray-800 text-white border-gray-800"
                                                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                                                        }`}
                                                    >
                                                        {level.charAt(0).toUpperCase() + level.slice(1)}
                                                    </button>
                                                ))}
                                            </div>
                                            <p className="text-xs text-gray-400">
                                                Controls LLM reasoning depth. Higher = better quality but slower.
                                            </p>
                                        </div>

                                        {/* Agent Max Turns */}
                                        <div className="flex flex-col gap-1.5">
                                            <label className="text-sm font-medium text-gray-700">
                                                Agent Max Turns
                                            </label>
                                            <input
                                                type="number"
                                                value={agentMaxTurns}
                                                onChange={(e) => setAgentMaxTurns(Math.max(1, Math.min(200, parseInt(e.target.value) || 1)))}
                                                min={1}
                                                max={200}
                                                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                            />
                                            <p className="text-xs text-gray-400">
                                                Maximum agent loop iterations per request (default: 50).
                                            </p>
                                        </div>

                                        {/* Model Fallbacks */}
                                        <div className="flex flex-col gap-1.5">
                                            <label className="text-sm font-medium text-gray-700">
                                                Model Fallbacks
                                                <span className="ml-1 text-xs text-gray-400 font-normal">(Optional)</span>
                                            </label>
                                            <input
                                                type="text"
                                                value={modelFallbacks}
                                                onChange={(e) => setModelFallbacks(e.target.value)}
                                                placeholder="gpt-4o-mini, gpt-3.5-turbo"
                                                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                            />
                                            <p className="text-xs text-gray-400">
                                                Comma-separated fallback models when the primary model fails.
                                            </p>
                                        </div>

                                        {/* Context Compaction */}
                                        <div className="flex flex-col gap-2">
                                            <div className="flex items-center justify-between">
                                                <label className="text-sm font-medium text-gray-700">
                                                    Context Compaction
                                                </label>
                                                <button
                                                    type="button"
                                                    onClick={() => setContextCompactionEnabled(!contextCompactionEnabled)}
                                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                                                        contextCompactionEnabled ? "bg-blue-600" : "bg-gray-300"
                                                    }`}
                                                >
                                                    <span
                                                        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                                                            contextCompactionEnabled ? "translate-x-4.5" : "translate-x-0.5"
                                                        }`}
                                                    />
                                                </button>
                                            </div>
                                            <p className="text-xs text-gray-400">
                                                Automatically compress long conversation history to stay within model context limits.
                                            </p>
                                        </div>

                                        {/* Keep Recent Messages */}
                                        {contextCompactionEnabled && (
                                            <div className="flex gap-4">
                                                <div className="flex-1 flex flex-col gap-1.5">
                                                    <label className="text-sm font-medium text-gray-700">
                                                        Keep Recent
                                                    </label>
                                                    <input
                                                        type="number"
                                                        value={contextKeepRecent}
                                                        onChange={(e) => setContextKeepRecent(Math.max(1, parseInt(e.target.value) || 1))}
                                                        min={1}
                                                        className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                                    />
                                                    <p className="text-xs text-gray-400">
                                                        Messages kept during compaction.
                                                    </p>
                                                </div>
                                                <div className="flex-1 flex flex-col gap-1.5">
                                                    <label className="text-sm font-medium text-gray-700">
                                                        Min Messages
                                                    </label>
                                                    <input
                                                        type="number"
                                                        value={contextMinMessages}
                                                        onChange={(e) => setContextMinMessages(Math.max(1, parseInt(e.target.value) || 1))}
                                                        min={1}
                                                        className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all"
                                                    />
                                                    <p className="text-xs text-gray-400">
                                                        Min messages before compacting.
                                                    </p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* ===== Action Buttons ===== */}
                            <div className="flex flex-row gap-3 pt-2 border-t border-gray-100">
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium bg-gray-800 text-white hover:bg-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                >
                                    {saving ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Save className="w-4 h-4" />
                                    )}
                                    Save
                                </button>
                                <button
                                    onClick={handleClearAll}
                                    disabled={saving || (!currentSettings?.api_key_set && !currentSettings?.base_url && !currentSettings?.model_name)}
                                    className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium bg-white text-red-600 border border-red-200 hover:bg-red-50 hover:border-red-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Clear All
                                </button>
                            </div>
                        </div>
                    )}
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
};

export default SettingsModal;
