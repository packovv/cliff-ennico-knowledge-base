# Происхождение записей

Сохранены переданные результаты публичного исследования: для всех 53 названий найдены видео официального канала и индивидуальные даты публикации. Для `019` подтверждена идентичность видео по последовательности вступления; остальные 52 остаются candidate, поскольку их текст не сравнивался с записью. Это не проверка точности всех расшифровок или актуальности советов.

Документ фиксирует уже выполненное исследование, переданное исполнителю в текущем запросе. В этом followup сетевые запросы не повторялись; исходные JSON-ответы и файлы субтитров не были переданы и здесь не выдаются за сохранённые вложения. Дата фиксации результатов не означает дату исследования, публикации или записи выступления.

## Источники и способ проверки

- Официальная страница автора https://succeedinginyourbusiness.com/ ссылается на канал `UCahNH8FgCHT0fFt0cONZj0A` и непосредственно на https://www.youtube.com/watch?v=mNe7hUAkx4M.
- Официальный канал: https://www.youtube.com/channel/UCahNH8FgCHT0fFt0cONZj0A.
- По переданному исследованию использовался установленный `yt-dlp 2026.08.19` с `--ignore-config --no-cache-dir --skip-download` для публичных метаданных, без cookies и чтения пользовательской конфигурации. Здесь эти команды не выполнялись.
- Для каждого видео получены совпадение названия, `channel_id` и индивидуальный `upload_date`. Последний сохранён в `published_at` как YYYY-MM-DD. Это дата публикации найденного видео, а не установленная дата записи выступления.

## Уровни доказательства

**A, candidate.** Официальная страница связывает автора с каналом; индивидуальные метаданные YouTube совпадают по названию и channel_id. Вступление локального TXT не сравнивалось. Название, канал и дата подтверждают сведения о видео-кандидате, но не идентичность локальной расшифровки. URL, дата и это ограничение сохраняются в `source-metadata.csv`; поля URL и даты каталога остаются пустыми.

**S, confirmed для `019`.** Источник `How To Sell Anything To Anybody with Cliff Ennico.txt` сопоставлен с видео `mNe7hUAkx4M`, на которое ссылается официальный сайт. Переданное сравнение установило совпадение следующей последовательности публичных автоматических субтитров со вступлением локального текста.

| Позиция в публичных субтитрах | Текст публичных автоматических субтитров |
|---|---|
| 00:00.480 | `good evening everyone thank you so much` |
| 00:02.280 | `for joining us my name is Dina maon` |
| 00:04.920 | `I am a certified mentor and counselor` |
| 00:07.080 | `with score` |
| 00:10.599 | `of being the workshop woman` |
| 00:21.560 | `present how to sell anything to anyone` |

В локальном распознавании имя записано как Dena Maison, в публичных субтитрах как Dina maon. Это отмеченная ASR-вариация, а не основание исправлять исходник или утверждать правильное написание имени. Остальная приведённая последовательность вступления совпала по переданному сравнению. Подтверждена идентичность видео, не полная точность текста, не атрибуция каждого говорящего и не дата записи выступления.

Эти позиции относятся только к полученным публичным субтитрам вступления. Они не добавлялись в TXT или chunks и не являются восстановленными таймкодами всего корпуса.

## Карта публикаций

ID относится к сохранённой строке `catalog.csv`; точный путь указан в `source-metadata.csv`. Каждая ссылка ведёт на найденное видео, а статус A/S определяет, подтверждена ли привязка к TXT. Все даты ниже являются upload_date, а не датами записи.

