Контейнеризация

Люди всегда опираются на опыт и знания предшественников.  
Разработчики не исключение: программы переиспользуют написанный код, либо копируя его в новые программы, либо подключая как отдельные пакеты.  
  
Первый подход обычно называют статическим связыванием (копирование исходного кода в новую программу, статическая линковка для компилируемых программ, вендоринг и т. д.), второй — динамическим связыванием (подключение раздельных библиотек, поиск кода в глобальном реестре и т. д.).  
  
Очевидно, статическое связывание проще, т.к. мы приносим все зависимости с собой: мы можем гарантировать совместимость версий используемого кода, не нужно волноваться об источниках получения зависимостей. Но минусы такого подхода также очевидны — каждая программа копирует все нужные ей зависимости, раздувая размер, усложняется аудит зависимостей.  
Также, на Linux, самая популярная реализация стандартной библиотеки C (glibc) по сути не поддерживает статическую линковку.  
  
Поэтому во всех дистрибутивах Linux широко используется динамическая линковка, причем в некоторых вообще запрещена публикация статически собранных пакетов в системные репозитории. Это привело к тому, что большинство языков программирования, пакетных менеджеров не поддерживают статическую сборку.  
  
Контейнеры — радикальное решение этой проблемы. Программа и все ее зависимости упаковываются в будто бы образ цельной операционной системы и запускается изолированно, опять же, будто единственный процесс этой операционной системы.  
  
При этом контейнеры используют для изоляции встроенные механизмы Linux и не эмулируют отдельное ядро операционной системы, в отличии от систем виртуализации. Поэтому при помощи контейнеров нельзя запускать программы, написанные для Windows, MacOS или скомпилированных для архитектуры процессора, отличной от хост-архитектуры. Но контейнеры менее требовательны к ресурсам, что позволяет запускать большее их число.  
  
Далее мы будем рассматривать Docker и его подход к контейнерам, где один контейнер — это программа с ее зависимостями, а взаимодействие нескольких программ реализуется не при помощи упаковки нескольких программ в один контейнер и оркестрации внутри, а запуска множества контейнеров и оркестрации при помощи инструментов межпроцессного взаимодействия ОС: файловой системы, пайп, сокетов и т. д.  
  
Такой подход «тонких» контейнеров поощряет отделение состояния программы от кода: контейнер это лишь сама программа, состояние должно монтироваться извне при помощи сети, файловой системы хоста и т. п.  
  
Такой подход доминирует в индустрии, но он не единственный: поверх тех же механизмов Linux работают LXC (Linux Containers) и systemd-nspawn — менее популярные системы контейнеризации, реализующие механизм «толстых» контейнеров, когда, по аналогии с виртуальными машинами, все взаимодействия строятся внутри контейнера.

Образы

Программы, упакованные для использования в качестве контейнеров, называют образами (images)_._ По-сути они состоят из слепка файловой системы и конфигурации, указывающей как запустить стартовый процесс. Эти образа распространяются при помощи контейнерных реестров (container registry)_._ Доступно множество публичных реестров от различных вендоров, также существуют программы, позволяющие запустить приватный реестр. Все эти реестры реализуют одинаковый интерфейс загрузки/публикации/поиска образов и поэтому взаимозаменяемы.

Open Container Initiative — OCI

При работе с контейнерами вам встретятся термины «OCI совместимые образы», «OCI реестры», «OCI артефакты», «OCI среда выполнения». Это не что-то совершенно новое, а открытый стандарт для Docker контейнеров. OCI сущности выполняют ту же функцию, только основаны на открытом стандарте, а не на конкретной реализации Docker. Docker способен запускать OCI образы и Docker образы могут быть однозначно конвертированы в OCI образы.

Запуск первого контейнера

Мы запустили службу Docker на первой практике, напомним команду для запуска:

```
$ systemctl enable --now docker.service
```

Контейнеры запускаются командой docker run, например запустим nginx:

```
$ docker run nginx
Unable to find image 'nginx:latest' locally
latest: Pulling from library/nginx
Digest: sha256:32da30332506740a2f7c34d5dc70467b7f14ec67d912703568daff790ab3f755
Status: Downloaded newer image for nginx:latest
/docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to perform configuration
...
```

Эта команда запустит образ nginx и подключится к его выводу. Обратите внимание, что имя образа nginx было конвертировано в nginx: latest. latest -- тэг по умолчанию, он подставляется автоматически если не указать тег в имени образа. Нажмите CTRL+C, чтобы закрыть контейнер.  
  
Другие опции docker run можно просмотреть в man docker-run.  
  
docker run автоматически скачивает образ, если такой образ не сохранен локально.  
Команда docker pull загружает образ явно. Например загрузим nginx:1.20 :

```
$ docker pull nginx:1.20
1.20: Pulling from library/nginx
214ca5fb9032: Pull complete 
50836501937f: Pull complete 
d838e0361e8e: Pull complete 
fcc7a415e354: Pull complete 
dc73b4533047: Pull complete 
e8750203e985: Pull complete 
Digest: sha256:38f8c1d9613f3f42e7969c3b1dd5c3277e635d4576713e6453c6193e66270a6d
Status: Downloaded newer image for nginx:1.20
docker.io/library/nginx:1.20
```

По умолчанию docker run не перекачивает образ, если образ с таким тегом уже загружен. Вы можете использовать docker pull, чтобы принудительно обновить образ перед запуском контейнера.  
  
