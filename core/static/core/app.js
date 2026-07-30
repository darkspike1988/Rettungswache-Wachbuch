(() => {
  const doc = document;
  const root = doc.documentElement;

  function setOnlineState() {
    root.dataset.connection = navigator.onLine ? "online" : "offline";
    const chip = doc.querySelector("[data-connection-chip]");
    if (!chip) {
      return;
    }
    chip.hidden = navigator.onLine;
    chip.textContent = "Offline – angezeigte Daten können veraltet sein";
  }

  window.addEventListener("online", setOnlineState);
  window.addEventListener("offline", setOnlineState);
  setOnlineState();

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(() => {});
    });
  }

  let deferredPrompt = null;
  const installBanner = doc.querySelector("[data-install-banner]");
  const installButton = doc.querySelector("[data-install-button]");
  const dismissButton = doc.querySelector("[data-install-dismiss]");

  function hideInstallBanner() {
    if (installBanner) {
      installBanner.hidden = true;
    }
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event;
    if (installBanner && !window.matchMedia("(display-mode: standalone)").matches) {
      installBanner.hidden = false;
    }
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    hideInstallBanner();
    try {
      localStorage.setItem("rwsth-installed", "1");
    } catch (_error) {
      /* ignore quota / private mode */
    }
  });

  if (installButton) {
    installButton.addEventListener("click", async () => {
      if (!deferredPrompt) {
        return;
      }
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      hideInstallBanner();
    });
  }

  if (dismissButton) {
    dismissButton.addEventListener("click", () => {
      hideInstallBanner();
      try {
        localStorage.setItem("rwsth-install-dismissed", String(Date.now()));
      } catch (_error) {
        /* ignore */
      }
    });
  }

  try {
    if (localStorage.getItem("rwsth-install-dismissed")) {
      hideInstallBanner();
    }
  } catch (_error) {
    /* ignore */
  }

  doc.querySelectorAll("[data-clear-cache-on-submit]").forEach((form) => {
    form.addEventListener("submit", () => {
      if (navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: "CLEAR_CACHES" });
      }
    });
  });
})();
