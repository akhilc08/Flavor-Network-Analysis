const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw Object.assign(new Error(detail.detail ?? res.statusText), { status: res.status })
  }
  return res.json()
}

export async function listIngredients(): Promise<string[]> {
  const data = await get<{ ingredients: string[] }>('/ingredients')
  return data.ingredients
}

export async function searchIngredient(q: string, limit = 10) {
  return get<import('./types').SearchResponse>(
    `/search?q=${encodeURIComponent(q)}&limit=${limit}`
  )
}

export async function getUncertainPairs() {
  return get<import('./types').UncertainPairsResponse>('/uncertain-pairs')
}

export async function submitRatings(body: import('./types').RateRequest) {
  const res = await fetch(`${BASE}/rate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Rate failed')
  return res.json() as Promise<import('./types').RateResponse>
}

export async function getGraph(center: string, maxNodes = 50, minScore = 0.0) {
  return get<import('./types').GraphResponse>(
    `/graph?center=${encodeURIComponent(center)}&max_nodes=${maxNodes}&min_score=${minScore}`
  )
}

export async function streamRecipe(
  body: import('./types').RecipeRequest,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
) {
  try {
    const res = await fetch(`${BASE}/recipe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(detail.detail ?? res.statusText)
    }
    if (!res.body) {
      throw new Error('No response body')
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      onChunk(decoder.decode(value, { stream: true }))
    }
    onDone()
  } catch (e) {
    onError(e instanceof Error ? e : new Error(String(e)))
  }
}
