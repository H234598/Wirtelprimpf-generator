function setStatus(root: HTMLElement, message: string): void {
  const status = root.querySelector<HTMLElement>("[data-media-action-status]");
  if (status) status.textContent = message;
}

function mount(root: HTMLElement): void {
  const row = root.querySelector<HTMLElement>("[data-media-action-row]");
  const frame = root.closest<HTMLElement>("[data-media-frame]") ?? document.querySelector<HTMLElement>("[data-media-frame]");
  const fullscreen = root.querySelector<HTMLButtonElement>("[data-media-fullscreen]");
  const share = root.querySelector<HTMLButtonElement>("[data-media-share]");
  if (!row) return;

  const canFullscreen = Boolean(document.fullscreenEnabled && frame?.requestFullscreen);
  const canShare = typeof navigator.share === "function";
  if (!canFullscreen && !canShare) return;
  row.hidden = false;

  if (fullscreen && canFullscreen) {
    fullscreen.hidden = false;
    fullscreen.addEventListener("click", async () => {
      if (!frame?.requestFullscreen) return;
      try {
        await frame.requestFullscreen();
      } catch {
        setStatus(root, "Vollbild ist in diesem Browser nicht verfügbar.");
      }
    });
  }

  if (share && canShare) {
    share.hidden = false;
    share.addEventListener("click", async () => {
      try {
        await navigator.share({ title: document.title, url: window.location.href });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setStatus(root, "Teilen ist in diesem Browser nicht verfügbar.");
      }
    });
  }
}

if (typeof document !== "undefined") {
  for (const root of document.querySelectorAll<HTMLElement>("[data-media-actions]")) mount(root);
}

export {};
