'use client'

import { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { streamRecipe } from '@/lib/api'
import { ALL_INGREDIENTS } from '@/lib/ingredients'

const MAX_SELECTED = 6
type Tab = 'ingredients' | 'api-key'

export default function RecipePage() {
  const [tab, setTab] = useState<Tab>('ingredients')
  const [selected, setSelected] = useState<string[]>([])
  const [query, setQuery] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [recipe, setRecipe] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const filtered = query.trim().length === 0
    ? []
    : ALL_INGREDIENTS
        .filter(i => !selected.includes(i) && i.includes(query.trim().toLowerCase()))
        .slice(0, 10)

  function addIngredient(ingredient: string) {
    if (!ingredient) return
    setSelected(prev => {
      if (prev.includes(ingredient) || prev.length >= MAX_SELECTED) return prev
      return [...prev, ingredient]
    })
    setQuery('')
    setShowDropdown(false)
    setActiveIndex(-1)
    inputRef.current?.focus()
  }

  function removeIngredient(ingredient: string) {
    setSelected(prev => prev.filter(i => i !== ingredient))
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showDropdown || filtered.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(i => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault()
      addIngredient(filtered[activeIndex])
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  async function handleGenerate() {
    if (generating) return
    if (selected.length < 2) {
      setError('Select at least 2 ingredients first.')
      return
    }
    if (!apiKey.trim()) {
      setError('No API key provided. Go to the API Key tab and enter your Anthropic key.')
      return
    }
    setGenerating(true)
    setRecipe('')
    setError(null)
    setDone(false)

    streamRecipe(
      { ingredients: selected, shared_molecules: [], flavor_labels: {}, api_key: apiKey.trim() },
      (chunk) => setRecipe(prev => prev + chunk),
      () => { setGenerating(false); setDone(true) },
      (err) => { setError(err.message); setGenerating(false) },
    )
  }

  return (
    <div className="min-h-screen bg-bg py-12 px-4">
      {/* Error banner — fixed at top so it's always visible */}
      {error && (
        <div
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
            backgroundColor: '#b91c1c', color: '#fff',
            padding: '12px 24px', textAlign: 'center',
            fontSize: '14px', fontFamily: 'system-ui, sans-serif',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: 16, opacity: 0.8, fontWeight: 'bold' }}
          >
            ✕
          </button>
        </div>
      )}
      <div className="max-w-2xl mx-auto" style={error ? { paddingTop: 48 } : {}}>
        <h1 className="font-serif text-3xl text-dark mb-2">Recipe Generator</h1>
        <p className="text-muted font-serif mb-8">Select 2–6 ingredients to generate a molecularly-paired recipe</p>

        {/* Tab bar */}
        <div className="flex border-b border-[#e8d5bc] mb-6">
          <button
            onClick={() => setTab('ingredients')}
            className={[
              'px-5 py-2.5 text-sm font-sans -mb-px border-b-2 transition-colors',
              tab === 'ingredients' ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-dark',
            ].join(' ')}
          >
            Ingredients
            {selected.length > 0 && (
              <span className="ml-1.5 text-xs bg-accent text-bg rounded-full px-1.5 py-0.5">{selected.length}</span>
            )}
          </button>
          <button
            onClick={() => setTab('api-key')}
            className={[
              'px-5 py-2.5 text-sm font-sans -mb-px border-b-2 transition-colors flex items-center gap-1.5',
              tab === 'api-key' ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-dark',
            ].join(' ')}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            API Key
            <span className={`w-1.5 h-1.5 rounded-full ${apiKey.trim() ? 'bg-green-500' : 'bg-red-400'}`} />
          </button>
        </div>

        {/* Ingredients tab */}
        {tab === 'ingredients' && (
          <section className="bg-card border border-[#e8d5bc] rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg text-dark">Select Ingredients</h2>
              <span className="text-sm text-muted font-sans">{selected.length}/{MAX_SELECTED} selected</span>
            </div>
            {/* Combobox */}
            <div className="relative mb-4">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => { setQuery(e.target.value); setShowDropdown(true); setActiveIndex(-1) }}
                onFocus={() => { if (query) setShowDropdown(true) }}
                onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                onKeyDown={handleKeyDown}
                disabled={selected.length >= MAX_SELECTED}
                placeholder={selected.length >= MAX_SELECTED ? 'Maximum ingredients selected' : 'Search ingredients…'}
                className="w-full px-3 py-2.5 rounded-lg border border-[#e8d5bc] bg-bg font-sans text-sm text-dark placeholder-muted focus:outline-none focus:border-accent disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {showDropdown && filtered.length > 0 && (
                <div
                  ref={dropdownRef}
                  className="absolute z-10 mt-1 w-full bg-card border border-[#e8d5bc] rounded-lg shadow-md overflow-hidden"
                >
                  {filtered.map((ingredient, i) => (
                    <button
                      key={ingredient}
                      onMouseDown={() => addIngredient(ingredient)}
                      className={[
                        'w-full text-left px-4 py-2 text-sm font-sans capitalize transition-colors',
                        i === activeIndex ? 'bg-accent text-bg' : 'text-dark hover:bg-[#f5ece0]',
                      ].join(' ')}
                    >
                      {ingredient}
                    </button>
                  ))}
                </div>
              )}
              {showDropdown && query.trim().length > 0 && filtered.length === 0 && (
                <div className="absolute z-10 mt-1 w-full bg-card border border-[#e8d5bc] rounded-lg shadow-md px-4 py-2 text-sm text-muted font-sans">
                  No ingredients found
                </div>
              )}
            </div>

            {selected.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {selected.map(ingredient => (
                  <span
                    key={ingredient}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-sans capitalize bg-accent text-bg"
                  >
                    {ingredient}
                    <button
                      onClick={() => removeIngredient(ingredient)}
                      aria-label={`Remove ${ingredient}`}
                      className="hover:opacity-70 transition-opacity leading-none"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted font-sans">No ingredients selected yet.</p>
            )}
          </section>
        )}

        {/* API Key tab */}
        {tab === 'api-key' && (
          <section className="bg-card border border-[#e8d5bc] rounded-lg p-6 mb-6 space-y-5">
            <div className="flex items-start gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
              <svg className="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <div>
                <p className="text-sm font-sans font-medium text-green-800">Your key stays private</p>
                <p className="text-xs font-sans text-green-700 mt-1 leading-relaxed">
                  Your API key is sent directly to the server over HTTPS for one request only. It is <strong>never logged, stored, or shared</strong> — not in a database, not in server memory beyond the single call.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-sans text-dark mb-2" htmlFor="api-key-input">
                Anthropic API Key
              </label>
              <div className="relative">
                <input
                  id="api-key-input"
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  placeholder="sk-ant-..."
                  autoComplete="off"
                  spellCheck={false}
                  className="w-full px-4 py-2.5 pr-10 rounded-lg border border-[#e8d5bc] bg-bg font-mono text-sm text-dark placeholder-muted focus:outline-none focus:border-accent"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-dark transition-colors"
                  aria-label={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="text-xs text-muted font-sans mt-2">
                Get your key at{' '}
                <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                  console.anthropic.com
                </a>
              </p>
            </div>

            <p className="text-xs font-sans text-muted leading-relaxed border-t border-[#e8d5bc] pt-4">
              Recipe generation uses Claude AI. To keep this app free for everyone, each user provides their own key — no usage costs are passed to the app.
            </p>
          </section>
        )}

        {tab === 'api-key' ? (
          <button
            onClick={() => setTab('ingredients')}
            className="w-full py-3 rounded-lg font-sans text-base bg-accent text-bg hover:bg-accent/90 cursor-pointer transition-colors"
          >
            Save API Key
          </button>
        ) : (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className={[
              'w-full py-3 rounded-lg font-sans text-base transition-colors flex items-center justify-center gap-2',
              generating
                ? 'bg-[#e8d5bc] text-muted cursor-not-allowed'
                : 'bg-accent text-bg hover:bg-accent/90 cursor-pointer',
            ].join(' ')}
          >
            {generating && (
              <span aria-hidden="true" className="inline-block w-4 h-4 border-2 border-bg border-t-transparent rounded-full animate-spin" />
            )}
            {generating ? 'Generating…' : 'Generate Recipe'}
          </button>
        )}

        {/* Recipe output */}
        {(recipe || generating) && !error && (
          <div className="mt-8 bg-card border border-[#e8d5bc] rounded-lg p-6">
            <div className="recipe-prose">
              <ReactMarkdown>{recipe}</ReactMarkdown>
              {generating && (
                <span
                  className="inline-block w-px h-4 bg-dark ml-0.5 align-middle"
                  style={{ animation: 'blink 1s step-end infinite' }}
                />
              )}
            </div>
          </div>
        )}

        {done && !generating && tab === 'ingredients' && (
          <button
            onClick={() => { setRecipe(''); setDone(false); setError(null) }}
            className="mt-6 w-full py-3 rounded-lg font-sans text-base bg-card border border-[#e8d5bc] text-dark hover:border-accent hover:text-accent transition-colors"
          >
            Generate Another
          </button>
        )}
      </div>

      <style jsx global>{`
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>
    </div>
  )
}
