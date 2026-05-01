// ─────────────────────────────────────────────────────────
// SECTION 1: CONSTANTS
// ─────────────────────────────────────────────────────────

const MC = {
  VERSION:     '3.0.0',
  TAG:         'magecomp-chat',
  STORAGE_KEY: 'mc_session',
  HISTORY_KEY: 'mc_history',
  PREFS_KEY:   'mc_prefs',
  BRAND:       'Powered by MageComp',
  BRAND_URL:   'https://magecomp.com',
};

// ─────────────────────────────────────────────────────────
// SECTION 2: COLOR ENGINE
// ─────────────────────────────────────────────────────────

function hexToRgb(hex) {
  let h = hex.replace('#', '');
  if (h.length === 3)  h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
  if (h.length === 4)  h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2]+h[3]+h[3];
  const int = parseInt(h.slice(0,6), 16);
  return {
    r: (int >> 16) & 255,
    g: (int >>  8) & 255,
    b:  int        & 255,
    a: h.length === 8 ? parseInt(h.slice(6,8), 16) / 255 : 1,
  };
}

function rgbToHex({ r, g, b }) {
  return '#' + [r, g, b].map(x => Math.round(Math.max(0, Math.min(255, x))).toString(16).padStart(2,'0')).join('');
}

function hexToHsl(hex) {
  const { r, g, b } = hexToRgb(hex);
  const rn = r/255, gn = g/255, bn = b/255;
  const max = Math.max(rn,gn,bn), min = Math.min(rn,gn,bn);
  let h = 0, s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case rn: h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6; break;
      case gn: h = ((bn - rn) / d + 2) / 6; break;
      default: h = ((rn - gn) / d + 4) / 6;
    }
  }
  return { h: h * 360, s: s * 100, l: l * 100 };
}

function hslToHex({ h, s, l }) {
  const sn = s / 100, ln = l / 100;
  const hue2rgb = (p, q, t) => {
    if (t < 0) t += 1; if (t > 1) t -= 1;
    if (t < 1/6) return p + (q-p)*6*t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q-p)*(2/3-t)*6;
    return p;
  };
  let r, g, b;
  if (sn === 0) {
    r = g = b = ln;
  } else {
    const q = ln < 0.5 ? ln*(1+sn) : ln+sn-ln*sn;
    const p = 2*ln - q;
    const hn = ((h % 360) + 360) % 360 / 360;
    r = hue2rgb(p, q, hn + 1/3);
    g = hue2rgb(p, q, hn);
    b = hue2rgb(p, q, hn - 1/3);
  }
  return rgbToHex({ r: r*255, g: g*255, b: b*255 });
}

function getLuminance(hex) {
  const { r, g, b } = hexToRgb(hex);
  const lin = c => { const s = c/255; return s <= 0.03928 ? s/12.92 : Math.pow((s+0.055)/1.055, 2.4); };
  return 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b);
}

function getContrast(hex1, hex2) {
  const l1 = getLuminance(hex1), l2 = getLuminance(hex2);
  return (Math.max(l1,l2) + 0.05) / (Math.min(l1,l2) + 0.05);
}

function getContrastText(bgHex) {
  return getContrast(bgHex, '#ffffff') >= 4.5 ? '#ffffff' : '#000000';
}

function adjustLightness(hex, delta) {
  const hsl = hexToHsl(hex);
  return hslToHex({ ...hsl, l: Math.min(100, Math.max(0, hsl.l + delta)) });
}

function adjustSaturation(hex, delta) {
  const hsl = hexToHsl(hex);
  return hslToHex({ ...hsl, s: Math.min(100, Math.max(0, hsl.s + delta)) });
}

function mixColors(hex1, hex2, weight = 0.5) {
  const c1 = hexToRgb(hex1), c2 = hexToRgb(hex2);
  return rgbToHex({
    r: c1.r + (c2.r - c1.r) * weight,
    g: c1.g + (c2.g - c1.g) * weight,
    b: c1.b + (c2.b - c1.b) * weight,
  });
}

