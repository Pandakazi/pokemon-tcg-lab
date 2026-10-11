// Retained from approved Figma source e3d410e; unsupported controls are disabled.
import {SettingsControl} from './Settings'
type ViewMode = 'gallery' | 'list'
type Category = 'pokemon' | 'trainers' | 'energy'
type Scope = 'all' | 'owned' | 'unowned'
export function TopBar({ activeNav, onNavChange }: { activeNav: string; onNavChange: (n: string) => void }) {
  return (
    <div style={{
      height: 48, display: 'flex', alignItems: 'center', padding: '0 16px',
      borderBottom: '1px solid var(--overlay-07)',
      background: 'var(--topbar)', flexShrink: 0, gap: 0, zIndex: 100,
    }}>
      {/* Logo */}
      <button aria-label="PokéLab Home" onClick={()=>onNavChange('Home')} style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 32 }}>
        <div style={{
          width: 26, height: 26, borderRadius: 7, background: 'linear-gradient(135deg, #7c3aed, #5b21b6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          boxShadow: '0 2px 8px rgba(124,58,237,0.35)',
        }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', fontFamily: 'Outfit' }}>PL</span>
        </div>
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--heading)', fontFamily: 'Outfit', letterSpacing: '-0.01em' }}>
          Poké<span style={{ color: '#8b5cf6' }}>Lab</span>
        </span>
      </button>

      {/* Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {['Library', 'Collection', 'Analytics', 'Deck Builder'].map(nav => (
          <span key={nav} title={nav==='Analytics'?'Coming soon!':undefined} style={{display:'inline-flex'}}><button
            key={nav}
            disabled={nav === "Analytics"} onClick={() => onNavChange(nav)}
            style={{
              padding: '5px 14px', borderRadius: 6, border: 'none', cursor: nav==='Analytics'?'not-allowed':'pointer',
              fontSize: 13, fontWeight: activeNav === nav ? 600 : 400,
              color: activeNav === nav ? 'var(--heading)' : 'var(--nav-muted)',
              background: activeNav === nav ? 'var(--overlay-08)' : 'transparent',
              transition: 'all 0.12s', fontFamily: 'Inter',
            }}
          >
            {nav}
          </button></span>
        ))}
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }}/>

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{color:'var(--muted)',fontSize:11}}>Local collection</span>
        <SettingsControl/>
      </div>
    </div>
  )
}

export function LibraryControls({
  category, onCategoryChange, scope, onScopeChange,
  viewMode, onViewModeChange, searchQuery, onSearchChange,
  filterOpen, onFilterToggle, totalCards, filteredCount,
}: {
  category: Category; onCategoryChange: (c: Category) => void
  scope: Scope; onScopeChange: (s: Scope) => void
  viewMode: ViewMode; onViewModeChange: (v: ViewMode) => void
  searchQuery: string; onSearchChange: (q: string) => void
  filterOpen: boolean; onFilterToggle: () => void
  totalCards: number; filteredCount: number
}) {
  return (
    <div className="library-controls" style={{
      height: 52, display: 'flex', alignItems: 'center', padding: '0 16px',
      borderBottom: '1px solid var(--overlay-06)', flexShrink: 0, gap: 12,
      background: 'var(--toolbar)',
    }}>
      {/* Filter toggle */}
      <button
        onClick={onFilterToggle}
        style={{
          width: 30, height: 30, borderRadius: 6, border: `1px solid ${filterOpen ? 'rgba(124,58,237,0.4)' : 'var(--overlay-08)'}`,
          background: filterOpen ? 'rgba(124,58,237,0.14)' : 'var(--overlay-04)',
          color: filterOpen ? 'var(--focus)' : 'var(--nav-muted)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13,
        }}
        aria-label="Toggle filters" aria-expanded={filterOpen} title="Toggle filters"
      >
        ⊞
      </button>

      {/* Category tabs */}
      <div style={{ display: 'flex', background: 'var(--overlay-04)', borderRadius: 7, padding: 2, border: '1px solid var(--overlay-07)' }}>
        {(['pokemon', 'trainers', 'energy'] as Category[]).map(cat => (
          <button
            key={cat}
            aria-pressed={category === cat} onClick={() => onCategoryChange(cat)}
            style={{
              padding: '4px 14px', borderRadius: 5, border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: category === cat ? 600 : 400,
              color: category === cat ? 'var(--text)' : 'var(--nav-muted)',
              background: category === cat ? 'var(--overlay-09)' : 'transparent',
              transition: 'all 0.12s', textTransform: 'capitalize', fontFamily: 'Inter',
            }}
          >
            {cat === 'pokemon' ? 'Pokémon' : cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* Scope */}
      <div style={{ display: 'flex', background: 'var(--overlay-04)', borderRadius: 7, padding: 2, border: '1px solid var(--overlay-07)' }}>
        {(['all', 'owned', 'unowned'] as Scope[]).map(s => (
          <button
            key={s}
            aria-pressed={scope===s} onClick={() => onScopeChange(s)}
            style={{
              padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: scope === s ? 600 : 400,
              color: scope === s ? 'var(--text)' : 'var(--nav-muted)',
              background: scope === s ? 'var(--overlay-09)' : 'transparent',
              transition: 'all 0.12s', textTransform: 'capitalize', fontFamily: 'Inter',
            }}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Card count */}
      <span data-testid="result-progress" style={{ fontSize: 11, color: 'var(--quiet)', fontFamily: 'JetBrains Mono', flexShrink: 0 }}>
        {filteredCount}/{totalCards}
      </span>

      {/* Search */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', gap: 8, maxWidth: 320,
        background: 'var(--overlay-05)', border: '1px solid var(--overlay-09)',
        borderRadius: 7, padding: '0 10px', height: 30,
      }}>
        <span style={{ color: 'var(--quiet)', fontSize: 12, flexShrink: 0 }}>⌕</span>
        <input
          aria-label="Search cards" maxLength={100} value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Search cards…"
          style={{
            flex: 1, background: 'none', border: 'none', outline: 'none',
            fontSize: 12, color: 'var(--text)', fontFamily: 'Inter',
          }}
        />
        {searchQuery && (
          <button aria-label="Clear search" onClick={() => onSearchChange('')} style={{ background: 'none', border: 'none', color: 'var(--quiet)', cursor: 'pointer', fontSize: 13, padding: 0 }}>×</button>
        )}
      </div>

      <div style={{ flex: 1 }}/>

      {/* View mode */}
      <div style={{ display: 'flex', background: 'var(--overlay-04)', borderRadius: 7, padding: 2, border: '1px solid var(--overlay-07)' }}>
        {[
          { mode: 'gallery' as ViewMode, icon: '⊞', label: 'Gallery' },
          { mode: 'list' as ViewMode, icon: '≡', label: 'List' },
        ].map(({ mode, icon, label }) => (
          <button
            key={mode}
            aria-pressed={viewMode === mode} aria-label={label} onClick={() => onViewModeChange(mode)}
            title={label}
            style={{
              padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
              fontSize: 14, color: viewMode === mode ? 'var(--text)' : 'var(--nav-muted)',
              background: viewMode === mode ? 'var(--overlay-09)' : 'transparent',
              transition: 'all 0.12s',
            }}
          >
            {icon}
          </button>
        ))}
      </div>
    </div>
  )
}
