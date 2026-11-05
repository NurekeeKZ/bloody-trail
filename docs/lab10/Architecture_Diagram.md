# Архитектура Bloody Trail

Срез v0.4 после MVP 1 / ЛР11. Существующая архитектура сохраняется. Сплошные связи — текущий поток; пунктир и подпись «план» — будущая интеграция. Высокоуровневая цепочка ниже показывает цикл интеллектуального действия: обычное перемещение не требует AI.

```mermaid
flowchart LR
    U[User] --> I[Interface]
    I --> G[Game Logic]
    G --> A[AI Module]
    A --> D[Data / Storage]
    D --> R[Result]
    R --> I
```

## Компоненты и границы

```mermaid
flowchart TB
    user[Игрок: клавиатура и мышь] --> ui[Pygame UI: окна, кнопки, текст, HUD]
    ui --> sm[SceneManager: стек сцен]
    sm --> exploration[Exploration: Player, коллизии, InteractionSystem]
    exploration --> worldcam[Camera: слежение за игровым миром]
    sm --> investigation[Investigation / ObjectInspection: JSON hotspots]
    sm --> board[Evidence Board / Inventory]
    sm --> dialogue[Dialogue UI]
    dialogue --> dm[DialogueManager: условия и реплики]
    investigation --> em[EvidenceManager: сбор и проверка связей]
    board --> em
    dm --> gs[GameState: улики, flags, ресурсы, день]
    em --> gs
    sm --> assistant[N.U.R.S. UI: текстовые команды]
    assistant --> nlp[AI Module: локальный IntentClassifier]
    nlp --> dispatch[Assistant.execute: разрешённые действия]
    dispatch --> em
    dispatch --> board
    dispatch --> map[Карта маршрута]
    sm --> qte[QTE: тренировка и сюжетный вход в квартиру]
    qte --> gs
    qte -. план: второй эпизод .-> future[QTE второй главы]
    mic[Микрофон: план] -.-> voice[AI Voice: STT / VAD, план]
    voice -. команды .-> nlp
    voice -. шум в эпизоде тишины .-> gs
    webcam[Веб-камера: план] -.-> cv[Camera Module: лицо / движение, план]
    cv -. игровой индикатор .-> gs
    consent[Settings: согласия и доступность] -. перед захватом .-> voice
    consent -. перед захватом .-> cv
    gs --> save[Save System: v4, валидация и миграции]
    save <--> storage[(saves: JSON / checkpoint)]
    json[(src/data: dialogues, evidence, rules, worlds, investigations, intents)] --> dm
    json --> em
    json --> nlp
    json --> investigation
    gs --> result[Results / Game Over / новые реплики]
    result --> ui
    sm --> commerce[Monetization UI: описание демо / full / DLC]
    commerce -. план .-> access[Content Access: demo / full test entitlement]
    access -. доступ к главам .-> sm
    assets[(assets: спрайты и фоны)] --> ui
```

| Компонент | Реальный файл / планируемая граница | Контракт |
|---|---|---|
| Pygame UI | `src/ui/widgets.py`, `src/scenes/` | Логические координаты 1280×720, масштабирование ввода; UI не подтверждает улику самостоятельно |
| SceneManager | `src/core/scene_manager.py` | push/pop/replace; Investigation возвращает прежний Exploration |
| DialogueManager | `src/systems/dialogue.py` | JSON + evidence_ids/flags → доступные реплики |
| EvidenceManager | `src/systems/evidence.py` | collect/propose/evaluate; требуется полный набор оснований, повторный сбор без награды |
| QTE | `src/scenes/settings.py`, `src/scenes/qte.py` | Практика и один сюжетный эпизод: таймер, здоровье, checkpoint; второй планируется BT-17 |
| AI Voice | Новая граница в `src/ai/`, BT-25/26 | PCM → текст → существующий IntentClassifier; VAD → ограниченный игровой сигнал |
| Camera Module | Новая граница в `src/ai/`, BT-27 | Кадр → наличие лица/движение → игровой индикатор; не детектор лжи |
| Save System | `src/systems/save.py` | Проверка версии, конечных чисел и доказательств до bind_state; атомарная замена JSON |
| Monetization / Content Access | UI `src/scenes/menu.py`; проверка доступа планируется BT-31 | Карточки пока заблокированы; будущий тестовый entitlement не является оплатой/DRM |

N.U.R.S. помогает проверять правила, но не создаёт доказательства из текста команды. Будущие сенсоры передают результат через тот же слой логики и не записывают flags напрямую. При загрузке не возобновлять захват автоматически. Клавиатурные альтернативы должны использовать те же игровые последствия. Сеть и внешние AI-сервисы не входят в обязательный путь запуска.