function transparentize(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r},${g},${b},${alpha})`;
}

function isLight(hex) { return getLuminance(hex) > 0.4; }

function generateColorScale(primaryHex) {
  const stops = { 50:92, 100:85, 200:72, 300:55, 400:38, 500:0, 600:-12, 700:-22, 800:-32, 900:-42 };
  const out = {};
  for (const [key, delta] of Object.entries(stops)) {
    if (delta === 0) { out[key] = primaryHex; }
    else if (delta > 0) { out[key] = mixColors(primaryHex, '#ffffff', delta/100); }
    else { out[key] = adjustLightness(primaryHex, delta); }
  }
  return out;
}

class ColorEngine {
  constructor(rawCfg) {
    this._raw = rawCfg;
    this._resolved = {};
  }

  resolve() {
    const raw   = this._raw;
    const p     = raw.primaryColor || '#5046e4';
    const isDark = raw.theme === 'dark';
    const pe    = raw.primaryGradientEnd || this._deriveGradientEnd(p);
    const angle = raw.primaryGradientAngle || 135;
    const scale = generateColorScale(p);

    this._resolved = {
      '--mc-grad-start':        p,
      '--mc-grad-end':          pe,
      '--mc-grad-angle':        `${angle}deg`,
      '--mc-gradient':          `linear-gradient(${angle}deg, ${p}, ${pe})`,

      '--mc-p50':   scale[50],
      '--mc-p100':  scale[100],
      '--mc-p200':  scale[200],
      '--mc-p300':  scale[300],
      '--mc-p400':  scale[400],
      '--mc-p500':  scale[500],
      '--mc-p600':  scale[600],
      '--mc-p700':  scale[700],
      '--mc-p800':  scale[800],
      '--mc-p900':  scale[900],

      '--mc-bg':
        raw.bgColor || (isDark ? '#0f0f1a' : '#ffffff'),

      '--mc-bg-messages':
        raw.bgMessagesColor || (isDark ? '#13131f' : adjustLightness(p, 47)),

      '--mc-surface':   isDark ? '#1a1a2e' : '#ffffff',
      '--mc-surface-2': isDark ? '#16162a' : adjustLightness(p, 46),

      '--mc-header-text': raw.headerTextColor || '#ffffff',

      '--mc-bot-bubble-bg':
        raw.botBubbleColor || (isDark ? adjustLightness(p, 10) : '#ffffff'),

      '--mc-bot-bubble-text':
        raw.botBubbleTextColor || (isDark ? '#e8e8f8' : '#1a1a2e'),

      '--mc-bot-bubble-border':
        isDark ? transparentize(p, 0.2) : 'rgba(0,0,0,0.06)',

      '--mc-user-bubble-bg':
        raw.userBubbleColor || `linear-gradient(${angle}deg, ${p}, ${pe})`,

      '--mc-user-bubble-text':
        raw.userBubbleTextColor || getContrastText(p),

      '--mc-chip-border':
        raw.chipBorderColor || transparentize(p, 0.25),

      '--mc-chip-text':
        raw.chipTextColor || p,

      '--mc-chip-bg':
        raw.chipBgColor || transparentize(p, 0.06),

      '--mc-chip-hover-bg':   p,
      '--mc-chip-hover-text': getContrastText(p),

      '--mc-input-bg':
        raw.inputBgColor || (isDark ? adjustLightness(p, 8) : adjustLightness(p, 46)),

      '--mc-input-text':
        raw.inputTextColor || (isDark ? '#e8e8f8' : '#1a1a2e'),

      '--mc-input-placeholder':
        raw.inputPlaceholderColor || transparentize(p, isDark ? 0.55 : 0.45),

      '--mc-input-border-focus': p,

      '--mc-send-bg':
        raw.sendButtonColor || `linear-gradient(${angle}deg, ${p}, ${pe})`,

      '--mc-send-icon':
        raw.sendButtonIconColor || getContrastText(p),

      '--mc-typing-dot':
        raw.typingDotColor || (isDark ? adjustLightness(p, 30) : adjustLightness(p, 25)),

      '--mc-timestamp':
        raw.timestampColor || (isDark ? adjustLightness(p, 25) : adjustLightness(p, 28)),

      '--mc-status-dot': raw.statusDotColor || '#34d399',

      '--mc-launcher-bg':
        raw.launcherColor || `linear-gradient(${angle}deg, ${p}, ${pe})`,

      '--mc-launcher-icon': raw.launcherIconColor || '#ffffff',

      '--mc-badge-bg': raw.badgeColor || '#f43f5e',

      '--mc-shadow-color':
        raw.shadowColor || transparentize(p, 0.25),

      '--mc-shadow-panel':
        `0 24px 56px ${raw.shadowColor || transparentize(p, 0.22)}, 0 8px 16px ${transparentize(p, 0.12)}`,

      '--mc-footer-text':
        raw.footerTextColor || (isDark ? adjustLightness(p, 25) : adjustLightness(p, 28)),

      '--mc-footer-link': raw.footerLinkColor || p,

      '--mc-border':       isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)',
      '--mc-border-strong':isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.10)',

      '--mc-scrollbar-thumb': adjustLightness(p, 35),
      '--mc-scrollbar-track': 'transparent',

      '--mc-g-desktop-width': raw.floatpanelDesktopWidth || '50vw',
      '--mc-g-mobile-width':  raw.floatpanelMobileWidth  || '92vw',
      '--mc-g-input-border':
        raw.floatpanelInputBorderColor || (isDark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.12)'),
      '--mc-g-gc1': raw.floatpanelGradientColor1 || '#4285F4',
      '--mc-g-gc2': raw.floatpanelGradientColor2 || '#8B5CF6',
      '--mc-g-gc3': raw.floatpanelGradientColor3 || '#EC4899',
      '--mc-g-gc4': raw.floatpanelGradientColor4 || '#06B6D4',
      '--mc-g-panel-bg':
        raw.floatpanelPanelBg || (isDark ? '#0f0f1a' : '#ffffff'),
      '--mc-g-backdrop': (() => {
        // Layout: top `fadePct`% = smoothstep fade (zero velocity at both ends → no hard seam)
        //         bottom (100-fadePct)% = fully solid panel color
        const bg      = raw.floatpanelPanelBg || (isDark ? '#0f0f1a' : '#ffffff');
        const fadePct = Math.max(10, Math.min(80, raw.floatpanelBackdropFrom || 50));
        const { r, g, b } = hexToRgb(bg);
        const steps   = 20;
        const stops   = [`rgba(${r},${g},${b},0) 0%`];
        // smoothstep: 3t²-2t³  — eases in AND out, no abrupt ramp at either boundary
        for (let i = 1; i <= steps; i++) {
          const t     = i / steps;
          const s     = t * t * (3 - 2 * t);           // smoothstep
          const alpha = +s.toFixed(3);
          const pct   = Math.round(t * fadePct);
          stops.push(`rgba(${r},${g},${b},${alpha}) ${pct}%`);
        }
        stops.push(`${bg} 100%`);
        return `linear-gradient(to bottom, ${stops.join(', ')})`;
      })(),
      '--mc-g-icon':
        raw.floatpanelIconColor || (isDark ? adjustLightness(p, 30) : p),

      '--mc-r-panel':    `${raw.panelRadius    || 20}px`,
      '--mc-r-bubble':   '16px',
      '--mc-r-chip':     '999px',
      '--mc-r-input':    '12px',
      '--mc-r-send':     '10px',
      '--mc-r-launcher': `${raw.launcherRadius != null ? raw.launcherRadius : 50}%`,

      '--mc-width':          `${raw.width        || 370}px`,
      '--mc-height':         `${raw.height       || 580}px`,
      '--mc-launcher-size':  `${raw.launcherSize  || 52}px`,
      '--mc-z':              `${raw.zIndex       || 9999}`,
      '--mc-offset-x':       `${raw.offsetX      || 24}px`,
      '--mc-offset-y':       `${raw.offsetY      || 24}px`,
    };

    return this._resolved;
  }

  applyTo(el) {
    const vars = this.resolve();
    Object.entries(vars).forEach(([k, v]) => el.style.setProperty(k, v));
  }

  setColor(property, value, el) {
    const map = {
      primary:    ['--mc-grad-start','--mc-p500','--mc-chip-text','--mc-footer-link','--mc-input-border-focus'],
      primaryEnd: ['--mc-grad-end'],
      botBubble:  ['--mc-bot-bubble-bg'],
      userBubble: ['--mc-user-bubble-bg'],
      background: ['--mc-bg'],
    };
    const targets = map[property] || [property];
    targets.forEach(t => el.style.setProperty(t, value));
  }

  _deriveGradientEnd(primaryHex) {
    const { h, s, l } = hexToHsl(primaryHex);
    return hslToHex({ h: (h + 25) % 360, s: Math.min(s + 5, 100), l: Math.max(l - 8, 20) });
  }
}

// ─────────────────────────────────────────────────────────
// SECTION 3: CONFIG PARSER
// ─────────────────────────────────────────────────────────

function parseConfig() {
  const script = document.currentScript ||
    [...document.querySelectorAll('script[data-app-id]')].pop();
  if (!script) throw new Error('[MC] Missing script tag with data-app-id');

  const d    = script.dataset;
  const str  = (v, def='')    => (v !== undefined && v !== '') ? v : def;
  const num  = (v, def=0)     => (v !== undefined && v !== '') ? parseInt(v, 10) : def;
  const bool = (v, def=false) => v === undefined ? def : (v === 'true' || v === '1');
  const json = (v, def=[])    => { try { return JSON.parse(v || JSON.stringify(def)); } catch { return def; } };
  const hex  = (v, def='')    => (v && /^#([0-9a-f]{3,8})$/i.test(v.trim())) ? v.trim() : def;

  return Object.freeze({
    appId:   str(d.appId),
    apiUrl:  str(d.apiUrl).replace(/\/$/, ''),

    primaryColor:          hex(d.primaryColor,          '#5046e4'),
    primaryGradientEnd:    hex(d.primaryGradientEnd,    ''),
    primaryGradientAngle:  num(d.primaryGradientAngle,  135),
    userBubbleColor:       hex(d.userBubbleColor,       ''),
    userBubbleTextColor:   hex(d.userBubbleTextColor,   '#ffffff'),
    botBubbleColor:        hex(d.botBubbleColor,        ''),
    botBubbleTextColor:    hex(d.botBubbleTextColor,    ''),
    bgColor:               hex(d.bgColor,               ''),
    bgMessagesColor:       hex(d.bgMessagesColor,       ''),
    headerTextColor:       hex(d.headerTextColor,       '#ffffff'),
    timestampColor:        hex(d.timestampColor,        ''),
    chipBorderColor:       hex(d.chipBorderColor,       ''),
    chipTextColor:         hex(d.chipTextColor,         ''),
    chipBgColor:           hex(d.chipBgColor,           ''),
    inputBgColor:          hex(d.inputBgColor,          ''),
    inputTextColor:        hex(d.inputTextColor,        ''),
    inputPlaceholderColor: hex(d.inputPlaceholderColor, ''),
    footerTextColor:       hex(d.footerTextColor,       ''),
    footerLinkColor:       hex(d.footerLinkColor,       ''),
    sendButtonColor:       hex(d.sendButtonColor,       ''),
    sendButtonIconColor:   hex(d.sendButtonIconColor,   '#ffffff'),
    statusDotColor:        hex(d.statusDotColor,        '#34d399'),
    typingDotColor:        hex(d.typingDotColor,        ''),
    launcherColor:         hex(d.launcherColor,         ''),
    launcherIconColor:     hex(d.launcherIconColor,     '#ffffff'),
    badgeColor:            hex(d.badgeColor,            '#f43f5e'),
    shadowColor:           str(d.shadowColor,           ''),

    variant:                  str(d.variant,                  'popup'),

    // Floatpanel variant — configurable props
    floatpanelDesktopWidth:       str(d.floatpanelDesktopWidth,       '50vw'),
    floatpanelMobileWidth:        str(d.floatpanelMobileWidth,        '92vw'),
    floatpanelInputBg:            hex(d.floatpanelInputBg,            ''),
    floatpanelInputTextColor:     hex(d.floatpanelInputTextColor,     ''),
    floatpanelInputBorderColor:   hex(d.floatpanelInputBorderColor,   ''),
    floatpanelGradientColor1:     hex(d.floatpanelGradientColor1,     ''),
    floatpanelGradientColor2:     hex(d.floatpanelGradientColor2,     ''),
    floatpanelGradientColor3:     hex(d.floatpanelGradientColor3,     ''),
    floatpanelGradientColor4:     hex(d.floatpanelGradientColor4,     ''),
    floatpanelPanelBg:            hex(d.floatpanelPanelBg,            ''),
    floatpanelBackdropFrom:       num(d.floatpanelBackdropFrom,       50),
    floatpanelIconColor:          hex(d.floatpanelIconColor,          ''),
    floatpanelPlaceholder:        str(d.floatpanelPlaceholder,        'Ask me anything…'),

    theme:               str(d.theme,             'light'),
    botName:             str(d.botName,           'Magecomp Assistant'),
    botAvatar:           str(d.botAvatar,         ''),
    botInitials:         str(d.botInitials,       'MC'),
    botStatusText:       str(d.botStatusText,     'Online · Typically replies instantly'),
    welcomeMessage:      str(d.welcomeMessage,    'Hi there! 👋 How can I help you today?'),
    welcomeMessage2:     str(d.welcomeMessage2,   ''),
    errorMessage:        str(d.errorMessage,      'Something went wrong. Please try again.'),
    placeholder:         str(d.placeholder,       'Ask me anything...'),
    typingText:          str(d.typingText,        'Assistant is typing'),
    locale:              str(d.locale,            'en'),
    userId:           str(d.userId,        ''),
    userName:         str(d.userName,      ''),
    userEmail:        str(d.userEmail,     ''),
    userBusinessName: str(d.userBusinessName, ''),
    userAvatar:       str(d.userAvatar,    ''),
    userInitials:     str(d.userInitials,  ''),

    position:         str(d.position,  'bottom-right'),
    offsetX:          num(d.offsetX,   24),
    offsetY:          num(d.offsetY,   24),
    width:            num(d.width,     370),
    height:           num(d.height,    580),
    panelRadius:      num(d.panelRadius,20),
    launcherSize:     num(d.launcherSize,52),
    launcherRadius:   num(d.launcherRadius,50),
    zIndex:           num(d.zIndex,    9999),
    mobileFullscreen: bool(d.mobileFullscreen, true),
    mobileBreakpoint: num(d.mobileBreakpoint,  768),

    autoOpen:             bool(d.autoOpen,             false),
    openDelay:            num(d.openDelay,             0),
    minimized:            bool(d.minimized,            false),
    showTimestamps:       bool(d.showTimestamps,       true),
    timestampFormat:      str(d.timestampFormat,       'time'),
    showTypingIndicator:  bool(d.showTypingIndicator,  true),
    showAvatar:           bool(d.showAvatar,           true),
    showAvatarGrouped:    bool(d.showAvatarGrouped,    false),
    allowAttachments:     bool(d.allowAttachments,     false),
    stream:               bool(d.stream,               true),
    persistHistory:       bool(d.persistHistory,       true),
    maxHistory:           num(d.maxHistory,            50),
    soundEnabled:         bool(d.soundEnabled,         false),
    showBranding:         bool(d.showBranding,         true),
    showClearButton:      bool(d.showClearButton,      true),
    showHeaderSubtitle:   bool(d.showHeaderSubtitle,   true),
    showNotificationBadge:bool(d.showNotificationBadge,true),
    inputMaxRows:         num(d.inputMaxRows,          4),
    typingSpeed:          num(d.typingSpeed,           18),
    inactivityReviewSeconds: num(d.inactivityReviewSeconds, 30),

    suggestedQuestions: json(d.suggestedQuestions, []),
    subScript:          str(d.subScript,           ''),
    metadata:           json(d.metadata,           {}),
  });
}

// ─────────────────────────────────────────────────────────
// SECTION 4: SESSION MANAGER
// ─────────────────────────────────────────────────────────

class SessionManager {
  constructor(cfg) {
    this.cfg   = cfg;
    this._sKey = `${MC.STORAGE_KEY}_${cfg.appId}`;
    this._hKey = `${MC.HISTORY_KEY}_${cfg.appId}`;
    this._pKey = `${MC.PREFS_KEY}_${cfg.appId}`;
  }

  getOrCreate() {
    let s = this._load(this._sKey);
    if (!s || !s.sessionId) {
      s = {
        sessionId:       this._uid('s'),
        userId:          this.cfg.userId           || this._uid('u'),
        userName:        this.cfg.userName         || '',
        userEmail:       this.cfg.userEmail        || '',
        userBusinessName:this.cfg.userBusinessName || '',
        userAvatar:      this.cfg.userAvatar       || '',
        appId:           this.cfg.appId,
        entryUrl:        location.href,
        createdAt:       Date.now(),
      };
    }
    if (this.cfg.userId)           s.userId           = this.cfg.userId;
    if (this.cfg.userName)         s.userName         = this.cfg.userName;
    if (this.cfg.userEmail)        s.userEmail        = this.cfg.userEmail;
    if (this.cfg.userBusinessName) s.userBusinessName = this.cfg.userBusinessName;
    if (this.cfg.userAvatar)       s.userAvatar       = this.cfg.userAvatar;
    s.lastSeen = Date.now();
    this._save(this._sKey, s);
    return s;
  }

  getHistory()      { return this._load(this._hKey) || []; }
  getPrefs()        { return this._load(this._pKey) || {}; }
  setPrefs(patch)   { this._save(this._pKey, { ...this.getPrefs(), ...patch }); }

  appendHistory(msg) {
    if (!this.cfg.persistHistory) return;
    const h = this.getHistory();
    h.push(msg);
    if (h.length > this.cfg.maxHistory) h.splice(0, h.length - this.cfg.maxHistory);
    this._save(this._hKey, h);
  }

  updateLastMessage(id, text) {
    const h = this.getHistory();
    const m = h.find(x => x.id === id);
    if (m) { m.text = text; this._save(this._hKey, h); }
  }

  clearHistory()  { localStorage.removeItem(this._hKey); }
  clearSession()  { localStorage.removeItem(this._sKey); }

  // ── Server-side history cache (4-hour TTL) ──────────────────────────
  _cacheKey(sessionId) { return `mc_hist_cache_${this.cfg.appId}_${sessionId}`; }

  getHistoryCache(sessionId) {
    const raw = this._load(this._cacheKey(sessionId));
    if (!raw || !raw.cached_at) return null;
    const FOUR_HOURS = 4 * 60 * 60 * 1000;
    if (Date.now() - raw.cached_at > FOUR_HOURS) return null;
    return raw.messages || [];
  }

  setHistoryCache(sessionId, messages) {
    this._save(this._cacheKey(sessionId), { messages, cached_at: Date.now() });
  }

  clearHistoryCache(sessionId) {
    try { localStorage.removeItem(this._cacheKey(sessionId)); } catch {}
  }

  // ── User identity lookup cache (4-hour TTL, keyed by email) ────────
  _lookupKey(email) { return `mc_user_lookup_${this.cfg.appId}_${encodeURIComponent(email)}`; }

  getUserLookup(email) {
    const raw = this._load(this._lookupKey(email));
    if (!raw || !raw.cached_at) return null;
    if (Date.now() - raw.cached_at > 4 * 60 * 60 * 1000) return null;
    return raw;  // { external_user_id: str|null, cached_at: number }
  }

  setUserLookup(email, externalUserId) {
    this._save(this._lookupKey(email), { external_user_id: externalUserId, cached_at: Date.now() });
  }

  clearUserLookup(email) {
    try { localStorage.removeItem(this._lookupKey(email)); } catch {}
  }

  /** Overwrite userId in the persisted session and return the updated object. */
  patchUserId(userId) {
    const s = this._load(this._sKey) || this.getOrCreate();
    s.userId   = userId;
    s.lastSeen = Date.now();
    this._save(this._sKey, s);
    return s;
  }

  // ── Switch to a different session (history panel load) ──────────────
  setActiveSession(newSessionId) {
    const s = this.getOrCreate();
    s.sessionId = newSessionId;
    s.lastSeen  = Date.now();
    this._save(this._sKey, s);
  }

  _load(k)        { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } }
  _save(k, v)     { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
  _uid(prefix='x'){ return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,9)}`; }
}

// ─────────────────────────────────────────────────────────
// SECTION 5: EVENT BUS
// ─────────────────────────────────────────────────────────

class EventBus {
  constructor(appId) { this._appId = appId; this._h = new Map(); }

  on(ev, fn)   { if (!this._h.has(ev)) this._h.set(ev,[]); this._h.get(ev).push(fn); return ()=>this.off(ev,fn); }
  off(ev, fn)  { this._h.set(ev,(this._h.get(ev)||[]).filter(f=>f!==fn)); }
  once(ev, fn) { const w = d=>{fn(d);this.off(ev,w);}; this.on(ev,w); }

  emit(ev, data={}) {
    (this._h.get(ev)||[]).forEach(fn=>{ try{fn(data);}catch(e){console.error('[MC]',e);} });
    window.dispatchEvent(new CustomEvent(`mc:${ev}`,{ bubbles:false, detail:{ appId:this._appId,...data } }));
  }
}

// ─────────────────────────────────────────────────────────
// SECTION 6: API CLIENT
// ─────────────────────────────────────────────────────────

class ApiClient {
  constructor(cfg, sessionData, bus, analytics = null) {
    this._cfg       = cfg;
    this._sess      = sessionData;
    this._bus       = bus;
    this._analytics = analytics;
    this._ctrl      = null;
  }

  async send(message, { onChunk, onDone, onError } = {}) {
    if (this._ctrl) this._ctrl.abort();
    this._ctrl = new AbortController();

    const payload = {
      app_id:     this._cfg.appId,
      session_id: this._sess.sessionId,
      message,
      stream:     this._cfg.stream,
      user_info: {
        external_user_id: this._sess.userId          || null,
        name:             this._sess.userName        || null,
        email:            this._sess.userEmail       || null,
        business_name:    this._sess.userBusinessName|| null,
        extra_metadata:   Object.keys(this._cfg.metadata || {}).length
                            ? { ...this._cfg.metadata, widget: MC.VERSION }
                            : { widget: MC.VERSION },
      },
      session_context: {
        entry_url:   this._sess.entryUrl  || null,
        exit_url:    null,
        device_type: this._analytics?.deviceType || null,
        browser:     this._analytics?.browser    || null,
        extra_metadata: null,
      },
    };

    try {
      const res = await fetch(`${this._cfg.apiUrl}/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
        signal:  this._ctrl.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(()=>({}));
        throw Object.assign(new Error(err.error || res.statusText), { status: res.status });
      }

      if (this._cfg.stream && res.headers.get('content-type')?.includes('event-stream')) {
        await this._sse(res, onChunk, onDone);
      } else {
        const data = await res.json();
        onDone?.({ reply: data.reply, tokens: data.token_usage });
      }
    } catch(e) {
      if (e.name === 'AbortError') return;
      this._bus.emit('error', { error: e.message, status: e.status || 0 });
      onError?.(e);
    }
  }

  async _sse(res, onChunk, onDone) {
    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buf='', full='', meta={};

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const raw = line.slice(5).trim();
        if (!raw || raw === '[DONE]') continue;
        try {
          const p = JSON.parse(raw);
          if (p.chunk) { full += p.chunk; onChunk?.(p.chunk, full); }
          if (p.done)  meta = {
            tokens:         p.token_usage,
            timestamp:      p.timestamp,
            user_timestamp: p.user_timestamp,
          };
        } catch {}
      }
    }
    onDone?.({ reply: full, ...meta });
  }

  abort() { this._ctrl?.abort(); this._ctrl = null; }

  // ── Session API methods ───────────────────────────────────────────────────

  async createSession() {
    const sess = this._sess;
    const body = {
      session_id: sess.sessionId,
      app_id:     this._cfg.appId,
      user_info: {
        external_user_id: sess.userId          || null,
        name:             sess.userName        || null,
        email:            sess.userEmail       || null,
        business_name:    sess.userBusinessName|| null,
      },
      session_context: {
        entry_url:   sess.entryUrl || null,
        device_type: this._analytics?.deviceType || null,
        browser:     this._analytics?.browser    || null,
      },
    };
    const res = await fetch(`${this._cfg.apiUrl}/chat/session/create`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`session/create ${res.status}`);
    return res.json();
  }

  async fetchHistory(sessionId) {
    const res = await fetch(
      `${this._cfg.apiUrl}/chat/history/${encodeURIComponent(sessionId)}?app_id=${encodeURIComponent(this._cfg.appId)}`,
      { method: 'GET' }
    );
    if (!res.ok) throw new Error(`history ${res.status}`);
    return res.json();  // { session_id, messages: [{role, content, timestamp}] }
  }

  async fetchSessions() {
    const userId = this._sess.userId || '';
    const res = await fetch(
      `${this._cfg.apiUrl}/chat/sessions?app_id=${encodeURIComponent(this._cfg.appId)}&user_id=${encodeURIComponent(userId)}`,
      { method: 'GET' }
    );
    if (!res.ok) throw new Error(`sessions ${res.status}`);
    return res.json();  // { sessions: [...] }
  }

  async submitReview(sessionId, rating, label, comment) {
    const res = await fetch(`${this._cfg.apiUrl}/chat/session/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, app_id: this._cfg.appId, rating, emoji_label: label, comment: comment || null }),
    });
    if (!res.ok) throw new Error(`review ${res.status}`);
    return res.json();
  }
}

