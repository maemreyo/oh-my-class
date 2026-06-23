---
title: "Frontend Wiring + Approval UI"
status: done
labels: []
created: 2026-06-23
github: 12
---

## What to build

Wire the Next.js frontend to the gateway API and implement the approval workflow UI. Files exist with partial implementations.

## Current State

```
apps/web/src/
├── hooks/
│   ├── use-run.ts          — EXISTS (partial, needs API wiring)
│   └── use-approval.ts     — EXISTS (partial, needs API wiring)
├── components/
│   └── approval-modal.tsx   — EXISTS (partial, needs enhancement)
├── lib/
│   └── api-client.ts       — EXISTS (complete)
└── app/(dashboard)/
    ├── page.tsx             — EXISTS (dashboard)
    └── runs/[runId]/page.tsx — EXISTS (run detail)
```

## Implementation Spec

### 1. Update `apps/web/src/hooks/use-run.ts`

Replace or enhance existing hook:

```typescript
"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface RunRequest {
    raw_request: string;
    class_info: {
        grade: number;
        subject: string;
        student_count?: number;
        language?: string;
    };
    teacher_id: string;
}

interface RunResponse {
    run_id: string;
    status: string;
    state?: Record<string, unknown>;
}

export function useCreateRun() {
    return useMutation<RunResponse, Error, RunRequest>({
        mutationFn: async (request) => {
            const response = await apiClient.post<RunResponse>("/run", request);
            return response;
        },
    });
}

export function useRun(runId: string | null) {
    return useQuery<RunResponse>({
        queryKey: ["run", runId],
        queryFn: async () => {
            if (!runId) throw new Error("No run ID");
            const response = await apiClient.get<RunResponse>(`/run/${runId}`);
            return response;
        },
        enabled: !!runId,
        refetchInterval: 5000, // Poll every 5 seconds
    });
}

export function useRunStatus(runId: string | null) {
    // SSE connection for real-time updates
    const subscribe = (callback: (event: MessageEvent) => void) => {
        if (!runId) return () => {};
        
        const eventSource = new EventSource(
            `${process.env.NEXT_PUBLIC_GATEWAY_URL}/run/${runId}/status`
        );
        
        eventSource.onmessage = callback;
        eventSource.onerror = (error) => {
            console.error("SSE error:", error);
        };
        
        return () => eventSource.close();
    };
    
    return { subscribe };
}
```

### 2. Update `apps/web/src/hooks/use-approval.ts`

Replace or enhance existing hook:

```typescript
"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface ApprovalRequest {
    action: "approve" | "edit" | "reject";
    feedback?: string;
    edits?: Record<string, unknown>;
}

interface ApprovalResponse {
    status: string;
    message: string;
    run_id: string;
}

export function useApproveRun(runId: string) {
    return useMutation<ApprovalResponse, Error, ApprovalRequest>({
        mutationFn: async (request) => {
            const endpoint = request.action === "reject" 
                ? `/run/${runId}/reject`
                : `/run/${runId}/approve`;
            
            const response = await apiClient.post<ApprovalResponse>(endpoint, request);
            return response;
        },
    });
}

export function useRejectRun(runId: string) {
    return useMutation<ApprovalResponse, Error, { feedback: string }>({
        mutationFn: async ({ feedback }) => {
            const response = await apiClient.post<ApprovalResponse>(
                `/run/${runId}/reject`,
                { action: "reject", feedback }
            );
            return response;
        },
    });
}
```

### 3. Update `apps/web/src/components/approval-modal.tsx`

Enhance with full approval workflow:

