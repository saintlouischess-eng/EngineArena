# Languages — local development preview, September 22, 2026

Choose **Language** in the sidebar, select a language, then choose **Apply language**.
English, Spanish, French, German, Portuguese, Italian, Dutch and Polish are bundled
and work offline. The choice is saved in the workspace. Applying it reloads the
interface and retains the selected tournament; the worker continues playing.

This is the first translation pass, with a reviewed chess glossary. The longer
translations began as machine-generated drafts and still need native-speaker
review. Catalog coverage is not a claim of linguistic certification. Report a
correction with the language, window name, original wording and suggested wording.

## Scope and protected data

The catalogs cover authored interface labels, settings, help, status messages,
human-readable exports, HTML tournament reports and the desktop's own prompts.
Numbers and dates use the selected locale where the UI formats them. Standard
chess clocks, ISO timestamps and recorded protocol values retain their conventional
notation. Windows supplies the language of the operating-system file dialog's
buttons; Engine Arena translates its custom titles and file-type labels.

Engine names, user-created names, file paths, engine-advertised option names,
raw engine diagnostics, standard PGN notation/tags, UCI commands, database keys,
JSON/CSV field names and statistical inputs are not translated. Piece collection
names remain stable. Developer documentation, the existing beta installer and
third-party driver/runtime installers retain their existing languages. No new
installer or GitHub release was published during this pass.

## Maintaining translations

`locales/en.json` contains the English source; the other seven JSON files contain
translations in their `messages` objects. `locales/sources.json` records source
locations. `locales/glossary.tsv` records reviewed common and chess terminology.
Current catalogs contain 2,618 source messages each, including reusable application
messages; some entries are only used by particular formats or error conditions.

- Preserve every numbered placeholder, including its index. HTML template indices
  refer to the whole template, not just the visible sentence.
- Prefer complete sentences. Never translate internal identifiers or concatenate
  translated labels to construct DOM IDs, database queries or UCI commands.
- JavaScript uses `ArenaI18n.t`, tagged `ArenaI18n.m` and tagged `ArenaI18n.h`.
  HTML translations are escaped and dynamic values are inserted afterward. Static
  page translation runs once before user data is rendered; there is no global
  observer translating arbitrary engine output or user names.
- Python reports use `arena.i18n` with request-local context, including background
  report processes. Translate display labels at render time, not module import
  time or during calculations. Do not translate SQL fragments or metric keys.
- Missing/malformed catalogs or mismatched placeholders fall back to English.
  Template caches are bounded and reset when changing language. Only the chosen
  catalog is included in the page; no online translation service runs in the app.

After adding authored messages:

```powershell
node --expose-internals scripts/collect_locales.cjs
.venv/Scripts/python.exe -X utf8 scripts/collect_backend_locales.py
# Edit the seven translations, preserving placeholders.
.venv/Scripts/python.exe -X utf8 scripts/check_locales.py --sync
```

The collectors do not certify translation completeness for newly added raw
strings. Review new UI/report code for unmarked authored text. Do not run the
one-time migration scripts again; they are retained only with local development
evidence outside the packaged source tree.

Initial drafts were generated locally using Argos translation models and
CTranslate2. No tournament data was used, and neither translation models nor their
development runtime are distributed with Engine Arena. Provenance/download hashes
are retained in `test-output/i18n-provenance/`.

## Validation

- Full backend regression suite: 309 passed (`languages-acceptance.xml`).
- Interface unit checks: 41 passed; placeholder preservation, escaping, fallback,
  locale switching and number formatting included.
- Completed-game reports rendered in all eight languages without changing official
  standings/settings or technical data. Raw names such as `White` and `Draw` stay
  intact.
- A running node-only tournament survived all eight language selections, finishing
  its original attempts; every search remained exactly `go nodes 100`.
- Browser checks exercised language selection, tournament/KO setup, appearance,
  panel size controls, crosstable paging, HTML/text reports and saved selection in
  all eight languages. No browser errors or missing captured translations.
- German and Polish at 1,050 × 760 with 24 px text: no page overflow or clipped
  buttons in the overview, appearance and language dialogs.
- Native startup with a separate Spanish workspace passed. Desktop and sensor
  companion were rebuilt locally; all eight catalogs are included. NuGet's online
  vulnerability feed was unavailable during the build; compilation succeeded
  using already-restored dependencies. No dependencies were changed.

Evidence is in `test-output/languages-*.json` and `languages-*.xml`. All fixtures
are separate from the user's tournament database. Human translation review and
the previously planned long endurance tests remain separate follow-up work.
