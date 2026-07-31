(() => {
  const doc = document;
  const root = doc.documentElement;

  function csrfToken() {
    const meta = doc.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function setStatus(el, text) {
    if (!el) {
      return;
    }
    el.hidden = !text;
    el.textContent = text || "";
  }

  function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    bytes.forEach((value) => {
      binary += String.fromCharCode(value);
    });
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  function base64urlToBuffer(value) {
    const padded = value.replace(/-/g, "+").replace(/_/g, "/");
    const pad = "=".repeat((4 - (padded.length % 4)) % 4);
    const raw = atob(padded + pad);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) {
      bytes[i] = raw.charCodeAt(i);
    }
    return bytes.buffer;
  }

  function revivePublicKeyOptions(options) {
    const copy = structuredClone(options);
    copy.challenge = base64urlToBuffer(copy.challenge);
    if (copy.user && copy.user.id) {
      copy.user.id = base64urlToBuffer(copy.user.id);
    }
    if (copy.excludeCredentials) {
      copy.excludeCredentials = copy.excludeCredentials.map((item) => ({
        ...item,
        id: base64urlToBuffer(item.id),
      }));
    }
    if (copy.allowCredentials) {
      copy.allowCredentials = copy.allowCredentials.map((item) => ({
        ...item,
        id: base64urlToBuffer(item.id),
      }));
    }
    return copy;
  }

  function serializeCredential(credential) {
    const response = credential.response;
    const raw = {
      id: credential.id,
      rawId: bufferToBase64url(credential.rawId),
      type: credential.type,
      response: {},
      clientExtensionResults: credential.getClientExtensionResults(),
    };
    if (response.attestationObject) {
      raw.response = {
        clientDataJSON: bufferToBase64url(response.clientDataJSON),
        attestationObject: bufferToBase64url(response.attestationObject),
      };
    } else {
      raw.response = {
        clientDataJSON: bufferToBase64url(response.clientDataJSON),
        authenticatorData: bufferToBase64url(response.authenticatorData),
        signature: bufferToBase64url(response.signature),
        userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
      };
    }
    return raw;
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || "Anfrage fehlgeschlagen.");
    }
    return data;
  }

  async function runPasskeyLogin(statusEl) {
    setStatus(statusEl, "Passkey wird geprüft …");
    const optionsResponse = await fetch("/anmelden/passkey/optionen/", { credentials: "same-origin" });
    if (!optionsResponse.ok) {
      throw new Error("Passkeys sind hier nicht verfügbar.");
    }
    const options = revivePublicKeyOptions(await optionsResponse.json());
    const credential = await navigator.credentials.get({ publicKey: options });
    const result = await postJson("/anmelden/passkey/pruefen/", {
      credential: serializeCredential(credential),
    });
    window.location.href = result.redirect || "/";
  }

  async function runPasskeyMfa(statusEl) {
    setStatus(statusEl, "Passkey wird geprüft …");
    const optionsResponse = await fetch("/anmelden/mfa/passkey/optionen/", { credentials: "same-origin" });
    if (!optionsResponse.ok) {
      throw new Error("Passkey-Bestätigung nicht möglich.");
    }
    const options = revivePublicKeyOptions(await optionsResponse.json());
    const credential = await navigator.credentials.get({ publicKey: options });
    const result = await postJson("/anmelden/mfa/passkey/pruefen/", {
      credential: serializeCredential(credential),
    });
    window.location.href = result.redirect || "/";
  }

  async function runPasskeyRegister(statusEl) {
    setStatus(statusEl, "Passkey wird registriert …");
    const optionsResponse = await fetch("/konto/mfa/passkey/optionen/", { credentials: "same-origin" });
    if (!optionsResponse.ok) {
      throw new Error("Passkey-Registrierung nicht möglich.");
    }
    const options = revivePublicKeyOptions(await optionsResponse.json());
    const credential = await navigator.credentials.create({ publicKey: options });
    await postJson("/konto/mfa/passkey/pruefen/", {
      credential: serializeCredential(credential),
      device_name: navigator.platform || "Passkey",
    });
    window.location.reload();
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const output = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) {
      output[i] = raw.charCodeAt(i);
    }
    return output;
  }

  async function runPushSubscribe(statusEl, config) {
    setStatus(statusEl, "Berechtigung wird angefragt …");
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      throw new Error("Benachrichtigungen wurden nicht erlaubt.");
    }
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(config.vapidPublicKey),
    });
    await postJson(config.subscribeUrl, subscription.toJSON());
    window.location.reload();
  }

  async function runPushUnsubscribe(statusEl, config) {
    setStatus(statusEl, "Push wird deaktiviert …");
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      await subscription.unsubscribe();
    }
    await postJson(config.subscribeUrl, { action: "unsubscribe" });
    window.location.reload();
  }

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

  const loginBtn = doc.querySelector("[data-passkey-login]");
  if (loginBtn) {
    loginBtn.addEventListener("click", async () => {
      const status = doc.querySelector("[data-passkey-login-status]");
      try {
        await runPasskeyLogin(status);
      } catch (error) {
        setStatus(status, error.message || "Passkey-Anmeldung fehlgeschlagen.");
      }
    });
  }

  const mfaBtn = doc.querySelector("[data-passkey-mfa]");
  if (mfaBtn) {
    mfaBtn.addEventListener("click", async () => {
      const status = doc.querySelector("[data-passkey-mfa-status]");
      try {
        await runPasskeyMfa(status);
      } catch (error) {
        setStatus(status, error.message || "Passkey-Bestätigung fehlgeschlagen.");
      }
    });
  }

  const registerBtn = doc.querySelector("[data-passkey-register]");
  if (registerBtn) {
    registerBtn.addEventListener("click", async () => {
      const status = doc.querySelector("[data-passkey-register-status]");
      try {
        await runPasskeyRegister(status);
      } catch (error) {
        setStatus(status, error.message || "Passkey-Registrierung fehlgeschlagen.");
      }
    });
  }

  const pushConfigEl = doc.getElementById("push-config");
  if (pushConfigEl) {
    const config = JSON.parse(pushConfigEl.textContent || "{}");
    const status = doc.querySelector("[data-push-status]");
    const subscribeBtn = doc.querySelector("[data-push-subscribe]");
    const unsubscribeBtn = doc.querySelector("[data-push-unsubscribe]");
    if (subscribeBtn) {
      subscribeBtn.addEventListener("click", async () => {
        try {
          await runPushSubscribe(status, config);
        } catch (error) {
          setStatus(status, error.message || "Push konnte nicht aktiviert werden.");
        }
      });
    }
    if (unsubscribeBtn) {
      unsubscribeBtn.addEventListener("click", async () => {
        try {
          await runPushUnsubscribe(status, config);
        } catch (error) {
          setStatus(status, error.message || "Push konnte nicht deaktiviert werden.");
        }
      });
    }
  }
})();
