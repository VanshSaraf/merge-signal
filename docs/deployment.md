# Deployment

MergeSignal is prepared for manual deployment with the backend on Render and the frontend on Vercel. This repository does not include credentials, automatic deployment commands, or provider-specific secrets.

## Manual Sequence

1. Create a Render web service from the GitHub repository.
2. Use the root-level `render.yaml`; it points Render at `backend`.
3. Configure backend environment variables in Render.
4. Deploy the backend and verify `GET /health`.
5. Create a Vercel project with `frontend` as the project root.
6. Set `VITE_API_BASE_URL` to the deployed backend base URL.
7. Deploy the frontend.
8. Add the final Vercel origin to `MERGE_SIGNAL_CORS_ORIGINS` in Render.
9. Redeploy the backend so the CORS allowlist is active.
10. Run `python scripts/smoke_deployment.py <backend-url> --pull-request-url <public-pr-url>`.
11. Analyze a real public pull request in the frontend.

## Environment Variables

| Surface | Variable | Required | Notes |
| --- | --- | --- | --- |
| Backend | `MERGE_SIGNAL_ENVIRONMENT` | Yes | Use `production` on Render. Local development uses `development`. |
| Backend | `MERGE_SIGNAL_CORS_ORIGINS` | Yes in production | Comma-separated frontend origins. No wildcard is allowed in production. Trailing slashes are normalized. |
| Backend | `MERGE_SIGNAL_PROJECT_NAME` | No | Defaults to `MergeSignal`. |
| Backend | `GITHUB_API_BASE_URL` | No | Defaults to `https://api.github.com`. |
| Backend | `GITHUB_TOKEN` | No | Optional backend-only token for higher GitHub API limits. Leave empty for unauthenticated public requests. |
| Backend | `GITHUB_REQUEST_TIMEOUT_SECONDS` | No | Existing request timeout. |
| Backend | `GITHUB_MAX_RETRIES` | No | Existing retry count for transport/transient failures. |
| Backend | `GITHUB_RETRY_BASE_DELAY_SECONDS` | No | Existing retry backoff base. |
| Backend | `GITHUB_PER_PAGE` | No | Existing GitHub pagination page size. |
| Backend | `GITHUB_MAX_PAGES` | No | Existing GitHub pagination safety bound. |
| Backend | `GITHUB_USER_AGENT` | No | User-Agent sent to GitHub. |
| Backend | `PORT` | Provider-managed | Render supplies this automatically; `render.yaml` binds Uvicorn to `$PORT`. |
| Frontend | `VITE_API_BASE_URL` | Yes in production | Base URL of the deployed backend. Do not include secrets. |

## Render Backend

`render.yaml` installs from `backend/requirements.txt`, starts Uvicorn without development reload, binds to `0.0.0.0:$PORT`, and uses `/health` as the health check. The health endpoint returns local application status only and does not call GitHub, so health checks do not consume GitHub quota.

In production, `MERGE_SIGNAL_CORS_ORIGINS` must contain exact frontend origins, for example a Vercel production origin and any preview origins you intentionally allow. The backend rejects malformed origins and wildcard production CORS.

## Vercel Frontend

Set the Vercel project root to `frontend`. `frontend/vercel.json` runs `npm run build`, serves `dist`, and rewrites routes to `index.html` for React Router client-side navigation.

Production builds must have `VITE_API_BASE_URL` configured. Local development may omit it and use the localhost backend fallback.

## Smoke Test

Run the standard-library smoke script after both services are deployed:

```bash
python scripts/smoke_deployment.py https://backend.example.com \
  --pull-request-url https://github.com/owner/repository/pull/123
```

The script checks `/health`, `/openapi.json`, and optionally the snapshot endpoint. It prints concise pass/fail lines and does not print tokens or full response bodies.

## Rate Limits

Without `GITHUB_TOKEN`, GitHub requests are unauthenticated and subject to lower public rate limits. A backend-only token can improve rate limits, but it must be configured only in Render and must never be exposed through Vite variables.

## Troubleshooting

- CORS failures usually mean the final Vercel origin is missing from `MERGE_SIGNAL_CORS_ORIGINS` or includes an invalid path/trailing route instead of just the origin.
- Backend unavailable messages in the frontend usually mean `VITE_API_BASE_URL` is missing, malformed, or pointing to the wrong backend service.
- Render logs are the first place to inspect backend startup, settings validation, and GitHub upstream failures.
- Vercel deployment logs are the first place to inspect frontend build failures and missing environment variables.
- Roll back through the provider dashboard by redeploying the previous successful deployment, then restore the matching environment variables if they changed.

## Current Limitations

MergeSignal currently has no authentication, persistence, historical report storage, Redis, background workers, GitHub App installation, webhooks, or deployment automation. It analyzes a single public GitHub pull-request snapshot at a time.
