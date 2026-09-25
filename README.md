# AI-stock-news

A single-page app that shows an AI-generated summary of the latest news for a stock, aimed at
traders who want to stay informed while managing a portfolio.

> **Status: core build complete.** The full pipeline — Finnhub/Alpha Vantage news adapters with
> fallback, the OpenAI summarizer with grounding validation, and the `GET /api/summary/{ticker}`
> and `GET /` endpoints — is implemented and tested.

---

## 1. Goal and scope

| Requirement from the task | How it is addressed |
| --- | --- |
| Functioning app showing an AI summary of latest news for a stock | FastAPI service with a JSON endpoint and a single HTML page |
| Written in Python with modern libraries | Python 3.12, FastAPI, Pydantic v2, httpx |
| Clear ReadMe with setup and design decisions | This file |
| Clearly defined testing strategy | [Testing strategy](#4-testing-strategy) |
| Ability to plug in your own OpenAI API key | Single `OPENAI_API_KEY` env var, no code change required |

Out of scope by choice: user accounts, persistence, portfolio management, deployment. The
reasoning for each omission is in [Trade-offs](#8-design-decisions-and-trade-offs).

---

## 2. Stack

| Choice | Reason |
| --- | --- |
| Python 3.12 | The role and team are Python-based |
| FastAPI | Async-native, Pydantic-integrated request/response models, generated OpenAPI docs for free |
| Pydantic v2 | Doubles as the domain model and the validation boundary for LLM output |
| httpx | Async HTTP client, first-class test support via `respx` |
| Static HTML page served by FastAPI | Satisfies "full stack app" with one process to run; avoids a second toolchain and build step. Plain HTML and inline JS, so no template engine either |
| pytest + respx | Fast, offline, deterministic test suite |
| uv | Fast, reproducible dependency install for whoever runs this locally |

---

## 3. Architecture

Ports and adapters (hexagonal). The domain knows nothing about Finnhub, Alpha Vantage or OpenAI.

```
                    ┌──────────────────────────────┐
  HTTP ──────────▶  │  FastAPI routers             │
                    │  /  and  /api/summary/{tkr}  │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │  SummaryService (domain)       │
                    │  fetch → dedupe/cap → summarize│
                    └───────┬──────────────┬─────────┘
                            │              │
              ┌─────────────▼───┐    ┌─────▼──────────────┐
              │ NewsProvider    │    │ Summarizer         │   ← ports (Protocols)
              └─────────────────┘    └────────────────────┘
                      │                        │
              CompositeNewsProvider      OpenAISummarizer
                (fallback + source           (degrades to
                 tracking)                 summary_status:
                      │                      degraded)
          ┌───────────┴───────────┐
    FinnhubNewsProvider   AlphaVantageNewsProvider
       (primary)               (secondary, optional)
```

Actual layout:

```
app/
  domain/        models.py           (Article, NewsResult, StockSummary, Takeaway)
                 ports.py            (NewsProvider, Summarizer Protocols)
                 summary_service.py  (SummaryService — the only place business rules live)
  adapters/
    http_client.py                  (shared httpx get/post helper)
    news/        finnhub.py  alphavantage.py  composite.py  mapper.py
    llm/         openai_summarizer.py  schema.py  grounding.py
  api/           routes.py  dependencies.py
  static/        index.html
  config.py      (pydantic-settings, env-driven)
  main.py
tests/
  unit/  adapters/  api/  fixtures/
```

Adapters are selected from config and injected with FastAPI `Depends`.
That decision is what makes "plug in our OpenAI key and run" a config change and makes provider substitution a one-file job.

---

## 4. Testing strategy

The goal is fast, deterministic feedback on all the code we own, plus one explicit check against
what we don't own (the real news APIs and OpenAI). The default suite runs offline, with no API
keys, in well under a second.

**Tools:** pytest (with pytest-asyncio for the async code), respx to mock httpx at the transport
level, FastAPI's `TestClient`, and JSON fixtures shaped like real provider responses.

### 4.1 The test pyramid

```
E2E                      real Finnhub + OpenAI, opt-in

API (integration)        HTTP in, JSON/HTML out, service stubbed

Adapter                  real adapter code, network mocked with respx

Unit                     pure logic, no I/O, fakes behind the ports
```

Counts are as of this writing (58 offline tests plus 1 live). The shape follows from the
architecture: ports and adapters keep every business rule in code that needs no I/O, so most
tests can be pure unit tests. Each tier up adds one real piece — the HTTP client, then the web
framework, then the real services — and tests only what that piece adds. Tiers are defined by
what a test exercises.

### 4.2 Known gaps

- No test executes the page's JavaScript; the API tier only checks that the served HTML contains
  the expected hooks. A browser test (e.g. Playwright) would be the next tier if the frontend grows.
- The fixtures are hand-written, so a provider changing its payload format is only caught by the
  live test.

---

## 5. Data sources

### 5.1 Research

Four candidates were compared on payload shape, ticker tagging, free-tier limits and licensing
(checked September 2026; worth re-verifying before relying on them). **Finnhub** and **Alpha
Vantage** were the only two with real ticker tagging and enough free-tier headroom to be usable —
Finnhub returns a flat article list at ~60 calls/min, Alpha Vantage a nested feed with sentiment
scores at a tight ~25 requests/day. Two others were considered and rejected: **Marketaux**'s free
tier caps responses at ~3 articles, too thin to summarize; generic **NewsAPI**-style keyword
search has no ticker tagging and inherits a precision problem.

### 5.2 Chosen: Finnhub (primary) + Alpha Vantage (secondary)

The reasoning:

1. **Finnhub is the right primary for development.** ~60 calls/min means prompt iteration and a
   live demo are never rate-limited, and the payload maps almost one-to-one onto the domain model.
2. **Alpha Vantage is the right secondary.** Its ~25/day cap rules it out as a primary but is
   perfectly adequate for a fallback that fires only when the primary errors or rate-limits. It
   also ships its own sentiment scores, which could serve as a cheap non-LLM baseline to
   sanity-check the model's tone against. The mapper does not use them yet; they are dropped
   when the feed is mapped onto `Article`.

A `CompositeNewsProvider` wraps both: try primary, fall back to secondary on error or empty
result, and pass back the result of whichever one served it — each provider returns a
`NewsResult` carrying its articles and its own name. The response surfaces `source_provider` so
the behaviour is observable rather than hidden.

---

## 6. LLM design

- **Structured output, not prose.** The model is called with `response_format: json_object` and
  the response is parsed and validated against a Pydantic schema (`SummarizerOutput`): overall
  sentiment (one of `positive`, `negative`, `neutral`, `mixed`), 1–5 bullet takeaways (the prompt
  asks for 3–5 when enough material exists), a risk note, and the article IDs backing each
  bullet. Structured output is renderable, testable, and makes grounding checkable.
- **Grounding.** The prompt supplies numbered articles and instructs the model to use only those,
  citing IDs. Any bullet that cites no article, or cites an unknown ID, fails validation
  (`validate_grounding`). The page shows each bullet's citations as numbered links matching the
  numbered article list, so the reader can check a claim against its source.
- **Determinism and cost.** `temperature=0`, an explicit `max_tokens`, each article's summary
  truncated to 500 characters before being sent, and the article list capped to `MAX_ARTICLES`
  (done by `SummaryService` before the summarizer ever sees them).
- **Model config.** `OPENAI_MODEL` is an env var so the reviewer can point it at whatever they have
  access to.
- **Failure handling.** A timeout (30s), non-2xx response, malformed JSON, a response shape that
  doesn't match the schema, or a grounding failure all return the real articles with a
  `summary_status: degraded` flag, `overall_sentiment: unknown` and no takeaways, and a 200,
  rather than a 500 — logged as a warning so a persistent failure (e.g. a revoked key) stays
  visible. A news app that still shows the headlines
  when the LLM is down is more useful than one that shows an error page.
- **Disclaimer.** The page carries a "not investment advice" line.

---

## 7. Getting started

```bash
git clone <repo> && cd AI-stock-news
uv sync
cp .env.example .env        # add your keys
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000 and enter a ticker, or call the API directly:

```bash
curl http://localhost:8000/api/summary/AAPL
```

`.env.example`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
FINNHUB_API_KEY=...
# ALPHAVANTAGE_API_KEY=...        # optional; uncomment to enable the fallback provider
NEWS_LOOKBACK_DAYS=7
MAX_ARTICLES=10
```

Only `OPENAI_API_KEY` and `FINNHUB_API_KEY` are required. `ALPHAVANTAGE_API_KEY` is commented out
in the template; uncomment it and add a real key to enable the fallback provider. Left commented
out, the composite provider simply runs with one backend.

Tests:

```bash
uv run pytest                     # offline suite
uv run pytest -m live             # requires real keys
```

---

## 8. Design decisions and trade-offs

| Decision | Trade-off accepted |
| --- | --- |
| Ports and adapters for a small app | More files than a single-module script. Bought back in test speed, provider swappability and a clean seam for the fallback logic. |
| Static page over SPA | No rich client interactivity. The JSON endpoint remains the real product if a SPA is ever added. |
| Two news providers | A little extra mapping code. Buys resilience and demonstrates the abstraction holds. |
| Structured LLM output | Slightly more prompt work and a validation path. Buys testability and grounded citations. |
| No persistence | Every request hits the news provider and OpenAI. Acceptable for a demo, not for production — see below. |
| Degrade instead of erroring | Slightly more branching in the summarizer adapter. The user still gets headlines when the model is unavailable. |

## 9. Scaling this (discussion notes)

- **Caching is the first move.** Cache the summary keyed by ticker plus a hash of the article set,
  so the key changes only when the news changes. TTL tied to market hours; shorter during the
  session, longer overnight.
- **Upstream limits.** Both news APIs and OpenAI rate-limit. Needs a token bucket per provider,
  retry with backoff and jitter, and a circuit breaker so a dead upstream fails fast.
- **Perceived latency.** Stream the summary token-by-token to the client; show the headlines
  immediately and let the summary fill in.
- **Observability.** Latency and error rate per adapter, token spend per request, cache hit ratio,
  share of degraded responses. Token spend is a product metric here, not just an ops one.
- **Correctness at scale.** Grounding-failure rate is the metric that matters for an AI feature in
  a financial context, and it needs sampling and review, not just unit tests.
- **Richer frontend.** If interactivity grows (watchlists, live refresh), the JSON endpoint is
  already the contract a SPA would consume.

---

## 10. Checklist

**Build**
- [x] Project skeleton: `uv` init, dependencies, `config.py` with pydantic-settings, `/health`
- [x] Domain layer: `Article`, `Takeaway`, `StockSummary`, the two port Protocols
- [x] `FinnhubNewsProvider` + mapper + JSON fixture
- [x] `AlphaVantageNewsProvider` + mapper + JSON fixture
- [x] `CompositeNewsProvider` with fallback
- [x] `OpenAISummarizer`: prompt, structured output schema, truncation, temperature 0
- [x] Grounding validation: reject bullets citing unknown article IDs
- [x] `SummaryService` wiring fetch → cap → summarize, with the degraded path
- [x] `GET /api/summary/{ticker}` + `GET /` serving a static page, loading and error states

**Tests**
- [x] Domain unit tests
- [x] Mapper tests
- [x] respx adapter tests: auth, date window, non-200, timeout
- [x] Composite provider fallback tests
- [x] LLM contract test against a canned response
- [x] API tests: happy path, unknown ticker, provider outage, summarizer outage

**Docs and hygiene**
- [x] `.env.example` committed, real `.env` gitignored
- [x] Verify a clean clone runs with only the README instructions

**Deliberately not doing** (mention in the walkthrough rather than building)
- Persistence / caching layer, auth, deployment, watchlists, streaming responses, Docker
- Ticker format validation — any string is only trimmed and uppercased before being passed to the
  news providers; an invalid ticker just comes back as a no-news-found result (`risk_note` says
  so) rather than a 400. Not worth the added surface for a demo.

---
