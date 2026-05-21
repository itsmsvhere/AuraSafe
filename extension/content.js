/**
 * AuraSafe — content.js
 * Real-time DOM scanner: text detection, image/video blur, MutationObserver.
 * FIX: Keywords now sync from backend via chrome.storage (single source of truth).
 */

"use strict";

const AURA_ATTR = "data-aura-safe";
const AURA_MASK = "data-aura-masked";
const BACKEND   = "http://127.0.0.1:5000";
const THROTTLE_MS = 300;

// ── Default keyword lists (fallback if backend offline) ──────────────────────
const DEFAULT_KEYWORDS = {
  english: [
    "porn","xxx","nude","naked","nsfw","adult content","sex","escort","onlyfans",
    "hate","kill","murder","rape","drug","cocaine","heroin",
    "gambling","bet now","casino","self harm","suicide","explicit","18+"
  ],
  tamil:    ["ஆபாசம்","வன்முறை","கொலை","போதை","சூதாட்டம்"],
  tanglish: ["punda","otha","koothi","sunni","sappi","thevidiya","loosu","thayoli","naaye","poda"]
};

// ── State ────────────────────────────────────────────────────────────────────
let isFullBlocked = false;
let scanThrottle  = null;
let allPatterns   = buildPatterns(DEFAULT_KEYWORDS);

// ── Pattern builder ──────────────────────────────────────────────────────────
function buildPatterns(keywords) {
  const list = [];
  for (const [lang, words] of Object.entries(keywords)) {
    for (const word of words) {
      const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = lang === "english"
        ? new RegExp(`\\b${escaped}\\b`, "i")
        : new RegExp(escaped, "i");
      list.push({ regex, word, lang });
    }
  }
  return list;
}

// ── Load keywords from storage (synced by background.js) ────────────────────
function loadKeywords() {
  chrome.storage.local.get("aura_keywords", (data) => {
    if (data.aura_keywords) {
      allPatterns = buildPatterns(data.aura_keywords);
    }
  });
}
loadKeywords(); // on init

// ── Text detection ───────────────────────────────────────────────────────────
function detectInText(text) {
  if (!text || text.length < 3) return null;
  const normalized = text.toLowerCase()
    .replace(/[01346789@$!]/g, c => ({"0":"o","1":"i","3":"e","4":"a","6":"g","7":"t","@":"a","$":"s","!":"i","9":"g"}[c] || c));
  for (const { regex, word, lang } of allPatterns) {
    if (regex.test(normalized)) return { word, lang };
  }
  return null;
}

// ── DOM helpers ──────────────────────────────────────────────────────────────
function maskMedia(el) {
  if (el.hasAttribute(AURA_MASK)) return;
  el.setAttribute(AURA_MASK, "1");
  el.classList.add("aura-blur");

  const wrapper = document.createElement("div");
  wrapper.className = "aura-media-wrapper";
  el.parentNode?.insertBefore(wrapper, el);
  wrapper.appendChild(el);

  const label = document.createElement("div");
  label.className = "aura-media-label";
  label.textContent = "🛡 Blocked by AuraSafe";
  wrapper.appendChild(label);
}

function maskTextNode(node, match) {
  if (!node.parentElement || node.parentElement.hasAttribute(AURA_ATTR)) return;
  const span = document.createElement("span");
  span.setAttribute(AURA_ATTR, match.word);
  span.className = "aura-text-block";
  span.textContent = node.textContent.replace(
    new RegExp(match.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"),
    "▓".repeat(match.word.length)
  );
  span.title = `AuraSafe: unsafe content hidden (${match.lang})`;
  node.parentElement.replaceChild(span, node);
}

function injectFullBlock(reason) {
  if (document.getElementById("aura-fullblock")) return;
  const div = document.createElement("div");
  div.id = "aura-fullblock";
  div.innerHTML = `
    <div class="aura-fb-inner">
      <div class="aura-fb-icon">🛡️</div>
      <div class="aura-fb-title">BLOCKED BY AURASAFE</div>
      <div class="aura-fb-reason">${reason.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}</div>
    </div>
  `;
  document.body.appendChild(div);
}

function removeFullBlock() {
  const el = document.getElementById("aura-fullblock");
  if (el) el.remove();
}

// ── DOM scanning ─────────────────────────────────────────────────────────────
function scanNode(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    const text = node.textContent;
    if (text && text.trim().length > 2) {
      const match = detectInText(text);
      if (match) { maskTextNode(node, match); notifyBackend(match.word, match.lang); }
    }
  } else if (node.nodeType === Node.ELEMENT_NODE) {
    const tag = node.tagName?.toLowerCase();
    if (["script","style","noscript","head"].includes(tag)) return;
    if (node.hasAttribute(AURA_ATTR) || node.hasAttribute(AURA_MASK)) return;

    if (["img","video","iframe"].includes(tag)) {
      const src = (node.src || node.href || node.data || "").toLowerCase();
      const alt = (node.alt || node.title || "").toLowerCase();
      const match = detectInText(src + " " + alt);
      if (match) { maskMedia(node); notifyBackend(match.word, match.lang); return; }
    }

    for (const child of Array.from(node.childNodes)) {
      try { scanNode(child); } catch (e) { /* degrade gracefully */ }
    }
  }
}

function scanPage() {
  if (isFullBlocked || !document.body) return;
  scanNode(document.body);
}

// ── Backend notification ─────────────────────────────────────────────────────
let lastNotified = "", lastNotifiedTime = 0;
function notifyBackend(keyword, lang) {
  const now = Date.now();
  if (keyword === lastNotified && now - lastNotifiedTime < 2000) return;
  lastNotified = keyword; lastNotifiedTime = now;

  const tooExplicit = ["porn","xxx","nude","naked","onlyfans","escort"].includes(keyword.toLowerCase());
  const endpoint = tooExplicit ? `${BACKEND}/block` : `${BACKEND}/warn`;

  fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      keyword, lang,
      reason:  `Keyword "${keyword}" detected on ${new URL(window.location.href).hostname}`,
      message: `⚠ AuraSafe: "${keyword}" detected`,
      source:  "extension"
    })
  }).catch(() => {});
}

// ── MutationObserver ─────────────────────────────────────────────────────────
const observer = new MutationObserver((mutations) => {
  if (isFullBlocked) return;
  if (scanThrottle) clearTimeout(scanThrottle);
  scanThrottle = setTimeout(() => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        try { scanNode(node); } catch (e) {}
      }
    }
  }, THROTTLE_MS);
});
observer.observe(document.documentElement, { childList: true, subtree: true });

// ── Message listener ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "FULL_BLOCK") {
    isFullBlocked = true;
    injectFullBlock(msg.reason || "Blocked by AuraSafe");
  } else if (msg.type === "UNBLOCK") {
    isFullBlocked = false;
    removeFullBlock();
  } else if (msg.type === "RESCAN") {
    scanPage();
  } else if (msg.type === "KEYWORDS_UPDATED") {
    loadKeywords(); // reload from storage then rescan
    setTimeout(scanPage, 200);
  }
});

// ── Init ─────────────────────────────────────────────────────────────────────
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", scanPage);
} else {
  scanPage();
}
