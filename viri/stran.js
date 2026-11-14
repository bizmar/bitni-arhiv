// Bitni pogovori: arhiv. Stran deluje tudi brez te datoteke; tu so samo dodatki.
(function () {
	"use strict";

	function shrani(kljuc, vrednost) {
		try { localStorage.setItem(kljuc, vrednost); } catch (e) { /* zasebno okno */ }
	}
	function preberi(kljuc) {
		try { return localStorage.getItem(kljuc); } catch (e) { return null; }
	}

	// Predvajalnik: hitrost, preskoki, zapomni si položaj.
	document.querySelectorAll(".predvajalnik").forEach(function (ovoj) {
		var zvok = ovoj.querySelector("audio");
		var dodatki = ovoj.querySelector(".dodatki");
		if (!zvok || !dodatki) return;
		dodatki.hidden = false;
		var kljuc = "polozaj:" + ovoj.dataset.oznaka;
		var hitrosti = [1, 1.25, 1.5, 2];
		var gumbHitrost = dodatki.querySelector("[data-hitrost]");

		zvok.addEventListener("loadedmetadata", function () {
			var zacetek = Number(new URLSearchParams(location.search).get("t")) || Number(preberi(kljuc)) || 0;
			if (zacetek > 0 && zacetek < zvok.duration - 5) zvok.currentTime = zacetek;
			zvok.playbackRate = Number(preberi("hitrost")) || 1;
			if (gumbHitrost) gumbHitrost.textContent = zvok.playbackRate + "×";
		});
		zvok.addEventListener("timeupdate", function () {
			if (Math.floor(zvok.currentTime) % 5 === 0) shrani(kljuc, String(Math.floor(zvok.currentTime)));
		});
		dodatki.addEventListener("click", function (dogodek) {
			var gumb = dogodek.target.closest("button");
			if (!gumb) return;
			if (gumb.dataset.skok) zvok.currentTime = Math.max(0, zvok.currentTime + Number(gumb.dataset.skok));
			if (gumb === gumbHitrost) {
				var naslednja = hitrosti[(hitrosti.indexOf(zvok.playbackRate) + 1) % hitrosti.length];
				zvok.playbackRate = naslednja;
				gumb.textContent = naslednja + "×";
				shrani("hitrost", String(naslednja));
			}
		});
		// Poglavja: klik skoči na čas.
		document.querySelectorAll("[data-cas]").forEach(function (povezava) {
			povezava.addEventListener("click", function (dogodek) {
				dogodek.preventDefault();
				zvok.currentTime = Number(povezava.dataset.cas);
				zvok.play();
			});
		});
	});

	// Seznam epizod: iskanje in filter po osebah.
	var seznam = document.querySelector("[data-seznam-epizod]");
	if (!seznam) return;
	var polje = document.querySelector(".iskanje");
	var stevec = document.querySelector(".stevec");
	var vrstice = Array.prototype.slice.call(seznam.querySelectorAll(".vrstica"));
	var gumbi = Array.prototype.slice.call(document.querySelectorAll("[data-oseba]"));
	var opombe = null; // celotno besedilo opomb, naloži se ob prvem iskanju
	var izbrana = new URLSearchParams(location.search).get("oseba") || "";
	document.querySelector(".filtri-ovoj").hidden = false;

	function brezStresic(niz) {
		return niz.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
	}
	function osvezi() {
		var iskano = brezStresic(polje.value.trim());
		var vidnih = 0;
		vrstice.forEach(function (v) {
			var besedilo = brezStresic(v.textContent) + " " + (opombe ? opombe[v.dataset.oznaka] || "" : "");
			var ujema = (!iskano || besedilo.indexOf(iskano) !== -1) &&
				(!izbrana || (" " + v.dataset.osebe + " ").indexOf(" " + izbrana + " ") !== -1);
			v.hidden = !ujema;
			if (ujema) vidnih += 1;
		});
		document.querySelectorAll("[data-obdobje]").forEach(function (o) {
			o.hidden = !o.querySelector(".vrstica:not([hidden])");
		});
		gumbi.forEach(function (g) { g.setAttribute("aria-pressed", String(g.dataset.oseba === izbrana)); });
		stevec.textContent = vidnih === vrstice.length ? "Vseh " + vidnih + " epizod" : "Prikazanih " + vidnih + " od " + vrstice.length;
	}
	polje.addEventListener("focus", function () {
		if (opombe) return;
		opombe = {};
		fetch("/iskanje.json").then(function (o) { return o.json(); }).then(function (podatki) {
			opombe = podatki;
			osvezi();
		}).catch(function () { /* iskanje po naslovih deluje naprej */ });
	});
	polje.addEventListener("input", osvezi);
	gumbi.forEach(function (g) {
		g.addEventListener("click", function () {
			izbrana = izbrana === g.dataset.oseba ? "" : g.dataset.oseba;
			history.replaceState(null, "", izbrana ? "?oseba=" + izbrana : location.pathname);
			osvezi();
		});
	});
	osvezi();
})();
