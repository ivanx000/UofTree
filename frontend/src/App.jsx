import React from 'react'
import { useLazyQuery } from '@apollo/client'
import SearchBar from './components/SearchBar'
import FlowVisualizer from './components/FlowVisualizer'
import { GET_COURSE } from './graphql/queries'
import bgVideo from './assets/14471921_3840_2160_30fps.mp4'

export default function App() {
  const [queriedCode, setQueriedCode] = React.useState(null)
  const [showResult, setShowResult]   = React.useState(false)

  const [fetchCourse, { loading, error, data }] = useLazyQuery(GET_COURSE, {
    fetchPolicy: 'cache-first',
  })

  function handleSearch(code) {
    const normalized = (code || '').trim().toUpperCase()
    if (!normalized) return
    setQueriedCode(normalized)
    setShowResult(false)
    fetchCourse({ variables: { code: normalized } })
  }

  const course = data?.course

  React.useEffect(() => {
    if (course) setShowResult(true)
  }, [course])

  function handleBack() {
    setShowResult(false)
    setQueriedCode(null)
  }

  // ── Shared background elements ────────────────────────────────────────────
  const Background = () => (
    <>
      <video
        autoPlay loop muted playsInline src={bgVideo}
        style={{ position: 'fixed', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 0 }}
      />
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(255,255,255,0.52)', zIndex: 1 }} />
    </>
  )

  // ── Tree view ─────────────────────────────────────────────────────────────
  if (showResult && course) {
    return (
      <div style={{ position: 'relative', minHeight: '100vh' }}>
        <Background />
        <button
          onClick={handleBack}
          style={{
            position: 'fixed',
            top: 20,
            left: 20,
            zIndex: 10,
            background: 'rgba(255,255,255,0.88)',
            color: '#002A5C',
            border: '1.5px solid #4a90d9',
            borderRadius: '6px',
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 700,
            cursor: 'pointer',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          ← Back
        </button>
        <div style={{ position: 'relative', zIndex: 2 }}>
          <FlowVisualizer courseData={course} />
        </div>
      </div>
    )
  }

  // ── Landing page ──────────────────────────────────────────────────────────
  return (
    <div className="font-sans" style={{ position: 'relative', minHeight: '100vh' }}>
      <Background />
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <main
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            padding: '0 1.5rem',
          }}
        >
          <div style={{ flexShrink: 0, height: 'calc(50vh - 110px)' }} />

          <div style={{ width: '100%', maxWidth: '700px', margin: '0 auto' }}>
            <h1
              style={{
                fontWeight: 800,
                lineHeight: 1.15,
                textAlign: 'left',
                marginBottom: '1.25rem',
              }}
            >
              <span style={{ display: 'block', fontSize: 'clamp(1.4rem, 2.6vw, 2.2rem)', color: '#000000' }}>
                Explore course prerequisites
              </span>
              <span style={{ display: 'block', fontSize: 'clamp(1.4rem, 2.6vw, 2.2rem)', color: '#000000' }}>
                at the{' '}
                <span style={{
                  background: 'linear-gradient(135deg, #4a90d9 0%, #0033a0 60%, #00205b 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  filter: 'drop-shadow(0 0 8px rgba(74, 144, 217, 0.65))',
                }}>
                  University of Toronto
                </span>
              </span>
            </h1>

            <SearchBar onSearch={handleSearch} landing />
          </div>

          {loading && (
            <p style={{ marginTop: '2rem', color: 'rgba(0,0,0,0.45)', fontSize: '0.875rem' }}>
              Loading <span style={{ fontFamily: 'monospace' }}>{queriedCode}</span>…
            </p>
          )}

          {!loading && error && (
            <p style={{ marginTop: '2rem', color: '#dc2626', fontSize: '0.875rem' }}>
              Could not load course. Please try again.
            </p>
          )}

          {!loading && !error && data && !course && (
            <p style={{ marginTop: '2rem', color: 'rgba(0,0,0,0.45)', fontSize: '0.875rem' }}>
              Course{' '}
              <span style={{ fontFamily: 'monospace', color: '#b45309' }}>{queriedCode}</span>{' '}
              was not found.
            </p>
          )}
        </main>
      </div>
    </div>
  )
}
