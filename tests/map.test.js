import{test}from'node:test';import assert from'node:assert/strict';import{CENTER,project,unproject,fitView,clusterMarkers}from'../js/map-math.js';
test('Web Mercator round trip preserves property coordinates',()=>{for(const c of [CENTER,[55.8252381,49.1194653],[56.4,49.5]])for(const z of [3,9,14,18]){const v=unproject(project(c,z),z);assert(Math.abs(v[0]-c[0])<1e-8);assert(Math.abs(v[1]-c[1])<1e-8);}});
test('fit places all properties within the viewport margins',()=>{const points=[CENTER,[56.4,49.5]],width=360,height=500;const v=fitView(points,width,height),center=project(v.center,v.zoom);for(const c of points){const p=project(c,v.zoom);assert(Math.abs(p[0]-center[0])<width/2);assert(Math.abs(p[1]-center[1])<height/2);}});
test('overlapping prices merge without losing offers and separate on zoom',()=>{
 const points=[{x:0,y:0,row:'a'},{x:100,y:20,row:'b'},{x:500,y:0,row:'c'}];
 const groups=clusterMarkers(points);assert.equal(groups.length,2);assert.deepEqual(groups.flatMap(g=>g.items).sort(),['a','b','c']);
 assert.equal(clusterMarkers(points.map(p=>({...p,x:p.x*4,y:p.y*4}))).length,3);
});
test('transitive groups leave no price rectangles overlapping',()=>{
 const points=Array.from({length:40},(_,i)=>({x:(i*113)%500,y:(i*47)%400,row:i}));
 const groups=clusterMarkers(points);assert.equal(groups.flatMap(g=>g.items).length,points.length);
 for(let i=0;i<groups.length;i++)for(let j=i+1;j<groups.length;j++)assert(Math.abs(groups[i].x-groups[j].x)>=176||Math.abs(groups[i].y-groups[j].y)>=56);
});
