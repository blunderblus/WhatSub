function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function createTtlCache(ttlMs) {
  const entries = new Map();

  async function getOrSet(key, loader) {
    const cached = entries.get(key);
    const now = Date.now();
    if (cached && cached.expiresAt > now) {
      return cloneJson(cached.value);
    }

    const value = await loader();
    entries.set(key, {
      value: cloneJson(value),
      expiresAt: now + ttlMs,
    });
    return value;
  }

  function clear() {
    entries.clear();
  }

  return { getOrSet, clear };
}