Чаще всего Docker используют для запуска фоновых служб, для этого воспользуемся опцией -d (-- detach) docker run :

```
$ docker run \
  --name test \
  --publish 127.0.0.1:8080:80/tcp \
  --detach nginx:1.20
70ab136de007179f27abf2b1b69bf50d3b0646758c1ff2d5908a9cef552b9509
```

Мы запустили контейнер в фоне, явно указав его имя опцией --name и опубликовав порт при помощи --publish (-p). Опция --publish позволяет пробросить порт из виртуальной сети контейнера в сеть хоста. Эта опция принимает как аргумент строку формата:

```
[HOST_ADDRESS:]<HOST_PORT>:<CONTAINER_PORT>[/PROTOCOL]
```

Здесь:  
HOST\_INTERFACE (опционально, по умолчанию 0.0.0.0) — IP адрес, к которому привязать порт в сети хоста. Укажите 127.0.0.1, чтобы порт был доступен только локально или 0.0.0.0, чтобы порт слушался на всех адресах, привязанных к хосту;  
HOST\_PORT (обязательно) — слушаемый порт в сети хоста;  
CONTAINER\_PORT (обязательно) — слушаемый порт в сети контейнера;  
PROTOCOL (опционально, по умолчанию tcp) — протокол слушаемого порта, вы можете указатьtcp либо udp.  
  
Воспользуемся командой docker ps, чтобы посмотреть запущенные контейнеры:

```
$ docker ps
CONTAINER ID   IMAGE     COMMAND                  CREATED              STATUS              PORTS     NAMES
70ab136de007   nginx     "/docker-entrypoint.…"   About a minute ago   Up About a minute   80/tcp    test
```

По умолчанию docker ps выводит список запущенных контейнеров в человекочитаемом формате.  
Используйте man docker-ps, чтобы просмотреть другие опции.  
Обратите внимание, что имя контейнера сгенерировано случайно. Чтобы задать имя явно используйте docker run --name NAME .  
  
Просмотрим логи контейнера (у вас будет другой ID контейнера):

```
$ docker logs --follow 70ab136de007
/docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to perform configuration
/docker-entrypoint.sh: Looking for shell scripts in /docker-entrypoint.d/
/docker-entrypoint.sh: Launching /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
10-listen-on-ipv6-by-default.sh: info: Getting the checksum of /etc/nginx/conf.d/default.conf
10-listen-on-ipv6-by-default.sh: info: Enabled listen on IPv6 in /etc/nginx/conf.d/default.conf
...
```

Откроем вторую консоль и сделаем запрос к запущенному контейнеру при помощи curl:

```
$ curl http://localhost:8080
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
```

Обратите внимание, что в логе появилась новая запись.  
  
Чтобы просмотреть детали по запущенному контейнеру воспользуемся docker top и docker stats:

```
$ docker top 70ab136de007
UID                 PID                 PPID                C                   STIME               TTY                 TIME                CMD
root                19021               19002               0                   00:00               ?                   00:00:00            nginx: master process nginx -g daemon off;
systemd+            19077               19021               0                   00:00               ?                   00:00:00            nginx: worker process
systemd+            19078               19021               0                   00:00               ?                   00:00:00            nginx: worker process
```

docker top показывает информацию о процессах, запущенных внутри контейнера. После идентификатора или имени контейнера она принимает аргументы команды ps, детали смотрите в man ps. Например, чтобы просмотреть текущую нагрузку в разбивке по процессам:

```
$ docker top 70ab136de007 -o pid,ppid,uid,gid,%cpu,%mem,cmd
PID                 PPID                UID                 GID                 %CPU                %MEM                CMD
19021               19002               0                   0                   0.0                 0.3                 nginx: master process nginx -g daemon off;
19077               19021               101                 101                 0.0                 0.1                 nginx: worker process
19078               19021               101                 101                 0.0                 0.1                 nginx: worker process
```

docker stats показывает ресурсы потребляемые контейнером в реальном времени:

```
$ docker stats 70ab136de007
CONTAINER ID   NAME      CPU %     MEM USAGE / LIMIT    MEM %     NET I/O       BLOCK I/O         PIDS
70ab136de007   test      0.00%     7.215MiB / 1.99GiB   0.35%     1.67kB / 0B   12.4MB / 12.3kB   3
```

Чтобы запустить новый процесс в уже существующем контейнере существует команда docker exec. Например, просмотрим конфигурацию nginx:

```
$ docker exec 70ab136de007 cat /etc/nginx/nginx.conf
```

Или терминал:

```
$ docker exec --interactive --tty 70ab136de007 bash
```

Опция --interactive (-i) насильно подключает stdin к сессии docker exec, а --tty (-t)создает псевдо-консоль для процесса.  
Внутри контейнера информацию о процессах, как она выглядит изнутри контейнера. Воспользуемся виртуальной файловой системой /proc:

```
$ printf 'PID\tPPID\tUID\tGID\tCMD\n' ; \
  find /proc -maxdepth 1 \
      -regex '/proc/[0-9]+' \
    | while read -r p
      do [ -r "$p/cmdline" ] || continue
         printf '%s\t%s\t%s\t%s\t%s\n' \
                "$(echo $p | cut -d/ -f3)" \
                "$(grep -F PPid <"$p/status" | cut -f2)" \
                "$(grep -F Uid  <"$p/status" | cut -f2)" \
                "$(grep -F Gid  <"$p/status" | cut -f2)" \
                "$(tr '\0' ' ' <"$p/cmdline")"
      done
PID PPID    UID GID CMD
1   0       0   0   nginx: master process nginx -g daemon off;
30  1       101 101 nginx: worker process
31  1       101 101 nginx: worker process
...
```

