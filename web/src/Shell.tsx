// Retained from approved Figma source e3d410e; unsupported controls are disabled.
type ViewMode = 'gallery' | 'list'
type Category = 'pokemon' | 'trainers' | 'energy'
type Scope = 'all' | 'owned' | 'unowned'
export function TopBar({ activeNav, onNavChange }: { activeNav: string; onNavChange: (n: string) => void }) {
  return (
    <div style={{
      height: 48, display: 'flex', alignItems: 'center', padding: '0 16px',
      borderBottom: '1px solid rgba(255,255,255,0.07)',
      background: 'rgba(11,13,19,0.95)', flexShrink: 0, gap: 0, zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 32 }}>
        <div style={{
          width: 26, height: 26, borderRadius: 7, background: 'linear-gradient(135deg, #7c3aed, #5b21b6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          boxShadow: '0 2px 8px rgba(124,58,237,0.35)',
        }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', fontFamily: 'Outfit' }}>PL</span>
        </div>
        <span style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0', fontFamily: 'Outfit', letterSpacing: '-0.01em' }}>
          Poké<span style={{ color: '#8b5cf6' }}>Lab</span>
        </span>
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {['Library', 'Collection', 'Analytics'].map(nav => (
          <button
            key={nav}
            disabled={nav !== "Library"} onClick={() => onNavChange(nav)}
            style={{
              padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: activeNav === nav ? 600 : 400,
              color: activeNav === nav ? '#e2e8f0' : '#6b7280',
              background: activeNav === nav ? 'rgba(255,255,255,0.08)' : 'transparent',
              transition: 'all 0.12s', fontFamily: 'Inter',
            }}
          >
            {nav}
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }}/>

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{color:'#8892a4',fontSize:11}}>Library · Phase 2</span>
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
    <div style={{
      height: 52, display: 'flex', alignItems: 'center', padding: '0 16px',
      borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0, gap: 12,
      background: 'rgba(11,13,19,0.6)',
    }}>
      {/* Filter toggle */}
      <button
        onClick={onFilterToggle}
        style={{
          width: 30, height: 30, borderRadius: 6, border: `1px solid ${filterOpen ? 'rgba(124,58,237,0.4)' : 'rgba(255,255,255,0.08)'}`,
          background: filterOpen ? 'rgba(124,58,237,0.14)' : 'rgba(255,255,255,0.04)',
          color: filterOpen ? '#a78bfa' : '#6b7280', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13,
        }}
        aria-label="Toggle filters" aria-expanded={filterOpen} title="Toggle filters"
      >
        ⊞
      </button>

      {/* Category tabs */}
      <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', borderRadius: 7, padding: 2, border: '1px solid rgba(255,255,255,0.07)' }}>
        {(['pokemon', 'trainers', 'energy'] as Category[]).map(cat => (
          <button
            key={cat}
            aria-pressed={category === cat} onClick={() => onCategoryChange(cat)}
            style={{
              padding: '4px 14px', borderRadius: 5, border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: category === cat ? 600 : 400,
              color: category === cat ? '#dde1ed' : '#6b7280',
              background: category === cat ? 'rgba(255,255,255,0.09)' : 'transparent',
              transition: 'all 0.12s', textTransform: 'capitalize', fontFamily: 'Inter',
            }}
          >
            {cat === 'pokemon' ? 'Pokémon' : cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* Scope */}
      <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', borderRadius: 7, padding: 2, border: '1px solid rgba(255,255,255,0.07)' }}>
        {(['all', 'owned', 'unowned'] as Scope[]).map(s => (
          <button
            key={s}
            disabled onClick={() => onScopeChange(s)}
            style={{
              padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: scope === s ? 600 : 400,
              color: scope === s ? '#dde1ed' : '#6b7280',
              background: scope === s ? 'rgba(255,255,255,0.09)' : 'transparent',
              transition: 'all 0.12s', textTransform: 'capitalize', fontFamily: 'Inter',
            }}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Card count */}
      <span style={{ fontSize: 11, color: '#505c70', fontFamily: 'JetBrains Mono', flexShrink: 0 }}>
        {filteredCount}/{totalCards}
      </span>

      {/* Search */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', gap: 8, maxWidth: 320,
        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
        borderRadius: 7, padding: '0 10px', height: 30,
      }}>
        <span style={{ color: '#505c70', fontSize: 12, flexShrink: 0 }}>⌕</span>
        <input
          aria-label="Search cards" maxLength={100} value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Search cards…"
          style={{
            flex: 1, background: 'none', border: 'none', outline: 'none',
            fontSize: 12, color: '#dde1ed', fontFamily: 'Inter',
          }}
        />
        {searchQuery && (
          <button aria-label="Clear search" onClick={() => onSearchChange('')} style={{ background: 'none', border: 'none', color: '#505c70', cursor: 'pointer', fontSize: 13, padding: 0 }}>×</button>
        )}
      </div>

      <div style={{ flex: 1 }}/>

      {/* View mode */}
      <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', borderRadius: 7, padding: 2, border: '1px solid rgba(255,255,255,0.07)' }}>
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
              fontSize: 14, color: viewMode === mode ? '#dde1ed' : '#6b7280',
              background: viewMode === mode ? 'rgba(255,255,255,0.09)' : 'transparent',
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
