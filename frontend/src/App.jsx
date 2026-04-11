import React from 'react'
import SearchBar from './components/SearchBar'

export default function App() {
  function handleSearch() {}

  return (
    <div className="min-h-screen flex flex-col font-sans" style={{ backgroundColor: '#ffffff' }}>
      {/* Navigation Bar */}
      <nav
        className="w-full py-4 px-8"
        style={{ backgroundColor: '#00205b' }}
      >
        <div className="max-w-6xl mx-auto flex items-center">
          <h1 className="text-white font-bold text-xl">UofTree</h1>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12 w-full">
        <div className="w-full max-w-2xl text-center">
          <h1
            className="font-bold leading-tight mb-8"
            style={{
              fontSize: 'clamp(2rem, 4.2vw, 3.6rem)',
              color: '#000000',
            }}
          >
            <span style={{ display: 'block', whiteSpace: 'nowrap' }}>
              Explore prerequisite trees from
            </span>
            <span>University of Toronto courses</span>
          </h1>

          <div className="w-full">
            <SearchBar onSearch={handleSearch} landing />
          </div>
        </div>
      </main>
    </div>
  )
}
