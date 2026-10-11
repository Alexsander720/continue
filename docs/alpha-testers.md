# Public alpha tester checklist

**English** · [Українська](alpha-testers.uk.md) · [Русский](alpha-testers.ru.md)

Thank you for testing Continue? 0.1.0. The goal is to find real Deck, Steam-client, save-reader, media, and layout problems without collecting your saves or identity.

## Before testing

1. Install the alpha by following the [Steam Deck guide](install-deck.md).
2. Note whether you use Deck LCD/OLED or an external display, its resolution, and your Steam interface language.
3. Do not share a save, Steam ID, account name, home-directory path, or an unredacted Steam log.

## What to check

- Open Steam Home and several game pages. Check that Steam's own header, buttons, dialogs, and bottom hints remain usable.
- Test the built-in Deck screen and an external display if available. Pay special attention to 1280×720, 1920×1080, and high-DPI/4K output.
- Switch Steam between English, Ukrainian, and Russian when practical. Look for untranslated interface strings, clipped text, and broken focus order. Game-provided text can legitimately fall back to English.
- For a supported game, compare chapter/place/facts with the latest save you knowingly made. Say exactly what disagrees; do not attach the save.
- Try Steam, artwork, and local-recording background sources when available. YouTube and theme music are optional and must show a consent dialog before downloading yt-dlp.
- Try Light, Balanced, and Maximum. Light must avoid Home video and use a still image on battery; Maximum may use 1080p video everywhere. Also change the separate cache budget.
- Toggle the brightness bar. If the Brightness Bar plugin is present, Continue? should not duplicate it.
- Check the update row. A network failure must not stop the installed version from working.
- Open **Collect a developer report**. Read the complete JSON preview before saving.

## Create the report ZIP

1. Open Continue?'s `…` menu and choose **Collect a developer report**.
2. Review every line. The preview is exactly the JSON that will be put in the archive.
3. Confirm that it contains no save content, Steam ID, account/persona name, or profile path. Expected replacements are `<steamid>` and `<user>`.
4. Select **Save ZIP**. Continue? writes `continue-report-*.zip` to Desktop, or Downloads when Desktop is unavailable.
5. Open an [Alpha tester report issue](../.github/ISSUE_TEMPLATE/alpha_tester_report.md), complete the environment and reproduction fields, and attach the ZIP manually.

The ZIP contains plugin/Decky/SteamOS/Steam versions when available, language and settings, a bounded plugin-log tail, installed-game reader status and parse time, and background-cache state. It does **not** contain saves, media, or a full system log.

## If you find private data

Do not upload the ZIP. Cancel, keep the file local, and file an issue without the attachment that describes only the kind of leaked value (for example, “persona name appears in reader error”). Do not paste the value itself.

## A useful issue includes

- display and resolution;
- Steam interface language;
- plugin version and whether installation was ZIP or URL;
- game name and what screen was open;
- exact actions that reproduce the problem;
- expected and actual result;
- whether it happens again after reopening the page;
- the sanitized report ZIP.

Screenshots are welcome only after checking all visible account, notification, chat, path, and QR information.

[Install guide](install-deck.md) · [README](../README.md) · [Roadmap](ROADMAP.md)
