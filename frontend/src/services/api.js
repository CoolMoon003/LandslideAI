const BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";


async function get(path) {

  const response =
    await fetch(BASE_URL + path);

  if (!response.ok) {

    throw new Error(
      `${response.status} ${response.statusText}`
    );
  }

  return response.json();
}


function extractArray(value) {

  if (typeof value === "string") {

    try {
      value = JSON.parse(value);
    } catch {
      return [];
    }
  }

  if (Array.isArray(value)) {
    return value;
  }

  if (!value || typeof value !== "object") {
    return [];
  }

  if (Array.isArray(value.features)) {
    return value.features;
  }

  const possibleKeys = [
    "data",
    "items",
    "results",
    "roads",
    "settlements",
    "landslides",
    "records",
    "values",
  ];

  for (const key of possibleKeys) {

    if (Array.isArray(value[key])) {
      return value[key];
    }
  }

  for (const key of Object.keys(value)) {

    if (Array.isArray(value[key])) {
      return value[key];
    }
  }

  return [];
}


export const api = {
  health: () => get("/health"),

  summary: (date) =>
    get(`/summary${date ? `?date=${date}` : ""}`),

  statistics: (date) =>
    get(`/risk/statistics?date=${date}`),

  scenario: (date) =>
    get(`/risk/scenario?date=${date}`),

  distribution: (date) =>
    get(`/risk/distribution?date=${date}`),

  point: (lat, lon, date) =>
    get(`/risk/point?lat=${lat}&lon=${lon}&date=${date}`),

  overlayUrl: (date) =>
    `${BASE_URL}/risk/overlay?date=${date}`,

  landslides: async () =>
    extractArray(await get("/landslides")),

  roads: async () =>
    extractArray(
      await get("/infrastructure/roads?limit=5000")
    ),

  settlements: async () =>
    extractArray(
      await get("/infrastructure/settlements?limit=5000")
    ),

  metrics: async () => {
    let value = await get("/model/metrics");

    if (typeof value === "string") {
      try {
        value = JSON.parse(value);
      } catch {
        return [];
      }
    }

    return Array.isArray(value)
      ? value
      : value?.metrics || [];
  },

  features: async () => {
    let value = await get("/model/features");

    if (typeof value === "string") {
      try {
        value = JSON.parse(value);
      } catch {
        return [];
      }
    }

    return Array.isArray(value)
      ? value
      : value?.features || [];
  },

  rainfallScenario: (date) =>
    get(`/rainfall/scenario?date=${date}`),
};