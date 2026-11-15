let instance=null,layer=null,current=[],currentRadius=100,target=null,unknownCount=0;
const CENTER=[55.796127,49.106414];
const rub=v=>v==null?'Цена не указана':new Intl.NumberFormat('ru-RU',{maximumFractionDigits:0}).format(v)+' ₽';
const compact=v=>v==null?'—':new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(v/1000000)+' млн ₽';
const safe=url=>{try{const u=new URL(url);return u.protocol==='https:'?u.href:'#';}catch{return '#';}};
function paint(){
 if(!instance)return;const L=window.L;layer.clearLayers();const bounds=[CENTER];
 L.circleMarker(CENTER,{radius:5,color:'#172b28',fillOpacity:1}).bindTooltip('Центр Казани').addTo(layer);
 if(currentRadius)L.circle(CENTER,{radius:currentRadius*1000,color:'#39775c',weight:1,dashArray:'5 6',fillOpacity:.025,interactive:false}).addTo(layer);
 const groups=new Map();for(const row of current){if(!row.coordinates||row.distance_km==null)continue;const key=row.coordinates.map(v=>v.toFixed(5)).join(',');if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
 for(const rows of groups.values()){
  const x=rows[0],price=Math.min(...rows.map(r=>r.price??Infinity));const label=(rows.length>1?'от ':'')+compact(Number.isFinite(price)?price:null)+(rows.length>1?' · '+rows.length:'');
  const popup=document.createElement('div');popup.className='map-popup';
  for(const r of rows){const part=document.createElement('section');const h=document.createElement('strong');h.textContent=rub(r.price);const address=document.createElement('p');address.textContent=r.address||r.title;const rent=document.createElement('p');rent.textContent=`Аренда: ${rub(r.monthly_rent)} / мес. · ${r.distance_km.toLocaleString('ru-RU')} км от Казани`;part.append(h,address,rent);for(const s of r.sources||[]){const link=document.createElement('a');link.href=safe(s.url);link.target='_blank';link.rel='noopener noreferrer';link.textContent=`${s.name}: открыть объявление ↗`;part.append(link);}popup.append(part);}
  const icon=L.divIcon({className:'price-pin',html:`<span>${label}</span>`,iconSize:[110,32],iconAnchor:[55,32]});L.marker(x.coordinates,{icon,title:`${label} · ${x.address}`,keyboard:true}).bindPopup(popup,{maxWidth:280}).addTo(layer);bounds.push(x.coordinates);
 }
 if(bounds.length>1)instance.fitBounds(bounds,{padding:[65,45],maxZoom:14});else instance.setView(CENTER,10);
 document.querySelector('#map-status').textContent=current.length?`На карте: ${current.length}. Адресов региона без координат: ${unknownCount}. Нажмите цену — откроются адрес, аренда и объявление.`:`По этим фильтрам нет объектов с координатами. Адресов региона без координат: ${unknownCount}. Они не отмечены на карте.`;
}
export function drawMap(container,rows,radius,unresolved=0){unknownCount=unresolved;target=container;current=rows;currentRadius=radius;paint();}
export function openMap(){
 const status=document.querySelector('#map-status');if(!window.L){status.textContent='Не удалось загрузить библиотеку карты. Объявления и ссылки доступны в списке.';return;}
 target.hidden=false;
 if(!instance){const L=window.L;instance=L.map(target,{scrollWheelZoom:false}).setView(CENTER,9);layer=L.layerGroup().addTo(instance);const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',referrerPolicy:'strict-origin-when-cross-origin'});tiles.on('tileerror',()=>{status.textContent='Подложка карты временно недоступна. Ценовые маркеры и ссылки остаются доступны.';});tiles.addTo(instance);L.control.scale({imperial:false}).addTo(instance);}
 requestAnimationFrame(()=>{instance.invalidateSize();paint();});document.querySelector('#open-map').textContent='Показать все найденные на карте';
}
