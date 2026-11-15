"""Broker regression cases: never turn potential cash flow into current rent."""
import pytest
from parsers.rental_fields import rent_claim, tenant_claim, rental_candidate
from parsers.cian import convert


@pytest.mark.parametrize('description', [
    'ГАБ. Арендная плата 1 200 000 рублей за год',
    'ГАБ. Арендная плата 100000 рублей в квартал',
    'ГАБ. Годовая текущая арендная плата 1200000 рублей',
    'ГАБ. МАП 1000 долларов',
    'ГАБ. Арендная плата 1000 EUR в месяц',
    'ГАБ. Потенциальная арендная плата 100000 рублей в месяц',
    'ГАБ. Планируемая арендная плата 100000 рублей в месяц',
    'ГАБ. МАП 100000 рублей — потенциальный, помещение пока пустует',
    'Чистая прибыль салона 150000 рублей в месяц',
])
def test_uncertain_or_non_monthly_cash_flow_is_not_current_ruble_rent(description):
    assert rent_claim(description) is None


@pytest.mark.parametrize(('description', 'expected'), [
    ('Действующий арендатор. МАП 150 тыс. рублей', 150000),
    ('Арендная плата 100000 рублей в месяц', 100000),
    ('Арендный поток 4195000 рублей в месяц', 4195000),
    ('Месячный арендный поток: 75 000 ₽', 75000),
])
def test_explicit_monthly_ruble_rent(description, expected):
    assert rent_claim(description) == expected


@pytest.mark.parametrize('description', [
    'ГАБ. Магнит находится через дорогу',
    'Готовый арендный бизнес. Рядом Магнит',
    'ГАБ. Возможный арендатор Ozon, договор ещё не подписан',
    'ГАБ. Арендатор Ozon съехал, помещение свободно',
    'ГАБ. Бывший арендатор Ozon',
    'ГАБ. Планируем сдать помещение арендатору Ozon',
])
def test_neighbor_prospective_or_departed_brand_is_not_a_current_tenant(description):
    assert tenant_claim(description)[0] is None


def test_neighbor_pharmacy_does_not_set_tenant_type():
    name, kind = tenant_claim('ГАБ. Рядом аптека')
    assert name is None
    assert kind is None


@pytest.mark.parametrize(('description', 'name', 'kind'), [
    ('Действующий арендатор — Ozon', 'Ozon', 'ПВЗ'),
    ('Помещение сдано в аренду. Арендатор Магнит', 'Магнит', 'Продуктовый магазин'),
])
def test_explicit_current_brand(description, name, kind):
    assert tenant_claim(description) == (name, kind)


def offer():
    return {
        'category': 'businessSale',
        'fullUrl': 'https://kazan.cian.ru/sale/commercial/1/',
        'description': 'ГАБ. Действующий арендатор Ozon. МАП 50000 рублей',
        'totalArea': '50',
        'bargainTerms': {'price': 5000000, 'currency': 'rur'},
        'geo': {
            'userInput': 'Казань, ул Мусина, 29д',
            'coordinates': {'lat': 55.8, 'lng': 49.1},
            'address': [
                {'geoType': 'location', 'name': 'Казань', 'title': 'Казань', 'isFormingAddress': True},
                {'geoType': 'street', 'name': 'Мусина', 'title': 'ул Мусина', 'isFormingAddress': True},
                {'geoType': 'house', 'name': '29д', 'title': '29д', 'isFormingAddress': True},
            ],
        },
        'isNeedHideExactAddress': False,
    }


def test_fully_specified_non_hidden_house_retains_source_coordinates():
    row = convert(offer())
    assert row['coordinates'] == [55.8, 49.1]
    assert row['geo_accuracy'] == 'building'


@pytest.mark.parametrize('hidden', [True, None])
def test_hidden_or_unknown_visibility_is_not_exact_building(hidden):
    source = offer()
    source['isNeedHideExactAddress'] = hidden
    row = convert(source)
    assert row['coordinates'] is None
    assert row['geo_accuracy'] is None


def test_missing_visibility_is_not_exact_building():
    source = offer()
    del source['isNeedHideExactAddress']
    assert convert(source)['coordinates'] is None


def test_house_category_without_house_number_is_not_exact_building():
    source = offer()
    source['geo']['address'][-1] = {'geoType': 'house'}
    assert convert(source)['coordinates'] is None


def test_rental_clause_banning_sublease_does_not_exclude_owner_property():
    assert rental_candidate('Готовый арендный бизнес с арендатором. По договору субаренда запрещена.')


def test_monthly_period_from_another_sentence_is_not_inherited():
    assert rent_claim('ГАБ. Арендная плата 1200000 рублей. Обслуживание 5000 рублей в месяц.') is None


@pytest.mark.parametrize('description', [
    'ГАБ. Магнит на соседней улице.',
    'ГАБ. Магнит в соседнем здании.',
    'ГАБ. Арендатор не Ozon, а локальный магазин.',
])
def test_brand_requires_an_explicit_positive_current_tenant_relationship(description):
    assert tenant_claim(description)[0] is None


def test_placeholder_house_is_not_a_precise_address():
    source = offer()
    source['geo']['userInput'] = 'Казань, адрес не указан'
    source['geo']['address'][-1] = {'geoType': 'house', 'name': 'не указан'}
    assert convert(source)['coordinates'] is None
