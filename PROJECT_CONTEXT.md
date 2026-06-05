# WhatSub? — Project Context

## Overview

WhatSub? is a subscription management platform that helps users track their recurring subscriptions, discover streaming content, and maximize the value they get from their services.

Unlike traditional subscription trackers, WhatSub? combines:

- Subscription management
- Streaming content discovery
- Personalized platform recommendations
- Promotion and bundle optimization

into a single ecosystem.

---

## Current MVP Goals

1. Google Login
2. Gmail Inbox Access
3. Automatic Subscription Detection
4. UserSubscription Generation
5. TMDB-based Content Search
6. Streaming Platform Availability Lookup
7. Personalized Subscription Dashboard

The primary objective is to automate subscription discovery and management with minimal manual input from the user.

---

## Core Features

### 1. Gmail-Based Subscription Detection

During onboarding, users connect their Gmail account. The system scans the inbox to identify subscription-related payment records and automatically builds an initial subscription profile.

**Target services include (but are not limited to):**
- Netflix, Disney+, Tving, Wavve, Watcha
- YouTube Premium, Spotify
- ChatGPT Plus
- Coupang WOW, Baemin Club
- Apple Services, Google One

#### Pipeline

```
Gmail Inbox Access
  → Email Metadata Collection
    → Rule-Based Filtering
      → Deduplication
        → LLM-Based Extraction
          → UserSubscription Generation
```

#### Rule-Based Filtering

Before invoking the LLM, potential subscription emails are identified using:

**Keywords:**
payment, purchase, membership, premium, subscription, renewal, invoice, receipt,
결제, 구매, 구독, 멤버십, 정기결제

**Known Service Names:**
Netflix, Disney, Spotify, Apple, Google, OpenAI, Coupang, Baemin, Tving, Wavve

**Payment Processors:**
NHN KCP, KG Inicis, Toss Payments, KakaoPay, Naver Pay

#### Gmail Search Filters (to be evaluated)
- `category:purchases`
- `newer_than:1m`
- `has:attachment`

#### Deduplication Criteria
- Same sender
- Same platform
- Similar subject line
- Similar payment amount
- Close timestamps

#### LLM Extraction Output Schema

```json
{
  "platform": "Netflix",
  "plan_name": "Standard",
  "payment_amount": 13500,
  "billing_cycle": "monthly",
  "renewal_date": "2026-06-15"
}
```

---

### 2. Streaming Content Discovery

Similar to JustWatch and Letterboxd, but focused on subscription optimization rather than social interaction.

**Features:**
- Movie and TV show search
- Platform availability lookup (subscription / rent / buy / free)
- Personalized content recommendations

---

### 3. User Preferences

Users can like movies and TV shows to build a preference profile.

**Tracked dimensions:**
- Genre preference
- Runtime preference
- Language preference
- Platform preference

---

### 4. Platform Benchmark & Leaderboard (Killer Feature)

#### Value Score Formula

```
Value Score =
  Content Quantity Score  × 0.40
+ Content Quality Score   × 0.30
+ Price Competitiveness   × 0.20
+ Accessibility Score     × 0.10
```

#### Data Sources per Dimension

| Dimension | Weight | Source | Update Strategy |
|---|---|---|---|
| Content Quantity | 40% | TMDB `/discover` API | Weekly batch job |
| Content Quality | 30% | TMDB `/discover` (vote_average ≥ 7.0, vote_count ≥ 1000) | Weekly batch job |
| Price Competitiveness | 20% | Hardcoded table | Manual update |
| Accessibility | 10% | Hardcoded table | Manual update |

#### Content Quantity & Quality — TMDB Approach

```python
# Count titles per platform per genre
GET /discover/movie
  ?with_watch_providers={provider_id}
  &with_genres={genre_id}
  &watch_region=KR
  &vote_average.gte=7.0   # Quality filter
  &vote_count.gte=1000    # Minimum vote threshold
# → total_results used as the metric
```

Korean streaming provider IDs on TMDB:
- Netflix: 8
- Disney+: 337
- Apple TV+: 350
- Watcha: 97
- Wavve: 356
- TVING: 200

#### Price & Accessibility — DB-Managed Tables

Platform pricing and feature data are stored in the database and managed manually.
Data changes infrequently; manual updates are acceptable.

See **Platform Data Model** section for full schema.

---

### 5. Personal Score (Killer Feature)

