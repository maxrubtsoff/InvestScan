// Web Mercator pixel coordinates. No map framework or external JavaScript.
export const CENTER=[55.796127,49.106414];
export function project([lat,lon],zoom){const size=256*2**zoom;const phi=Math.max(-85.05112878,Math.min(85.05112878,lat))*Math.PI/180;return[(lon+180)/360*size,(1-Math.log(Math.tan(phi)+1/Math.cos(phi))/Math.PI)/2*size];}
export function unproject([x,y],zoom){const size=256*2**zoom;return[Math.atan(Math.sinh(Math.PI*(1-2*y/size)))*180/Math.PI,x/size*360-180];}
export function fitView(points,width,height){const all=points.length?points:[CENTER];for(let z=14;z>=3;z--){const p=all.map(c=>project(c,z)),xs=p.map(c=>c[0]),ys=p.map(c=>c[1]);const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);if(maxX-minX<Math.max(100,width-150)&&maxY-minY<Math.max(100,height-100)||z===3)return{zoom:z,center:unproject([(minX+maxX)/2,(minY+maxY)/2],z)};}}
// Merge overlapping label rectangles at the current zoom, retaining every offer.
// Repeat after centroid movement so merging cannot create a new collision.
export function clusterMarkers(points,width=176,height=56){
 let groups=points.map(p=>({x:p.x,y:p.y,items:[p.row]}));
 for(;;){
  const parent=groups.map((_,i)=>i),root=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  for(let i=0;i<groups.length;i++)for(let j=i+1;j<groups.length;j++)if(Math.abs(groups[i].x-groups[j].x)<width&&Math.abs(groups[i].y-groups[j].y)<height)parent[root(j)]=root(i);
  const merged=new Map();groups.forEach((g,i)=>{const key=root(i);if(!merged.has(key))merged.set(key,{x:0,y:0,items:[]});const m=merged.get(key);m.x+=g.x*g.items.length;m.y+=g.y*g.items.length;m.items.push(...g.items);});
  if(merged.size===groups.length)return groups;
  groups=[...merged.values()].map(g=>({...g,x:g.x/g.items.length,y:g.y/g.items.length}));
 }
}
