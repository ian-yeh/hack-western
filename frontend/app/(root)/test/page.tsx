"use client";

import { useState } from "react";
import {
  Sparkles,
  Play,
  Loader2,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const router = useRouter();
  const [serverUrl, setServerUrl] = useState("");
  const [testPrompt, setTestPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);

  const handleRunTests = async () => {
    if (!serverUrl || !testPrompt || isRunning) return;

    setIsRunning(true);

    // simple client-side session id
    const sessionId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}`;

    const params = new URLSearchParams({
      serverUrl,
      prompt: testPrompt,
    });

    console.log(params.toString())

    router.push(`/test/${sessionId}?${params.toString()}`);
    setIsRunning(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] via-[#0f0a1f] to-[#1a0a1f]">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Link href={"/"}>
          <ArrowLeft className="h-4 w-4 text-white mb-8" />
        </Link>

        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs backdrop-blur-sm mb-4">
            <Sparkles className="h-3 w-3 text-purple-400" />
            <p className="text-white">AI Testing Dashboard</p>
          </div>
          <h1 className="text-4xl font-semibold text-white mb-2">
            Test Your App
          </h1>
          <p className="text-gray-400">
            Run AI-powered tests on your local development environment.
          </p>
        </div>

        {/* Main Content */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Input Section */}
          <Card className="bg-[#1a1a2e]/50 border-gray-800 backdrop-blur-sm">
            <CardContent className="p-6 space-y-6">
              <div className="space-y-2">
                <Label
                  htmlFor="server-url"
                  className="text-white text-sm font-medium"
                >
                  Local Dev Server URL
                </Label>
                <Input
                  id="server-url"
                  placeholder="http://localhost:3000"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  className="bg-[#0f0f1e] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 focus:ring-purple-500/20"
                />
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="test-prompt"
                  className="text-white text-sm font-medium"
                >
                  Test Instructions
                </Label>
                <Textarea
                  id="test-prompt"
                  placeholder="Describe what you want to test... e.g., 'Test the login flow with valid credentials' or 'Check if all navigation links work'"
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  rows={6}
                  className="bg-[#0f0f1e] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 focus:ring-purple-500/20 resize-none"
                />
              </div>

              <Button
                onClick={handleRunTests}
                disabled={!serverUrl || !testPrompt || isRunning}
                className="w-full bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-700 hover:to-purple-600 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Preparing test session...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Run Tests
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Info / Preview Section */}
          <Card className="bg-[#1a1a2e]/50 border-gray-800 backdrop-blur-sm">
            <CardContent className="p-6">
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <AlertCircle className="h-10 w-10 text-gray-500 mb-4" />
                <p className="text-white font-medium mb-2">
                  No tests started in this session yet
                </p>
                <p className="text-gray-400 text-sm max-w-md">
                  Configure your test on the left and click{" "}
                  <span className="font-semibold">“Run Tests”</span>. You’ll be
                  taken to a ChatGPT-style view where you can see detailed
                  results, screenshots, and continue prompting the AI.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
