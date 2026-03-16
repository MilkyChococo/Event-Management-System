export const PHONE_COUNTRIES = [
  { dialCode: "+84", name: "Vietnam", flag: "vn" },
  { dialCode: "+1", name: "United States", flag: "us" },
  { dialCode: "+65", name: "Singapore", flag: "sg" },
  { dialCode: "+81", name: "Japan", flag: "jp" },
];

export const LOCATION_DIRECTORY = {
  Vietnam: {
    provinces: {
      "Ho Chi Minh City": {
        districts: {
          "District 1": ["Ben Nghe Ward", "Ben Thanh Ward", "Da Kao Ward"],
          "Go Vap District": ["Ward 1", "Ward 3", "Ward 10"],
          "Phu Nhuan District": ["Ward 7", "Ward 9", "Ward 13"],
        },
      },
      Hanoi: {
        districts: {
          "Ba Dinh District": ["Dien Bien Ward", "Kim Ma Ward", "Ngoc Ha Ward"],
          "Cau Giay District": ["Dich Vong Ward", "Nghia Tan Ward", "Yen Hoa Ward"],
          "Dong Da District": ["Cat Linh Ward", "Lang Thuong Ward", "Trung Liet Ward"],
        },
      },
      "Da Nang": {
        districts: {
          "Hai Chau District": ["Binh Hien Ward", "Hoa Cuong Bac Ward", "Thach Thang Ward"],
          "Lien Chieu District": ["Hoa Khanh Bac Ward", "Hoa Minh Ward", "Hoa Hiep Nam Ward"],
          "Son Tra District": ["An Hai Bac Ward", "Man Thai Ward", "Phuoc My Ward"],
        },
      },
    },
  },
  "United States": {
    provinces: {
      California: {
        districts: {
          "San Francisco County": ["Mission District", "Sunset District", "SoMa"],
          "Santa Clara County": ["Cupertino", "San Jose", "Sunnyvale"],
        },
      },
      "New York": {
        districts: {
          "Kings County": ["Brooklyn Heights", "Park Slope", "Williamsburg"],
          "New York County": ["Chelsea", "Harlem", "Lower East Side"],
        },
      },
      Washington: {
        districts: {
          "King County": ["Bellevue", "Capitol Hill", "Redmond"],
          "Pierce County": ["Lakewood", "Tacoma", "University Place"],
        },
      },
    },
  },
  Singapore: {
    provinces: {
      "Central Region": {
        districts: {
          Orchard: ["Cairnhill", "Paterson", "Somerset"],
          "Downtown Core": ["Marina Centre", "Raffles Place", "Shenton Way"],
          "River Valley": ["Havelock", "Kim Seng", "Robertson Quay"],
        },
      },
      "East Region": {
        districts: {
          Bedok: ["Bedok Central", "Fengshan", "Kaki Bukit"],
          PasirRis: ["Elias", "Loyang", "Pasir Ris Central"],
          Tampines: ["Simei", "Tampines Central", "Tampines North"],
        },
      },
      "North-East Region": {
        districts: {
          Hougang: ["Kovan", "Lorong Ah Soo", "Punggol Park"],
          Sengkang: ["Anchorvale", "Compassvale", "Fernvale"],
          Serangoon: ["Lorong Chuan", "Serangoon Garden", "Serangoon North"],
        },
      },
    },
  },
  Japan: {
    provinces: {
      Tokyo: {
        districts: {
          Shibuya: ["Daikanyama", "Ebisu", "Harajuku"],
          Shinjuku: ["Kabukicho", "Nishi-Shinjuku", "Takadanobaba"],
          Taito: ["Asakusa", "Kuramae", "Ueno"],
        },
      },
      Osaka: {
        districts: {
          Kita: ["Nakazakicho", "Ogimachi", "Umeda"],
          Naniwa: ["Daikokucho", "Namba", "Shinsekai"],
          Tennoji: ["Abeno", "Shitennoji", "Uehonmachi"],
        },
      },
      Kyoto: {
        districts: {
          "Fushimi Ward": ["Momoyama", "Takeda", "Uji Riverfront"],
          "Nakagyo Ward": ["Karasuma", "Kawaramachi", "Nijo"],
          "Sakyo Ward": ["Demachiyanagi", "Ginkakuji", "Shugakuin"],
        },
      },
    },
  },
};

export const DEFAULT_COUNTRY = "Vietnam";
export const DEFAULT_PROVINCE = "Ho Chi Minh City";
export const DEFAULT_DISTRICT = "Go Vap District";
export const DEFAULT_WARD = "Ward 3";
export const DEFAULT_PHONE_DIAL_CODE = "+84";

export function getCountryNames() {
  return Object.keys(LOCATION_DIRECTORY);
}

export function getProvinces(country) {
  return Object.keys(LOCATION_DIRECTORY[country]?.provinces || {});
}

export function getDistricts(country, province) {
  return Object.keys(LOCATION_DIRECTORY[country]?.provinces?.[province]?.districts || {});
}

export function getWards(country, province, district) {
  return LOCATION_DIRECTORY[country]?.provinces?.[province]?.districts?.[district] || [];
}

export function getPhoneCountryByCode(dialCode) {
  return PHONE_COUNTRIES.find((country) => country.dialCode === dialCode) || PHONE_COUNTRIES[0];
}

export function buildPermanentAddress({ street_address, ward, district, province, country }) {
  return [street_address, ward, district, province, country].filter(Boolean).join(", ");
}
