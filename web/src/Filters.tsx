import type { FilterOption } from './api'
export const filterFamilies=['pokemon_types','stages','trainer_types','energy_types','regulation_marks']
export function valueLabel(value:string) {return ({Stage1:'Stage 1',Stage2:'Stage 2',Normal:'Basic Energy',Special:'Special Energy'} as Record<string,string>)[value] || value}
export function Filters({options,params,onChange,onClear}:{options:FilterOption[];params:URLSearchParams;onChange:(key:string,value:string)=>void;onClear:()=>void}) {
 return <aside className="filter-panel" aria-label="Filters"><h2>FILTERS</h2><button onClick={onClear}>Clear filters</button>
  {options.map(family=><fieldset key={family.parameter}><legend>{family.label}</legend>
   {[...new Set([...family.values,...params.getAll(family.parameter)])].map(value=><label key={value}>
    <input type="checkbox" checked={params.getAll(family.parameter).includes(value)} onChange={()=>onChange(family.parameter,value)}/>{' '}{valueLabel(value)}
   </label>)}
  </fieldset>)}
  <p>OR within each group. AND between groups. Source-marked Standard printings only.</p>
 </aside>
}
