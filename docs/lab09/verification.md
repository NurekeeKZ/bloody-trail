# Лабораторная работа №9 — отчёт о проверке

28 октября 2026. Windows, Python 3.12.14, Pygame 2.6.1. Автотесты используют SDL_VIDEODRIVER=dummy и SDL_AUDIODRIVER=dummy и временные слоты без изменения прогресса пользователя.

## Выполненные команды

```powershell
cd G:\bloody\bloody_trail
& G:\bloody\.venv\Scripts\python.exe -m unittest discover -s tests -v
& G:\bloody\.venv\Scripts\python.exe main.py --smoke
& G:\bloody\.venv\Scripts\python.exe -m compileall -q src main.py
```

**37 тестов прошли** — 20 прежних и 17 новых. Smoke создал 19 PNG. Проверка компиляции не выявила синтаксических ошибок.

## Трассировка новых проверок

Все перечисленные тесты находятся в tests/test_lab09.py и завершились PASS.

| Тест | Что проверяет |
|---|---|
| test_start_waits_and_menu_has_six_working_entries | Start ждёт ввод; шесть пунктов меню; disabled Continue; Load/Settings/DLC/Exit |
| test_full_success_transition_chain | Start → Menu → Game → Pause → Game → Results → Menu и загрузка финала |
| test_failure_retry_and_menu_transition | Подтверждённый отказ → Game Over → checkpoint → Game; загрузка и меню |
| test_pause_all_settings_links_and_escape | Вкладки настроек из паузы, сохранение и загрузка |
| test_manual_slot_is_independent | Новая игра и autosave не изменяют ручной слот |
| test_load_empty_and_corrupt_slots | Пустые/повреждённые слоты и сохранность текущего состояния |
| test_settings_persist_audio_and_mute | Создание звуков, громкость и выключение |
| test_settings_corruption_safe_default | Повреждённые настройки дают безопасные значения |
| test_controls_change_actual_direction | Выбранная схема влияет на направление движения |
| test_sensor_consent_confirmation_cancel_and_revoke | Подтверждение, отмена, сохранение и отзыв локального согласия |
| test_qte_modes_and_no_story_mutation | Три режима QTE, успех/тайм-аут, отсутствие сюжетных изменений |
| test_time_excludes_pause_settings_results_and_counts_elapsed | Реальное elapsed-время и исключение паузы/настроек |
| test_old_save_migration | Сохранение v1 читается с play_seconds=0 |
| test_fullscreen_invokes_real_display_flags_and_persists | SDL-флаги FULLSCREEN/RESIZABLE через mock, сохранение настройки |
| test_button_hover_once_and_keyboard_navigation | Один hover-звук при входе; ↑/↓/Enter пропускают disabled |
| test_reduced_motion_disables_fade_and_rain_animation | Уменьшение анимации даёт неизменный стартовый кадр |
| test_results_and_gameover_do_not_create_checkpoint | Game Over и сохранение финального состояния не заменяют checkpoint |

Прежние tests/test_game.py проверяют коллизии, дистанцию взаимодействий, возврат из осмотра в ту же позицию, сбор 12 улик, три исхода, четыре цепочки, отказы NLP и координаты мыши при 1920×1080.

## Визуальная проверка

Рендерятся start, menu, exploration, investigation, assistant, map, dialogue, pause, settings_sound, settings_controls, settings_qte, settings_privacy, load, dlc, qte, inventory, board, results, game_over. Шесть основных экранов и новые вспомогательные панели просмотрены на PNG 1280×720. Smoke использует подготовленные данные; достижимость финалов проверяется интеграционным тестом, а не снимками.

## Границы результата

Полноэкранное переключение физического монитора и слышимость звуков не проверялись в этом этапе: SDL-вызов проверен через mock, звуки созданы в dummy-драйвере. Не выполнялось полное прохождение живой клавиатурой. Нет заявлений о работе сенсоров, платежей, сюжетных QTE, расхода здоровья/репутации: этих функций здесь нет.

## Ручная приёмка перед защитой

1. Запустить run.bat, проверить дождь и переход клавишей в меню.
2. Проверить мышью и ↑/↓/Enter шесть пунктов; новую игру создавать после нужного ручного сохранения.
3. Проверить движение, HUD, E и возврат, затем Esc → Pause → Продолжить.
4. Сохранить и загрузить ручной слот; проверить позицию и улики.
5. Прослушать hover/click при 0/20/100%; проверить F11 в обе стороны и попадание мыши в кнопки после изменения размера.
6. Пройти тренировку QTE в трёх режимах, проверить уменьшение анимации.
7. Проверить отмену и отзыв локального согласия; устройства не должны включаться.
8. Подтвердить отказ, повторить checkpoint; собрать цепочки и получить Results, вернуться в меню.
9. Зафиксировать реальные замечания двух студентов отдельно. Этот отчёт не имитирует их участие.
