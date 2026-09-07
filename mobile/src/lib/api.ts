export const SITE_ORIGIN = "https://the-equalizer.onrender.com";
export const API_BASE_URL = `${SITE_ORIGIN}/api/mobile`;
export const LOGO_URL = `${SITE_ORIGIN}/static/images/equalizer-logo.jpg`;

const REQUEST_TIMEOUT_MS = 90000;

export async function apiGet<T>(path: string): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const controller = new AbortController();

  const timeout = setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${normalizedPath}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "include",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(
        `The Equalizer server returned HTTP ${response.status}.`
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(
        "The server took too long to respond. It may be waking up. Please try again."
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}


export async function apiPost<T>(path: string): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const controller = new AbortController();

  const timeout = setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${normalizedPath}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      credentials: "include",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(
        `The Equalizer server returned HTTP ${response.status}.`
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(
        "The server took too long to respond. It may be waking up. Please try again."
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export function formatDate(value?: string | null): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat("en-PH", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

export function stripHtml(value = ""): string {
  return value
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<\/div>/gi, "\n")
    .replace(/<\/li>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function truncateWords(value = "", maxWords = 28): string {
  const plain = stripHtml(value).trim();
  if (!plain) return "";

  const words = plain.split(/\s+/);

  if (words.length <= maxWords) {
    return plain;
  }

  return `${words.slice(0, maxWords).join(" ")}…`;
}
