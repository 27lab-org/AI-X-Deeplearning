/* 웹 배포용 어댑터: claude.ai 아티팩트 런타임(window.claude.use("db"|"user"|"downloads"))을
   review.27lab.org 백엔드(REST)로 흉내 낸다. 화면 코드(app.js)는 아티팩트판과 같다.
   - 로그인: 사람마다 다른 링크 https://<host>/#k=<토큰>. 토큰은 이 기기 localStorage 에 남고 주소창에서는 지운다.
   - 실시간: 4초마다 /api/changes?since=N 로 바뀐 문서만 받는다.
   - 데이터(검수 카드)는 토큰이 있어야 /api/data 로 받는다. 받은 뒤 app.js 를 붙인다. */
(function () {
  "use strict";
  var KEY = "tcr:key", POLL = 4000;
  var m = /(?:^|[#&])k=([A-Za-z0-9_-]{16,200})/.exec(location.hash || "");
  try { if (m) localStorage.setItem(KEY, m[1]); } catch (e) {}
  if (m) history.replaceState(null, "", location.pathname + location.search);
  var tok = m ? m[1] : null;
  try { tok = tok || localStorage.getItem(KEY); } catch (e) {}

  function stop(msg) {
    var a = document.getElementById("app");
    a.innerHTML = "";
    var d = document.createElement("div"); d.className = "banner warn"; d.style.marginTop = "40px";
    d.textContent = msg; a.append(d);
  }
  if (!tok) { stop("검수 링크로 들어와 주세요. 링크는 Daniel이 사람마다 따로 보내 드려요."); return; }

  function api(method, path, body) {
    return fetch(path, { method: method, headers: Object.assign({ "X-Review-Key": tok }, body ? { "Content-Type": "application/json" } : {}),
      body: body ? JSON.stringify(body) : undefined, cache: "no-store" }).then(function (r) {
      if (r.status === 401) { try { localStorage.removeItem(KEY); } catch (e) {} }
      if (!r.ok) { var e = new Error("http " + r.status); e.code = r.status === 401 || r.status === 403 ? "invalid_argument" : r.status === 413 ? "invalid_argument" : "unavailable"; e.status = r.status; throw e; }
      return r.json();
    });
  }

  /* ---------- 문서 저장소 ---------- */
  var store = {}, seq = 0, ready = false, subs = [], me = null;
  function coll(c) { return store[c] || (store[c] = new Map()); }
  function snapColl(c) {
    var docs = []; coll(c).forEach(function (v, id) { docs.push({ id: id, data: function () { return v; } }); });
    return { docs: docs, metadata: { fromCache: !ready } };
  }
  function snapDoc(c, id) {
    var v = coll(c).get(id);
    return { exists: v != null, id: id, data: function () { return v; }, metadata: { fromCache: !ready } };
  }
  function fire(changed) {
    subs.forEach(function (s) { if (!changed || changed[s.c]) s.fn(); });
  }
  function poll() {
    return api("GET", "/api/changes?since=" + seq).then(function (r) {
      if (r.full) store = {};
      var changed = {};
      r.docs.forEach(function (d) { changed[d[0]] = 1; if (d[2] == null) coll(d[0]).delete(d[1]); else coll(d[0]).set(d[1], d[2]); });
      seq = r.seq;
      var first = !ready; ready = true;
      if (first || r.full) fire(null); else if (r.docs.length) fire(changed);
      if (r.more) return poll();
    });
  }
  var fails = 0;
  function loop() {
    poll().then(function () { fails = 0; }, function (e) {
      fails++; subs.forEach(function (s) { if (s.err && fails === 3) s.err({ code: e.code || "unavailable" }); });
    }).then(function () { setTimeout(loop, document.hidden ? POLL * 4 : POLL); });
  }
  function split(path) { var p = path.split("/"); return { c: p.slice(0, -1).join("/"), id: p[p.length - 1] }; }

  var dbApi = {
    collection: function (c) {
      return {
        onSnapshot: function (fn, err) {
          var s = { c: c, fn: function () { fn(snapColl(c)); }, err: err }; subs.push(s); if (ready) s.fn();
          return function () { subs = subs.filter(function (x) { return x !== s; }); };
        },
        doc: function (id) { return docRef(c, id); },
      };
    },
    doc: function (path) {
      if (path === "data/answerkey/items/planted") return answerRef();
      var p = split(path); return docRef(p.c, p.id);
    },
  };
  function docRef(c, id) {
    var path = "/api/doc/" + encodeURIComponent(c) + "/" + encodeURIComponent(id);
    return {
      set: function (v) { return api("PUT", path, v).then(function () { coll(c).set(id, v); fire(o(c)); }); },
      delete: function () { return api("DELETE", path).then(function () { coll(c).delete(id); fire(o(c)); }); },
      onSnapshot: function (fn, err) {
        var s = { c: c, fn: function () { fn(snapDoc(c, id)); }, err: err }; subs.push(s); if (ready) s.fn();
        return function () { subs = subs.filter(function (x) { return x !== s; }); };
      },
    };
  }
  function o(k) { var x = {}; x[k] = 1; return x; }
  // 정답표: 관리자만. 1분마다 다시 읽는다.
  function answerRef() {
    return {
      onSnapshot: function (fn, err) {
        function get() {
          api("GET", "/api/answerkey").then(function (d) { fn({ exists: true, data: function () { return d; }, metadata: { fromCache: false } }); }, function (e) { if (err) err(e); });
        }
        get(); var t = setInterval(get, 60000);
        return function () { clearInterval(t); };
      },
    };
  }

  var userApi = {
    id: function () { return Promise.resolve(me.uid); },
    name: function () { return me.name; },
    isOwner: function () { return me.role === "admin"; },
    canEdit: function () { return me.role === "admin"; },
    can: function () { return Promise.resolve(true); },
  };
  var downloadsApi = {
    save: function (o) {
      var blob = new Blob([o.data], { type: "application/octet-stream" });
      var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = o.filename || "download.txt";
      document.body.append(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
      return Promise.resolve({ status: "saved" });
    },
  };
  window.claude = { use: function (k) { return Promise.resolve(k === "db" ? dbApi : k === "user" ? userApi : k === "downloads" ? downloadsApi : null); } };

  /* ---------- 시작: 나 → 데이터 → 화면 ---------- */
  api("GET", "/api/me").then(function (u) {
    me = u;
    // 검수자 링크면 자기 칸(A/B/C)으로 맞춘다 (서버도 자기 칸에만 쓰게 막음)
    try { if (u.role !== "admin" && /^[ABC]$/.test(u.name)) localStorage.setItem("tcr:slot", JSON.stringify(u.name)); } catch (e) {}
    return api("GET", "/api/data");
  }).then(function (d) {
    window.__RV_DATA = d;
    loop();
    var s = document.createElement("script"); s.src = "app.js?v=" + (document.documentElement.dataset.v || "1"); document.body.append(s);
  }).catch(function (e) {
    stop(e.status === 401 ? "링크가 맞지 않아요. 받은 검수 링크로 다시 들어와 주세요." : e.status === 503 ? "검수 데이터가 아직 올라가지 않았어요. Daniel에게 알려 주세요." : "서버에 연결하지 못했어요. 잠시 뒤 새로고침해 주세요.");
  });
})();
