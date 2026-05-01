# 01 — Quick Start

Get the chat widget running on any webpage in under 2 minutes.

---

## Step 1 — Serve the widget file

The widget is a single self-contained JavaScript file.

```
widget/magecomp-chat.js
```

Serve it from your web server, CDN, or directly from the backend's static files. It has no dependencies and no build step.

---

## Step 2 — Add the script tag

Paste this one tag before `</body>` in your HTML:

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="your_app_id"
  data-api-url="https://your-backend.com"
></script>
```

| Attribute | Required | Description |
|-----------|----------|-------------|
| `data-app-id` | Yes | The app ID from your admin portal |
| `data-api-url` | Yes | Base URL of your MageComp backend |

That is enough to render a working chat widget with default settings.

---

## Step 3 — Verify it works

Open the page in a browser. You should see:

- A floating chat button in the bottom-right corner (popup variant)
- Clicking it opens the chat panel
- The bot sends the configured welcome message

Open the browser console. You should see:

```
[MageComp Chat] v3.0.0 | app:your_app_id | session:s_xxxxxxxxx
```

---

## Full Minimal Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>My Store</title>
</head>
<body>

  <h1>Welcome to My Store</h1>
  <p>Browse our products below...</p>

  <!-- MageComp Chat Widget -->
  <script
    src="/widget/magecomp-chat.js"
    data-app-id="ecommerce"
    data-api-url="http://localhost:8000"
  ></script>

</body>
</html>
```

---

## What the widget does automatically

- Creates a persistent session ID in `localStorage`
- Loads previous chat history for returning visitors
- Detects mobile browsers and switches to fullscreen mode
- Streams AI responses word-by-word
- Handles all network errors with retries and user-facing messages

---

## Next Steps

- [Configure the widget](./02-configuration.md) — change colors, bot name, position, etc.
- [Choose a variant](./03-variants.md) — popup or floatpanel layout
- [Use the JavaScript API](./05-javascript-api.md) — open/close programmatically, listen to events
