# 04 — Theming

The widget uses a CSS variable system. All colors derive from the primary color automatically. You can override any individual color with a `data-*` attribute.

---

## Dark / Light / Auto Mode

```html
data-theme="light"   <!-- default -->
data-theme="dark"
data-theme="auto"    <!-- follows OS preference -->
```

You can switch themes at runtime:

```js
document.querySelector('magecomp-chat').setAttribute('data-theme', 'dark');
```

---

## Primary Color

Setting one color automatically derives all other colors:

```html
data-primary-color="#5046e4"
data-primary-gradient-end="#7c3aed"
data-primary-gradient-angle="135"
```

| Attribute | Default | Affects |
|-----------|---------|---------|
| `data-primary-color` | `#5046e4` | Buttons, chips, links, input focus ring, launcher |
| `data-primary-gradient-end` | auto-derived | Gradient end on buttons, user bubbles, launcher |
| `data-primary-gradient-angle` | `135` | Gradient direction in degrees |

---

## Individual Color Overrides

### Launcher Button
| Attribute | Description |
|-----------|-------------|
| `data-launcher-color` | Launcher button background (overrides gradient) |
| `data-launcher-icon-color` | Icon color on launcher, default `#ffffff` |

### Chat Panel
| Attribute | Description |
|-----------|-------------|
| `data-bg-color` | Panel background color |
| `data-header-text-color` | Header text color, default `#ffffff` |

### Messages
| Attribute | Description |
|-----------|-------------|
| `data-user-bubble-color` | User message bubble background |
| `data-user-bubble-text-color` | User message text, default `#ffffff` |
| `data-bot-bubble-color` | Bot message bubble background |
| `data-bot-bubble-text-color` | Bot message text color |
| `data-bg-messages-color` | Message area background |
| `data-timestamp-color` | Timestamp text color |

### Input Bar
| Attribute | Description |
|-----------|-------------|
| `data-input-bg-color` | Input field background |
| `data-input-text-color` | Input text color |
| `data-input-placeholder-color` | Placeholder text color |
| `data-send-button-color` | Send button background |
| `data-send-button-icon-color` | Send button icon, default `#ffffff` |

### Chips / Suggestions
| Attribute | Description |
|-----------|-------------|
| `data-chip-border-color` | Suggestion chip border |
| `data-chip-text-color` | Suggestion chip text |
| `data-chip-bg-color` | Suggestion chip background |

### Misc
| Attribute | Description |
|-----------|-------------|
| `data-status-dot-color` | Online status dot, default `#34d399` |
| `data-typing-dot-color` | Typing indicator dots |
| `data-badge-color` | Unread count badge, default `#f43f5e` |
| `data-footer-text-color` | Branding footer text |
| `data-footer-link-color` | Branding footer link |
| `data-shadow-color` | Panel and launcher shadow |

---

## Live Color Update (JavaScript)

Change colors at runtime without reinitialising the widget:

```js
// Change primary color and all derived colors
MagecompChat.setColor('primary', '#e53e3e');

// Change individual targets
MagecompChat.setColor('botBubble',  '#1a1a2e');
MagecompChat.setColor('userBubble', '#e53e3e');
MagecompChat.setColor('background', '#f8f8ff');
```

Available `setColor` targets:
| Target | What changes |
|--------|-------------|
| `primary` | Gradient, chips, links, focus ring, scrollbar |
| `primaryEnd` | Gradient end color |
| `botBubble` | Bot message bubble background |
| `userBubble` | User message bubble background |
| `background` | Panel background |

You can also set any CSS variable directly:

```js
const el = document.querySelector('magecomp-chat');
el.style.setProperty('--mc-send-bg', 'linear-gradient(135deg, #e53e3e, #dd6b20)');
el.style.setProperty('--mc-input-placeholder', 'rgba(80,70,228,0.45)');
```

---

## Brand Presets — Example

### Indigo (default)
```html
data-primary-color="#5046e4"
data-primary-gradient-end="#7c3aed"
```

### Emerald
```html
data-primary-color="#059669"
data-primary-gradient-end="#0284c7"
```

### Red / Alert
```html
data-primary-color="#dc2626"
data-primary-gradient-end="#ea580c"
```

### Sky / Blue
```html
data-primary-color="#0284c7"
data-primary-gradient-end="#0ea5e9"
```

---

## Floatpanel Border Ring Colors

The animated gradient border on the floatpanel input uses four configurable stops:

```html
data-floatpanel-gradient-color1="#4285F4"
data-floatpanel-gradient-color2="#8B5CF6"
data-floatpanel-gradient-color3="#EC4899"
data-floatpanel-gradient-color4="#06B6D4"
```

These cycle in a seamless loop. All four must be set if you override any.

---

## Dark Mode Full Example

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="support"
  data-api-url="https://api.example.com"
  data-theme="dark"
  data-primary-color="#7c3aed"
  data-primary-gradient-end="#5046e4"
  data-bot-bubble-color="#1e1e3a"
  data-user-bubble-color="#5046e4"
  data-bg-color="#0f0f1a"
></script>
```
