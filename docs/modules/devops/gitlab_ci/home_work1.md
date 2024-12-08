**Домашнее задание №7**

Сделайте форк проекта [counter-backend](https://git.devops-teta.ru/materials/counter-backend) и доработайте следующий пайплайн:  
stages:  
  - build  
  - test  
  - publish  
variables:  
  POETRY\_IMAGE: registry.devops-teta.ru/materials/ci/images/poetry:1.4.1-3.11.6-bookworm  
  KANIKO\_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1  
  POETRY\_CACHE\_DIR: .cache/poetry  
  PIP\_CACHE\_DIR: .cache/pip  
  GIT\_CLONE\_PATH: $CI\_BUILDS\_DIR/$CI\_PROJECT\_PATH\_SLUG  
default:  
  before\_script:  
    - set -eu  
  
Update Cache:  
  stage: .pre  
  needs: \[\]  
  image: &poetry\_image  
    name: $POETRY\_IMAGE  
    entrypoint: \[""\]  
  cache:  
    - &poetry\_packages  
      key: poetry-packages  
      paths:  
        - .cache  
      unprotect: true  
    - &poetry\_venv  
      key:  
        prefix: poetry-venv  
        files:  
          - poetry.lock  
      paths:  
        - .venv  
      unprotect: true  
  script:  
    - &poetry\_install poetry install --no-root --no-interaction  
  
Build Package:  
  stage: build  
  needs:  
    - job: Update Cache  
      artifacts: false  
  image:  
    name: $POETRY\_IMAGE  
    entrypoint: \[""\]  
  cache:  
    - \<\<: \*poetry\_packages  
      policy: pull  
    - \<\<: \*poetry\_venv  
      policy: pull  
  script:  
    - \*poetry\_install  
    - mkdir -p dist  
    - poetry export --without-hashes --format constraints.txt --output dist/constraints.txt  
    - poetry run python -m pip wheel --isolated --requirement dist/constraints.txt --wheel-dir dist/vendor  
    - poetry build --format wheel  
  artifacts:  
    paths:  
      - dist  
  
Publish Package:  
  stage: publish  
  needs:  
    - job: Build Package  
      artifacts: true  
  interruptible: false  
  image:  
    name: $KANIKO\_IMAGE  
    entrypoint: \[""\]  
  script:  
    - b64\_auth=$(printf '%s:%s' "$HARBOR\_USER" "$HARBOR\_PASSWORD" | base64 | tr -d '\\n')  
    - >-  
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR\_HOST" "$b64\_auth"  
      >/kaniko/.docker/config.json  
    - >-  
      /kaniko/executor  
      --cache  
      --use-new-run  
      --skip-unused-stages  
      --context "$CI\_PROJECT\_DIR"  
      --dockerfile "$CI\_PROJECT\_DIR/Dockerfile"  
      --destination "$HARBOR\_IMAGE:$IMAGE\_TAG"  
      --cache-repo "$HARBOR\_IMAGE/cache"  
  
_Во-первых,_ напишите на основе этого пайплайна шаблон, который необходимо подключить к counter-backend.  
  
_Во-вторых,_ добавьте задачу Run Tests, запускающую unit-тесты при помощи следующего скрипта:  
$ poetry install --no-root --no-interaction  
$ poetry run pytest --junitxml python.junit.xml  
  
Задача должна экспортировать отчет в формате [junit](https://docs.gitlab.com/ee/ci/yaml/artifacts_reports.html#artifactsreportsjunit) при любом завершении задачи (успешном или с ошибкой). Также исправьте зависимости задач так, чтобы публикация Docker-образа не происходила при ошибке в тестах.  
  
_В-третьих_, модифицируйте правила задач так, чтобы:  
 

*   в запросах на слияние запускались только задачи, проверяющие корректность кода;
*   в тегах запускались только задачи, собирающие Docker-образ;
*   в ветке по умолчанию запускались все задачи.

Для проверки предоставьте:  
 

*   ссылки на отработанные пайплайны в counter-backend;
*   ссылку на точку входа в шаблон для backend;
*   diff — изменений в шаблонах при подключении шаблона для counter-backend.