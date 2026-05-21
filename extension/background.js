/**
 * AuraSafe — background.js (Service Worker)
 * Polls Python backend for state changes.
 * Syncs keyword lists from backend /keywords endpoint.
 * Relays block/unblock commands to active tabs.
 */

"use strict";

const BACKEND         = "http://127.0.0.1:5000";
const POLL_MS         = 1500;
const KEYWORD_SYNC_MS = 30000; // sync keywords every 30s

let lastBlockState  = false;
let backendOnline   = false;

// ── Backend polling ──────────────────────────────────────────────────────────

async function pollBackend() {
  try {
    const res = await fetch(`${BACKEND}/status`, {
      signal: AbortSignal.timeout(1000)
    });
    if (!res.ok) { handleOffline(); return; }

    const data = await res.json();
    backendOnline = true;

    const blocked = data.blocked === true;
    const locked  = data.locked  === true;

    if (blocked && !lastBlockState) {
      lastBlockState = true;
      broadcastToTabs({ type: "FULL_BLOCK", reason: data.last_event || "Blocked by backend" });
    } else if (!blocked && lastBlockState) {
      lastBlockState = false;
      broadcastToTabs({ type: "UNBLOCK" });
    }

    chrome.storage.local.set({
      aura_status: {
        online: true, blocked, locked,
        last_event: data.last_event,
        timestamp: Date.now()
      }
    });

  } catch (e) {
    handleOffline();
  }
}

function handleOffline() {
  if (backendOnline) {
    backendOnline = false;
    chrome.storage.local.set({
      aura_status: { online: false, blocked: false, locked: false, timestamp: Date.now() }
    });
  }
}

// ── Keyword sync from backend ────────────────────────────────────────────────

async function syncKeywords() {
  try {
    const res = await fetch(`${BACKEND}/keywords`, {
      signal: AbortSignal.timeout(2000)
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data.ok) {
      chrome.storage.local.set({
        aura_keywords: {
          english:  data.english  || [],
          tamil:    data.tamil    || [],
          tanglish: data.tanglish || [],
          synced_at: Date.now()
        }
      });
      // Notify all content scripts to reload keywords
      broadcastToTabs({ type: "KEYWORDS_UPDATED" });
    }
  } catch (e) {
    // Backend may not be running — silent fail
  }
}

// ── Tab communication ────────────────────────────────────────────────────────

function broadcastToTabs(message) {
  chrome.tabs.query({}, (tabs) => {
    for (const tab of tabs) {
      if (tab.id && tab.url && !tab.url.startsWith("chrome://")) {
        chrome.tabs.sendMessage(tab.id, message).catch(() => {});
      }
    }
  });
}

// ── Popup → background messages ──────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "GET_STATUS") {
    chrome.storage.local.get("aura_status", (data) => {
      sendResponse(data.aura_status || { online: false });
    });
    return true;
  }

  if (msg.type === "MANUAL_BLOCK") {
    fetch(`${BACKEND}/block`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "Manually triggered from extension", source: "popup" })
    }).then(() => sendResponse({ ok: true })).catch(() => sendResponse({ ok: false }));
    return true;
  }

  if (msg.type === "MANUAL_UNBLOCK") {
    fetch(`${BACKEND}/unblock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "popup" })
    }).then(() => sendResponse({ ok: true })).catch(() => sendResponse({ ok: false }));
    return true;
  }

  if (msg.type === "RESCAN_TAB") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { type: "RESCAN" }).catch(() => {});
      }
    });
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === "SYNC_KEYWORDS") {
    syncKeywords().then(() => sendResponse({ ok: true }));
    return true;
  }
});

// ── Alarms ───────────────────────────────────────────────────────────────────

chrome.alarms.create("aura_poll",    { periodInMinutes: 1 / 40 });  // ~1.5s
chrome.alarms.create("aura_kw_sync", { periodInMinutes: 0.5 });     // 30s

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "aura_poll")    pollBackend();
  if (alarm.name === "aura_kw_sync") syncKeywords();
});

// Startup
pollBackend();
syncKeywords();
