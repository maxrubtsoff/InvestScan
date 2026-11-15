export function matches(x,f,mode='all',unknown=false){
 const n=k=>f[k] === ''||f[k]==null?null:Number(f[k]);
 const max=n('maxPrice')??12000000;
 if(unknown ? x.distance_km!=null : x.distance_km==null)return false;
 if(unknown&&f.radius!==''&&!x.regional_candidate)return false;
 if(!unknown&&n('radius')!=null&&x.distance_km>n('radius'))return false;
 for(const [field,min,maxKey] of [['price','minPrice','maxPrice'],['area','minArea','maxArea']]){if(n(min)!=null&&(x[field]==null||x[field]<n(min)))return false;if(n(maxKey)!=null&&mode!=='over'&&(x[field]==null||x[field]>n(maxKey)))return false;}
 if(mode==='over'&&(x.price==null||x.price<=max))return false;
 if(mode==='budget'&&(x.price==null||x.price>max))return false;
 if(['review','confirmed'].includes(mode)&&x.verification!==mode)return false;
 if(f.verification&&x.verification!==f.verification)return false;
 if(f.settlement&&x.settlement!==f.settlement)return false;
 if(f.district&&!(x.district||'').toLowerCase().includes(f.district.toLowerCase()))return false;
 if(f.q&&!`${x.title} ${x.address} ${x.tenant_name}`.toLowerCase().includes(f.q.toLowerCase()))return false;
 if(f.tenantType&&x.tenant_type!==f.tenantType)return false;
 for(const [key,field] of [['activeTenant','active_tenant'],['contract','contract'],['indexation','indexation']]){if(f[key]&&(f[key]==='unknown'?x[field]!=null:String(x[field])!==f[key]))return false;}
 if(n('minYield')!=null&&(x.finance?.gross_yield==null||x.finance.gross_yield<n('minYield')))return false;
 if(n('maxPayback')!=null&&(x.finance?.payback_years==null||x.finance.payback_years>n('maxPayback')))return false;
 return true;
}
export function compare(key){const spec={score:['score',-1],yield:['finance.gross_yield',-1],payback:['finance.payback_years',1],price:['price',1],distance:['distance_km',1],published:['published_at',-1]};const [path,dir]=spec[key]||spec.score;const get=x=>path.split('.').reduce((a,k)=>a?.[k],x);return(a,b)=>{const x=get(a),y=get(b);if(x==null)return y==null?0:1;if(y==null)return -1;return(x<y?-1:x>y?1:0)*dir;};}
