import { getCurrentUser, setupAccountMenu, setupGlobalFooter } from "/static/shared.js?v=20260317-global-footer-routes";

const welcomeText = document.querySelector("#welcome-text");
const roleChip = document.querySelector("#about-role-chip");
const signInLink = document.querySelector("#about-signin-link");
const accountAnchor = document.querySelector("#about-account-anchor");
const adminTopbarNav = document.querySelector("#admin-topbar-nav");

function toTitleCase(value) {
  if (!value) {
    return "";
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    signInLink?.classList.remove("hidden");
    welcomeText.textContent = "About EventHub Verify";
    return;
  }

  accountAnchor?.classList.remove("hidden");
  roleChip?.classList.remove("hidden");
  roleChip.textContent = toTitleCase(user.role);
  welcomeText.textContent = `Welcome, ${user.name}`;
  setupAccountMenu(user);
  setupGlobalFooter(user);

  if (user.role === "admin") {
    adminTopbarNav?.classList.remove("hidden");
  }
}

boot();
