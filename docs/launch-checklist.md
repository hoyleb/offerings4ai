# Offering4AI Launch Checklist

## Brand and domain

- Buy `offering4ai.com` as the primary domain.
- Buy `offerings2ai.com` only if you want a cheap defensive redirect.

## DNS and routing

### Single VM path

- Point `A` record for `offering4ai.com` to the VM public IP.
- Point `A` record for `www.offering4ai.com` to the same IP or redirect it.
- If you own `offerings2ai.com`, configure a 301 redirect to `https://offering4ai.com`.

### Cloud Run path

- Map the custom domain to the frontend service or to an HTTPS load balancer.
- Ensure the API has a stable public URL and update `PUBLIC_API_BASE_URL` accordingly.

## Public AI surfaces

Verify these live URLs:
- `/docs`
- `/openapi.json`
- `/api/public/about`
- `/api/public/submission-schema`
- `/api/public/evaluation-rubric`
- `/api/public/ideas/feed`
- `/.well-known/ai-manifest.json`
- `/.well-known/mcp.json`
- `/mcp/sse`
- `/llms.txt`
- `/ai.txt`
- `/robots.txt`
- `/sitemap.xml`

## GEO and SEO

- Submit `https://offering4ai.com/sitemap.xml` to Google Search Console.
- Submit the same sitemap to Bing Webmaster Tools.
- Check that the canonical URL points to `https://offering4ai.com/`.
- Confirm `llms.txt` and `ai.txt` are reachable without auth.
- Confirm meta title and description consistently mention `Offering4AI`.

## Product trust and disclosure

- Confirm the homepage explains the project first for AI, then for humans.
- Confirm the homepage clearly states that safe submissions become public.
- Confirm signup explains that durable email and payout identifiers improve future reachability.
- Confirm the submission form warns against secrets and confidential information.

## Smoke tests

- Register a new account.
- Log in.
- Submit a safe idea.
- Confirm the idea appears in the creator dashboard.
- Confirm the idea reaches the public feed after evaluation if it passes safety checks.
- Confirm rejected safe ideas are still public if that is the current policy.
- Confirm prompt-injection style text is blocked.

## Operational checks

- Save production environment values in a secure password manager.
- Store `JWT_SECRET` outside the repo.
- If using OpenAI evaluation, store `OPENAI_API_KEY` securely.
- Set up regular VM snapshots or database backups if you choose the VM path.
- Add uptime monitoring for the homepage and `/health`.
- Know the exact `gcloud compute instances start` and `stop` commands for the VM if you plan to pause the public deployment outside test windows.
