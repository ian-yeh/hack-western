"use client"

import { useState } from "react"
import { Sparkles, Play, CheckCircle2, XCircle, Loader2, AlertCircle, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import Link from "next/link"

interface TestResult {
  id: string
  name: string
  status: "passed" | "failed" | "running"
  message?: string
  duration?: number
}

export default function DashboardPage() {
  const [serverUrl, setServerUrl] = useState("")
  const [testPrompt, setTestPrompt] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [testResults, setTestResults] = useState<TestResult[]>([])

  const handleRunTests = async () => {
    if (!serverUrl || !testPrompt) return

    setIsRunning(true)
    setTestResults([])

    try {
      const response = await fetch("/api/test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          serverUrl,
          prompt: testPrompt,
        }),
      })

      if (!response.ok) {
        throw new Error("Test execution failed")
      }

      const data = await response.json()
      setTestResults(data.results || [])
    } catch (error) {
      console.error("[v0] Test execution error:", error)
      setTestResults([
        {
          id: "error",
          name: "Test Execution Failed",
          status: "failed",
          message: error instanceof Error ? error.message : "An error occurred",
        },
      ])
    } finally {
      setIsRunning(false)
    }
  }

  const getStatusIcon = (status: TestResult["status"]) => {
    switch (status) {
      case "passed":
        return <CheckCircle2 className="h-5 w-5 text-green-400" />
      case "failed":
        return <XCircle className="h-5 w-5 text-red-400" />
      case "running":
        return <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
    }
  }

  const passedCount = testResults.filter((t) => t.status === "passed").length
  const failedCount = testResults.filter((t) => t.status === "failed").length

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] via-[#0f0a1f] to-[#1a0a1f]">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Link href={"/"}>
          <ArrowLeft className="h-4 w-4 text-white mb-8"/>
        </Link>
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs backdrop-blur-sm mb-4">
            <Sparkles className="h-3 w-3 text-purple-400" />
            <p className="text-white">AI Testing Dashboard</p>
          </div>
          <h1 className="text-4xl font-semibold text-white mb-2">Test Your App</h1>
          <p className="text-gray-400">Run AI-powered tests on your local development environment</p>
        </div>

        {/* Main Content */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Input Section */}
          <Card className="bg-[#1a1a2e]/50 border-gray-800 backdrop-blur-sm">
            <CardContent className="p-6 space-y-6">
              <div className="space-y-2">
                <Label htmlFor="server-url" className="text-white text-sm font-medium">
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
                <Label htmlFor="test-prompt" className="text-white text-sm font-medium">
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
                    Running Tests...
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

          {/* Results Section */}
          <Card className="bg-[#1a1a2e]/50 border-gray-800 backdrop-blur-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Test Results</h2>
                {testResults.length > 0 && (
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                      <span className="text-gray-400">{passedCount}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <XCircle className="h-4 w-4 text-red-400" />
                      <span className="text-gray-400">{failedCount}</span>
                    </div>
                  </div>
                )}
              </div>

              {testResults.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <AlertCircle className="h-12 w-12 text-gray-600 mb-4" />
                  <p className="text-gray-500 text-sm">
                    No tests run yet. Configure your test above and click "Run Tests".
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[500px] overflow-y-auto">
                  {testResults.map((result) => (
                    <div
                      key={result.id}
                      className="p-4 rounded-lg bg-[#0f0f1e] border border-gray-800 hover:border-gray-700 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        {getStatusIcon(result.status)}
                        <div className="flex-1 min-w-0">
                          <p className="text-white font-medium text-sm mb-1">{result.name}</p>
                          {result.message && <p className="text-gray-400 text-xs leading-relaxed">{result.message}</p>}
                          {result.duration && <p className="text-gray-600 text-xs mt-2">{result.duration}ms</p>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
