# Состав изменения RC3

Пути указаны относительно `G:\bloody\bloody_trail`.

## Новые рабочие модули
- `src/ui/portraits.py` — PortraitManager, авторские портреты и выражения.
- `src/ai/pathfinding.py` — NPCPathfinding / A*.
- `src/ai/companion.py` — CompanionAI и четыре режима.
- `src/entities/npc.py` — PatrolNPC.
- `src/scenes/companion.py` — меню F.
- `src/systems/puzzles.py` — HiddenEvidenceSystem, PuzzleManager, HintManager.
- `src/scenes/puzzles.py` — интерактивные коды, фрагменты, сравнение фото.
- `src/ui/location_art.py`, `src/ui/apartment_art.py` — оригинальная временная графика.
- `src/data/puzzles.json` — задания, требования, ответы, награды и подсказки.
- `src/data/maps/{station,apartment,archive,metro,helios,port}.json` — отдельные карты.
- `assets/portraits/<ID>/<emotion>.png` — 72 PNG; `assets/portraits/README.md` — замена ассетов.

## Изменённые рабочие модули
- `src/core/game.py`, `state.py` — подключение карт/систем и новое сохраняемое состояние.
- `src/systems/save.py` — v7, миграция v1–v6 и актуализация отображаемых имён.
- `src/systems/audio.py` — атмосфера локаций с сохранением настроек и сенсорного отключения.
- `src/scenes/exploration.py`, `investigation.py`, `overlays.py`, `campaign.py`, `sensors.py` — соединение механик с игровыми сценами.
- `src/ui/art.py`, `prologue_art.py`, `investigation_art.py` — портреты, карты, интерьер.
- Тексты остальных JSON, сцен и старых генераторов данных обновлены на новые имена; технические ID не менялись.
- `src/data/evidence.json`, `investigations.json`, `dialogues.json`, `prologue.json`, `rules.json`, `worlds.json` — новые задания, портретные параметры, биография и имена.
- `BloodyTrail.spec` — включение портретов; `tools/package_release.py` — RC3.

## Проверки и документация
- `tests/test_expansion.py` — 16 новых проверок.
- `tests/scenario_steps.py` — решения через реальные обработчики игровых сцен.
- `tests/test_beta.py`, `test_game.py`, `test_lab09.py` — обновлённый маршрут с головоломками и ручными выводами; ожидаемые имена обновлены в остальных тестах.
- `docs/expansion/Expansion_Report.md`, `Demo_Walkthrough.md`, `Changed_Files.md`.
- `docs/expansion/tests.log`, `source_runtime.json`, `packaged_runtime.json`.
- `docs/screenshots/expansion/*.png`, `README.md`.

Файлы исходных Project Charter и Game Concept Document не изменялись. Переименование и дополнительные механики следуют более позднему заданию пользователя. Старые лабораторные отчёты сохраняют историческую фактуру и не выдают старые результаты за новые.
