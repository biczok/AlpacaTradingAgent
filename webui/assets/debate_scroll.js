(function () {
    const SCROLL_IDS = ["risk-debate-scroll", "researcher-debate-scroll"];
    const saved = {};
    let restoring = false;

    function isDebatePane(node) {
        return node && SCROLL_IDS.indexOf(node.id) !== -1;
    }

    function capturePane(el) {
        if (!el || restoring) {
            return;
        }
        saved[el.id] = {
            top: el.scrollTop,
            atBottom: el.scrollHeight - el.scrollTop - el.clientHeight < 48,
        };
    }

    function restorePane(el) {
        const state = saved[el.id];
        if (!state) {
            return;
        }
        restoring = true;
        const apply = function () {
            if (state.atBottom) {
                el.scrollTop = el.scrollHeight;
            } else {
                el.scrollTop = state.top;
            }
            restoring = false;
        };
        requestAnimationFrame(apply);
    }

    document.addEventListener(
        "scroll",
        function (event) {
            if (isDebatePane(event.target)) {
                capturePane(event.target);
            }
        },
        true
    );

    const observer = new MutationObserver(function () {
        SCROLL_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                restorePane(el);
            }
        });
    });

    function watchTab(id) {
        const node = document.getElementById(id);
        if (node) {
            observer.observe(node, { childList: true, subtree: true });
        }
    }

    function attach() {
        watchTab("risk-debate-tab-content");
        watchTab("researcher-debate-tab-content");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", attach);
    } else {
        attach();
    }
    setTimeout(attach, 500);
    setTimeout(attach, 2000);
})();
