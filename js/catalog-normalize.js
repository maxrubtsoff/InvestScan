// Also protect older catalog snapshots until the next Python export revalidates them.
export function cleanTenantName(value){
 if(typeof value!=='string')return null;value=value.trim();
 if(!value||/^(?:мап|месячный арендный поток|арендная плата|стоимость|цена)(?=$|[^а-яёa-z0-9_])/i.test(value))return null;
 if(/^(?:не указан|нет информации|нет данных|—|-)$/i.test(value)||/^[\d\s.,]+(?:\s*(?:₽|руб\.?|рублей))?$/i.test(value))return null;
 return value;
}
export function normalizeCard(row,sources=[]){
 const x={...row,tenant_name:cleanTenantName(row.tenant_name)};
 const blocked=new Set(sources.filter(s=>['blocked','error'].includes(s.status)).map(s=>s.name));
 if(!x.source_fetched_at&&x.sources?.length&&x.sources.every(s=>blocked.has(s.name)))x.source_fetched_at=x.last_seen||null;
 return x;
}
export function priceValues(x){return [...new Set([x.price,...(x.price_claims||[]).map(c=>c.value)].filter(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0))].sort((a,b)=>a-b);}
export function dataNote(x){
 if(x.source_fetched_at)return`Снимок от ${new Date(x.source_fetched_at).toLocaleDateString('ru-RU',{timeZone:'Europe/Moscow'})}.`;
 return x.acquisition_mode==='import'?'Импорт: дата данных источника не указана.':'';
}
export function observedDate(x){return x.last_seen?new Date(x.last_seen).toLocaleString('ru-RU',{timeZone:'Europe/Moscow'})+' МСК':'Дата наблюдения источника не указана';}
