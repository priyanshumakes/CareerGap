# CareerGap bot protection: Turnstile + AI quota

This change adds three layers of bot protection, all free:

1. **Cloudflare Turnstile** (a bot check) on sign-up, sign-in and
   password reset. Bots then cannot mass-create accounts.
2. **A daily AI quota** in the backend: 30 AI calls per account per
   day and 800 across the whole app per day (UTC), so nobody can
   drain the free Groq plan and take AI features down for everyone.
3. **A rate limit on `/ats/keywords`**, the one route that was
   missing one (10/minute per IP, same as the others).

## What works with zero dashboard steps

The daily AI quota and the `/ats/keywords` limit work as soon as the
backend deploys. No keys, no dashboards.

## Activating Turnstile (about 10 minutes, all free)

Do the steps in this order. Order matters: if CAPTCHA is enabled in
Supabase before the site has the widget, real users cannot sign in.

1. **Cloudflare dashboard** -> Turnstile -> **Add site**:
   - Name: `careergap`
   - Hostnames: `careergap.pages.dev` (and `localhost` for local
     testing if wanted)
   - Widget mode: **Managed** (the default)
   - Cloudflare shows a **site key** and a **secret key**.
2. **Paste the site key** into `frontend/turnstile-config.js`
   (`CAREERGAP_TURNSTILE_SITE_KEY`) and deploy the frontend. The
   widget now shows on the sign-in, sign-up and password-reset
   forms. Supabase still ignores the token at this point, so sign-in
   keeps working.
3. **Supabase dashboard** -> Authentication -> **Attack Protection**
   -> enable CAPTCHA, choose **Turnstile**, paste the **secret
   key**, save.
4. Test: sign up with a throwaway address, sign in, and send a
   password reset email. Each should show the check and succeed.

The secret key goes only into Supabase. Never commit it to this
repository.

## Tuning the quota

Both caps are environment variables on the Render backend:

- `AI_DAILY_USER_CAP` (default `30`)
- `AI_DAILY_GLOBAL_CAP` (default `800`)

When a cap is hit the user gets a clear 429 message; everything
resets at midnight UTC.

## Honest limits

- The quota counters live in backend memory. Render's free plan
  restarts the service on deploys and after idle time, so counters
  reset early on those days (a user could get a fresh allowance
  sooner than 24 hours). The quota is abuse protection, not exact
  metering; making it exact would need a database table.
- Turnstile blocks most automated sign-ups, not a determined human
  clicking through the check. The daily quota is the second wall
  behind it.
- Users with aggressive ad-blockers may not see the widget once it
  is on; they will be told to complete the bot check and can disable
  the blocker for the auth pages.
