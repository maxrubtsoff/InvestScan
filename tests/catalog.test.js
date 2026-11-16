import test from'node:test';
import assert from'node:assert/strict';
import{cleanTenantName,normalizeCard}from'../js/catalog-normalize.js';
test('financial fields cannot identify a tenant',()=>{
 for(const v of ['МАП: 16800','Арендная плата 50000','16800 ₽','Не указан'])assert.equal(cleanTenantName(v),null);
 for(const v of ['Магнит','1000 мелочей','ООО «МАП»'])assert.equal(cleanTenantName(v),v);
});
test('old records from blocked sources display their actual last observation',()=>{
 const row={tenant_name:'МАП: 16800',last_seen:'2026-11-15T12:00:00Z',sources:[{name:'ЦИАН'}]};
 const x=normalizeCard(row,[{name:'ЦИАН',status:'blocked'}]);
 assert.equal(x.tenant_name,null);assert.equal(x.source_fetched_at,row.last_seen);
 assert.equal(normalizeCard(row,[{name:'ЦИАН',status:'ok'}]).source_fetched_at,undefined);
 assert.equal(normalizeCard({...row,sources:[{name:'ЦИАН'},{name:'АРР'}]},[{name:'ЦИАН',status:'blocked'},{name:'АРР',status:'ok'}]).source_fetched_at,undefined);
 assert.equal(normalizeCard({...row,source_fetched_at:'2026-11-14'},[{name:'ЦИАН',status:'blocked'}]).source_fetched_at,'2026-11-14');
});
