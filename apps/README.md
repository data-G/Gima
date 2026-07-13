# Gima Apps

Gima is currently packaged as a free local web app/PWA. The same local server works on Mac, iPhone, and Android when the device can reach the Mac running Gima.

## Mac

1. Run `apps/mac/Gima.command`.
2. Open `http://127.0.0.1:8787/`.
3. In Safari or Chrome, use the browser menu to add/install the web app.

## iPhone or iPad

1. Keep Gima running on the Mac.
2. Connect the iPhone/iPad to the same Wi-Fi.
3. Open Safari to the Mac network address and port `8787`.
4. Tap Share, then Add to Home Screen.

## Android

1. Keep Gima running on the Mac.
2. Connect Android to the same Wi-Fi.
3. Open Chrome to the Mac network address and port `8787`.
4. Tap Install app or Add to Home screen.

## OpenRouter Terminal Agent

`apps/gima-openrouter-agent` is a separate TypeScript terminal agent built with `@openrouter/agent`. It supports OpenRouter web search/datetime tools, read-only local repo tools, session logs, model switching, and a custom Gima status tool.

Start it from that folder after exporting `OPENROUTER_API_KEY`.

## Notes

- `127.0.0.1` only works on the Mac itself. Phones need the Mac LAN IP, for example `http://192.168.1.10:8787/`.
- Keep the server local/private unless you intentionally configure a secure remote tunnel.
- Native App Store / Play Store builds can come later using Capacitor, Tauri, Flutter, or React Native wrappers around the same local API.
