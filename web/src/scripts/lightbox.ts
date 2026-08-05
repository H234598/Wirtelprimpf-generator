function focusable(root: HTMLElement): HTMLElement[] {
  return [...root.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), [tabindex]:not([tabindex=\"-1\"])")]
    .filter((element) => !element.hasAttribute("hidden"));
}


function mount(dialog: HTMLDialogElement): void {
  const opener = document.querySelector<HTMLAnchorElement>("[data-lightbox-open]");
  const image = dialog.querySelector<HTMLImageElement>("[data-lightbox-image]");
  const close = dialog.querySelector<HTMLElement>("[data-lightbox-close]");
  const surface = dialog.querySelector<HTMLElement>("[data-lightbox-surface]");
  if (!opener || !image || !close || !surface || typeof dialog.showModal !== "function") return;
  let returnFocus: HTMLElement | null = null;

  opener.addEventListener("click", (event) => {
    event.preventDefault();
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : opener;
    dialog.showModal();
    close.focus();
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    dialog.close();
  });

  dialog.addEventListener("close", () => {
    returnFocus?.focus({ preventScroll: true });
    returnFocus = null;
  });

  dialog.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const selector = event.key === "ArrowLeft" ? '[data-lightbox-nav="previous"]' : '[data-lightbox-nav="next"]';
      const link = dialog.querySelector<HTMLAnchorElement>(selector);
      if (link) {
        event.preventDefault();
        link.click();
      }
      return;
    }
    if (event.key !== "Tab") return;
    const elements = focusable(dialog);
    if (!elements.length) return;
    const first = elements[0];
    const last = elements.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  });

  let startX = 0;
  let startY = 0;
  surface.addEventListener("touchstart", (event) => {
    const touch = event.changedTouches[0];
    if (!touch) return;
    startX = touch.clientX;
    startY = touch.clientY;
  }, { passive: true });
  surface.addEventListener("touchend", (event) => {
    const touch = event.changedTouches[0];
    if (!touch) return;
    const deltaX = touch.clientX - startX;
    const deltaY = touch.clientY - startY;
    if (Math.abs(deltaX) < 56 || Math.abs(deltaX) <= Math.abs(deltaY)) return;
    const selector = deltaX < 0 ? '[data-lightbox-nav="next"]' : '[data-lightbox-nav="previous"]';
    dialog.querySelector<HTMLAnchorElement>(selector)?.click();
  }, { passive: true });
}


export function mountLightbox(
  dialog: HTMLDialogElement | null = typeof document === "undefined"
    ? null
    : document.querySelector<HTMLDialogElement>("[data-lightbox]"),
): void {
  if (!dialog || typeof window === "undefined") return;
  mount(dialog);
}


if (typeof document !== "undefined") mountLightbox();
