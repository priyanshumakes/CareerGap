document.addEventListener("DOMContentLoaded", function () {
    const signupForm = document.getElementById("signup-form");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput =
        document.getElementById("confirm-password");
    const signupButton = document.querySelector(".login-button");

    // =================================================
    // SHOW / HIDE PASSWORD
    // Matches the existing login page pattern.
    // Toggling only swaps the input type, so the
    // entered value is never read or modified.
    // =================================================

    function setupPasswordToggle(input, toggle, label) {
        if (!input || !toggle) {
            return;
        }

        const openEye =
            toggle.querySelector(".password-eye-open");

        const closedEye =
            toggle.querySelector(".password-eye-closed");

        toggle.addEventListener("click", function () {
            const isPassword = input.type === "password";

            input.type = isPassword ? "text" : "password";

            if (openEye) {
                openEye.classList.toggle("hidden", isPassword);
            }

            if (closedEye) {
                closedEye.classList.toggle("hidden", !isPassword);
            }

            toggle.setAttribute(
                "aria-label",
                isPassword
                    ? `Hide ${label}`
                    : `Show ${label}`
            );

            toggle.setAttribute("aria-pressed", String(isPassword));

            input.focus();
        });
    }

    setupPasswordToggle(
        passwordInput,
        document.getElementById("password-toggle"),
        "password"
    );

    setupPasswordToggle(
        confirmPasswordInput,
        document.getElementById("confirm-password-toggle"),
        "password confirmation"
    );

    // =================================================
    // PASSWORD POLICY
    // Matches reset-password.js: the minimum length is
    // checked before submit so the user gets a clear
    // message; Supabase Auth remains the authoritative
    // server-side validator.
    // =================================================

    const MIN_PASSWORD_LENGTH = 8;

    // Cloudflare Turnstile bot check. Renders only when a site key is
    // configured (turnstile-config.js); otherwise resolves to null
    // and the form behaves exactly as before.
    let turnstileWidgetId = null;

    careerGapTurnstileRender("turnstile-container")
        .then(function (widgetId) {
            turnstileWidgetId = widgetId;
        })
        .catch(function () {
            // The widget failing to load must not break the form for
            // everyone before CAPTCHA is enabled in Supabase; once it
            // is enabled, sign-up without a token is rejected by
            // Supabase itself with a clear message.
            turnstileWidgetId = null;
        });

    signupForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        if (!email || !password || !confirmPassword) {
            alert("Please complete all fields.");
            return;
        }

        if (password.length < MIN_PASSWORD_LENGTH) {
            alert(
                "Password must be at least " +
                    MIN_PASSWORD_LENGTH +
                    " characters."
            );
            return;
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }

        // When Turnstile is configured a solved token is required;
        // Supabase verifies it server-side once CAPTCHA protection is
        // enabled there.
        const signUpOptions = {};

        if (careerGapTurnstileEnabled()) {
            const captchaToken =
                careerGapTurnstileToken(turnstileWidgetId);

            if (!captchaToken) {
                alert("Please complete the bot check.");
                return;
            }

            signUpOptions.captchaToken = captchaToken;
        }

        signupButton.disabled = true;
        signupButton.textContent = "Creating account...";

        const { error } =
            await careerGapSupabase.auth.signUp({
                email: email,
                password: password,
                options: signUpOptions,
            });

        if (error) {
            alert(error.message);
            careerGapTurnstileReset(turnstileWidgetId);
            signupButton.disabled = false;
            signupButton.textContent = "Create Account ";
            signupButton.appendChild(Object.assign(document.createElement("span"), { textContent: "→" }));
            return;
        }

        alert(
            "Account created. Please check your email and confirm your account before signing in."
        );

        window.location.href = "login.html";
    });
});
