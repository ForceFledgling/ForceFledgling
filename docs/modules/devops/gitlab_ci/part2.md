Масштабирование пайплайнов

На прошлом занятии мы написали пайплайн для довольно типового проекта на NextJS. Он может использоваться как и для монолитных веб-приложений, где для фронт и бэк части используется одна кодовая база, так и для полностью браузерных приложений (как в нашем примере).  
  
Несложно представить, как в нетривиальных продуктах появляется несколько репозиториев, содержащих аналогичные проекты (например, выносится отдельно внутренний интерфейс администратора), или же как в другом проекте, собирающемся в Docker-образ, мы захотим переиспользовать уже готовую задачу для сборки образа.  
  
Для переиспользования готовых пайплайнов GitLab использует механизм включений: директива [include](https://docs.gitlab.com/ee/ci/yaml/#include) задает список подключаемых пайплайнов. Источником может выступать файл в текущем репозитории, файл в другом репозитории на том же сервере GitLab, файл на произвольном HTTP сервере или шаблон, настроенный на уровне сервера GitLab.  
  
Далее мы будем рассматривать включения из отдельных репозиториев, как самый частый случай, и включения локальных файлов, которые используются для организации репозиториев шаблонных пайплайнов.  
  
Но сначала немного об оптимизации самого пайплайна.

Оптимизация пайплайна

YAML-якоря

YAML-якоря используются для ссылки на другие части YAML-документа, чтобы избежать дублирования данных. Они позволяют определить блок данных один раз и затем использовать ссылку на этот блок в нескольких местах документа.  
YAML-якоря создаются с помощью символа _&_ и идентификатора, который должен быть уникальным в пределах документа. Затем этот идентификатор можно использовать в качестве ссылки. При разборе документа YAML-процессор заменит эту ссылку на фактическое значение.  
  
Вот пример использования YAML-якоря:

```
car_details: &CAR_DETAILS 
  make: Toyota 
  model: Camry 
  year: 2021 
 
new_car: 
  <<: *CAR_DETAILS 
  color: White 
 
used_car: 
  <<: *CAR_DETAILS 
  odometer_reading: 32410 
  condition: Good
```

В этом примере мы определяем блок данных car\_details в качестве якоря и затем используем его для создания двух других объектов — new\_car и used\_car.  
  
Воспользуемся YAML-якорями, чтобы избавиться от повторов:

```
stages:
  - build
  - publish
variables:
  NODEJS_IMAGE: registry.devops-teta.ru/materials/ci/images/nodejs:18.18.2-bookworm
  KANIKO_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1
  NEXT_TELEMETRY_DISABLED: "1"
  NPM_CONFIG_CACHE: $CI_PROJECT_DIR/.cache/npm
  
Update Cache:
  stage: .pre
  needs: []
  allow_failure: true
  image: &nodejs_image
    name: $NODEJS_IMAGE
    entrypoint: [""]
  cache:
    - &npm_packages ### YAML Якорь
      key: npm-packages
      paths:
        - .cache
      unprotect: true
    - &npm_node_modules  ### YAML Якорь
      key:
        prefix: npm-node-modules
        files:
          - package-lock.json
      paths:
        - node_modules
      unprotect: true
  script:
    - &npm_clean_install ### YAML Якорь
      if [ ! -e node_modules ] ; then npm clean-install ; fi
  
# @NoArtifactsToSource
Lint:
  stage: .pre
  needs:
    - job: Update Cache
      artifacts: false
  allow_failure: true
  image: *nodejs_image
  variables:
    ESLINT_CODE_QUALITY_REPORT: eslint.codequality.json
  cache:
    - <<: *npm_packages ### ссылка на YAML Якорь
      policy: pull
    - <<: *npm_node_modules ### ссылка на YAML Якорь
      policy: pull
  script:
    - *npm_clean_install
    - npm run lint -- --format gitlab
  artifacts:
    paths:
      - $ESLINT_CODE_QUALITY_REPORT
    reports:
      codequality: $ESLINT_CODE_QUALITY_REPORT
  
# @NoArtifactsToSource
Build Package:
  stage: build
  needs:
    - job: Update Cache
      artifacts: false
  image: *nodejs_image
  cache:
    - <<: *npm_packages ### ссылка на YAML Якорь
      policy: pull
    - <<: *npm_node_modules ### ссылка на YAML Якорь
      policy: pull
    - key: npm-next-cache
      paths:
        - .next/cache
  script:
    - *npm_clean_install ### ссылка на YAML Якорь
    - npm run build
    - mv .next/standalone dist
    - mv public dist/public
    - mv .next/static dist/.next/static
  artifacts:
    expire_in: 1h
    paths:
      - dist
  
Publish Package:
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  variables:
    HARBOR_HOST: harbor.devops-teta.ru
    HARBOR_PROJECT: demo
    HARBOR_USER: robot_demo+gitlab
    HARBOR_PASSWORD: $__HARBOR_PASSWORD
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME:${CI_COMMIT_REF_NAME}_${CI_COMMIT_SHORT_SHA}"
      --cache-repo "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME/cache"
```

Before\_script и after\_script

[before\_script](https://docs.gitlab.com/ee/ci/yaml/#before_script) является одним из ключевых элементов, используемых в файле. gitlab-ci.yml для определения задач, которые должны быть выполнены перед началом выполнения каждого задания (job) пайплайна в GitLab CI. Он позволяет установить и настроить необходимое окружение перед выполнением фактического скрипта задания.  
  
Важно отметить, что содержимое before\_script будет выполнено перед каждым заданием пайплайна, независимо от его положения в .gitlab-ci.yml файле. А after\_script — после. Это позволяет обеспечить однородность окружения выполнения задач в рамках пайплайна.  
  
[before\_script](https://docs.gitlab.com/ee/ci/yaml/#before_script) обычно используется для выполнения следующих действий:  
  
Установка зависимостей: Выполнение команд для установки необходимых зависимостей или пакетов перед запуском заданий.  
Настройка окружения: Установка переменных окружения, настройка конфигурационных файлов и других параметров для заданий пайплайна.  
Подготовка ресурсов: Запуск контейнеров, развертывание виртуальных машин, настройка инфраструктуры и другие операции, необходимые для подготовки рабочей среды заданий.  
Настройка доступа: Создание или настройка учетных записей, прав доступа, ключей SSH и других ресурсов, необходимых для выполнения задач.  
  
Использование before\_script в GitLab CI позволяет унифицировать и автоматизировать процесс подготовки окружения перед выполнением задач пайплайна, обеспечивая последовательность и надежность выполнения.  
  
Директива default задает аргументы, применяемые ко всем задачам пайплайна. Воспользуемся ей, чтобы добавить ко всем задачам before\_script, переводящий shell в «строгий» режим:

```
default:
  before_script:
    - set -eu
```

Обратите внимание, что after\_script запускается в отдельном процессе shell и переменные заданные в before\_script и script не переносятся.

Rules

Сейчас наш пайплайн запускается при любых событиях GitLab (коммите в ветку, изменения в запросе на слияние и т. д.). Но некоторые задачи должны запускаться не всегда — например, мы не хотим публиковать образа из feature-веток или запускать статический анализатор в ветках, отличных от ветки по-умолчанию. Чтобы задать условия, при которых запускаются задачи, воспользуемся директивой [rules](https://docs.gitlab.com/ee/ci/yaml/#rules).  
  
Сделаем так, чтобы задача Lint запускалась при событиях запросов на слияния и в ветке по умолчанию:

```
Lint:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

Все правила вычисляются во время создания пайплайна по очереди, в порядке написания, до первого удовлетворяющего условиям. Они поддерживают следующие параметры:  
  
if — условие запуска задачи;  
changes — список файлов, при изменении которых запускается задача;  
exists — список файлов, при существовании которых запускается задача;  
allow\_failure — выставляет параметр allow\_failure при выполнении этого правила;  
variables — задает указанные переменные при выполнении этого правила;  
when —изменяет результат выполнения этого правила, по умолчанию он совпадает с директивой when, заданной в задаче; доступные варианты:  
on\_success — запустить задачу, когда все задачи в предыдущей стадии завершились успешно (или задачи, указанные в needs);  
on\_failure — запустить задачу, когда хотя бы одна родительская задача завершилась с ошибкой;  
never — не запускать задачу;  
always — запустить задачу независимо от статуса родительских задач;  
manual — запустить задачу вручную;  
Условия запуска используют свой синтаксис, описанный в [документации](https://docs.gitlab.com/ee/ci/jobs/job_control.html#cicd-variable-expressions).  
  
Опишем основы:  
 

*   $VARIABLE == "some value" – переменная равна строке;
*   $VARIABLE != "some value" – переменная не равна строке;
*   $VARIABLE1 == $VARIABLE2 – переменная равна другой переменной;
*   $VARIABLE1 != $VARIABLE2 – переменная не равна другой переменной;
*   $VARIABLE == null – переменная не задана;
*   $VARIABLE != null – переменная задана;
*   $VARIABLE == "" – переменная пуста;
*   $VARIABLE != "" – переменная не пуста;
*   $VARIABLE – переменная задана и не пуста;
*   $VARIABLE =~ /pattern/ – проверить, подходит ли значение переменной под регулярное выражение;
*   $VARIABLE !~ /pattern/ – проверить, что значение не подходит под регулярное выражение;
*   EXPRESSION1 || EXPRESSION2 – условный оператор ИЛИ;
*   EXPRESSION1 && EXPRESSION2 – условный оператор И;
*   (EXPRESSION) – группировка выражений;

  
Оператор && имеет приоритет выше чем ||, т. е. выражение $VAR1 && $VAR2 || $VAR3 эквивалентно ($VAR1 && $VAR2) || $VAR3.  
Зададим флаг, выключающий статический анализ — ENABLE\_LINT и напишем соответствующие правило:

```
variables:
  ENABLE_LINT: "true"
 
Lint:
  rules:
    - if: $ENABLE_LINT != "true"
      when: never
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

Здесь мы используем вариант с отрицанием, чтобы гарантировать, что задача не запустится независимо от других правил. Если бы мы использовали форму if: $ENABLE\_LINT == «true», то задача бы запустилась при выполнении следующих правил.  
  
Напишем правила для Publish Package.  
  
Пусть эта задача выполняется при пуше в ветку по-умолчанию и в релизных тегах формата \[v\]MAJOR.MINOR.PATCH. Также сделаем так, чтобы тег собранного образа был равен сочетанию имени ветки и хеша коммита при запуске из ветки или имени тега:

```
Publish Package:
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      variables:
        IMAGE_TAG: ${CI_COMMIT_BRANCH}_${CI_COMMIT_SHORT_SHA}
    - if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
      variables:
        IMAGE_TAG: $CI_COMMIT_TAG
```

Вынесем тег загружаемого образа в переменную:

```
Publish Package:
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  variables:
    HARBOR_HOST: harbor.devops-teta.ru
    HARBOR_PROJECT: demo
    HARBOR_USER: robot_demo+gitlab
    HARBOR_PASSWORD: $__HARBOR_PASSWORD
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME:$IMAGE_TAG"
      --cache-repo "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME/cache"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      variables:
        IMAGE_TAG: ${CI_COMMIT_BRANCH}_${CI_COMMIT_SHORT_SHA}
    - if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
      variables:
        IMAGE_TAG: $CI_COMMIT_TAG
```

Осталось обеспечить, чтобы зависимости задач Lint и Publish Package выполнялись. Напишем для задач Update Cache и Build Package правила, чтобы они запускались в ветке по-умолчанию, тегах и запросах на слияние:

```
Update Cache:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_COMMIT_TAG
 
Build Package:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_COMMIT_TAG
```

Приведем пайплайн целиком, снова убрав повторяющиеся секции при помощи YAML-якорей:

```
stages:
  - build
  - publish
default:
  before_script:
    - set -eu
variables:
  NODEJS_IMAGE: registry.devops-teta.ru/materials/ci/images/nodejs:18.18.2-bookworm
  KANIKO_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1
  NEXT_TELEMETRY_DISABLED: "1"
  NPM_CONFIG_CACHE: $CI_PROJECT_DIR/.cache/npm
  ENABLE_LINT: "true"
 
Update Cache:
  stage: .pre
  needs: []
  image: &nodejs_image
    name: $NODEJS_IMAGE
    entrypoint: [""]
  cache:
    - &npm_packages
      key: npm-packages
      paths:
        - .cache
      unprotect: true
    - &npm_node_modules
      key:
        prefix: npm-node-modules
        files:
          - package-lock.json
      paths:
        - node_modules
      unprotect: true
  script:
    - &npm_clean_install
      if [ ! -e node_modules ] ; then npm clean-install ; fi
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      allow_failure: true
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      allow_failure: true
    - if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
      allow_failure: true
 
# @NoArtifactsToSource
Lint:
  stage: .pre
  needs:
    - job: Update Cache
      artifacts: false
  allow_failure: true
  image: *nodejs_image
  variables:
    ESLINT_CODE_QUALITY_REPORT: eslint.codequality.json
  cache:
    - <<: *npm_packages
      policy: pull
    - <<: *npm_node_modules
      policy: pull
  script:
    - *npm_clean_install
    - npm run lint -- --format gitlab
  artifacts:
    paths:
      - $ESLINT_CODE_QUALITY_REPORT
    reports:
      codequality: $ESLINT_CODE_QUALITY_REPORT
  rules:
    - if: $ENABLE_LINT != "true"
      when: never
    - &on_merge_request
      if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - &on_default_branch
      if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
 
# @NoArtifactsToSource
Build Package:
  stage: build
  needs:
    - job: Update Cache
      artifacts: false
  image: *nodejs_image
  cache:
    - <<: *npm_packages
      policy: pull
    - <<: *npm_node_modules
      policy: pull
    - key: npm-next-cache
      paths:
        - .next/cache
  script:
    - *npm_clean_install
    - npm run build
    - mv .next/standalone dist
    - mv public dist/public
    - mv .next/static dist/.next/static
  artifacts:
    expire_in: 1h
    paths:
      - dist
  rules:
    - *on_merge_request
    - *on_default_branch
    - &on_release_tag
      if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
 
Publish Package:
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  variables:
    HARBOR_HOST: harbor.devops-teta.ru
    HARBOR_PROJECT: demo
    HARBOR_USER: robot_demo+gitlab
    HARBOR_PASSWORD: $__HARBOR_PASSWORD
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME:$IMAGE_TAG"
      --cache-repo "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME/cache"
  rules:
    - <<: *on_default_branch
      variables:
        IMAGE_TAG: ${CI_COMMIT_BRANCH}_${CI_COMMIT_SHORT_SHA}
    - <<: *on_release_tag
      variables:
        IMAGE_TAG: $CI_COMMIT_TAG
```

Обратим внимание, что мы перенесли allow\_failure в каждое правило. Это один из примеров, когда реализация gitlab-ci-local отличается от реального GitLab, т.к. GitLab пробрасывает allow\_failure из задачи во все правила, а gitlab-ci-local — нет.

Воспользуемся gitlab-ci-local, чтобы протестировать правила. Для этого используются две команды. Первая, --list-all, выводит все существующие задачи и их зависимости:

```
$ gitlab-ci-local --list-all
name             description  stage    when   allow_failure  needs
Update Cache                  .pre     never  false          []
Lint                          .pre     never  false          [Update Cache]
Build Package                 build    never  false          [Update Cache]
Publish Package               publish  never  false          [Build Package]
```

Заметим, что с текущими переменными не будет запущена ни одна задача, т.к. gitlab-ci-local не задает ни одной предопределенной переменной.  
Вторая команда, --list выводит задачи, запускаемые при выполнении текущих правил:

```
$ gitlab-ci-local --list
name             description  stage    when   allow_failure  needs
```

Мы можем задать переменные, создав файл .gitlab-ci-local-variables.yml в корне проекта. Например, зададим переменные, будто пайплайн запущен в ветке по-умолчанию (мы не будем указывать все возможные переменные для простоты):

```
CI: "true"
CI_COMMIT_BRANCH: "develop"
CI_DEFAULT_BRANCH: "develop"
CI_PIPELINE_SOURCE: "push"
```

Для запуска kaniko с помощью gitlab-ci-local, требуются дополнительные переменные, указанные в скрипте запуска kaniko.  
Без дополнительных переменных запуск kaniko будет завершаться с ошибкой.

Снова просмотрим список задач:

```
$ gitlab-ci-local --list
name             description  stage    when        allow_failure  needs
Update Cache                  .pre     on_success  true           []
Lint                          .pre     on_success  false          [Update Cache]
Build Package                 build    on_success  false          [Update Cache]
Publish Package               publish  on_success  false          [Build Package]
```

Если вы используете gitlab-ci-local в своих проектах, добавьте в .gitignore все файлы по маске .gitlab-ci-local\*

Include

include в GitLab CI полезен по нескольким причинам:  
  
1\. Уменьшение дублирования кода: include позволяет избежать дублирования кода в файлах конфигурации CI, таким образом упрощая обслуживание и рефакторинг пайплайнов.  
  
2\. Модульность конфигурации: Путем включения других файлов конфигурации с помощью include, вы можете разделить конфигурацию на модули или шаблоны, что делает ваш код более организованным и масштабируемым.  
  
3\. Переиспользование кода: С помощью include вы можете использовать общие шаблоны или стандартные настройки в различных пайплайнах, что сокращает повторное использование кода и упрощает обновление конфигурации.  
  
4\. Управление внешними URL и репозиториями: Вы можете загружать конфигурацию из удаленных URL или внешних репозиториев с использованием include, что позволяет вам подключать общие шаблоны или библиотеки с правильными настройками CI.  
  
5\. Улучшение читаемости и поддержки: include делает ваш файл конфигурации более читаемым, поскольку разделяет его на более мелкие и логические части, что упрощает обнаружение ошибок и модификацию конфигурации.  
  
В целом, include в GitLab CI обеспечивает гибкость и удобство при организации и написании конфигурации CI/CD, что позволяет эффективно управлять и настраивать ваши пайплайны с минимальными усилиями.

pipelines/nextjs\_standalone\_docker.yml

Вынесем написанный выше пайплайн в отдельный репозиторий.  
Cоздайте в своей подгруппе репозиторий templates, инициализируйте его [README.md](http://readme.md/) файлом, склонируйте на рабочую ВМ и откройте этот репозиторий в редакторе. Теперь скопируйте пайплайн из counter-frontend в файл pipelines/nextjs\_standalone\_docker.yml и загрузите изменения в GitLab.  
Приведем содержимое пайплайна counter-frontend:

```
stages:
  - build
  - publish
default:
  before_script:
    - set -eu
variables:
  NODEJS_IMAGE: registry.devops-teta.ru/materials/ci/images/nodejs:18.18.2-bookworm
  KANIKO_IMAGE: gcr.io/kaniko-project/executor:v1.9.1-debug
  NEXT_TELEMETRY_DISABLED: "1"
  NPM_CONFIG_CACHE: $CI_PROJECT_DIR/.cache/npm
  ENABLE_LINT: "true"
 
Update Cache:
  stage: .pre
  needs: []
  image: &nodejs_image
    name: $NODEJS_IMAGE
    entrypoint: [""]
  cache:
    - &npm_packages
      key: npm-packages
      paths:
        - .cache
      unprotect: true
    - &npm_node_modules
      key:
        prefix: npm-node-modules
        files:
          - package-lock.json
      paths:
        - node_modules
      unprotect: true
  script:
    - &npm_clean_install
      if [ ! -e node_modules ] ; then npm clean-install ; fi
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      allow_failure: true
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      allow_failure: true
    - if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
      allow_failure: true
 
# @NoArtifactsToSource
Lint:
  stage: .pre
  needs:
    - job: Update Cache
      artifacts: false
  allow_failure: true
  image: *nodejs_image
  variables:
    ESLINT_CODE_QUALITY_REPORT: eslint.codequality.json
  cache:
    - <<: *npm_packages
      policy: pull
    - <<: *npm_node_modules
      policy: pull
  script:
    - *npm_clean_install
    - npm run lint -- --format gitlab
  artifacts:
    paths:
      - $ESLINT_CODE_QUALITY_REPORT
    reports:
      codequality: $ESLINT_CODE_QUALITY_REPORT
  rules:
    - if: $ENABLE_LINT != "true"
      when: never
    - &on_merge_request
      if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - &on_default_branch
      if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
 
# @NoArtifactsToSource
Build Package:
  stage: build
  needs:
    - job: Update Cache
      artifacts: false
  image: *nodejs_image
  cache:
    - <<: *npm_packages
      policy: pull
    - <<: *npm_node_modules
      policy: pull
    - key: npm-next-cache
      paths:
        - .next/cache
  script:
    - *npm_clean_install
    - npm run build
    - mv .next/standalone dist
    - mv public dist/public
    - mv .next/static dist/.next/static
  artifacts:
    expire_in: 1h
    paths:
      - dist
  rules:
    - *on_merge_request
    - *on_default_branch
    - &on_release_tag
      if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
 
Publish Package:
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  variables:
    HARBOR_HOST: harbor.devops-teta.ru
    HARBOR_PROJECT: demo
    HARBOR_USER: robot_demo+gitlab
    HARBOR_PASSWORD: $__HARBOR_PASSWORD
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME:$IMAGE_TAG"
      --cache-repo "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME/cache"
  rules:
    - <<: *on_default_branch
      variables:
        IMAGE_TAG: ${CI_COMMIT_BRANCH}_${CI_COMMIT_SHORT_SHA}
    - <<: *on_release_tag
      variables:
        IMAGE_TAG: $CI_COMMIT_TAG
```

Теперь мы можем подключить готовый пайплайн в репозиторий нашего фронтэнда:

```
include:
  - project: <PATH_TO_YOUR_GROUP>/templates
    file:
      - pipelines/nextjs_standalone_docker.yml
```

Проверим, что пайплайн подключился успешно при помощи gitlab-ci-local:

```
$ gitlab-ci-local --list-all
name             description  stage    when   allow_failure  needs
Update Cache                  .pre     never  false          []
Lint                          .pre     never  false          [Update Cache]
Build Package                 build    never  false          [Update Cache]
Publish Package               publish  never  false          [Build Package]
```

Вывод gitlab-ci-local --list-all будет идентичен таковому до внесения изменений.  
Теперь вспомним задачу Publish Package: ее скрипт и образ будет идентичен для всех проектов, которые публикуют Docker-образа на Harbor, но общий CI процесс может отличаться, из-за чего в различных проектах у такой задачи будут разные правила, зависимости и т. д.  
  
Мы можем сохранить заготовку задачи, поместив ее в так называемый _cкрытый символ_ — это ключ в корне GitLab CI файла, начинающийся с точки (.). Такие ключи не добавляются в пайплайн как задачи и могут иметь произвольное содержимое.

jobs/kaniko.yml

Создадим заготовку задачи Publish Package в файле jobs/kaniko.yml нашего репозитория templates:

```
variables:
  KANIKO_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1
  HARBOR_HOST: harbor.devops-teta.ru
  HARBOR_PROJECT: demo
  HARBOR_USER: robot_demo+gitlab
  HARBOR_PASSWORD: $__HARBOR_PASSWORD
  IMAGE_TAG: ""
 
.job__kaniko_publish_image:
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME:$IMAGE_TAG"
      --cache-repo "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME/cache"
```

Обратите внимание, что мы добавили проверку на наличие переменной IMAGE\_TAG в начало скрипта: в прошлой версии мы гарантировали, что эта переменная всегда задана в правилах, здесь же правил нет и следует убедиться что переменная существует, чтобы избежать неочевидных ошибок в середине сборки.  
Теперь подключим этот файл к pipelines/nextjs\_standalone\_docker.yml:

```
include:
  - local: jobs/kaniko.yml
 
# ...Остальной пайплайн
 
Publish Package:
  extends:
    - .job__kaniko_publish_image
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  rules:
    - <<: *on_default_branch
      variables:
        IMAGE_TAG: ${CI_COMMIT_BRANCH}_${CI_COMMIT_SHORT_SHA}
    - <<: *on_release_tag
      variables:
        IMAGE_TAG: $CI_COMMIT_TAG
```

Опция local директивы include включает файл в текущем репозитории, путь к файлу указывается от корня репозитория. Также вместо явного указания local можно просто написать имя файла:

```
include:
  - jobs/kaniko.yml
```

extends

Директива [extends](https://docs.gitlab.com/ee/ci/yaml/#extends) позволяет переиспользовать части задач, она принимает на вход список задач, как обычных, так и скрытых. Таким образом мы, например, можем отделить место задачи в конкретном пайплайне от совершаемых ей действий и создать переиспользуемую задачу.  
Мы можем использовать extends рекурсивно: создадим скрытые задачи с часто встречающимися стратегиями клонирования в файле jobs/git\_strategy.yml:

```
.job__shallow_clone:
  variables:
    GIT_STRATEGY: fetch
    GIT_DEPTH: 20
    GIT_CLONE_PATH: $CI_BUILDS_DIR/$CI_PROJECT_PATH_SLUG
 
.job__full_clone:
  variables:
    GIT_STRATEGY: clone
    GIT_DEPTH: 0
    GIT_CLONE_PATH: $CI_BUILDS_DIR/$CI_PROJECT_PATH_SLUG
 
.job__no_clone:
  variables:
    GIT_STRATEGY: none
```

и подключим .job\_\_shallow\_clone к заготовке .job\_\_kaniko\_publish\_image в jobs/kaniko.yml:

```
include:
  - local: jobs/git_strategy.yml
 
variables:
  KANIKO_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1
  HARBOR_HOST: harbor.devops-teta.ru
  HARBOR_PROJECT: demo
  HARBOR_USER: robot_demo+gitlab
  HARBOR_PASSWORD: $__HARBOR_PASSWORD
  IMAGE_TAG: ""
 
.job__kaniko_publish_image:
  extends:
    - .job__shallow_clone
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME:$IMAGE_TAG"
      --cache-repo "$HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME/cache"
```

GIT\_STRATEGY

Вы логично зададитесь вопросом: «Что настраивают переменные, которые мы только что написали?» Эти переменные определяют поведение GitLab раннера при клонировании репозитория в начале задачи:  
GIT\_STRATEGY — метод клонирования:  
fetch — сохраняет в раннере копию репозитория, удаляя любые изменения при помощи git clean; самый быстрый метод и метод по-умолчанию;  
clone — заново клонирует репозиторий в каждой задаче, самый медленный метод;  
none — не клонирует репозиторий;  
GIT\_DEPTH — глубина клонирования: сколько коммитов в текущей ветке склонировать в задачу;  
GIT\_CLONE\_PATH — задает фиксированный путь к клонируемому проекту, следует использовать когда сборочные системы или скрипты полагаются на абсолютные пути.

Обратите внимание, что при клонировании GitLab использует имя ветки (или тега) откуда запускается пайплайн, а не идентификатор конкретного коммита. Поэтому, если вы укажете маленькое значение для GIT\_DEPTH и попытаетесь перезапустить задачу в старом пайплайне, то GitLab не сможет выбрать коммит этой задачи после клонирования.

!reference

Также большинство пайплайнов используют одни и те же правила, чтобы не наследовать список правил целиком при помощи extends можно ссылаться на конкретный символ при помощи тега !reference. Создадим файл с переиспользуемым набором правил: rules/main.yml.

!reference — это расширение GitLab CI поверх стандартного синтаксиса YAML. Оно не будет работать, например, в Ansible.

```
variables:
  ENABLE_LINT: "true"
  ENABLE_TESTS: "true"
 
.rule__enable_lint:
  if: $ENABLE_LINT != "true"
  when: never
 
.rule__enable_tests:
  if: $ENABLE_TESTS != "true"
  when: never
 
.rule__on_merge_requests:
  if: $CI_PIPELINE_SOURCE == "merge_request_event"
 
.rule__on_default_branch:
  if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  variables:
    IMAGE_TAG: ${CI_COMMIT_BRANCH}_${CI_COMMIT_SHORT_SHA}
.rule__on_release_tag:
  if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}/
  variables:
    IMAGE_TAG: $CI_COMMIT_TAG
.rule__on_release_candidate_tag:
  if: $CI_COMMIT_TAG =~ /v?[0-9]+(\.[0-9]+){2}(-rc\.[0-9]+)/
  variables:
    IMAGE_TAG: $CI_COMMIT_TAG
```

Включим наши правила в pipelines/nextjs\_standalone\_docker.yml:

```
include:
  - local: rules/main.yml
  - local: jobs/kaniko.yml
 
Lint:
  # ...
  rules:
    - !reference [.rule__enable_lint]
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
```

В качестве аргумента !reference принимает путь к узлу YAML, т. е. мы можем ссылаться не только на скрытые символы, но и на части обычных задач:

```
Update Cache:
  image:
    name: $NODEJS_IMAGE
    entrypoint: [""]
  # ...
 
Lint:
  image: !reference [Update Cache, image]
```

Вы можете воспринимать !reference как замену YAML-якорям, которая лучше интегрируется с механизмом включений GitLab CI.  
Также обратите внимание на порядок операций: подстановки extends и !referenceвыполняются после всех включений (include), а включения в свою очередь происходят по-очереди, в порядке написания. Таким образом при переопределении символа в одном из включаемых файлов подставлена будет последняя версия.

npm.yml

Продолжаем оптимизировать наш пайплайн.  
Создадим jobs/npm.yml. Вынесем отдельно задачи, связанные со сборкой npm. Напомним, что использовать якоря можно только в контексте одного файла yml. Оставленные в данном примере якоря будут доступны только в этом скрипте и не доступны на других уровнях.

```
variables:
  NODEJS_IMAGE: registry.devops-teta.ru/materials/ci/images/nodejs:18.18.2-bookworm
  
.script__npm_clean_install:
  if [ ! -e node_modules ] ; then npm clean-install ; fi
  
.npm_cache:
  cache:
  - &npm_packages
    key: npm-packages
    paths:
      - .cache
    unprotect: true
  - &npm_node_modules
    key:
      prefix: npm-node-modules
      files:
        - package-lock.json
    paths:
      - node_modules
 
 
.job__npm_build:
  image:
    name: $NODEJS_IMAGE
    entrypoint: [""]
  cache:
    - <<: *npm_packages
      policy: pull
    - <<: *npm_node_modules
      policy: pull
    - key: npm-next-cache
      paths:
        - .next/cache
  script:
    - !reference [.script__npm_clean_install]
    - npm run build
    - mv .next/standalone dist
    - mv public dist/public
    - mv .next/static dist/.next/static
```

В rules/main.yml добавим:

```
.rule__allow_failure:
  allow_failure: true
```

Исправим соответствующие задачи в nextjs\_standalone\_docker.yml:

```
include:
  - local: jobs/kaniko.yml
  - local: rules/main.yml
  - local: jobs/npm.yml
 
{...}
 
 
Update Cache:
  stage: .pre
  needs: []
  script:
    - !reference [.script__npm_clean_install]
  extends:
    - .job__npm_build
    - .npm_cache
    - .rule__allow_failure
  rules:
    - !reference [.rule__enable_lint]
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
    - !reference [.rule__on_release_tag]
 
Lint:
  extends:
    - .job__npm_build
    - .rule__allow_failure   
  stage: .pre
  needs:
    - job: Update Cache
      artifacts: false
  variables:
    ESLINT_CODE_QUALITY_REPORT: eslint.codequality.json
  script:
    - !reference [.script__npm_clean_install]
    - npm run lint -- --format gitlab
  artifacts:
    paths:
      - $ESLINT_CODE_QUALITY_REPORT
    reports:
      codequality: $ESLINT_CODE_QUALITY_REPORT
  rules:
    - !reference [.rule__enable_lint]
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
 
Build Package:
  extends:
    - .job__npm_build
  stage: build
  needs:
    - job: Update Cache
      artifacts: false
  artifacts:
    expire_in: 1h
    paths:
      - dist
  rules:
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
    - !reference [.rule__on_release_tag]
 
{...}
```

variables.yml

Самый популярный способ использования шаблонов — это вынос переменных в отдельный файлы. Мы так же займемся этой модернизацией.  
Создадим папку variables и в ней несколько файлов.

**variables/default.yml:**

```
default:
  before_script:
    - set -eu
```

**variables/harbor.yml:**

```
variables:
  HARBOR_HOST: harbor.devops-teta.ru
  HARBOR_PROJECT: demo
  HARBOR_USER: robot_demo+gitlab
  HARBOR_PASSWORD: $__HARBOR_PASSWORD
  HARBOR_IMAGE: $HARBOR_HOST/$HARBOR_PROJECT/$CI_PROJECT_NAME
```

**variables/stages.yml:**

```
stages:
  - build
  - publish
  - deploy
```

**variables/vars.yml:**

```
variables:
  NODEJS_IMAGE: registry.devops-teta.ru/materials/ci/images/nodejs:18.18.2-bookworm
  KANIKO_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1
  NEXT_TELEMETRY_DISABLED: "1"
  NPM_CONFIG_CACHE: $CI_PROJECT_DIR/.cache/npm
  ENABLE_LINT: "true"
  ENABLE_TESTS: "true"
```

**variables/main.yml:**

```
include:
  - variables/default.yml
  - variables/stages.yml
  - variables/vars.yml
  - variables/harbor.yml
```

Внесем изменения в скрипты. В основном все изменения связанны с удаление вынесенных переменных. Приведем пример итогового скрипта:

**pipelines/nextjs\_standalone\_docker.yml:**

```
include:
  - local: variables/main.yml
  - local: jobs/kaniko.yml
  - local: rules/main.yml
  - local: jobs/npm.yml
 
Update Cache:
  stage: .pre
  needs: []
  script:
    - !reference [.script__npm_clean_install]
  extends:
    - .job__npm_build
    - .npm_cache
    - .rule__allow_failure
  rules:
    - !reference [.rule__enable_lint]
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
 
Lint:
  extends:
    - .job__npm_build
    - .rule__allow_failure   
  stage: .pre
  needs:
    - job: Update Cache
      artifacts: false
  variables:
    ESLINT_CODE_QUALITY_REPORT: eslint.codequality.json
  script:
    - !reference [.script__npm_clean_install]
    - npm run lint -- --format gitlab
  artifacts:
    paths:
      - $ESLINT_CODE_QUALITY_REPORT
    reports:
      codequality: $ESLINT_CODE_QUALITY_REPORT
  rules:
    - !reference [.rule__enable_lint]
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
 
Build Package:
  extends:
    - .job__npm_build
  stage: build
  needs:
    - job: Update Cache
      artifacts: false
  artifacts:
    expire_in: 1h
    paths:
      - dist
  rules:
    - !reference [.rule__on_merge_requests]
    - !reference [.rule__on_default_branch]
    - !reference [.rule__on_release_tag]
 
Publish Package:
  extends:
  - .job__kaniko_publish_image
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  rules:
    - !reference [.rule__on_default_branch]
    - !reference [.rule__on_release_tag]
```

**jobs/kaniko.yml:**

```
include:
  - local: jobs/git_strategy.yml
 
variables:
  IMAGE_TAG: ""
 
.job__kaniko_publish_image:
  extends:
    - .job__shallow_clone
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_IMAGE:$IMAGE_TAG"
      --cache-repo "$HARBOR_IMAGE/cache"
```

Пример неправильной последовательности при использовании include

Например файл npm. yml, содержащий скелеты сборочных задач для пакетного менеджера npm:

```
variables:
  NODEJS_IMAGE: registry.devops-teta.ru/materials/ci/images/nodejs:18.18.2-bookworm
 
.script__npm_clean_install:
  - if [ ! -e node_modules ] ; then npm clean-install ; fi
 
.job__npm_build:
  image:
    name: $NODEJS_IMAGE
    entrypoint: [""]
  script:
    - !reference [.script__npm_clean_install]
    - npm run build
```

который подключается в основной пайплайн main. yml:

```
include:
  - npm.yml
 
Build Package:
  extends:
    - .job__npm_build
 
.script__npm_clean_install:
  - npm clean-install
```

В котором мы для отладки изменили скрипт .script\_\_npm\_clean\_install так, чтобы он перетирал node\_modules при каждом запуске, игнорируя кеш. Символ .script\_\_npm\_clean\_install в основном пайплайне заменит такой же из npm. yml (исходный пайплайн включается последним, следовательно имеет наивысший приоритет).  
Воспользуемся gitlab-ci-local, чтобы просмотреть объединенный пайплайн:

```
$ gitlab-ci-local --preview --file main.yml
---
stages:
  - .pre
  - build
  - test
  - deploy
  - .post
Build Package:
  image:
    name: $NODEJS_IMAGE
    entrypoint:
      - ''
  script:
    - npm clean-install
    - npm run build
```

gitlab-ci-local --preview вырезает скрытые символы и переменные, но показывает остальные параметры после разрешения всех включений. Как видим в задаче используется вторая версия скрипта .script\_\_npm\_clean\_install. Чтобы просмотреть полностью разрешенный пайплайн без вырезанных символов и атрибутов используйте View Merged YAML в редакторе пайплайнов GitLab CI.  
  
После всех изменений репозиторий templates будет выглядеть так:

```
$ tree
.
├── jobs
│   ├── docker_login.yml
│   ├── git_strategy.yml
│   ├── kaniko.yml
│   └── npm.yml
├── pipelines
│   └── nextjs_standalone_docker.yml
├── rules
│   └── main.yml
└── variables
    ├── default.yml
    ├── harbor.yml
    ├── main.yml
    ├── stages.yml
    └── vars.yml
```

Загрузите все свои изменения в GitLab CI, они понадобятся вам позднее.

Домашнее задание

Сделайте форк проекта [counter-backend](https://git.devops-teta.ru/materials/counter-backend) и доработайте следующий пайплайн:

```
stages:
  - build
  - test
  - publish
variables:
  POETRY_IMAGE: registry.devops-teta.ru/materials/ci/images/poetry:1.4.1-3.11.6-bookworm
  KANIKO_IMAGE: registry.devops-teta.ru/materials/ci/images/kaniko:1.9.1
  POETRY_CACHE_DIR: .cache/poetry
  PIP_CACHE_DIR: .cache/pip
  GIT_CLONE_PATH: $CI_BUILDS_DIR/$CI_PROJECT_PATH_SLUG
default:
  before_script:
    - set -eu
 
Update Cache:
  stage: .pre
  needs: []
  image: &poetry_image
    name: $POETRY_IMAGE
    entrypoint: [""]
  cache:
    - &poetry_packages
      key: poetry-packages
      paths:
        - .cache
      unprotect: true
    - &poetry_venv
      key:
        prefix: poetry-venv
        files:
          - poetry.lock
      paths:
        - .venv
      unprotect: true
  script:
    - &poetry_install poetry install --no-root --no-interaction
 
Build Package:
  stage: build
  needs:
    - job: Update Cache
      artifacts: false
  image:
    name: $POETRY_IMAGE
    entrypoint: [""]
  cache:
    - <<: *poetry_packages
      policy: pull
    - <<: *poetry_venv
      policy: pull
  script:
    - *poetry_install
    - mkdir -p dist
    - poetry export --without-hashes --format constraints.txt --output dist/constraints.txt
    - poetry run python -m pip wheel --isolated --requirement dist/constraints.txt --wheel-dir dist/vendor
    - poetry build --format wheel
  artifacts:
    paths:
      - dist
 
Publish Package:
  stage: publish
  needs:
    - job: Build Package
      artifacts: true
  interruptible: false
  image:
    name: $KANIKO_IMAGE
    entrypoint: [""]
  script:
    - b64_auth=$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\n')
    - >-
      printf '{"auths": {"%s": {"auth": "%s"}}}' "$HARBOR_HOST" "$b64_auth"
      >/kaniko/.docker/config.json
    - >-
      /kaniko/executor
      --cache
      --use-new-run
      --skip-unused-stages
      --context "$CI_PROJECT_DIR"
      --dockerfile "$CI_PROJECT_DIR/Dockerfile"
      --destination "$HARBOR_IMAGE:$IMAGE_TAG"
      --cache-repo "$HARBOR_IMAGE/cache"
```

Во-первых_,_ напишите на основе этого пайплайна шаблон, который необходимо подключить к counter-backend.  
Во-вторых, добавьте задачу Run Tests, запускающую unit-тесты при помощи следующего скрипта:

```
$ poetry install --no-root --no-interaction
$ poetry run pytest --junitxml python.junit.xml
```

Задача должна экспортировать отчет в формате [junit](https://docs.gitlab.com/ee/ci/yaml/artifacts_reports.html#artifactsreportsjunit) при любом завершении задачи (успешном или с ошибкой). Также исправьте зависимости задач так, чтобы публикация Docker-образа не происходила при ошибке в тестах.  
  
_В-третьих_, модифицируйте правила задач так, чтобы:  
 

*   в запросах на слияние запускались только задачи, проверяющие корректность кода;
*   в тегах запускались только задачи, собирающие Docker-образ;
*   в ветке по умолчанию запускались все задачи.

Для проверки предоставьте:  
 

*   ссылки на отработанные пайплайны в counter-backend;
*   ссылку на точку входа в шаблон для backend;
*   diff — изменений в шаблонах при подключении шаблона для counter-backend.