Обратите внимание на идентификаторы процессов и пользователей. Первые изолированы в отдельное пространство имен Linux, вторые — нет.  
  
Остановим запущенный контейнер:

```
$ docker stop 70ab136de007
70ab136de007
```

Запустим docker ps еще раз:

```
$ docker ps
CONTAINER ID IMAGE COMMAND CREATED STATUS PORTS NAMES
```

По умолчанию docker ps выводит только запущенные контейнеры, добавим -a (--all) чтобы увидеть только что остановленный контейнер:

```
$ docker ps --all
CONTAINER ID   IMAGE     COMMAND                  CREATED         STATUS                     PORTS     NAMES
70ab136de007   nginx     "/docker-entrypoint.…"   4 minutes ago   Exited (0) 3 minutes ago             test
```

Запустим контейнер снова командой docker start:

```
$ docker start 70ab136de007
70ab136de007
```

Наконец удалим контейнер:

```
$ docker rm 70ab136de007
Error response from daemon: You cannot remove a running container 
70ab136de007179f27abf2b1b69bf50d3b0646758c1ff2d5908a9cef552b9509. Stop the container 
before attempting removal or force remove
```

Мы должны остановить контейнер, чтобы удалить его:

```
$ docker stop 70ab136de007 && docker rm 70ab136de007
70ab136de007
70ab136de007
```

Или же воспользуйтесь опцией -f (--force) команды docker rm :

```
$ docker rm --force 70ab136de007
70ab136de007
```

