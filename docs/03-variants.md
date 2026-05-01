# 03 — Variants

The widget ships with two layout variants. Set the variant using `data-variant`.

---

## Popup (default)

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="your_app"
  data-api-url="https://your-backend.com"
  data-variant="popup"
></script>
```

**How it looks:**
- A floating circular launcher button fixed to a corner of the page
- Clicking the button opens a chat panel (card-style, fixed width/height)
- The panel appears above the launcher with a smooth animation
- On mobile: expands to fullscreen (configurable)

**Best for:**
- E-commerce stores
- Support desks
- Any page where chat is secondary to page content

**Key config options:**
| Attribute | Description |
|-----------|-------------|
| `data-position` | `bottom-right` (default), `bottom-left`, `top-right`, `top-left` |
| `data-width` | Panel width in px, default `370` |
| `data-height` | Panel height in px, default `580` |
| `data-offset-x` | Distance from edge, default `24px` |
| `data-offset-y` | Distance from edge, default `24px` |
| `data-launcher-size` | Button diameter, default `52px` |
| `data-launcher-radius` | `50` = circle, `12` = rounded square |

---

## Floatpanel

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="your_app"
  data-api-url="https://your-backend.com"
  data-variant="floatpanel"
></script>
```

**How it looks:**
- No launcher button — the input bar floats at the bottom-center of the viewport
- The input bar has an animated gradient border ring at rest
- Clicking/typing in the input opens the full chat panel upward
- Chat messages stack from bottom to top with a depth-fade mask
- A soft gradient backdrop fades in behind the content
- History panel slides in-place above the input bar (no separate panel)
- Close button (×) appears in the top-right corner when open

**Best for:**
- Dedicated help/FAQ pages
- Landing pages where chat is the primary interaction
- AI assistant or search experiences
- Full-page chatbot applications

**Key config options:**
| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-floatpanel-desktop-width` | `50vw` | Column width on desktop |
| `data-floatpanel-mobile-width` | `92vw` | Column width on mobile |
| `data-floatpanel-placeholder` | `Ask me anything…` | Input placeholder |
| `data-floatpanel-panel-bg` | `#ffffff` | Backdrop/panel background color |
| `data-floatpanel-backdrop-from` | `50` | % of screen height where backdrop becomes fully opaque |
| `data-floatpanel-gradient-color1` | `#4285F4` | Border ring gradient — Blue |
| `data-floatpanel-gradient-color2` | `#8B5CF6` | Border ring gradient — Violet |
| `data-floatpanel-gradient-color3` | `#EC4899` | Border ring gradient — Pink |
| `data-floatpanel-gradient-color4` | `#06B6D4` | Border ring gradient — Cyan |
| `data-floatpanel-icon-color` | primary | Color of history/new-chat icons |

---

## Floatpanel — Full Example

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="assistant"
  data-api-url="https://your-backend.com"

  data-variant="floatpanel"

  data-floatpanel-desktop-width="50vw"
  data-floatpanel-mobile-width="92vw"
  data-floatpanel-placeholder="Ask me anything…"
  data-floatpanel-panel-bg="#ffffff"
  data-floatpanel-backdrop-from="50"

  data-floatpanel-gradient-color1="#4285F4"
  data-floatpanel-gradient-color2="#8B5CF6"
  data-floatpanel-gradient-color3="#EC4899"
  data-floatpanel-gradient-color4="#06B6D4"

  data-primary-color="#5046e4"
  data-theme="light"
  data-bot-name="AI Assistant"
  data-stream="true"
></script>
```

---

## Side-by-side Comparison

| Feature | Popup | Floatpanel |
|---------|-------|------------|
| Launcher button | Yes (floating circle) | No |
| Panel shape | Fixed card | Full-width column |
| Opens from | Launcher click | Input bar click or focus |
| Messages direction | Top to bottom | Bottom to top |
| Backdrop | None | Gradient fade |
| History panel | Slides from right | Appears in-place above input |
| Close button | In panel header | Fixed top-right of viewport |
| Mobile behaviour | Fullscreen card | Same column, wider |
| Best for | Auxiliary chat | Primary chat experience |
