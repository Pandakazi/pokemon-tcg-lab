import type { FilterOption } from './api'
export const filterFamilies=['pokemon_types','stages','trainer_types','energy_types','regulation_marks','has_ability','ability','illustrators']
export function abilityValues(params:URLSearchParams) {
 return params.has('ability') ? params.getAll('ability') : ['true','1','yes','on'].includes((params.get('has_ability')||'').toLowerCase()) ? ['Yes'] : []
}
export function valueLabel(value:string) {return ({Stage1:'Stage 1',Stage2:'Stage 2',Normal:'Basic Energy',Special:'Special Energy'} as Record<string,string>)[value] || value}
const artistOrder=new Intl.Collator('en',{sensitivity:'base',numeric:true})
export function illustratorGroups(values:string[]) {
 const groups=new Map<string,string[]>()
 for(const name of [...new Set(values)].sort((a,b)=>artistOrder.compare(a,b)||a.localeCompare(b,'en'))){
  const first=name.trim().charAt(0).toUpperCase(),letter=/^[A-Z]$/.test(first)?first:'#'
  groups.set(letter,[...(groups.get(letter)||[]),name])
 }
 return [...groups].sort(([a],[b])=>a==='#'?1:b==='#'?-1:a.localeCompare(b))
}
export function Filters({options,params,onChange,onClear}:{options:FilterOption[];params:URLSearchParams;onChange:(key:string,value:string)=>void;onClear:()=>void}) {
 const artistCatalog=!!params.get('illustrators')
 const groups=options.filter(f=>f.parameter!=='ability'&&(!artistCatalog||f.parameter==='illustrators'))
 if(!artistCatalog&&(params.get('category')||'Pokemon')==='Pokemon') {
  const regulation=groups.findIndex(f=>f.parameter==='regulation_marks')
  groups.splice(regulation<0?groups.length:regulation,0,{parameter:'ability',label:'Ability',values:['Yes','No']})
 }
 return <aside className="filter-panel" aria-label="Filters"><h2>FILTERS</h2><button onClick={onClear}>Clear filters</button>
  {groups.map(family=>{
   const values=[...new Set([...family.values,...params.getAll(family.parameter)])]
   const checkbox=(value:string)=><label key={value}>
    <input type="checkbox" checked={(family.parameter==='ability'?abilityValues(params):params.getAll(family.parameter)).includes(value)} onChange={()=>onChange(family.parameter,value)}/>{' '}{valueLabel(value)}
   </label>
   return <fieldset key={family.parameter}><legend>{family.label}</legend>
    {family.parameter==='illustrators'?illustratorGroups(values).map(([letter,names])=><details key={letter} open={names.some(name=>params.getAll('illustrators').includes(name))||undefined}><summary>{letter}</summary>{names.map(checkbox)}</details>):values.map(checkbox)}
   </fieldset>
  })}
  <p>{artistCatalog?'All indexed printings by the selected illustrators. Other category, legality and ownership filters do not apply.':'OR within each group. AND between groups. Source-marked Standard printings only.'}</p>
 </aside>
}
