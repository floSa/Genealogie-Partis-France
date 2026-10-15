/* Frise des partis et mouvements politiques français (Ve République).
   Aucune dépendance : SVG généré à la main. Données : window.GRAPH (site/data.js). */
(() => {
  "use strict";
  const D = window.GRAPH;
  const orgs = D.orgs;
  const people = D.people;
  const O = new Map(orgs.map((o) => [o.id, o]));
  const P = new Map(people.map((p) => [p.id, p]));
  const NS = "http://www.w3.org/2000/svg";
  const DOMAIN_START = 1958;
  const NOW = 2026.8;

  const KIND_LABEL = {
    party: "Partis", movement: "Mouvements et organisations", coalition: "Coalitions et alliances",
    current: "Courants internes", youth: "Mouvements de jeunesse", micro_party: "Micro-partis",
    association: "Associations", think_tank: "Think tanks", parliamentary_group: "Groupes parlementaires",
  };
  const KIND_SINGLE = {
    party: "Parti", movement: "Mouvement ou organisation", coalition: "Coalition ou alliance",
    current: "Courant interne", youth: "Mouvement de jeunesse", micro_party: "Micro-parti",
    association: "Association", think_tank: "Think tank", parliamentary_group: "Groupe parlementaire",
  };
  const KIND_DEFAULT_ON = ["party", "movement", "coalition", "current", "youth", "micro_party"];
  const FAMILY_LABEL = {
    communiste: "Communiste", trotskiste: "Trotskiste", maoiste: "Maoïste",
    anarchiste_libertaire: "Anarchiste, libertaire", extreme_gauche_autre: "Extrême gauche (autres)",
    socialiste: "Socialiste, social-démocrate", ecologiste: "Écologiste", radical: "Radical",
    centriste_democrate_chretien: "Centriste, démocrate-chrétien", liberal: "Libéral", gaulliste: "Gaulliste",
    conservateur_droite: "Conservateur, droite", souverainiste: "Souverainiste",
    extreme_droite_nationaliste: "Extrême droite, nationaliste", regionaliste_autonomiste: "Régionaliste, autonomiste",
    agrarien_rural: "Agrarien, ruralité", populiste: "Populiste", republicain_laique: "Républicain, laïque",
  };
  const FAM_POS = {
    trotskiste: -2.9, communiste: -2.7, maoiste: -3, anarchiste_libertaire: -2.9, extreme_gauche_autre: -2.8,
    socialiste: -1.6, ecologiste: -1.5, republicain_laique: -0.5, radical: 0.3, centriste_democrate_chretien: 0.2,
    liberal: 1.2, agrarien_rural: 1.5, gaulliste: 1.8, conservateur_droite: 2, souverainiste: 2,
    populiste: 2.5, extreme_droite_nationaliste: 2.9,
  };
  const ROLE_LABEL = { founder: "Fondateur", leader: "Dirigeant", member: "Membre" };
  const REL_LABEL = { split: "Scission", merge: "Fusion", succession: "Succession", affiliation: "Affiliation" };
  const POS_NAMES = [
    [-3, "Extrême gauche"], [-2, "Gauche"], [-1, "Centre gauche"], [0, "Centre"],
    [1, "Centre droit"], [2, "Droite"], [3, "Extrême droite"],
  ];
  const WINGS = {
    all: [-3.3, 4.3], xg: [-3.3, -2.35], g: [-2.35, -0.65], c: [-0.65, 0.65], d: [0.65, 2.35], xd: [2.35, 3.3],
  };
  const PRESIDENTS = [
    ["de Gaulle", 1958.0, 1969.3], ["Pompidou", 1969.4, 1974.3], ["Giscard d'Estaing", 1974.4, 1981.4],
    ["Mitterrand", 1981.4, 1995.4], ["Chirac", 1995.4, 2007.4], ["Sarkozy", 2007.4, 2012.4],
    ["Hollande", 2012.4, 2017.4], ["Macron", 2017.4, 2027.5],
  ];
  const STOPS = [[-3, "#7e1630"], [-2, "#cf3b49"], [-1, "#ea9b93"], [0, "#d9b73f"], [1, "#8fb2de"], [2, "#3f72b8"], [3, "#1b2b63"]];

  // ------------------------------------------------------------------ utilitaires
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const yf = (iso) => {
    if (!iso) return null;
    const y = +iso.slice(0, 4);
    const m = iso.length >= 7 ? +iso.slice(5, 7) : 1;
    const d = iso.length >= 10 ? +iso.slice(8, 10) : 1;
    return y + (m - 1) / 12 + (d - 1) / 372;
  };
  const fmtDate = (iso) => {
    if (!iso) return "";
    const mois = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    if (iso.length >= 10) return `${+iso.slice(8, 10)} ${mois[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
    if (iso.length >= 7) return `${mois[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
    return iso.slice(0, 4);
  };
  const span = (s, e, openEnd) => {
    const a = fmtDate(s), b = fmtDate(e);
    if (a && b) return a === b ? a : `${a} - ${b}`;
    if (a) return openEnd ? `depuis ${a}` : `${a} - ?`;
    if (b) return `jusqu'en ${b}`;
    return "dates inconnues";
  };
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const posColor = (v) => {
    if (v == null) return "#8a8f98";
    v = Math.max(-3, Math.min(3, v));
    for (let i = 0; i < STOPS.length - 1; i++) {
      const [a, ca] = STOPS[i], [b, cb] = STOPS[i + 1];
      if (v <= b) {
        const t = (v - a) / (b - a), A = hex(ca), B = hex(cb);
        return "#" + A.map((x, k) => Math.round(x + (B[k] - x) * t).toString(16).padStart(2, "0")).join("");
      }
    }
    return STOPS[STOPS.length - 1][1];
  };
  const posWord = (v) => {
    if (v == null) return "non renseignée";
    let best = POS_NAMES[0];
    for (const p of POS_NAMES) if (Math.abs(p[0] - v) < Math.abs(best[0] - v)) best = p;
    return best[1].toLowerCase();
  };

  // --------------------------------------------------------------- préparation des données
  const famCount = new Map();
  for (const o of orgs) {
    o.t0 = yf(o.s);
    const t1 = yf(o.e);
    o.endUnknown = false;
    if (o.t0 != null) {
      if (t1 != null) o.t1 = Math.max(t1, o.t0 + 0.3);
      else if (o.st === "actif") o.t1 = NOW;
      else { o.t1 = o.t0 + 3; o.endUnknown = true; }
    } else o.t1 = null;
    // intervalle pendant lequel l'organisation est comptée comme active (photographie à une date) :
    // celui de la barre dessinée ; sans date de fin et toujours active, elle l'est jusqu'à aujourd'hui
    o.a1 = o.t0 == null ? null : (o.st === "actif" && !o.e) ? Infinity : o.t1;
    const b = (() => {
      if (o.pv != null) return { x: o.pv, est: o.ps === "relations" };
      for (const f of o.fam) if (f in FAM_POS) return { x: FAM_POS[f], est: true };
      return { x: null, est: true };
    })();
    o.px = b.x; o.est = b.est;
    o.color = posColor(o.px);
    o.search = norm([o.n, o.t, ...(o.ab || [])].join(" "));
    for (const f of o.fam) famCount.set(f, (famCount.get(f) || 0) + 1);
  }
  for (const p of people) p.search = norm(p.n);

  const relOut = new Map(), relIn = new Map();
  for (const e of D.orgEdges) {
    (relOut.get(e.s) || relOut.set(e.s, []).get(e.s)).push(e);
    (relIn.get(e.t) || relIn.set(e.t, []).get(e.t)).push(e);
  }
  // Lignées : un parti qui change de nom (RPR, UMP, Les Républicains) reste sur la même ligne.
  // On enchaîne les relations de succession qui se suivent dans le temps (chevauchement de 2 ans
  // au plus), une seule suite par organisation.
  const chainNext = new Map(), chainPrev = new Map();
  D.orgEdges
    .filter((e) => e.ty === "succession" && (e.dc || e.c))
    .sort((a, b) => (b.dc + b.c) - (a.dc + a.c))
    .forEach((e) => {
      const a = O.get(e.s), b = O.get(e.t);
      if (!a || !b || a === b || a.t0 == null || b.t0 == null || b.t0 < a.t0) return;
      if (Math.min(a.t1, b.t1) - Math.max(a.t0, b.t0) > 2) return;
      if (chainNext.has(a.id) || chainPrev.has(b.id)) return;
      chainNext.set(a.id, b.id);
      chainPrev.set(b.id, a.id);
    });

  const persByOrg = new Map(), orgsByPers = new Map();
  for (const e of D.personEdges) {
    (persByOrg.get(e.o) || persByOrg.set(e.o, []).get(e.o)).push(e);
    (orgsByPers.get(e.p) || orgsByPers.set(e.p, []).get(e.p)).push(e);
  }

  // --------------------------------------------------------------------------- état
  const state = {
    detail: 2, wing: "all", ppy: 22, y0: 1958, y1: 2027, fam: new Set(), kinds: new Set(KIND_DEFAULT_ON),
    per: false, rel: true, aff: false, pres: true, chains: true, sel: null, person: null,
    date: null, // date de la photographie (ISO complète) ou null
  };
  let forced = new Set();
  let geom = new Map(); // id -> {x, w, y0, y1}
  let cur = null; // dernier rendu

  // ------------------------------------------------------------------------ visibilité
  function inWing(o) {
    const [lo, hi] = WINGS[state.wing];
    if (state.wing === "all") return true;
    if (o.px == null) return false;
    return o.px >= lo && o.px <= hi;
  }
  // filtres de contenu (nature, famille, zone, étrangères), sans le niveau de détail
  function passesFilters(o) {
    if (o.t0 == null) return false;
    if (!state.per && o.per) return false;
    if (!state.kinds.has(o.k)) return false;
    if (state.fam.size && !o.fam.some((f) => state.fam.has(f))) return false;
    return inWing(o);
  }
  function isVisible(o) {
    if (o.t0 == null || o.t1 < state.y0 || o.t0 > state.y1) return false;
    if (o.t1 < DOMAIN_START) return false;
    if (forced.has(o.id)) return true;
    if (o.tier > state.detail) return false;
    return passesFilters(o);
  }
  // l'organisation existe-t-elle à l'instant t (année décimale) ?
  const isActiveAt = (o, t) => o.t0 != null && o.t0 <= t && o.a1 >= t;

  // -------------------------------------------------------------------------- mise en page
  function computeLayout(vis, innerW, left) {
    const [lo, hi] = WINGS[state.wing];
    const xs = (v) => left + ((v - lo) / (hi - lo)) * innerW;
    const UNPOS = 3.85;
    const Y = (t) => TOP + (t - state.y0) * state.ppy;
    // groupes de placement : les organisations d'une même lignée (changements de nom) partagent
    // une ligne ; les autres sont seules
    const inVis = new Set(vis.map((o) => o.id));
    const seen = new Set();
    const groups = [];
    for (const o of vis) {
      if (seen.has(o.id)) continue;
      if (!state.chains) { groups.push([o]); seen.add(o.id); continue; }
      let head = o;
      const guard = new Set([o.id]);
      while (chainPrev.has(head.id) && !guard.has(chainPrev.get(head.id))) {
        head = O.get(chainPrev.get(head.id));
        guard.add(head.id);
      }
      const members = [];
      let cur = head;
      const g2 = new Set();
      while (cur && !g2.has(cur.id)) {
        g2.add(cur.id);
        if (inVis.has(cur.id)) members.push(cur);
        const nx = chainNext.get(cur.id);
        cur = nx ? O.get(nx) : null;
      }
      members.forEach((m) => seen.add(m.id));
      if (members.length) groups.push(members);
    }
    const rank = (grp) => [Math.min(...grp.map((m) => m.tier)), -Math.max(...grp.map((m) => m.imp))];
    groups.sort((A, B) => { const a = rank(A), b = rank(B); return a[0] - b[0] || a[1] - b[1]; });

    const placed = [];
    geom = new Map();
    const bwOf = (o) => (o.tier === 1 ? 13 : o.tier === 2 ? 10 : 8);
    for (const grp of groups) {
      const items = grp.map((o) => {
        const ya = Y(Math.max(o.t0, state.y0));
        return { o, bw: bwOf(o), ya, yb: Math.max(ya + 7, Y(Math.min(o.t1, state.y1))) };
      });
      const lead = [...grp].sort((a, b) => b.imp - a.imp).find((m) => m.px != null);
      const base = lead ? xs(lead.px) : xs(UNPOS);
      const wmax = Math.max(...items.map((i) => i.bw));
      let center = null;
      for (let k = 0; k < 140 && center == null; k++) {
        const sgn = k % 2 ? 1 : -1;
        const c = base + (k === 0 ? 0 : Math.ceil(k / 2) * (wmax + 3) * sgn);
        if (c - wmax / 2 < left || c + wmax / 2 > left + innerW) continue; // reste dans la zone de dessin
        let ok = true;
        for (const it of items) {
          const x = c - it.bw / 2;
          for (const q of placed) {
            if (x < q.x + q.w + 2 && x + it.bw + 2 > q.x && it.ya < q.yb + 12 && it.yb + 12 > q.ya) { ok = false; break; }
          }
          if (!ok) break;
        }
        if (ok) center = c;
      }
      if (center == null) center = Math.max(left + wmax / 2, Math.min(base, left + innerW - wmax / 2));
      for (const it of items) {
        const g = { x: center - it.bw / 2, w: it.bw, ya: it.ya, yb: it.yb };
        placed.push(g);
        geom.set(it.o.id, g);
      }
    }
    return { xs, Y, UNPOS, lo, hi };
  }
  const TOP = 24;

  // -------------------------------------------------------------------------- dessin
  function render() {
    const scroller = $("#scroller");
    const svg = $("#chart");
    const W = Math.max(520, scroller.clientWidth - 4);
    const LEFT = 84, RIGHT = 18;
    const innerW = W - LEFT - RIGHT;
    const vis = orgs.filter(isVisible);
    const L = computeLayout(vis, innerW, LEFT);
    const H = TOP + (state.y1 - state.y0) * state.ppy + 40;
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);
    svg.replaceChildren();

    const defs = el("defs", {}, svg);
    const m = el("mask", { id: "fade", maskContentUnits: "objectBoundingBox" }, defs);
    const lg = el("linearGradient", { id: "fadeg", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: "0", "stop-color": "#fff" }, lg);
    el("stop", { offset: "0.55", "stop-color": "#fff" }, lg);
    el("stop", { offset: "1", "stop-color": "#222" }, lg);
    el("rect", { x: 0, y: 0, width: 1, height: 1, fill: "url(#fadeg)" }, m);

    // bandes de présidence + repères d'années
    const gBg = el("g", {}, svg);
    if (state.pres) {
      PRESIDENTS.forEach(([name, a, b], i) => {
        const ya = L.Y(Math.max(a, state.y0)), yb = L.Y(Math.min(b, state.y1));
        if (yb <= ya) return;
        el("rect", { x: LEFT - 4, y: ya, width: W - LEFT + 4, height: yb - ya, fill: i % 2 ? "var(--band-b)" : "var(--band-a)" }, gBg);
        if (yb - ya > 60) {
          const t = el("text", { x: 70, y: (ya + yb) / 2, class: "yr", "text-anchor": "middle", transform: `rotate(-90 70 ${(ya + yb) / 2})` }, gBg);
          t.textContent = name;
        }
      });
    }
    const step = state.ppy >= 40 ? 1 : state.ppy >= 14 ? 5 : 10;
    for (let y = Math.ceil(state.y0 / step) * step; y <= state.y1; y += step) {
      const yy = L.Y(y);
      el("line", { x1: 28, x2: W - RIGHT, y1: yy, y2: yy, stroke: "var(--grid)" }, gBg);
      const t = el("text", { x: 4, y: yy - 3, class: "yr" }, gBg);
      t.textContent = y;
    }
    for (const [v] of POS_NAMES) {
      if (v < L.lo || v > L.hi) continue;
      const xx = L.xs(v);
      el("line", { x1: xx, x2: xx, y1: 0, y2: H, stroke: "var(--grid)", "stroke-dasharray": v === 0 ? "" : "2 5" }, gBg);
    }
    if (state.wing === "all") {
      const xx = L.xs(3.5);
      el("line", { x1: xx, x2: xx, y1: 0, y2: H, stroke: "var(--line)", "stroke-dasharray": "6 4" }, gBg);
    }

    const gEdges = el("g", {}, svg);
    const gBars = el("g", {}, svg);
    const gLbl = el("g", {}, svg);
    const gPath = el("g", {}, svg);

    const hl = highlightSet();
    const td = state.date ? yf(state.date) : null;
    // estompée si hors de la sélection, ou inexistante à la date de la photographie
    const dimmed = (o) => (hl && !hl.has(o.id)) || (td != null && !isActiveAt(o, td));
    const link = (x1, y1, x2, y2) => {
      const mx = (x1 + x2) / 2;
      return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
    };
    const midX = (g) => g.x + g.w / 2;

    // relations
    let nEdges = 0;
    for (const e of D.orgEdges) {
      if (e.ty === "affiliation" ? !state.aff : !state.rel) continue;
      // un changement de nom sur la même ligne est déjà continu : pas de connecteur
      if (e.ty === "succession" && state.chains && geom.get(e.s) && geom.get(e.t) &&
          Math.abs(geom.get(e.s).x + geom.get(e.s).w / 2 - geom.get(e.t).x - geom.get(e.t).w / 2) < 1.5) continue;
      const a = O.get(e.s), b = O.get(e.t);
      const ga = geom.get(e.s), gb = geom.get(e.t);
      if (!ga || !gb) continue;
      let d;
      if (e.ty === "split") {
        const t = yf(e.d) ?? b.t0;
        const ya = L.Y(Math.min(Math.max(t, a.t0, state.y0), a.t1)), yb = L.Y(Math.max(b.t0, state.y0));
        d = link(midX(ga), ya, midX(gb), yb);
      } else if (e.ty === "merge") {
        const t = yf(e.d) ?? b.t0;
        const ya = L.Y(Math.min(Math.max(a.t1, state.y0), state.y1));
        const yb = L.Y(Math.min(Math.max(t, state.y0), state.y1));
        d = link(midX(ga), ya, midX(gb), yb);
      } else if (e.ty === "succession") {
        const ya = L.Y(Math.min(Math.max(a.t1, state.y0), state.y1)), yb = L.Y(Math.max(b.t0, state.y0));
        d = link(midX(ga), ya, midX(gb), yb);
      } else {
        const t0 = yf(e.st) ?? Math.max(a.t0, b.t0);
        const yy = L.Y(Math.min(Math.max(t0, state.y0), state.y1));
        d = link(midX(ga), yy, midX(gb), yy);
      }
      const path = el("path", {
        d, fill: "none", stroke: "var(--edge)",
        "stroke-width": e.ty === "merge" ? 2.2 : e.ty === "affiliation" ? 1 : 1.5,
        "stroke-opacity": e.ty === "affiliation" ? 0.45 : 0.6,
        "stroke-dasharray": e.ty === "succession" ? "5 3" : e.ty === "affiliation" ? "1 3" : "",
      }, gEdges);
      if ((hl && !(hl.has(e.s) && hl.has(e.t))) || (td != null && !(isActiveAt(a, td) && isActiveAt(b, td)))) path.setAttribute("class", "dim");
      nEdges++;
    }

    // barres
    const labelBoxes = [];
    const sorted = [...vis].sort((a, b) => b.imp - a.imp);
    for (const o of vis) {
      const g = geom.get(o.id);
      const bar = el("g", { class: "bar", tabindex: 0, role: "button", "data-id": o.id, "aria-label": `${o.n}, ${span(o.s, o.e, o.st === "actif")}${td != null && isActiveAt(o, td) ? ", active à la date choisie" : ""}` }, gBars);
      const rect = el("rect", {
        class: "body", x: g.x, y: g.ya, width: g.w, height: g.yb - g.ya, rx: 3,
        fill: o.color, "fill-opacity": o.est ? 0.38 : 0.92,
        stroke: o.color, "stroke-width": o.est ? 1.3 : 0.6, "stroke-dasharray": o.est ? "3 2" : "",
      }, bar);
      if (o.endUnknown) rect.setAttribute("mask", "url(#fade)");
      if (state.sel === o.id) {
        el("rect", { x: g.x - 3, y: g.ya - 3, width: g.w + 6, height: g.yb - g.ya + 6, rx: 5, fill: "none", stroke: "var(--focus)", "stroke-width": 2.5 }, bar);
      }
      if (dimmed(o)) bar.setAttribute("class", "bar dim");
    }
    // étiquettes (placement glouton : les plus importants d'abord)
    for (const o of sorted) {
      const g = geom.get(o.id);
      const txt = labelText(o);
      const fs = o.tier === 1 ? 12 : 11;
      const w = txt.length * fs * 0.54 + 6;
      const bx = g.x + g.w + 4, by = g.ya + 10;
      const box = { x: bx, y: by - 10, w, h: 12 };
      const forcedLabel = forced.has(o.id) || state.sel === o.id;
      if (!forcedLabel && labelBoxes.some((q) => box.x < q.x + q.w && box.x + box.w > q.x && box.y < q.y + q.h && box.y + box.h > q.y)) continue;
      labelBoxes.push(box);
      const t = el("text", { class: "lbl", x: bx, y: by, "font-weight": o.tier === 1 || forcedLabel ? 650 : 400, "font-size": fs }, gLbl);
      t.textContent = txt;
      if (dimmed(o)) t.setAttribute("class", "lbl dim");
    }
    // repères de renommage sur les barres (FN -> RN, UMP -> LR...) : trait et nom, au zoom suffisant
    for (const o of vis) {
      if (!o.nc || o.nc.length < 2) continue;
      const g = geom.get(o.id);
      o.nc.slice(1).forEach((c) => {
        const t = yf(c.date);
        if (t == null || t < o.t0 || t > o.t1) return;
        const yy = L.Y(t);
        if (yy < g.ya || yy > g.yb) return;
        const tick = el("line", { x1: g.x - 2, x2: g.x + g.w + 2, y1: yy, y2: yy, stroke: "var(--halo)", "stroke-width": 2.2 }, gLbl);
        const tt = el("title", {}, tick);
        tt.textContent = `${c.label} (${fmtDate(c.date)})`;
        if (state.ppy >= 18) {
          const box = { x: g.x + g.w + 4, y: yy - 9, w: c.label.length * 5.6 + 6, h: 12 };
          if (!labelBoxes.some((q) => box.x < q.x + q.w && box.x + box.w > q.x && box.y < q.y + q.h && box.y + box.h > q.y)) {
            labelBoxes.push(box);
            const lt = el("text", { class: "lbl", x: box.x, y: yy + 3, "font-size": 10, "font-style": "italic" }, gLbl);
            lt.textContent = "→ " + (c.label.length > 22 ? c.label.slice(0, 21) + "…" : c.label);
          }
        }
      });
    }

    // parcours d'une personne
    if (state.person) drawPersonPath(gPath, L);
    // ligne de la photographie à une date, tracée par-dessus
    if (td != null && td >= state.y0 && td <= state.y1) drawDateLine(gPath, L, W, RIGHT);

    cur = { L, W, H, count: vis.length, edges: nEdges, vis };
    drawAxis(L, W, LEFT);
    updateCounts(vis.length);
    updateSnapshot();
    scheduleHash();
  }

  // ligne horizontale à la date choisie, avec la date écrite à droite
  function drawDateLine(parent, L, W, RIGHT) {
    const yy = L.Y(yf(state.date));
    const g = el("g", { class: "dateline", "pointer-events": "none" }, parent);
    el("line", { x1: 28, x2: W - RIGHT, y1: yy, y2: yy, stroke: "var(--accent)", "stroke-width": 2 }, g);
    const t = el("text", { class: "lbl", x: W - RIGHT - 4, y: yy - 6, "text-anchor": "end", "font-size": 12, "font-weight": 650 }, g);
    t.textContent = fmtDate(state.date);
  }

  function labelText(o) {
    const long = o.n.length > 30;
    if (long && o.ab && o.ab.length) return o.ab[0];
    return o.n.length > 34 ? o.n.slice(0, 32) + "…" : o.n;
  }

  function highlightSet() {
    if (state.person) {
      const s = new Set();
      for (const e of orgsByPers.get(state.person) || []) s.add(e.o);
      return s;
    }
    if (state.sel) {
      const s = new Set([state.sel]);
      for (const e of relOut.get(state.sel) || []) s.add(e.t);
      for (const e of relIn.get(state.sel) || []) s.add(e.s);
      return s;
    }
    return null;
  }

  function drawPersonPath(g, L) {
    const rows = (orgsByPers.get(state.person) || [])
      .map((e) => ({ e, o: O.get(e.o), g: geom.get(e.o) }))
      .filter((r) => r.g && r.o);
    const pts = [];
    for (const r of rows) {
      const t = yf(r.e.s) ?? r.o.t0;
      if (t == null) continue;
      const x = r.g.x + r.g.w / 2;
      const y = L.Y(Math.min(Math.max(t, state.y0), state.y1));
      pts.push({ x, y, t, r, known: !!r.e.s });
    }
    pts.sort((a, b) => a.t - b.t);
    if (pts.length > 1) {
      const d = pts.map((p, i) => (i ? `L${p.x},${p.y}` : `M${p.x},${p.y}`)).join(" ");
      el("path", { d, fill: "none", stroke: "var(--focus)", "stroke-width": 2, "stroke-opacity": 0.85, "stroke-linejoin": "round" }, g);
    }
    for (const p of pts) {
      const c = el("circle", {
        cx: p.x, cy: p.y, r: p.r.e.r === "member" ? 4.5 : 6,
        fill: p.known ? "var(--focus)" : "var(--surface)", stroke: "var(--focus)", "stroke-width": 2,
      }, g);
      const tt = el("title", {}, c);
      tt.textContent = `${ROLE_LABEL[p.r.e.r]} - ${p.r.o.n} (${span(p.r.e.s, p.r.e.e, true)})`;
    }
  }

  function drawAxis(L, W, LEFT) {
    const ax = $("#axis");
    ax.setAttribute("width", W);
    ax.replaceChildren();
    for (const [v, name] of POS_NAMES) {
      if (v < L.lo || v > L.hi) continue;
      const xx = L.xs(v);
      el("line", { x1: xx, x2: xx, y1: 30, y2: 46, stroke: "var(--muted)" }, ax);
      const t = el("text", { x: xx, y: 22, "text-anchor": "middle", class: "yr", "font-size": 12 }, ax);
      t.textContent = name;
    }
    const grad = el("defs", {}, ax);
    const lg = el("linearGradient", { id: "axg", x1: 0, x2: 1, y1: 0, y2: 0 }, grad);
    for (let i = 0; i <= 12; i++) {
      const v = L.lo + ((L.hi - L.lo) * i) / 12;
      el("stop", { offset: i / 12, "stop-color": posColor(Math.min(v, 3)) }, lg);
    }
    el("rect", { x: LEFT, y: 36, width: W - LEFT - 18, height: 5, rx: 2.5, fill: "url(#axg)" }, ax);
    if (state.wing === "all") {
      const t = el("text", { x: L.xs(3.85), y: 22, "text-anchor": "middle", class: "yr", "font-size": 12 }, ax);
      t.textContent = "Non positionné";
    }
  }

  function updateCounts(n) {
    const total = orgs.filter((o) => o.t0 != null).length;
    const nodate = orgs.filter((o) => o.t0 == null).length;
    $("#detail-count").innerHTML = `${n} organisations affichées sur ${total}. ` +
      (nodate ? `<button class="lnk" id="nodate">${nodate} sans date de fondation</button> ne sont pas dessinées.` : "");
    const b = $("#nodate");
    if (b) b.onclick = () => showNoDate();
  }

  // ---------------------------------------------------------------------- panneau
  const panel = $("#panel");
  const orgLink = (id, label) => `<button class="lnk" data-org="${esc(id)}">${esc(label ?? O.get(id)?.n ?? id)}</button>`;
  const perLink = (id, label) => `<button class="lnk" data-person="${esc(id)}">${esc(label ?? P.get(id)?.n ?? id)}</button>`;

  // ce que montre le panneau : "defaut" (accueil ou photographie), ou une fiche
  let panelMode = "defaut";
  let snapHtml = ""; // dernier HTML de la photographie, pour ne pas reconstruire à l'identique
  const zoneOpen = {}; // zones dépliées par l'utilisateur dans la photographie

  function showDefault() {
    panelMode = "defaut";
    if (state.date) { showSnapshot(); return; }
    snapHtml = "";
    delete panel.dataset.snap;
    const total = orgs.length, np = people.length;
    const m = D.meta || {};
    panel.innerHTML = `
      <h2>Explorer la Ve République</h2>
      <p class="meta">Les partis sont placés sur un axe gauche-droite, le temps descend de 1958 à aujourd'hui.</p>
      <div class="stats">
        <div><b>${total}</b><span>organisations</span></div>
        <div><b>${np}</b><span>personnes</span></div>
        <div><b>${D.orgEdges.length}</b><span>filiations</span></div>
      </div>
      <section><h3>Pour commencer</h3>
        <p>Cliquez sur une barre pour voir un parti, ses scissions, fusions, ses fondateurs et dirigeants. Cliquez sur un nom de personne pour suivre son parcours à travers les partis.</p>
        <p>Choisissez une zone du spectre à gauche pour agrandir cette partie de l'axe et faire apparaître les petits mouvements.</p>
        <p>Ctrl + molette sur la frise pour changer l'échelle du temps.</p>
        <p>Le champ « Voir à la date » trace une ligne sur la frise et liste les organisations qui existaient ce jour-là.</p>
      </section>
      <section><h3>Sources et limites</h3>
        <p class="src">Données extraites automatiquement de Wikipédia en français (texte sous licence CC BY-SA 4.0) et de Wikidata (CC0). Les positions gauche-droite sont celles que déclare Wikipédia, ou une estimation par famille politique, signalée par un contour en pointillés. Les dates sont souvent limitées à l'année.</p>
        <p class="src">Données collectées du ${esc(m.collected_from || "?")} au ${esc(m.collected_to || "?")}${m.wikipedia_last_revision ? ", dernière révision Wikipédia lue : " + esc(String(m.wikipedia_last_revision).slice(0, 10)) : ""}.</p>
      </section>`;
  }

  function showNoDate() {
    panelMode = "autre"; delete panel.dataset.snap;
    const list = orgs.filter((o) => o.t0 == null).sort((a, b) => b.imp - a.imp);
    panel.innerHTML = `<h2>Sans date de fondation</h2><p class="meta">${list.length} organisations dont Wikipédia ne donne pas la date.</p>
      <ul class="rel">${list.map((o) => `<li>${orgLink(o.id)} <span class="d">${esc(KIND_SINGLE[o.k] || "")}</span></li>`).join("")}</ul>`;
  }

  function relList(title, rows) {
    if (!rows.length) return "";
    return `<section><h3>${title}</h3><ul class="rel">${rows.join("")}</ul></section>`;
  }

  function showOrg(o) {
    panelMode = "autre"; delete panel.dataset.snap;
    const out = relOut.get(o.id) || [], inn = relIn.get(o.id) || [];
    const row = (id, txt, e) => `<li>${txt ? esc(txt) + " " : ""}${orgLink(id)}<span class="d">${e}</span></li>`;
    const dt = (e) => (e ? span(e.d || e.st, e.en, !e.en) : "");
    const parents = inn.filter((e) => e.ty === "split").map((e) => row(e.s, "Issu d'une scission de", dt(e)));
    const children = out.filter((e) => e.ty === "split").sort((a, b) => (a.d || "").localeCompare(b.d || "")).map((e) => row(e.t, "", dt(e)));
    const mergedFrom = inn.filter((e) => e.ty === "merge").map((e) => row(e.s, "A fusionné ici :", dt(e)));
    const mergedInto = out.filter((e) => e.ty === "merge").map((e) => row(e.t, "A fusionné dans", dt(e)));
    const pred = inn.filter((e) => e.ty === "succession").map((e) => row(e.s, "Précédé par", dt(e)));
    const succ = out.filter((e) => e.ty === "succession").map((e) => row(e.t, "Devenu", dt(e)));
    const affOut = out.filter((e) => e.ty === "affiliation").map((e) => row(e.t, "", dt(e)));
    const affIn = inn.filter((e) => e.ty === "affiliation").map((e) => row(e.s, "", dt(e)));

    const pe = persByOrg.get(o.id) || [];
    const byPerson = (role) => pe.filter((e) => e.r === role && P.get(e.p));
    const founders = byPerson("founder");
    const leaders = byPerson("leader").sort((a, b) => (a.s || "9999").localeCompare(b.s || "9999"));
    const members = byPerson("member").sort((a, b) => P.get(b.p).imp - P.get(a.p).imp);
    const seenL = new Set();
    const leaderRows = leaders.filter((e) => { const k = e.p + e.l; if (seenL.has(k)) return false; seenL.add(k); return true; })
      .map((e) => `<li>${perLink(e.p)}<span class="d">${esc(e.l ? e.l.replace(/\s+/g, " ").slice(0, 46) + " " : "")}${esc(span(e.s, e.e, true))}</span></li>`);
    const founderRows = founders.map((e) => `<li>${perLink(e.p)}<span class="d">${esc(e.s ? fmtDate(e.s) : "")}</span></li>`);
    const memberRows = members.map((e) => `<li>${perLink(e.p)}<span class="d">${esc(e.s || e.e ? span(e.s, e.e, true) : "")}</span></li>`);

    const famBadges = o.fam.map((f) => `<span class="badge">${esc(FAMILY_LABEL[f] || f)}</span>`).join("");
    const posNote = o.pv == null ? (o.px != null ? `Position estimée : ${posWord(o.px)}` : "Position non renseignée") : `Position : ${posWord(o.pv)}`;
    const status = { actif: "toujours actif", dissous: "dissous", fusionne: "a fusionné", transforme: "transformé" }[o.st] || o.st;
    const lineage = (() => {
      const names = (o.nc && o.nc.length >= 2) ? o.nc.map((c) => `${esc(c.label)} (${esc(fmtDate(c.date))})`) : [];
      return names.length ? `<p class="kicker">Noms successifs : ${names.join(", puis ")}</p>` : "";
    })();
    panel.innerHTML = `
      <h2>${esc(o.n)}</h2>
      <div class="meta">${esc(KIND_SINGLE[o.k] || "")}${o.ab && o.ab.length ? " (" + esc(o.ab.join(", ")) + ")" : ""}<br>
        ${esc(span(o.s, o.e, o.st === "actif"))} - ${esc(status)}${o.endUnknown ? ", date de fin inconnue" : ""}</div>
      <div><span class="badge">${esc(posNote)}</span>${famBadges}${o.per ? '<span class="badge">hors de France ou frontalier</span>' : ""}</div>
      <p>${esc(o.sum || "Pas de résumé disponible.")}</p>
      ${lineage}
      <p class="src">Source : <a href="${esc(o.url)}" target="_blank" rel="noopener">Wikipédia</a>, texte sous licence CC BY-SA 4.0.</p>
      ${relList("Origine", [...parents, ...pred, ...mergedFrom])}
      ${relList("Devenir", [...succ, ...mergedInto])}
      ${relList(`Scissions (${children.length})`, children)}
      ${relList("Fait partie de", affOut)}
      ${relList("Composantes et membres", affIn)}
      ${relList("Fondateurs", founderRows)}
      ${relList(`Dirigeants (${leaderRows.length})`, leaderRows)}
      <section><h3>Personnes rattachées (${memberRows.length})</h3>
        <ul class="rel" id="members">${memberRows.slice(0, 12).join("")}</ul>
        ${memberRows.length > 12 ? `<button class="more" id="more-members">Afficher les ${memberRows.length - 12} autres</button>` : ""}
      </section>
      ${fixSection(o)}`;
    const more = $("#more-members");
    if (more) more.onclick = () => { $("#members").innerHTML = memberRows.join(""); more.remove(); };
    wireFix(o);
  }

  function showPerson(p) {
    panelMode = "autre"; delete panel.dataset.snap;
    const rows = [...(orgsByPers.get(p.id) || [])].filter((e) => O.get(e.o))
      .sort((a, b) => (a.s || O.get(a.o).s || "9999").localeCompare(b.s || O.get(b.o).s || "9999"));
    const life = p.b || p.d ? `${p.b ? fmtDate(p.b) : "?"} - ${p.d ? fmtDate(p.d) : ""}` : "";
    panel.innerHTML = `
      <h2>${esc(p.n)}</h2>
      <div class="meta">${esc(life)}</div>
      <p>${esc(p.sum || "")}</p>
      <p class="src">Source : <a href="${esc(p.url)}" target="_blank" rel="noopener">Wikipédia</a>, texte sous licence CC BY-SA 4.0.</p>
      <section><h3>Parcours dans les partis (${rows.length})</h3>
        <ul class="rel">${rows.map((e) => `<li>${esc(ROLE_LABEL[e.r])} ${orgLink(e.o)}<span class="d">${esc(e.l && e.r === "leader" ? e.l.replace(/\s+/g, " ").slice(0, 40) + " " : "")}${esc(span(e.s, e.e, true))}</span></li>`).join("")}</ul>
      </section>
      <p class="kicker">Le parcours est tracé en orange sur la frise ; les ronds creux indiquent une date inconnue.</p>
      <button class="more" id="clear-person">Quitter le parcours</button>`;
    $("#clear-person").onclick = () => selectNone();
  }

  // ------------------------------------------------------- photographie à une date
  const ZONES = [
    ["xg", "Extrême gauche"], ["g", "Gauche"], ["c", "Centre"], ["d", "Droite"], ["xd", "Extrême droite"], ["np", "Non positionné"],
  ];
  // zone du spectre d'une organisation (mêmes bornes que le zoom par zone)
  function zoneOf(o) {
    const v = o.px;
    if (v == null) return "np";
    if (v < -2.35) return "xg";
    if (v < -0.65) return "g";
    if (v <= 0.65) return "c";
    if (v < 2.35) return "d";
    return "xd";
  }
  // organisations actives à la date choisie, groupées par zone. On respecte les filtres de contenu
  // (nature, famille, zone, étrangères) mais pas le niveau de détail : `hidden` compte celles qui
  // existent mais ne sont pas dessinées à ce niveau.
  function snapshot() {
    const t = yf(state.date);
    const groups = new Map(ZONES.map(([k]) => [k, []]));
    let total = 0, hidden = 0;
    for (const o of orgs) {
      if (!passesFilters(o) || !isActiveAt(o, t)) continue;
      groups.get(zoneOf(o)).push(o);
      total++;
      if (o.tier > state.detail) hidden++;
    }
    for (const l of groups.values()) l.sort((a, b) => b.imp - a.imp);
    return { t, groups, total, hidden };
  }
  const plural = (n, un, plus) => `${n} ${n > 1 ? plus : un}`;

  function showSnapshot() {
    const sn = snapshot();
    const when = fmtDate(state.date);
    const zonesHtml = ZONES.map(([k, name]) => {
      const list = sn.groups.get(k);
      if (!list.length) return "";
      const open = zoneOpen[k] ?? list.length <= 15;
      const rows = list.map((o) => `<li>${orgLink(o.id)}<span class="d">${esc(KIND_SINGLE[o.k] || "")}, ${esc(span(o.s, o.e, o.st === "actif"))}${o.endUnknown ? " (fin inconnue)" : ""}${o.tier > state.detail ? ", non dessinée" : ""}</span></li>`);
      return `<details data-zone="${k}"${open ? " open" : ""}><summary>${esc(name)} (${list.length})</summary><ul class="rel">${rows.join("")}</ul></details>`;
    }).join("");
    snapHtml = `
      <h2>Photographie au ${esc(when)}</h2>
      <p class="meta">${plural(sn.total, "organisation active", "organisations actives")} à cette date, d'après les dates de fondation et de fin de chaque fiche.</p>
      <div class="stats zones">${ZONES.map(([k, name]) => `<div><b>${sn.groups.get(k).length}</b><span>${esc(name)}</span></div>`).join("")}</div>
      ${sn.hidden ? `<p class="hint">${plural(sn.hidden, "organisation n'est pas dessinée", "organisations ne sont pas dessinées")} au niveau de détail actuel. <button class="lnk" data-act="all-levels">Afficher tous les niveaux</button></p>` : ""}
      <section><h3>Organisations actives</h3>${zonesHtml || "<p>Aucune organisation ne correspond aux filtres actuels à cette date.</p>"}</section>
      <p class="src">Une organisation dont la fin est inconnue est comptée sur la durée tracée (trois ans). Les dates données à l'année près sont comptées au 1er janvier.</p>
      <button class="more" data-act="clear-date">Retirer la date</button>`;
    if (panel.dataset.snap !== snapHtml) { panel.innerHTML = snapHtml; panel.dataset.snap = snapHtml; }
  }
  // mise à jour après chaque dessin : texte du bloc « Voir à la date » et, si le panneau montre la
  // photographie, sa liste
  function updateSnapshot() {
    const out = $("#date-out"), see = $("#date-see");
    if (!state.date) {
      out.textContent = "Aucune date choisie.";
      see.hidden = true;
      return;
    }
    const sn = snapshot();
    out.textContent = `${fmtDate(state.date)} : ${plural(sn.total, "organisation active", "organisations actives")}.`;
    see.hidden = false;
    if (panelMode === "defaut" && !state.sel && !state.person) showSnapshot();
  }

  const DATE_MIN = "1958-01-01", DATE_MAX = "2026-12-31";
  const monthIso = (i) => `${1958 + Math.floor(i / 12)}-${String(i % 12 + 1).padStart(2, "0")}-01`;
  const isoMonth = (iso) => (+iso.slice(0, 4) - 1958) * 12 + (+iso.slice(5, 7) - 1);
  const validIso = (v) => /^\d{4}-\d{2}-\d{2}$/.test(v || "") && !Number.isNaN(Date.parse(v));
  const clampDate = (v) => (v < DATE_MIN ? DATE_MIN : v > DATE_MAX ? DATE_MAX : v);

  // aligne le curseur, le champ et le bouton sur state.date
  function syncDateControls() {
    const range = $("#date-range");
    $("#date").value = state.date || "";
    if (state.date) {
      range.value = isoMonth(state.date);
      range.setAttribute("aria-valuetext", fmtDate(state.date));
    }
    range.classList.toggle("off", !state.date);
    $("#date-clear").hidden = !state.date;
  }
  // fixe (ou retire, avec null) la date de la photographie
  function setDate(iso, { scroll = true } = {}) {
    state.date = iso && validIso(iso) ? clampDate(iso) : null;
    syncDateControls();
    if (panelMode === "defaut" && !state.sel && !state.person) showDefault();
    render();
    if (state.date && scroll) scrollToDate();
  }
  function scrollToDate() {
    if (!state.date || !cur) return;
    const yy = cur.L.Y(yf(state.date));
    const sc = $("#scroller");
    sc.scrollTop = Math.max(0, yy - sc.clientHeight / 2);
  }

  // ------------------------------------------------------------- liens permanents
  // L'état de la vue est écrit dans le fragment d'URL (#zone=g&detail=3&...) avec replaceState : on
  // ne crée pas d'entrée d'historique à chaque réglage. Seules les valeurs différentes des valeurs par
  // défaut sont écrites, pour garder l'adresse courte.
  const OPT_NAMES = { per: "etrangeres", rel: "relations", aff: "coalitions", pres: "presidences", chains: "lignees" };
  const OPT_DEFAULT = ["rel", "pres", "chains"];
  const sameList = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

  function encodeState() {
    const q = new URLSearchParams();
    if (state.wing !== "all") q.set("zone", state.wing);
    if (state.detail !== 2) q.set("detail", state.detail);
    if (state.ppy !== 22) q.set("echelle", state.ppy);
    if (state.y0 !== 1958) q.set("de", state.y0);
    if (state.y1 !== 2027) q.set("a", state.y1);
    if (state.fam.size) q.set("familles", [...state.fam].sort().join(","));
    const kinds = [...state.kinds].sort();
    if (!sameList(kinds, KIND_DEFAULT_ON)) q.set("natures", kinds.join(","));
    const opts = Object.keys(OPT_NAMES).filter((k) => state[k]);
    if (!sameList(opts, OPT_DEFAULT)) q.set("options", opts.map((k) => OPT_NAMES[k]).join(","));
    if (state.sel) q.set("org", state.sel);
    if (state.person) q.set("personne", state.person);
    if (state.date) q.set("date", state.date);
    return q.toString().replace(/%3A/g, ":").replace(/%2C/g, ",");
  }

  let hashTimer = null, lastHash = "";
  function writeHash() {
    clearTimeout(hashTimer);
    const h = encodeState();
    lastHash = h;
    if (h === location.hash.slice(1)) return;
    try {
      history.replaceState(null, "", location.pathname + location.search + (h ? "#" + h : ""));
    } catch (e) { /* adresse non modifiable (aperçu, navigateur restrictif) : on ignore */ }
  }
  // écriture différée : un curseur déplacé en continu ne déclenche qu'une écriture
  function scheduleHash() {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(writeHash, 200);
  }

  // aligne tous les contrôles de la barre latérale sur state
  function syncControls() {
    document.querySelectorAll("#wings button").forEach((b) => b.classList.toggle("on", b.dataset.wing === state.wing));
    $("#detail").value = state.detail;
    $("#ppy").value = state.ppy;
    $("#y0").value = state.y0;
    $("#y1").value = state.y1;
    $("#presidents").checked = state.pres;
    for (const k of ["per", "rel", "aff", "chains"]) $("#" + k).checked = state[k];
    document.querySelectorAll("#families .chip").forEach((b) => b.classList.toggle("on", state.fam.has(b.dataset.fam)));
    document.querySelectorAll("#kinds input").forEach((i) => { i.checked = state.kinds.has(i.dataset.kind); });
    syncDateControls();
  }

  // lit le fragment d'URL et applique l'état ; renvoie false s'il ne contient pas de réglage
  function applyHash() {
    const raw = location.hash.replace(/^#/, "");
    if (!raw.includes("=")) return false;
    const q = new URLSearchParams(raw);
    const num = (k, lo, hi, def) => {
      const v = q.has(k) ? Number(q.get(k)) : NaN;
      return Number.isFinite(v) ? Math.max(lo, Math.min(hi, Math.round(v))) : def;
    };
    const list = (k) => (q.get(k) || "").split(",").filter(Boolean);
    state.wing = q.get("zone") in WINGS ? q.get("zone") : "all";
    state.detail = num("detail", 1, 3, 2);
    state.ppy = num("echelle", 8, 80, 22);
    state.y0 = num("de", 1958, 2026, 1958);
    state.y1 = Math.max(state.y0 + 1, num("a", 1959, 2027, 2027));
    state.fam = new Set(list("familles").filter((f) => famCount.has(f)));
    state.kinds = q.has("natures") ? new Set(list("natures").filter((k) => k in KIND_LABEL)) : new Set(KIND_DEFAULT_ON);
    const opts = q.has("options") ? list("options") : OPT_DEFAULT.map((k) => OPT_NAMES[k]);
    for (const k of Object.keys(OPT_NAMES)) state[k] = opts.includes(OPT_NAMES[k]);
    const date = q.get("date");
    state.date = validIso(date) ? clampDate(date) : null;
    state.sel = null; state.person = null; forced = new Set();
    syncControls();
    const org = O.get(q.get("org")), pers = P.get(q.get("personne"));
    if (org && org.t0 != null) selectOrg(org.id);
    else if (pers) selectPerson(pers.id);
    else {
      showDefault();
      render();
      const sc = $("#scroller");
      if (state.date) scrollToDate(); else sc.scrollTop = 0;
    }
    return true;
  }
  // un fragment modifié à la main (ou collé) dans l'onglet déjà ouvert est appliqué ; nos propres
  // écritures passent par replaceState et ne déclenchent pas cet événement
  window.addEventListener("hashchange", () => {
    if (location.hash.slice(1) !== lastHash) applyHash();
  });

  // ---------------------------------------------------------------- copie dans le presse-papiers
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) { /* repli ci-dessous */ }
    const ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", "");
    ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }
  // message court à côté des boutons d'outils, annoncé par la région role="status"
  let statusTimer = null;
  function announce(msg) {
    const st = $("#status");
    st.textContent = msg;
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => { st.textContent = ""; }, 4000);
  }
  $("#copy-link").addEventListener("click", async () => {
    writeHash();
    const ok = await copyText(location.href);
    if (ok) announce("Lien copié.");
    else { announce("Copie automatique impossible."); window.prompt("Copiez ce lien :", location.href); }
  });

  // ------------------------------------------------------------------------ export CSV
  const STATUS_LABEL = { actif: "toujours actif", dissous: "dissous", fusionne: "a fusionné", transforme: "transformé" };
  // une cellule CSV : guillemets doublés si besoin, et apostrophe devant les valeurs qu'un tableur
  // lirait comme une formule (= + @ -) pour éviter l'injection de formule
  function csvCell(v) {
    let t = v == null ? "" : String(v);
    if (/^[=+@\t\r]/.test(t) || /^-(?![\d.,]+$)/.test(t)) t = "'" + t;
    return /[;"\r\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
  }
  const csvRow = (cells) => cells.map(csvCell).join(";");
  function posText(o) {
    if (o.pv != null) return posWord(o.pv);
    return o.px != null ? `${posWord(o.px)} (estimée)` : "non positionnée";
  }

  // Le fichier contient les organisations actuellement dessinées et, si une personne est
  // sélectionnée, un second bloc avec son parcours. Séparateur point-virgule, UTF-8 avec BOM
  // (pour qu'Excel lise bien les accents), fins de ligne CRLF.
  function buildCsv() {
    const td = state.date ? yf(state.date) : null;
    const lines = [];
    const head = ["Nom", "Nature", "Début", "Fin", "Statut", "Position", "Familles", "Lien Wikipédia"];
    if (td != null) head.push(`Active le ${fmtDate(state.date)}`);
    lines.push(csvRow(head));
    const rows = [...((cur && cur.vis) || [])].sort((a, b) => a.t0 - b.t0 || a.n.localeCompare(b.n, "fr"));
    for (const o of rows) {
      const cells = [o.n, KIND_SINGLE[o.k] || o.k, o.s || "", o.e || "", STATUS_LABEL[o.st] || o.st, posText(o),
        o.fam.map((f) => FAMILY_LABEL[f] || f).join(" / "), o.url];
      if (td != null) cells.push(isActiveAt(o, td) ? "oui" : "non");
      lines.push(csvRow(cells));
    }
    const p = state.person && P.get(state.person);
    if (p) {
      lines.push("", csvRow([`Parcours de ${p.n}`]), csvRow(["Rôle", "Organisation", "Début", "Fin"]));
      const path = [...(orgsByPers.get(p.id) || [])].filter((e) => O.get(e.o))
        .sort((a, b) => (a.s || O.get(a.o).s || "9999").localeCompare(b.s || O.get(b.o).s || "9999"));
      for (const e of path) lines.push(csvRow([ROLE_LABEL[e.r] || e.r, O.get(e.o).n, e.s || "", e.e || ""]));
    }
    return { text: lines.join("\r\n") + "\r\n", nOrgs: rows.length, person: p || null };
  }
  function downloadCsv() {
    const { text, nOrgs, person } = buildCsv();
    const blob = new Blob(["﻿" + text], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `partis-affiches-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    announce(`${plural(nOrgs, "organisation exportée", "organisations exportées")}${person ? ", avec le parcours de " + person.n : ""}.`);
  }
  $("#export-csv").addEventListener("click", downloadCsv);

  // ----------------------------------------------------------- proposer une correction
  // Formulaire qui prépare l'entrée à coller dans data/overrides.json. La clé est le titre de la page
  // Wikipédia (champ `t`). Les valeurs actuelles sont pré-remplies ; rien n'est envoyé nulle part.
  const ISO_PARTIAL = /^\d{4}(-\d{2}(-\d{2})?)?$/;

  function fixSection(o) {
    const v = (x) => esc(x ?? "");
    return `<section class="fix"><h3>Corriger cette fiche</h3>
      <button class="more" id="fix-open" type="button" aria-expanded="false" aria-controls="fix-box">Proposer une correction</button>
      <div id="fix-box" hidden>
        <p class="hint">Modifiez les valeurs, puis copiez l'entrée JSON et collez-la dans <code>data/overrides.json</code>
          (en la fusionnant avec les clés existantes). Relancez ensuite <code>python pipeline/run_all.py 7 8 9</code>.</p>
        <div class="fix-grid">
          <label for="fx-start">Début</label>
          <input id="fx-start" type="text" value="${v(o.s)}" placeholder="AAAA, AAAA-MM ou AAAA-MM-JJ" autocomplete="off">
          <label for="fx-end">Fin <span class="d">(vide si toujours actif)</span></label>
          <input id="fx-end" type="text" value="${v(o.e)}" placeholder="AAAA, AAAA-MM ou AAAA-MM-JJ" autocomplete="off">
          <label for="fx-pos">Position <span class="d">(-3 extrême gauche à 3 extrême droite)</span></label>
          <input id="fx-pos" type="number" min="-3" max="3" step="0.5" value="${o.pv == null ? "" : o.pv}">
          <label for="fx-tier">Niveau de zoom</label>
          <select id="fx-tier">${[1, 2, 3].map((n) => `<option value="${n}"${o.tier === n ? " selected" : ""}>${n} - ${["grands partis", "principaux", "détail"][n - 1]}</option>`).join("")}</select>
        </div>
        <label class="check"><input id="fx-per" type="checkbox"${o.per ? " checked" : ""}> Organisation périphérique (masquée par défaut)</label>
        <fieldset class="fix-act"><legend>Page Wikipédia « ${esc(o.t)} »</legend>
          <label class="check"><input type="radio" name="fx-act" value="none" checked> Garder dans le graphe</label>
          <label class="check"><input type="radio" name="fx-act" value="exclude"> Demander l'exclusion de la page</label>
          <label class="check"><input type="radio" name="fx-act" value="include"> Demander l'inclusion forcée de la page</label>
        </fieldset>
        <label class="check"><input id="fx-only" type="checkbox"> Ne garder que les champs modifiés</label>
        <p class="fix-err" id="fx-err" role="alert"></p>
        <label for="fx-out" class="fix-lbl">Entrée à coller</label>
        <textarea id="fx-out" readonly rows="11" spellcheck="false"></textarea>
        <button class="more" id="fx-copy" type="button">Copier l'entrée JSON</button>
      </div></section>`;
  }

  // construit l'objet à coller et la liste des erreurs de saisie
  function buildFix(o) {
    const err = [];
    const dateField = (id, label) => {
      const raw = $(id).value.trim();
      const bad = raw !== "" && !ISO_PARTIAL.test(raw);
      $(id).setAttribute("aria-invalid", bad ? "true" : "false");
      if (bad) err.push(`${label} : format attendu AAAA, AAAA-MM ou AAAA-MM-JJ.`);
      return raw;
    };
    const posRaw = $("#fx-pos").value.trim();
    const pos = posRaw === "" ? null : Number(posRaw);
    const posBad = pos != null && (!Number.isFinite(pos) || pos < -3 || pos > 3);
    $("#fx-pos").setAttribute("aria-invalid", posBad ? "true" : "false");
    if (posBad) err.push("Position : un nombre entre -3 et 3 est attendu.");
    const now = {
      start: dateField("#fx-start", "Début"), end: dateField("#fx-end", "Fin"),
      position_value: pos, tier: Number($("#fx-tier").value), peripheral: $("#fx-per").checked,
    };
    const was = { start: o.s || "", end: o.e || "", position_value: o.pv ?? null, tier: o.tier, peripheral: !!o.per };
    const only = $("#fx-only").checked;
    const entry = {};
    for (const k of Object.keys(now)) if (!only || now[k] !== was[k]) entry[k] = now[k];
    const act = (document.querySelector('input[name="fx-act"]:checked') || {}).value;
    const out = {};
    if (act === "exclude") out.exclude = [o.t];
    if (act === "include") out.include = [o.t];
    if (act !== "exclude" && (Object.keys(entry).length || !only)) out.org = { [o.t]: entry };
    return { json: JSON.stringify(out, null, 2), err };
  }

  function wireFix(o) {
    const btn = $("#fix-open"), box = $("#fix-box");
    if (!btn) return;
    const refresh = () => {
      const { json, err } = buildFix(o);
      $("#fx-out").value = json;
      $("#fx-err").textContent = err.join(" ");
    };
    btn.onclick = () => {
      const open = box.hidden;
      box.hidden = !open;
      btn.setAttribute("aria-expanded", String(open));
      if (open) { refresh(); $("#fx-start").focus(); }
    };
    box.addEventListener("input", refresh);
    box.addEventListener("change", refresh);
    $("#fx-copy").onclick = async () => {
      refresh();
      const out = $("#fx-out");
      const ok = await copyText(out.value);
      if (!ok) out.select();
      announce(ok ? "Entrée JSON copiée." : "Sélectionnée : copiez avec Ctrl + C.");
    };
  }

  // ------------------------------------------------------------------- interactions
  function neighborsForced(id) {
    const s = new Set([id]);
    for (const e of relOut.get(id) || []) if (e.ty !== "affiliation") s.add(e.t);
    for (const e of relIn.get(id) || []) if (e.ty !== "affiliation") s.add(e.s);
    return s;
  }
  function selectOrg(id, scroll = true) {
    state.sel = id; state.person = null;
    forced = neighborsForced(id);
    showOrg(O.get(id));
    render();
    if (scroll) scrollToOrg(id);
  }
  function selectPerson(id) {
    state.person = id; state.sel = null;
    forced = new Set((orgsByPers.get(id) || []).map((e) => e.o));
    showPerson(P.get(id));
    render();
    const first = (orgsByPers.get(id) || []).map((e) => O.get(e.o)).filter((o) => o && o.t0 != null).sort((a, b) => a.t0 - b.t0)[0];
    if (first) scrollToOrg(first.id);
  }
  function selectNone() {
    state.sel = null; state.person = null; forced = new Set();
    showDefault();
    render();
  }
  function scrollToOrg(id) {
    const g = geom.get(id);
    if (!g) return;
    const sc = $("#scroller");
    sc.scrollTo({ top: Math.max(0, g.ya - 140), behavior: "smooth" });
    const cx = g.x + g.w / 2;
    if (cx < sc.scrollLeft || cx > sc.scrollLeft + sc.clientWidth) sc.scrollTo({ left: Math.max(0, cx - sc.clientWidth / 2) });
  }

  $("#chart").addEventListener("click", (ev) => {
    const bar = ev.target.closest(".bar");
    if (bar) selectOrg(bar.dataset.id, false);
    else if (state.sel || state.person) selectNone();
  });
  $("#chart").addEventListener("keydown", (ev) => {
    if ((ev.key === "Enter" || ev.key === " ") && ev.target.classList.contains("bar")) {
      ev.preventDefault();
      selectOrg(ev.target.dataset.id, false);
    }
  });
  panel.addEventListener("click", (ev) => {
    const o = ev.target.closest("[data-org]");
    const p = ev.target.closest("[data-person]");
    const a = ev.target.closest("[data-act]");
    if (o) selectOrg(o.dataset.org);
    else if (p) selectPerson(p.dataset.person);
    else if (a) panelAction(a.dataset.act);
  });
  // mémorise les zones dépliées dans la photographie (l'événement toggle ne remonte pas : capture)
  panel.addEventListener("toggle", (ev) => {
    const d = ev.target;
    if (d.dataset && d.dataset.zone) zoneOpen[d.dataset.zone] = d.open;
  }, true);
  function panelAction(act) {
    if (act === "clear-date") setDate(null);
    else if (act === "all-levels") { state.detail = 3; $("#detail").value = 3; render(); }
  }

  const tip = $("#tooltip");
  $("#chart").addEventListener("mousemove", (ev) => {
    const bar = ev.target.closest(".bar");
    if (!bar) { tip.hidden = true; return; }
    const o = O.get(bar.dataset.id);
    tip.innerHTML = `<b>${esc(o.n)}</b>${esc(KIND_SINGLE[o.k] || "")}<br>${esc(span(o.s, o.e, o.st === "actif"))}<br>${esc(o.pv == null ? (o.px != null ? "position estimée : " + posWord(o.px) : "position non renseignée") : posWord(o.pv))}`;
    tip.hidden = false;
    const x = Math.min(ev.clientX + 14, window.innerWidth - 320), y = Math.min(ev.clientY + 14, window.innerHeight - 110);
    tip.style.left = x + "px"; tip.style.top = y + "px";
  });
  $("#chart").addEventListener("mouseleave", () => { tip.hidden = true; });

  // filtres
  $("#wings").addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    const wasAll = state.wing === "all";
    state.wing = b.dataset.wing;
    document.querySelectorAll("#wings button").forEach((x) => x.classList.toggle("on", x === b));
    if (state.wing !== "all" && wasAll) state.detail = 3;
    if (state.wing === "all") state.detail = 2;
    $("#detail").value = state.detail;
    render();
    $("#scroller").scrollTo({ top: 0 });
  });
  $("#detail").addEventListener("input", (ev) => { state.detail = +ev.target.value; render(); });

  function setPpy(v) {
    const sc = $("#scroller");
    const centerYear = state.y0 + (sc.scrollTop + sc.clientHeight / 2 - TOP) / state.ppy;
    state.ppy = Math.max(8, Math.min(80, v));
    $("#ppy").value = state.ppy;
    render();
    sc.scrollTop = TOP + (centerYear - state.y0) * state.ppy - sc.clientHeight / 2;
  }
  $("#ppy").addEventListener("input", (ev) => setPpy(+ev.target.value));
  $("#zoom-in").onclick = () => setPpy(state.ppy + 4);
  $("#zoom-out").onclick = () => setPpy(state.ppy - 4);
  $("#scroller").addEventListener("wheel", (ev) => {
    if (!ev.ctrlKey) return;
    ev.preventDefault();
    setPpy(state.ppy + (ev.deltaY < 0 ? 3 : -3));
  }, { passive: false });
  const yearInput = () => {
    const a = Math.max(1958, Math.min(2026, +$("#y0").value || 1958));
    const b = Math.max(a + 1, Math.min(2027, +$("#y1").value || 2027));
    state.y0 = a; state.y1 = b;
    render();
  };
  $("#y0").addEventListener("change", yearInput);
  $("#y1").addEventListener("change", yearInput);
  $("#presidents").addEventListener("change", (ev) => { state.pres = ev.target.checked; render(); });
  $("#per").addEventListener("change", (ev) => { state.per = ev.target.checked; render(); });
  $("#rel").addEventListener("change", (ev) => { state.rel = ev.target.checked; render(); });
  $("#aff").addEventListener("change", (ev) => { state.aff = ev.target.checked; render(); });
  $("#chains").addEventListener("change", (ev) => { state.chains = ev.target.checked; render(); });

  // photographie à une date
  $("#date-range").addEventListener("input", (ev) => setDate(monthIso(+ev.target.value)));
  $("#date").addEventListener("change", (ev) => setDate(ev.target.value || null));
  $("#date-clear").onclick = () => setDate(null);
  $("#date-see").onclick = () => selectNone();

  // familles et natures
  const famBox = $("#families");
  [...famCount.entries()].sort((a, b) => b[1] - a[1]).forEach(([f, n]) => {
    const b = document.createElement("button");
    b.className = "chip"; b.dataset.fam = f; b.textContent = `${FAMILY_LABEL[f] || f} (${n})`;
    famBox.appendChild(b);
  });
  famBox.addEventListener("click", (ev) => {
    const b = ev.target.closest(".chip");
    if (!b) return;
    const f = b.dataset.fam;
    if (state.fam.has(f)) state.fam.delete(f); else state.fam.add(f);
    b.classList.toggle("on", state.fam.has(f));
    render();
  });
  const kindBox = $("#kinds");
  const kindCount = {};
  for (const o of orgs) kindCount[o.k] = (kindCount[o.k] || 0) + 1;
  Object.keys(KIND_LABEL).forEach((k) => {
    if (!kindCount[k]) return;
    const l = document.createElement("label");
    l.className = "check";
    l.innerHTML = `<input type="checkbox" data-kind="${k}" ${state.kinds.has(k) ? "checked" : ""}> ${esc(KIND_LABEL[k])} (${kindCount[k]})`;
    kindBox.appendChild(l);
  });
  kindBox.addEventListener("change", (ev) => {
    const k = ev.target.dataset.kind;
    if (ev.target.checked) state.kinds.add(k); else state.kinds.delete(k);
    render();
  });

  // recherche
  const q = $("#q"), res = $("#results");
  let resItems = [], resCur = -1;
  function search() {
    const s = norm(q.value.trim());
    if (s.length < 2) { res.hidden = true; return; }
    const hits = [];
    for (const o of orgs) {
      const i = o.search.indexOf(s);
      if (i >= 0) hits.push({ type: "org", o, score: (i === 0 ? 0 : 10) - Math.min(o.imp, 60) / 10 });
    }
    for (const p of people) {
      const i = p.search.indexOf(s);
      if (i >= 0) hits.push({ type: "person", p, score: (i === 0 ? 1 : 11) - Math.min(p.imp, 60) / 10 });
    }
    hits.sort((a, b) => a.score - b.score);
    resItems = hits.slice(0, 14);
    res.innerHTML = resItems.map((h, i) => h.type === "org"
      ? `<li data-i="${i}"><span>${esc(h.o.n)}</span><span class="tag">${esc(KIND_SINGLE[h.o.k] || "")}${h.o.s ? ", " + h.o.s.slice(0, 4) : ""}</span></li>`
      : `<li data-i="${i}"><span>${esc(h.p.n)}</span><span class="tag">personne${h.p.b ? ", né en " + h.p.b.slice(0, 4) : ""}</span></li>`).join("") || '<li><span class="tag">Aucun résultat</span></li>';
    res.hidden = false; resCur = -1;
  }
  function choose(i) {
    const h = resItems[i];
    if (!h) return;
    res.hidden = true; q.value = "";
    if (h.type === "org") {
      const o = h.o;
      if (o.t0 == null) { showOrg(o); return; }
      selectOrg(o.id);
    } else selectPerson(h.p.id);
  }
  q.addEventListener("input", search);
  q.addEventListener("keydown", (ev) => {
    const items = [...res.querySelectorAll("li[data-i]")];
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      resCur = (resCur + (ev.key === "ArrowDown" ? 1 : -1) + items.length) % Math.max(1, items.length);
      items.forEach((x, i) => x.classList.toggle("cur", i === resCur));
    } else if (ev.key === "Enter") choose(resCur >= 0 ? resCur : 0);
    else if (ev.key === "Escape") res.hidden = true;
  });
  res.addEventListener("mousedown", (ev) => { const li = ev.target.closest("li[data-i]"); if (li) choose(+li.dataset.i); });
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".search")) res.hidden = true; });

  let rt;
  new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(render, 120); }).observe($("#scroller"));

  // démarrage : un lien permanent restaure la vue, sinon vue par défaut
  if (!applyHash()) { showDefault(); render(); }
})();
