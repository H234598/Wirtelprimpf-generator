function showFallback(image: HTMLImageElement): void {
  image.hidden = true;
  const frame = image.closest<HTMLElement>("[data-media-frame]");
  const fallback = frame?.querySelector<HTMLElement>("[data-media-error]");
  if (fallback) fallback.hidden = false;
}


function mount(): void {
  for (const image of document.querySelectorAll<HTMLImageElement>("[data-media-image]")) {
    image.addEventListener("error", () => showFallback(image), { once: true });
    if (image.complete && image.naturalWidth === 0) showFallback(image);
  }
}


if (typeof document !== "undefined") mount();