// ─────────────────────────────────────────────────────────
// SECTION 7: ANALYTICS QUEUE + CLIENT
// ─────────────────────────────────────────────────────────

class AnalyticsQueue {
  constructor(maxRetries = 3, baseDelayMs = 1500) {
    this._queue      = [];
    this._maxRetries = maxRetries;
    this._baseDelay  = baseDelayMs;
    this._running    = false;
  }

  enqueue(fn, label = 'analytics') {
    this._queue.push({ fn, label, attempts: 0 });
    this._run();
  }

  async _run() {
    if (this._running || !this._queue.length) return;
    this._running = true;
    const item = this._queue[0];
    try {
      await item.fn();
      this._queue.shift();
    } catch(e) {
      item.attempts++;
      if (item.attempts >= this._maxRetries) {
        console.warn(`[MC] Analytics dropped after ${this._maxRetries} retries: ${item.label}`);
        this._queue.shift();
      } else {
        const delay = this._baseDelay * Math.pow(2, item.attempts - 1); // exponential back-off
        await new Promise(r => setTimeout(r, delay));
      }
    }
    this._running = false;
    if (this._queue.length) this._run();
  }
}

class AnalyticsClient {
  constructor(cfg, sessionData, queue) {
    this._cfg   = cfg;
    this._sess  = sessionData;
    this._queue = queue;
    this.deviceType = this._detectDevice();
    this.browser    = this._detectBrowser();
  }