| ID | Видео | Публикация | Доказательство |
|---|---|---|---|
| 001 | https://www.youtube.com/watch?v=QQHS85NIK3w | 2015-03-24 | A |
| 002 | https://www.youtube.com/watch?v=jFlLwGICK54 | 2020-05-28 | A |
| 003 | https://www.youtube.com/watch?v=JMhY_3xIvCQ | 2016-08-19 | A |
| 004 | https://www.youtube.com/watch?v=qRPIjSaZlz8 | 2018-05-02 | A |
| 005 | https://www.youtube.com/watch?v=NDZjvuVi7qg | 2020-01-08 | A |
| 006 | https://www.youtube.com/watch?v=KIAe9pLFFbI | 2021-02-12 | A |
| 007 | https://www.youtube.com/watch?v=cjhEVwIpy-U | 2016-11-27 | A |
| 008 | https://www.youtube.com/watch?v=JMMbnX5eEf4 | 2017-02-11 | A |
| 009 | https://www.youtube.com/watch?v=yL8xPHxQzY8 | 2015-06-28 | A |
| 010 | https://www.youtube.com/watch?v=DmdubHMlsJ0 | 2016-06-08 | A |
| 011 | https://www.youtube.com/watch?v=VIVBXUzADPQ | 2016-05-13 | A |
| 012 | https://www.youtube.com/watch?v=q0XYAeVSCOs | 2016-04-19 | A |
| 013 | https://www.youtube.com/watch?v=15HRmnxuoeU | 2015-05-08 | A |
| 014 | https://www.youtube.com/watch?v=XGL4yRPcHJ8 | 2016-05-19 | A |
| 015 | https://www.youtube.com/watch?v=H4-m3XOdy5A | 2015-04-13 | A |
| 016 | https://www.youtube.com/watch?v=D7eRDI2_pMU | 2015-05-08 | A |
| 017 | https://www.youtube.com/watch?v=f52KnX_vc0M | 2016-02-02 | A |
| 018 | https://www.youtube.com/watch?v=7JH5l7k1_Vk | 2020-04-08 | A |
| 019 | https://www.youtube.com/watch?v=mNe7hUAkx4M | 2013-01-17 | S |
| 020 | https://www.youtube.com/watch?v=3tJqNhLaLwE | 2018-05-17 | A |
| 021 | https://www.youtube.com/watch?v=1viuhVp8Ugk | 2018-05-18 | A |
| 022 | https://www.youtube.com/watch?v=rDzv9Z1r2Vw | 2016-02-23 | A |
| 023 | https://www.youtube.com/watch?v=camtt3FFpRw | 2016-02-23 | A |
| 024 | https://www.youtube.com/watch?v=uICO7e7XzvM | 2016-04-19 | A |
| 025 | https://www.youtube.com/watch?v=ZBnoErKeH_I | 2020-10-26 | A |
| 026 | https://www.youtube.com/watch?v=HfdOwY33Dw0 | 2017-12-05 | A |
| 027 | https://www.youtube.com/watch?v=PlTLAGxV6uk | 2015-04-03 | A |
| 028 | https://www.youtube.com/watch?v=pzayKlv8Qpk | 2016-02-23 | A |
| 029 | https://www.youtube.com/watch?v=C9EY5pGJ9Eg | 2015-05-16 | A |
| 030 | https://www.youtube.com/watch?v=lJ37Ua81bks | 2016-04-05 | A |
| 031 | https://www.youtube.com/watch?v=KcX-dvExgwY | 2015-04-06 | A |
| 032 | https://www.youtube.com/watch?v=94DXMDv1duE | 2015-11-14 | A |
| 033 | https://www.youtube.com/watch?v=CaG533bdZHw | 2015-09-08 | A |
| 034 | https://www.youtube.com/watch?v=2YF0_N7DuwA | 2015-07-07 | A |
| 035 | https://www.youtube.com/watch?v=aj29Xy33lDE | 2020-07-31 | A |
| 036 | https://www.youtube.com/watch?v=nGque0BeUH4 | 2015-08-26 | A |
| 037 | https://www.youtube.com/watch?v=j8v6CFwMi9c | 2015-08-26 | A |
| 038 | https://www.youtube.com/watch?v=NLmO5DXNEHg | 2015-08-27 | A |
| 039 | https://www.youtube.com/watch?v=1N47MaGpJAM | 2015-08-27 | A |
| 040 | https://www.youtube.com/watch?v=lK89ooux1hw | 2015-08-27 | A |
| 041 | https://www.youtube.com/watch?v=gTyRQert4JY | 2015-08-26 | A |
| 042 | https://www.youtube.com/watch?v=qd5RFlxNSAY | 2016-05-16 | A |
| 043 | https://www.youtube.com/watch?v=bV7hx2SR50w | 2016-05-16 | A |
| 044 | https://www.youtube.com/watch?v=5oMZshWmRss | 2015-08-27 | A |
| 045 | https://www.youtube.com/watch?v=TIjAFoCX91I | 2015-05-08 | A |
| 046 | https://www.youtube.com/watch?v=1SloL-Zi5ys | 2017-09-01 | A |
| 047 | https://www.youtube.com/watch?v=rp7uMYauloo | 2017-10-25 | A |
| 048 | https://www.youtube.com/watch?v=XESv6QWeTqo | 2015-11-13 | A |
| 049 | https://www.youtube.com/watch?v=5ArKUfQUbIQ | 2013-03-06 | A |
| 050 | https://www.youtube.com/watch?v=U7lRh76VtTs | 2021-03-08 | A |
| 051 | https://www.youtube.com/watch?v=HujLQwVlmzI | 2016-07-01 | A |
| 052 | https://www.youtube.com/watch?v=94aqe-RA9aI | 2020-04-01 | A |
| 053 | https://www.youtube.com/watch?v=wEChfncwMZc | 2022-02-02 | A |

## Точный блокер

Endpoint timedtext дважды отклонил автоматизацию; второй ответ был HTTP 429. Попытки остановлены по правилу двух одинаковых ошибок. В этом followup не выполнялись новые запросы, обход ограничения, обращения с cookies или повторная загрузка субтитров.

Поэтому вступления остальных 52 TXT не сверены с видео и их нельзя повысить до confirmed только по заголовкам и датам. Дальнейшая проверка требует отдельно разрешённого доступа к публичным субтитрам или ручного сопоставления с записью, без повторения заблокированной автоматизации. До такого сравнения статусы остаются candidate.

## Граница технической проверки

Генератор проверяет форму URL и даты, наличие evidence, сохранность таблицы и правила переноса confirmed в каталог. Он не обращается к YouTube и не устанавливает истинность переданного исследования. Предыдущее независимое одобрение технической реализации подтверждает целостность корпуса и работу генератора, но не подтверждает за него происхождение 52 кандидатов или точность всех текстов. Внешние учебные ИИ-проверки остаются not_run.