Based on a user's liked content, the system calculates how well each platform aligns with their genre preferences.

#### Calculation Logic

```python
# Step 1: Derive user genre weights from liked titles
user_weights = {
    "Romance": 0.6,
    "Action":  0.3,
    "Animation": 0.1,
}

# Step 2: Fetch platform genre stats (from DB cache)
platform_genre_stats = {
    "Netflix": {"Romance": 1200, "Action": 800,  "Animation": 300},
    "Disney+": {"Romance": 200,  "Action": 1500, "Animation": 900},
}

# Step 3: Compute weighted personal score per platform
for platform, genres in platform_genre_stats.items():
    score = sum(user_weights.get(g, 0) * count for g, count in genres.items())
```

Example output:
> "You watch mostly Romance — Netflix has 1,200 Romance titles vs Disney+'s 200. Netflix fits you better."

---

## API Strategy

### TMDB (Primary — Free, Unlimited)

- Content metadata: titles, ratings, posters, genres
- Platform availability via Watch Providers
- Benchmark data via `/discover` endpoint with filters
- Already integrated

### Watchmode (Secondary — 2,500 free requests/month)

- Real-time per-title streaming availability for KR region
- Rental/purchase price data for individual titles
- Caching is mandatory to stay within free tier limits

#### Confirmed KR Region Coverage

Watchmode indexes the following services in South Korea:

**Subscription:**
Netflix, Prime Video, Disney+, Apple TV+, Crunchyroll Premium,
Curiosity Stream, GuideDoc, MUBI, TVING, Watcha, Wavve, Zee5

**Purchase & Rental:**
Plex

> TVING, Watcha, and Wavve are confirmed covered — JustWatch/Kinolights crawling is not required for availability checks.

#### Two-Step Deep Link Strategy

Watchmode provides title-level deep links but not episode-level links.
The recommended approach:

```
Step 1 — Availability check (Watchmode)
  → Confirm title is available on platform X
  → Receive title-level web_url from Watchmode

Step 2 — Episode-level link construction
  → Global services: construct URL from known patterns
  → Korean services: construct URL from known patterns or crawl episode listing
```

Known URL patterns:

```python
EPISODE_URL_PATTERNS = {
    # Global
    "Netflix":   "https://www.netflix.com/watch/{content_id}",
    "Disney+":   "https://www.disneyplus.com/video/{content_id}",
    "Apple TV+": "https://tv.apple.com/movie/{slug}",
    "Prime Video": "https://www.primevideo.com/detail/{content_id}",
    # Korean
    "TVING":  "https://www.tving.com/vod/player/{content_id}",
    "Wavve":  "https://www.wavve.com/player/movie/{content_id}",
    "Watcha": "https://watcha.com/contents/{content_id}",
}
```

Episode-level IDs must be resolved via platform-specific crawling or TMDB external_ids mapping where available.

#### Caching Strategy

```python
# Cache per-title streaming availability for 24 hours
def get_streaming_sources(tmdb_id):
    cached = db.get(f"streaming:{tmdb_id}")
    if cached:
        return cached  # No API call

    data = watchmode_api.get_sources(tmdb_id, region="KR")
    db.set(f"streaming:{tmdb_id}", data, ttl=86400)
    return data
```

With 50 DAU, real unique title lookups per day ≈ 30–50.
Estimated monthly API calls: ~900–1,500 (within 2,500 free tier).

### Benchmark Data Refresh (Batch Job — Weekly)

```
For each platform × genre combination:
  → Call TMDB /discover with watch_provider + genre filters
  → Store total_results in platform_genre_stats table
  → Used for Value Score and Personal Score calculations
```

---

## TMDB Integration

TMDB is the primary content metadata provider.

**Current usage:**
- Movie and TV metadata
- Posters, backdrops, ratings
- Watch Providers (streaming availability)

**Known Limitation:**

TMDB Watch Provider data for Korean domestic services is incomplete or outdated.

Affected services: TVING, Wavve, Watcha

**Mitigation:**
Watchmode (KR region) covers TVING, Watcha, and Wavve directly.
Use Watchmode as the source of truth for per-title availability on Korean services.
TMDB Watch Providers are used only for benchmark batch stats (content quantity/quality scoring), where minor gaps are acceptable.

---

## Platform Data Model

