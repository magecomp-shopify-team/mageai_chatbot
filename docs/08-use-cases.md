# 08 — Use Cases

Real-world integration examples for common scenarios.

---

## 1. E-commerce Support Chat

Popup widget in the bottom-right corner. Pre-fills the user's account data. Opens automatically after 5 seconds.

```html
<script
  src="/widget/magecomp-chat.js"

  data-app-id="ecommerce"
  data-api-url="https://chat.mystore.com"

  data-bot-name="Shop Assistant"
  data-bot-initials="SA"
  data-bot-status-text="Online · Replies instantly"
  data-welcome-message="Hi {{ user }}! 👋 How can I help you today?"
  data-placeholder="Ask about orders, returns, products…"

  data-variant="popup"
  data-position="bottom-right"
  data-width="380"
  data-height="600"

  data-primary-color="#059669"
  data-primary-gradient-end="#0284c7"
  data-theme="light"

  data-user-id="usr_12345"
  data-user-name="Jane Doe"
  data-user-email="jane@mystore.com"

  data-auto-open="true"
  data-open-delay="5000"
  data-stream="true"
  data-allow-attachments="true"
  data-show-branding="false"
></script>

<script>
  // Pre-load relevant suggestions based on page context
  MagecompChat.on('load', () => {
    const page = window.location.pathname;

    if (page.includes('/orders')) {
      MagecompChat.setSuggestions(['Track my order', 'Cancel an order', 'Return an item']);
    } else if (page.includes('/product')) {
      MagecompChat.setSuggestions(['Is this in stock?', 'Shipping time?', 'Do you offer discounts?']);
    } else {
      MagecompChat.setSuggestions(['Store hours', 'Track my order', 'Return policy', 'Speak to agent']);
    }
  });
</script>
```

---

## 2. Dedicated Help / FAQ Page (Floatpanel)

Full-page AI assistant experience. No launcher — the input bar is always visible.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Help Center</title>
  <style>
    body { margin: 0; background: #f8f8ff; font-family: Inter, sans-serif; }
    .hero { text-align: center; padding: 60px 20px 20px; }
    .hero h1 { font-size: 32px; color: #1a1a2e; margin-bottom: 8px; }
    .hero p  { color: #6b6b8a; font-size: 16px; }
  </style>
</head>
<body>

  <div class="hero">
    <h1>How can we help?</h1>
    <p>Ask anything — our AI has answers 24/7</p>
  </div>

  <script
    src="/widget/magecomp-chat.js"

    data-app-id="helpdesk"
    data-api-url="https://api.example.com"

    data-variant="floatpanel"
    data-floatpanel-desktop-width="52vw"
    data-floatpanel-mobile-width="94vw"
    data-floatpanel-placeholder="Type your question…"
    data-floatpanel-backdrop-from="50"

    data-bot-name="Help Assistant"
    data-welcome-message="Hi! Ask me anything about our products, policies, or account."

    data-primary-color="#5046e4"
    data-theme="light"
    data-stream="true"
    data-show-branding="false"
  ></script>

</body>
</html>
```

---

## 3. SaaS Onboarding Bot

Guides new users through setup steps. Context-aware suggestions change as the user progresses.

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="saas-onboarding"
  data-api-url="https://api.myapp.com"
  data-bot-name="Setup Guide"
  data-welcome-message="Welcome to MyApp! 🎉 I'll help you get set up in a few minutes."
  data-primary-color="#7c3aed"
  data-user-id="usr_abc"
  data-user-name="Alex"
></script>

<script>
  // Step-aware suggestions driven by your app state
  function updateChatContext(step) {
    const suggestions = {
      1: ['Connect my account', 'What integrations are available?'],
      2: ['How do I invite teammates?', 'Set team permissions'],
      3: ['How do I create my first project?', 'Import existing data'],
    };
    MagecompChat.setSuggestions(suggestions[step] || []);
  }

  // Call this from your onboarding wizard
  // e.g. updateChatContext(currentStep);

  MagecompChat.on('load', () => updateChatContext(1));
</script>
```

---

## 4. Dark Mode Website

Widget matches site theme and switches automatically with OS preference.

```html
<script
  src="/widget/magecomp-chat.js"
  data-app-id="darksite"
  data-api-url="https://api.example.com"

  data-theme="auto"

  data-primary-color="#7c3aed"
  data-primary-gradient-end="#5046e4"

  data-bg-color="#0f0f1a"
  data-bot-bubble-color="#1e1e3a"
  data-user-bubble-color="#5046e4"
  data-input-bg-color="#1a1a2e"
  data-header-text-color="#ffffff"
></script>
```

---

## 5. Multi-language Site

Serve the correct app ID per language, pass user locale.

```html
<script>
  // Detect user language from HTML lang attribute or browser
  const lang  = document.documentElement.lang || navigator.language.split('-')[0];
  const appId = { en: 'support-en', fr: 'support-fr', de: 'support-de' }[lang] || 'support-en';

  const script = document.createElement('script');
  script.src              = '/widget/magecomp-chat.js';
  script.dataset.appId    = appId;
  script.dataset.apiUrl   = 'https://api.example.com';
  script.dataset.locale   = lang;
  script.dataset.placeholder = lang === 'fr' ? 'Posez votre question…' : 'Ask me anything…';
  document.body.appendChild(script);
</script>
```

---

## 6. Chat Triggered from a Page Button

Hide the floating launcher. Use your own CTA button to open the chat.

```html
<!-- Your page button -->
<button id="chat-cta" class="cta-button">
  💬 Talk to an expert
</button>

<script
  src="/widget/magecomp-chat.js"
  data-app-id="sales"
  data-api-url="https://api.example.com"
  data-launcher-size="0"
  data-bot-name="Sales Team"
  data-welcome-message="Hi! Ready to find the right plan for you?"
></script>

<script>
  document.getElementById('chat-cta').addEventListener('click', () => {
    MagecompChat.open();
    MagecompChat.sendMessage('I want to learn more about your plans');
  });
</script>
```

---

## 7. Passing Context After Login

Update user identity and session context when the user logs in without reloading the page.

```js
// After successful login:
async function onUserLogin(user) {
  // Add a system message for context
  MagecompChat.addSystemMessage(`You are now signed in as ${user.name}.`);

  // Update suggestions to match logged-in state
  MagecompChat.setSuggestions([
    'My recent orders',
    'My account settings',
    'Upgrade my plan',
  ]);
}
```

---

## 8. Sending Analytics to Your Backend

```js
const sessionRef = {};

MagecompChat.on('load', ({ sessionId }) => {
  sessionRef.id = sessionId;
});

MagecompChat.on('send', ({ message }) => {
  fetch('/api/analytics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event:     'chat_send',
      sessionId: sessionRef.id,
      message,
      page:      window.location.pathname,
      ts:        Date.now(),
    }),
  });
});

MagecompChat.on('review', ({ rating, label, comment }) => {
  fetch('/api/analytics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event:  'chat_review',
      rating,
      label,
      comment,
      ts:     Date.now(),
    }),
  });
});
```
