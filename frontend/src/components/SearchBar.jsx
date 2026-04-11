import React, { useState } from 'react'
import { useLazyQuery } from '@apollo/client'
import { SEARCH_COURSES } from '../graphql/queries'

export default function SearchBar({ onSearch, landing = false }) {
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const [fetchSuggestions] = useLazyQuery(SEARCH_COURSES, {
    onCompleted: (data) => setSuggestions(data.courses ?? []),
  })

  function handleChange(e) {
    const value = e.target.value
    setInput(value)
    if (value.length >= 2) {
      fetchSuggestions({ variables: { search: value } })
      setShowSuggestions(true)
    } else {
      setShowSuggestions(false)
      setSuggestions([])
    }
  }

  function handleSelect(code) {
    setInput(code)
    setShowSuggestions(false)
    onSearch(code)
  }

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = input.trim().toUpperCase()
    if (trimmed) {
      onSearch(trimmed)
      setShowSuggestions(false)
    }
  }

  function handleBlur() {
    setTimeout(() => setShowSuggestions(false), 150)
  }

  if (landing) {
    // Large white search bar matching the reference screenshot
    return (
      <div className="relative w-full">
        <form onSubmit={handleSubmit} className="relative">
          {/* Magnifying glass icon */}
          <svg
            className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none"
            width="18" height="18" viewBox="0 0 24 24"
            fill="none" stroke="rgba(100,100,120,0.5)" strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={input}
            onChange={handleChange}
            onBlur={handleBlur}
            onFocus={() => input.length >= 2 && setShowSuggestions(true)}
            placeholder="Search for a Course..."
            className="w-full pl-11 pr-4 py-3.5 rounded-xl text-gray-800 text-sm outline-none transition"
            style={{
              background: 'rgba(255,255,255,0.97)',
              boxShadow: '0 0 0 3px rgba(0, 51, 160, 0), 0 0 12px rgba(0, 51, 160, 0)',
              fontSize: '15px',
            }}
            onFocusCapture={e => {
              e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0, 51, 160, 0.2), 0 0 12px rgba(0, 51, 160, 0.4)'
            }}
            onBlurCapture={e => {
              e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0, 51, 160, 0), 0 0 12px rgba(0, 51, 160, 0)'
            }}
          />
        </form>

        {showSuggestions && suggestions.length > 0 && (
          <ul
            className="absolute z-50 mt-1 w-full rounded-xl overflow-hidden shadow-lg"
            style={{ background: '#ffffff', border: '1px solid #e0e0e0' }}
          >
            {suggestions.map((c) => (
              <li
                key={c.code}
                onMouseDown={() => handleSelect(c.code)}
                className="px-4 py-2.5 cursor-pointer flex items-center gap-3 transition"
                style={{ color: '#000000' }}
                onMouseEnter={e => e.currentTarget.style.background = '#e8f1ff'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span className="font-mono text-sm shrink-0" style={{ color: '#0033a0' }}>{c.code}</span>
                <span className="text-sm truncate" style={{ color: 'rgba(0,0,0,0.7)' }}>{c.name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  // Compact dark search bar (used in results view)
  return (
    <div className="relative w-full">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
            width="15" height="15" viewBox="0 0 24 24"
            fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={input}
            onChange={handleChange}
            onBlur={handleBlur}
            onFocus={() => input.length >= 2 && setShowSuggestions(true)}
            placeholder="Search a course code..."
            className="w-full pl-9 pr-3 py-2 rounded-lg text-sm outline-none transition"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              color: '#f1f5f9',
            }}
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 rounded-lg text-sm font-medium text-white transition"
          style={{ background: '#7B6CF6' }}
          onMouseEnter={e => e.currentTarget.style.background = '#6a5be0'}
          onMouseLeave={e => e.currentTarget.style.background = '#7B6CF6'}
        >
          Search
        </button>
      </form>

      {showSuggestions && suggestions.length > 0 && (
        <ul
          className="absolute z-50 mt-1 w-full rounded-lg overflow-hidden shadow-2xl"
          style={{ background: '#1a1a3a', border: '1px solid rgba(255,255,255,0.1)' }}
        >
          {suggestions.map((c) => (
            <li
              key={c.code}
              onMouseDown={() => handleSelect(c.code)}
              className="px-4 py-2 cursor-pointer flex items-center gap-3 transition"
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(123,108,246,0.15)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span className="font-mono text-xs shrink-0" style={{ color: '#7B6CF6' }}>{c.code}</span>
              <span className="text-xs truncate" style={{ color: 'rgba(255,255,255,0.6)' }}>{c.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
