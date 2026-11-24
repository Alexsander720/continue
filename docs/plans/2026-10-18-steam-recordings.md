# Steam recording backgrounds implementation plan

**Goal:** Use local Steam bg recordings on Windows, including Until Dawn, in the native card while preserving the running personal hub and all its files.

**Architecture:** Shared discovery reads Windows SteamPath and all userdata accounts. Steam HEVC fragments are copied and rebased in Continue cache, then decoded and converted to validated AVC. An isolated recording adapter extends the existing owner-theme service; it neither constructs the full backend nor registers a bridge.

**Tech stack:** Python stdlib, existing PCMediaManager/ffmpeg, leased JavaScript decorator, pytest and native Steam CDP.

Alternatives considered: fixing discovery alone cannot affect the deployed owner-theme mode; replacing the personal backend violates the task boundary. Use the existing leased decorator and its loopback control server, with a narrow cached-video endpoint supporting Range.

1. Record hashes for Steam recordings and owner pc_bp/plugin files; preserve source backups as `.bak-ud`.
2. Add failing discovery and HEVC regression tests. Run before changing production code and save actual output.
3. Fix Windows discovery and input-only HEVC normalization, preserving strict AVC output validation. Exercise real sessions and nested clips.
4. Test then implement a single-worker recording adapter, cache containment, Range responses, cancellation while a game runs, and restoration of original DOM/background.
5. Exclude `.bak-ud` from both packagers, build local PC candidate r8, inspect CRC/content and run relevant suites.
6. Prepare rollback from the current installed public app using a complete package; verify no running game before the standard installer.
7. Install through the standard installer with retained owner-theme mode, inspect native frames of Until Dawn and at least three other games, verify advancing muted video and original hub identity.
8. Recheck protected hashes, scheduled task state and service health. Write the required report, stating any limits. No commits, publication, paid calls, Deck access or Steam-recording mutation.
