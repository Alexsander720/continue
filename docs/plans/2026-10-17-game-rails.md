# Shared decorative rails and Play button

The public PC and Deck builds share `plugin/dist/index.js` directly, without a bundler. Keep the existing nine CSS themes intact. Add a small local metadata loader that attaches a validated accent and optional PNG data URL to the standalone card. Both renderers use that metadata, so save parsers and the owner runtime stay untouched.

1. Capture existing public and protected file hashes. Back up every existing changed file with `.bak-rails`.
2. Establish missing-feature tests for contrast, asset bounds, and image load/error fallback. Run the existing PC tests independently.
3. Use two authorized ChatGPT web accounts through ImageForge, pinning account and backend. Generate two distinct variants per catalog game and stop the affected account on error/limit. Keep official Steam screenshot references, request receipts and original outputs in local evidence only.
4. Remove a uniform matte from generated images, preserve the silhouette, tint with the game accent, constrain to RGBA 48×512 and 30 KB. Keep selected and reserve variants. Preserve the approved original golden curl, white Bleach and blue Sally Face ornaments by rasterizing their existing SVG.
5. Test the shared metadata loader with missing, malformed, oversized and unsafe files. Test button contrast for accents and white fallback, including normal, hover and controller-focus states. Render a keyed decorative image and suppress legacy CSS only after a successful matching load.
6. Exclude `.bak-rails` from both archives. Add an archive-only candidate suffix while keeping embedded semantic version `0.1.5`.
7. Run PC/Deck regression suites, Linux tests, package E2E and private scans. Create local r2 candidates only. Copy the established PC trial kit into local evidence, pin the new archive hash, self-test its rollback, then run live only after the owner's task and game-running preconditions pass. Capture at least eight game pages and repeat volume/music-off checks. Restore the owner hub and verify protected hashes.
8. Inspect the contact sheet, review alternatives and remaining uncertainty, perform structural handoff validation and request an independent real codex-pool review before claiming completion. Physical Deck and owner aesthetic acceptance remain separate.
