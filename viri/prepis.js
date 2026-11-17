// Bitni pogovori: prepisi. Stran deluje tudi brez te datoteke (prepis je
// navaden HTML); tu so samo sledenje predvajanju in iskanje.
(function () {
	"use strict";

	function brezStresic(niz) {
		return niz.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
	}
	function besede(niz) {
		return brezStresic(niz).match(/[a-z0-9]{2,}/g) || [];
	}
	function cas(s) {
		s = Math.floor(s);
		var m = Math.floor(s / 60) % 60, h = Math.floor(s / 3600), sek = ("0" + (s % 60)).slice(-2);
		return h ? h + ":" + ("0" + m).slice(-2) + ":" + sek : m + ":" + sek;
	}
	// Slovenska števila: 1 odstavek, 2 odstavka, 3 odstavki, 5 odstavkov.
	function stevilo(n, oblike) {
		var o = n % 100;
		return n + " " + (o === 1 ? oblike[0] : o === 2 ? oblike[1] : o === 3 || o === 4 ? oblike[2] : oblike[3]);
	}
	function oznaci(besedilo, iskano) {
		var mali = brezStresic(besedilo), mesta = [];
		iskano.forEach(function (b) {
			var i = -1;
			while ((i = mali.indexOf(b, i + 1)) !== -1) mesta.push([i, i + b.length]);
		});
		mesta.sort(function (a, b) { return a[0] - b[0]; });
		var html = "", zadnji = 0;
		mesta.forEach(function (m) {
			if (m[0] < zadnji) return;
			html += ubezi(besedilo.slice(zadnji, m[0])) + "<mark>" + ubezi(besedilo.slice(m[0], m[1])) + "</mark>";
			zadnji = m[1];
		});
		return html + ubezi(besedilo.slice(zadnji));
	}
	function ubezi(niz) {
		return niz.replace(/[&<>"]/g, function (z) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[z]; });
	}

	// ---------- stran epizode ----------
	// Opozorilo o strojnem prepisu se da skriti; izbira si jo brskalnik zapomni.
	var opozorilo = document.querySelector("[data-opozorilo]");
	if (opozorilo) {
		var skrito = false;
		try { skrito = localStorage.getItem("prepis-opozorilo") === "skrito"; } catch (e) {}
		if (skrito) opozorilo.hidden = true;
		var gumbSkrij = opozorilo.querySelector("button");
		gumbSkrij.hidden = false;
		gumbSkrij.addEventListener("click", function () {
			opozorilo.hidden = true;
			try { localStorage.setItem("prepis-opozorilo", "skrito"); } catch (e) {}
		});
	}
	var prepis = document.querySelector("[data-prepis]");
	var zvok = document.querySelector(".predvajalnik audio");
	if (prepis && zvok) {
		var odstavki = Array.prototype.slice.call(prepis.querySelectorAll("p[data-z]"));
		var sledi = prepis.querySelector("[data-sledi]");
		var trenutni = null;
		prepis.querySelector(".prepis-orodja").hidden = false;

		zvok.addEventListener("timeupdate", function () {
			var t = zvok.currentTime, nov = null;
			for (var i = 0; i < odstavki.length; i++) {
				if (Number(odstavki[i].dataset.z) <= t) nov = odstavki[i]; else break;
			}
			if (nov === trenutni) return;
			if (trenutni) trenutni.classList.remove("zdaj");
			trenutni = nov;
			if (!nov) return;
			nov.classList.add("zdaj");
			var odprt = !prepis.closest("details") || prepis.closest("details").open;
			if (sledi && sledi.checked && odprt && !zvok.paused) {
				nov.scrollIntoView({ block: "center", behavior: "smooth" });
			}
		});

		// Iskanje znotraj prepisa: skrije neujemajoče odstavke in označi zadetke.
		var polje = prepis.querySelector(".prepis-iskanje");
		var stevec = prepis.querySelector(".prepis-stevec");
		odstavki.forEach(function (p) { p.dataset.html = p.querySelector(".t").innerHTML; });
		polje.addEventListener("input", function () {
			var iskano = besede(polje.value);
			var zadetkov = 0;
			odstavki.forEach(function (p) {
				var t = p.querySelector(".t");
				t.innerHTML = p.dataset.html;
				if (!iskano.length) { p.hidden = false; return; }
				var besedilo = brezStresic(t.textContent);
				var ujema = iskano.every(function (b) { return besedilo.indexOf(b) !== -1; });
				p.hidden = !ujema;
				if (!ujema) return;
				zadetkov += 1;
				t.innerHTML = oznaci(t.textContent, iskano);
			});
			stevec.textContent = iskano.length ? stevilo(zadetkov, ["odstavek", "odstavka", "odstavki", "odstavkov"]) : "";
		});

		// Prihod z iskanja (?t=…&q=…): odpri prepis in pokaži mesto.
		var parametri = new URLSearchParams(location.search);
		if (parametri.get("t") && prepis.closest("details")) {
			prepis.closest("details").open = true;
			var t0 = Number(parametri.get("t"));
			var cilj = odstavki.filter(function (p) { return Number(p.dataset.z) <= t0; }).pop();
			if (cilj) {
				cilj.classList.add("zdaj");
				trenutni = cilj;
				setTimeout(function () { cilj.scrollIntoView({ block: "center" }); }, 50);
			}
		}
	}

	// ---------- iskanje po vseh prepisih (seznam epizod) ----------
	var vnos = document.querySelector("[data-seznam-epizod]") && document.querySelector(".iskanje");
	if (!vnos) return;
	var izid = document.createElement("section");
	izid.className = "prepisi-zadetki";
	izid.hidden = true;
	var seznam = document.querySelector("[data-seznam-epizod]");
	seznam.parentNode.insertBefore(izid, seznam);

	var epizode = null, kosi = {}, besedila = {}, cakam = null;
	function nalozi(pot) {
		return fetch(pot).then(function (o) { if (!o.ok) throw new Error(pot); return o.json(); });
	}
	function kos(beseda) {
		var kljuc = beseda.slice(0, 2);
		if (!kosi[kljuc]) kosi[kljuc] = nalozi("/prepisi/kazalo/" + kljuc + ".json").catch(function () { return {}; });
		return kosi[kljuc];
	}
	// Vrne {epizoda: {odstavek: true}} za besedo; zadnja beseda se ujema tudi kot začetek.
	function zadetki(beseda, predpona) {
		return kos(beseda).then(function (k) {
			var izhod = {};
			Object.keys(k).forEach(function (b) {
				if (b !== beseda && !(predpona && b.indexOf(beseda) === 0)) return;
				k[b].split(";").forEach(function (del) {
					var d = del.split(":"), e = d[0];
					izhod[e] = izhod[e] || {};
					d[1].split(",").forEach(function (o) { izhod[e][o] = true; });
				});
			});
			return izhod;
		});
	}
	function besedilo(oznaka) {
		if (!besedila[oznaka]) besedila[oznaka] = nalozi("/prepisi/" + oznaka + ".json");
		return besedila[oznaka];
	}
	function isci() {
		var iskano = besede(vnos.value);
		if (!iskano.length || iskano.join("").length < 3) { izid.hidden = true; return; }
		var poizvedba = vnos.value;
		(epizode ? Promise.resolve(epizode) : nalozi("/prepisi/kazalo/epizode.json").then(function (e) { epizode = e; return e; }))
			.then(function () {
				return Promise.all(iskano.map(function (b, i) { return zadetki(b, i === iskano.length - 1); }));
			})
			.then(function (vsi) {
				if (poizvedba !== vnos.value) return;
				// Odstavki, ki vsebujejo vse besede.
				var rezultat = [];
				Object.keys(vsi[0]).forEach(function (e) {
					var skupni = Object.keys(vsi[0][e]).filter(function (o) {
						return vsi.every(function (z) { return z[e] && z[e][o]; });
					});
					if (skupni.length) rezultat.push([e, skupni.map(Number).sort(function (a, b) { return a - b; })]);
				});
				rezultat.sort(function (a, b) { return b[1].length - a[1].length; });
				izris(rezultat, iskano);
			});
	}
	function izris(rezultat, iskano) {
		izid.hidden = false;
		if (!rezultat.length) {
			izid.innerHTML = '<h2>V prepisih</h2><p class="tiho">Ni zadetkov v prepisih.</p>';
			return;
		}
		var vseh = rezultat.reduce(function (s, r) { return s + r[1].length; }, 0);
		izid.innerHTML = "<h2>V prepisih</h2><p class=\"tiho\">" + stevilo(vseh, ["mesto", "mesti", "mesta", "mest"]) +
			" v " + stevilo(rezultat.length, ["epizodi", "epizodah", "epizodah", "epizodah"]) + "</p><ol></ol>";
		var ol = izid.querySelector("ol");
		rezultat.slice(0, 20).forEach(function (r) {
			var e = epizode[r[0]];
			var li = document.createElement("li");
			li.innerHTML = '<a class="naslov" href="/' + ubezi(e[0]) + '">' + ubezi(e[1]) + "</a><ul></ul>";
			ol.appendChild(li);
			besedilo(e[0]).then(function (p) {
				var ul = li.querySelector("ul");
				r[1].slice(0, 3).forEach(function (i) {
					var o = p.odstavki[i];
					if (!o) return;
					var t = o.t, mali = brezStresic(t), m = mali.indexOf(iskano[0]);
					var od = Math.max(0, m - 80), izsek = (od ? "…" : "") + t.slice(od, od + 220) + (t.length > od + 220 ? "…" : "");
					var item = document.createElement("li");
					item.innerHTML = '<a href="/' + ubezi(e[0]) + "?t=" + Math.floor(o.z) + '"><span class="tiho">' +
						cas(o.z) + " · " + ubezi(o.ime) + "</span> " + oznaci(izsek, iskano) + "</a>";
					ul.appendChild(item);
				});
				if (r[1].length > 3) {
					var vec = document.createElement("li");
					vec.className = "tiho";
					vec.textContent = "in še " + stevilo(r[1].length - 3, ["mesto", "mesti", "mesta", "mest"]);
					ul.appendChild(vec);
				}
			});
		});
	}
	vnos.addEventListener("input", function () {
		clearTimeout(cakam);
		cakam = setTimeout(isci, 250);
	});
})();
