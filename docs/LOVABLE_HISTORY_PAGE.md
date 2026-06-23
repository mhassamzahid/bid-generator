# Bid History And Revisions: Lovable Prompt

Paste the prompt below into Lovable.

---

Update the existing BidCraft React + Tailwind app with a full bid-history and AI revision workflow. Keep the current dark professional SaaS visual language, existing sidebar, React/Tailwind stack, and native `fetch` + `ReadableStream` SSE handling. The FastAPI base URL remains `http://localhost:8000`, and no authentication is required.

## Add A New Sidebar Page

Add a sidebar item named `Bid History` with a history/clock icon. This page is separate from the existing `History` job list and is the workspace for viewing all versions of one job's bid and asking AI to revise a selected version.

### Page Behaviour

1. Fetch `GET /api/v1/jobs/?skip=0&limit=20` when the page opens. Display jobs in a compact left column, newest first. Each item shows title, budget, skills, and date. Include a `Load more` button using the same endpoint and increasing `skip`.

2. When the user selects a job, fetch all of its bid versions with:

```text
GET /api/v1/jobs/{job_id}/bids
```

The response is newest first:

```json
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "bid_text": "...",
    "is_manual": false,
    "created_at": "2024-..."
  }
]
```

3. In the main workspace, show a version timeline/list and a document-style bid editor panel. The newest version should be selected by default. Each version should show its number, timestamp, and either `Manual Reference` when `is_manual` is true or `AI Generated` otherwise. Clicking a version loads its full `bid_text` into the document panel. Include a copy-to-clipboard icon button.

4. Beneath the selected bid, provide an `Edit with AI` textarea labelled `What should change?`, for example: `Make the opening more direct and mention my Shopify migration experience.` Add a primary `Generate revision` button. Disable it when no bid is selected, the instruction is blank, or a revision is streaming.

5. On submit, POST to this endpoint using the selected job and selected bid IDs:

```text
POST /api/v1/jobs/{job_id}/bids/{bid_id}/revise
Content-Type: application/json

{
  "instruction": "Make the opening more direct and mention my Shopify migration experience."
}
```

This endpoint returns SSE. Use `fetch`, read `response.body` with `ReadableStream`, split lines, and process each line prefixed with `data: `. Do not use `EventSource` because the request is POST.

SSE events:

```json
{"type":"chunk","content":"some text"}
```

Append each chunk to a temporary new version in the bid document panel with a pulsing cursor while it streams.

```json
{"type":"done","bid_id":"uuid","job_id":"uuid"}
```

When `done` arrives, refetch `GET /api/v1/jobs/{job_id}/bids`, select the new bid using `bid_id`, clear the edit textarea, and show a success toast. The backend automatically stores both the edit instruction and AI response in its memory, so the frontend must not make any separate memory write request.

6. If a revision request is already streaming and the user submits another instruction, cancel the active request first with `AbortController`. Provide a small icon-only cancel button during streaming.

7. Add useful states: loading skeletons for jobs and versions, empty state when no jobs/bids exist, inline API error message, disabled button states, and a `Retry` action for failed loads. On mobile, stack the job selector above the workspace and keep version selection horizontally scrollable.

## Existing API Notes

- `GET /api/v1/jobs/{job_id}` returns the job details for showing the full job description in a collapsible `Job details` panel.
- `GET /api/v1/jobs/{job_id}/bid` still returns only the latest bid, but use `GET /api/v1/jobs/{job_id}/bids` for this new page because it returns every version.
- `GET /api/v1/memory/?skip=0&limit=20` is read-only diagnostic data. Do not show raw memory on the primary workflow and do not POST to it.

## Implementation Details

- Reuse the app's existing API base URL configuration and existing SSE helper where possible.
- Use TypeScript types for `Job`, `Bid`, revision request, and stream events.
- Keep the current visual design: restrained dark surfaces, document/editor output area, chips for skills, Lucide icons, 8px or smaller corner radii, and no nested cards.
- Do not change the existing Generate Bid, Add Reference Bid, or original History page behaviour.
