# GitHub: подготовка и перенос

На 2026-10-28 Git установлен, папка `G:\bloody` не является Git-репозиторием, CLI `gh` отсутствует, интеграция GitHub не подключена. Ни репозиторий, ни Issues, ни Project не созданы. Подготовлены локальные README, `.gitignore`, WBS, Kanban и 37 файлов `issues/BT-XX.md`. Следующие команды — инструкция для реального владельца после установки GitHub CLI и авторизации; они не были выполнены.

## 1. Private repository

Рабочий корень репозитория — `G:\bloody`, игра находится в `bloody_trail/`. Каждый участник указывает **своё** имя и email, связанные с его аккаунтом; допустим личный GitHub noreply email. Не подставлять Participant 1/2 как выдуманное авторство.

```powershell
Set-Location G:\bloody
gh auth login
gh auth status
git init -b main
git config user.name 'ВАШЕ РЕАЛЬНОЕ ИМЯ'
git config user.email 'ВАШ ПОДТВЕРЖДЁННЫЙ EMAIL'
git add README.md .gitignore bloody_trail
git diff --cached --stat
git diff --cached
# После просмотра содержимого — реальный снимок принятой основы, не фиктивная история разработки.
git commit -m "Record reviewed Bloody Trail baseline and project plan"
$btRepo = 'ВАШ_LOGIN/bloody-trail'
gh repo create $btRepo --private --source . --remote origin --push
gh repo view $btRepo --json nameWithOwner,isPrivate,url
```

Перед публикацией не включать `.venv`, пользовательские saves, секреты и исходные DOCX из Downloads. Выбрать свободное имя репозитория; при существующем repo сначала проверить владельца и private-видимость, затем подключать его как remote, не перезаписывая чужую историю. Флаг `--private` и перенос локального репозитория через `--source/--push` описаны в [официальной документации gh repo create](https://cli.github.com/manual/gh_repo_create).

В Settings репозитория пригласить второго участника по настоящему login и предоставить доступ преподавателю по условиям курса. Проверить принятие приглашения. Создавать ветки `feature/BT-XX-short-name`, осмысленные commits и PR; второй участник проверяет изменения. Сохранить реальные ссылки и результаты в задачах. Первичный импорт не доказывает участие обоих студентов.

## 2. Issues

У каждой задачи есть готовое тело. Пример создания одной задачи после проверки отсутствия такого WBS-ID среди открытых и закрытых Issues:

```powershell
$btRepo = 'ВАШ_LOGIN/bloody-trail'
gh issue list --repo $btRepo --state all --search '"BT-09" in:title'
gh issue create --repo $btRepo --title '[BT-09] Ручной маршрут текущего кабинета' --body-file 'G:\bloody\bloody_trail\docs\lab10\issues\BT-09.md'
```

Применить к BT-01…BT-37, используя названия из WBS.json. Для Done сохранить пояснение об исходном срезе, затем закрыть Issue после просмотра свидетельств; это не подмена реального PR. Назначать assignee только по подтверждённому соответствию Participant → login. Подготовленные файлы не являются опубликованными Issues. `--body-file` передаёт текст без потери переносов: [gh issue create](https://cli.github.com/manual/gh_issue_create).

Создать labels P0/P1/P2, areas code/story/art/AI/testing/docs, blocked. Сроки внести в поле проекта Target date; зависимости WBS связать с реальными URL после появления номеров. В локальной копии вести таблицу `WBS-ID → Issue URL`, не придумывать номера. Не запускать повторный массовый импорт без проверки дублей.

## 3. GitHub Projects Kanban

```powershell
gh auth refresh -s project
gh project create --owner '@me' --title 'Bloody Trail — Development' --format json
```

Использовать фактический номер из результата. В интерфейсе проекта проверить private-видимость, дать доступ обоим участникам, связать репозиторий. Создать Board view, группировка по Status; значения и порядок: **Backlog, To Do, In Progress, Testing, Done**. Удалить/переименовать стандартные значения, если они отличаются. Добавить поля WBS ID (text), Priority (single select), Participant (single select), Target date (date), Estimate hours (number). [Создание проекта](https://cli.github.com/manual/gh_project_create).

```powershell
$btProjectNumber = 1 # ЗАМЕНИТЬ реальным номером созданного проекта
$btIssueUrl = 'URL_РЕАЛЬНОГО_ISSUE'
gh project item-add $btProjectNumber --owner '@me' --url $btIssueUrl
```

Добавить все реальные Issues и вручную заполнить поля из WBS.json, затем сверить количество карточек каждой колонки с Kanban.md. Номер проекта и URL выше — placeholders, не свидетельство создания. [Добавление Issue в проект](https://cli.github.com/manual/gh_project_item-add).

## 4. Проверка переноса

- Репозиторий и Project доступны только согласованным аккаунтам.
- 37 уникальных WBS-ID, нет дубликатов; соответствие URL записано.
- Доска после MVP 1: Done 9, Testing 1, To Do 3, In Progress 0, Backlog 24. Далее обновлять по фактическим изменениям, сохраняя дату среза.
- Зависимости и критерии присутствуют; реальные assignees соответствуют ролям.
- Каждый студент самостоятельно внёс содержательный вклад и может объяснить его; фиктивные авторы и задним числом созданные commits не используются.