```tsx
"use client";

import { useState } from "react";
import { useApproveRun, useRejectRun } from "@/hooks/use-approval";

interface ApprovalModalProps {
    runId: string;
    gateType: "blueprint_approval" | "content_approval";
    data: {
        lesson_plan?: Record<string, unknown>;
        artifacts?: Record<string, unknown>[];
        quality_scores?: Record<string, unknown>;
    };
    onClose: () => void;
    onApproved?: () => void;
    onRejected?: () => void;
}

export function ApprovalModal({
    runId,
    gateType,
    data,
    onClose,
    onApproved,
    onRejected,
}: ApprovalModalProps) {
    const [feedback, setFeedback] = useState("");
    const [activeTab, setActiveTab] = useState<"preview" | "feedback">("preview");
    
    const approveMutation = useApproveRun(runId);
    const rejectMutation = useRejectRun(runId);
    
    const handleApprove = async () => {
        await approveMutation.mutateAsync({ action: "approve" });
        onApproved?.();
        onClose();
    };
    
    const handleReject = async () => {
        if (!feedback.trim()) {
            alert("Feedback required for rejection");
            return;
        }
        await rejectMutation.mutateAsync({ feedback });
        onRejected?.();
        onClose();
    };
    
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg max-w-4xl max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b">
                    <h2 className="text-xl font-semibold">
                        {gateType === "blueprint_approval" 
                            ? "Review Lesson Plan" 
                            : "Review Generated Content"}
                    </h2>
                </div>
                
                {/* Tabs */}
                <div className="flex border-b">
                    <button
                        className={`px-4 py-2 ${activeTab === "preview" ? "border-b-2 border-blue-500" : ""}`}
                        onClick={() => setActiveTab("preview")}
                    >
                        Preview
                    </button>
                    <button
                        className={`px-4 py-2 ${activeTab === "feedback" ? "border-b-2 border-blue-500" : ""}`}
                        onClick={() => setActiveTab("feedback")}
                    >
                        Feedback
                    </button>
                </div>
                
                {/* Content */}
                <div className="p-4 overflow-y-auto max-h-[60vh]">
                    {activeTab === "preview" && (
                        <div>
                            {gateType === "blueprint_approval" && data.lesson_plan && (
                                <pre className="bg-gray-100 p-4 rounded overflow-auto">
                                    {JSON.stringify(data.lesson_plan, null, 2)}
                                </pre>
                            )}
                            {gateType === "content_approval" && data.artifacts && (
                                <div className="space-y-4">
                                    {data.artifacts.map((artifact, i) => (
                                        <div key={i} className="border rounded p-4">
                                            <h3 className="font-medium">{artifact.title || `Artifact ${i + 1}`}</h3>
                                            <pre className="bg-gray-100 p-2 mt-2 rounded text-sm overflow-auto">
                                                {JSON.stringify(artifact, null, 2)}
                                            </pre>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    
                    {activeTab === "feedback" && (
                        <div>
                            <label className="block mb-2 font-medium">
                                Feedback {activeTab === "feedback" && "(required for rejection)"}
                            </label>
                            <textarea
                                className="w-full border rounded p-2 h-32"
                                value={feedback}
                                onChange={(e) => setFeedback(e.target.value)}
                                placeholder="Provide feedback for rejection..."
                            />
                        </div>
                    )}
                </div>
                
                {/* Footer */}
                <div className="p-4 border-t flex justify-end gap-2">
                    <button
                        className="px-4 py-2 border rounded hover:bg-gray-100"
                        onClick={onClose}
                    >
                        Cancel
                    </button>
                    <button
                        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                        onClick={handleReject}
                        disabled={rejectMutation.isPending}
                    >
                        {rejectMutation.isPending ? "Rejecting..." : "Reject"}
                    </button>
                    <button
                        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                        onClick={handleApprove}
                        disabled={approveMutation.isPending}
                    >
                        {approveMutation.isPending ? "Approving..." : "Approve"}
                    </button>
                </div>
            </div>
        </div>
    );
}
```

### 4. Update `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx`

Enhance with SSE and approval modal:

```tsx
"use client";

import { useState, useEffect } from "react";
import { useRun, useRunStatus } from "@/hooks/use-run";
import { ApprovalModal } from "@/components/approval-modal";

export default function RunDetailPage({ params }: { params: { runId: string } }) {
    const { runId } = params;
    const { data: run, isLoading } = useRun(runId);
    const { subscribe } = useRunStatus(runId);
    const [events, setEvents] = useState<string[]>([]);
    const [approvalGate, setApprovalGate] = useState<{
        type: "blueprint_approval" | "content_approval";
        data: Record<string, unknown>;
    } | null>(null);
    
    // Subscribe to SSE events
    useEffect(() => {
        const unsubscribe = subscribe((event) => {
            const data = JSON.parse(event.data);
            setEvents((prev) => [...prev, `${event.event}: ${JSON.stringify(data)}`]);
            
            // Check for approval gates
            if (event.event === "interrupt" && data.gate) {
                setApprovalGate({
                    type: data.gate,
                    data: data,
                });
            }
        });
        
        return unsubscribe;
    }, [subscribe]);
    
    if (isLoading) {
        return <div className="p-8">Loading...</div>;
    }
    
    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold mb-4">Run: {runId}</h1>
            
            {/* Status */}
            <div className="mb-6">
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                    {run?.status || "Unknown"}
                </span>
            </div>
            
            {/* Events Log */}
            <div className="mb-6">
                <h2 className="text-lg font-semibold mb-2">Events</h2>
                <div className="bg-gray-100 rounded p-4 max-h-64 overflow-auto font-mono text-sm">
                    {events.length === 0 ? (
                        <div className="text-gray-500">Waiting for events...</div>
                    ) : (
                        events.map((event, i) => (
                            <div key={i} className="border-b border-gray-200 py-1">
                                {event}
                            </div>
                        ))
                    )}
                </div>
            </div>
            
            {/* Run Details */}
            {run?.state && (
                <div>
                    <h2 className="text-lg font-semibold mb-2">State</h2>
                    <pre className="bg-gray-100 rounded p-4 overflow-auto text-sm">
                        {JSON.stringify(run.state, null, 2)}
                    </pre>
                </div>
            )}
            
            {/* Approval Modal */}
            {approvalGate && (
                <ApprovalModal
                    runId={runId}
                    gateType={approvalGate.type}
                    data={approvalGate.data}
                    onClose={() => setApprovalGate(null)}
                    onApproved={() => {
                        setApprovalGate(null);
                        // Refresh run data
                    }}
                    onRejected={() => {
                        setApprovalGate(null);
                        // Refresh run data
                    }}
                />
            )}
        </div>
    );
}
```

