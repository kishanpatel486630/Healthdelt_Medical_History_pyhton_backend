# AI Agent Setup (Doctor / Patient / Admin)

This project now includes a role-aware assistant endpoint:

- `POST /api/assistant/query`
- `POST /api/assistant/feedback`

It works in two modes:

1. Built-in knowledge mode (default, no API key required)
2. LLM mode (optional) when `OPENAI_API_KEY` is configured

It also includes docs/runbook retrieval from markdown files under `docs/` for richer project-specific answers.

## Request

```json
{
  "query": "How do I upload my report?",
  "context": {
    "feature": "reports"
  }
}
```

## Response

```json
{
  "success": true,
  "role": "PATIENT",
  "queryLogId": "9f9e3f5b-4ee0-4b9f-9f90-8be95ca3f37f",
  "assistant": {
    "answer": "Patient support: ...",
    "source": "knowledge-base",
    "confidence": 0.92,
    "actions": [
      {
        "label": "Upload a report",
        "method": "POST",
        "endpoint": "/api/reports/upload",
        "hint": "Attach report file and metadata like reportType, category, and labName."
      }
    ]
  }
}
```

## Feedback request

```json
{
  "queryLogId": "9f9e3f5b-4ee0-4b9f-9f90-8be95ca3f37f",
  "helpful": true,
  "feedback": "This answer solved my issue"
}
```

## Environment variables

Add to `.env` (optional for LLM mode):

```env
OPENAI_API_KEY=
AI_ASSISTANT_MODEL=gpt-4o-mini
```

If `OPENAI_API_KEY` is empty, the assistant still answers using built-in project knowledge and safe fallbacks.

## Security and role behavior

- Endpoint requires authenticated user token.
- The assistant receives caller role (`PATIENT`, `DOCTOR`, `ADMIN`) and provides role-focused guidance.
- Query/answer interactions are logged for continuous improvement.
- Users can mark responses helpful or not helpful via feedback endpoint.
- For emergency-like language, it appends a safety note.
- It is a support assistant, not a diagnostic replacement.

## How to improve "training" quality

To make it behave like a fully trained project assistant over time:

1. Add more knowledge entries in `app/services/ai_service.py`.
2. Add FAQ pairs from real support tickets.
3. Log unresolved queries and convert them into new knowledge items.
4. Add role-specific examples and expected responses in tests.
5. Optionally connect retrieval over docs and SOP files.
