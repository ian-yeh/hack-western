// app/(root)/test/[sessionId]/page.tsx

// 1) Make sure this file is a SERVER component (NO "use client" here)

import TestSessionClient from "./test-session-client";

// 2) Force this page to be rendered dynamically on every request
export const dynamic = "force-dynamic";

type PageProps = {
  params: { sessionId: string };
  searchParams: { [key: string]: string | string[] | undefined };
};

export default function TestSessionPage({ params, searchParams }: PageProps) {
  // Safely read query params from the server-rendered props
  const urlParam =
    typeof searchParams.serverUrl === "string" ? searchParams.serverUrl : "";

  const promptParam =
    typeof searchParams.prompt === "string" ? searchParams.prompt : "";

  // Optional: log everything to confirm it's working
  console.log("searchParams:", searchParams);
  console.log("serverUrl:", urlParam);
  console.log("prompt:", promptParam);

  return (
    <TestSessionClient
      sessionId={params.sessionId}
      initialUrl={urlParam}
      initialPrompt={promptParam}
    />
  );
}
