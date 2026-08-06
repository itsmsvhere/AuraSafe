const dot       = document.getElementById("status-dot");
const statusTxt = document.getElementById("status-text");
const valBe     = document.getElementById("val-backend");
const valBlocked= document.getElementById("val-blocked");
const valLocked = document.getElementById("val-locked");
const lastEvent = document.getElementById("last-event");

function refresh() {
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (s) => {
    if (!s || !s.online) {
      dot.className = "dot offline";
      statusTxt.textContent = "Backend offline";
      valBe.textContent = "Offline"; valBe.className = "stat-value red";
      valBlocked.textContent = "—";
      valLocked.textContent  = "—";
      return;
    }

    if (s.blocked) {
      dot.className = "dot blocked";
      statusTxt.textContent = "BLOCKED";
    } else {
      dot.className = "dot online";
      statusTxt.textContent = "Active — All Clear";
    }

    valBe.textContent = "Online"; valBe.className = "stat-value green";

    valBlocked.textContent = s.blocked ? "BLOCKED" : "Clear";
    valBlocked.className   = "stat-value " + (s.blocked ? "red" : "green");

    valLocked.textContent  = s.locked ? "LOCKED" : "Off";
    valLocked.className    = "stat-value " + (s.locked ? "red" : "");

    lastEvent.textContent = s.last_event || "none";
  });
}

refresh();
setInterval(refresh, 2000);

document.getElementById("btn-block").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "MANUAL_BLOCK" }, refresh);
});
document.getElementById("btn-unblock").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "MANUAL_UNBLOCK" }, refresh);
});
document.getElementById("btn-rescan").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "RESCAN_TAB" });
});
