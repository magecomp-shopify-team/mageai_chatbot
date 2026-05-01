# 06 — Events

Listen to widget events using `MagecompChat.on(event, callback)`.

```js
MagecompChat.on('eventName', (data) => {
  console.log(data);
});
```

The callback receives a data object. All events include `sessionId` where applicable.

---

## Lifecycle Events

### `load`
Fired once when the widget has fully initialised.

```js
MagecompChat.on('load', ({ sessionId, version }) => {
  console.log('Widget ready, session:', sessionId);
  console.log('Version:', version);
});
```

---

### `open`
Fired when the chat panel opens.

```js
MagecompChat.on('open', ({ sessionId }) => {
  // track in analytics
  gtag('event', 'chat_open', { session_id: sessionId });
});
```

---

### `close`
Fired when the chat panel closes.

```js
MagecompChat.on('close', ({ sessionId }) => {
  console.log('Chat closed');
});
```

---

### `resize`
Fired on window resize. Tells you whether the user is on mobile.

```js
MagecompChat.on('resize', ({ mobile, width }) => {
  console.log('Mobile?', mobile, '| Width:', width);
});
```

---

## Message Events

### `send`
Fired when the user sends a message.

```js
MagecompChat.on('send', ({ message, sessionId }) => {
  console.log('User said:', message);
});
```

---

### `receive`
Fired when the bot's response is complete.

```js
MagecompChat.on('receive', ({ message, sessionId, tokens }) => {
  console.log('Bot replied:', message);
  console.log('Tokens used:', tokens);  // { input: number, output: number }
});
```

---

### `typing`
Fired when the bot starts generating a response.

```js
MagecompChat.on('typing', ({ sessionId }) => {
  console.log('Bot is typing...');
});
```

---

### `typing:end`
Fired when the bot finishes responding.

```js
MagecompChat.on('typing:end', ({ sessionId }) => {
  console.log('Bot finished typing');
});
```

---

### `error`
Fired when a network or API error occurs.

```js
MagecompChat.on('error', ({ error, status, sessionId }) => {
  console.error('Chat error:', error, 'HTTP status:', status);
});
```

---

## Session Events

### `session:new`
Fired when a new chat session starts (new chat button or first visit).

```js
MagecompChat.on('session:new', ({ sessionId }) => {
  console.log('New session started:', sessionId);
});
```

---

### `session:load`
Fired when a previous session is loaded from history.

```js
MagecompChat.on('session:load', ({ sessionId }) => {
  console.log('Loaded session:', sessionId);
});
```

---

## User Action Events

### `action`
Fired on various user actions. Check `data.action` for the specific action.

```js
MagecompChat.on('action', ({ action, value, sessionId }) => {
  // action: 'suggestion' | 'attach'
  // value: the suggestion text (for 'suggestion' action)
  console.log('Action:', action, value);
});
```

---

### `clear`
Fired when the user starts a new chat (clears the current conversation).

```js
MagecompChat.on('clear', ({ sessionId }) => {
  console.log('Chat cleared');
});
```

---

### `minimize`
Fired when the panel is minimized.

```js
MagecompChat.on('minimize', ({ sessionId }) => {
  console.log('Chat minimized');
});
```

---

### `restore`
Fired when the panel is restored from minimized state.

```js
MagecompChat.on('restore', ({ sessionId }) => {
  console.log('Chat restored');
});
```

---

### `review`
Fired when the user submits a conversation rating.

```js
MagecompChat.on('review', ({ sessionId, rating, label, comment }) => {
  // rating: 1-5
  // label:  'Very Bad' | 'Bad' | 'Normal' | 'Good' | 'Very Good'
  // comment: optional string
  console.log(`Rating: ${rating} (${label})`);
  if (comment) console.log('Comment:', comment);
});
```

---

## Plugin Events

### `plugin:load`
Fired when a sub-script plugin is loaded via `data-sub-script`.

```js
MagecompChat.on('plugin:load', ({ url, id }) => {
  console.log('Plugin loaded:', id);
});
```

---

## Unsubscribing

`MagecompChat.on()` returns an unsubscribe function:

```js
const off = MagecompChat.on('send', handler);

// Stop listening later
off();
```

---

## Full Analytics Integration Example

```js
MagecompChat.on('load',    ({ sessionId }) => track('chat_init',    { sessionId }));
MagecompChat.on('open',    ({ sessionId }) => track('chat_open',    { sessionId }));
MagecompChat.on('close',   ({ sessionId }) => track('chat_close',   { sessionId }));
MagecompChat.on('send',    ({ message })   => track('chat_message', { message }));
MagecompChat.on('receive', ({ tokens })    => track('chat_tokens',  { tokens }));
MagecompChat.on('review',  ({ rating })    => track('chat_rating',  { rating }));
MagecompChat.on('error',   ({ error })     => track('chat_error',   { error }));

function track(name, data) {
  // Replace with your analytics provider
  gtag('event', name, data);
}
```
