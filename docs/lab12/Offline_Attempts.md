# Фактические offline-проверки

Это НЕ распознавание 20 произнесённых фраз: проверяется маршрутизация текста после STT.

| № | Текст | Ожидалось | Получено | Верно |
|---|---|---|---|---|
| 1 | Покажи улики | evidence | evidence | True |
| 2 | Анализируй запись | analyze | analyze | True |
| 3 | Повтори показания | testimony | testimony | True |
| 4 | Какие есть версии | versions | versions | True |
| 5 | Сравни следы | analyze | analyze | True |
| 6 | ПОКАЖИ УЛИКИ | evidence | evidence | True |
| 7 | АНАЛИЗИРУЙ ЗАПИСЬ | analyze | analyze | True |
| 8 | ПОВТОРИ ПОКАЗАНИЯ | testimony | testimony | True |
| 9 | КАКИЕ ЕСТЬ ВЕРСИИ | versions | versions | True |
| 10 | СРАВНИ СЛЕДЫ | analyze | analyze | True |
| 11 | покажи улики. | evidence | evidence | True |
| 12 | анализируй запись. | analyze | analyze | True |
| 13 | повтори показания. | testimony | testimony | True |
| 14 | какие есть версии. | versions | versions | True |
| 15 | сравни следы. | analyze | analyze | True |
| 16 | Покажи улики | evidence | evidence | True |
| 17 | Анализируй запись | analyze | analyze | True |
| 18 | Повтори показания | testimony | testimony | True |
| 19 | Какие есть версии | versions | versions | True |
| 20 | Сравни следы | analyze | analyze | True |

Точность маршрутизации текста: 20/20 = 100%. Это не Voice Accuracy.

OpenCV: три одноцветных кадра, результат: [{'brightness': 0, 'present': False, 'reliable': False, 'motion': 0.0}, {'brightness': 80, 'present': False, 'reliable': False, 'motion': 0.0}, {'brightness': 255, 'present': False, 'reliable': False, 'motion': 0.0}]

Vosk, синтетическая тишина 2 с: {'text': ''}
