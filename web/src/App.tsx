import { useState, useRef, useCallback, useEffect, CSSProperties } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type PokemonType = 'Grass' | 'Fire' | 'Water' | 'Lightning' | 'Psychic' | 'Fighting' | 'Darkness' | 'Metal' | 'Dragon' | 'Colorless'
type ViewMode = 'gallery' | 'list'
type Category = 'pokemon' | 'trainers' | 'energy'
type Scope = 'all' | 'owned' | 'unowned'

interface CardData {
  id: number
  name: string
  type: PokemonType
  set: string
  num: string
  hp: number
  stage: string
  baseQty: number
  price: number
  usagePct: number
  avgCopies: number
  decklistsAnalyzed: number
  excluded: number
  archetypes: { name: string; pct: number }[]
}

interface TooltipState {
  card: CardData
  x: number
  y: number
  side: 'right' | 'left'
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_INFO: Record<PokemonType, { accent: string; bg: string; text: string; dim: string }> = {
  Grass:     { accent: '#4ade80', bg: '#071a0f', text: '#86efac', dim: '#4ade8025' },
  Fire:      { accent: '#f97316', bg: '#1c0a02', text: '#fdba74', dim: '#f9731625' },
  Water:     { accent: '#38bdf8', bg: '#041422', text: '#7dd3fc', dim: '#38bdf825' },
  Lightning: { accent: '#fbbf24', bg: '#1a1000', text: '#fde68a', dim: '#fbbf2425' },
  Psychic:   { accent: '#e879f9', bg: '#1a0520', text: '#f0abfc', dim: '#e879f925' },
  Fighting:  { accent: '#ef4444', bg: '#1a0505', text: '#fca5a5', dim: '#ef444425' },
  Darkness:  { accent: '#a78bfa', bg: '#0d0a1a', text: '#c4b5fd', dim: '#a78bfa25' },
  Metal:     { accent: '#94a3b8', bg: '#0f1420', text: '#cbd5e1', dim: '#94a3b825' },
  Dragon:    { accent: '#818cf8', bg: '#0a0d1f', text: '#a5b4fc', dim: '#818cf825' },
  Colorless: { accent: '#d1d5db', bg: '#111318', text: '#e5e7eb', dim: '#d1d5db18' },
}

const ALL_TYPES: PokemonType[] = ['Grass', 'Fire', 'Water', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal', 'Dragon', 'Colorless']

const CARDS: CardData[] = [
  { id: 1,  name: 'Dragapult ex',    type: 'Dragon',    set: 'TWM', num: '130/167', hp: 320, stage: 'Basic',   baseQty: 4, price: 28.50, usagePct: 41.2, avgCopies: 3.9, decklistsAnalyzed: 1112, excluded: 98,  archetypes: [{ name: 'Dragapult', pct: 100 }, { name: 'Dragon Ctrl', pct: 82.1 }, { name: 'Turbo Dragon', pct: 61.4 }, { name: 'Miraidon', pct: 12.3 }, { name: 'Charizard', pct: 8.9 }] },
  { id: 2,  name: 'Night Stretcher', type: 'Colorless', set: 'SFA', num: '061/072', hp: 0,   stage: 'Item',    baseQty: 2, price: 14.25, usagePct: 38.7, avgCopies: 1.6, decklistsAnalyzed: 1112, excluded: 315, archetypes: [{ name: 'Dragapult', pct: 73.1 }, { name: 'Raging Bolt', pct: 61.8 }, { name: 'Gardevoir', pct: 58.4 }, { name: 'Alakazam', pct: 42.7 }, { name: 'Charizard', pct: 39.2 }] },
  { id: 3,  name: 'Gardevoir ex',    type: 'Psychic',   set: 'PAR', num: '086/182', hp: 310, stage: 'Stage 2', baseQty: 2, price: 18.75, usagePct: 29.4, avgCopies: 3.8, decklistsAnalyzed: 987,  excluded: 143, archetypes: [{ name: 'Gardevoir', pct: 100 }, { name: 'Garde-Scream', pct: 74.3 }, { name: 'Psychic Box', pct: 41.8 }, { name: 'Lost Zone Garde', pct: 28.5 }, { name: 'Mirror Match', pct: 21.2 }] },
  { id: 4,  name: 'Raging Bolt ex',  type: 'Lightning', set: 'TEF', num: '123/162', hp: 280, stage: 'Basic',   baseQty: 2, price: 22.00, usagePct: 24.6, avgCopies: 3.7, decklistsAnalyzed: 843,  excluded: 201, archetypes: [{ name: 'Raging Bolt', pct: 100 }, { name: 'Bolt Tina', pct: 67.4 }, { name: 'Miraidon Bolt', pct: 44.1 }, { name: 'Lightning Box', pct: 31.8 }, { name: 'Turbo', pct: 22.9 }] },
  { id: 5,  name: 'Charizard ex',    type: 'Fire',      set: 'OBF', num: '125/197', hp: 330, stage: 'Stage 2', baseQty: 1, price: 45.00, usagePct: 31.8, avgCopies: 3.9, decklistsAnalyzed: 1089, excluded: 187, archetypes: [{ name: 'Charizard', pct: 100 }, { name: 'Char-Pidgeot', pct: 88.6 }, { name: 'Char-Rotom', pct: 62.3 }, { name: 'Char-Lost Zone', pct: 37.1 }, { name: 'Fire Box', pct: 22.8 }] },
  { id: 6,  name: 'Pidgeot ex',      type: 'Colorless', set: 'OBF', num: '164/197', hp: 280, stage: 'Stage 2', baseQty: 2, price: 9.50,  usagePct: 58.2, avgCopies: 1.9, decklistsAnalyzed: 1098, excluded: 212, archetypes: [{ name: 'Charizard', pct: 88.6 }, { name: 'Gardevoir', pct: 61.4 }, { name: 'Dragapult', pct: 52.3 }, { name: 'Buddy-Buddy Pult', pct: 41.7 }, { name: 'Control', pct: 38.9 }] },
  { id: 7,  name: 'Miraidon ex',     type: 'Lightning', set: 'SVI', num: '081/198', hp: 220, stage: 'Basic',   baseQty: 0, price: 12.00, usagePct: 19.3, avgCopies: 3.8, decklistsAnalyzed: 661,  excluded: 122, archetypes: [{ name: 'Miraidon', pct: 100 }, { name: 'Miraidon Tina', pct: 71.3 }, { name: 'Bolt Miraidon', pct: 48.2 }, { name: 'Raichu Bench', pct: 28.4 }, { name: 'Speed Lightning', pct: 19.6 }] },
  { id: 8,  name: 'Chien-Pao ex',    type: 'Water',     set: 'PAL', num: '061/193', hp: 230, stage: 'Basic',   baseQty: 3, price: 8.75,  usagePct: 15.7, avgCopies: 3.9, decklistsAnalyzed: 539,  excluded: 98,  archetypes: [{ name: 'Chien-Pao', pct: 100 }, { name: 'Bax Chien', pct: 87.4 }, { name: 'Ice Rider', pct: 44.1 }, { name: 'Water Box', pct: 28.6 }, { name: 'Serperior', pct: 12.3 }] },
  { id: 9,  name: 'Baxcalibur',      type: 'Water',     set: 'PAL', num: '060/193', hp: 180, stage: 'Stage 2', baseQty: 2, price: 6.25,  usagePct: 14.9, avgCopies: 1.8, decklistsAnalyzed: 511,  excluded: 88,  archetypes: [{ name: 'Chien-Pao', pct: 87.4 }, { name: 'Kyurem', pct: 63.2 }, { name: 'Ice Rider', pct: 51.8 }, { name: 'Water Toolbox', pct: 31.4 }, { name: 'Bax Control', pct: 24.7 }] },
  { id: 10, name: 'Iron Hands ex',   type: 'Lightning', set: 'PAR', num: '070/182', hp: 230, stage: 'Basic',   baseQty: 0, price: 16.00, usagePct: 11.4, avgCopies: 2.1, decklistsAnalyzed: 391,  excluded: 74,  archetypes: [{ name: 'Iron Thorns', pct: 78.3 }, { name: 'Hands FTW', pct: 64.1 }, { name: 'Lightning Box', pct: 42.8 }, { name: 'Durant Lock', pct: 31.2 }, { name: 'Future Box', pct: 18.6 }] },
  { id: 11, name: 'Roaring Moon ex', type: 'Darkness',  set: 'PAR', num: '105/182', hp: 270, stage: 'Basic',   baseQty: 2, price: 19.25, usagePct: 22.1, avgCopies: 3.8, decklistsAnalyzed: 758,  excluded: 141, archetypes: [{ name: 'Roaring Moon', pct: 100 }, { name: 'Moon Tomb', pct: 78.4 }, { name: 'Cornerstone', pct: 41.3 }, { name: 'Dark Box', pct: 28.7 }, { name: 'Paradox Ctrl', pct: 21.4 }] },
  { id: 12, name: 'Espathra ex',     type: 'Psychic',   set: 'PAL', num: '093/193', hp: 270, stage: 'Stage 1', baseQty: 1, price: 7.50,  usagePct: 8.3,  avgCopies: 3.7, decklistsAnalyzed: 285,  excluded: 52,  archetypes: [{ name: 'Espathra', pct: 100 }, { name: 'Gardevoir', pct: 22.4 }, { name: 'Psych Box', pct: 18.7 }, { name: 'Speed Esp', pct: 88.3 }, { name: 'Control', pct: 11.6 }] },
  { id: 13, name: 'Armarouge ex',    type: 'Fire',      set: 'PAR', num: '026/182', hp: 280, stage: 'Stage 2', baseQty: 0, price: 5.50,  usagePct: 6.1,  avgCopies: 3.6, decklistsAnalyzed: 209,  excluded: 41,  archetypes: [{ name: 'Armarouge', pct: 100 }, { name: 'Future Box', pct: 41.3 }, { name: 'Charizard', pct: 18.2 }, { name: 'Fire Box', pct: 71.4 }, { name: 'Torch', pct: 28.9 }] },
  { id: 14, name: 'Sandy Shocks ex', type: 'Lightning', set: 'PAR', num: '072/182', hp: 230, stage: 'Basic',   baseQty: 1, price: 4.75,  usagePct: 5.8,  avgCopies: 1.4, decklistsAnalyzed: 199,  excluded: 38,  archetypes: [{ name: 'Sandy Shocks', pct: 100 }, { name: 'Miraidon', pct: 31.4 }, { name: 'Lightning Box', pct: 27.8 }, { name: 'Paradox Mix', pct: 41.6 }, { name: 'Raging Bolt', pct: 18.3 }] },
  { id: 15, name: 'Greninja ex',     type: 'Water',     set: 'TWM', num: '134/167', hp: 280, stage: 'Stage 2', baseQty: 2, price: 11.00, usagePct: 13.7, avgCopies: 3.8, decklistsAnalyzed: 470,  excluded: 91,  archetypes: [{ name: 'Greninja', pct: 100 }, { name: 'Frog Box', pct: 71.4 }, { name: 'Water Ctrl', pct: 48.3 }, { name: 'Chien-Pao', pct: 22.7 }, { name: 'Ancient Box', pct: 16.4 }] },
  { id: 16, name: 'Snorlax',         type: 'Colorless', set: 'SVI', num: '143/198', hp: 150, stage: 'Basic',   baseQty: 3, price: 2.25,  usagePct: 7.4,  avgCopies: 1.2, decklistsAnalyzed: 254,  excluded: 47,  archetypes: [{ name: 'Control', pct: 62.4 }, { name: 'Durant Lock', pct: 41.8 }, { name: 'Snorlax Stall', pct: 88.3 }, { name: 'Big Body', pct: 31.4 }, { name: 'Budget Ctrl', pct: 21.7 }] },
  { id: 17, name: 'Mew ex',          type: 'Psychic',   set: 'MEW', num: '151/165', hp: 180, stage: 'Basic',   baseQty: 2, price: 32.00, usagePct: 26.4, avgCopies: 3.9, decklistsAnalyzed: 906,  excluded: 168, archetypes: [{ name: 'Mew VMAX', pct: 81.4 }, { name: 'Psychic Turbo', pct: 58.3 }, { name: 'Gardevoir', pct: 31.7 }, { name: 'Mew Tech', pct: 44.2 }, { name: 'Lugia', pct: 21.8 }] },
  { id: 18, name: 'Lugia V',         type: 'Colorless', set: 'SIT', num: '138/195', hp: 220, stage: 'Basic',   baseQty: 1, price: 8.00,  usagePct: 12.8, avgCopies: 3.8, decklistsAnalyzed: 439,  excluded: 81,  archetypes: [{ name: 'Lugia VSTAR', pct: 100 }, { name: 'Lugia Ctrl', pct: 64.3 }, { name: 'Turbo Lugia', pct: 47.8 }, { name: 'Colorless Box', pct: 28.4 }, { name: 'Legacy', pct: 18.2 }] },
  { id: 19, name: 'Giratina V',      type: 'Dragon',    set: 'LOR', num: '186/196', hp: 220, stage: 'Basic',   baseQty: 2, price: 6.50,  usagePct: 11.2, avgCopies: 3.7, decklistsAnalyzed: 384,  excluded: 71,  archetypes: [{ name: 'Giratina VSTAR', pct: 100 }, { name: 'Lost Box', pct: 68.4 }, { name: 'Dragon Ctrl', pct: 41.3 }, { name: 'Tina Comfy', pct: 78.2 }, { name: 'Chaos', pct: 31.6 }] },
  { id: 20, name: 'Kyurem V',        type: 'Water',     set: 'SIT', num: '048/195', hp: 230, stage: 'Basic',   baseQty: 0, price: 4.25,  usagePct: 9.4,  avgCopies: 3.8, decklistsAnalyzed: 323,  excluded: 59,  archetypes: [{ name: 'Kyurem VMAX', pct: 100 }, { name: 'Ice Wall', pct: 73.4 }, { name: 'Bax Kyurem', pct: 58.2 }, { name: 'Water Box', pct: 34.7 }, { name: 'Blizzard', pct: 22.1 }] },
  { id: 21, name: 'Mewtwo V',        type: 'Psychic',   set: 'CRZ', num: '076/159', hp: 220, stage: 'Basic',   baseQty: 3, price: 7.75,  usagePct: 10.7, avgCopies: 3.7, decklistsAnalyzed: 368,  excluded: 68,  archetypes: [{ name: 'Mewtwo VUNION', pct: 100 }, { name: 'Gardevoir', pct: 28.4 }, { name: 'Psych Box', pct: 41.8 }, { name: 'Union Power', pct: 81.3 }, { name: 'Control', pct: 18.7 }] },
  { id: 22, name: 'Darkrai V',       type: 'Darkness',  set: 'ASR', num: '098/189', hp: 220, stage: 'Basic',   baseQty: 2, price: 5.25,  usagePct: 7.8,  avgCopies: 3.7, decklistsAnalyzed: 268,  excluded: 49,  archetypes: [{ name: 'Darkrai VSTAR', pct: 100 }, { name: 'Dark Box', pct: 68.4 }, { name: 'Roaring Moon', pct: 28.3 }, { name: 'Turbo Dark', pct: 51.7 }, { name: 'Control', pct: 19.4 }] },
  { id: 23, name: 'Rayquaza V',      type: 'Dragon',    set: 'CRE', num: '110/198', hp: 220, stage: 'Basic',   baseQty: 1, price: 5.75,  usagePct: 6.8,  avgCopies: 3.6, decklistsAnalyzed: 234,  excluded: 43,  archetypes: [{ name: 'Rayquaza VMAX', pct: 100 }, { name: 'Sky High', pct: 78.4 }, { name: 'Dragon Box', pct: 43.2 }, { name: 'Storm', pct: 61.7 }, { name: 'Ancient Dragon', pct: 18.4 }] },
  { id: 24, name: 'Dialga V',        type: 'Metal',     set: 'ASR', num: '058/189', hp: 220, stage: 'Basic',   baseQty: 0, price: 5.00,  usagePct: 5.1,  avgCopies: 3.5, decklistsAnalyzed: 175,  excluded: 32,  archetypes: [{ name: 'Dialga VSTAR', pct: 100 }, { name: 'Time Control', pct: 74.3 }, { name: 'Metal Box', pct: 51.8 }, { name: 'Origin Forme', pct: 87.2 }, { name: 'Turbo Steel', pct: 28.4 }] },
]

// ─── Card Art SVG ─────────────────────────────────────────────────────────────

function CardArt({ type }: { type: PokemonType }) {
  const { accent, bg } = TYPE_INFO[type]
  const a = accent

  const patterns: Record<PokemonType, JSX.Element> = {
    Dragon: (
      <g>
        <defs><radialGradient id={`rg-dragon`} cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor={`${a}35`}/><stop offset="100%" stopColor="transparent"/></radialGradient></defs>
        <g stroke={`${a}28`} strokeWidth="0.7" fill="none">
          {[-20,10,40,70,100].map(ox => [0,35,70].map(oy => <polygon key={`${ox}-${oy}`} points={`${ox+15},${oy} ${ox+30},${oy+17} ${ox+15},${oy+34} ${ox},${oy+17}`}/>)).flat()}
        </g>
        <rect width="100" height="70" fill={`url(#rg-dragon)`}/>
        <polygon points="50,18 65,35 50,52 35,35" fill="none" stroke={`${a}55`} strokeWidth="1"/>
        <polygon points="50,24 60,35 50,46 40,35" fill={`${a}18`} stroke={`${a}40`} strokeWidth="0.8"/>
      </g>
    ),
    Psychic: (
      <g>
        <defs><radialGradient id={`rg-psy`} cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor={`${a}40`}/><stop offset="100%" stopColor="transparent"/></radialGradient></defs>
        {[8,16,24,32,40].map(r => <circle key={r} cx="50" cy="35" r={r} stroke={`${a}${r < 20 ? '45' : '25'}`} strokeWidth="0.7" fill="none"/>)}
        <rect width="100" height="70" fill={`url(#rg-psy)`}/>
        {[0,60,120,180,240,300].map(deg => {
          const rad = deg * Math.PI / 180
          const x1 = 50 + Math.cos(rad) * 6, y1 = 35 + Math.sin(rad) * 6
          const x2 = 50 + Math.cos(rad) * 43, y2 = 35 + Math.sin(rad) * 43
          return <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} stroke={`${a}20`} strokeWidth="0.5"/>
        })}
        <circle cx="50" cy="35" r="4" fill={`${a}60`}/>
      </g>
    ),
    Fire: (
      <g>
        <defs><linearGradient id={`rg-fire`} x1="0%" y1="100%" x2="0%" y2="0%"><stop offset="0%" stopColor={`${a}50`}/><stop offset="100%" stopColor="transparent"/></linearGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-fire)`}/>
        <polygon points="22,70 32,40 42,55 52,25 62,45 72,35 82,70" fill={`${a}22`} stroke={`${a}35`} strokeWidth="0.8"/>
        <polygon points="35,70 45,42 55,55 65,30 75,50 80,70" fill={`${a}15`} stroke={`${a}28`} strokeWidth="0.7"/>
        <polygon points="45,70 52,38 60,52 68,28 76,70" fill={`${a}30`} stroke={`${a}45`} strokeWidth="0.9"/>
      </g>
    ),
    Water: (
      <g>
        <defs><linearGradient id={`rg-water`} x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stopColor="transparent"/><stop offset="100%" stopColor={`${a}30`}/></linearGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-water)`}/>
        {[15,25,35,45,55].map((y, i) => (
          <path key={y} d={`M0,${y} Q12.5,${y - 8 + i*2} 25,${y} Q37.5,${y + 8 - i*2} 50,${y} Q62.5,${y - 8 + i*2} 75,${y} Q87.5,${y + 8 - i*2} 100,${y}`}
            stroke={`${a}${i < 2 ? '35' : '22'}`} strokeWidth="0.8" fill="none"/>
        ))}
        <ellipse cx="50" cy="40" rx="18" ry="12" fill={`${a}15`} stroke={`${a}30`} strokeWidth="0.7"/>
      </g>
    ),
    Lightning: (
      <g>
        <defs><radialGradient id={`rg-light`} cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor={`${a}50`}/><stop offset="100%" stopColor="transparent"/></radialGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-light)`}/>
        <g stroke={`${a}20`} strokeWidth="0.5" fill="none">
          {[10,30,50,70,90].map(x => <line key={x} x1={x} y1="0" x2={x-5} y2="70"/>)}
        </g>
        <path d="M57,5 L43,32 L54,32 L40,65 L67,28 L55,28 Z" fill={`${a}30`} stroke={`${a}60`} strokeWidth="1"/>
        <path d="M57,5 L43,32 L54,32 L40,65" fill="none" stroke={`${a}80`} strokeWidth="1.2"/>
      </g>
    ),
    Fighting: (
      <g>
        <defs><radialGradient id={`rg-fight`} cx="50%" cy="70%" r="60%"><stop offset="0%" stopColor={`${a}40`}/><stop offset="100%" stopColor="transparent"/></radialGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-fight)`}/>
        <g stroke={`${a}35`} strokeWidth="1" fill="none" strokeLinecap="round">
          <line x1="20" y1="55" x2="80" y2="15"/>
          <line x1="20" y1="15" x2="80" y2="55"/>
        </g>
        <g stroke={`${a}22`} strokeWidth="0.6" fill="none">
          <polygon points="50,8 70,35 50,62 30,35"/>
          <polygon points="50,18 62,35 50,52 38,35"/>
        </g>
        <circle cx="50" cy="35" r="5" fill={`${a}35`}/>
      </g>
    ),
    Darkness: (
      <g>
        <defs><radialGradient id={`rg-dark`} cx="50%" cy="50%" r="60%"><stop offset="0%" stopColor={`${a}35`}/><stop offset="70%" stopColor={`${a}10`}/><stop offset="100%" stopColor="transparent"/></radialGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-dark)`}/>
        {Array.from({length: 18}, (_, i) => {
          const x = (i * 31 + 7) % 95 + 2
          const y = (i * 17 + 11) % 65 + 2
          const r = (i % 4) * 0.6 + 0.4
          return <circle key={i} cx={x} cy={y} r={r} fill={`${a}40`}/>
        })}
        <circle cx="50" cy="35" r="14" fill="none" stroke={`${a}35`} strokeWidth="0.8"/>
        <circle cx="50" cy="35" r="7" fill={`${a}25`} stroke={`${a}45`} strokeWidth="0.7"/>
      </g>
    ),
    Metal: (
      <g>
        <defs><linearGradient id={`rg-metal`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor={`${a}35`}/><stop offset="100%" stopColor={`${a}15`}/></linearGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-metal)`}/>
        {Array.from({length: 5}, (_, col) => Array.from({length: 4}, (_, row) => {
          const cx = col * 20 + 10, cy = row * 18 + 8
          return <polygon key={`${col}-${row}`} points={`${cx},${cy-7} ${cx+6},${cy-3} ${cx+6},${cy+3} ${cx},${cy+7} ${cx-6},${cy+3} ${cx-6},${cy-3}`}
            fill="none" stroke={`${a}30`} strokeWidth="0.6"/>
        })).flat()}
        <circle cx="50" cy="35" r="12" fill={`${a}20`} stroke={`${a}50`} strokeWidth="1"/>
        <circle cx="50" cy="35" r="5" fill={`${a}40`}/>
      </g>
    ),
    Grass: (
      <g>
        <defs><radialGradient id={`rg-grass`} cx="50%" cy="80%" r="60%"><stop offset="0%" stopColor={`${a}35`}/><stop offset="100%" stopColor="transparent"/></radialGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-grass)`}/>
        <path d="M50,65 C50,65 30,50 28,35 C26,20 40,8 50,5 C60,8 74,20 72,35 C70,50 50,65 50,65Z" fill={`${a}22`} stroke={`${a}40`} strokeWidth="0.8"/>
        <path d="M50,65 C45,55 20,55 15,40 C10,25 25,10 35,12" fill="none" stroke={`${a}30`} strokeWidth="0.8"/>
        <path d="M50,65 C55,55 80,55 85,40 C90,25 75,10 65,12" fill="none" stroke={`${a}25`} strokeWidth="0.7"/>
        <line x1="50" y1="65" x2="50" y2="12" stroke={`${a}35`} strokeWidth="0.7"/>
      </g>
    ),
    Colorless: (
      <g>
        <defs><radialGradient id={`rg-col`} cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor={`${a}25`}/><stop offset="100%" stopColor={`${a}08`}/></radialGradient></defs>
        <rect width="100" height="70" fill={`url(#rg-col)`}/>
        <g stroke={`${a}18`} strokeWidth="0.5" fill="none">
          {[15,30,45,60,75,90].map(x => <line key={x} x1={x} y1="0" x2={x} y2="70"/>)}
          {[10,20,30,40,50,60].map(y => <line key={y} x1="0" y1={y} x2="100" y2={y}/>)}
        </g>
        <circle cx="50" cy="35" r="16" fill="none" stroke={`${a}30`} strokeWidth="0.8"/>
        <circle cx="50" cy="35" r="8" fill={`${a}20`} stroke={`${a}40`} strokeWidth="0.7"/>
      </g>
    ),
  }

  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: bg }}>
      <svg viewBox="0 0 100 70" className="absolute inset-0 w-full h-full" preserveAspectRatio="xMidYMid slice">
        {patterns[type]}
      </svg>
    </div>
  )
}

