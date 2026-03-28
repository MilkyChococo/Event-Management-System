import {
  api,
  getCurrentUser,
  redirectTo,
  renderUserAvatar,
  setupAccountMenu,
  setupGlobalFooter,
  showToast,
} from "/static/shared.js?v=20260328-notification-reminder-cta";

const profileAvatar = document.querySelector("[data-testid='profile-avatar']");
const profileRole = document.querySelector("#profile-role");
const securityHeroCopy = document.querySelector("#security-hero-copy");
const securityForm = document.querySelector("#security-form");

const state = {
  user: null,
};

function populateHero(user) {
  renderUserAvatar(profileAvatar, user, "profile-avatar-image");
  if (profileRole) {
    profileRole.textContent = user.role;
  }
  if (securityHeroCopy) {
    securityHeroCopy.textContent = `${user.name} · ${user.email}`;
  }
  setupAccountMenu(user);
  setupGlobalFooter(user);
}

async function handleSecuritySubmit(event) {
  event.preventDefault();
  const currentPasswordField = document.querySelector("#security-current-password");
  const newPasswordField = document.querySelector("#security-new-password");
  const updatedUser = await api("/api/me/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPasswordField.value,
      new_password: newPasswordField.value,
    }),
  });
  state.user = updatedUser;
  populateHero(updatedUser);
  securityForm?.reset();
  showToast("Password updated successfully.");
}

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    redirectTo("/");
    return;
  }

  state.user = user;
  populateHero(user);

  securityForm?.addEventListener("submit", async (event) => {
    try {
      await handleSecuritySubmit(event);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
}

boot();

