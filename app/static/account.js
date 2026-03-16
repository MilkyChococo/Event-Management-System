import { getCurrentUser, redirectTo, setupAccountMenu } from "/static/shared.js";

const profileName = document.querySelector("[data-testid='profile-name']");
const profileEmail = document.querySelector("#profile-email");
const profileRole = document.querySelector("#profile-role");
const profileAvatar = document.querySelector("[data-testid='profile-avatar']");
const profileNameField = document.querySelector("#profile-name-field");
const profileAge = document.querySelector("#profile-age");
const profileDateOfBirth = document.querySelector("#profile-date-of-birth");
const profilePhoneFlag = document.querySelector("#profile-phone-flag");
const profilePhoneRegion = document.querySelector("#profile-phone-region");
const profilePhone = document.querySelector("#profile-phone");
const profileCountry = document.querySelector("#profile-country");
const profileProvince = document.querySelector("#profile-province");
const profileDistrict = document.querySelector("#profile-district");
const profileWard = document.querySelector("#profile-ward");
const profileStreetAddress = document.querySelector("#profile-street-address");
const profileAddress = document.querySelector("#profile-address");

function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    redirectTo("/");
    return;
  }

  setupAccountMenu(user);
  profileName.textContent = user.name;
  profileEmail.textContent = user.email;
  profileRole.textContent = user.role;
  profileAvatar.textContent = initials(user.name);
  profileNameField.textContent = user.name;
  profileAge.textContent = String(user.age);
  profileDateOfBirth.textContent = user.date_of_birth;
  profilePhoneFlag.className = `flag-badge flag-${user.phone_country_flag || "vn"}`;
  profilePhoneRegion.textContent = `${user.phone_country_code} ${user.phone_country_label}`;
  profilePhone.textContent = user.phone_number;
  profileCountry.textContent = user.country;
  profileProvince.textContent = user.province;
  profileDistrict.textContent = user.district;
  profileWard.textContent = user.ward || "Not specified";
  profileStreetAddress.textContent = user.street_address;
  profileAddress.textContent = user.permanent_address;
}

boot();