Мы, очевидно, рассмотрели далеко не все команды. Остальные можно просмотреть либо в справке (docker --help, man docker) или [онлайн-документации](https://docs.docker.com/engine/reference/commandline/docker/). Обратите внимание на следующие команды:  
docker create — создать контейнер без запуска;  
docker diff — просмотреть изменения файловой системы контейнера, по сравнению с изначальным образом;  
docker export — экспортировать файловую систему контейнера в архив;  
docker save — сохранить образ в архив;  
docker restart — перезапустить контейнер.

Сборка образов

Мы запускали контейнер из существующего образа. Довольно часто мы будем упаковывать свои приложения в контейнеры, рассмотрим как собирать Docker образы.

Dockerfile

Рассмотрим стандартный способ сборки Docker образов: Dockerfile. Этот файл состоит из последовательности команд, которые позволяют выполнять команды в окружении сборки, выставлять параметры конфигурации и т. д.  
  
Рассмотрим основные команды на примере, склонируйте проект [counter-frontend](https://git.devops-teta.ru/materials/counter-frontend)на рабочую ВМ и перейдите в папку с проектом:

```
git clone git@git.devops-teta.ru:materials/counter-frontend.git && cd counter-frontend
```

Если вы используете VSCode на ВМ, то откройте VSCode в текущей папке так: code.  
  
Этот проект — простой фронтэнд на NextJS, реализующий счетчик. Напишем простой Dockerfile для сборки и запуска этого проекта.  
  
Создайте в корневой папке проекта файл Dockerfile со следующим содержимым:

**Dockerfile**

```
FROM node:18-slim
```

Директива FROM указывает базовый образ, т. е. образ поверх которого мы строим образ своего приложения.  
  
Теперь нам нужно скопировать исходный код приложения внутрь нового образа:

**Dockerfile**

```
FROM node:18-slim
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
```

Директива WORKDIR задает рабочую директорию, воспринимайте ее как аналог cd, который используется остальными директивами, работающими с файловой системой. Если такой папки не существует, то она будет создана.  
  
COPY копирует файлы из текущего контекста сборки внутрь образа. Эта команда принимает на вход список путей, последний путь — это целевой путь в образе, остальные — исходные пути в контексте сборки. Если путь заканчивается на /, то он считается директорией. Можно копировать несколько файлов в папку одной директивой, для копирования папок нужно написать отдельную директиву.  
  
Контекст сборки — это папка хоста, из которой копируются файлы директивами ADD и COPY. По умолчанию это папка, из которой была запущена команда docker build, но ее можно переопределить. При старте сборки Docker копирует все файлы из контекста во временную директорию, чтобы зафиксировать состояние на начало сборки.  
  
Если контекст занимает много места (например, если здесь мы скачаем все зависимости в папку node\_modules), то сборка будет долго запускаться и иногда завершаться с ошибкой, если в /var/lib/docker недостаточно места.  
  
Чтобы избежать этой проблемы используется файл. dockerignore — это файл, где на каждой строке указывается подстановочный шаблон (синтаксис очень похож на таковые из Shell) и если файл из контекста подходит под шаблон, то он не копируется в слепок контекста в начале сборки.  
  
Обратите внимание, что при попытке скопировать проигнорированный файл Docker выдаст такую ошибку, как будто этого файла не существует. Используйте. dockerignore осторожно и проверяйте его содержимое при ошибках копирования.  
  
Создадим .dockerignore:

**.dockerignore**

```
# NodeJS modules
/node_modules
```

\# — обозначает комментарий. Мы скопировали исходные файлы и сборочную конфигурацию внутрь образа, теперь соберем проект:

**Dockerfile**

```
FROM node:18-slim
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
ARG NODE_ENV=production
RUN npx next build
```

RUN запускает Shell команду в текущем состоянии образа. Она запускается как будто в контейнере, собранном при помощи предыдущих директив. Также для нее используется отдельный процесс Shell, т. е. изменения состояния оболочки не сохранятся. Изменения cd и setне применятся к последующим директивам RUN .  
  
ARG задает параметр сборки — переменную окружения доступную во время сборки контейнера. Эти переменные доступны в командах, запускаемых директивами RUN и при подстановке переменных. Чтобы задать глобальные параметры оболочки, в которой запускаются директивы RUN используется SHELL:

**Dockerfile**

```
FROM node:18-slim
SHELL [ "/bin/sh", "-eu", "-c" ]
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
RUN npm install
RUN npx next build
```

Аргументы SHELL — список в формате JSON, которым задается команда, запускающая оболочку для RUN, т. е. полная команда RUN будет выглядеть так:

```
/bin/sh -eu -c 'npx next build'
```

Теперь установим собранный проект в /app:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN npm install
RUN npx next build
 
RUN cp --recursive .next/standalone /app
RUN cp --recursive public /app/public
RUN cp --recursive .next/static /app/.next/static
```

И укажем какую команду запускать при старте контейнера:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN npm install
RUN npx next build
 
RUN cp --recursive .next/standalone /app
RUN cp --recursive public /app/public
RUN cp --recursive .next/static /app/.next/static
 
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

ENTRYPOINT, аналогично SHELL принимает как аргумент JSON список, из которого формируется запускаемая команда. Аналогично вместо JSON списка вы можете передать как аргумент произвольную строку и она будет запущена командой /bin/sh -c.  
  
Почти всегда Shell форма используется по ошибке, когда вы ошибаетесь в JSON строке. Внимательно проверяйте запятые и кавычки, т.к. Docker не укажет вам на ошибку.  
  
Запускаемая нами команда по умолчанию слушает TCP порт 3000, мы можем указать на это директивой EXPOSE:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN npm install
RUN npx next build
 
RUN cp --recursive .next/standalone /app
RUN cp --recursive public /app/public
RUN cp --recursive .next/static /app/.next/static
 
EXPOSE 3000/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

EXPOSE указывает, что внутри контейнера запущен процесс, слушающий указанный порт. Она никак не влияет на поведение docker run.  
  
Наш сервер позволяет переопределить слушаемый порт переменной окружения PORT:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN npm install
RUN npx next build
 
RUN cp --recursive .next/standalone /app
RUN cp --recursive public /app/public
RUN cp --recursive .next/static /app/.next/static
 
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

ENV задает переменную окружения, такие переменные, аналогично параметрам сборки доступны при сборке контейнера, но также они выставляются при запуске контейнера. Обратите внимание, что в директивах можно использовать переменные окружения и параметры сборки. Список поддерживаемых директив см. в [](denied:3 https://docs.docker.com/engine/reference/builder/#environment-replacement) [документации](https://docs.docker.com/engine/reference/builder/#environment-replacement).  
  
Вы можете переопределить значение переменной окружения при запуске контейнера, но это не изменит результаты подстановок т.к. они выполняются при сборке и в образ сохраняется результат. Даже если вы зададите переменную окружения PORT при запуске контейнера порт, указанный в EXPOSE не изменится.  
  
Запустим сборку образа командой docker build :

```
$ docker build --tag image .
```

Мы указываем два обязательных параметра:  
\--tag (-t) — имя собранного образа;  
. — контекст сборки;

Строение образа

Docker образ состоит из последовательности слоев — архивов, содержащих слепок файловой системы будущего контейнера. При создании контейнера эти слепки последовательно распаковываются в пустую файловую систему и полученный набор файлов становится файловой системой нового контейнера.  
  
Слои идентифицируются своей контрольной суммой. Контрольные суммы вычисляются так, чтобы минимизировать вероятность их совпадения для различных архивов. Это позволяет независимо генерировать уникальные идентификаторы для слоев.  
  
Docker хранит слои отдельно, образы лишь указывают их идентификаторы и порядок. Также образ содержит остальную конфигурацию, такую как переменные окружения образа, точку входа и т. д. Вся эта конфигурация хранится в одном JSON файле. Такой подход к хранению позволяет эффективно реализовать концепцию базовых образов: директива FROM imageговорит, что в качестве первых слоев образа нужно использовать слои образа image.  
Формат образа довольно прост, несложно представить альтернативные инструменты сборки.  
  
Мы рассмотрим один из них в будущем, когда будем рассматривать проблему сборки образов внутри Docker контейнеров при написании пайплайнов Gitlab CI.  
  
Мы можем просмотреть строение образа командой docker image save. Эта команда используется для распространения образов без использования реестров.

```
$ docker pull nginx:1.20  # Сначала загружаем образ
$ docker image save --output nginx.tgz nginx:1.20
```

Распакуем образ в папку и перейдем в нее:

```
$ mkdir --parents nginx
$ tar --extract --verbose --directory nginx --file nginx.tgz
$ cd nginx
```

Просмотрим содержимое образа:

```
$ tree
.
├── 0584b370e957bf9d09e10f424859a02ab0fda255103f75b3f8c7d410a4e96ed5.json
├── 0f363816624a8a468120a586323f47356ff12b78aa366cd56838c776b6f8a1fe
│   ├── json
│   ├── layer.tar
│   └── VERSION
├── 113c0561792ebb622236711a2025c47610078086f300659530cb000f6d8919dc
│   ├── json
│   ├── layer.tar
│   └── VERSION
├── 429ee11cfd71d01b280e7f2b906d9ae9c41c950f2c1781698f2c42a00d2ec615
│   ├── json
│   ├── layer.tar
│   └── VERSION
├── 671a1d9053e403e9c149ce5f7360117b8ce8d77e441849d5396eb4843f198e78
│   ├── json
│   ├── layer.tar
│   └── VERSION
├── 8afcedb90abfd1ca2924ca223dd9e4d26ca3053537663a607be3ee2fc1eefec0
│   ├── json
│   ├── layer.tar
│   └── VERSION
├── 8dfd5b8b88d1474acf828115a543c879247d2ff710e55f45b2ec5453cb6571db
│   ├── json
│   ├── layer.tar
│   └── VERSION
├── manifest.json
└── repositories
2 directories, 18 files
```

Образ состоит из:  
Манифеста — JSON файла, содержащего ссылки на остальные части образа: конфигурацию и слои;  
Конфиг — JSON файл, содержащий метаданные образа: переменные окружения, точку входа, аргументы, историю сборки, платформу под которую собран образ и т. д.;  
Слоев — слепков файловой системы с их метаданными.  
  
Посмотрим манифест:

```
$ jq . manifest.json
[
 {
 "Config": 
"0584b370e957bf9d09e10f424859a02ab0fda255103f75b3f8c7d410a4e96ed5.json",
 "RepoTags": [
 "nginx:1.20"
 ],
 "Layers": [
 "429ee11cfd71d01b280e7f2b906d9ae9c41c950f2c1781698f2c42a00d2ec615/layer.tar",
 "0f363816624a8a468120a586323f47356ff12b78aa366cd56838c776b6f8a1fe/layer.tar",
 "8dfd5b8b88d1474acf828115a543c879247d2ff710e55f45b2ec5453cb6571db/layer.tar",
 "113c0561792ebb622236711a2025c47610078086f300659530cb000f6d8919dc/layer.tar",
 "671a1d9053e403e9c149ce5f7360117b8ce8d77e441849d5396eb4843f198e78/layer.tar",
 "8afcedb90abfd1ca2924ca223dd9e4d26ca3053537663a607be3ee2fc1eefec0/layer.tar"
 ]
 }
]
```

Заметим, что все объекты идентифицируются своими контрольными суммами, в т. ч. конфиг. Docker всегда использует алгоритм SHA-256. Манифест используется для параллельной загрузки образов:  
сначала скачивается манифест, затем из него извлекаются идентификаторы слоев и конфигурации для параллельной загрузки.  
  
Просмотрим конфигурацию:

```
$ jq . 0584b370e957bf9d09e10f424859a02ab0fda255103f75b3f8c7d410a4e96ed5.json
{
 "architecture": "amd64",
 "config": {
 "Hostname": "",
 "Domainname": "",
 "User": "",
 "AttachStdin": false,
 "AttachStdout": false,
 "AttachStderr": false,
 "ExposedPorts": {
 "80/tcp": {}
 },
 "Tty": false,
 "OpenStdin": false,
 "StdinOnce": false,
 "Env": [
 "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
 "NGINX_VERSION=1.20.2",
 "NJS_VERSION=0.7.3",
 "PKG_RELEASE=1~bullseye"
 ],
 "Cmd": [
 "nginx",
 "-g",
 "daemon off;"
 ],
 "Image": 
"sha256:568a65393e894cd19a0473a1716fdee1b96246c302b2446296c555744e8d919e",
 "Volumes": null,
 "WorkingDir": "",
 "Entrypoint": [
 "/docker-entrypoint.sh"
 ],
 "OnBuild": null,
 "Labels": {
 "maintainer": "NGINX Docker Maintainers <docker-maint@nginx.com>"
 },
 "StopSignal": "SIGQUIT"
 },
 "container": "758f963724ce27609407bcc02105d7a411d09b61e3d7af87b84ef884179ab8b5",
 "container_config": {
 "Hostname": "758f963724ce",
 "Domainname": "",
 "User": "",
 "AttachStdin": false,
 "AttachStdout": false,
 "AttachStderr": false,
 "ExposedPorts": {
 "80/tcp": {}
 },
 "Tty": false,
 "OpenStdin": false,
 "StdinOnce": false,
 "Env": [
 "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
 "NGINX_VERSION=1.20.2",
 "NJS_VERSION=0.7.3",
 "PKG_RELEASE=1~bullseye"
 ],
 "Cmd": [
 "/bin/sh",
 "-c",
 "#(nop) ",
 "CMD [\"nginx\" \"-g\" \"daemon off;\"]"
 ],
 "Image": 
"sha256:568a65393e894cd19a0473a1716fdee1b96246c302b2446296c555744e8d919e",
 "Volumes": null,
 "WorkingDir": "",
 "Entrypoint": [
 "/docker-entrypoint.sh"
 ],
 "OnBuild": null,
 "Labels": {
 "maintainer": "NGINX Docker Maintainers <docker-maint@nginx.com>"
 },
 "StopSignal": "SIGQUIT"
 },
 "created": "2022-05-17T22:37:17.011072851Z",
 "docker_version": "20.10.12",
 "history": [
 {
 "created": "2022-05-11T01:20:16.520708229Z",
 "created_by": "/bin/sh -c #(nop) ADD 
file:4a0bb88956083aa56032fdd9601d9b66c39b18c896ba35ea33594cd75621640a in / "
 },
 {
 "created": "2022-05-11T01:20:16.833449474Z",
 "created_by": "/bin/sh -c #(nop) CMD [\"bash\"]",
 "empty_layer": true
 },
 {
 "created": "2022-05-11T05:04:29.216415069Z",
 "created_by": "/bin/sh -c #(nop) LABEL maintainer=NGINX Docker Maintainers 
<docker-maint@nginx.com>",
 "empty_layer": true
 },
 {
 "created": "2022-05-11T05:05:20.5186653Z",
 "created_by": "/bin/sh -c #(nop) ENV NGINX_VERSION=1.20.2",
 "empty_layer": true
 },
 {
 "created": "2022-05-17T22:36:58.109357274Z",
 "created_by": "/bin/sh -c #(nop) ENV NJS_VERSION=0.7.3",
 "empty_layer": true
 },
 {
 "created": "2022-05-17T22:36:58.209807672Z",
 "created_by": "/bin/sh -c #(nop) ENV PKG_RELEASE=1~bullseye",
 "empty_layer": true
 },
 {
 "created": "2022-05-17T22:37:16.079017297Z",
 "created_by": "/bin/sh -c set -x && addgroup --system --gid 101 nginx 
&& adduser --system --disabled-login --ingroup nginx --no-create-home --home /
nonexistent --gecos \"nginx user\" --shell /bin/false --uid 101 nginx && apt-get 
update && apt-get install --no-install-recommends --no-install-suggests -y gnupg1 
ca-certificates && NGINX_GPGKEY=573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62; 
found=''; for server in hkp://keyserver.ubuntu.com:80 
pgp.mit.edu ; do echo \"Fetching GPG key $NGINX_GPGKEY from $server\"; 
apt-key adv --keyserver \"$server\" --keyserver-options timeout=10 --recv-keys 
\"$NGINX_GPGKEY\" && found=yes && break; done; test -z \"$found\" && echo >&2 
\"error: failed to fetch GPG key $NGINX_GPGKEY\" && exit 1; apt-get remove --
purge --auto-remove -y gnupg1 && rm -rf /var/lib/apt/lists/* && dpkgArch=\"$(dpkg 
--print-architecture)\" && nginxPackages=\" nginx=${NGINX_VERSION}-$
{PKG_RELEASE} nginx-module-xslt=${NGINX_VERSION}-${PKG_RELEASE} 
nginx-module-geoip=${NGINX_VERSION}-${PKG_RELEASE} nginx-module-imagefilter=${NGINX_VERSION}-${PKG_RELEASE} nginx-module-njs=${NGINX_VERSION}+$
{NJS_VERSION}-${PKG_RELEASE} \" && case \"$dpkgArch\" in amd64|arm64) 
echo \"deb https://nginx.org/packages/debian/ bullseye nginx\" >> /etc/apt/
sources.list.d/nginx.list && apt-get update ;; *) 
echo \"deb-src https://nginx.org/packages/debian/ bullseye nginx\" >> /etc/apt/
sources.list.d/nginx.list && tempDir=\"$(mktemp -d)\" 
&& chmod 777 \"$tempDir\" && savedAptMark=\"$(apt-mark 
showmanual)\" && apt-get update && apt-get builddep -y $nginxPackages && ( cd \"$tempDir\" 
&& DEB_BUILD_OPTIONS=\"nocheck parallel=$(nproc)\" apt-get source 
--compile $nginxPackages ) && apt-mark showmanual 
| xargs apt-mark auto > /dev/null && { [ -z \"$savedAptMark\" ] || aptmark manual $savedAptMark; } && ls -lAFh \"$tempDir\" 
&& ( cd \"$tempDir\" && dpkg-scanpackages . > Packages ) && grep 
'^Package: ' \"$tempDir/Packages\" && echo \"deb [ trusted=yes ] file://
$tempDir ./\" > /etc/apt/sources.list.d/temp.list && apt-get -o 
Acquire::GzipIndexes=false update ;; esac && apt-get install 
--no-install-recommends --no-install-suggests -y 
$nginxPackages gettext-base curl 
&& apt-get remove --purge --auto-remove -y && rm -rf /var/lib/apt/lists/* /etc/apt/
sources.list.d/nginx.list && if [ -n \"$tempDir\" ]; then apt-get 
purge -y --auto-remove && rm -rf \"$tempDir\" /etc/apt/sources.list.d/
temp.list; fi && ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /
dev/stderr /var/log/nginx/error.log && mkdir /docker-entrypoint.d"
 },
 {
 "created": "2022-05-17T22:37:16.308331577Z",
 "created_by": "/bin/sh -c #(nop) COPY 
file:65504f71f5855ca017fb64d502ce873a31b2e0decd75297a8fb0a287f97acf92 in / "
 },
 {
 "created": "2022-05-17T22:37:16.42037498Z",
 "created_by": "/bin/sh -c #(nop) COPY 
file:0b866ff3fc1ef5b03c4e6c8c513ae014f691fb05d530257dfffd07035c1b75da in /dockerentrypoint.d "
 },
 {
 "created": "2022-05-17T22:37:16.526730341Z",
 "created_by": "/bin/sh -c #(nop) COPY 
file:0fd5fca330dcd6a7de297435e32af634f29f7132ed0550d342cad9fd20158258 in /dockerentrypoint.d "
 },
 {
 "created": "2022-05-17T22:37:16.63286206Z",
 "created_by": "/bin/sh -c #(nop) COPY 
file:09a214a3e07c919af2fb2d7c749ccbc446b8c10eb217366e5a65640ee9edcc25 in /dockerentrypoint.d "
 },
 {
 "created": "2022-05-17T22:37:16.723840482Z",
 "created_by": "/bin/sh -c #(nop) ENTRYPOINT [\"/docker-entrypoint.sh\"]",
 "empty_layer": true
 },
 {
 "created": "2022-05-17T22:37:16.816451964Z",
 "created_by": "/bin/sh -c #(nop) EXPOSE 80",
 "empty_layer": true
 },
 {
 "created": "2022-05-17T22:37:16.912604472Z",
 "created_by": "/bin/sh -c #(nop) STOPSIGNAL SIGQUIT",
 "empty_layer": true
 },
 {
 "created": "2022-05-17T22:37:17.011072851Z",
 "created_by": "/bin/sh -c #(nop) CMD [\"nginx\" \"-g\" \"daemon off;\"]",
 "empty_layer": true
 }
 ],
 "os": "linux",
 "rootfs": {
 "type": "layers",
 "diff_ids": [
 "sha256:fd95118eade99a75b949f634a0994e0f0732ff18c2573fabdfc8d4f95b092f0e",
 "sha256:c2a3d4a53f9adaef9826a74511dcab96c18c6cab06d39270b82dcd2b0c496e5f",
 "sha256:a64d597d6b14cfa4291fb73cbe9c998610d37d049b34b9e6271f0b72a893ebb2",
 "sha256:4f49c6d6dd075585b63d71ad3e63a3cc9ae2c3319a01ecb9ca1fbc78768d4b7b",
 "sha256:881700cb7ab2ce8da6ae29674416aa6dbe6ce0a652a9a81a9d5aefc36da122ee",
 "sha256:07ef16952879508db7972ea8a2815a3bc8caea4950c0195223d67ea938b44957"
 ]
 }
}
```

Конфигурация содержит все метаданные образа. Обратите внимание на переменные окружения и историю сборки: значения аргументов сборки сохраняются в истории, а значения переменных в отдельном списке. Не передавайте секреты как аргументы сборки и не сохраняйте их как переменные окружения, когда пользуетесь docker build.  
Для передачи секретов используется расширение директивы RUN: [RUN --mount-type=secret.](https://docs.docker.com/engine/reference/builder/#run---mounttypesecret)

Оптимизация образа

При сборке при помощи Dockerfile каждая директива, изменяющая состояние файловой системы, создает новый слой в образе. Вернемся с новым знанием к нашему Dockerfile:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN npm install
RUN npx next build
 
RUN cp --recursive .next/standalone /app
RUN cp --recursive public /app/public
RUN cp --recursive .next/static /app/.next/static
 
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

Заметим, что четыре последних директивы RUN создают по новому слою, но при изменении первого слоя, изменятся все остальные. Т. е. не имеет никакого смысла содержать четыре отдельных слоя:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN \
  npm install \
  && npx next build \
  && cp --recursive .next/standalone /app \
  && cp --recursive public /app/public \
  && cp --recursive .next/static /app/.next/static
 
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

Также после сборки нам не нужны исходные файлы, их можно удалить:

**Dockerfile**

```
FROM node:18-slim
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN \
  npm install \
  && npx next build \
  && cp --recursive .next/standalone /app \
  && cp --recursive public /app/public \
  && cp --recursive .next/static /app/.next/static \
  && cd / \
  && rm --recursive --force /build
 
WORKDIR /app
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

Такой образ похож на оптимальный, но все еще содержит ненужные слои COPY, т.к. следующий слой RUN полностью удаляет их содержимое. Чтобы упростить сборку и не удалять ненужные файлы воспользуемся многоступенчатой сборкой (multi-stage build).

**Dockerfile**

```
FROM node:18-slim AS base
 
 
FROM base AS build
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN \
  npm install \
  && npx next build \
  && cp --recursive .next/standalone /app \
  && cp --recursive public /app/public \
  && cp --recursive .next/static /app/.next/static
 
 
FROM base AS final
 
WORKDIR /app
COPY --from=build /app/ ./
 
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

В таких сборках используется понятии стадия — последовательность директив между директивами FROM, включая начальную FROM. Имя стадии задается опцией AS в директиве FROM.  
Наш Dockerfile состоит из трех стадий:

**base**

```
FROM node:18-slim AS base
```

**build**

```
FROM base AS build
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN \
  npm install \
  && npx next build \
  && cp --recursive .next/standalone /app \
  && cp --recursive public /app/public \
  && cp --recursive .next/static /app/.next/static
```

**final**

```
FROM base AS final
 
WORKDIR /app
COPY --from=build /app/ ./
 
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

Мы можем использовать стадию как базовый образ, либо копировать файлы из одной стадии в другую.  
Имена образов и стадий взаимозаменяемы.  
При окончании сборки, все стадии, кроме последней, отбрасываются. Т. е. конечный образ будет состоять всего из N + 1 слоев, где N — число образов в базовом образе node:18-slim.

Понижение привилегий

По умолчанию процесс в контейнере запускается из-под пользователя root. Это считается плохой практикой, т.к. обычно повышенные привилегии не нужны для работы процесса, они лишь упрощают использование уязвимостей. Чтобы переопределить пользователя его нужно создать и выбрать директивой USER:

**Dockerfile**

```
FROM node:18-slim AS base
 
 
FROM base AS build
 
SHELL [ "/bin/sh", "-eu", "-c" ]
 
WORKDIR /build
COPY src/ src/
COPY public/ public/
COPY package.json package-lock.json next.config.js tsconfig.json ./
 
RUN \
  npm install \
  && npx next build \
  && cp --recursive .next/standalone /app \
  && cp --recursive public /app/public \
  && cp --recursive .next/static /app/.next/static
 
 
FROM base AS final
 
ARG USER=user
ARG HOME=/app
ARG UID=1001
ARG GID=1001
RUN \
  addgroup --gid "${GID}" "${USER}" \
  && adduser --disabled-password --gecos "" \
  --home "${HOME}" --ingroup "${USER}" --uid "${UID}" "${USER}"
 
WORKDIR ${HOME}
COPY --from=build /app/ ./
 
USER ${USER}
ENV PORT="8080"
EXPOSE ${PORT}/tcp
ENTRYPOINT [ "node", "--", "/app/server.js" ]
```

Для создания пользователя и главной группы для него воспользуемся скриптами addgroupи adduser. Эти команды будут отличаться в зависимости от базового образа, но они есть в базовых образах debian и alpine.  
  
Директива USER задает активного пользователя, в качестве ее аргумента можно передать идентификатор пользователя, либо его имя.  
Заметим, что создание пользователя и копирование файлов в финальный слой — независимые операции. В таких случаях лучше размещать команды, результат выполнения которых меняется реже. Здесь, очевидно, что мы не будем часто менять имя пользователя и его идентификаторы.

Проверка

Запустим собранный нами образ:

```
$ docker run --detach --name counter --publish 8080:8080/tcp x
```

Вы можете проверить собранное приложение при помощи браузера или curl .

Домашнее задание

Соберите Docker образ для проекта [counter-backend](https://git.devops-teta.ru/materials/counter-backend). В качестве базового образа используйте [python:3.11.6-slim-bookworm](https://hub.docker.com/_/python). Для сборки используйте следующие команды:  
  
Установка зависимостей для сборки пакета:

```
$ python -m pip install \
    --no-color \
    --no-cache-dir \
    --disable-pip-version-check \
    --no-python-version-warning \
    --no-warn-script-location \
    --break-system-packages \
    --progress-bar off \
    poetry setuptools wheel
```

Загрузка всех зависимостей в папку dist/vendor:

```
$ mkdir -p dist
$ poetry export \
   --without-hashes \
   --format constraints.txt \
   --output dist/constraints.txt
$ poetry run \
    python -m pip wheel \
      --isolated \
      --requirement dist/constraints.txt \
      --wheel-dir dist/vendor
```

Пакетирование проекта в папку dist:

```
$ poetry build --format wheel
```

Установка всех зависимостей:

```
$ packages=$(\
    find 'dist' 'dist/vendor' \
        -maxdepth 1 \
        -iname '*.whl' \
        -exec realpath {} \; \
        -print0 \
      | xargs --null)
$ python -m pip install
    --isolated \
    --no-index \
    --no-color \
    --no-cache-dir \
    --disable-pip-version-check \
    --no-python-version-warning \
    --no-warn-script-location \
    --no-deps \
    --break-system-packages \
    --progress-bar off \
    ${packages}
```

Эти команды находят все пакеты Python собранные предыдущими командами и затем устанавливают их.  
  
Запуск модуля:

```
$ python -m counter_backend
```

Напишите три варианта Dockerfile:  
 

*   Без использования многоступенчатой сборки и запуском процесса из-под суперпользователя
*   С использованием многоступенчатой сборки ()
*   С использованием многоступенчатой сборки и понижением привилегий:
*   Загрузите пакеты первым и вторым набором команд, скопируйте в финальный слой и установите в нем;
*   Воспользуйтесь приведенным выше скриптом для создания пользователя

Загрузите написанные Dockerfile в курсовой GitLab, в отдельный репозиторий. Если вы не пользовались ранее Git, то просмотрите краткую справку, приведенную дальше.

Справка по Git

Чтобы создать новый Git репозиторий, создайте папку и инициализируйте в нет репозиторий командой git init:

```
$ mkdir --parents new-project
$ cd new-projects
$ git init
```

Все данные репозитория хранятся в папке .git, которая создается git init.  
  
После этого сделайте нужные правки, создайте файлы и т. д. Затем добавьте файлы, чтобы Git начал их отслеживать:

```
$ git add FILE1 FILE2
```

После этого зафиксируйте изменения:

```
$ git commit --message 'initial commit'
```

Эта команда создаст новый коммит (фиксацию) — именованный набор изменений. Коммит — это минимальная единица истории Git.  
  
После этого создайте новый проект на GitLab. Выключите опцию Initialize repository with a README, чтобы загрузить уже существующий репозиторий.  
  
Добавьте в ваш локальный репозиторий ссылку на проект GitLab, скопировав команду из GitLab:

```
$ git remote add origin git@git.devops-teta.ru:....git
```

После этого загрузите изменения в GitLab, скопировав команду из GitLab:

```
$ git push -u origin main
```