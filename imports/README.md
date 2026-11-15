# Импорт

Добавляйте только данные, на использование которых у вас есть права, без контактов продавцов и секретов.
Формат файла `*.json` — массив объектов. `title` и `sources: [{name, url}]` обязательны.
`name`: Авито, ЦИАН или Домклик. `price`, `area`, `monthly_rent` — числа в рублях/м²;
неизвестные поля — null. Координаты `[широта, долгота]` требуют `coordinate_source` и
`geo_accuracy: building | parcel | street`. Для подтверждения: `active_tenant`,
`payments_confirmed`, `contract` должны быть true; нужна `verification_evidence`.
Не публикуйте персональные данные документов — укажите обезличенное основание проверки.
См. `analyzer/validation.py` для полной схемы.
