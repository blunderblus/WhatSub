# Subscription catalog database dump

This folder contains a Django fixture with **official streaming/subscription platforms and plan pricing**.

| File | Contents |
|------|----------|
| `subscriptions_catalog.json` | Categories, platforms, plans, bundles, add-on passes (full catalog) |
| `platform_seed.json` | Legacy seed (subset); prefer `subscriptions_catalog.json` |

## Load on a new device

From the project root (`10-pjt/`):

```bash
# 1. Virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r backend/requirements.txt

# 2. Environment
# Copy .env from your secure store into 10-pjt/.env

# 3. Database schema
cd backend
python manage.py migrate

# 4. Load subscription catalog (platforms + plans)
python manage.py loaddata subscriptions/fixtures/subscriptions_catalog.json
```

Verify:

```bash
python manage.py shell -c "from subscriptions.models import Platform, SubscriptionPlan; print(Platform.objects.count(), 'platforms', SubscriptionPlan.objects.count(), 'plans')"
```

Expected: **16 platforms** and **40+ plans** (counts may grow if the fixture is updated).

## Refresh the dump (after editing plans in admin)

```bash
cd backend
python manage.py dumpdata subscriptions.category subscriptions.platform subscriptions.subscriptionplan subscriptions.bundlecontent subscriptions.addonpass subscriptions.addonpasspricing --indent 2 -o subscriptions/fixtures/subscriptions_catalog.json
```

Commit the updated JSON so other machines stay in sync.

## Notes

- This dump is **catalog data only** (no users, Gmail tokens, or `UserSubscription` rows).
- Gmail onboarding only surfaces platforms present in this catalog.
- Icons live under `backend/subscriptions/media/` and are served via `MEDIA_URL`.