## Acceptance criteria

- [ ] `useCreateRun()` calls `POST /run` with correct payload
- [ ] `useRun()` calls `GET /run/{runId}` and polls
- [ ] `useRunStatus()` subscribes to SSE events
- [ ] `useApproveRun()` calls `POST /run/{runId}/approve`
- [ ] `useRejectRun()` calls `POST /run/{runId}/reject` with feedback
- [ ] `ApprovalModal` displays lesson plan for Step 04
- [ ] `ApprovalModal` displays artifacts for Step 11
- [ ] `ApprovalModal` has Approve/Reject buttons
- [ ] `ApprovalModal` requires feedback for rejection
- [ ] Run detail page shows SSE events in real-time
- [ ] Run detail page shows approval modal when gate triggered
- [ ] Unit test: hooks call correct endpoints
- [ ] E2E test: approval workflow works in browser

## Test suite

Create `apps/web/tests/hooks.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useCreateRun, useRun } from "@/hooks/use-run";
import { useApproveRun, useRejectRun } from "@/hooks/use-approval";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

const wrapper = ({ children }: { children: React.ReactNode }) => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useCreateRun", () => {
    it("calls POST /run", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ run_id: "test-123", status: "created" }),
        });
        global.fetch = mockFetch;
        
        const { result } = renderHook(() => useCreateRun(), { wrapper });
        
        await result.current.mutateAsync({
            raw_request: "Teach photosynthesis",
            class_info: { grade: 5, subject: "science" },
            teacher_id: "t-001",
        });
        
        expect(mockFetch).toHaveBeenCalledWith(
            expect.stringContaining("/run"),
            expect.objectContaining({ method: "POST" })
        );
    });
});

describe("useApproveRun", () => {
    it("calls POST /run/{runId}/approve", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ status: "resumed", message: "Approved", run_id: "test-123" }),
        });
        global.fetch = mockFetch;
        
        const { result } = renderHook(() => useApproveRun("test-123"), { wrapper });
        
        await result.current.mutateAsync({ action: "approve" });
        
        expect(mockFetch).toHaveBeenCalledWith(
            expect.stringContaining("/run/test-123/approve"),
            expect.objectContaining({ method: "POST" })
        );
    });
});
```

Create `apps/web/tests/approval-modal.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ApprovalModal } from "@/components/approval-modal";

describe("ApprovalModal", () => {
    const mockProps = {
        runId: "test-123",
        gateType: "blueprint_approval" as const,
        data: {
            lesson_plan: { topic: "Photosynthesis", grade_level: "Grade 5" },
        },
        onClose: vi.fn(),
        onApproved: vi.fn(),
        onRejected: vi.fn(),
    };

    it("displays lesson plan", () => {
        render(<ApprovalModal {...mockProps} />);
        
        expect(screen.getByText("Photosynthesis")).toBeInTheDocument();
        expect(screen.getByText("Grade 5")).toBeInTheDocument();
    });

    it("approve button calls onApproved", async () => {
        render(<ApprovalModal {...mockProps} />);
        
        fireEvent.click(screen.getByText("Approve"));
        
        await waitFor(() => {
            expect(mockProps.onApproved).toHaveBeenCalled();
        });
    });

    it("reject requires feedback", async () => {
        render(<ApprovalModal {...mockProps} />);
        
        // Try to reject without feedback
        fireEvent.click(screen.getByText("Reject"));
        
        // Should show alert or not call onRejected
        await waitFor(() => {
            expect(mockProps.onRejected).not.toHaveBeenCalled();
        });
    });
});
```

## File paths

| File | Action |
|------|--------|
| `apps/web/src/hooks/use-run.ts` | MODIFY: Enhance with create, status, SSE |
| `apps/web/src/hooks/use-approval.ts` | MODIFY: Enhance with approve, reject |
| `apps/web/src/components/approval-modal.tsx` | MODIFY: Enhance with full workflow |
| `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx` | MODIFY: Add SSE and modal |
| `apps/web/tests/hooks.test.ts` | CREATE: Hook tests |
| `apps/web/tests/approval-modal.test.tsx` | CREATE: Component tests |

## Dependencies

- `@tanstack/react-query` — Data fetching (already installed)
- `@/lib/api-client` — API client (already exists)
- `next` — Next.js framework (already installed)
- `react` — React (already installed)

## Edge cases to handle

1. No run ID → don't subscribe to SSE
2. SSE connection fails → log error, don't crash
3. Multiple approval gates → only show one at a time
4. Network error on approve/reject → show error message
5. Run already completed → don't show approval modal
