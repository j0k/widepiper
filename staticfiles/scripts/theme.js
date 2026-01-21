const themeBtn = document.getElementById('theme-btn');

const darkImages = {
  theme_btn: "/static/img/moon.svg"
};

const lightImages = {
  theme_btn: "/static/img/sun.svg"
};

function calculateSettingAsThemeString({ localStorageTheme, systemSettingDark }) {
  if (localStorageTheme !== null) {
    return localStorageTheme;
  }

  if (systemSettingDark.matches) {
    localStorage.setItem('theme', 'dark');
    return "dark";
  }
  localStorage.setItem('theme', 'light');
  return "light";
}

const localStorageTheme = localStorage.getItem("theme");
const systemSettingDark = window.matchMedia("(prefers-color-scheme: dark)");

let currentThemeSetting = calculateSettingAsThemeString({ localStorageTheme, systemSettingDark });


const button = document.getElementById('theme-btn');

button.addEventListener("click", () => {
  const newTheme = currentThemeSetting === "dark" ? "light" : "dark";

  document.querySelector("html").setAttribute("class", newTheme);
  updateImages(newTheme);
  localStorage.setItem("theme", newTheme);

  currentThemeSetting = newTheme;
});


function updateImages(theme) {
  const images = theme === 'dark' ? darkImages : lightImages;

  Object.keys(images).forEach(key => {
    const elem = document.getElementById(key);
    if (elem) {
      elem.src = images[key];
    }
  });
};




