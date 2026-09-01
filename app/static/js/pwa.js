/* ResumeLens — PWA registration + install prompt.
   Loaded separately from main.js; does not touch analysis logic. */

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((err) => {
      console.warn("ResumeLens: service worker registration failed", err);
    });
  });
}

let deferredInstallPrompt = null;

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  const btn = document.getElementById("installAppBtn");
  if (btn) btn.classList.remove("hidden");
});

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("installAppBtn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    btn.classList.add("hidden");
  });
});

window.addEventListener("appinstalled", () => {
  const btn = document.getElementById("installAppBtn");
  if (btn) btn.classList.add("hidden");
});
