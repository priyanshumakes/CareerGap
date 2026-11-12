// Cloudflare Turnstile (bot check) configuration for the auth pages.
//
// CAREERGAP_TURNSTILE_SITE_KEY starts EMPTY on purpose. While it is
// empty the login and signup pages behave exactly as before: no
// widget is rendered, no Turnstile script is loaded, and no captcha
// token is sent to Supabase. In that state CAPTCHA protection must
// stay OFF in the Supabase dashboard.
//
// To activate (full steps in docs/bot-protection-setup.md):
//   1. Create a Turnstile site in the Cloudflare dashboard and paste
//      its site key below.
//   2. Deploy the site. Supabase CAPTCHA stays off for now, so the
//      token is ignored and sign-in keeps working for everyone.
//   3. Add the Turnstile SECRET key under Supabase -> Authentication
//      -> Attack Protection and enable CAPTCHA there.
//
// Only the site key (public) ever lives here. The secret key goes
// into Supabase and must never be committed to this repository.
const CAREERGAP_TURNSTILE_SITE_KEY = "";

function careerGapTurnstileEnabled() {
    return (
        typeof CAREERGAP_TURNSTILE_SITE_KEY === "string" &&
        CAREERGAP_TURNSTILE_SITE_KEY.length > 0
    );
}

let careerGapTurnstileLoader = null;

// Loads the Turnstile API script on demand (never at page load when
// the feature is off) and resolves once window.turnstile is ready.
// One shared promise, so several widgets on a page reuse one script.
function careerGapTurnstileLoad() {
    if (!careerGapTurnstileEnabled()) {
        return Promise.resolve(false);
    }

    if (window.turnstile) {
        return Promise.resolve(true);
    }

    if (!careerGapTurnstileLoader) {
        careerGapTurnstileLoader = new Promise(function (resolve, reject) {
            const script = document.createElement("script");
            script.src =
                "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
            script.async = true;
            script.defer = true;
            script.onload = function () {
                resolve(true);
            };
            script.onerror = function () {
                careerGapTurnstileLoader = null;
                reject(new Error("Turnstile failed to load."));
            };
            document.head.appendChild(script);
        });
    }

    return careerGapTurnstileLoader;
}

// Renders a widget into the given container. Resolves to the widget
// id, or to null when Turnstile is not configured (feature off).
function careerGapTurnstileRender(containerId) {
    return careerGapTurnstileLoad().then(function (loaded) {
        if (!loaded) {
            return null;
        }

        return window.turnstile.render("#" + containerId, {
            sitekey: CAREERGAP_TURNSTILE_SITE_KEY,
        });
    });
}

// The current token for a widget, or "" when there is none yet.
function careerGapTurnstileToken(widgetId) {
    if (
        widgetId === null ||
        widgetId === undefined ||
        !window.turnstile
    ) {
        return "";
    }

    return window.turnstile.getResponse(widgetId) || "";
}

// Resets a widget after a failed submit; tokens are single-use.
function careerGapTurnstileReset(widgetId) {
    if (
        widgetId === null ||
        widgetId === undefined ||
        !window.turnstile
    ) {
        return;
    }

    window.turnstile.reset(widgetId);
}