  /**
   * Send a session-end signal.
   * @param {string} exitUrl
   * @param {boolean} unloading  true when called from a page-exit event (uses beacon/keepalive)
   */
  endSession(exitUrl = location.href, unloading = false) {
    const url  = `${this._cfg.apiUrl}/chat/session/end`;
    const body = JSON.stringify({
      session_id: this._sess.sessionId,
      app_id:     this._cfg.appId,
      exit_url:   exitUrl,
    });

    if (unloading) {
      // Prefer sendBeacon (fire-and-forget, survives tab close)
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        const ok = navigator.sendBeacon(url, blob);
        if (ok) return;
      }
      // Fallback: keepalive fetch (also survives tab close in most browsers)
      fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true }).catch(() => {});
      return;
    }

    // Normal (non-unload) path: use the retrying queue
    this._queue.enqueue(
      () => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body }),
      'endSession'
    );
  }

  /** Queue any analytics POST with retry. */
  track(path, payload, label = 'track') {
    const url  = `${this._cfg.apiUrl}${path}`;
    const body = JSON.stringify(payload);
    this._queue.enqueue(
      () => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body }),
      label
    );
  }

  _detectDevice() {
    const ua = navigator.userAgent;
    if (/tablet|ipad|playbook|silk/i.test(ua))                       return 'tablet';
    if (/mobile|iphone|ipod|android|blackberry|mini|palm/i.test(ua)) return 'mobile';
    return 'desktop';
  }

  _detectBrowser() {
    const ua = navigator.userAgent;
    if (/edg\//i.test(ua))   return 'Edge';
    if (/opr\//i.test(ua))   return 'Opera';
    if (/chrome/i.test(ua))  return 'Chrome';
    if (/safari/i.test(ua))  return 'Safari';
    if (/firefox/i.test(ua)) return 'Firefox';
    if (/trident/i.test(ua)) return 'IE';
    return 'Unknown';
  }
}

// ─────────────────────────────────────────────────────────
// SECTION 8: ACTIVITY OBSERVER + PLUGIN LOADER
// ─────────────────────────────────────────────────────────

class ActivityObserver {
  constructor(onIdle, idleSeconds = 30) {
    this._onIdle  = onIdle;
    this._idleMs  = idleSeconds * 1000;
    this._timer   = null;
    this._active  = false;
    this._fired   = false;       // shows only once per session
    this._handler = this._reset.bind(this);
    this._events  = ['mousemove','click','keydown','scroll','touchstart'];
  }

  start() {
    if (this._active) return;
    this._active = true;
    this._events.forEach(e => document.addEventListener(e, this._handler, { passive: true }));
    this._reset();
  }

  stop() {
    clearTimeout(this._timer);
    this._active = false;
    this._events.forEach(e => document.removeEventListener(e, this._handler));
  }

  resetForNewSession() { this._fired = false; this._reset(); }

  _reset() {
    clearTimeout(this._timer);
    if (this._fired) return;
    this._timer = setTimeout(() => { this._fired = true; this._onIdle(); }, this._idleMs);
  }
}

class PluginLoader {
  constructor(bus) { this._bus = bus; this._loaded = new Set(); }

  async load(url, publicAPI) {
    if (!url || this._loaded.has(url)) return;
    try {
      const mod = await import(/* webpackIgnore:true */ url);
      if (typeof mod.default !== 'function') return;
      await mod.default(publicAPI);
      this._loaded.add(url);
      this._bus.emit('plugin:load', { url, id: url.split('/').pop().replace(/\.[^.]+$/,'') });
    } catch(e) { console.error('[MC] Plugin failed:', url, e); }
  }
}

// ─────────────────────────────────────────────────────────
// SECTION 8: INLINE SVG ICONS
// ─────────────────────────────────────────────────────────

const ICONS = {
  chat:    `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>`,
  close:   `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  send:    `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="22 2 15 22 11 13 2 9"/><line x1="22" y1="2" x2="11" y2="13" stroke="currentColor" stroke-width="2" fill="none"/></svg>`,
  attach:  `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>`,
  copy:    `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>`,
  check:   `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  history: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  newchat: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
  back:    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>`,
};

// ─────────────────────────────────────────────────────────
// SECTION 9: CSS
// ─────────────────────────────────────────────────────────

const MC_STYLES = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:host {
  all: initial;
  display: block;
  position: fixed;
  z-index: var(--mc-z);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

:host([data-position="bottom-right"]) { bottom: var(--mc-offset-y); right: var(--mc-offset-x); }
:host([data-position="bottom-left"])  { bottom: var(--mc-offset-y); left:  var(--mc-offset-x); }
:host([data-position="top-right"])    { top:    var(--mc-offset-y); right: var(--mc-offset-x); }
:host([data-position="top-left"])     { top:    var(--mc-offset-y); left:  var(--mc-offset-x); }

/* ── LAUNCHER ─────────────────────────────────────── */
.mc-launcher {
  width:  var(--mc-launcher-size);
  height: var(--mc-launcher-size);
  border-radius: var(--mc-r-launcher);
  background: var(--mc-launcher-bg);
  border: 3px solid var(--mc-bg, #fff);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--mc-launcher-icon);
  position: relative;
  transition: transform 200ms cubic-bezier(0.34,1.56,0.64,1), box-shadow 200ms;
  box-shadow: 0 8px 24px var(--mc-shadow-color);
  animation: mc-pop-in 400ms cubic-bezier(0.34,1.56,0.64,1) both;
  outline: none;
}
.mc-launcher:hover  { transform: scale(1.10); box-shadow: 0 12px 32px var(--mc-shadow-color); }
.mc-launcher:active { transform: scale(0.94); }
.mc-launcher:focus-visible { outline: 3px solid var(--mc-grad-start); outline-offset: 3px; }

.mc-launcher .mc-icon-chat  { display: flex; transition: transform 250ms cubic-bezier(0.4,0,0.2,1); }
.mc-launcher .mc-icon-close { display: none; transform: rotate(-90deg); transition: transform 250ms cubic-bezier(0.4,0,0.2,1); }
:host([data-open]) .mc-launcher .mc-icon-chat  { display: none; }
:host([data-open]) .mc-launcher .mc-icon-close { display: flex; transform: rotate(0deg); }

.mc-badge {
  position: absolute;
  top: -3px; right: -3px;
  width: 14px; height: 14px;
  background: var(--mc-badge-bg);
  border-radius: 50%;
  border: 2px solid white;
  animation: mc-badge-pulse 2s ease-in-out infinite;
}
.mc-badge[hidden] { display: none; }

@keyframes mc-badge-pulse {
  0%,100% { transform: scale(1);   opacity: 1; }
  50%      { transform: scale(1.2); opacity: 0.8; }
}
@keyframes mc-pop-in {
  from { transform: scale(0); opacity: 0; }
  to   { transform: scale(1); opacity: 1; }
}

/* ── PANEL ────────────────────────────────────────── */
.mc-panel {
  position: absolute;
  bottom: calc(var(--mc-launcher-size) + 14px);
  right: 0;
  width:  var(--mc-width);
  height: var(--mc-height);
  background: var(--mc-bg);
  border-radius: var(--mc-r-panel);
  box-shadow: var(--mc-shadow-panel);
  display: flex; flex-direction: column;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  transform: translateY(16px) scale(0.97);
  transform-origin: bottom right;
  transition: opacity 260ms cubic-bezier(0.4,0,0.2,1),
              transform 260ms cubic-bezier(0.34,1.2,0.64,1);
  will-change: transform, opacity;
}
:host([data-open]) .mc-panel {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0) scale(1);
}
:host([data-position="bottom-left"]) .mc-panel  { right: auto; left: 0; transform-origin: bottom left; }
:host([data-position="top-right"])   .mc-panel  { bottom: auto; top: calc(var(--mc-launcher-size) + 14px); transform-origin: top right; }
:host([data-position="top-left"])    .mc-panel  { bottom: auto; top: calc(var(--mc-launcher-size) + 14px); right: auto; left: 0; transform-origin: top left; }

/* ── HEADER ───────────────────────────────────────── */
.mc-header {
  background: var(--mc-gradient);
  padding: 14px 16px;
  display: flex; align-items: center; gap: 11px;
  flex-shrink: 0;
}
.mc-avatar-ring {
  width: 42px; height: 42px;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.mc-avatar-inner {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: rgba(255,255,255,0.95);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  font-size: 12px; font-weight: 700;
  color: var(--mc-grad-start);
}
.mc-avatar-inner img { width: 100%; height: 100%; object-fit: cover; }
.mc-header-info { flex: 1; min-width: 0; }
.mc-header-name {
  color: var(--mc-header-text);
  font-size: 14px; font-weight: 600;
  letter-spacing: -0.01em; line-height: 1.3;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mc-header-status {
  display: flex; align-items: center; gap: 5px;
  color: rgba(255,255,255,0.75);
  font-size: 11px; margin-top: 2px;
}
.mc-status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--mc-status-dot);
  flex-shrink: 0;
  animation: mc-pulse 2s ease-in-out infinite;
}
@keyframes mc-pulse { 0%,100%{opacity:1}50%{opacity:0.6} }
.mc-header-actions { display: flex; gap: 4px; }
.mc-hbtn {
  width: 28px; height: 28px;
  border-radius: 8px;
  background: rgba(255,255,255,0.12);
  border: none; cursor: pointer;
  color: rgba(255,255,255,0.9);
  display: flex; align-items: center; justify-content: center;
  transition: background 150ms;
  flex-shrink: 0;
}
.mc-hbtn:hover  { background: rgba(255,255,255,0.22); }
.mc-hbtn:active { background: rgba(255,255,255,0.08); }
.mc-hbtn:focus-visible { outline: 2px solid rgba(255,255,255,0.7); outline-offset: 1px; }

/* ── MESSAGES ─────────────────────────────────────── */
.mc-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: var(--mc-bg-messages);
  display: flex; flex-direction: column; gap: 10px;
  scroll-behavior: smooth;
}
.mc-messages::-webkit-scrollbar       { width: 4px; }
.mc-messages::-webkit-scrollbar-track { background: var(--mc-scrollbar-track); }
.mc-messages::-webkit-scrollbar-thumb { background: var(--mc-scrollbar-thumb); border-radius: 2px; }

/* ── ROWS ─────────────────────────────────────────── */
.mc-row      { display: flex; gap: 8px; align-items: flex-end; animation: mc-slide-in-left  200ms cubic-bezier(0.4,0,0.2,1) both; }
.mc-row-user { justify-content: flex-end;                       animation: mc-slide-in-right 200ms cubic-bezier(0.4,0,0.2,1) both; }
@keyframes mc-slide-in-left  { from{transform:translateX(-10px);opacity:0} to{transform:none;opacity:1} }
@keyframes mc-slide-in-right { from{transform:translateX(10px); opacity:0} to{transform:none;opacity:1} }

.mc-av-sm {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--mc-gradient);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  font-size: 9px; font-weight: 700;
  color: var(--mc-launcher-icon);
  overflow: hidden;
}
.mc-av-sm img    { width:100%; height:100%; object-fit:cover; }
.mc-av-sm.hidden { visibility: hidden; }

.mc-bubble-wrap { display: flex; flex-direction: column; gap: 3px; max-width: 78%; }
.mc-row-user .mc-bubble-wrap { align-items: flex-end; }

/* ── BUBBLES ──────────────────────────────────────── */
.mc-bubble {
  background: var(--mc-bot-bubble-bg);
  color: var(--mc-bot-bubble-text);
  border: 1px solid var(--mc-bot-bubble-border);
  border-radius: 4px var(--mc-r-bubble) var(--mc-r-bubble) var(--mc-r-bubble);
  padding: 10px 13px;
  font-size: 13.5px; line-height: 1.55;
  word-wrap: break-word;
}
.mc-bubble-user {
  background: var(--mc-user-bubble-bg);
  color: var(--mc-user-bubble-text);
  border: none;
  border-radius: var(--mc-r-bubble) 4px var(--mc-r-bubble) var(--mc-r-bubble);
}
.mc-bubble a       { color: var(--mc-grad-start); text-decoration: underline; word-break: break-all; }
.mc-bubble strong  { font-weight: 600; }
.mc-bubble em      { font-style: italic; }
.mc-bubble blockquote {
  border-left: 3px solid var(--mc-grad-start);
  margin: 6px 0; padding: 4px 10px;
  background: var(--mc-input-bg);
  border-radius: 0 6px 6px 0;
  color: var(--mc-timestamp);
}
.mc-bubble ul      { padding-left: 18px; margin: 4px 0; }
.mc-bubble li      { margin: 2px 0; }
.mc-bubble pre {
  background: var(--mc-input-bg);
  border-radius: 8px; padding: 10px 12px;
  overflow-x: auto; margin: 6px 0;
  position: relative;
}
.mc-bubble pre code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; background: none; padding: 0;
}
.mc-bubble code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: var(--mc-input-bg);
  border-radius: 4px; padding: 1px 5px;
}
.mc-copy-btn {
  position: absolute; top: 6px; right: 6px;
  background: var(--mc-bg); border: 1px solid var(--mc-border);
  border-radius: 6px; padding: 2px 7px;
  font-size: 10px; cursor: pointer;
  color: var(--mc-timestamp); opacity: 0;
  transition: opacity 150ms, background 150ms;
  font-family: inherit;
}
.mc-bubble pre:hover .mc-copy-btn { opacity: 1; }
.mc-copy-btn:hover { background: var(--mc-grad-start); color: #fff; border-color: transparent; }

.mc-ts {
  font-size: 10px; color: var(--mc-timestamp); letter-spacing: 0.01em;
}
.mc-row-user .mc-ts { text-align: right; }

.mc-system {
  text-align: center; font-size: 11px;
  color: var(--mc-timestamp); padding: 4px 12px;
  background: rgba(0,0,0,0.04); border-radius: 999px; align-self: center;
}

/* ── DATE SEPARATOR ───────────────────────────────── */
.mc-date-sep {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px; align-self: stretch;
}
.mc-date-sep::before,
.mc-date-sep::after {
  content: ''; flex: 1; height: 1px;
  background: var(--mc-border);
}
.mc-date-sep span {
  font-size: 11px; font-weight: 500; white-space: nowrap;
  color: var(--mc-timestamp);
  background: var(--mc-surface);
  padding: 2px 10px; border-radius: 999px;
  border: 1px solid var(--mc-border);
}

/* ── TYPING ───────────────────────────────────────── */
.mc-typing {
  display: flex; gap: 8px; align-items: flex-end;
  padding: 0 16px 10px;
  background: var(--mc-bg-messages);
  flex-shrink: 0;
}
.mc-typing[hidden] { display: none; }
.mc-dots {
  background: var(--mc-bot-bubble-bg);
  border: 1px solid var(--mc-bot-bubble-border);
  border-radius: 4px var(--mc-r-bubble) var(--mc-r-bubble) var(--mc-r-bubble);
  padding: 12px 16px;
  display: flex; gap: 5px; align-items: center;
}
.mc-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--mc-typing-dot);
  animation: mc-bounce 1.2s ease-in-out infinite;
}
.mc-dot:nth-child(2) { animation-delay: 0.2s; }
.mc-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes mc-bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }

/* ── CHIPS ────────────────────────────────────────── */
.mc-chips {
  display: flex; gap: 7px;
  flex-wrap: nowrap; overflow-x: auto;
  padding: 8px 14px;
  background: var(--mc-bg-messages);
  border-top: 1px solid var(--mc-border);
  scrollbar-width: none; flex-shrink: 0;
}
.mc-chips::-webkit-scrollbar { display: none; }
.mc-chips[hidden] { display: none; }
.mc-chip {
  border: 1.5px solid var(--mc-chip-border);
  color: var(--mc-chip-text);
  background: var(--mc-chip-bg);
  border-radius: var(--mc-r-chip);
  padding: 5px 12px;
  font-size: 11.5px; font-weight: 500;
  cursor: pointer; white-space: nowrap;
  transition: all 160ms cubic-bezier(0.4,0,0.2,1);
  font-family: inherit;
}
.mc-chip:hover {
  background: var(--mc-chip-hover-bg);
  color: var(--mc-chip-hover-text);
  border-color: transparent;
  transform: translateY(-1px);
}
.mc-chip:active { transform: translateY(0); }

/* ── INPUT AREA ───────────────────────────────────── */
.mc-input-area {
  background: var(--mc-bg);
  padding: 10px 14px 12px;
  border-top: 1px solid var(--mc-border);
  flex-shrink: 0;
}
.mc-input-row {
  display: flex; align-items: center; gap: 8px;
  background: var(--mc-input-bg);
  border-radius: var(--mc-r-input);
  padding: 8px 10px 8px 14px;
  border: 1.5px solid transparent;
  transition: border-color 200ms;
}
.mc-input-row:focus-within { border-color: var(--mc-input-border-focus); }
.mc-attach-btn {
  background: none; border: none; cursor: pointer;
  color: var(--mc-input-placeholder);
  display: flex; align-items: center; padding: 2px;
  flex-shrink: 0; align-self: flex-end; margin-bottom: 2px;
  transition: color 150ms;
}
.mc-attach-btn:hover { color: var(--mc-input-text); }
.mc-attach-btn[hidden] { display: none; }
.mc-input {
  flex: 1; border: none; outline: none; background: transparent;
  font-family: inherit; font-size: 13.5px;
  color: var(--mc-input-text);
  resize: none; line-height: 1.5;
  min-height: 22px; max-height: 90px;
  overflow-y: auto; scrollbar-width: thin;
}
.mc-input::placeholder { color: var(--mc-input-placeholder); }
.mc-send-btn {
  width: 32px; height: 32px;
  border-radius: var(--mc-r-send);
  background: var(--mc-send-bg);
  border: none; cursor: pointer;
  color: var(--mc-send-icon);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: transform 150ms, opacity 150ms;
}
.mc-send-btn:hover:not(:disabled)  { transform: scale(1.08); }
.mc-send-btn:active:not(:disabled) { transform: scale(0.93); }
.mc-send-btn:disabled {
  background: var(--mc-border);
  color: var(--mc-input-placeholder);
  cursor: not-allowed; opacity: 1;
}

/* ── FOOTER ───────────────────────────────────────── */
.mc-footer {
  text-align: center; padding: 7px 12px 9px;
  font-size: 10.5px; color: var(--mc-footer-text);
  letter-spacing: 0.01em; flex-shrink: 0;
}
.mc-footer[hidden] { display: none; }
.mc-footer a { color: var(--mc-footer-link); font-weight: 600; text-decoration: none; }
.mc-footer a:hover { text-decoration: underline; }

/* ── HISTORY PANEL ────────────────────────────────── */
.mc-history-panel {
  position: absolute; inset: 0;
  background: var(--mc-bg);
  z-index: 5;
  display: flex; flex-direction: column;
  transform: translateX(100%);
  transition: transform 280ms cubic-bezier(0.4,0,0.2,1);
  border-radius: var(--mc-r-panel);
  overflow: hidden;
}
.mc-history-panel.open { transform: translateX(0); }
.mc-history-panel[hidden] { display: none; }
.mc-history-head {
  background: var(--mc-gradient);
  padding: 14px 16px;
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}
.mc-history-head span { color: #fff; font-size: 14px; font-weight: 600; }
.mc-history-close {
  background: rgba(255,255,255,0.15); border: none; cursor: pointer;
  color: #fff; width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; transition: background 150ms;
}
.mc-history-close:hover { background: rgba(255,255,255,0.25); }
.mc-history-list {
  flex: 1; overflow-y: auto; padding: 10px;
  display: flex; flex-direction: column; gap: 6px;
}
.mc-history-list::-webkit-scrollbar { width: 4px; }
.mc-history-list::-webkit-scrollbar-thumb { background: var(--mc-scrollbar-thumb); border-radius: 2px; }
.mc-history-entry {
  padding: 11px 13px;
  background: var(--mc-surface-2);
  border: 1px solid var(--mc-border);
  border-radius: 10px; cursor: pointer;
  transition: border-color 150ms, background 150ms;
}
.mc-history-entry:hover { border-color: var(--mc-grad-start); background: var(--mc-input-bg); }
.mc-history-entry-time { font-size: 10.5px; color: var(--mc-timestamp); margin-bottom: 4px; }
.mc-history-entry-preview {
  font-size: 12.5px; color: var(--mc-bot-bubble-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mc-history-empty { text-align: center; color: var(--mc-timestamp); font-size: 12px; padding: 32px 16px; }

/* ── REVIEW PROMPT ─────────────────────────────────── */
.mc-review-prompt {
  margin: 0 16px 8px;
  padding: 12px 14px;
  background: var(--mc-surface-2);
  border: 1px solid var(--mc-border-strong);
  border-radius: 12px; flex-shrink: 0;
  animation: mc-slide-in-left 200ms cubic-bezier(0.4,0,0.2,1) both;
}
.mc-review-prompt[hidden] { display: none; }
.mc-review-label {
  font-size: 12px; font-weight: 500; color: var(--mc-bot-bubble-text);
  margin-bottom: 10px; text-align: center;
}
.mc-review-emojis { display: flex; justify-content: center; gap: 6px; }
.mc-review-btn {
  font-size: 22px; background: none; border: 2px solid transparent;
  border-radius: 10px; padding: 4px 7px; cursor: pointer;
  transition: border-color 150ms, transform 150ms; line-height: 1;
}
.mc-review-btn:hover { border-color: var(--mc-grad-start); transform: scale(1.15); }
.mc-review-btn:active { transform: scale(0.95); }
.mc-review-btn.mc-selected { border-color: var(--mc-grad-start); background: rgba(var(--mc-grad-start-rgb,99,102,241),0.12); transform: scale(1.1); }
.mc-review-comment-wrap { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
.mc-review-comment-wrap[hidden] { display: none; }
.mc-review-textarea {
  width: 100%; padding: 7px 10px; font-size: 12.5px; font-family: inherit;
  background: var(--mc-surface); border: 1px solid var(--mc-border-strong);
  border-radius: 8px; color: var(--mc-bot-bubble-text); resize: none;
  outline: none; transition: border-color 150ms; box-sizing: border-box;
}
.mc-review-textarea:focus { border-color: var(--mc-grad-start); }
.mc-review-submit {
  align-self: flex-end; padding: 5px 14px; font-size: 12px; font-weight: 600;
  background: var(--mc-grad-start); color: #fff; border: none;
  border-radius: 8px; cursor: pointer; transition: opacity 150ms;
}
.mc-review-submit:hover { opacity: 0.85; }
.mc-review-thanks { text-align: center; font-size: 12px; color: var(--mc-bot-bubble-text); padding: 4px 0; }

/* ── ERROR TOAST ──────────────────────────────────── */
.mc-toast {
  position: absolute; bottom: 80px; left: 14px; right: 14px;
  background: #ef4444; color: #fff;
  border-radius: 10px; padding: 10px 14px;
  font-size: 12px; font-weight: 500;
  animation: mc-toast-in 250ms cubic-bezier(0.34,1.2,0.64,1);
  z-index: 10;
}
@keyframes mc-toast-in { from{transform:translateY(10px);opacity:0} }

/* ── MOBILE ───────────────────────────────────────── */
/* only expand host to full-screen when chat is open — closed state must not block the page */
:host([data-mobile][data-open]) {
  position: fixed; inset: 0;
  width: 100% !important; height: 100% !important;
}
:host([data-mobile]) .mc-panel {
  position: fixed; inset: 0;
  width: 100%; height: 100%;
  border-radius: 0; bottom: 0; top: 0; right: 0; left: 0;
  transform-origin: center bottom;
}
/* hide launcher only while the full-screen panel is open, not when closed */
:host([data-mobile][data-open]) .mc-launcher { display: none; }

/* ── MINIMIZED ────────────────────────────────────── */
:host([data-minimized]) .mc-panel { display: none; }

/* ── RTL ──────────────────────────────────────────── */
:host([dir="rtl"]) .mc-row      { flex-direction: row-reverse; }
:host([dir="rtl"]) .mc-row-user { flex-direction: row; }
:host([dir="rtl"]) .mc-bubble      { border-radius: var(--mc-r-bubble) 4px var(--mc-r-bubble) var(--mc-r-bubble); }
:host([dir="rtl"]) .mc-bubble-user { border-radius: 4px var(--mc-r-bubble) var(--mc-r-bubble) var(--mc-r-bubble); }
`;

// ─────────────────────────────────────────────────────────
// SECTION 9b: FLOATPANEL VARIANT CSS
// ─────────────────────────────────────────────────────────

const FLOATPANEL_STYLES = `
/* ═══════════════════════════════════════════════════════
   FLOATPANEL VARIANT
   Host is a full-screen fixed overlay. The trigger input
   box floats at bottom-center at rest. When open the full-
   width panel expands upward and the input becomes part of
   the interface, still centered.
═══════════════════════════════════════════════════════ */

/* ── HOST: full-screen fixed layer ───────────────────── */
:host([data-variant="floatpanel"]) {
  position: fixed !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  pointer-events: none;
  z-index: var(--mc-z);
}

/* ── CENTRED COLUMN: constrains all content to configured width */
.mc-gcol {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: var(--mc-g-desktop-width);
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  /* closed: column takes no pointer events — only input wrap is interactive */
  pointer-events: none;
  height: auto;
}
/* only the input wrap is clickable when chat is closed */
:host([data-variant="floatpanel"]) .mc-ginput-wrap {
  pointer-events: auto;
}
:host([data-open][data-variant="floatpanel"]) .mc-gcol {
  height: 100vh;
  height: 100dvh;
  pointer-events: auto;
}

@media (max-width: 768px) {
  .mc-gcol { width: var(--mc-g-mobile-width); }
}

/* ── FULL-WIDTH PANEL BACKDROP ────────────────────────── */
/* True transparent-at-top → solid-white-at-bottom gradient.
   The gradient covers the full viewport height. The bottom 30%
   is fully opaque white. The top 50% is fully transparent.     */
.mc-gpanel-backdrop {
  position: fixed;
  inset: 0;
  background: var(--mc-g-backdrop);
  opacity: 0;
  pointer-events: none;
  transition: opacity 320ms cubic-bezier(0.4,0,0.2,1);
  z-index: -1;
}
:host([data-open][data-variant="floatpanel"]) .mc-gpanel-backdrop {
  opacity: 1;
}

/* ── MESSAGE AREA ─────────────────────────────────────── */
/*
  Height is purely content-driven — no flex:1, no fixed height.
  justify-content:flex-end makes messages stack at the bottom
  so the first message appears just above the input bar.
  As conversation grows, messages push upward naturally.
  max-height keeps it from overflowing the viewport.
*/
.mc-gpanel-messages {
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px 16px 4px;
  display: flex;
  flex-direction: column;
  /* spacer at top pushes messages to bottom — see .mc-gmsg-spacer */
  gap: 10px;
  scroll-behavior: smooth;
  opacity: 0;
  pointer-events: none;
  transition: opacity 240ms 60ms;
  max-height: calc(100vh - 160px);
  max-height: calc(100dvh - 160px);
  /* depth fade: top messages ghosted, fully opaque at bottom */
  mask-image: linear-gradient(to bottom,
    transparent 0%,
    rgba(0,0,0,0.2) 12%,
    rgba(0,0,0,0.65) 30%,
    black 50%);
  -webkit-mask-image: linear-gradient(to bottom,
    transparent 0%,
    rgba(0,0,0,0.2) 12%,
    rgba(0,0,0,0.65) 30%,
    black 50%);
  /* transparent — no background block in the message area */
  background: transparent !important;
  /* collapsed when chat is closed so it takes zero height */
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
:host([data-open][data-variant="floatpanel"]) .mc-gpanel-messages {
  opacity: 1;
  pointer-events: auto;
  max-height: calc(100vh - 160px);
  max-height: calc(100dvh - 160px);
  padding-top: 20px;
  padding-bottom: 4px;
}
.mc-gpanel-messages { scrollbar-width: none; }
.mc-gpanel-messages::-webkit-scrollbar { display: none; }
.mc-gpanel-messages.mc-g-hidden { display: none !important; }

/* Spacer: grows to fill empty space (pushes messages to bottom).
   Collapses to 0 when messages overflow so scroll works normally. */
.mc-gmsg-spacer { flex: 1; min-height: 0; }

/* Strip all opaque backgrounds from Floatpanel message layer so the
   gradient backdrop shows through cleanly                        */
.mc-gcol .mc-messages,
.mc-gcol .mc-typing,
.mc-gcol .mc-chips,
.mc-gcol .mc-dots  { background: transparent !important; }

/* Date separator pill — transparent background in Floatpanel */
.mc-gcol .mc-date-sep span {
  background: transparent !important;
  border-color: transparent !important;
}

/* System messages — subtle, no filled pill */
.mc-gcol .mc-system {
  background: transparent !important;
  color: var(--mc-timestamp);
}

/* ── TYPING + CHIPS (inside panel only) ──────────────── */
.mc-gtyping {
  display: flex; gap: 8px; align-items: flex-end;
  padding: 0 2px 6px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 200ms;
}
.mc-gtyping[hidden] { display: none !important; }
:host([data-open][data-variant="floatpanel"]) .mc-gtyping { opacity: 1; }

.mc-gchips {
  display: flex; gap: 7px;
  flex-wrap: nowrap; overflow-x: auto;
  padding: 4px 2px;
  scrollbar-width: none; flex-shrink: 0;
  opacity: 0;
  transition: opacity 200ms;
}
.mc-gchips::-webkit-scrollbar { display: none; }
.mc-gchips[hidden] { display: none !important; }
:host([data-open][data-variant="floatpanel"]) .mc-gchips { opacity: 1; }

/* ── REVIEW PROMPT ────────────────────────────────────── */
.mc-greview {
  padding: 12px 14px;
  background: var(--mc-surface-2);
  border: 1px solid var(--mc-border-strong);
  border-radius: 12px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 200ms;
  animation: mc-slide-in-left 200ms cubic-bezier(0.4,0,0.2,1) both;
}
.mc-greview[hidden] { display: none !important; }
:host([data-open][data-variant="floatpanel"]) .mc-greview { opacity: 1; }

/* ── INPUT BAR WRAPPER ────────────────────────────────── */
.mc-ginput-wrap {
  flex-shrink: 0;
  padding: 8px 0 16px;
  position: relative;
}

/*
  Gradient border: a wide linear-gradient (300% wide) slides
  horizontally behind the input row via background-position.
  No rotation — stays fully contained, no overflow.
  First and last color stop are the same so the loop is seamless.
*/
.mc-ginput-wrap::before {
  content: '';
  position: absolute;
  /* 2px outside the input row on all sides = border thickness */
  inset: 6px -2px 14px;
  border-radius: 16px;
  padding: 2px;                /* border thickness — controls how wide the ring is */
  background: linear-gradient(
    90deg,
    var(--mc-g-gc1),
    var(--mc-g-gc2),
    var(--mc-g-gc3),
    var(--mc-g-gc4),
    var(--mc-g-gc1)
  );
  background-size: 300% 100%;
  animation: mc-g-border-flow 4s linear infinite;
  /* punch out the center: only the padded border ring is visible */
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: destination-out;
  mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite: exclude;
  z-index: 0;
  transition: opacity 220ms;
}
/* when open: stop animation, show primary-coloured solid border ring */
:host([data-open][data-variant="floatpanel"]) .mc-ginput-wrap::before {
  animation: none;
  background: var(--mc-input-border-focus);  /* = primary colour, updated by liveColor() */
  background-size: auto;
}

@keyframes mc-g-border-flow {
  0%   { background-position: 0%   50%; }
  100% { background-position: 100% 50%; }
}

/* ── INPUT ROW ITSELF ─────────────────────────────────── */
.mc-ginput-row {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--mc-input-bg);   /* same as popup */
  border-radius: 14px;
  padding: 10px 10px 10px 16px;
  border: none;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  opacity: 0.72;
  transition: opacity 220ms cubic-bezier(0.4,0,0.2,1),
              box-shadow 220ms;
}
:host([data-open][data-variant="floatpanel"]) .mc-ginput-row,
.mc-ginput-wrap:hover .mc-ginput-row,
.mc-ginput-row:focus-within {
  opacity: 1;
  box-shadow: 0 6px 32px rgba(0,0,0,0.12);
}

/* text + placeholder — same vars as popup */
.mc-ginput-row .mc-input {
  color: var(--mc-input-text);
}
.mc-ginput-row .mc-input::placeholder {
  color: var(--mc-input-placeholder);
}

/* send button — same colours as popup */
.mc-ginput-row .mc-send-btn {
  background: var(--mc-send-bg);
  color: var(--mc-send-icon);
}
.mc-ginput-row .mc-send-btn:disabled {
  background: var(--mc-border);
  color: var(--mc-input-placeholder);
}

/* attach button colour */
.mc-ginput-row .mc-attach-btn {
  color: var(--mc-input-placeholder);
}
.mc-ginput-row .mc-attach-btn:hover {
  color: var(--mc-input-text);
}

/* input bar locked while history is open */
.mc-gcol[data-history-open] .mc-ginput-row {
  opacity: 0.45;
  pointer-events: none;
}

/* ── ACTION ICONS INSIDE INPUT BAR ───────────────────── */
.mc-g-actions {
  display: none;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
:host([data-open][data-variant="floatpanel"]) .mc-g-actions { display: flex; }

.mc-g-icon-btn {
  width: 34px; height: 34px;
  border-radius: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--mc-input-placeholder);   /* same tint as attach icon, updates with primary */
  display: flex; align-items: center; justify-content: center;
  transition: background 150ms, color 150ms;
  flex-shrink: 0;
}
.mc-g-icon-btn:hover  { background: var(--mc-border); color: var(--mc-grad-start); }
.mc-g-icon-btn:active { background: var(--mc-border-strong); }
.mc-g-icon-btn:focus-visible { outline: 2px solid var(--mc-grad-start); outline-offset: 2px; }

/* ── CLOSE BUTTON (top-right of viewport when open) ───── */
.mc-gclose {
  position: fixed;
  top: 14px;
  right: 16px;
  z-index: calc(var(--mc-z) + 2);
  width: 34px; height: 34px;
  border-radius: 50%;
  background: rgba(0,0,0,0.07);
  border: 1px solid rgba(0,0,0,0.09);
  cursor: pointer;
  color: var(--mc-bot-bubble-text);
  display: none;
  align-items: center; justify-content: center;
  transition: background 150ms;
  pointer-events: auto;
}
:host([data-open][data-variant="floatpanel"]) .mc-gclose { display: flex; }
.mc-gclose:hover  { background: rgba(0,0,0,0.14); }
.mc-gclose:active { background: rgba(0,0,0,0.22); }
.mc-gclose:focus-visible { outline: 2px solid var(--mc-grad-start); outline-offset: 2px; }

/* ── FOOTER ───────────────────────────────────────────── */
.mc-gfooter {
  text-align: center;
  padding: 0 12px 6px;
  font-size: 10.5px;
  color: var(--mc-footer-text);
  letter-spacing: 0.01em;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 200ms;
}
.mc-gfooter[hidden] { display: none; }
:host([data-open][data-variant="floatpanel"]) .mc-gfooter { opacity: 1; }
.mc-gfooter a { color: var(--mc-footer-link); font-weight: 600; text-decoration: none; }
.mc-gfooter a:hover { text-decoration: underline; }

/* ── HISTORY PANEL (Floatpanel variant) ──────────────────── */
/* ── Floatpanel history: auto height, anchored above input bar ── */
.mc-gcol .mc-history-panel {
  /* reset popup positioning */
  position: static;
  transform: none;
  inset: auto;
  /* push panel to the bottom of the column (just above input bar) */
  margin-top: auto;
  flex-shrink: 0;
  /* auto height, capped at 50% viewport — content drives the size */
  height: auto;
  max-height: 50vh;
  max-height: 50dvh;
  display: flex;
  flex-direction: column;
  background: var(--mc-surface);
  border-radius: 16px 16px 0 0;
  overflow: hidden;
  pointer-events: auto;
}
.mc-gcol .mc-history-panel[hidden] { display: none; }
.mc-gcol .mc-history-panel.open    { transform: none; }

/* history list: scrollable, hidden scrollbar */
.mc-gcol .mc-history-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 12px 6px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 6px;
  scrollbar-width: none;
}
.mc-gcol .mc-history-list::-webkit-scrollbar { display: none; }

/* mobile / tablet: allow up to 75% height */
@media (max-width: 768px) {
  .mc-gcol .mc-history-panel {
    max-height: 75vh;
    max-height: 75dvh;
  }
}

/* ── entry card ── */
.mc-gcol .mc-history-entry {
  background: var(--mc-surface-2);
  border: 1px solid var(--mc-border);
  border-radius: 12px;
  padding: 11px 14px;
  cursor: pointer;
  flex-shrink: 0;
  pointer-events: auto;
  opacity: 0;
  transform: translateY(14px);
  transition: border-color 160ms, background 160ms,
              opacity 280ms ease, transform 280ms ease;
}
.mc-gcol .mc-history-entry.mc-gh-visible {
  opacity: 1;
  transform: translateY(0);
}
.mc-gcol .mc-history-entry:hover {
  border-color: var(--mc-grad-start);
  background: var(--mc-input-bg);
}

/* ── back button row at bottom of history panel ── */
.mc-gcol .mc-g-history-back {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 0 12px;
  background: var(--mc-surface);
}
.mc-gcol .mc-g-history-back button {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1.5px solid var(--mc-border-strong);
  border-radius: 999px;
  padding: 7px 22px;
  font-size: 13px;
  font-weight: 500;
  color: var(--mc-input-text);
  cursor: pointer;
  transition: background 150ms, border-color 150ms, color 150ms;
}
.mc-gcol .mc-g-history-back button:hover {
  background: var(--mc-border);
  border-color: var(--mc-grad-start);
  color: var(--mc-grad-start);
}

/* hide the gradient header — not used in Floatpanel variant */
.mc-gcol .mc-history-head { display: none; }
`;

// ─────────────────────────────────────────────────────────
// SECTION 10: HTML TEMPLATE
// ─────────────────────────────────────────────────────────

function _esc(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function buildTemplate(cfg) {
  const botAv = cfg.botAvatar
    ? `<img src="${_esc(cfg.botAvatar)}" alt="${_esc(cfg.botName)}" loading="lazy">`
    : `<span>${_esc(cfg.botInitials)}</span>`;

  const footerHtml = MC.BRAND.includes('MageComp')
    ? MC.BRAND.replace('MageComp', `<a href="${_esc(MC.BRAND_URL)}" target="_blank" rel="noopener noreferrer">MageComp</a>`)
    : `${_esc(MC.BRAND)} <a href="${_esc(MC.BRAND_URL)}" target="_blank" rel="noopener noreferrer">MageComp</a>`;

  return `
<button class="mc-launcher" aria-label="Open ${_esc(cfg.botName)}" part="launcher">
  <span class="mc-icon-chat">${ICONS.chat}</span>
  <span class="mc-icon-close">${ICONS.close}</span>
  <span class="mc-badge" ${!cfg.showNotificationBadge ? 'hidden' : ''} aria-hidden="true"></span>
</button>

<div class="mc-panel" role="dialog" aria-label="${_esc(cfg.botName)}" aria-modal="true">

  <header class="mc-header" part="header">
    <div class="mc-avatar-ring">
      <div class="mc-avatar-inner">${botAv}</div>
    </div>
    <div class="mc-header-info">
      <div class="mc-header-name">${_esc(cfg.botName)}</div>
      ${cfg.showHeaderSubtitle ? `<div class="mc-header-status"><span class="mc-status-dot"></span><span>${_esc(cfg.botStatusText)}</span></div>` : ''}
    </div>
    <div class="mc-header-actions">
      <button class="mc-hbtn mc-btn-newchat" title="New conversation" aria-label="New conversation">${ICONS.newchat}</button>
      <button class="mc-hbtn mc-btn-history" title="Chat history"     aria-label="Chat history">${ICONS.history}</button>
      <button class="mc-hbtn mc-btn-close"   title="Close"            aria-label="Close">${ICONS.close}</button>
    </div>
  </header>

  <div class="mc-messages" role="log" aria-live="polite" aria-label="Chat messages" part="messages"></div>

  <div class="mc-typing" aria-hidden="true" hidden>
    <div class="mc-av-sm">${botAv}</div>
    <div class="mc-dots">
      <div class="mc-dot"></div>
      <div class="mc-dot"></div>
      <div class="mc-dot"></div>
    </div>
  </div>

  <div class="mc-chips" hidden aria-label="Suggested questions" part="chips"></div>

  <div class="mc-input-area" part="input-area">
    <div class="mc-input-row">
      <button class="mc-attach-btn" title="Attach file" aria-label="Attach file" ${!cfg.allowAttachments ? 'hidden' : ''}>${ICONS.attach}</button>
      <textarea class="mc-input" placeholder="${_esc(cfg.placeholder)}" rows="1" aria-label="Type a message" maxlength="4000"></textarea>
      <button class="mc-send-btn" aria-label="Send message" disabled>${ICONS.send}</button>
    </div>
  </div>

  <div class="mc-review-prompt" hidden aria-label="Rate this conversation">
    <p class="mc-review-label">How was your experience?</p>
    <div class="mc-review-emojis">
      <button class="mc-review-btn" data-rating="1" data-label="Very Bad"  title="Very Bad">😡</button>
      <button class="mc-review-btn" data-rating="2" data-label="Bad"       title="Bad">😞</button>
      <button class="mc-review-btn" data-rating="3" data-label="Normal"    title="Normal">😐</button>
      <button class="mc-review-btn" data-rating="4" data-label="Good"      title="Good">😊</button>
      <button class="mc-review-btn" data-rating="5" data-label="Very Good" title="Very Good">😍</button>
    </div>
    <div class="mc-review-comment-wrap">
      <textarea class="mc-review-textarea" rows="2" placeholder="Add a comment (optional)" maxlength="500" aria-label="Review comment"></textarea>
      <button class="mc-review-submit" aria-label="Submit review">Submit</button>
    </div>
  </div>

  <footer class="mc-footer" ${!cfg.showBranding ? 'hidden' : ''} aria-label="Branding">
    ${footerHtml}
  </footer>

  <div class="mc-history-panel" hidden>
    <div class="mc-history-head">
      <span>Recent Conversations</span>
      <button class="mc-history-close" aria-label="Close history">${ICONS.close}</button>
    </div>
    <div class="mc-history-list"></div>
  </div>

</div>`;
}

function buildFloatpanelTemplate(cfg) {
  const botAv = cfg.botAvatar
    ? `<img src="${_esc(cfg.botAvatar)}" alt="${_esc(cfg.botName)}" loading="lazy">`
    : `<span>${_esc(cfg.botInitials)}</span>`;

  const footerHtml = MC.BRAND.includes('MageComp')
    ? MC.BRAND.replace('MageComp', `<a href="${_esc(MC.BRAND_URL)}" target="_blank" rel="noopener noreferrer">MageComp</a>`)
    : `${_esc(MC.BRAND)} <a href="${_esc(MC.BRAND_URL)}" target="_blank" rel="noopener noreferrer">MageComp</a>`;

  return `
<!-- full-width white backdrop (position:fixed, z-index:-1 relative to host) -->
<div class="mc-gpanel-backdrop" aria-hidden="true"></div>

<!-- close button lives outside the centred column so it sits at top-right of viewport -->
<button class="mc-gclose mc-btn-close" title="Close" aria-label="Close">${ICONS.close}</button>

<!-- centred column — all interactive content lives here -->
<div class="mc-gcol">

  <!-- messages (hidden when history is open) -->
  <div class="mc-gpanel-messages mc-messages" role="log" aria-live="polite" aria-label="Chat messages" part="messages">
    <div class="mc-gmsg-spacer" aria-hidden="true"></div>
  </div>

  <!-- history panel: sits in the same flex slot as messages, right above input bar -->
  <div class="mc-history-panel" hidden aria-label="Recent conversations">
    <div class="mc-history-head" aria-hidden="true"></div>
    <div class="mc-history-list" role="list"></div>
    <div class="mc-g-history-back">
      <button class="mc-history-close" aria-label="Back to chat">
        ${ICONS.back} Back
      </button>
    </div>
  </div>

  <!-- typing indicator -->
  <div class="mc-gtyping mc-typing" aria-hidden="true" hidden>
    <div class="mc-av-sm">${botAv}</div>
    <div class="mc-dots">
      <div class="mc-dot"></div>
      <div class="mc-dot"></div>
      <div class="mc-dot"></div>
    </div>
  </div>

  <!-- suggested questions chips -->
  <div class="mc-gchips mc-chips" hidden aria-label="Suggested questions" part="chips"></div>

  <!-- review prompt -->
  <div class="mc-greview mc-review-prompt" hidden aria-label="Rate this conversation">
    <p class="mc-review-label">How was your experience?</p>
    <div class="mc-review-emojis">
      <button class="mc-review-btn" data-rating="1" data-label="Very Bad"  title="Very Bad">😡</button>
      <button class="mc-review-btn" data-rating="2" data-label="Bad"       title="Bad">😞</button>
      <button class="mc-review-btn" data-rating="3" data-label="Normal"    title="Normal">😐</button>
      <button class="mc-review-btn" data-rating="4" data-label="Good"      title="Good">😊</button>
      <button class="mc-review-btn" data-rating="5" data-label="Very Good" title="Very Good">😍</button>
    </div>
    <div class="mc-review-comment-wrap" hidden>
      <textarea class="mc-review-textarea" rows="2" placeholder="Add a comment (optional)" maxlength="500" aria-label="Review comment"></textarea>
      <button class="mc-review-submit" aria-label="Submit review">Submit</button>
    </div>
  </div>

  <!-- input bar (always visible; animated gradient border at rest) -->
  <div class="mc-ginput-wrap" part="input-area">
    <div class="mc-ginput-row">
      <button class="mc-attach-btn" title="Attach file" aria-label="Attach file" ${!cfg.allowAttachments ? 'hidden' : ''}>${ICONS.attach}</button>
      <textarea class="mc-input" placeholder="${_esc(cfg.floatpanelPlaceholder || cfg.placeholder)}" rows="1" aria-label="Type a message" maxlength="4000"></textarea>
      <!-- history + new-chat icons — only shown when panel is open -->
      <div class="mc-g-actions" aria-label="Chat actions">
        <button class="mc-g-icon-btn mc-btn-history"  title="Chat history"      aria-label="Chat history">${ICONS.history}</button>
        <button class="mc-g-icon-btn mc-btn-newchat"  title="New conversation"  aria-label="New conversation">${ICONS.newchat}</button>
      </div>
      <button class="mc-send-btn" aria-label="Send message" disabled>${ICONS.send}</button>
    </div>
  </div>

  <footer class="mc-gfooter" ${!cfg.showBranding ? 'hidden' : ''} aria-label="Branding">
    ${footerHtml}
  </footer>

</div>`;
}

// ─────────────────────────────────────────────────────────
// SECTION 11: MAGECOMP CHAT ELEMENT
// ─────────────────────────────────────────────────────────

class MagecompChatElement extends HTMLElement {
  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'closed' });
    this._state  = { open: false, loading: false, messages: [], unread: 0 };
    this._booted = false;
  }

  connectedCallback()    { this._boot(); }
  disconnectedCallback() { this._destroy(); }

  static get observedAttributes() { return ['data-theme']; }

  attributeChangedCallback(name, _, val) {
    if (!this._booted || name !== 'data-theme') return;
    this._cfg = Object.freeze({ ...this._cfg, theme: val });
    this._colorEngine = new ColorEngine(this._cfg);
    this._colorEngine.applyTo(this);
  }

  async _boot() {
    const isFloatpanel = this._cfg.variant === 'floatpanel';
    const styles   = isFloatpanel ? `${MC_STYLES}${FLOATPANEL_STYLES}` : MC_STYLES;
    const template = isFloatpanel ? buildFloatpanelTemplate(this._cfg) : buildTemplate(this._cfg);
    this._shadow.innerHTML = `<style>${styles}</style>${template}`;

    this._r = {
      // Floatpanel: launcher = the input wrap (click anywhere on it opens chat)
      launcher:     this._shadow.querySelector(isFloatpanel ? '.mc-ginput-wrap' : '.mc-launcher'),
      panel:        this._shadow.querySelector(isFloatpanel ? '.mc-gcol' : '.mc-panel'),
      messages:     this._shadow.querySelector('.mc-messages'),
      input:        this._shadow.querySelector('.mc-input'),
      send:         this._shadow.querySelector('.mc-send-btn'),
      close:        this._shadow.querySelector('.mc-btn-close'),
      newchat:      this._shadow.querySelector('.mc-btn-newchat'),
      historyBtn:   this._shadow.querySelector('.mc-btn-history'),
      historyPanel: this._shadow.querySelector('.mc-history-panel'),
      historyClose: this._shadow.querySelector('.mc-history-close'),
      historyList:  this._shadow.querySelector('.mc-history-list'),
      reviewPrompt:    this._shadow.querySelector('.mc-review-prompt'),
      reviewComment:   this._shadow.querySelector('.mc-review-comment-wrap'),
      reviewTextarea:  this._shadow.querySelector('.mc-review-textarea'),
      reviewSubmit:    this._shadow.querySelector('.mc-review-submit'),
      typing:       this._shadow.querySelector('.mc-typing'),
      chips:        this._shadow.querySelector('.mc-chips'),
      badge:        this._shadow.querySelector('.mc-badge'),
      attach:       this._shadow.querySelector('.mc-attach-btn'),
    };

    this._colorEngine.applyTo(this);
    if (isFloatpanel) this.setAttribute('data-variant', 'floatpanel');
    this.setAttribute('data-position', this._cfg.position);
    if (this._cfg.rtl) this.setAttribute('dir', 'rtl');

    this._bindEvents();

    if (this._cfg.persistHistory) await this._loadHistory();

    if (this._state.messages.length === 0) {
      this._addBot(this._cfg.welcomeMessage, false);
      if (this._cfg.welcomeMessage2) this._addBot(this._cfg.welcomeMessage2, false);
    }

    this._renderChips();

    const prefs = this._session.getPrefs();
    if (prefs.minimized) this.toggleAttribute('data-minimized', true);

    if (this._cfg.autoOpen) setTimeout(() => this.open(), this._cfg.openDelay || 0);

    if (this._cfg.subScript) await this._plugins.load(this._cfg.subScript, this.publicAPI);

    this._booted = true;
    this._bus.emit('load', { sessionId: this._session.getOrCreate().sessionId, version: MC.VERSION });
  }

  // ── EVENT BINDING ─────────────────────────────────────

  _bindEvents() {
    const r = this._r;
    if (this._cfg.variant === 'floatpanel') {
      // Click on the input wrap opens the chat only when not yet open;
      // once open the wrap is the live input area — don't toggle on it.
      r.launcher.addEventListener('click', () => { if (!this._state.open) this.open(); });
      // Focus on the textarea also opens
      r.input.addEventListener('focus', () => { if (!this._state.open) this.open(); });
    } else {
      r.launcher.addEventListener('click', () => this.toggle());
    }
    r.close.addEventListener('click',       () => this.close());
    r.newchat?.addEventListener('click',    () => this._startNewChat());
    r.historyBtn?.addEventListener('click', () => this._openHistoryPanel());
    r.historyClose?.addEventListener('click',()=> this._closeHistoryPanel());
    r.send.addEventListener('click',        () => this._send());

    // Review prompt — step 1: pick emoji, step 2: optional comment + submit
    let _pendingRating = null, _pendingLabel = null;
    r.reviewPrompt?.querySelectorAll('.mc-review-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        r.reviewPrompt.querySelectorAll('.mc-review-btn').forEach(b => b.classList.remove('mc-selected'));
        btn.classList.add('mc-selected');
        _pendingRating = parseInt(btn.dataset.rating, 10);
        _pendingLabel  = btn.dataset.label;
        if (r.reviewComment) r.reviewComment.hidden = false;
        r.reviewTextarea?.focus();
        this._scrollToBottom();
      });
    });
    r.reviewSubmit?.addEventListener('click', () => {
      if (_pendingRating === null) return;
      const comment = r.reviewTextarea?.value.trim() || null;
      this._submitReview(_pendingRating, _pendingLabel, comment);
    });

    r.input.addEventListener('input', () => {
      this._resizeInput();
      r.send.disabled = !r.input.value.trim();
    });

    r.input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!r.send.disabled && !this._state.loading) this._send();
      }
    });

    r.attach?.addEventListener('click', () =>
      this._bus.emit('action', { action: 'attach', sessionId: this._session.getOrCreate().sessionId })
    );

    this._onKeydown = e => {
      if (e.key !== 'Escape' || !this._state.open) return;
      // Escape closes history first; second Escape closes the chat
      if (this._r?.historyPanel && !this._r.historyPanel.hidden) {
        this._closeHistoryPanel();
      } else {
        this.close();
      }
    };
    document.addEventListener('keydown', this._onKeydown);

    // End session reliably on page exit.
    // visibilitychange→hidden is the most reliable signal (tab close, switch, browser close).
    // pagehide is a secondary fallback. beforeunload is intentionally omitted — it fires
    // before navigation is committed and browsers throttle network in that handler.
    // The _sessionEndedBeacon guard prevents the beacon firing twice.
    this._sessionEndedBeacon = false;
    this._onPageHide = () => {
      if (this._sessionEndedBeacon) return;
      this._sessionEndedBeacon = true;
      this._analytics?.endSession(location.href, true);
    };
    this._onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') this._onPageHide();
    };
    document.addEventListener('visibilitychange', this._onVisibilityChange);
    window.addEventListener('pagehide', this._onPageHide);

    if (this._cfg.theme === 'auto') {
      this._mq = window.matchMedia('(prefers-color-scheme: dark)');
      this._mqHandler = () => {
        const theme = this._mq.matches ? 'dark' : 'light';
        this._colorEngine = new ColorEngine({ ...this._cfg, theme });
        this._colorEngine.applyTo(this);
      };
      this._mq.addEventListener('change', this._mqHandler);
    }

    this._ro = new ResizeObserver(() => {
      const mobile = window.innerWidth < this._cfg.mobileBreakpoint;
      this.toggleAttribute('data-mobile', mobile && this._cfg.mobileFullscreen);
      this._bus.emit('resize', { mobile, width: window.innerWidth });
    });
    this._ro.observe(document.documentElement);
    // Run once immediately
    this.toggleAttribute('data-mobile', window.innerWidth < this._cfg.mobileBreakpoint && this._cfg.mobileFullscreen);

    this._mo = new MutationObserver(() => this._scrollToBottom());
    this._mo.observe(this._r.messages, { childList: true, subtree: true });

    // Activity observer — starts after first user message is sent
    const idleSec = parseInt(this._cfg.inactivityReviewSeconds || 30, 10);
    this._activityObserver = new ActivityObserver(() => this._showReviewPrompt(), idleSec);
  }

  // ── PUBLIC API ─────────────────────────────────────────

  open() {
    if (this._state.open) return;
    this._state.open = true;
    this.toggleAttribute('data-open', true);
    if (this._r.badge) this._r.badge.hidden = true;
    this._state.unread = 0;
    setTimeout(() => this._r.input?.focus(), 50);
    this._bus.emit('open', { sessionId: this._session.getOrCreate().sessionId });
  }

  close() {
    if (!this._state.open) return;
    // close history panel if open
    if (this._r?.historyPanel && !this._r.historyPanel.hidden) {
      this._closeHistoryPanel();
    }
    // hide review prompt if visible
    if (this._r?.reviewPrompt && !this._r.reviewPrompt.hidden) {
      this._r.reviewPrompt.hidden = true;
    }
    this._state.open = false;
    this.removeAttribute('data-open');
    this._bus.emit('close', { sessionId: this._session.getOrCreate().sessionId });
  }

  toggle() { this._state.open ? this.close() : this.open(); }

  async sendMessage(text) {
    if (!text?.trim()) return;
    this._r.input.value = text;
    this._r.send.disabled = false;
    await this._send();
  }

  addSystemMessage(text) {
    const el = document.createElement('div');
    el.className   = 'mc-system';
    el.textContent = text;
    this._r.messages.appendChild(el);
    this._scrollToBottom();
  }

  setSuggestions(questions = []) {
    this._cfg = Object.freeze({ ...this._cfg, suggestedQuestions: questions });
    this._renderChips();
  }

  on(ev, fn) { return this._bus.on(ev, fn); }

  get session() { return { ...this._session.getOrCreate() }; }
  get config()  { return { ...this._cfg }; }

  get publicAPI() {
    return {
      open:             this.open.bind(this),
      close:            this.close.bind(this),
      toggle:           this.toggle.bind(this),
      sendMessage:      this.sendMessage.bind(this),
      addSystemMessage: this.addSystemMessage.bind(this),
      setSuggestions:   this.setSuggestions.bind(this),
      on:               this.on.bind(this),
      setColor:         (prop, val) => this._colorEngine.setColor(prop, val, this),
      endSession:       (exitUrl)   => this._analytics?.endSession(exitUrl),
      session:          this.session,
      config:           this.config,
      analytics:        { deviceType: this._analytics?.deviceType, browser: this._analytics?.browser },
      version:          MC.VERSION,
    };
  }

  // ── SEND FLOW ──────────────────────────────────────────

  async _send() {
    const text = this._r.input.value.trim();
    if (!text || this._state.loading) return;

    this._r.input.value        = '';
    this._r.input.style.height = '';
    this._r.send.disabled      = true;
    this._state.loading        = true;

    const userMsgId = this._addUser(text);
    this._bus.emit('send', { message: text, sessionId: this._session.getOrCreate().sessionId });
    this._setTyping(true);

    // Start inactivity observer on the first message sent this session
    if (!this._activityObserverStarted) {
      this._activityObserverStarted = true;
      this._activityObserver?.start();
    }

    if (this._cfg.stream) {
      let botId = null, fullText = '', started = false;

      await this._api.send(text, {
        onChunk: (chunk, full) => {
          fullText = full;
          if (!started) {
            this._setTyping(false);
            botId   = this._addBot('', true, true);
            started = true;
          }
          this._updateBubble(botId, full);
          this._scrollToBottom();
        },
        onDone: (meta) => {
          this._state.loading = false;
          this._setTyping(false);
          if (meta?.user_timestamp) this._updateMsgTimestamp(userMsgId, meta.user_timestamp);
          if (botId) {
            const m = this._state.messages.find(x => x.id === botId);
            if (m) {
              m.text = fullText;
              m.streaming = false;
              if (meta?.timestamp) { m.timestamp = new Date(meta.timestamp).getTime(); this._updateMsgTimestamp(botId, meta.timestamp); }
            }
            this._session.updateLastMessage(botId, fullText);
          }
          this._bus.emit('receive', {
            message:   fullText,
            sessionId: this._session.getOrCreate().sessionId,
            tokens:    meta?.tokens,
          });
        },
        onError: (err) => {
          this._state.loading = false;
          this._setTyping(false);
          this._toast(
            err.status === 429 ? 'Too many requests. Please wait.' :
            err.status === 503 ? 'Service temporarily unavailable.' :
            this._cfg.errorMessage
          );
        },
      });
    } else {
      await this._api.send(text, {
        onDone: (data) => {
          this._state.loading = false;
          this._setTyping(false);
          if (data.user_timestamp) this._updateMsgTimestamp(userMsgId, data.user_timestamp);
          this._addBot(data.reply || '', true, false, data.timestamp);
          this._bus.emit('receive', {
            message:   data.reply,
            sessionId: this._session.getOrCreate().sessionId,
            tokens:    data.tokens,
          });
        },
        onError: (err) => {
          this._state.loading = false;
          this._setTyping(false);
          this._toast(
            err.status === 429 ? 'Too many requests. Please wait.' :
            this._cfg.errorMessage
          );
        },
      });
    }
  }

  // ── MESSAGE RENDERING ──────────────────────────────────

  _addBot(text, animate = true, isStreaming = false, serverTimestamp = null) {
    const ts  = serverTimestamp ? new Date(serverTimestamp).getTime() : Date.now();
    const msg = { id: this._uid(), role: 'bot', text, timestamp: ts, streaming: isStreaming };
    this._state.messages.push(msg);
    this._renderRow(msg, animate);
    if (!isStreaming) this._session.appendHistory(msg);
    if (!this._state.open) { this._state.unread++; if (this._r.badge) this._r.badge.hidden = false; }
    return msg.id;
  }

  _addUser(text, serverTimestamp = null) {
    const ts  = serverTimestamp ? new Date(serverTimestamp).getTime() : Date.now();
    const msg = { id: this._uid(), role: 'user', text, timestamp: ts };
    this._state.messages.push(msg);
    this._renderRow(msg, true);
    this._session.appendHistory(msg);
    return msg.id;
  }

  _dateLabel(ts) {
    const d     = new Date(ts);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const sameDay = (a, b) =>
      a.getFullYear() === b.getFullYear() &&
      a.getMonth()    === b.getMonth()    &&
      a.getDate()     === b.getDate();
    if (sameDay(d, today))     return 'Today';
    if (sameDay(d, yesterday)) return 'Yesterday';
    return new Intl.DateTimeFormat(this._cfg.locale, { day: 'numeric', month: 'long', year: 'numeric' }).format(d);
  }

  _renderDateSeparator(ts) {
    const sep = document.createElement('div');
    sep.className = 'mc-date-sep';
    sep.innerHTML = `<span>${this._dateLabel(ts)}</span>`;
    this._r.messages.appendChild(sep);
  }

  _renderRow(msg, animate) {
    const isBot    = msg.role === 'bot';
    const prev     = this._state.messages.at(-2);
    const isGrouped = prev?.role === msg.role;
    const isFirst  = !isGrouped;

    // Date separator: show when day changes (or for the very first message)
    const prevDate = prev ? new Date(prev.timestamp).toDateString() : null;
    const thisDate = new Date(msg.timestamp).toDateString();
    if (!prevDate || prevDate !== thisDate) {
      this._renderDateSeparator(msg.timestamp);
    }

    const row = document.createElement('div');
    row.className = `mc-row${isBot ? '' : ' mc-row-user'}${isFirst ? ' mc-row-first' : ''}${animate ? '' : ' mc-no-anim'}`;
    row.dataset.id = msg.id;

    if (animate) {
      row.style.animationDuration = '200ms';
    } else {
      row.style.animation = 'none';
    }

    if (isBot && this._cfg.showAvatar) {
      const av = document.createElement('div');
      av.className = 'mc-av-sm' + (isGrouped && !this._cfg.showAvatarGrouped ? ' hidden' : '');
      if (this._cfg.botAvatar) {
        av.innerHTML = `<img src="${_esc(this._cfg.botAvatar)}" alt="${_esc(this._cfg.botName)}" loading="lazy">`;
      } else {
        av.textContent = this._cfg.botInitials;
      }
      row.appendChild(av);
    }

    const wrap = document.createElement('div');
    wrap.className = 'mc-bubble-wrap';

    const bubble = document.createElement('div');
    bubble.className = `mc-bubble${isBot ? '' : ' mc-bubble-user'}`;
    bubble.innerHTML = this._renderContent(msg.text);
    this._attachCopyBtns(bubble);
    wrap.appendChild(bubble);

    if (this._cfg.showTimestamps) {
      const ts = document.createElement('time');
      ts.className = 'mc-ts';
      ts.dateTime  = new Date(msg.timestamp).toISOString();
      ts.textContent = this._formatTime(msg.timestamp);
      wrap.appendChild(ts);
    }

    row.appendChild(wrap);
    this._r.messages.appendChild(row);
  }

  _updateBubble(id, text) {
    const row = this._r.messages.querySelector(`[data-id="${id}"]`);
    if (!row) return;
    const bubble = row.querySelector('.mc-bubble');
    if (bubble) {
      bubble.innerHTML = this._renderContent(text);
      this._attachCopyBtns(bubble);
    }
  }

  _attachCopyBtns(bubble) {
    bubble.querySelectorAll('pre').forEach(pre => {
      if (pre.querySelector('.mc-copy-btn')) return;
      const btn = document.createElement('button');
      btn.className   = 'mc-copy-btn';
      btn.innerHTML   = ICONS.copy;
      btn.title       = 'Copy';
      btn.setAttribute('aria-label', 'Copy code');
      btn.addEventListener('click', () => {
        const code = pre.querySelector('code')?.textContent || pre.textContent;
        navigator.clipboard?.writeText(code).then(() => {
          btn.innerHTML = ICONS.check;
          setTimeout(() => { btn.innerHTML = ICONS.copy; }, 2000);
        });
      });
      pre.appendChild(btn);
    });
  }

  _renderContent(text) {
    if (!text) return '';
    let s = String(text)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');

    // Code blocks
    s = s.replace(/```[\s\S]*?```/g, m => {
      const inner = m.slice(3,-3).replace(/^\w+\n/,'');
      return `<pre><code>${inner}</code></pre>`;
    });
    // Inline code
    s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
    // Bold
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    s = s.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
    // Links
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    // Blockquotes
    s = s.replace(/(^|\n)&gt; ?(.+)/g, '$1<blockquote>$2</blockquote>');
    // Lists
    s = s.replace(/((?:(?:^|\n)- .+)+)/g, block => {
      const items = block.trim().split('\n').map(l=>`<li>${l.replace(/^- /,'')}</li>`).join('');
      return `<ul>${items}</ul>`;
    });
    // Line breaks
    s = s.replace(/\n/g, '<br>');
    return s;
  }

  async _loadHistory() {
    const sessionId = this._session.getOrCreate().sessionId;

    // Try server-side cache first (4-hour TTL)
    let messages = this._session.getHistoryCache(sessionId);

    if (!messages) {
      try {
        const data = await this._api.fetchHistory(sessionId);
        messages = data.messages || [];
        this._session.setHistoryCache(sessionId, messages);
      } catch(e) {
        // Fall back to old localStorage message format
        messages = this._session.getHistory().map(m => ({
          role: m.role === 'bot' ? 'assistant' : m.role,
          content: m.text,
          timestamp: null,
        }));
      }
    }

    messages.forEach(m => {
      const role = m.role === 'assistant' ? 'bot' : m.role;
      if (role === 'bot')  this._addBot(m.content, false, false, m.timestamp);
      if (role === 'user') this._addUser(m.content, m.timestamp);
    });
    if (messages.length) this._scrollToBottom();
  }

  // ── UI HELPERS ─────────────────────────────────────────

  _renderChips() {
    const qs = this._cfg.suggestedQuestions;
    const el = this._r.chips;
    if (!el) return;
    el.innerHTML = '';
    if (!qs?.length) { el.hidden = true; return; }
    el.hidden = false;
    qs.forEach(q => {
      const chip = document.createElement('button');
      chip.className   = 'mc-chip';
      chip.textContent = q;
      chip.addEventListener('click', () => {
        this._bus.emit('action', { action:'suggestion', value:q, sessionId: this._session.getOrCreate().sessionId });
        chip.remove();
        if (!el.children.length) el.hidden = true;
        this.sendMessage(q);
      });
      el.appendChild(chip);
    });
  }

  _setTyping(show) {
    if (!this._cfg.showTypingIndicator) return;
    this._r.typing.hidden = !show;
    if (show) {
      this._bus.emit('typing', { sessionId: this._session.getOrCreate().sessionId });
      this._scrollToBottom();
    } else {
      this._bus.emit('typing:end', { sessionId: this._session.getOrCreate().sessionId });
    }
  }

  _toast(message) {
    const t = document.createElement('div');
    t.className   = 'mc-toast';
    t.textContent = message;
    this._r.panel.appendChild(t);
    this._bus.emit('error', { error: message, sessionId: this._session.getOrCreate().sessionId });
    setTimeout(() => t.remove(), 4500);
  }

  // Wipe the messages container and restore the Floatpanel spacer so the
  // bottom-anchoring height logic resets to its initial state.
  _resetMessages() {
    this._r.messages.innerHTML = '';
    if (this._cfg.variant === 'floatpanel') {
      const spacer = document.createElement('div');
      spacer.className = 'mc-gmsg-spacer';
      spacer.setAttribute('aria-hidden', 'true');
      this._r.messages.appendChild(spacer);
    }
  }

  _clear() {
    this._state.messages = [];
    this._resetMessages();
    this._session.clearHistory();
    this._addBot(this._cfg.welcomeMessage, false);
    if (this._cfg.welcomeMessage2) this._addBot(this._cfg.welcomeMessage2, false);
    this._renderChips();
    this._bus.emit('clear', { sessionId: this._session.getOrCreate().sessionId });
  }

  _toggleMinimize() {
    const val = !this.hasAttribute('data-minimized');
    this.toggleAttribute('data-minimized', val);
    this._session.setPrefs({ minimized: val });
    this._bus.emit(val ? 'minimize' : 'restore', { sessionId: this._session.getOrCreate().sessionId });
  }

  _scrollToBottom() {
    this._r.messages.scrollTop = this._r.messages.scrollHeight;
  }

  // ── Server timestamp update ────────────────────────────────────────────────
  _updateMsgTimestamp(id, isoTimestamp) {
    const msg = this._state.messages.find(m => m.id === id);
    if (msg) msg.timestamp = new Date(isoTimestamp).getTime();
    const row = this._r.messages.querySelector(`[data-id="${id}"]`);
    const ts  = row?.querySelector('.mc-ts');
    if (ts) ts.textContent = this._formatTime(new Date(isoTimestamp).getTime());
  }

  // ── History panel ──────────────────────────────────────────────────────────
  async _openHistoryPanel() {
    const r        = this._r;
    const isFloatpanel = this._cfg.variant === 'floatpanel';

    // Floatpanel: hide messages + disable chat input
    if (isFloatpanel) {
      r.messages.classList.add('mc-g-hidden');
      r.input.disabled     = true;
      r.send.disabled      = true;
      if (r.attach) r.attach.disabled = true;
      r.input.placeholder  = '';
      this._shadow.querySelector('.mc-gcol')?.setAttribute('data-history-open', '');
    }

    r.historyPanel.hidden = false;
    if (!isFloatpanel) requestAnimationFrame(() => r.historyPanel.classList.add('open'));
    r.historyList.innerHTML = `<p class="mc-history-empty">Loading…</p>`;

    try {
      const data = await this._api.fetchSessions();
      r.historyList.innerHTML = '';
      if (!data.sessions?.length) {
        r.historyList.innerHTML = `<p class="mc-history-empty">No previous conversations.</p>`;
        return;
      }

      // Floatpanel: oldest first (top) → newest last (bottom); popup: API order
      const sessions = isFloatpanel
        ? [...data.sessions].sort((a, b) => new Date(a.started_at) - new Date(b.started_at))
        : data.sessions;

      sessions.forEach((s, idx) => {
        const entry = document.createElement('div');
        entry.className = 'mc-history-entry';
        entry.setAttribute('role', 'listitem');
        const timeStr = new Intl.DateTimeFormat(this._cfg.locale, {
          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        }).format(new Date(s.started_at));
        entry.innerHTML = `
          <div class="mc-history-entry-time">${_esc(timeStr)}</div>
          <div class="mc-history-entry-preview">${_esc(s.preview || '(empty conversation)')}</div>
        `;
        entry.addEventListener('click', () => this._loadSession(s));
        r.historyList.appendChild(entry);

        // Floatpanel: stagger fade-in bottom-to-top
        // items are in DOM order top→bottom; animate in reverse so bottom appears first
        if (isFloatpanel) {
          const total      = data.sessions.length;
          const delayIndex = total - 1 - idx;          // bottom item = delay 0
          const delay      = delayIndex * 55;           // 55ms per step
          setTimeout(() => entry.classList.add('mc-gh-visible'), delay);
        }
      });

      // Floatpanel: scroll to bottom so newest entry is visible
      if (isFloatpanel) r.historyList.scrollTop = r.historyList.scrollHeight;

    } catch(e) {
      r.historyList.innerHTML = `<p class="mc-history-empty">Could not load history.</p>`;
    }
  }

  _closeHistoryPanel() {
    const r        = this._r;
    const isFloatpanel = this._cfg.variant === 'floatpanel';
    r.historyPanel.classList.remove('open');
    setTimeout(() => {
      r.historyPanel.hidden = true;
      // Floatpanel: restore messages + re-enable chat input
      if (isFloatpanel) {
        r.messages.classList.remove('mc-g-hidden');
        r.input.disabled    = false;
        if (r.attach) r.attach.disabled = false;
        r.input.placeholder = this._cfg.floatpanelPlaceholder || this._cfg.placeholder;
        this._shadow.querySelector('.mc-gcol')?.removeAttribute('data-history-open');
        // send button re-enables only if there is text
        r.send.disabled = r.input.value.trim().length === 0;
      }
    }, isFloatpanel ? 0 : 290);
  }

  _loadSession(sessionRecord) {
    this._closeHistoryPanel();
    this._state.messages = [];
    this._resetMessages();

    // Cache the loaded session messages and switch active session
    this._session.setHistoryCache(sessionRecord.session_id, sessionRecord.messages);
    this._session.setActiveSession(sessionRecord.session_id);
    this._api._sess = this._session.getOrCreate();

    sessionRecord.messages.forEach(m => {
      const role = m.role === 'assistant' ? 'bot' : m.role;
      if (role === 'bot')  this._addBot(m.content, false, false, m.timestamp);
      if (role === 'user') this._addUser(m.content, m.timestamp);
    });
    this._scrollToBottom();
    this._bus.emit('session:load', { sessionId: sessionRecord.session_id });
  }

  // ── New chat ───────────────────────────────────────────────────────────────
  async _startNewChat() {
    const oldSessionId = this._session.getOrCreate().sessionId;

    try {
      // Close current session
      await fetch(`${this._cfg.apiUrl}/chat/session/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: oldSessionId, app_id: this._cfg.appId, exit_url: location.href }),
      });
    } catch(e) { /* non-fatal */ }

    // Generate new session
    const newId = this._session._uid('s');
    this._session.clearHistory();
    this._session.clearHistoryCache(oldSessionId);
    this._session.setActiveSession(newId);
    const sessData = this._session.getOrCreate();
    this._api._sess = sessData;

    // Create new session on server (queued with retry)
    this._analytics?.track('/chat/session/create', {
      session_id:      newId,
      app_id:          this._cfg.appId,
      session_context: { entry_url: location.href, device_type: this._analytics?.deviceType, browser: this._analytics?.browser },
    }, 'newSession');

    // Reset UI
    this._state.messages = [];
    this._state.loading  = false;
    this._resetMessages();
    this._r.reviewPrompt.hidden = true;
    this._activityObserverStarted = false;
    this._activityObserver?.resetForNewSession();

    this._addBot(this._cfg.welcomeMessage, false);
    if (this._cfg.welcomeMessage2) this._addBot(this._cfg.welcomeMessage2, false);
    this._renderChips();
    this._bus.emit('session:new', { sessionId: newId });
  }

  // ── Review prompt ──────────────────────────────────────────────────────────
  _showReviewPrompt() {
    // Only show if at least one real message was exchanged
    if (this._state.messages.filter(m => m.role === 'user').length === 0) return;
    if (this._r.reviewPrompt) this._r.reviewPrompt.hidden = false;
    this._scrollToBottom();
  }

  async _submitReview(rating, label, comment) {
    const sessionId = this._session.getOrCreate().sessionId;
    const r = this._r;

    // Replace prompt contents with thank-you message, then hide after 5 s
    if (r.reviewPrompt) {
      r.reviewPrompt.innerHTML = `<p class="mc-review-thanks">Thanks for your feedback! ${label === 'Very Good' || label === 'Good' ? '😊' : '🙏'}</p>`;
      setTimeout(() => { r.reviewPrompt.hidden = true; }, 5000);
    }

    this._analytics?.track('/chat/session/review', {
      session_id: sessionId,
      app_id:     this._cfg.appId,
      rating,
      emoji_label: label,
      comment: comment || null,
    }, 'review');

    this._bus.emit('review', { sessionId, rating, label, comment });
  }

  _resizeInput() {
    const el = this._r.input;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, this._cfg.inputMaxRows * 22)}px`;
  }

  _formatTime(ts) {
    return new Intl.DateTimeFormat(this._cfg.locale, { hour:'2-digit', minute:'2-digit' }).format(new Date(ts));
  }

  _uid() { return `m_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,7)}`; }

  _destroy() {
    document.removeEventListener('keydown',        this._onKeydown);
    document.removeEventListener('visibilitychange', this._onVisibilityChange);
    window.removeEventListener('pagehide',          this._onPageHide);
    this._mq?.removeEventListener('change', this._mqHandler);
    this._ro?.disconnect();
    this._mo?.disconnect();
    this._api?.abort();
    this._activityObserver?.stop();
    // Only send end-session if the beacon hasn't already fired
    if (!this._sessionEndedBeacon) {
      this._analytics?.endSession(location.href);
    }
  }
}

// ─────────────────────────────────────────────────────────
// SECTION 12: SELF-INJECT & BOOT
// ─────────────────────────────────────────────────────────

/**
 * If an email is configured, resolve the canonical external_user_id for that
 * email+app_id pair from the backend (with a 4-hour localStorage cache).
 * On a match the session's userId is patched in-place so every subsequent
 * API call carries the correct identity and history panel loads correctly.
 * If the email changes the old cache key is automatically orphaned and a
 * fresh lookup is made for the new key.
 */
async function _resolveUserIdentity(cfg, session, sessionData) {
  const email = cfg.userEmail;
  if (!email) return;

  // Serve from cache if still fresh
  const cached = session.getUserLookup(email);
  if (cached !== null) {
    if (cached.external_user_id && cached.external_user_id !== sessionData.userId) {
      Object.assign(sessionData, session.patchUserId(cached.external_user_id));
    }
    return;
  }

  // Cache miss — ask the backend
  try {
    const res = await fetch(`${cfg.apiUrl}/chat/user/lookup`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ app_id: cfg.appId, email }),
    });
    if (!res.ok) return;
    const data = await res.json();
    // Cache regardless of found/not-found to avoid repeated calls for 4 hours
    session.setUserLookup(email, data.found ? data.external_user_id : null);
    if (data.found && data.external_user_id && data.external_user_id !== sessionData.userId) {
      Object.assign(sessionData, session.patchUserId(data.external_user_id));
    }
  } catch(e) {
    // Non-fatal — widget continues with the locally-generated userId
  }
}

