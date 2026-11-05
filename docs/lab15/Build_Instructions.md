# Release build — Windows x64

1. На Windows x64 установить Python 3.12 и создать venv.
2. Установить `requirements.txt`, `requirements-ai.txt`, `requirements-build.txt`. Локальную модель разместить по `assets/models/README.md`.
3. Из каталога игры: `python -m unittest discover -s tests -q`.
4. `python -m PyInstaller BloodyTrail.spec --noconfirm`.
5. `dist/BloodyTrail/BloodyTrail.exe --release-check путь-к-output.json`; дождаться завершения, проверить passed=true. Камера/микрофон не включаются.
6. `python tools/prepare_demo.py`; затем `python tools/package_release.py`.
7. Передать `dist/BloodyTrail-Windows-x64-RC1.zip` и `.sha256`. Целиком распаковать и запустить BloodyTrail.exe.

Не переносить только EXE: `_internal` обязателен. Сохранения по умолчанию вне bundle в `%LOCALAPPDATA%/BloodyTrail/saves`; `--save-dir` задаёт альтернативу. Python и модель включены, сеть для игры не нужна.

Непроверенное: другой чистый ПК, SmartScreen, подпись издателя, аппаратная точность. Сборка не подписана. Синтетический release-check не является аппаратным acceptance test.

PyInstaller: [добавление данных](https://pyinstaller.org/en/stable/usage.html#what-to-bundle-where-to-search), [multiprocessing](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing). Точка входа вызывает freeze_support до argparse/GUI. Спецификация явно собирает данные, модель и нативные зависимости; исходные reference-картинки не входят.
