# 05 — JavaScript API

After the script loads, `window.MagecompChat` is available with methods to control the widget programmatically.

---

## Availability

The API is ready after the script executes. If you need to call it on page load, wrap in a small timeout or listen for the `load` event:

```js
// Option 1: simple timeout (works in most cases)
setTimeout(() => {
  MagecompChat.open();
}, 500);

// Option 2: event-based (guaranteed)
MagecompChat.on('load', () => {
  console.log('Widget ready');
});
```

---

## Methods

### `MagecompChat.open()`
Opens the chat panel.

```js
MagecompChat.open();
```

---

### `MagecompChat.close()`
Closes the chat panel. Also closes the history panel if it is open.

```js
MagecompChat.close();
```

---

### `MagecompChat.toggle()`
Opens if closed, closes if open.

```js
// Trigger from your own button
document.getElementById('my-chat-btn').addEventListener('click', () => {
  MagecompChat.toggle();
});
```

---

### `MagecompChat.sendMessage(text)`
Sends a message as the user. Opens the panel if it is closed.

```js
MagecompChat.sendMessage('What are your store hours?');
```

**Use case:** pre-fill a question from a help link or FAQ button.

```html
<button onclick="MagecompChat.sendMessage('Track my order')">
  Track my order
</button>
```

---

### `MagecompChat.addSystemMessage(text)`
Adds a grey system/info message to the chat that is not sent to the AI.

```js
MagecompChat.addSystemMessage('You are now chatting with the support bot.');
```

**Use case:** notify the user of a context switch, e.g. after login.

---

### `MagecompChat.setSuggestions(questions)`
Replaces the suggestion chip row with new questions.

```js
MagecompChat.setSuggestions([
  'What is your return policy?',
  'Track my order',
  'Speak to a human',
]);
```

Pass an empty array to clear chips:

```js
MagecompChat.setSuggestions([]);
```

---

### `MagecompChat.setColor(property, value)`
Changes a theme color at runtime without reloading the widget.

```js
MagecompChat.setColor('primary',    '#e53e3e');
MagecompChat.setColor('botBubble',  '#1a1a2e');
MagecompChat.setColor('userBubble', '#e53e3e');
MagecompChat.setColor('background', '#ffffff');
```

---

### `MagecompChat.endSession(exitUrl?)`
Ends the current session and optionally redirects the user.

```js
// End session without redirect
MagecompChat.endSession();

// End session and redirect
MagecompChat.endSession('https://example.com/thank-you');
```

---

### `MagecompChat.on(event, callback)`
Subscribe to a widget event. Returns an unsubscribe function.

```js
const off = MagecompChat.on('send', ({ message, sessionId }) => {
  console.log('User sent:', message);
});

// Later, to stop listening:
off();
```

See [06-events.md](./06-events.md) for all available events.

---

## Properties

### `MagecompChat.session()`
Returns the current session object.

```js
const { sessionId, userId, startedAt } = MagecompChat.session();
console.log('Session ID:', sessionId);
```

---

### `MagecompChat.config`
Read-only frozen config object with all resolved settings.

```js
console.log(MagecompChat.config.appId);
console.log(MagecompChat.config.variant);
console.log(MagecompChat.config.primaryColor);
```

---

### `MagecompChat.analytics`
Device and browser information.

```js
const { deviceType, browser } = MagecompChat.analytics;
// deviceType: 'mobile' | 'tablet' | 'desktop'
// browser:    'chrome' | 'firefox' | 'safari' | 'edge' | 'other'
```

---

### `MagecompChat.version`
Current widget version string.

```js
console.log(MagecompChat.version); // '3.0.0'
```

---

## Full Example — Custom Trigger Button

```html
<!-- Hide the default launcher, use your own button -->
<script
  src="/widget/magecomp-chat.js"
  data-app-id="support"
  data-api-url="https://api.example.com"
  data-launcher-size="0"
></script>

<button id="open-chat" style="position:fixed;bottom:24px;right:24px;">
  💬 Chat with us
</button>

<script>
  document.getElementById('open-chat').addEventListener('click', () => {
    MagecompChat.open();
  });
</script>
```
