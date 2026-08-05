import {
  GALLERY_DEFAULT_PAGE_SIZE,
  galleryPagePath,
  galleryPageSize,
  galleryUrl,
  parseGalleryPageSize,
  parseGalleryQuery,
  serializeGalleryQuery,
  type GalleryState,
} from "../lib/routes.ts";
import {
  galleryHistoryEntry,
  pushGalleryHistory,
  replaceGalleryHistory,
  restoreGalleryHistory,
  type GalleryHistoryEntry,
} from "./gallery-history.ts";


function readPage(root: HTMLElement): number {
  const value = Number(root.dataset.galleryPage || "1");
  return Number.isSafeInteger(value) && value > 0 ? value : 1;
}


function stateForPage(root: HTMLElement): GalleryState {
  const parsed = parseGalleryQuery(window.location.search);
  const availableYears = new Set((root.dataset.galleryYears || "").split(",").filter(Boolean).map(Number));
  return {
    ...parsed,
    seite: root.dataset.galleryFull === "true" ? parsed.seite : readPage(root),
    jahr: parsed.jahr !== null && availableYears.has(parsed.jahr) ? parsed.jahr : null,
  };
}


function updateUrl(root: HTMLElement, state: GalleryState, replace: boolean): void {
  const fullGallery = root.dataset.galleryFull === "true";
  const url = fullGallery
    ? galleryUrl("/bilder/", state)
    : galleryPagePath(readPage(root));
  const method = replace ? "replaceState" : "pushState";
  window.history[method]({ ...window.history.state }, "", url);
  root.dataset.galleryQuery = serializeGalleryQuery(state);
}


