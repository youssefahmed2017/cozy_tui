(function () {
  var toggle = document.getElementById("themeToggle");
  var root = document.documentElement;
  function apply(theme) {
    root.setAttribute("data-theme", theme);
    if (toggle) toggle.textContent = theme === "dark" ? "🌙" : "☀️";
  }
  var stored = null;
  try { stored = localStorage.getItem("termquarium-theme"); } catch (e) {}
  if (stored) apply(stored);
  if (toggle) {
    toggle.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      apply(next);
      try { localStorage.setItem("termquarium-theme", next); } catch (e) {}
    });
  }
})();

(function () {
  var nav = document.querySelector(".nav");
  var toggle = document.getElementById("navToggle");
  if (!nav || !toggle) return;
  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.textContent = open ? "✕" : "☰";
  }
  toggle.addEventListener("click", function () {
    setOpen(!nav.classList.contains("is-open"));
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setOpen(false);
  });
  document.addEventListener("click", function (e) {
    if (nav.classList.contains("is-open") && !nav.contains(e.target)) setOpen(false);
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth > 760) setOpen(false);
  });
})();
