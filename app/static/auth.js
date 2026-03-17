import { api, clearNotice, getCurrentUser, redirectTo, showNotice } from "/static/shared.js?v=20260317-account-avatar-modal";
import {
  DEFAULT_COUNTRY,
  DEFAULT_DISTRICT,
  DEFAULT_PHONE_DIAL_CODE,
  DEFAULT_PROVINCE,
  DEFAULT_WARD,
  PHONE_COUNTRIES,
  getCountryNames,
  getDistricts,
  getPhoneCountryByCode,
  getProvinces,
  getWards,
} from "/static/location-data.js";

const messageBox = document.querySelector("[data-testid='auth-message']");
const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");
const forgotForm = document.querySelector("#forgot-form");
const tabButtons = document.querySelectorAll("[data-tab-target]");
const tabPanels = document.querySelectorAll("[data-tab-panel]");
const authHeading = document.querySelector("#auth-heading");
const loginEmail = document.querySelector("#login-email");
const loginPassword = document.querySelector("#login-password");
const loginInlineError = document.querySelector("[data-testid='login-inline-error']");
const registerCountry = document.querySelector("#register-country");
const registerProvince = document.querySelector("#register-province");
const registerDistrict = document.querySelector("#register-district");
const registerWard = document.querySelector("#register-ward");
const registerPhoneCountry = document.querySelector("#register-phone-country");
const registerPhoneFlag = document.querySelector("#register-phone-flag");

function fillSelect(select, values, preferredValue = "") {
  if (!select) {
    return;
  }
  select.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join("");
  if (!values.length) {
    return;
  }
  const nextValue = values.includes(preferredValue) ? preferredValue : values[0];
  select.value = nextValue;
}

function syncWardOptions(preferredValue = "") {
  const wards = getWards(registerCountry.value, registerProvince.value, registerDistrict.value);
  fillSelect(registerWard, wards, preferredValue || DEFAULT_WARD);
}

function syncDistrictOptions(preferredValue = "") {
  const districts = getDistricts(registerCountry.value, registerProvince.value);
  fillSelect(registerDistrict, districts, preferredValue || DEFAULT_DISTRICT);
  syncWardOptions();
}

function syncProvinceOptions(preferredValue = "") {
  const provinces = getProvinces(registerCountry.value);
  fillSelect(registerProvince, provinces, preferredValue || DEFAULT_PROVINCE);
  syncDistrictOptions();
}

function syncPhoneCountryPreview() {
  const selectedPhoneCountry = getPhoneCountryByCode(registerPhoneCountry.value);
  registerPhoneFlag.className = `flag-badge flag-${selectedPhoneCountry.flag}`;
  registerPhoneFlag.setAttribute("aria-label", selectedPhoneCountry.name);
}

function initializeRegisterLocationControls() {
  fillSelect(registerCountry, getCountryNames(), DEFAULT_COUNTRY);
  syncProvinceOptions();

  registerCountry.addEventListener("change", () => syncProvinceOptions());
  registerProvince.addEventListener("change", () => syncDistrictOptions());
  registerDistrict.addEventListener("change", () => syncWardOptions());

  registerPhoneCountry.innerHTML = PHONE_COUNTRIES.map(
    (country) => `<option value="${country.dialCode}">${country.dialCode} ${country.name}</option>`
  ).join("");
  registerPhoneCountry.value = DEFAULT_PHONE_DIAL_CODE;
  syncPhoneCountryPreview();
  registerPhoneCountry.addEventListener("change", syncPhoneCountryPreview);
}

function resetRegisterLocationControls() {
  fillSelect(registerCountry, getCountryNames(), DEFAULT_COUNTRY);
  syncProvinceOptions(DEFAULT_PROVINCE);
  syncDistrictOptions(DEFAULT_DISTRICT);
  syncWardOptions(DEFAULT_WARD);
  registerPhoneCountry.value = DEFAULT_PHONE_DIAL_CODE;
  syncPhoneCountryPreview();
}

function showLoginError(message) {
  if (!loginInlineError) {
    return;
  }
  loginInlineError.textContent = message;
  loginInlineError.className = "inline-error";
}

function clearLoginError() {
  if (!loginInlineError) {
    return;
  }
  loginInlineError.textContent = "";
  loginInlineError.className = "inline-error hidden";
}

function setActiveTab(targetId) {
  const headingByPanel = {
    "login-panel": "Sign in",
    "register-panel": "Register",
    "forgot-panel": "Forgot password",
  };

  tabPanels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === targetId);
  });
  if (authHeading) {
    authHeading.textContent = headingByPanel[targetId] || "Sign in";
  }
  clearNotice(messageBox);
  clearLoginError();
}

async function handleLogin(event) {
  event.preventDefault();
  clearNotice(messageBox);
  clearLoginError();

  const password = loginPassword.value.trim();
  if (password.length < 8) {
    showLoginError("Password must be at least 8 characters.");
    return;
  }

  try {
    await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: loginEmail.value.trim(),
        password,
      }),
    });
    redirectTo("/dashboard");
  } catch (error) {
    showLoginError(error.message);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  clearNotice(messageBox);
  clearLoginError();
  const selectedPhoneCountry = getPhoneCountryByCode(registerPhoneCountry.value);

  try {
    await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: document.querySelector("#register-name").value,
        date_of_birth: document.querySelector("#register-date-of-birth").value,
        country: registerCountry.value,
        province: registerProvince.value,
        district: registerDistrict.value,
        ward: registerWard.value,
        street_address: document.querySelector("#register-street-address").value,
        phone_country_code: selectedPhoneCountry.dialCode,
        phone_country_label: selectedPhoneCountry.name,
        phone_country_flag: selectedPhoneCountry.flag,
        phone_local_number: document.querySelector("#register-phone-local").value,
        email: document.querySelector("#register-email").value,
        password: document.querySelector("#register-password").value,
      }),
    });
    registerForm.reset();
    resetRegisterLocationControls();
    setActiveTab("login-panel");
    showNotice(messageBox, "Registration completed. You can sign in now.");
  } catch (error) {
    showNotice(messageBox, error.message, "error");
  }
}

async function handleForgotPassword(event) {
  event.preventDefault();
  clearNotice(messageBox);
  clearLoginError();
  try {
    await api("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({
        email: document.querySelector("#forgot-email").value,
        date_of_birth: document.querySelector("#forgot-date-of-birth").value,
        new_password: document.querySelector("#forgot-password").value,
      }),
    });
    forgotForm.reset();
    setActiveTab("login-panel");
    showNotice(messageBox, "Password updated. Please sign in again.");
  } catch (error) {
    showNotice(messageBox, error.message, "error");
  }
}

async function boot() {
  const user = await getCurrentUser();
  if (user) {
    redirectTo("/dashboard");
    return;
  }

  initializeRegisterLocationControls();
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tabTarget));
  });
  loginEmail.addEventListener("input", clearLoginError);
  loginPassword.addEventListener("input", clearLoginError);
  loginForm.addEventListener("submit", handleLogin);
  registerForm.addEventListener("submit", handleRegister);
  forgotForm.addEventListener("submit", handleForgotPassword);
}

boot();