Flat dictionaries cannot represent the complexity of real-world streaming plans (e.g., Coupang Play's regular vs. Wow member pricing, add-on passes with tiered pricing). A relational model is required.

### Schema

```python
# Core platform entity
Platform(
    id,
    name,           # "Netflix", "Coupang Play", ...
    logo_url,
    website_url,
    country,        # "KR", "GLOBAL"
)

# One platform has multiple plans (basic / standard / premium / 일반 / 와우 / ...)
SubscriptionPlan(
    id,
    platform_id,          # FK → Platform
    plan_name,            # "일반", "와우", "Basic", "Standard", "Premium"
    price,                # int (KRW), 0 = free
    billing_period,       # "monthly" | "annual" | "weekly"
    max_streams,          # int
    max_quality,          # "SD" | "HD" | "FHD" | "4K"
    has_download,         # bool
    has_ads,              # bool
    requires_membership,  # FK → SubscriptionPlan (nullable)
                          # e.g. Coupang Play 와우 requires Coupang WOW plan
    is_bundle,            # bool
)

# Services included in a bundle plan (1:N)
BundleContent(
    id,
    plan_id,              # FK → SubscriptionPlan
    included_platform_id, # FK → Platform
    # e.g. Baemin Club plan → includes YouTube Premium
)

# Add-on passes offered by a platform
AddOnPass(
    id,
    platform_id,  # FK → Platform
    pass_name,    # "스포츠 패스", "J PLUS 패스", "Paramount+ 패스", ...
)

# Price of each add-on pass varies by base membership tier
AddOnPassPricing(
    id,
    pass_id,         # FK → AddOnPass
    base_plan_id,    # FK → SubscriptionPlan (nullable = non-member price)
    price,           # int (KRW)
    billing_period,  # "monthly" | "annual"
)
```

### Example: Coupang Play

```
Platform: Coupang Play

SubscriptionPlan:
  일반   price=0,    billing=monthly, max_quality=FHD, max_streams=1, has_ads=True
  와우   price=7890, billing=monthly, max_quality=4K,  max_streams=2, has_ads=False
         requires_membership → Coupang WOW (SubscriptionPlan of Coupang platform)

AddOnPass: 스포츠 패스
  AddOnPassPricing: base_plan=일반 → 16,600원
  AddOnPassPricing: base_plan=와우  →  9,900원

AddOnPass: J PLUS 패스
  AddOnPassPricing: base_plan=일반 → 6,900원
  AddOnPassPricing: base_plan=와우  → 5,500원

AddOnPass: Paramount+ 패스
  AddOnPassPricing: base_plan=일반 → 4,900원
  AddOnPassPricing: base_plan=와우  → 3,300원
```

### Example: Baemin Club (Bundle)

```
Platform: Baemin

SubscriptionPlan:
  배민클럽  price=3990, billing=monthly, is_bundle=True

BundleContent:
  plan=배민클럽 → included_platform=YouTube Premium
```

---

## Bundle Subscription Handling

Many subscriptions bundle multiple services under a single payment.

**Examples:**
- Baemin Club + YouTube Premium
- SKT Universe + YouTube Premium
- TVING + Wavve Bundle
- Coupang WOW + Coupang Play

These are modeled via `SubscriptionPlan.is_bundle = True` and `BundleContent` mapping.
This allows bundle, individual, and mixed subscription portfolios to coexist without data conflicts.

---

## Promotion and Discount Sources

*(Reserved — document approved sources here)*

**Target categories:**
- Carrier promotions (SKT, KT, LG U+)
- OTT bundle packages
- Credit/debit card benefits
- Membership discounts (Naver Plus, Kakao, etc.)

---

## Tech Stack

- **Backend:** Django + Django REST Framework
- **Database:** PostgreSQL (psycopg2)
- **Authentication:** Google OAuth via django-allauth
- **External APIs:** TMDB, Watchmode, Gmail API
- **Environment:** python-dotenv, django-environ
- **Documentation:** drf-yasg (Swagger)

---

## Known Constraints

- Watchmode free tier: 2,500 requests/month — DB caching per title (TTL 24h) is required
- TMDB Watch Provider data for TVING/Wavve/Watcha is incomplete — use Watchmode for per-title availability
- Watchmode does not provide episode-level deep links — URL pattern construction or crawling required for episode linking
- Platform pricing and plan data (SubscriptionPlan, AddOnPass) must be maintained manually — no public API exists
- No public API exists for streaming platform subscription pricing