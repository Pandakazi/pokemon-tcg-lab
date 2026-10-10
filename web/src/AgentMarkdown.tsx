import type {ReactNode} from 'react'
import {ResearchCardText,type ResearchCard} from './ResearchCardText'

// Small presentation subset; React escapes HTML and no executable links/raw HTML
// are interpreted. Card previews still use the existing exact-printing renderer.
export function AgentMarkdown({text,cards,inspect}:{text:string;cards:ResearchCard[];inspect:(id:string)=>void}) {
 const clean=text.replace(/\\+([#*_`])/g,'$1')
 const plain=(s:string)=><ResearchCardText text={s} cards={cards} inspect={inspect}/>
 const inline=(s:string):ReactNode[]=>s.split(/(\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`\n]+`)/g).map((part,i)=>
  part.startsWith('**')||part.startsWith('__')?<strong key={i}>{plain(part.slice(2,-2))}</strong>:
  part.startsWith('*')||part.startsWith('_')?<em key={i}>{plain(part.slice(1,-1))}</em>:
  part.startsWith('`')?<code key={i}>{part.slice(1,-1)}</code>:<span key={i}>{plain(part)}</span>)
 const blocks:ReactNode[]=[];const lines=clean.split('\n')
 for(let i=0;i<lines.length;i++){
  const line=lines[i];if(!line.trim())continue
  const heading=/^\s*(#{1,6})\s+(.+)$/.exec(line)
  if(heading){blocks.push(heading[1].length<3?<h3 key={i}>{inline(heading[2])}</h3>:<h4 key={i}>{inline(heading[2])}</h4>);continue}
  if(/^\s*(?:[-*+] |\d+[.)] )/.test(line)){
   const ordered=/^\s*\d+[.)] /.test(line),items:ReactNode[]=[];const start=i
   const pattern=ordered?/^\s*\d+[.)] (.*)$/:/^\s*[-*+] (.*)$/
   while(i<lines.length){const m=pattern.exec(lines[i]);if(!m)break;items.push(<li key={i}>{inline(m[1])}</li>);i++}i--
   blocks.push(ordered?<ol key={start}>{items}</ol>:<ul key={start}>{items}</ul>);continue
  }
  const start=i;const paragraph=[line]
  while(i+1<lines.length&&lines[i+1].trim()&&!/^\s*(?:#|[-*+] |\d+[.)] )/.test(lines[i+1]))paragraph.push(lines[++i])
  blocks.push(<p key={start}>{inline(paragraph.join('\n'))}</p>)
 }
 return <div className="agent-markdown">{blocks}</div>
}
