import {
  api,
  getCurrentUser,
  redirectTo,
  renderUserAvatar,
  setupAccountMenu,
  setupGlobalFooter,
  showToast,
} from "/static/shared.js?v=20260406-contact-stack-fab";

const profileAvatar = document.querySelector("[data-testid='profile-avatar']");
const profileRole = document.querySelector("#profile-role");
const securityHeroCopy = document.querySelector("#security-hero-copy");
const changePasswordTrigger = document.querySelector("#security-change-password-link");
const passwordModal = document.querySelector("#security-password-modal");
const passwordModalClose = document.querySelector("#security-password-close");
const passwordModalCancel = document.querySelector("#security-password-cancel");
const passwordForm = document.querySelector("#security-password-form");
const currentPasswordField = document.querySelector("#security-current-password");
const newPasswordField = document.querySelector("#security-new-password");
const confirmModal = document.querySelector("#security-password-confirm-modal");
const confirmModalClose = document.querySelector("#security-password-confirm-close");
const confirmModalCancel = document.querySelector("#security-password-confirm-cancel");
const confirmModalGo = document.querySelector("#security-password-confirm-go");

function populateHero(user) {
  renderUserAvatar(profileAvatar, user, "profile-avatar-image");
  if (profileRole) {
    profileRole.textContent = user.role;
  }
  if (securityHeroCopy) {
    securityHeroCopy.textContent = `${user.name} - ${user.email}`;
  }
  setupAccountMenu(user);
  setupGlobalFooter(user);
}

function syncModalLock() {
  const hasOpenModal = Boolean(document.querySelector(".admin-modal:not(.hidden)"));
  document.body.classList.toggle("modal-open", hasOpenModal);
}

function openPasswordModal() {
  if (!(passwordModal instanceof HTMLElement)) {
    return;
  }
  passwordModal.classList.remove("hidden");
  passwordModal.setAttribute("aria-hidden", "false");
  syncModalLock();
  window.setTimeout(() => {
    currentPasswordField?.focus();
  }, 50);
}

function closeConfirmModal(syncLock = true) {
  if (!(confirmModal instanceof HTMLElement)) {
    return;
  }
  confirmModal.classList.add("hidden");
  confirmModal.setAttribute("aria-hidden", "true");
  if (syncLock) {
    syncModalLock();
  }
}

function closePasswordModal(reset = false) {
  if (!(passwordModal instanceof HTMLElement)) {
    return;
  }
  passwordModal.classList.add("hidden");
  passwordModal.setAttribute("aria-hidden", "true");
  closeConfirmModal(false);
  if (reset) {
    passwordForm?.reset();
  }
  syncModalLock();
}

function openConfirmModal() {
  if (!(confirmModal instanceof HTMLElement)) {
    return;
  }
  confirmModal.classList.remove("hidden");
  confirmModal.setAttribute("aria-hidden", "false");
  syncModalLock();
  window.setTimeout(() => {
    confirmModalGo?.focus();
  }, 50);
}

function validatePasswordForm() {
  if (!(passwordForm instanceof HTMLFormElement)) {
    return false;
  }
  return passwordForm.reportValidity();
}

async function submitPasswordChange() {
  if (!(currentPasswordField instanceof HTMLInputElement) || !(newPasswordField instanceof HTMLInputElement)) {
    return;
  }
  await api("/api/me/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPasswordField.value.trim(),
      new_password: newPasswordField.value.trim(),
    }),
  });
  closeConfirmModal(false);
  closePasswordModal(true);
  showToast("Password updated successfully.");
}

function bindSecurityModals() {
  changePasswordTrigger?.addEventListener("click", openPasswordModal);

  passwordModalClose?.addEventListener("click", () => closePasswordModal(true));
  passwordModalCancel?.addEventListener("click", () => closePasswordModal(true));
  passwordForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!validatePasswordForm()) {
      return;
    }
    openConfirmModal();
  });

  confirmModalClose?.addEventListener("click", () => closeConfirmModal());
  confirmModalCancel?.addEventListener("click", () => closeConfirmModal());
  confirmModalGo?.addEventListener("click", async () => {
    try {
      await submitPasswordChange();
    } catch (error) {
      closeConfirmModal(false);
      syncModalLock();
      showToast(error.message, "error");
    }
  });

  passwordModal?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.dataset.securityPasswordAction === "close") {
      closePasswordModal(true);
    }
  });

  confirmModal?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.dataset.securityConfirmAction === "close") {
      closeConfirmModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    if (!confirmModal?.classList.contains("hidden")) {
      closeConfirmModal();
      return;
    }
    if (!passwordModal?.classList.contains("hidden")) {
      closePasswordModal(true);
    }
  });
}

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    redirectTo("/");
    return;
  }

  populateHero(user);
  bindSecurityModals();
}

boot();

