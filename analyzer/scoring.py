"""Versioned, explainable heuristic. Missing facts earn zero points."""
def score(x):
    f=x['finance'];parts=[]
    def add(factor,points,max_,reason):parts.append(dict(factor=factor,points=round(points,1),max=max_,reason=reason))
    y=f.get('gross_yield');pay=f.get('payback_years');dist=x.get('distance_km')
    add('Валовая доходность',min(15,(y or 0)),15,'До 15 баллов: 1 балл за 1% годовых, валовый показатель')
    add('Простая окупаемость',15 if pay and pay<=9 else 12 if pay and pay<=10 else 6 if pay and pay<=12 else 0,15,'15 до 9 лет; 12 до 10; 6 до 12')
    add('Надёжность аренды',15 if x.get('payments_confirmed') is True and x.get('active_tenant') is True else 0,15,'Нужны подтверждённые платежи и действующий арендатор; бренд ПВЗ не гарантирует надёжность оператора')
    months=x.get('contract_months')
    add('Договор',10 if x.get('contract') is True and months and months>=36 else 5 if x.get('contract') is True else 0,10,'10 за подтверждённый срок от 36 месяцев; иначе 5 за договор')
    add('Индексация',5 if x.get('indexation') is True else 0,5,'Только подтверждённая ежегодная индексация')
    add('Расположение',5 if x.get('traffic') is True else 0,5,'Подтверждённый трафик / жилой массив')
    add('Расстояние',10 if dist is not None and dist<=30 else 7 if dist is not None and dist<=100 else 3 if dist is not None and dist<=200 else 0,10,'10 до 30 км; 7 до 100; 3 до 200')
    add('Состояние',sum(1 for k in ['repair','communications','wet_point','ventilation','separate_entrance'] if x.get(k) is True),5,'По 1 баллу за пять подтверждённых характеристик')
    keys=['price','area','monthly_rent','address','tenant_name','contract_months','floor','coordinates','condition','published_at']
    add('Полнота данных',sum(1 for k in keys if x.get(k) is not None and x.get(k)!=''),10,'По 1 баллу за каждое из 10 основных полей')
    add('Цена относительно рынка',0,10,'Нет проверенной сопоставимой выборки — баллы не начисляются')
    value=round(sum(a['points'] for a in parts));cap=100 if x['verification']=='confirmed' else 39
    x.update(score=min(cap,value),score_breakdown=parts,score_version=1,score_note=f'Экспертная эвристика. Сумма факторов {value}; предел для текущего статуса {cap}. '+('Без координат исключён из географического рейтинга.' if dist is None else ''))
    return x
