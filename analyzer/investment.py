COST_KEYS=('tax','utilities','maintenance','insurance','management','commissions')
def analyze(x):
    price=x.get('price');rent=x.get('monthly_rent');annual=rent*12 if rent is not None else None
    result=dict(annual_rent=annual,gross_yield=annual/price*100 if annual is not None and price else None,payback_years=price/annual if price and annual else None,net_yield=None,net_payback_years=None,scenarios=[])
    costs=x.get('annual_costs',{});complete=all(costs.get(k) is not None for k in COST_KEYS) and x.get('transaction_costs') is not None and x.get('vacancy_months') is not None
    if annual is None or not price:return result
    known=sum(v for v in costs.values() if v is not None)
    if complete:
        net=rent*(12-x['vacancy_months'])-known;investment=price+x['transaction_costs']
        result.update(net_yield=net/investment*100,net_payback_years=investment/net if net>0 else None)
    result['scenario_note']='Условные оценки: простой 0/1/2 мес.; неизвестные годовые расходы заменены общим резервом 5/10/15% валовой аренды; расходы на сделку 0/2/3% цены, если неизвестны. Известные значения всегда сохраняются. Индексация и рост цены не предполагаются.'
    for name,vacancy,reserve,deal in [('Оптимистичный',0,.05,0),('Базовый',1,.10,.02),('Консервативный',2,.15,.03)]:
        v=x['vacancy_months'] if x.get('vacancy_months') is not None else vacancy
        expense=known+(0 if all(costs.get(k) is not None for k in COST_KEYS) else annual*reserve)
        income=rent*(12-v)-expense;investment=price+(x['transaction_costs'] if x.get('transaction_costs') is not None else price*deal)
        result['scenarios'].append(dict(name=name,income=income,yield_=income/investment*100,payback=investment/income if income>0 else None,vacancy_months=v,expenses=expense,assumed=not complete))
        result['scenarios'][-1]['yield']=result['scenarios'][-1].pop('yield_')
    return result
