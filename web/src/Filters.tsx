import type { FilterOption } from './api'
export const filterFamilies=['pokemon_types','stages','trainer_types','energy_types','regulation_marks','has_ability','ability']
export function abilityValues(params:URLSearchParams) {
 return params.has('ability') ? params.getAll('ability') : ['true','1','yes','on'].includes((params.get('has_ability')||'').toLowerCase()) ? ['Yes'] : []
}
export function valueLabel(value:string) {return ({Stage1:'Stage 1',Stage2:'Stage 2',Normal:'Basic Energy',Special:'Special Energy'} as Record<string,string>)[value] || value}
export function Filters({options,params,onChange,onClear}:{options:FilterOption[];params:URLSearchParams;onChange:(key:string,value:string)=>void;onClear:()=>void}) {
 const groups=options.filter(f=>f.parameter!=='ability')
 if((params.get('category')||'Pokemon')==='Pokemon') {
  const regulation=groups.findIndex(f=>f.parameter==='regulation_marks')
  groups.splice(regulation<0?groups.length:regulation,0,{parameter:'ability',label:'Ability',values:['Yes','No']})
 }
 return <aside className="filter-panel" aria-label="Filters"><h2>FILTERS</h2><button onClick={onClear}>Clear filters</button>
  {groups.map(family=><fieldset key={family.parameter}><legend>{family.label}</legend>
   {[...new Set([...family.values,...params.getAll(family.parameter)])].map(value=><label key={value}>
    <input type="checkbox" checked={(family.parameter==='ability'?abilityValues(params):params.getAll(family.parameter)).includes(value)} onChange={()=>onChange(family.parameter,value)}/>{' '}{valueLabel(value)}
   </label>)}
  </fieldset>)}
  <p>OR within each group. AND between groups. Source-marked Standard printings only.</p>
 </aside>
}
