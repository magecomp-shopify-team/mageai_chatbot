# MageComp Chat Widget — Integration Docs

Frontend integration guide for `magecomp-chat.js` (v3).

---

## Guides

| # | File | What it covers |
|---|------|----------------|
| 1 | [01-quick-start.md](./01-quick-start.md) | Add the widget to any page in 2 minutes |
| 2 | [02-configuration.md](./02-configuration.md) | Every `data-*` attribute explained |
| 3 | [03-variants.md](./03-variants.md) | Popup vs Floatpanel variants |
| 4 | [04-theming.md](./04-theming.md) | Colors, dark mode, live color changes |
| 5 | [05-javascript-api.md](./05-javascript-api.md) | `MagecompChat.*` methods & events |
| 6 | [06-events.md](./06-events.md) | All events you can listen to |
| 7 | [07-mobile.md](./07-mobile.md) | Mobile fullscreen, breakpoints |
| 8 | [08-use-cases.md](./08-use-cases.md) | Real-world integration examples |
| 9 | [09-deployment.md](./09-deployment.md) | Deploy the backend to a Linux server |

---

## Requirements

- A running MageComp Chat backend (`src/api/main.py`)
- A valid `app_id` created in the admin portal
- The widget script file: `widget/magecomp-chat.js`

---

## Minimal Working Example

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="your_app_id"
  data-api-url="https://your-backend.com"
></script>
```

That is all that is required. Everything else is optional.
