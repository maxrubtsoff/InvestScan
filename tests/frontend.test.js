import{test}from'node:test';import assert from'node:assert/strict';import{matches,compare}from'../js/filters.js';
const x={price:10000000,area:100,distance_km:80,verification:'review',finance:{gross_yield:12,payback_years:8.3},score:39};
test('radius and budget',()=>{assert(matches(x,{radius:'100',maxPrice:'12000000'}));assert(!matches(x,{radius:'50'}));assert(matches({...x,price:15000000},{radius:'100',maxPrice:'12000000'},'over'));});
test('unknown geo separate',()=>{assert(!matches({...x,distance_km:null},{}));assert(matches({...x,distance_km:null,regional_candidate:true},{},'all',true));});
test('missing yield not sorted first',()=>{assert(compare('yield')({finance:{}},x)>0);});
test('unknown booleans',()=>{assert(matches(x,{contract:'unknown'}));assert(!matches(x,{contract:'true'}));});
test('foreign unresolved addresses are excluded from a bounded region',()=>{const foreign={...x,distance_km:null,regional_candidate:false};assert(!matches(foreign,{radius:'100'},'all',true));assert(matches(foreign,{radius:''},'all',true));assert(matches({...foreign,regional_candidate:true},{radius:'100'},'all',true));});
