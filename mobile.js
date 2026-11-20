/* Home-screen access and an account's local, unpublished recommendation draft. */
var MobileAccess = (function () {
  "use strict";
  var owner = null, lastSnapshot = "", installRequest = null, installedNow = false;
  var fields = ["f_t", "f_a", "f_lang", "f_th", "f_st", "f_r", "f_k", "f_w", "g_b", "g_m", "g_a"];
  function draftKey(id) { return "pb-recommend-draft:" + id; }
  function status(text) {
    var el = document.getElementById("draft-status");
    if (el && el.textContent !== text) el.textContent = text;
  }
  function selected(map) { return Object.keys(map).filter(function (key) { return map[key]; }); }
  function choices(values, allowed) {
    var map = Object.create(null);
    if (Array.isArray(values)) values.forEach(function (value) {
      if (allowed.indexOf(String(value)) >= 0) map[String(value)] = true;
    });
    return map;
  }
  function redrawChoices() {
    multi("fa", AG, FA, null, function (age) { return age + " 歲"; });
    multi("fs", STG, FS);
    multi("f_styles", STYLE_KEYS, FSTYLE);
    syncLifePickers();
  }
  function resetForm() {
    fields.forEach(function (id) { $(id).value = id === "f_lang" ? "中文" : ""; });
    $("f_tw").checked = false;
    $("f_ck").checked = false;
    PH = []; FA = {}; FS = {}; FT = {}; FSTYLE = {};
    pvH(); redrawChoices(); status(""); lastSnapshot = JSON.stringify(snapshot());
  }
  function snapshot() {
    var values = {};
    fields.forEach(function (id) { values[id] = $(id).value; });
    return {version: 1, values: values, taiwan: $("f_tw").checked,
      ages: selected(FA), stages: selected(FS), themes: selected(FT), styles: selected(FSTYLE)};
  }
  function hasContent(draft) {
    return fields.some(function (id) { return id !== "f_lang" && draft.values[id].trim(); }) ||
      draft.taiwan || draft.ages.length || draft.stages.length || draft.themes.length || draft.styles.length;
  }
  function saveDraft() {
    if (!owner || !me || owner !== me.id) return;
    var draft = snapshot(), serialized = JSON.stringify(draft);
    // Closing an unchanged older tab must not replace another tab's newer draft.
    if (serialized === lastSnapshot) return;
    try {
      if (hasContent(draft)) {
        localStorage.setItem(draftKey(owner), serialized);
        status("文字草稿已暫存，尚未公開。");
      } else {
        localStorage.removeItem(draftKey(owner));
        status("");
      }
      lastSnapshot = serialized;
    } catch (e) {
      status("目前無法自動暫存，請先複製想保留的文字，再關閉網頁。");
    }
  }
  function restoreDraft() {
    if (!me || owner === me.id) return;
    resetForm(); owner = me.id;
    try {
      var raw = localStorage.getItem(draftKey(owner));
      if (!raw || raw.length > 50000) return;
      var draft = JSON.parse(raw);
      if (!draft || draft.version !== 1 || !draft.values || typeof draft.values !== "object") return;
      fields.forEach(function (id) {
        var value = draft.values[id], input = $(id);
        if (typeof value !== "string") return;
        if (id === "f_lang") input.value = value === "英文" ? "英文" : "中文";
        else input.value = value.slice(0, input.maxLength > 0 ? input.maxLength : 5000);
      });
      $("f_tw").checked = draft.taiwan === true;
      FA = choices(draft.ages, AG.map(String));
      FS = choices(draft.stages, STG);
      FT = choices(draft.themes, Object.keys(LIFE));
      FSTYLE = choices(draft.styles, STYLE_KEYS);
      redrawChoices(); lastSnapshot = JSON.stringify(snapshot());
      if (hasContent(snapshot())) status("已帶回上次暫存的文字與選項；照片請重新選擇。");
    } catch (e) {
      status("目前無法讀取暫存草稿；你仍可填寫並送出心得。");
    }
  }
  function syncAccount() {
    if (owner && (!me || owner !== me.id)) { resetForm(); owner = null; }
  }
  function clearDraft() {
    if (!me || owner !== me.id) return;
    if ((hasContent(snapshot()) || PH.length) && !window.confirm("清除這份尚未送出的草稿？")) return;
    try { localStorage.removeItem(draftKey(owner)); }
    catch (e) { status("暫時無法清除已存的草稿，請稍後再試。"); return; }
    resetForm(); status("草稿已清除。"); $("f_t").focus();
  }
  function submitted() {
    if (owner) {
      try { localStorage.removeItem(draftKey(owner)); } catch (e) {}
    }
    owner = null; status("");
  }
  function standalone() {
    return installedNow || navigator.standalone === true || window.matchMedia("(display-mode: standalone)").matches;
  }
  function installState() {
    var added = standalone();
    document.querySelectorAll("[data-install-guide]").forEach(function (button) { button.hidden = added; });
    var card = document.getElementById("home-shortcut");
    if (card) card.hidden = added;
    var nativeButton = document.getElementById("install-native");
    if (nativeButton) nativeButton.hidden = added || !installRequest;
  }
  function openInstallGuide() {
    var ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || /Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1;
    var android = /Android/.test(navigator.userAgent);
    $("install-ios").hidden = android;
    $("install-android").hidden = ios;
    $("install-url").value = new URL("./", window.location.href).href;
    $("install-status").textContent = "";
    installState(); showDialog("ovinstall");
  }
  function copyUrl() {
    function fallback() {
      $("install-url").focus(); $("install-url").select();
      $("install-status").textContent = "請長按或選取上方網址，選擇複製。";
    }
    if (!navigator.clipboard || !navigator.clipboard.writeText) { fallback(); return; }
    navigator.clipboard.writeText($("install-url").value).then(function () {
      $("install-status").textContent = "網站網址已複製。";
    }, fallback);
  }
  function installNative() {
    var request = installRequest;
    if (!request) return;
    installRequest = null; installState();
    Promise.resolve().then(function () { return request.prompt(); }).then(function () {
      return request.userChoice;
    }).then(function (choice) {
      $("install-status").textContent = choice.outcome === "accepted" ? "已確認安裝，完成後可從主畫面圖示開啟。" : "你可以稍後再依上方步驟加入主畫面。";
    }).catch(function () {
      $("install-status").textContent = "請依上方瀏覽器選單的步驟加入主畫面。";
    });
  }
  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault(); installRequest = event; installState();
  });
  window.addEventListener("appinstalled", function () { installedNow = true; installRequest = null; installState(); });
  function init() {
    document.querySelectorAll("[data-install-guide]").forEach(function (button) { button.onclick = openInstallGuide; });
    $("install-copy").onclick = copyUrl; $("install-native").onclick = installNative;
    document.querySelector('[data-mobile="explore"]').onclick = showAllBooks;
    document.querySelector('[data-mobile="write"]').onclick = startRecommendation;
    document.querySelector('[data-mobile="shelf"]').onclick = function () { $("my-shelf").click(); };
    $("draft-clear").onclick = clearDraft;
    ["input", "change"].forEach(function (name) { $("ovf").addEventListener(name, saveDraft); });
    $("ovf").addEventListener("click", function (event) { if (event.target.closest(".chip")) saveDraft(); });
    window.addEventListener("pagehide", saveDraft);
    document.addEventListener("visibilitychange", function () { if (document.hidden) saveDraft(); });
    installState(); updateNav(S.tab);
  }
  function updateNav(tab) {
    document.querySelector('[data-mobile="explore"]').setAttribute("aria-pressed", tab === "all");
    document.querySelector('[data-mobile="shelf"]').setAttribute("aria-pressed", tab === "fav" || tab === "log");
  }
  function launchShortcut() {
    var url = new URL(window.location.href), action = url.searchParams.get("go");
    if (action !== "share" && action !== "shelf") return;
    url.searchParams.delete("go");
    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    if (action === "share") startRecommendation();
    else $("my-shelf").click();
  }
  return {init: init, restoreDraft: restoreDraft, syncAccount: syncAccount,
    submitted: submitted, launchShortcut: launchShortcut, updateNav: updateNav};
}());
