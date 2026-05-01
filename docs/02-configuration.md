# 02 — Configuration

All configuration is done via `data-*` attributes on the `<script>` tag. No JavaScript object is needed.

---

## Required

| Attribute | Type | Description |
|-----------|------|-------------|
| `data-app-id` | string | App ID from the admin portal |
| `data-api-url` | string | Base URL of the backend (no trailing slash) |

---

## Bot Identity

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-bot-name` | `Magecomp Assistant` | Display name shown in the header |
| `data-bot-avatar` | — | URL to bot avatar image |
| `data-bot-initials` | `MC` | Fallback initials when no avatar |
| `data-bot-status-text` | `Online · Typically replies instantly` | Subtitle under bot name |
| `data-welcome-message` | `Hi there! 👋 How can I help you today?` | First message shown on open |
| `data-welcome-message2` | — | Second welcome message (optional) |
| `data-placeholder` | `Ask me anything...` | Input placeholder text |
| `data-typing-text` | `Assistant is typing` | Text shown while bot is responding |

---

## User Identity

Pass user data so the backend can personalise responses and link sessions to accounts.

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-user-id` | — | Your app's user ID |
| `data-user-name` | — | User's display name |
| `data-user-email` | — | User's email address |
| `data-user-business-name` | — | Company / business name |
| `data-user-avatar` | — | URL to user avatar image |
| `data-user-initials` | — | Fallback initials for user bubble |

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="support"
  data-api-url="https://api.example.com"
  data-user-id="usr_12345"
  data-user-name="Jane Doe"
  data-user-email="jane@example.com"
></script>
```

---

## Layout & Position

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-variant` | `popup` | Layout variant: `popup` or `floatpanel` |
| `data-position` | `bottom-right` | `bottom-right`, `bottom-left`, `top-right`, `top-left` |
| `data-offset-x` | `24` | Horizontal offset from edge in px |
| `data-offset-y` | `24` | Vertical offset from edge in px |
| `data-width` | `370` | Panel width in px (popup variant) |
| `data-height` | `580` | Panel height in px (popup variant) |
| `data-panel-radius` | `20` | Panel corner radius in px |
| `data-launcher-size` | `52` | Launcher button size in px |
| `data-launcher-radius` | `50` | Launcher corner radius (50 = circle) |
| `data-z-index` | `9999` | CSS z-index for the widget |

---

## Behaviour

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-auto-open` | `false` | Open the chat automatically on page load |
| `data-open-delay` | `0` | Delay in ms before auto-open |
| `data-minimized` | `false` | Start in minimized state |
| `data-stream` | `true` | Stream AI response word-by-word |
| `data-persist-history` | `true` | Save and restore conversation history |
| `data-max-history` | `50` | Max messages kept in local history |
| `data-sound-enabled` | `false` | Play sound on new bot message |

---

## UI Toggles

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-show-timestamps` | `true` | Show time below each message |
| `data-timestamp-format` | `time` | `time` (12:34 PM) or `datetime` |
| `data-show-typing-indicator` | `true` | Show animated dots while bot is typing |
| `data-show-avatar` | `true` | Show bot avatar next to messages |
| `data-show-avatar-grouped` | `false` | Show avatar on every message, not just first |
| `data-allow-attachments` | `false` | Show file attachment button |
| `data-show-branding` | `true` | Show "Powered by MageComp" footer |
| `data-show-clear-button` | `true` | Show "New Chat" button |
| `data-show-header-subtitle` | `true` | Show status text under bot name |
| `data-show-notification-badge` | `true` | Show unread count badge on launcher |
| `data-input-max-rows` | `4` | Max rows textarea can expand to |

---

## Mobile

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-mobile-fullscreen` | `true` | Expand to fullscreen on mobile |
| `data-mobile-breakpoint` | `768` | px width below which mobile mode activates |

---

## Theme

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-theme` | `light` | `light`, `dark`, or `auto` |

See [04-theming.md](./04-theming.md) for color attributes.

---

## Complete Example

```html
<script
  src="/widget/magecomp-chat.js"

  data-app-id="ecommerce"
  data-api-url="https://chat.mystore.com"

  data-bot-name="Shop Assistant"
  data-bot-initials="SA"
  data-bot-status-text="Online · Here to help"
  data-welcome-message="Hi! 👋 How can I help you shop today?"
  data-placeholder="Ask about products, orders, returns…"

  data-user-id="usr_98765"
  data-user-name="John Smith"
  data-user-email="john@example.com"

  data-variant="popup"
  data-position="bottom-right"
  data-width="380"
  data-height="600"

  data-theme="light"
  data-primary-color="#5046e4"

  data-auto-open="false"
  data-stream="true"
  data-show-branding="false"
  data-allow-attachments="true"

  data-mobile-fullscreen="true"
></script>
```
