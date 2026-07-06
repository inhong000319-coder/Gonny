const ACCESS_TOKEN_KEY = "gonny:access-token";
const REFRESH_TOKEN_KEY = "gonny:refresh-token";

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function getAccessToken() {
  return getStorage()?.getItem(ACCESS_TOKEN_KEY) ?? null;
}

export function saveAccessToken(token: string) {
  getStorage()?.setItem(ACCESS_TOKEN_KEY, token);
}

export function removeAccessToken() {
  getStorage()?.removeItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return getStorage()?.getItem(REFRESH_TOKEN_KEY) ?? null;
}

export function saveRefreshToken(token: string) {
  getStorage()?.setItem(REFRESH_TOKEN_KEY, token);
}

export function removeRefreshToken() {
  getStorage()?.removeItem(REFRESH_TOKEN_KEY);
}

export function clearAuthTokens() {
  removeAccessToken();
  removeRefreshToken();
}
