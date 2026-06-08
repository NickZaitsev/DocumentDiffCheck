const topbar = document.querySelector(".topbar");
const navToggle = document.querySelector("[data-nav-toggle]");
const menuPanel = document.querySelector("#primaryNav");
const mobileNavQuery = window.matchMedia("(max-width: 860px)");

if (topbar && navToggle && menuPanel) {
  const setOpen = (open) => {
    topbar.classList.toggle("nav-open", open);
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
  };

  const isOpen = () => topbar.classList.contains("nav-open");

  navToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    setOpen(!topbar.classList.contains("nav-open"));
  });

  menuPanel.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  menuPanel.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      if (mobileNavQuery.matches) {
        setOpen(false);
      }
    });
  });

  window.addEventListener("resize", () => {
    if (!mobileNavQuery.matches) {
      setOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setOpen(false);
    }
  });

  document.addEventListener("click", () => {
    if (isOpen() && mobileNavQuery.matches) {
      setOpen(false);
    }
  });
}
