# Compatible visual installation implementation plan

**Goal:** Install r5 visuals through the public installer while the existing personal card service stays running and its files stay byte exact.

**Architecture:** An explicit `-OwnerThemeOnly` install option persists `mode=owner-theme` in the public install receipt. The public service selects a separate decorator before constructing any backend, adding a bridge or binding the media port. Only public packaged PNG assets decorate existing cards; no card text or save facts change. A separately named JS controller restores its own DOM changes on stop, navigation, replacement of the owner, and lease expiry. This is necessary to meet the requested installation and preservation requirements together. No private task/file changes, game/Steam launches, commits or publication.

**Tech Stack:** Existing stdlib Python CDP transport, public PowerShell installer, JavaScript, Chromium regression fixtures.

1. Preserve the current source and install receipts. Confirm private PID, task, protected hashes and no running game. Independently retain existing native r4/r5 evidence and rerun the intrinsic ratio regression.
2. Add failing tests for the explicit installer option and persisted mode, route/root changes, icon matching, original node restoration, owner identity changes, lease expiry and duplicate injection. Run RED before implementation.
3. Add public_owner_theme.py and bp_owner_theme.js. Load only the current game's assets. Use a control-only ephemeral localhost listener for the existing authenticated stop/health lifecycle; leave port 8793 to its owner. Reuse the CDP transport without registering bindings. Store mode in install.json and retain it during repairs and updates. Include the files in the PC allowlist.
4. Run GREEN, the existing complete checks, private scan and archive readback. Deck renderer stays the existing verified r5. No .bak-r5 enters either package.
5. Back up the actual installation source/task and preserve the previous public profile. Install with the extracted public package using the explicit mode only after tests pass. Measure and capture six native cards, verify unchanged private PID/bridge/task/files.
6. Execute one-command rollback through public uninstall and profile restore, verifying exact preinstall filesystem/task/DOM state. Reinstall the same tested archive and verify six native cards again; leave it installed. Keep backup/evidence outside the restored profile.
7. Write the executor report, perform structural validation, then invoke the requested real codex-pool reviewer. Address findings and verify again before complete status.

Alternative hypotheses already checked: PNG source shape, game_styles entries and flex shrink do not explain r4; object-fit:fill on a text-sized absolute box does. An alternate media port alone does not resolve shared __ghPC/__ghBridge ownership. Installing a static theme through private paths would violate scope; the explicit public mode provides the required delivery and rollback.
