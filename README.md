# Неофициальная синхронная обёртка для API сервиса lknpd.nalog.ru на Python.

Служит для автоматизации отправки информации о доходах самозанятых и получения информации о созданных чеках.

Inspired by [https://github.com/alexstep/moy-nalog](https://github.com/alexstep/moy-nalog)

## Использование
Установите пакет
```bash
pip install nalogapi
```

Инициализаци и авторизация
```python
from nalogapi import NalogAPI
NalogAPI.configure("inn", "password") #password that used in lkfl
```

Отправка информации о доходе
```python
NalogAPI.addIncome(datetime.utcnow(), 1.0, "Предоставление информационных услуг #970/2495")
```

Функция возвращает ссылку на чек вида [https://lknpd.nalog.ru/api/v1/receipt/344111066022/200egltxe8/print](https://lknpd.nalog.ru/api/v1/receipt/344111066022/200egltxe8/print)