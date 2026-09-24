import { useState } from 'react'
import type { Card } from './api'
export function CardTile({ card }: { card: Card }) {
  const [failed, setFailed] = useState(false)
  return <article className="card-tile" data-printing-id={card.id}>
    <div className="card-art">
      {card.image_url && !failed
        ? <img src={card.image_url} alt={`${card.name} — ${card.id}`} loading="lazy" onError={() => setFailed(true)}/>
        : <div className="image-fallback" role="img" aria-label={`${card.name}: image unavailable`}><strong>{card.name}</strong><span>Image unavailable</span><small>{card.id}</small></div>}
    </div>
    <strong title={card.name}>{card.name}</strong>
    <div className="printing">{card.set.name || card.set.id} · {card.localId}</div>
    <code>{card.id}</code>
    <div className="card-details">{[card.stage, card.types?.join(' / '), card.hp ? `${card.hp} HP` : null].filter(Boolean).join(' · ')}</div>
    <small title={`TCGdex Standard flag checked ${card.legality_provenance.checked_at}`}>Standard · {card.regulationMark || 'No regulation mark supplied'}</small>
  </article>
}
