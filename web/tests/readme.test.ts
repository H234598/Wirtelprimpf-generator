import assert from "node:assert/strict";
import test from "node:test";

import {
  parseReadmeSections,
  renderReadmeWithoutCodeBlocks,
  withoutFencedCodeBlocks,
} from "../src/lib/readme.ts";


test("README parsing returns named chapters and ignores headings inside code fences", () => {
  const sections = parseReadmeSections(`# Wurzel

Text.

## Kapitel

Inhalt.

\`\`\`bash
## Kein Kapitel
\`\`\`

### Unterkapitel

Mehr Inhalt.
`);
  assert.deepEqual(sections.map((section) => section.title), ["Wurzel", "Kapitel", "Unterkapitel"]);
  assert.match(sections[1]?.html ?? "", /Inhalt/);
  assert.match(sections[1]?.markdown ?? "", /## Kein Kapitel/);
});


test("relative README references point to the public repository instead of broken site paths", () => {
  const section = parseReadmeSections("# Kapitel\n\n[Dokument](docs/README.md)")[0]!;
  assert.match(section.html, /https:\/\/github\.com\/H234598\/Wirtelprimpf-generator\/blob\/main\/docs\/README\.md/);
});


test("project documentation links use internal mirrors and archive names use repository links", () => {
  const section = parseReadmeSections(
    "# Wirtelprimpf-generator\n\n`Wirtelprimpf-0001` and `Wirtelprimpf-0002`.\n\n[WEB-MEDIA](docs/WEB-MEDIA.md) [WEB-MEDIA-SECURITY](docs/WEB-MEDIA-SECURITY.md)",
  )[0]!;
  assert.match(section.html, /href="\/projekt\/web-media\/"/);
  assert.match(section.html, /href="\/projekt\/web-media-security\/"/);
  assert.match(section.html, /href="https:\/\/github\.com\/H234598\/Wirtelprimpf-0001"/);
  assert.match(section.html, /href="https:\/\/github\.com\/H234598\/Wirtelprimpf-0002"/);
});


test("public README rendering redacts local absolute paths", () => {
  const section = parseReadmeSections("# Kapitel\n\n`--source-root /home/teladi/private/media` and `/root/secret`.")[0]!;
  assert.doesNotMatch(section.html, /\/home\/teladi|\/root\/secret/);
  assert.match(section.html, /lokaler-medienbestand/);
});


test("governance rendering removes fenced commands but keeps explanatory prose", () => {
  const source = "Vorher.\n\n```bash\nmake check\n```\n\nNachher.";
  assert.equal(withoutFencedCodeBlocks(source), "Vorher.\n\n\nNachher.");
  const section = parseReadmeSections(`# Web-Governance\n\n${source}`)[0]!;
  const rendered = renderReadmeWithoutCodeBlocks(section);
  assert.doesNotMatch(rendered.html, /make check/);
  assert.match(rendered.html, /Vorher/);
  assert.match(rendered.html, /Nachher/);
});
