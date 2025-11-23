"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  History,
  Loader2,
  Send,
  Sparkles,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type TestStatus = "passed" | "failed" | "running";

interface TestResult {
  id: string;
  name: string;
  status: TestStatus;
  message?: string;
  duration?: number;
  screenshots?: string[];
}

interface TestRun {
  id: string;
  prompt: string;
  url: string;
  createdAt: string;
  results: TestResult[];
  status: "running" | "completed" | "failed";
}

interface Props {
  sessionId: string;
  initialUrl: string;
  initialPrompt: string;
}

export default function TestSessionClient({
  sessionId,
  initialUrl,
  initialPrompt,
}: Props) {
  const [serverUrl] = useState(initialUrl);
  const [currentPrompt, setCurrentPrompt] = useState(initialPrompt);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const selectedRun = useMemo(
    () => runs.find((r) => r.id === selectedRunId) ?? runs[runs.length - 1],
    [runs, selectedRunId]
  );

  const getStatusIcon = (status: TestStatus) => {
    switch (status) {
      case "passed":
        return <CheckCircle2 className="h-4 w-4 text-green-400" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-400" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
    }
  };

  const totalPassed =
    selectedRun?.results.filter((r) => r.status === "passed").length ?? 0;
  const totalFailed =
    selectedRun?.results.filter((r) => r.status === "failed").length ?? 0;

  const runTests = useCallback(async (promptToRun: string) => {
    if (!serverUrl || !promptToRun) return;

    setIsRunning(true);

    const runId = crypto.randomUUID();
    const newRun: TestRun = {
      id: runId,
      prompt: promptToRun,
      url: serverUrl,
      createdAt: new Date().toISOString(),
      results: [],
      status: "running",
    };

    setRuns((prev) => [...prev, newRun]);
    setSelectedRunId(runId);

    try {
      const response = await fetch("/api/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ serverUrl, prompt: promptToRun, sessionId }),
      });

      if (!response.ok) throw new Error("Test execution failed");

      const data = await response.json();
      const results: TestResult[] = data.results || [];

      setRuns((prev) =>
        prev.map((run) =>
          run.id === runId ? { ...run, results, status: "completed" } : run
        )
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unexpected error occurred";
      setRuns((prev) =>
        prev.map((run) =>
          run.id === runId
            ? {
                ...run,
                status: "failed",
                results: [
                  { id: "error", name: "Test Execution Failed", status: "failed", message },
                ],
              }
            : run
        )
      );
    } finally {
      setIsRunning(false);
    }
  }, [serverUrl, sessionId]);

  useEffect(() => {
    if (initialPrompt && initialUrl && runs.length === 0) {
      runTests(initialPrompt);
    }
  }, [initialPrompt, initialUrl, runTests, runs.length]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] via-[#0f0a1f] to-[#1a0a1f] text-white flex">

      {/* SIDEBAR */}
      <aside className="hidden md:flex md:w-72 border-r border-purple-900/30 bg-[#070711]/80 backdrop-blur-sm flex-col">
        <div className="px-4 py-4 border-b border-purple-900/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span className="text-sm font-semibold">Test Sessions</span>
          </div>
          <History className="h-4 w-4 text-gray-500" />
        </div>

        <div className="flex-1 overflow-y-auto">
          {runs.length === 0 ? (
            <div className="px-4 py-6 text-xs text-gray-500">
              No previous test sessions.
            </div>
          ) : (
            <ul className="py-2">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    onClick={() => setSelectedRunId(run.id)}
                    className={`w-full text-left px-4 py-3 text-xs flex items-start gap-2 hover:bg-purple-900/20 ${
                      selectedRun?.id === run.id ? "bg-purple-900/25" : ""
                    }`}
                  >
                    {getStatusIcon(
                      run.status === "running"
                        ? "running"
                        : run.results.some((r) => r.status === "failed")
                        ? "failed"
                        : "passed"
                    )}
                    <div className="flex-1">
                      <p className="font-medium line-clamp-2">{run.prompt}</p>
                      <p className="text-[0.6rem] text-gray-500 mt-1">
                        {new Date(run.createdAt).toLocaleTimeString()} · {run.url}
                      </p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* MAIN PANEL */}
      <div className="flex-1 flex flex-col">

        {/* TOP BAR */}
        <header className="border-b border-purple-900/30 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/test">
              <Button variant="ghost" size="icon" className="text-gray-300">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-semibold">AI Test Session</h1>
              <p className="text-xs text-gray-400">Session ID: {sessionId}</p>
            </div>
          </div>

          {!!selectedRun && (
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <div className="flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4 text-green-400" />
                <span>{totalPassed} passed</span>
              </div>
              <div className="flex items-center gap-1">
                <XCircle className="h-4 w-4 text-red-400" />
                <span>{totalFailed} failed</span>
              </div>
            </div>
          )}
        </header>

        {/* CHAT AREA */}
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-6">

          {selectedRun && (
            <>
              {/* USER MESSAGE */}
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-purple-600 flex items-center justify-center">U</div>
                <div className="bg-[#151521] border border-gray-700 rounded-xl px-4 py-3 max-w-3xl">
                  <p className="text-sm whitespace-pre-line">{selectedRun.prompt}</p>
                </div>
              </div>

              {/* AI RESPONSE */}
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-emerald-500 flex items-center justify-center">AI</div>
                <div className="flex-1 max-w-3xl space-y-4">
                  {selectedRun.results.map((result) => (
                    <Card key={result.id} className="bg-[#0f0f1e] border-gray-800">
                      <CardContent className="p-4 space-y-2">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(result.status)}
                          <span className="font-medium">{result.name}</span>
                        </div>
                        {result.message && <p className="text-xs text-gray-400">{result.message}</p>}
                        {result.duration && <p className="text-xs text-gray-500">{result.duration}ms</p>}

                        {result.screenshots?.length ? (
                          <div className="grid grid-cols-2 gap-2 mt-3">
                            {result.screenshots.map((src, idx) => (
                              <Image
                                key={idx}
                                src={src}
                                alt="screenshot"
                                width={400}
                                height={300}
                                className="rounded-lg border border-gray-700"
                              />
                            ))}
                          </div>
                        ) : null}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </>
          )}
        </main>

        {/* RE-PROMPT INPUT */}
        <footer className="border-t border-purple-900/30 p-4 bg-[#0d0d14]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!currentPrompt || isRunning) return;
              runTests(currentPrompt);
            }}
            className="max-w-3xl mx-auto flex flex-col gap-2"
          >
            <Textarea
              value={currentPrompt}
              onChange={(e) => setCurrentPrompt(e.target.value)}
              placeholder="Ask follow-up test instructions..."
              className="bg-[#13131f] border-gray-700 text-sm"
            />
            <div className="flex justify-end">
              <Button disabled={!currentPrompt || isRunning} className="bg-purple-600">
                {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </form>
        </footer>
      </div>
    </div>
  );
}
