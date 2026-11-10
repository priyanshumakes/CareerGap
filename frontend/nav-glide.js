/* Desktop nav: the green glider pill follows the pointer across the
   primary tabs and glides back to the active tab when the pointer
   leaves. Same movement as the portfolio nav pill: left + width over
   .38s cubic-bezier(.22,.8,.25,1), mouse and pen only. Phones keep the
   existing scroll-capsule glider in script.js (max-width 700px), and
   hovering never changes the real active tab - only clicking does. */
(() => {
    const desktop = window.matchMedia("(min-width: 701px)");
    const nav = document.querySelector(".primary-nav");
    if (!nav) return;
    const pill = nav.querySelector(".primary-nav-glider");
    const buttons = [...nav.querySelectorAll(".primary-nav-btn")];
    if (!pill || buttons.length < 2) return;

    const mark = (button) => {
        buttons.forEach((b) => b.classList.toggle("pill-under", b === button));
    };
    const to = (button) => {
        pill.style.left = button.offsetLeft + "px";
        pill.style.width = button.offsetWidth + "px";
        pill.style.transform = "none";
        mark(button);
    };
    const home = () =>
        to(nav.querySelector(".primary-nav-btn.active") || buttons[0]);

    buttons.forEach((button) =>
        button.addEventListener("pointerenter", (event) => {
            if (
                desktop.matches &&
                (event.pointerType === "mouse" ||
                    event.pointerType === "pen")
            ) {
                to(button);
            }
        })
    );
    nav.addEventListener("pointerleave", () => {
        if (desktop.matches) home();
    });
    // The view switch in script.js runs first (its listener was
    // registered earlier); re-park the pill on the new active tab.
    nav.addEventListener("click", () => {
        if (desktop.matches) setTimeout(home, 0);
    });

    const apply = () => {
        if (desktop.matches) {
            pill.style.transform = "none";
            home();
        } else {
            // Hand the pill back to the phone capsule script: clear the
            // desktop left, keep its transform/width positioning.
            pill.style.removeProperty("left");
            pill.style.removeProperty("width");
            pill.style.removeProperty("transform");
            buttons.forEach((b) => b.classList.remove("pill-under"));
        }
    };
    desktop.addEventListener("change", apply);
    window.addEventListener("resize", apply);
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => {
            if (desktop.matches) home();
        });
    }

    const style = document.createElement("style");
    style.textContent = `
@media (min-width: 701px) {
    body:not(.account-page) .primary-nav {
        position: relative;
    }
    body:not(.account-page) .primary-nav-glider {
        display: block;
        position: absolute;
        top: 4px;
        left: 0;
        height: calc(100% - 8px);
        border-radius: 999px;
        background: var(--ref-green-primary);
        box-shadow: var(--nav-pill-shadow);
        transition:
            left 0.38s cubic-bezier(0.22, 0.8, 0.25, 1),
            width 0.38s cubic-bezier(0.22, 0.8, 0.25, 1),
            background 0.2s ease;
        pointer-events: none;
        will-change: left, width;
    }
    body:not(.account-page) .primary-nav .primary-nav-btn {
        position: relative;
        z-index: 1;
    }
    /* The pill carries the highlight now, so the flat hover fill and
       the static active fill step back. */
    body:not(.account-page) .primary-nav .primary-nav-btn:hover {
        background: transparent;
    }
    body:not(.account-page) .primary-nav .primary-nav-btn.active {
        background: transparent;
        border-color: transparent;
        box-shadow: none;
        color: var(--ref-green-dark);
    }
    /* White ink only on the tab the pill is currently under. */
    body:not(.account-page) .primary-nav .primary-nav-btn.pill-under {
        color: var(--white);
    }
}
@media (min-width: 701px) and (prefers-reduced-motion: reduce) {
    body:not(.account-page) .primary-nav-glider {
        transition: none;
    }
}`;
    document.head.append(style);
    apply();
})();
