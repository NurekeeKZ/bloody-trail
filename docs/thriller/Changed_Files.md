# Файлы изменения RC4

База: `G:\bloody\bloody_trail`.

Новые модули:
- `src/systems/story_manager.py` — последствия, проверка состояния, условия пяти концовок.
- `src/systems/stealth_system.py` — калибровка, обнаружение, четыре типа QTE.
- `src/ai/motion_detector.py` — оптический поток в области головы/верхней части тела, контроль надёжности.
- `src/scenes/thriller.py` — склад, прятки, погоня, ранение, плен, побег, переулок/улица и финалы.
- `src/scenes/stealth_settings.py` — чувствительность и доступность.
- `src/core/thriller_check.py` — повторяемая проверка нового эпизода в исходниках и собранном EXE без устройств.
- `src/data/chase.json`, `branch_rooms.json`, `branch_endings.json` — QTE, карты эпизода, финальные реплики.
- `tests/test_thriller.py` — 35 проверок.

Изменены:
- `src/core/state.py`, `game.py` — состояние v8, подключение/восстановление эпизода, выключение звука при захвате.
- `src/systems/save.py`, `settings.py`, `campaign.py`, `audio.py` — миграции, настройки, достижения, сердцебиение.
- `src/ai/devices.py` — подключение нового процессора камеры к прежнему worker.
- `src/scenes/qte.py`, `src/scenes/exploration.py`, `campaign.py`, `overlays.py`, `evidence_board.py`, `settings.py` — вход на склад, реакции, NPC, страницы улик, доступ к концовкам и настройкам.
- `src/ui/art.py` — временный спрайт неизвестного преследователя.
- `src/data/maps/port.json`, `evidence.json` — объект склада и два новых материала.
- `src/core/release_check.py`, `tools/prepare_demo.py`, `tools/package_release.py` — Windows-проверка, отдельный демонстрационный слот, RC4.
- `README.md` и корневой README — актуальные запуск и управление.

Документы:
- `docs/thriller/Stealth_Branches_Report.md`
- `docs/thriller/AI_Experiments.md`
- `docs/thriller/Demo_Walkthrough.md`
- `docs/thriller/Changed_Files.md`
- `docs/thriller/tests.log`, `source_runtime.json`, `packaged_runtime.json`, `screenshots/`

Зависимости уже были установлены; новые пакеты не добавлялись. `requirements.txt` и `requirements-ai.txt` сохраняют совместимые проверенные версии. Используются существующие SceneManager, SaveManager, SensorSession, EvidenceManager и AudioManager; параллельных замен этих систем нет.
