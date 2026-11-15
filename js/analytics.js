export const money=v=>v==null?'Нет данных':new Intl.NumberFormat('ru-RU',{maximumFractionDigits:0}).format(v)+' ₽';
export const num=(v,s='')=>v==null?'—':Number(v).toLocaleString('ru-RU',{maximumFractionDigits:1})+s;
export const status=v=>v===true?'Подтверждено':v===false?'Не подтверждено':'Нет информации';
export function stats(rows){const vals=rows.map(x=>x.finance?.gross_yield).filter(x=>x!=null);return [['Всего в базе',rows.length],['Подтверждённые ГАБ',rows.filter(x=>x.verification==='confirmed').length],['Требуют проверки',rows.filter(x=>x.verification!=='confirmed').length],['Средняя валовая доходность',vals.length?num(vals.reduce((a,b)=>a+b)/vals.length,'%'):'—'],['Окупаемость до 10 лет',rows.filter(x=>x.finance?.payback_years!=null&&x.finance.payback_years<=10).length]];}
