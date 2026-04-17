import React from 'react'
import { useLazyQuery } from '@apollo/client'
import SearchBar from './components/SearchBar'
import FlowVisualizer from './components/FlowVisualizer'
import { GET_COURSE } from './graphql/queries'
import bgVideo from './assets/14471921_3840_2160_30fps.mp4'

const EXIT_LANDING_MS = 650
const EXIT_TREE_MS    = 750

export default function App() {
  const [queriedCode, setQueriedCode]     = React.useState(null)
  // Track which code the user actually submitted so re-searches of the
  // same course (served from Apollo cache) still trigger the transition.
  const [expectedCode, setExpectedCode]   = React.useState(null)
  const [viewState, setViewState]         = React.useState('landing')
  const [displayCourse, setDisplayCourse] = React.useState(null)
  const [landingKey, setLandingKey]       = React.useState(0)

  const [fetchCourse, { loading, error, data }] = useLazyQuery(GET_COURSE, {
    fetchPolicy: 'cache-first',
  })

  const course = data?.course

  // Step 1 — detect course arrival and start the exit animation.
  // Split into two effects so the timer in step 2 survives React StrictMode's
  // double-invocation (StrictMode cancels the first run's cleanup, but the
  // second run of step 2 restarts the timer with the same viewState value).
  React.useEffect(() => {
    if (!course || course.code !== expectedCode || viewState !== 'landing') return
    setExpectedCode(null)
    setDisplayCourse(course)
    setViewState('exit-landing')
  }, [course?.code, expectedCode, viewState])

  // Step 2 — advance to 'tree' after the exit animation completes.
  React.useEffect(() => {
    if (viewState !== 'exit-landing') return
    const t = setTimeout(() => setViewState('tree'), EXIT_LANDING_MS)
    return () => clearTimeout(t)
  }, [viewState])

  function handleSearch(code) {
    const normalized = (code || '').trim().toUpperCase()
    if (!normalized) return
    setQueriedCode(normalized)
    setExpectedCode(normalized)
    fetchCourse({ variables: { code: normalized } })
  }

  function handleBack() {
    setViewState('exit-tree')
    setLandingKey(k => k + 1)   // start landing animation immediately, in parallel with tree exit
    setTimeout(() => {
      setViewState('landing')
      setQueriedCode(null)
    }, EXIT_TREE_MS)
  }

  const exitingLanding = viewState === 'exit-landing'
  const showTree       = viewState === 'tree' || viewState === 'exit-tree'
  const exitingTree    = viewState === 'exit-tree'

  // Single return — background is always in the DOM so the video never
  // remounts (which caused the black flash between transitions).
  return (
    <div className="font-sans" style={{ position: 'relative', minHeight: '100vh', overflow: (exitingTree || exitingLanding) ? 'hidden' : undefined }}>

      {/* ── Background — never unmounts ──────────────────────────────────── */}
      <video
        autoPlay loop muted playsInline src={bgVideo}
        style={{ position: 'fixed', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 0 }}
      />
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(255,255,255,0.52)', zIndex: 1 }} />

      {/* ── Landing — also rendered during exit-tree so it slides in simultaneously ── */}
      {(!showTree || exitingTree) && (
        <div style={{ position: exitingTree ? 'fixed' : 'relative', ...(exitingTree ? { inset: 0 } : {}), zIndex: 2, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
          <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '0 1.5rem' }}>

            <div style={{ flexShrink: 0, height: 'calc(50vh - 110px)' }} />

            {/* Title + search slide together as one unit */}
            <div
              key={landingKey}
              className={exitingTree && landingKey > 0 ? 'landing-slide-down' : ''}
              style={{
                width: '100%',
                maxWidth: '700px',
                margin: '0 auto',
                ...(exitingLanding ? {
                  transform: 'translateY(-110vh)',
                  transition: `transform ${EXIT_LANDING_MS}ms cubic-bezier(0.4, 0, 1, 1)`,
                } : {}),
              }}
            >

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
                Course <span style={{ fontFamily: 'monospace', color: '#b45309' }}>{queriedCode}</span> was not found.
              </p>
            )}

          </main>
        </div>
      )}

      {/* ── Tree ─────────────────────────────────────────────────────────── */}
      {showTree && (
        <div
          style={{
            position: 'relative',
            zIndex: 3,
            transform: exitingTree ? 'translateY(100vh)' : 'translateY(0)',
            transition: exitingTree ? `transform ${EXIT_TREE_MS}ms cubic-bezier(0.4, 0, 1, 1)` : 'none',
          }}
        >
          <button
            onClick={handleBack}
            aria-label="Go back"
            style={{
              position: 'fixed',
              top: 20,
              left: 20,
              zIndex: 10,
              width: 44,
              height: 44,
              background: 'rgba(255,255,255,0.97)',
              color: '#002A5C',
              border: 'none',
              borderRadius: '50%',
              fontSize: '18px',
              cursor: 'pointer',
              backdropFilter: 'blur(8px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 16px rgba(0,0,0,0.12), 0 0 14px 3px rgba(74,144,217,0.45)',
              opacity: exitingTree ? 0 : 1,
              transition: exitingTree ? 'opacity 0.15s ease' : 'none',
            }}
          >
            ←
          </button>
          <div className={exitingTree ? '' : 'tree-slide-up'}>
            {displayCourse && <FlowVisualizer courseData={displayCourse} />}
          </div>
        </div>
      )}

    </div>
  )
}
