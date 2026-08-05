# Web Local State

The site stores optional comfort state under `wirtelprimpf.site-state.v1`.
Published stories, media manifests, prompts, chat content, device identifiers,
search history, and free text are never written there.

The versioned payload contains only:

- `theme`: `night` or `paper`;
- `reading_view`: `band` or `chapter`;
- gallery type, page, year, focus asset ID, and scroll position;
- reading position and an optional safe anchor per stable chapter ID;
- a bounded list of asset IDs reserved for the later favorites control.

The parser rejects malformed JSON, unknown schema versions, invalid IDs,
invalid ranges, duplicate favorites, and oversized collections. Serialized
UTF-8 state is limited to 64 KiB. Storage acquisition, reads, writes, and
deletion are all best-effort: a `SecurityError` or quota failure returns the
default state and cannot block the public page.

Chapter aliases are applied only to validated IDs and are bounded to prevent
cycles. The legacy `wirtelprimpf-theme` key is read as a migration fallback;
the settings control writes the versioned state. `Lokale Lesedaten löschen`
removes the versioned state and that legacy theme key.