function mount(root: HTMLElement): void {
  const cards = [...root.querySelectorAll<HTMLElement>("[data-gallery-card]")];
  const status = root.querySelector<HTMLElement>("[data-gallery-status]");
  const emptyState = root.querySelector<HTMLElement>("[data-gallery-empty]");
  const focusTarget = root.querySelector<HTMLElement>("[data-gallery-focus]");
  const filters = [...root.querySelectorAll<HTMLAnchorElement>("[data-gallery-filter]")];
  const years = [...root.querySelectorAll<HTMLAnchorElement>("[data-gallery-year]")];
  const pagination = [...root.querySelectorAll<HTMLAnchorElement>("[data-gallery-pagination]")];
  const paginationNav = root.querySelector<HTMLElement>("[data-gallery-pagination-nav]");
  const pageSizeSelect = root.querySelector<HTMLSelectElement>("[data-gallery-page-size]");

  const apply = (state: GalleryState, restore?: GalleryHistoryEntry | null): void => {
    const fullGallery = root.dataset.galleryFull === "true";
    const matching = fullGallery
      ? cards.filter((card) => state.typ === "all" || card.dataset.kind === state.typ)
        .filter((card) => state.jahr === null || card.dataset.year === String(state.jahr))
      : cards;
    const pageSize = galleryPageSize(state);
    const pageCount = fullGallery
      ? pageSize === null ? 1 : Math.max(1, Math.ceil(matching.length / pageSize))
      : Number(root.dataset.galleryPageCount || "1");
    const effectiveState = fullGallery
      ? { ...state, seite: Math.min(Math.max(1, state.seite), pageCount) }
      : state;
    let matchingIndex = 0;
    for (const card of cards) {
      const isMatch = effectiveState.typ === "all" || card.dataset.kind === effectiveState.typ;
      const yearMatches = effectiveState.jahr === null || card.dataset.year === String(effectiveState.jahr);
      const onPage = !fullGallery || pageSize === null || (matchingIndex >= (effectiveState.seite - 1) * pageSize && matchingIndex < effectiveState.seite * pageSize);
      card.hidden = !(isMatch && yearMatches && onPage);
      if (isMatch && yearMatches) matchingIndex += 1;
    }
    for (const filter of filters) {
      const active = filter.dataset.galleryFilter === effectiveState.typ;
      filter.setAttribute("aria-current", active ? "page" : "false");
    }
    for (const year of years) {
      const active = (year.dataset.galleryYear || "") === String(effectiveState.jahr ?? "");
      year.setAttribute("aria-current", active ? "page" : "false");
    }
    if (status) {
      const visible = cards.filter((card) => !card.hidden).length;
      const sizeLabel = effectiveState.proseite === "all" ? "alle" : String(effectiveState.proseite);
      status.textContent = `${visible} ${visible === 1 ? "Bild" : "Bilder"} auf Seite ${effectiveState.seite} von ${pageCount} (${sizeLabel} pro Seite).`;
      if (emptyState) emptyState.hidden = visible > 0;
    }
    if (pageSizeSelect) pageSizeSelect.value = effectiveState.proseite === "all" ? "all" : String(effectiveState.proseite);
    if (paginationNav) paginationNav.hidden = pageCount <= 1;
    for (const link of pagination) {
      const page = Number(link.dataset.galleryPage || "1");
      if (Number.isSafeInteger(page) && page > 0) {
        link.hidden = fullGallery && page > pageCount;
        link.setAttribute("aria-current", page === effectiveState.seite ? "page" : "false");
        link.href = fullGallery
          ? galleryUrl("/bilder/", { ...effectiveState, seite: page })
          : galleryPagePath(page);
      }
    }
    updateUrl(root, effectiveState, true);
    if (restore) {
      restoreGalleryHistory(restore, focusTarget);
    }
  };

  const initial = stateForPage(root);
  if (root.dataset.galleryFull !== "true" && (
    initial.typ !== "all"
    || initial.jahr !== null
    || initial.proseite !== GALLERY_DEFAULT_PAGE_SIZE
  )) {
    window.location.replace(galleryUrl("/bilder/", initial));
    return;
  }
  window.history.scrollRestoration = "manual";
  apply(initial);

  for (const link of root.querySelectorAll<HTMLAnchorElement>("[data-gallery-return-link]")) {
    link.addEventListener("click", () => {
      replaceGalleryHistory({ focusId: link.id || "galerie-ergebnisse", scrollY: Math.round(window.scrollY) });
    });
  }

  for (const filter of filters) {
    filter.addEventListener("click", (event) => {
      if (root.dataset.galleryFull !== "true") return;
      event.preventDefault();
      const state = { ...stateForPage(root), typ: filter.dataset.galleryFilter as GalleryState["typ"] };
      const focusId = filter.id || "galerie-ergebnisse";
      pushGalleryHistory(galleryUrl(window.location.pathname, state), { focusId, scrollY: Math.round(window.scrollY) });
      apply(state);
      focusTarget?.focus({ preventScroll: true });
    });
  }

  for (const year of years) {
    year.addEventListener("click", (event) => {
      if (root.dataset.galleryFull !== "true") return;
      event.preventDefault();
      const value = year.dataset.galleryYear || "";
      const state = { ...stateForPage(root), jahr: value ? Number(value) : null };
      const focusId = year.id || "galerie-ergebnisse";
      pushGalleryHistory(galleryUrl(window.location.pathname, state), { focusId, scrollY: Math.round(window.scrollY) });
      apply(state);
      focusTarget?.focus({ preventScroll: true });
    });
  }

  for (const link of pagination) {
    link.addEventListener("click", (event) => {
      if (root.dataset.galleryFull !== "true") return;
      const page = Number(link.dataset.galleryPage || "1");
      if (!Number.isSafeInteger(page) || page < 1) return;
      event.preventDefault();
      const state = { ...stateForPage(root), seite: page };
      pushGalleryHistory(galleryUrl("/bilder/", state), { focusId: "galerie-ergebnisse", scrollY: Math.round(window.scrollY) });
      apply(state);
      focusTarget?.focus({ preventScroll: true });
    });
  }

  pageSizeSelect?.addEventListener("change", () => {
    const state = { ...stateForPage(root), proseite: parseGalleryPageSize(pageSizeSelect.value), seite: 1 };
    if (root.dataset.galleryFull !== "true") {
      window.location.assign(galleryUrl("/bilder/", state));
      return;
    }
    pushGalleryHistory(galleryUrl("/bilder/", state), { focusId: pageSizeSelect.id || "galerie-ergebnisse", scrollY: Math.round(window.scrollY) });
    apply(state);
    pageSizeSelect.focus({ preventScroll: true });
  });

  window.addEventListener("popstate", (event: PopStateEvent) => {
    apply(stateForPage(root), galleryHistoryEntry(event.state));
  });

  window.addEventListener("pageshow", () => {
    apply(stateForPage(root), galleryHistoryEntry(window.history.state));
  });
}


export function mountGalleryState(root: HTMLElement | null = typeof document === "undefined" ? null : document.querySelector<HTMLElement>("[data-gallery-root]")): void {
  if (!root || typeof window === "undefined") return;
  mount(root);
}


if (typeof document !== "undefined") mountGalleryState();