(async function () {
  if (customElements.get(MC.TAG)) return;

  let cfg;
  try { cfg = parseConfig(); }
  catch (e) { console.error('[MC]', e); return; }

  if (!cfg.appId)  { console.error('[MC] data-app-id is required');  return; }
  if (!cfg.apiUrl) { console.error('[MC] data-api-url is required'); return; }

  const session     = new SessionManager(cfg);
  const sessionData = session.getOrCreate();

  // Resolve user identity from backend before the element boots so that
  // all API calls (history fetch, message send) carry the correct userId.
  await _resolveUserIdentity(cfg, session, sessionData);

  const bus         = new EventBus(cfg.appId);
  const aQueue      = new AnalyticsQueue();
  const analytics   = new AnalyticsClient(cfg, sessionData, aQueue);
  const api         = new ApiClient(cfg, sessionData, bus, analytics);
  const plugins     = new PluginLoader(bus);
  const colorEngine = new ColorEngine(cfg);

  Object.assign(MagecompChatElement.prototype, {
    _cfg:                    cfg,
    _session:                session,
    _bus:                    bus,
    _api:                    api,
    _analytics:              analytics,
    _plugins:                plugins,
    _colorEngine:            colorEngine,
    _activityObserverStarted: false,
  });

  customElements.define(MC.TAG, MagecompChatElement);

  const el = document.createElement(MC.TAG);
  el.setAttribute('data-app-id', cfg.appId);

  const inject = () => document.body.appendChild(el);
  if (document.body) { inject(); }
  else { document.addEventListener('DOMContentLoaded', inject, { once: true }); }

  window.MagecompChat = {
    open:             ()       => el.open(),
    close:            ()       => el.close(),
    toggle:           ()       => el.toggle(),
    sendMessage:      text     => el.sendMessage(text),
    addSystemMessage: text     => el.addSystemMessage(text),
    setSuggestions:   qs       => el.setSuggestions(qs),
    setColor:         (p,v)    => colorEngine.setColor(p, v, el),
    endSession:       exitUrl  => analytics.endSession(exitUrl),
    on:               (ev, fn) => el.on(ev, fn),
    session:          ()       => el.session,
    analytics:        { deviceType: analytics.deviceType, browser: analytics.browser },
    config:           cfg,
    version:          MC.VERSION,
  };

  console.info(`[MageComp Chat] v${MC.VERSION} | app:${cfg.appId} | session:${sessionData.sessionId}`);
})();
