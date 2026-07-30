# Findmystack

Finds which companies are using a particular tech stack — with a source URL and
verifier-checked evidence snippet for every match.

## How it works

1. You enter a tool name (e.g. `Algosec`) and optionally the vendor's URL.
2. Every configured provider searches its source for candidate mentions:
   - `vendor_case_studies` — crawls common customer/case-study paths on the
     vendor's site (works out of the box, no API key)
   - `web_search`, `job_postings` — stubs; wire Serper or Tavily
   - `review_sites` — stub; G2/Gartner/TrustRadius via scraping vendor
   - `linkedin` — stub; Proxycurl or Apollo
   - `youtube`, `podcasts` — stubs; YouTube Data API, Listen Notes
3. Each candidate hit is cross-checked by Claude against the fetched source
   text: *"does this page actually say Company X uses Tool Y?"* Only
   confirmed hits with confidence ≥ 0.4 are stored as confirmations.
4. Results are persisted in SQLite so re-searches are incremental. Every row
   is exportable as CSV with source URL and evidence.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY at minimum
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

## Wiring a new provider

Every provider implements the `Provider` protocol in `app/providers/base.py`:

```python
class Provider(Protocol):
    name: str
    source_type: str
    def is_configured(self) -> bool: ...
    async def search(self, req: SearchRequest) -> list[RawHit]: ...
```

Drop your new provider file into `app/providers/`, import it in
`app/providers/__init__.py::all_providers()`, and it flows through the runner
and verifier automatically.

## Current status

- Web app, DB, verifier, runner, CSV export: shipped.
- Provider that works today with no API key: `vendor_case_studies` (needs a
  vendor URL supplied with the search).
- All other providers are stubs that document exactly which API to wire.
- Verifier requires `ANTHROPIC_API_KEY`; without it, hits are collected but
  never promoted to confirmations.
