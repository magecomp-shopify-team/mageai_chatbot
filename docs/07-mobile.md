# 07 — Mobile

The widget automatically detects mobile browsers and adjusts its layout. No extra code is required.

---

## Default Mobile Behaviour

When the viewport width is below `data-mobile-breakpoint` (default `768px`):

- **Popup variant**: the panel expands to fullscreen (100vw × 100vh), the launcher button hides while the panel is open
- **Floatpanel variant**: the column width switches to `data-floatpanel-mobile-width` (default `92vw`)

---

## Controlling Mobile Fullscreen (Popup)

### Enable / Disable

```html
<!-- Enable fullscreen on mobile (default) -->
<script
  src="/widget/magecomp-chat.js"
  data-app-id="support"
  data-api-url="https://api.example.com"
  data-mobile-fullscreen="true"
></script>

<!-- Keep the card layout on mobile -->
<script
  src="/widget/magecomp-chat.js"
  data-app-id="support"
  data-api-url="https://api.example.com"
  data-mobile-fullscreen="false"
></script>
```

### Change the breakpoint

```html
<!-- Trigger mobile mode below 1024px instead of 768px -->
<script
  src="/widget/magecomp-chat.js"
  data-app-id="support"
  data-api-url="https://api.example.com"
  data-mobile-breakpoint="1024"
></script>
```

---

## Floatpanel on Mobile

The floatpanel column stretches wider on mobile. Customise:

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="assistant"
  data-api-url="https://api.example.com"
  data-variant="floatpanel"
  data-floatpanel-desktop-width="50vw"
  data-floatpanel-mobile-width="96vw"
></script>
```

The history panel max-height also adjusts:
- Desktop: `50vh`
- Mobile / tablet: `75vh`

These are built-in and not currently configurable via `data-*` attributes.

---

## Detecting Mobile in JavaScript

```js
MagecompChat.on('resize', ({ mobile, width }) => {
  if (mobile) {
    // User is on a narrow screen
    MagecompChat.setSuggestions(['Call us', 'Email us']);
  } else {
    MagecompChat.setSuggestions(['Browse products', 'Track order', 'Return policy']);
  }
});

// Also available on startup
const { deviceType } = MagecompChat.analytics;
// deviceType: 'mobile' | 'tablet' | 'desktop'
```

---

## Viewport Meta Tag

Ensure your page has the correct viewport meta tag, otherwise the widget layout may break on mobile:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
```

---

## Safe Area (iPhone Notch / Home Bar)

If your app runs as a PWA or in a WebView on iOS, the widget already uses `fixed` positioning which respects safe areas on modern browsers. No extra configuration is needed.

---

## Mobile-Specific Welcome Message

Use the `resize` event to adjust content after load:

```js
MagecompChat.on('load', () => {
  const { deviceType } = MagecompChat.analytics;
  if (deviceType === 'mobile') {
    MagecompChat.addSystemMessage('Tip: Tap any suggestion below to get started quickly.');
  }
});
```
