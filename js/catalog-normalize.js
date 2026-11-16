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