// ─── Card Frame (TCG proportions) ─────────────────────────────────────────────

function CardFrame({ card, small = false }: { card: CardData; small?: boolean }) {
  const { accent, text, dim } = TYPE_INFO[card.type]
  const f = small ? 0.75 : 1

  return (
    <div style={{
      width: '100%', aspectRatio: '5/7',
      borderRadius: small ? 6 : 8,
      border: `1.5px solid ${accent}50`,
      background: TYPE_INFO[card.type].bg,
      overflow: 'hidden', display: 'flex', flexDirection: 'column',
      boxShadow: `0 4px 20px ${accent}18, inset 0 1px 0 ${accent}20`,
      position: 'relative',
    }}>
      {/* Card header */}
      <div style={{
        padding: `${3*f}px ${6*f}px`, display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', borderBottom: `1px solid ${accent}25`,
        background: `${accent}10`, flexShrink: 0,
      }}>
        <span style={{ fontSize: `${7*f}px`, color: text, fontFamily: 'JetBrains Mono', fontWeight: 600, letterSpacing: '0.06em' }}>
          {card.type.toUpperCase()}
        </span>
        {card.hp > 0 && (
          <span style={{ fontSize: `${8*f}px`, color: text, fontWeight: 700, fontFamily: 'JetBrains Mono' }}>
            {card.hp} HP
          </span>
        )}
        {card.hp === 0 && (
          <span style={{ fontSize: `${7*f}px`, color: `${text}80`, fontFamily: 'JetBrains Mono' }}>
            ITEM
          </span>
        )}
      </div>

      {/* Art area */}
      <div style={{ flex: '0 0 44%', margin: `${4*f}px ${5*f}px`, borderRadius: 4, overflow: 'hidden', border: `1px solid ${accent}20` }}>
        <CardArt type={card.type} />
      </div>

      {/* Name strip */}
      <div style={{
        padding: `${3*f}px ${6*f}px`, background: `${accent}12`,
        borderTop: `1px solid ${accent}22`, borderBottom: `1px solid ${accent}18`,
        flexShrink: 0,
      }}>
        <div style={{ fontSize: `${8.5*f}px`, color: text, fontWeight: 700, fontFamily: 'Outfit', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {card.name}
        </div>
        <div style={{ fontSize: `${6*f}px`, color: `${text}70`, marginTop: 1 }}>
          {card.stage} · Pokémon
        </div>
      </div>

      {/* Text lines placeholder */}
      <div style={{ flex: 1, padding: `${5*f}px ${6*f}px`, display: 'flex', flexDirection: 'column', gap: `${3*f}px`, justifyContent: 'center' }}>
        <div style={{ height: `${2*f}px`, background: dim, borderRadius: 1 }}/>
        <div style={{ height: `${2*f}px`, background: dim, borderRadius: 1, width: '85%' }}/>
        <div style={{ height: `${3*f}px` }}/>
        <div style={{ height: `${2*f}px`, background: `${accent}20`, borderRadius: 1 }}/>
        <div style={{ height: `${2*f}px`, background: `${accent}15`, borderRadius: 1, width: '70%' }}/>
        <div style={{ height: `${2*f}px`, background: `${accent}15`, borderRadius: 1, width: '90%' }}/>
      </div>

      {/* Footer */}
      <div style={{
        padding: `${3*f}px ${6*f}px`, borderTop: `1px solid ${accent}15`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
      }}>
        <span style={{ fontSize: `${5.5*f}px`, color: `${text}55`, fontFamily: 'JetBrains Mono' }}>
          {card.set} {card.num}
        </span>
        <span style={{ fontSize: `${5.5*f}px`, color: `${text}40` }}>©</span>
      </div>
    </div>
  )
}

// ─── Analytics Tooltip ────────────────────────────────────────────────────────

function AnalyticsTooltip({
  tooltip, onEnter, onLeave,
}: {
  tooltip: TooltipState
  onEnter: () => void
  onLeave: () => void
}) {
  const { card, x, y, side } = tooltip
  const TOOLTIP_W = 272

  return (
    <div
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      style={{
        position: 'fixed', top: y, left: x, width: TOOLTIP_W, zIndex: 9999,
        background: '#151822', border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 10, boxShadow: '0 16px 48px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04)',
        overflow: 'hidden', fontFamily: 'Inter',
        animation: 'fadeIn 0.15s ease',
      }}
    >
      {/* Header */}
      <div style={{ padding: '12px 14px 10px', borderBottom: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <div style={{ width: 3, height: 14, background: '#8b5cf6', borderRadius: 2 }}/>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#dde1ed', fontFamily: 'Outfit', letterSpacing: '0.02em' }}>
            {card.name.toUpperCase()}
          </span>
        </div>
        <div style={{ fontSize: 10, color: '#6b7280', letterSpacing: '0.05em', marginLeft: 9 }}>
          COMPETITIVE STANDARD ANALYTICS
        </div>
      </div>

      {/* Stats grid */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        {[
          ['Overall usage', `${card.usagePct}%`],
          ['Average copies', card.avgCopies.toFixed(1)],
          ['Decklists analyzed', card.decklistsAnalyzed.toLocaleString()],
          ['Excluded / unresolved', card.excluded.toLocaleString()],
        ].map(([label, value]) => (
          <div key={label as string} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
            <span style={{ fontSize: 11, color: '#8892a4' }}>{label}</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#dde1ed', fontFamily: 'JetBrains Mono' }}>{value}</span>
          </div>
        ))}
      </div>

      {/* Archetypes */}
      <div style={{ padding: '10px 14px' }}>
        <div style={{ fontSize: 9, fontWeight: 600, color: '#505c70', letterSpacing: '0.08em', marginBottom: 7 }}>
          TOP ARCHETYPES
        </div>
        {card.archetypes.map(({ name, pct }) => (
          <div
            key={name}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, padding: '4px 6px',
              borderRadius: 5, cursor: 'pointer', transition: 'background 0.12s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.12)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                <span style={{ fontSize: 11, color: '#c4b5fd', fontWeight: 500 }}>{name}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontSize: 10, color: '#8892a4', fontFamily: 'JetBrains Mono' }}>{pct}%</span>
                  <span style={{ fontSize: 9, color: '#505c70' }}>→</span>
                </div>
              </div>
              <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 1 }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #7c3aed, #8b5cf6)', borderRadius: 1 }}/>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: '8px 14px 10px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 10, color: '#505c70' }}>Timeframe:</span>
        <button style={{
          fontSize: 10, color: '#a5b4fc', background: 'rgba(139,92,246,0.12)',
          border: '1px solid rgba(139,92,246,0.25)', borderRadius: 4, padding: '2px 8px',
          cursor: 'pointer', fontFamily: 'Inter',
        }}>
          Last 30 Days ▾
        </button>
      </div>

      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }`}</style>
    </div>
  )
}

// ─── Gallery Card Tile ────────────────────────────────────────────────────────

function CardTile({
  card, qty, onQtyChange, onHoverStart, onHoverEnd,
}: {
  card: CardData
  qty: number
  onQtyChange: (id: number, delta: number) => void
  onHoverStart: (card: CardData, el: HTMLElement) => void
  onHoverEnd: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  const { accent, text } = TYPE_INFO[card.type]

  return (
    <div
      ref={ref}
      onMouseEnter={() => ref.current && onHoverStart(card, ref.current)}
      onMouseLeave={onHoverEnd}
      style={{ display: 'flex', flexDirection: 'column', gap: 6, cursor: 'default' }}
    >
      <div style={{
        transition: 'transform 0.15s, box-shadow 0.15s',
        borderRadius: 8,
      }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)' }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = '' }}
      >
        <CardFrame card={card} />
      </div>

      {/* Card info */}
      <div style={{ padding: '0 2px' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#c8cee0', lineHeight: 1.3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {card.name}
        </div>
        <div style={{ fontSize: 10, color: '#505c70', fontFamily: 'JetBrains Mono', marginTop: 1 }}>
          {card.set} · {card.num}
        </div>
      </div>

      {/* Quantity control */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <button
          onClick={() => onQtyChange(card.id, -1)}
          style={{
            width: 22, height: 22, borderRadius: 4, border: '1px solid rgba(255,255,255,0.10)',
            background: 'rgba(255,255,255,0.04)', color: '#8892a4', fontSize: 13,
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            lineHeight: 1, transition: 'background 0.1s',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.08)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
        >−</button>
        <div style={{
          flex: 1, textAlign: 'center', fontSize: 12, fontWeight: 600,
          color: qty > 0 ? '#dde1ed' : '#505c70',
          fontFamily: 'JetBrains Mono', background: 'rgba(255,255,255,0.04)',
          borderRadius: 4, padding: '2px 0', border: `1px solid ${qty > 0 ? accent + '40' : 'rgba(255,255,255,0.06)'}`,
        }}>
          {qty}
        </div>
        <button
          onClick={() => onQtyChange(card.id, 1)}
          style={{
            width: 22, height: 22, borderRadius: 4, border: '1px solid rgba(255,255,255,0.10)',
            background: 'rgba(255,255,255,0.04)', color: '#8892a4', fontSize: 13,
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            lineHeight: 1, transition: 'background 0.1s',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.08)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
        >+</button>
      </div>
    </div>
  )
}

// ─── List Row ─────────────────────────────────────────────────────────────────

function CardRow({ card, qty, onQtyChange }: { card: CardData; qty: number; onQtyChange: (id: number, delta: number) => void }) {
  const { accent, text } = TYPE_INFO[card.type]
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'grid', gridTemplateColumns: '48px 1fr 110px 90px 72px 80px',
        alignItems: 'center', gap: 12, padding: '7px 16px',
        background: hovered ? 'rgba(255,255,255,0.03)' : 'transparent',
        borderBottom: '1px solid rgba(255,255,255,0.04)', cursor: 'default',
        transition: 'background 0.1s',
      }}
    >
      {/* Mini card thumbnail */}
      <div style={{ width: 34, aspectRatio: '5/7' }}>
        <CardFrame card={card} small />
      </div>

      {/* Name + type */}
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#dde1ed' }}>{card.name}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
          <span style={{
            fontSize: 9, fontWeight: 600, color: text, background: `${accent}18`,
            border: `1px solid ${accent}30`, borderRadius: 3, padding: '1px 5px',
            fontFamily: 'JetBrains Mono', letterSpacing: '0.04em',
          }}>{card.type}</span>
          <span style={{ fontSize: 10, color: '#505c70' }}>{card.stage}</span>
        </div>
      </div>

      {/* Set + num */}
      <div style={{ fontSize: 11, color: '#8892a4', fontFamily: 'JetBrains Mono' }}>
        {card.set} · {card.num}
      </div>

      {/* Usage */}
      <div>
        <div style={{ fontSize: 11, color: '#dde1ed', fontFamily: 'JetBrains Mono' }}>{card.usagePct}%</div>
        <div style={{ marginTop: 3, height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 1 }}>
          <div style={{ width: `${card.usagePct}%`, height: '100%', background: '#7c3aed', borderRadius: 1 }}/>
        </div>
      </div>

      {/* Price */}
      <div style={{ fontSize: 11, color: '#8892a4', fontFamily: 'JetBrains Mono' }}>
        ${card.price.toFixed(2)}
      </div>

      {/* Qty */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <button onClick={() => onQtyChange(card.id, -1)} style={{ width: 20, height: 20, borderRadius: 3, border: '1px solid rgba(255,255,255,0.10)', background: 'rgba(255,255,255,0.04)', color: '#8892a4', fontSize: 12, cursor: 'pointer' }}>−</button>
        <span style={{ width: 20, textAlign: 'center', fontSize: 11, fontWeight: 600, color: qty > 0 ? '#dde1ed' : '#505c70', fontFamily: 'JetBrains Mono' }}>{qty}</span>
        <button onClick={() => onQtyChange(card.id, 1)} style={{ width: 20, height: 20, borderRadius: 3, border: '1px solid rgba(255,255,255,0.10)', background: 'rgba(255,255,255,0.04)', color: '#8892a4', fontSize: 12, cursor: 'pointer' }}>+</button>
      </div>
    </div>
  )
}

// ─── Filter Panel ─────────────────────────────────────────────────────────────

function FilterPanel({
  selectedTypes, onToggleType, onClearFilters,
}: {
  selectedTypes: Set<PokemonType>
  onToggleType: (t: PokemonType) => void
  onClearFilters: () => void
}) {
  const futureGroups = ['Stage', 'Weakness', 'Regulation', 'Effects']

  return (
    <div style={{
      width: 210, minWidth: 210, height: '100%', background: '#0f1219',
      borderRight: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Panel header */}
      <div style={{ padding: '12px 14px 10px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: '#8892a4', letterSpacing: '0.07em', fontFamily: 'Outfit' }}>FILTERS</span>
        {selectedTypes.size > 0 && (
          <button onClick={onClearFilters} style={{ fontSize: 10, color: '#7c3aed', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: 'Inter' }}>
            Clear filters
          </button>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {/* Type section */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#505c70', letterSpacing: '0.08em', marginBottom: 8 }}>TYPE</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {ALL_TYPES.map(type => {
              const { accent, text, dim } = TYPE_INFO[type]
              const selected = selectedTypes.has(type)
              return (
                <button
                  key={type}
                  onClick={() => onToggleType(type)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px',
                    borderRadius: 5, border: `1px solid ${selected ? accent + '40' : 'rgba(255,255,255,0.06)'}`,
                    background: selected ? `${accent}14` : 'transparent',
                    cursor: 'pointer', textAlign: 'left', transition: 'all 0.12s',
                    width: '100%',
                  }}
                >
                  {/* Checkbox */}
                  <div style={{
                    width: 13, height: 13, borderRadius: 3,
                    border: `1.5px solid ${selected ? accent : 'rgba(255,255,255,0.18)'}`,
                    background: selected ? accent : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, transition: 'all 0.12s',
                  }}>
                    {selected && <span style={{ color: '#fff', fontSize: 8, lineHeight: 1, fontWeight: 700 }}>✓</span>}
                  </div>
                  {/* Type color dot */}
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: accent, flexShrink: 0 }}/>
                  <span style={{ fontSize: 12, color: selected ? text : '#8892a4', fontWeight: selected ? 500 : 400 }}>
                    {type}
                  </span>
                  {selected && (
                    <span style={{ marginLeft: 'auto', width: 5, height: 5, borderRadius: '50%', background: accent }}/>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Future groups */}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
          {futureGroups.map(group => (
            <div key={group} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '6px 8px', borderRadius: 5, marginBottom: 2,
              border: '1px solid transparent', cursor: 'not-allowed', opacity: 0.4,
            }}>
              <span style={{ fontSize: 11, color: '#505c70' }}>{group}</span>
              <span style={{ fontSize: 10, color: '#505c70' }}>›</span>
            </div>
          ))}
        </div>
      </div>

      {/* Active filter count badge */}
      {selectedTypes.size > 0 && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(124,58,237,0.08)' }}>
          <div style={{ fontSize: 11, color: '#a78bfa' }}>
            {selectedTypes.size} type{selectedTypes.size > 1 ? 's' : ''} selected
          </div>
          <div style={{ fontSize: 10, color: '#505c70', marginTop: 2 }}>
            {[...selectedTypes].join(', ')}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── AI Panel ─────────────────────────────────────────────────────────────────

function AIPanel({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const [input, setInput] = useState('')

  const messages = [
    {
      role: 'user',
      text: 'What are people pairing with this card, and is there anything interesting here?',
    },
    {
      role: 'agent',
      text: 'Night Stretcher appears frequently across several leading archetypes. Dragapult shows the strongest association in the current sample, appearing in 73.1% of lists that run the card. The Raging Bolt and Gardevoir pairings are also significant — both hovering above 58%, suggesting Night Stretcher has become a cross-archetype utility staple rather than a deck-specific tech.',
      sources: [
        { icon: '◈', label: 'Local Card Data' },
        { icon: '◉', label: 'Competitive Analytics' },
      ],
    },
    {
      role: 'user',
      text: 'Is 1.6 average copies unusual for an Item card?',
    },
    {
      role: 'agent',
      text: 'Somewhat. Most staple Items run at 2–4 copies. An average of 1.6 across 1,112 decklists suggests it\'s often a 1-of tech, particularly in Gardevoir builds where recovery lines are already established.',
      sources: [
        { icon: '◉', label: 'Competitive Analytics' },
      ],
    },
  ]

  return (
    <div style={{
      width: open ? 280 : 36, minWidth: open ? 280 : 36, height: '100%',
      background: '#0f1219', borderLeft: '1px solid rgba(255,255,255,0.06)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
      transition: 'width 0.2s ease, min-width 0.2s ease',
      position: 'relative',
    }}>
      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        style={{
          position: 'absolute', top: 12, left: open ? 12 : 6, zIndex: 10,
          width: 24, height: 24, borderRadius: 5,
          border: '1px solid rgba(255,255,255,0.10)', background: 'rgba(255,255,255,0.04)',
          color: '#8892a4', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, transition: 'all 0.15s', flexShrink: 0,
        }}
        title={open ? 'Collapse AI panel' : 'Expand AI panel'}
      >
        {open ? '›' : '‹'}
      </button>

      {open && (
        <>
          {/* Header */}
          <div style={{ padding: '12px 14px 10px 44px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }}/>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#dde1ed', fontFamily: 'Outfit', letterSpacing: '0.01em' }}>
                PokéLab Agent
              </span>
            </div>
            <div style={{ fontSize: 10, color: '#505c70', marginTop: 2, marginLeft: 12 }}>
              Research assistant · Standard format
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {messages.map((msg, i) => (
              <div key={i}>
                {msg.role === 'user' ? (
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{
                      maxWidth: '85%', padding: '8px 10px', borderRadius: '8px 8px 3px 8px',
                      background: 'rgba(124,58,237,0.18)', border: '1px solid rgba(124,58,237,0.25)',
                      fontSize: 11, color: '#c4b5fd', lineHeight: 1.5,
                    }}>
                      {msg.text}
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{
                      padding: '9px 11px', borderRadius: '8px 8px 8px 3px',
                      background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
                      fontSize: 11, color: '#a8b4c8', lineHeight: 1.6, marginBottom: 6,
                    }}>
                      {msg.text}
                    </div>
                    {msg.sources && (
                      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', paddingLeft: 2 }}>
                        {msg.sources.map(s => (
                          <span key={s.label} style={{
                            fontSize: 9, color: '#505c70', background: 'rgba(255,255,255,0.04)',
                            border: '1px solid rgba(255,255,255,0.07)', borderRadius: 3,
                            padding: '2px 6px', display: 'flex', alignItems: 'center', gap: 3,
                          }}>
                            <span style={{ color: '#7c3aed', fontSize: 8 }}>{s.icon}</span>
                            {s.label}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Input */}
          <div style={{ padding: '10px 14px 12px', borderTop: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.10)',
              borderRadius: 7, padding: '7px 10px',
            }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask PokéLab…"
                style={{
                  flex: 1, background: 'none', border: 'none', outline: 'none',
                  fontSize: 11, color: '#dde1ed', fontFamily: 'Inter',
                }}
              />
              <button style={{
                width: 22, height: 22, borderRadius: 5, background: input.trim() ? '#7c3aed' : 'rgba(255,255,255,0.06)',
                border: 'none', cursor: input.trim() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                transition: 'background 0.15s',
              }}>
                <span style={{ color: '#fff', fontSize: 10 }}>↑</span>
              </button>
            </div>
          </div>
        </>
      )}

      {!open && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 44, gap: 16, flex: 1 }}>
          <div style={{ width: 2, flex: 1, background: 'rgba(124,58,237,0.20)', borderRadius: 1 }}/>
          <span style={{
            fontSize: 9, color: '#505c70', letterSpacing: '0.12em',
            writingMode: 'vertical-lr', transform: 'rotate(180deg)', fontFamily: 'Outfit', fontWeight: 600,
          }}>AGENT</span>
          <div style={{ width: 2, flex: 1, background: 'rgba(124,58,237,0.20)', borderRadius: 1 }}/>
        </div>
      )}
    </div>
  )
}

// ─── Top Bar ──────────────────────────────────────────────────────────────────

function TopBar({ activeNav, onNavChange }: { activeNav: string; onNavChange: (n: string) => void }) {
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
            onClick={() => onNavChange(nav)}
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
        {/* Sync status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: 5, background: 'rgba(16,185,129,0.10)', border: '1px solid rgba(16,185,129,0.20)' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }}/>
          <span style={{ fontSize: 10, color: '#10b981', fontFamily: 'JetBrains Mono' }}>Synced</span>
        </div>

        {/* AI provider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: 5, background: 'rgba(139,92,246,0.10)', border: '1px solid rgba(139,92,246,0.20)' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#8b5cf6' }}/>
          <span style={{ fontSize: 10, color: '#a78bfa', fontFamily: 'JetBrains Mono' }}>GPT-4o</span>
        </div>

        {/* Settings icon */}
        <button style={{
          width: 30, height: 30, borderRadius: 7, border: '1px solid rgba(255,255,255,0.08)',
          background: 'rgba(255,255,255,0.04)', color: '#6b7280', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
          transition: 'all 0.12s',
        }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#dde1ed' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#6b7280' }}
        >
          ⚙
        </button>
      </div>
    </div>
  )
}

// ─── Library Controls ─────────────────────────────────────────────────────────

function LibraryControls({
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
        title="Toggle filters"
      >
        ⊞
      </button>

      {/* Category tabs */}
      <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', borderRadius: 7, padding: 2, border: '1px solid rgba(255,255,255,0.07)' }}>
        {(['pokemon', 'trainers', 'energy'] as Category[]).map(cat => (
          <button
            key={cat}
            onClick={() => onCategoryChange(cat)}
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
            onClick={() => onScopeChange(s)}
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
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Search cards…"
          style={{
            flex: 1, background: 'none', border: 'none', outline: 'none',
            fontSize: 12, color: '#dde1ed', fontFamily: 'Inter',
          }}
        />
        {searchQuery && (
          <button onClick={() => onSearchChange('')} style={{ background: 'none', border: 'none', color: '#505c70', cursor: 'pointer', fontSize: 13, padding: 0 }}>×</button>
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
            onClick={() => onViewModeChange(mode)}
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

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [activeNav, setActiveNav] = useState('Library')
  const [category, setCategory] = useState<Category>('pokemon')
  const [scope, setScope] = useState<Scope>('all')
  const [viewMode, setViewMode] = useState<ViewMode>('gallery')
  const [filterOpen, setFilterOpen] = useState(true)
  const [aiOpen, setAiOpen] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypes, setSelectedTypes] = useState<Set<PokemonType>>(new Set(['Psychic', 'Dragon']))
  const [quantities, setQuantities] = useState<Record<number, number>>(
    Object.fromEntries(CARDS.map(c => [c.id, c.baseQty]))
  )
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)

  const hoverTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const hideTimerRef = useRef<ReturnType<typeof setTimeout>>()

  const handleQtyChange = useCallback((id: number, delta: number) => {
    setQuantities(prev => ({ ...prev, [id]: Math.max(0, (prev[id] ?? 0) + delta) }))
  }, [])

  const handleHoverStart = useCallback((card: CardData, el: HTMLElement) => {
    clearTimeout(hideTimerRef.current)
    clearTimeout(hoverTimerRef.current)
    hoverTimerRef.current = setTimeout(() => {
      const rect = el.getBoundingClientRect()
      const TOOLTIP_W = 272
      const MARGIN = 10
      const spaceRight = window.innerWidth - rect.right
      const side = spaceRight >= TOOLTIP_W + MARGIN ? 'right' : 'left'
      const x = side === 'right' ? rect.right + MARGIN : rect.left - TOOLTIP_W - MARGIN
      const y = Math.max(8, Math.min(rect.top, window.innerHeight - 420 - 8))
      setTooltip({ card, x, y, side })
    }, 2000)
  }, [])

  const handleHoverEnd = useCallback(() => {
    clearTimeout(hoverTimerRef.current)
    hideTimerRef.current = setTimeout(() => {
      setTooltip(null)
    }, 200)
  }, [])

  const handleTooltipEnter = useCallback(() => {
    clearTimeout(hideTimerRef.current)
  }, [])

  const handleTooltipLeave = useCallback(() => {
    setTooltip(null)
  }, [])

  const toggleType = useCallback((t: PokemonType) => {
    setSelectedTypes(prev => {
      const next = new Set(prev)
      next.has(t) ? next.delete(t) : next.add(t)
      return next
    })
  }, [])

  // Filter cards
  const filteredCards = CARDS.filter(card => {
    if (selectedTypes.size > 0 && !selectedTypes.has(card.type)) return false
    if (scope === 'owned' && (quantities[card.id] ?? 0) === 0) return false
    if (scope === 'unowned' && (quantities[card.id] ?? 0) > 0) return false
    if (searchQuery && !card.name.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  useEffect(() => {
    return () => {
      clearTimeout(hoverTimerRef.current)
      clearTimeout(hideTimerRef.current)
    }
  }, [])

  return (
    <div className="mica-bg" style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', fontFamily: 'Inter' }}>
      <TopBar activeNav={activeNav} onNavChange={setActiveNav} />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left filter panel */}
        {filterOpen && (
          <FilterPanel
            selectedTypes={selectedTypes}
            onToggleType={toggleType}
            onClearFilters={() => setSelectedTypes(new Set())}
          />
        )}

        {/* Main content */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          <LibraryControls
            category={category} onCategoryChange={setCategory}
            scope={scope} onScopeChange={setScope}
            viewMode={viewMode} onViewModeChange={setViewMode}
            searchQuery={searchQuery} onSearchChange={setSearchQuery}
            filterOpen={filterOpen} onFilterToggle={() => setFilterOpen(v => !v)}
            totalCards={CARDS.length} filteredCount={filteredCards.length}
          />

          {/* Gallery / List */}
          {viewMode === 'gallery' ? (
            <div style={{
              flex: 1, overflowY: 'auto', padding: 20,
            }}>
              {filteredCards.length === 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 200, color: '#505c70', gap: 8 }}>
                  <span style={{ fontSize: 24 }}>⊘</span>
                  <span style={{ fontSize: 13 }}>No cards match the current filters</span>
                  <button
                    onClick={() => { setSelectedTypes(new Set()); setSearchQuery(''); setScope('all') }}
                    style={{ fontSize: 12, color: '#7c3aed', background: 'none', border: 'none', cursor: 'pointer', marginTop: 4 }}
                  >
                    Clear all filters
                  </button>
                </div>
              ) : (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
                  gap: 16,
                }}>
                  {filteredCards.map(card => (
                    <CardTile
                      key={card.id}
                      card={card}
                      qty={quantities[card.id] ?? 0}
                      onQtyChange={handleQtyChange}
                      onHoverStart={handleHoverStart}
                      onHoverEnd={handleHoverEnd}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {/* List header */}
              <div style={{
                display: 'grid', gridTemplateColumns: '48px 1fr 110px 90px 72px 80px',
                alignItems: 'center', gap: 12, padding: '6px 16px',
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(255,255,255,0.02)', position: 'sticky', top: 0,
              }}>
                {['', 'Card Name', 'Set · Num', 'Usage %', 'Market', 'Qty'].map((h, i) => (
                  <span key={i} style={{ fontSize: 10, fontWeight: 600, color: '#505c70', letterSpacing: '0.07em', fontFamily: 'Outfit' }}>
                    {h}
                  </span>
                ))}
              </div>
              {filteredCards.map(card => (
                <CardRow
                  key={card.id}
                  card={card}
                  qty={quantities[card.id] ?? 0}
                  onQtyChange={handleQtyChange}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right AI panel */}
        <AIPanel open={aiOpen} onToggle={() => setAiOpen(v => !v)} />
      </div>

      {/* Tooltip */}
      {tooltip && (
        <AnalyticsTooltip
          tooltip={tooltip}
          onEnter={handleTooltipEnter}
          onLeave={handleTooltipLeave}
        />
      )}
    </div>
  )
}
