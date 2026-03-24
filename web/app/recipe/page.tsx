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
        .filter(i => !selected.includes(i) && i.toLowerCase().includes(query.trim().toLowerCase()))
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
    <>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-serif text-[32px] font-normal text-dark mb-1">Recipe Generator</h1>
        <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
          Select 2–6 ingredients &middot; AI-generated molecular recipe
        </p>
      </div>

      <div className="max-w-2xl">
        {/* Tab bar */}
        <div className="flex border-b border-muted mb-6">
          <button
            onClick={() => setTab('ingredients')}
            className={[
              'px-5 py-2.5 font-sans text-[10px] font-bold tracking-[0.12em] uppercase -mb-px border-b-2 transition-colors duration-150',
              tab === 'ingredients' ? 'border-accent text-accent' : 'border-transparent text-warm-mid hover:text-dark',
            ].join(' ')}
          >
            Ingredients
            {selected.length > 0 && (
              <span className="ml-2 font-sans text-[10px] bg-accent text-bg rounded-sm px-1.5 py-0.5">{selected.length}</span>
            )}
          </button>
          <button
            onClick={() => setTab('api-key')}
            className={[
              'px-5 py-2.5 font-sans text-[10px] font-bold tracking-[0.12em] uppercase -mb-px border-b-2 transition-colors duration-150 flex items-center gap-1.5',
              tab === 'api-key' ? 'border-accent text-accent' : 'border-transparent text-warm-mid hover:text-dark',
            ].join(' ')}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            API Key
            <span className={`w-1.5 h-1.5 rounded-full ${apiKey.trim() ? 'bg-green' : 'bg-warm-light'}`} />
          </button>
        </div>

        {/* Ingredients tab */}
        {tab === 'ingredients' && (
          <section className="bg-card border border-muted rounded p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-[22px] font-normal text-dark">Select Ingredients</h2>
              <span className="font-sans text-[11px] text-warm-mid tracking-[0.04em]">{selected.length}/{MAX_SELECTED}</span>
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
                className="w-full font-serif text-base text-dark bg-bg border-[1.5px] border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)] placeholder:text-warm-light disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {showDropdown && filtered.length > 0 && (
                <div
                  ref={dropdownRef}
                  className="absolute z-10 mt-1 w-full bg-card border border-muted rounded shadow-card-hover overflow-hidden"
                >
                  {filtered.map((ingredient, i) => (
                    <button
                      key={ingredient}
                      onMouseDown={() => addIngredient(ingredient)}
                      className={[
                        'w-full text-left px-4 py-2 font-serif text-[14px] capitalize transition-colors duration-150',
                        i === activeIndex ? 'bg-accent text-bg' : 'text-dark hover:bg-bg',
                      ].join(' ')}
                    >
                      {ingredient}
                    </button>
                  ))}
                </div>
              )}
              {showDropdown && query.trim().length > 0 && filtered.length === 0 && (
                <div className="absolute z-10 mt-1 w-full bg-card border border-muted rounded shadow-card px-4 py-2 font-serif text-[14px] italic text-warm-mid">
                  No ingredients found
                </div>
              )}
            </div>

            {selected.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {selected.map(ingredient => (
                  <span
                    key={ingredient}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-sm font-sans text-[11px] font-semibold tracking-[0.06em] uppercase capitalize bg-accent/10 text-accent border border-accent/25"
                  >
                    {ingredient}
                    <button
                      onClick={() => removeIngredient(ingredient)}
                      aria-label={`Remove ${ingredient}`}
                      className="hover:opacity-70 transition-opacity duration-150 leading-none text-[14px]"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="font-serif text-[14px] italic text-warm-light">Search for an ingredient above to add it.</p>
            )}
          </section>
        )}

        {/* API Key tab */}
        {tab === 'api-key' && (
          <section className="bg-card border border-muted rounded p-6 mb-6 flex flex-col gap-5">
            <div className="flex items-start gap-3 p-4 bg-green/10 border border-green/20 rounded">
              <svg className="w-4 h-4 text-green mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <div>
                <p className="font-sans text-[10px] font-bold tracking-[0.1em] uppercase text-green mb-1">Your key stays private</p>
                <p className="font-sans text-[12px] text-warm-mid leading-relaxed">
                  Your API key is sent directly to the server over HTTPS for one request only. It is <strong>never logged, stored, or shared</strong>.
                </p>
              </div>
            </div>

            <div>
              <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5" htmlFor="api-key-input">
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
                  className="w-full font-mono text-[13px] text-dark bg-bg border-[1.5px] border-muted rounded px-3.5 py-2.5 pr-10 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)] placeholder:text-warm-light"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-warm-mid hover:text-dark transition-colors duration-150"
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
              <p className="font-sans text-[11px] text-warm-light mt-1.5">
                Get your key at{' '}
                <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                  console.anthropic.com
                </a>
              </p>
            </div>

            <p className="font-sans text-[12px] text-warm-mid leading-relaxed border-t border-muted pt-4">
              Recipe generation uses Claude AI. To keep this app free for everyone, each user provides their own key.
            </p>
          </section>
        )}

        {/* Primary action */}
        {tab === 'api-key' ? (
          <button
            onClick={() => setTab('ingredients')}
            className="w-full font-sans text-[11px] font-bold tracking-[0.12em] uppercase text-dark bg-card border border-muted px-6 py-2.5 rounded cursor-pointer transition-colors duration-150 hover:border-accent hover:text-accent"
          >
            Done
          </button>
        ) : (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full font-sans text-[11px] font-bold tracking-[0.12em] uppercase text-bg bg-accent px-6 py-2.5 rounded cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {generating && (
              <span aria-hidden="true" className="inline-block w-3.5 h-3.5 border-2 border-bg/40 border-t-bg rounded-full animate-spin" />
            )}
            {generating ? 'Generating…' : 'Generate Recipe'}
          </button>
        )}

        {/* Error state */}
        {error && (
          <p className="font-serif text-[14px] italic text-warm-mid mt-3">{error}</p>
        )}

        {/* Recipe output */}
        {(recipe || generating) && (
          <div className="mt-8 bg-card border border-muted rounded p-7">
            <div className="recipe-prose">
              <ReactMarkdown>{recipe}</ReactMarkdown>
              {generating && (
                <span className="inline-block w-px h-4 bg-dark ml-0.5 align-middle blink-cursor" />
              )}
            </div>
          </div>
        )}

        {done && !generating && tab === 'ingredients' && (
          <button
            onClick={() => { setRecipe(''); setDone(false); setError(null) }}
            className="mt-4 w-full font-sans text-[11px] font-bold tracking-[0.12em] uppercase text-dark bg-card border border-muted px-6 py-2.5 rounded cursor-pointer transition-colors duration-150 hover:border-accent hover:text-accent"
          >
            Generate Another
          </button>
        )}
      </div>
    </>
  )
}
