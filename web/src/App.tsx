import { useEffect, useState } from 'react'
import { LibraryControls, TopBar } from './Shell'
import { loadCards, type CardPage } from './api'
import { CardTile } from './CardTile'

export default function App() {
  const [filterOpen, setFilterOpen] = useState(true)
  const [agentOpen, setAgentOpen] = useState(true)
  const [page, setPage] = useState(1)
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState<CardPage | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setData(null)
    loadCards(page, controller.signal).then(result => {
      if (!controller.signal.aborted) setData(result)
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to reach the card API.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [page, attempt])
  return <div className="mica-bg app-shell">
    <TopBar activeNav="Library" onNavChange={() => {}} />
    <div className="workspace">
      {filterOpen && <aside className="filter-panel" aria-label="Filters">
        <h2>FILTERS</h2><p>Filters are unavailable in Phase 1.</p><h3>POKÉMON TYPE</h3>
        {['Grass','Fire','Water','Lightning','Psychic','Fighting','Darkness','Metal','Dragon','Colorless'].map(type =>
          <label key={type}><input disabled type="checkbox"/> {type}</label>)}
        <p>Showing Standard Pokémon printings using TCGdex legality flags.</p>
      </aside>}
      <main>
        <LibraryControls category="pokemon" onCategoryChange={() => {}} scope="all" onScopeChange={() => {}}
          viewMode="gallery" onViewModeChange={() => {}} searchQuery="" onSearchChange={() => {}}
          filterOpen={filterOpen} onFilterToggle={() => setFilterOpen(v => !v)}
          totalCards={data?.total ?? 0} filteredCount={data?.cards.length ?? 0}/>
        <div className="source-note">TCGdex · local SQLite · Standard Pokémon
          {data && <span> · Sync: {data.sync.status}{data.sync.finished_at ? ` · ${data.sync.finished_at.slice(0, 10)}` : ''}</span>}
        </div>
        <section className="gallery-scroll" aria-label="Card gallery" aria-busy={loading}>
          {loading && <p role="status">Loading cards…</p>}
          {error && <div role="alert"><h2>Cards could not be loaded</h2><p>{error}</p><button onClick={() => setAttempt(v => v+1)}>Retry</button></div>}
          {data && !data.cards.length && <p>No Standard Pokémon printings on this page.</p>}
          {data && <div className="card-grid">{data.cards.map(card => <CardTile key={card.id} card={card}/>)}</div>}
        </section>
        <nav className="pagination" aria-label="Pagination">
          <button disabled={loading || page === 1} onClick={() => setPage(v => v-1)}>Previous</button>
          <span>Page {page}{data ? ` of ${Math.max(1, Math.ceil(data.total/data.page_size))}` : ''}</span>
          <button disabled={loading || !data?.next_page} onClick={() => setPage(data!.next_page!)}>Next</button>
        </nav>
      </main>
      <aside className={`agent-panel ${agentOpen ? '' : 'collapsed'}`} aria-label="PokéLab Agent">
        <button aria-expanded={agentOpen} onClick={() => setAgentOpen(v => !v)}>{agentOpen ? 'PokéLab Agent  ›' : '‹'}</button>
        {agentOpen && <p>The Agent workspace is preserved for a later slice. No AI provider is connected.</p>}
      </aside>
    </div>
  </div>
}
