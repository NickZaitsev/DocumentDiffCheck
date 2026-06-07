const topbar = document.querySelector(".topbar");
const navToggle = document.querySelector("[data-nav-toggle]");
const primaryNav = document.querySelector("#primaryNav");

if (topbar && navToggle && primaryNav) {
  const setOpen = (open) => {
    topbar.classList.toggle("nav-open", open);
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
  };

  navToggle.addEventListener("click", () => {
    setOpen(!topbar.classList.contains("nav-open"));
  });

  primaryNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.matchMedia("(max-width: 560px)").matches) {
        setOpen(false);
      }
    });
  });

  window.addEventListener("resize", () => {
    if (!window.matchMedia("(max-width: 560px)").matches) {
      setOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setOpen(false);
    }
  });
}
