# cotizaciones-uy

**The open, machine-readable dataset of currency exchange rates in Uruguay.**

Every Uruguayan bank and *casa de cambio* publishes its rates in its own
format; the Banco Central del Uruguay (BCU) publishes only an official
reference rate. This repository collects them into one versioned JSON dataset,
updated automatically, with the full history preserved in git.

The primary consumer is a **frontend**: a web app fetching JSON over HTTPS.
Every design decision resolves in favor of that consumer.

> **Disclaimer.** This project is unaffiliated with the BCU or any financial
> institution. Data comes from public sources and may be stale or wrong. Verify
> against the institution before transacting.

## Status

| Provider | Slug | Rate type | Status |
|---|---|---|---|
| Banco Central del Uruguay | `bcu` | `official` | Verified against the live service (USD, EUR) |
| Itaú | `itau` | `cash` | Verified against the live document (USD, EUR) |
| BROU | `brou` | `cash` + `ebanking` | Verified against the live endpoint (USD, EUR) |
| BBVA | `bbva` | `cash` | Verified locally (USD, EUR); blocked by Akamai from CI, so it fails the hourly run |

Current milestone: **M6: BBVA.** The dataset is live on GitHub Pages, refreshed
hourly, and now covers four institutions: the BCU official reference, plus
Itaú, BROU, and BBVA retail rates. Each parser is verified against the live
source and tested offline. `bbva` is a known exception: it works from a
residential IP but not from CI (see below).

### Notes on the data

- The `bcu` provider publishes the **official reference** rate (BCU currency
  codes 2222 = USD, 1111 = EUR, international group). This is a reference, not a
  price you can transact at; that is what the retail providers are for. On the
  official reference, `buy` and `sell` are often equal (no spread). The service
  is only queried for the last market-close date (weekends and holidays are
  skipped automatically).
- The `brou` provider targets the Liferay portlet endpoint that serves BROU's
  rates (no headless browser). It publishes the dollar twice: the regular rate
  (`cash`) and the preferential eBROU online-banking rate (`ebanking`), plus the
  euro (`cash`). The source has no quote date, so `quoted_at` is the fetch date.
- The `itau` provider publishes Itaú's retail board (`cash`) rates, which carry
  a real spread. Amounts on the wire come from a document that uses a comma
  decimal separator; we normalize them to `Decimal`.
- The `bbva` provider publishes BBVA's retail board (`cash`) rates from a
  small server-rendered HTML table at a stable URL. No session token or
  client-side rendering is involved. Amounts use a comma decimal separator,
  and the source has no quote date, so `quoted_at` is the fetch date.
  BBVA's endpoint sits behind Akamai Bot Manager, which scores requests from
  cloud/datacenter IP ranges (including GitHub Actions runners) as bots and
  returns `403`, regardless of headers. The provider works when run from a
  residential IP but fails the hourly CI run; that failure is expected and is
  isolated like any other, so it does not affect the rest of the dataset.

## The data

Published under `data/v1/` (served over HTTPS by GitHub Pages):

- **`latest.json`**: the most recent snapshot.
- **`history/YYYY-MM-DD.json`**: one snapshot per run; git holds the full record.
- **`schema.json`**: the JSON Schema every payload is validated against in CI.
- **`institutions.json`**: slug to display name, type, homepage. Don't hardcode this.

### Payload shape

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-09T14:00:03Z",
  "rates": [
    {
      "institution": "bcu",
      "institution_name": "Banco Central del Uruguay",
      "currency": "USD",
      "buy": "39.750",
      "sell": "40.450",
      "rate_type": "official",
      "quoted_at": "2026-07-08",
      "fetched_at": "2026-07-09T14:00:03Z",
      "source_url": "https://cotizaciones.bcu.gub.uy/..."
    }
  ],
  "failures": {
    "brou": "TimeoutError: read timed out"
  }
}
```

### Field semantics

| Field | Meaning |
|---|---|
| `buy` | What the institution **pays you** for one unit of foreign currency. You are selling. |
| `sell` | What the institution **charges you** for one unit. You are buying. |
| `rate_type` | `official` \| `cash` \| `ebanking`. **Never compare across types.** |
| `quoted_at` | The date the rate applies to. |
| `fetched_at` | When we retrieved it. Lets you detect stale data. |
| `currency` | ISO 4217 code. |

**Money is emitted as JSON strings, never numbers.** `"40.450"`, not `40.45`.
Parse it to whatever you like on your end, but the wire format preserves exact
decimal precision. `40.45` has no exact binary representation, so emitting a
float would silently corrupt the value.

## Design

- **A data repo, not a service.** No server, no database. GitHub Actions runs
  the pipeline on a schedule and commits the result; GitHub Pages serves it.
- **git is the historical database.** Every commit is a free, permanent,
  timestamped snapshot.
- **A broken provider never breaks the run.** Each provider is isolated; its
  failure is recorded in `failures` and the rest of the dataset still ships.
- **Never overwrite good data with nothing.** If every provider fails, the run
  exits non-zero and leaves `latest.json` untouched.
- **The schema is versioned in the URL path** (`/v1/`). Breaking a public JSON
  URL is breaking an API.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                       # create the venv, install dev deps
uv run ruff check .           # lint
uv run mypy                   # type-check (strict)
uv run pytest                 # test (fully offline)
uv run python -m cotizaciones_uy   # run the pipeline, write data/v1/
```

The test suite runs fully offline; a test that touches the network is a broken
test. Adding a provider means subclassing `Provider`, implementing `fetch()`
and `parse()`, committing a real captured response to `tests/fixtures/`, and
writing a test against it.

## License

Code is [MIT](LICENSE). The dataset under `data/` is released into the public
domain under [CC0 1.0](data/LICENSE): use it for anything, no attribution
required.
