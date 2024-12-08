Inspect и прочий дебаг

Build debug

Для того что бы достаточно достоверно выяснить в чем проблема при билде контейнера можно использовать расширенный вывод команды build.

```
docker build --progress=plain --no-cache .
```

Рассмотрим чуть подробнее. Опция _plain_ показывает вывод контейнера. Опция _no-cache_используется потому что закэшированный контейнер не показывает вывода.  
  
Если дебажить надо, а желания постоянно дописывать дополнительные команды нет, то можно экспортировать переменную.

```
export BUILDKIT_PROGRESS=plain
```

Docker inspect

Базовый синтаксис выглядит так:

```
docker inspect [OPTIONS] NAME
```

Давайте посмотрим на примере контейнера с Nginx.  
По умолчанию вывод в виде json массива:

```
docker inspect <NAME>
```

В json мы можем использовать методы поиска по массиву:

```
docker inspect --format='{\{.Os}}' nginx
```

Inspect может использоваться для получения информации как о образе так и запущенном контейнере.  
Покажет какой порт был опубликован:

```
docker inspect --format='{\{.Config.ExposedPorts}}' nginx
```

Посмотрим какой контейнер у нас сейчас запущен и получим о нем информацию:

```
docker ps
```

```
docker inspect <ID>
```

Посмотреть IP и Hostname контейнера:

```
docker inspect --format='{\{.Config.Hostname}} has the following IP: {\{.NetworkSettings.IPAddress}}'
```

Дополнительные флаги типа -s позволяют узнать объём контейнера:

```
docker inspect -s
```

Для более читаемого вывода можно использовать jq:

```
docker inspect --format='{\{json .NetworkSettings.Networks }}' <ID> | jq .
```

Если по каким-то причинам имя запущенного контейнера равнозначно образу, то для однозначного определения того, что просматривать, используется команда type:

```
docker inspect --type=image nginx
```

Интеграция контейнеров

Docker реализует концепцию «тонких» контейнеров — когда один контейнер содержит ровно одну программу и взаимодействие между ними организуется при помощи механизмов межпроцессного взаимодействия Linux, в основном сети и файловой системы.

Сеть

Рассмотрим взаимодействие через сеть: Docker по умолчанию выделяет контейнеру адрес в отдельной изолированной сети. Чтобы взаимодействовать с контейнером извне используется механизм публикации портов. Используйте опцию --publish (-p), чтобы пробросить порт в хост-систему:

```
$ docker run \
    --detach \
    --name test \
    --publish 8080:80/tcp \
    nginx:1.20
```

Мы рассмотрели синтаксис этой опции на предыдущей практике.  
Напомним формат:

```
[HOST_ADDRESS:]<HOST_PORT>:<CONTAINER_PORT>[/PROTOCOL]
```

Здесь:  
HOST\_ADDRESS (опционально, по-умолчанию 0.0.0.0) — IP адрес, к которому привязать порт в сети хоста. Укажите 127.0.0.1, чтобы порт был доступен только локально или 0.0.0.0, чтобы порт слушался на всех адресах, привязанных к хосту;  
HOST\_PORT (обязательно) — слушаемый порт в сети хоста;  
CONTAINER\_PORT (обязательно) — слушаемый порт в сети контейнера;  
PROTOCOL — (опционально, по-умолчанию tcp) — протокол слушаемого порта, вы можете указать tcp либо udp.  
Чтобы интегрировать несколько контейнеров на одном хосте используйте пользовательские bridge сети. Создадим новую сеть my-net командой docker network create:

```
$ docker network create \
   --driver bridge \
   my-net
897f0f84af6251554d98481a5bcdb8169c5d3db9591709a8456f905687bed4b7
```

Просмотрим список существующих сетей:

```
$ docker network ls
NETWORK ID    NAME    DRIVER  SCOPE
8033a0ba9455  bridge  bridge  local
773e51a4eeb6  host    host    local
897f0f84af62  my-net  bridge  local
850a1793ff17  none    null    local
```

Просмотрим IP адрес сети и другие метаданные.

```
$ docker network inspect my-net | jq --indent 2
[
  {
    "Name": "my-net",
    "Id": "897f0f84af6251554d98481a5bcdb8169c5d3db9591709a8456f905687bed4b7",
    "Created": "1970-00-00T00:00:00.000000000Z",
    "Scope": "local",
    "Driver": "bridge",
    "EnableIPv6": false,
    "IPAM": {
      "Driver": "default",
      "Options": {},
      "Config": [
        {
          "Subnet": "172.18.0.0/16",
          "Gateway": "172.18.0.1"
        }
      ]
    },
    "Internal": false,
    "Attachable": false,
    "Ingress": false,
    "ConfigFrom": {
      "Network": ""
    },
    "ConfigOnly": false,
    "Containers": {},
    "Options": {},
    "Labels": {}
  }
]
```

Чтобы запустить контейнер, подключенный к новой сети выполним команду docker run, указав опцию --network:

```
$ docker run \
    --tty \
    --interactive \
    --detach \
    --network my-net \
    --name alpine1 \
    alpine:3.18 \
    sh
a69e1c307932f4ea208825e2b0afc559b0210d63766c1c75f6f9b09f05dea8a7
```

Запустим еще два контейнера:

```
$ docker run \
    --tty \
    --interactive \
    --detach \
    --network my-net \
    --name alpine2 \
    alpine:3.18 \
    sh
856d424e5354b61975b77bd25aa361b6075770c42cdd5050b2c573f2e582c3bd

$ docker run \
    --tty \
    --interactive \
    --detach \
    --name alpine3 \
    alpine:3.18 \
    sh
d809123381dd9fe3e9cea04c2bf7cb8f13138fe7116725ac618c930204bba5bb
```

Просмотрим информацию о нашей сети еще раз:

```
$ docker network inspect my-net | jq --indent 2
[
  {
    "Name": "my-net",
    "Id": "897f0f84af6251554d98481a5bcdb8169c5d3db9591709a8456f905687bed4b7",
    "Created": "1970-00-00T00:00:00.000000000Z",
    "Scope": "local",
    "Driver": "bridge",
    "EnableIPv6": false,
    "IPAM": {
      "Driver": "default",
      "Options": {},
      "Config": [
        {
          "Subnet": "172.18.0.0/16",
          "Gateway": "172.18.0.1"
        }
      ]
    },
    "Internal": false,
    "Attachable": false,
    "Ingress": false,
    "ConfigFrom": {
      "Network": ""
    },
    "ConfigOnly": false,
    "Containers": {
      "856d424e5354b61975b77bd25aa361b6075770c42cdd5050b2c573f2e582c3bd": {
        "Name": "alpine2",
        "EndpointID": "a08c120e7277900ba11dee1898bf07fd388b11a845f925768339eb00c2ba3868",
        "MacAddress": "02:42:ac:12:00:03",
        "IPv4Address": "172.18.0.3/16",
        "IPv6Address": ""
      },
      "a69e1c307932f4ea208825e2b0afc559b0210d63766c1c75f6f9b09f05dea8a7": {
        "Name": "alpine1",
        "EndpointID": "f47668578a1786403f33fa293ee594bd432809f85a1e4e015169ed1ce0148f81",
        "MacAddress": "02:42:ac:12:00:02",
        "IPv4Address": "172.18.0.2/16",
        "IPv6Address": ""
      }
    },
    "Options": {},
    "Labels": {}
  }
]
```

Заметим, что к сети теперь подключены два контейнера. Также просмотрим метаданные сети по умолчанию (bridge):

```
$ docker network inspect bridge | jq --indent 2
[
  {
    "Name": "bridge",
    "Id": "8033a0ba945562834572c9f577ce91189c88a93fa807941af388af6777a21185",
    "Created": "1970-00-00T00:00:00.000000000Z",
    "Scope": "local",
    "Driver": "bridge",
    "EnableIPv6": false,
    "IPAM": {
      "Driver": "default",
      "Options": null,
      "Config": [
        {
          "Subnet": "172.17.0.0/16",
          "Gateway": "172.17.0.1"
        }
      ]
    },
    "Internal": false,
    "Attachable": false,
    "Ingress": false,
    "ConfigFrom": {
      "Network": ""
    },
    "ConfigOnly": false,
    "Containers": {
      "d809123381dd9fe3e9cea04c2bf7cb8f13138fe7116725ac618c930204bba5bb": {
        "Name": "alpine3",
        "EndpointID": "2c1bc055f99cadde2ddc0b8491b1c87c217a9b69c303aa86e5444153b6143327",
        "MacAddress": "02:42:ac:11:00:02",
        "IPv4Address": "172.17.0.2/16",
        "IPv6Address": ""
      }
    },
    "Options": {
      "com.docker.network.bridge.default_bridge": "true",
      "com.docker.network.bridge.enable_icc": "true",
      "com.docker.network.bridge.enable_ip_masquerade": "true",
      "com.docker.network.bridge.host_binding_ipv4": "0.0.0.0",
      "com.docker.network.bridge.name": "docker0",
      "com.docker.network.driver.mtu": "1500"
    },
    "Labels": {}
  }
]
```

Попробуем подключиться к alpine2 и alpine3 из alpine1:

```
$ docker attach alpine1
# ping -c 2 alpine2
PING alpine2 (172.18.0.3): 56 data bytes
64 bytes from 172.18.0.3: seq=0 ttl=64 time=0.146 ms
64 bytes from 172.18.0.3: seq=1 ttl=64 time=0.097 ms
 
--- alpine2 ping statistics ---
2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max = 0.097/0.121/0.146 ms
# ping -c 2 alpine3
ping: bad address 'alpine3'
# ping -c 2 172.17.0.2
PING 172.17.0.2 (172.17.0.2): 56 data bytes
 
--- 172.17.0.2 ping statistics ---
2 packets transmitted, 0 packets received, 100% packet loss
```

Заметим, что мы можем обратиться к контейнерам, подключенным к одной пользовательской сети, используя их имя. К контейнеру же подключенному к сети по умолчанию нельзя подключиться ни по имени, ни по адресу. Удалим созданную сеть и контейнеры:

```
$ docker container rm --force alpine1 alpine2 alpine3
$ docker network rm my-net
```

Файловая система

Теперь рассмотрим интеграцию при помощи файловой системы. Docker позволяет монтировать элементы файловой системы хоста внутрь контейнера, чтобы гарантировать их сохранение при пересоздании контейнера. Также Docker поддерживает тома—именованные директории, полностью управляемые Docker. Для сохранения состояния контейнеров рекомендуется использовать тома, для инъекции внутрь контейнера заранее известных файлов (например, конфигов) рекомендуется монтирование.  
  
Запустим контейнер с СУБД PostgreSQL, сохранив состояние контейнера при помощи тома state:

```
$ docker run --detach \
 --name postgres \
 --env PGDATA=/var/lib/postgresql/data/pgdata \
 --env POSTGRES_PASSWORD=postgres \
 --volume state:/var/lib/postgresql/data:rw \
postgres:16.0
```

Здесь опция --volume (-v) объявляет точку монтирования и имеет следующий формат:

```
[HOST_DIR:]CONTAINER_DIR[:OPTIONS]
```

HOST\_DIR — абсолютный путь (начинается с /) к элементу файловой системы хоста или имя Docker тома. Если том с таким именем не существует, то он будет создан. Если же этот параметр пропущен, то Docker создаст новый том с автосгенерированным именем;  
  
CONTAINER\_DIR — абсолютный путь к точке монтирования в контейнере. Данные из хост-пути или тома будут доступны по этому пути;  
  
OPTIONS — Параметры монтирования. Здесь указана опция rw — том доступен для чтения и записи. Опция ro, например, указывает что том доступен только для чтения, ее часто используют при монтировании конфигов.

Остальные параметры смотрите в [онлайн-документации](https://docs.docker.com/engine/reference/commandline/run/#volume) или man docker-run.

Также мы воспользовались опцией --env (-e), которая задает переменную окружения, доступную всем процессам в контейнере. Здесь мы указали директорию, содержащую состояние нашего кластера БД (PGDATA) и пароль от суперпользователя кластера (POSTGRES\_PASSWORD).

Если ваши переменные окружения содержат секреты, то не пробрасывайте их при помощи --env и --env-file, т.к. они отображаются в метаданных контейнера. Вместо этого используйте конфигурационные файлы, либо файлы с переменными окружения, которые читаются после запуска контейнера либо самой программой, либо скриптом инициализации.

Подключимся к запущенной СУБД и создадим таблицу:

```
$ docker exec \
    --tty \
    --interactive \
    postgres \
    psql -U postgres
postgres=# create table test as select 1;
SELECT 1
postgres=# select * from test;
 ?column?
----------
        1
(1 row)
postgres=# \q
```

Удалим запущенный контейнер командой docker rm --force postgres, при этот созданный том state не будет удален:

```
$ docker volume ls
DRIVER  VOLUME NAME
local   state
```

Просмотрим детальную информацию по тому:

```
$ docker volume inspect state
[
    {
        "CreatedAt": "1970-01-01T00:00:00+00:00",
        "Driver": "local",
        "Labels": null,
        "Mountpoint": "/var/lib/docker/volumes/state/_data",
        "Name": "state",
        "Options": null,
        "Scope": "local"
    }
]
```

Снова запустим контейнер указанными выше командами:

```
$ docker run \
    --detach \
    --name postgres \
    --env PGDATA=/var/lib/postgresql/data/pgdata \
    --env POSTGRES_PASSWORD=postgres \
    --volume state:/var/lib/postgresql/data:rw \
    postgres:16.0
...
$ docker exec \
    --tty \
    --interactive \
    postgres \
    psql -U postgres
postgres=# select * from test;
 ?column?
----------
        1
(1 row)
postgres=# \q
```

Заметим, что созданная таблица сохранилась. Удалим созданный том и контейнер:

```
$ docker container rm postgres
...
$ docker volume rm state
```

Мы можем подключить один том к нескольким контейнерам, чтобы синхронизировать состояние между двумя контейнерами. Например, используем именованный канал (named pipe) — специальный файл, позволяющий передавать данные из ровно одного процесса в другой:

```
$ docker run \
    --detach \
    --name source \
    --volume state:/data:rw \
    alpine:3.18 \
    sh -c 'mkfifo /data/pipe || true
           while true
           do 
             wget -O- 2>/dev/null https://httpbin.org/uuid \
               | grep -oE "[a-z0-9-]{36}" \
               | tee /data/pipe
             sleep 10
           done'
...
$ docker run \
    --detach \
    --name dest \
    --volume state:/data:rw \
    alpine:3.18 \
    sh -c 'while true
           do
             cat /data/pipe
             sleep 10
           done'
...
```

Таким образом мы можем получать поток случайных UUID и передавать их для использования в другой процесс:

```
$ docker logs --follow dest
ba5f070d-7712-418b-9f02-bdac160fa812
cd74a971-706e-4992-bb8e-03ba8c616740
...
```

Удалим созданные контейнеры и том:

```
$ docker rm --force source dest
...
$ docker volume rm state
...
```

Такой подход можно использовать для синхронизации конфигурации контейнера с внешним источником. Например, можно использовать утилиту [git-sync](https://github.com/kubernetes/git-sync).  
  
Вместо томов можно монтировать пути файловой системы хоста, в примере с PostgreSQL мы можем заменить на абслютный путь к папке с данными:

```
$ mkdir -p data

$ docker run \
    --detach \
    --name postgres \
    --env PGDATA=/var/lib/postgresql/data/pgdata \
    --env POSTGRES_PASSWORD=postgres \
    --volume "$(realpath data):/var/lib/postgresql/data:rw" \
    postgres:16.0
...
```

Мы используем утилиту realpath, чтобы привести путь data к абсолютному.  
Чаще монтирование файлов хост-системы используется для подкладывания конфигов и различных скриптов. Вынесем скрипты в примере про обмен данными между контейнерами:

```
$ cat <<'EOT' >source.sh
#!/bin/sh
set -eu

mkfifo /data/pipe || true

while true
do
    wget -O- 2>/dev/null \
        https://httpbin.org/uuid \
      | grep -oE '[a-z0-9-]{36}' \
      | tee /data/pipe
    sleep 10
done
EOT
$ cat <<'EOT' >dest.sh
#!/bin/sh
set -eu

while true
do
    cat /data/pipe
    sleep 10
done
EOT
$ docker run \
    --detach \
    --name source \
    --volume state:/data:rw \
    --volume "$(realpath source.sh):/source.sh:ro" \
    alpine:3.18 \
    sh /source.sh
...
$ docker run \
    --detach \
    --name dest \
    --volume state:/data:rw \
    --volume "$(realpath dest.sh):/dest.sh:ro" \
    alpine:3.18 \
    sh /dest.sh
...
```

Если погрузиться чуть ниже

Если задуматься, как на самом деле работают внутренние компоненты, обеспечивающие работу интерфейса Docker, то можно осознать, что за этим простым интерфейсом скрывается множество продвинутых технологий, поэтому чуть поближе рассмотрим одну из них — объединённую файловую систему.  
  
Что такое объединённая файловая система?  
  
Каскадно-объединённое монтирование — это тип файловой системы, в которой создается иллюзия объединения содержимого нескольких каталогов в один без изменения исходных (физических) источников.  
  
Такой подход может оказаться полезным, если имеются связанные наборы файлов, хранящиеся в разных местах или на разных носителях, но отображать их надо как единое и совокупное целое.  
  
Однако технологию объединённого монтирования (или объединённой файловой системы), по сути, нельзя считать отдельным типом файловой системы. Это, скорее, особая концепция с множеством реализаций.  
  
Мы не будем рассматривать все существующие реализации, а поговорим про OverlayFS.  
  
OverlayFS — была включена в ядро Linux Kernel, начиная с версии 3.18 (26 октября 2014 года). Данная файловая система используется по умолчанию драйвером overlay2 Docker. Можно проверить, запустив команду:

```
docker system info | grep Storage
```

Почему Overlay?  
Многие образы, используемые для запуска контейнеров, занимают довольно большой объём. Было бы разорительно выделять столько места всякий раз, когда потребуется из этих образов создать контейнер.  
  
При использовании объединённой файловой системы Docker создаёт поверх образа тонкий слой, а остальная часть образа может быть распределена между всеми контейнерами.  
  
Мы также получаем дополнительное преимущество за счёт сокращения времени запуска, так как отпадает необходимость в копировании файлов образа и данных.  
  
Объединённая файловая система также обеспечивает изоляцию, поскольку контейнеры имеют доступ к общим слоям образа только для чтения.  
Если контейнерам когда-нибудь понадобится внести изменения в любой файл, доступный только для чтения, они используют стратегию копирования при записи copy-on-write, позволяющую копировать содержимое на верхний слой, доступный для записи, где такое содержимое может быть безопасно изменено.  
  
CoW — это способ оптимизации, при котором, если две вызывающих программы обращаются к одному и тому же ресурсу, можно дать им указатель на один и тот же ресурс, не копируя его.  
  
  
Копирование необходимо только тогда, когда одна из вызывающих программ пытается осуществить запись собственной «копии» — отсюда в названии способа появилось слово «копия», то есть копирование осуществляется при (первой попытке) записи.  
  
Рассмотрим многоуровневую архитектуру Docker. Песочница контейнера состоит из нескольких ветвей образа, или, как мы их называем, слоёв. Такими слоями являются часть объединённого представления, доступная только для чтения (lowerdir), и слой контейнера — тонкая верхняя часть, доступная для записи (upperdir).  
  
Не считая терминологических различий, речь фактически идёт об одном и том же — слои образа, извлекаемые из реестра, представляют собой lowerdir, и, если запускается контейнер, upperdir прикрепляется поверх слоев образа, обеспечивая рабочую область, доступную для записи в контейнер.  
  
Чтобы показать, как Docker использует файловую систему OverlayFS, попробуем посмотреть процесс монтирования Docker контейнеров и слоев образа.  
  
Итак, у нас на системе присутствует контейнер, который мы можем рассмотреть подробнее.  
Далее нужно проверить его слои. Проверить слои образа можно, либо запустив проверку образа в Docker и изучив поля GraphDriver, либо перейдя в каталог /var/lib/docker/overlay2, в котором хранятся все слои образа.  
  
Выполним обе эти операции и посмотрим, что получится:

```
docker inspect nginx | jq .[0].GraphDriver.Data
```

```
cd /var/lib/docker/overlay2
ls -l
tree <ID>
```

Если внимательно посмотреть на полученные результаты, можно увидеть следующую информацию:  
  
LowerDir — это каталог, в котором слои образа, доступные только для чтения, разделены двоеточиями.  
MergedDir — объединённое представление всех слоев образа и контейнера.  
UpperDir — слой для чтения и записи, на котором записываются изменения.  
WorkDir — рабочий каталог, используемый Linux OverlayFS для подготовки объединённого представления.  
Сделаем ещё один шаг — запустим контейнер и изучим его слои:

```
docker run -d --name overlay nginx
 
docker inspect overlay | jq .[0].GraphDriver.Data
 
tree -l 3 <"UpperDir">
```

Из представленных выше выходных данных следует, что те же каталоги, которые были перечислены в выводе команды docker inspect nginx ранее как MergedDir, UpperDirи WorkDir, теперь являются частью LowerDir контейнера.  
  
В нашем случае LowerDir составляется из всех слоев образа nginx, размещённых друг на друге. Поверх них размещается слой в UpperDir, доступный для записи, содержащий каталоги /etc, /run и /var.  
  
Также, раз уж мы выше упомянули MergedDir, можно видеть всю доступную для контейнера файловую систему, в том числе всё содержимое каталогов UpperDir и LowerDir.  
  
Именно к этому сводится действие файловой системы OverlayFS в Docker — на множестве уложенных друг на друга слоев может использоваться одна команда монтирования.

Docker Compose

Docker-compose — это надстройка над докером, приложение написанное на Python, которое позволяет запускать множество контейнеров одновременно и маршрутизировать потоки данных между ними. Оно предназначено для решения задач, связанных с развёртыванием проектов.  
  
Для чего нужен Compose? Если для функционирования проекта используется несколько сервисов, то Docker Compose может вам пригодиться. Например, в ситуации, когда создают веб-сайт, которому для выполнения аутентификации пользователей, нужно подключиться к базе данных.  
  
Подобный проект может состоять из двух сервисов — того, что обеспечивает работу сайта, и того, который отвечает за поддержку базы данных. Технология Docker Compose позволяет с помощью одной команды запускать множество сервисов.  
  
Разница между Docker и Docker Compose:  
 

*   Docker применяется для управления отдельными контейнерами (сервисами), из которых состоит приложение.
*   Docker Compose используется для одновременного управления несколькими контейнерами, входящими в состав приложения. Этот инструмент предлагает те же возможности, что и Docker, но позволяет работать с более сложными приложениями.

  
Итак, давайте попробуем собрать наш Docker Compose проект.

Пример: Kafka

Если говорить про Kafka просто то это распределенный горизонтально масштабируемый отказоустойчивый журнал коммитов.  
  
Журнал коммитов, также именуемый как «журнал опережающей записи», «журнал транзакций», — это долговременная упорядоченная структура данных, причем, данные в такую структуру можно только добавлять.  
  
Записи из этого журнала нельзя ни изменять, ни удалять. Информация считывается слева направо; таким образом гарантируется правильный порядок элементов.  
  
KRaft это замена Zookeeper на механизм использующий протокол консенсуса на основе кворума (Raft). Который использует саму Kafka для хранения метаданных.  
  
Запустим для примера Kafka и веб-интерфейс для нее при помощи docker-compose. Мы развернем Kafka в режиме KRaft для простоты, для начала сгенерируем случайный ID кластера при помощи docker run:

```
docker run \
    --rm \
    confluentinc/cp-kafka:7.5.0 \
    kafka-storage random-uuid
```

Скопируйте полученный ID, мы вставим его позже в docker-compose файл.  
Теперь создадим docker-compose.yml

**docker-compose.yml**

```
version: "3"
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      # вставьте сгенерированный ID сюда
      CLUSTER_ID:
      KAFKA_NODE_ID: 1
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_LISTENERS: PLAINTEXT://kafka:29092,CONTROLLER://kafka:29093,PLAINTEXT_HOST://0.0.0.0:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_JMX_PORT: 9999
      KAFKA_JMX_HOSTNAME: kafka
```

Рассмотрим полученный файл.  
  
Здесь объявлена директива version, которая задает версию docker-compose файла и секция services, которая определяет запускаемые контейнеры. Мы объявляем один контейнер kafka, который запускается из образа, заданного директивой image. Эта директива отмечает готовый образ. Если же мы хотим собрать свой образ, то image можно заменить на секцию build, которая настраивает сборку, ее мы рассмотрим позднее. Мы настраиваем контейнер при помощи переменных окружения, задавая их в секции environment.  
  
В переменных окружения можно заметить упоминания имени сервиса, будто это имя хоста, это так потому что docker-compose по умолчанию создает общую сеть для всех сервисов и задает им внутренние доменные имена, равные именам сервисов. Это имя можно переопределить директивой hostname.  
  
Запустим контейнер:

```
docker-compose up
```

Эта команда запустит контейнеры на переднем плане и будет выводить логи всех контейнеров в консоль. Подождем пару минут, пока кафка не запустится, затем закроем контейнеры нажав CTRL+C.  
  
Удалим все созданные ресурсы:

```
docker-compose down
```

Эта команда удалит все созданные контейнеры и сети, мы будем удалять ресурсы после любого изменения, чтобы старые ресурсы и конфигурации не конфликтовали с новыми.  
  
Доработаем нашу конфигурацию.  
  
Переменные окружения можно вынести в отдельный файл и указать путь к нему в секции env\_file. Создадим файл kafka.env:

**kafka.env**

```
CLUSTER_ID=
KAFKA_NODE_ID=1
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
KAFKA_PROCESS_ROLES=broker,controller
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:29093
KAFKA_LISTENERS=PLAINTEXT://kafka:29092,CONTROLLER://kafka:29093,PLAINTEXT_HOST://0.0.0.0:9092
KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT
KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
KAFKA_JMX_PORT=9999
KAFKA_JMX_HOSTNAME=kafka
```

И заменим environment на env\_file:

**docker-compose.yml**

```
version: "3"
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    env_file:
      - kafka.env
```

Как мы узнали ранее, данные, хранящиеся в контейнере, не сохраняются при удалении контейнера. Мы можем монтировать директории из хост-системы или использовать тома Docker. Подключим том kafka:

**docker-compose.yml**

```
version: "3"
volumes:
  kafka:
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    env_file:
      - kafka.env
    volumes:
      - kafka:/var/lib/kafka/data:rw
```

Синтаксис директив volume совпадает с опцией -v (--volume) команды docker run. Аналогично в Docker Compose пробросить порты из сети, созданной в Compose, в хост сеть директивой ports:

**docker-compose.yml**

```
version: "3"
volumes:
  kafka:
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    env_file:
      - kafka.env
    ports:
      - 127.0.0.1:9092:29092/tcp
    volumes:
      - kafka:/var/lib/kafka/data:rw
```

Синтаксис опять совпадает с опцией -p (--publish).  
  
Добавим второй сервис, WEB интерфейс для Kafka:

**docker-compose.yml**

```
version: "3"
volumes:
  kafka:
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    env_file:
      - kafka.env
    ports:
      - 127.0.0.1:9092:29092/tcp
    volumes:
      - kafka:/var/lib/kafka/data:rw
  kafka_ui:
    image: provectuslabs/kafka-ui:latest
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_METRICS_PORT: 9999
      KAFKA_CLUSTERS_0_METRICS_TYPE: JMX
    ports:
      - 127.0.0.1:8080:8080/tcp
    depends_on:
      - kafka
```

Compose позволяет добавлять зависимости между контейнерами при помощи depends\_on. По умолчанию зависимые контейнеры запускаются после старта процесса, т. е. в случае Kafka можно заметить, что Kafka UI запускается раньше инициализации Kafka и какое-то время падает.  
  
depends\_on имеет расширенную форму, которая позволяет указать событие при котором запускается зависимый контейнер, например service\_healthy:

**docker-compose.yml**

```
version: "3"
volumes:
  kafka:
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    env_file:
      - kafka.env
    ports:
      - 127.0.0.1:9092:29092/tcp
    volumes:
      - kafka:/var/lib/kafka/data:rw
  kafka_ui:
    image: provectuslabs/kafka-ui:latest
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_METRICS_PORT: 9999
      KAFKA_CLUSTERS_0_METRICS_TYPE: JMX
    ports:
      - 127.0.0.1:8080:8080/tcp
    depends_on:
      kafka:
        condition: service_healthy
```

Такая конфигурация не имеет смысла, т.к. сейчас в контейнере Kafka не задан HEALTHCHECK, исправим это: создадим скрипт, проверяющий запущена ли Kafka:

**kafka-healthcheck.sh**

```
#!/bin/sh
 
exec /usr/bin/kafka-broker-api-versions \
       --bootstrap-server localhost:9092 \
       2>/dev/null
```

И Dockerfile:

**kafka.dockerfile**

```
FROM confluentinc/cp-kafka:7.5.0

USER root
COPY ./kafka-healthcheck.sh /usr/local/bin/
RUN \
    chmod 0755 /usr/local/bin/kafka-healthcheck.sh

USER appuser
HEALTHCHECK \
    --interval=30s \
    --timeout=30s \
    --start-period=5s \
    --retries=3 \
  CMD [ "/usr/local/bin/kafka-healthcheck.sh" ]
```

Обновим docker-compose.yml:

**docker-compose.yml**

```
version: "3"
volumes:
  kafka:
services:
  kafka:
    build:
      context: .
      dockerfile: kafka.dockerfile
    env_file:
      - kafka.env
    ports:
      - 127.0.0.1:9092:29092/tcp
    volumes:
      - kafka:/var/lib/kafka/data:rw
  kafka_ui:
    image: provectuslabs/kafka-ui:latest
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_METRICS_PORT: 9999
      KAFKA_CLUSTERS_0_METRICS_TYPE: JMX
    ports:
      - 127.0.0.1:8080:8080/tcp
    depends_on:
      kafka:
        condition: service_healthy
```

Мы заменили директиву image на build, чтобы собрать свой образ для контейнера kafka. Аналогично секции services.\* секция services.\*.build повторяет аргументы docker build. Запустим контейнеры:

```
docker-compose up --detach --build
```

Эта команда запустит контейнеры в фоновом режиме и пересоберет образа, даже если они уже существуют. Просмотрим логи сервисов:

```
docker-compose logs --follow
```

Мы можем посмотреть логи конкретного контейнера:

```
docker-compose logs --follow kafka
```

Добавим последний контейнер с консольным клиентом Kafka, kcat:

**docker-compose.yml**

```
version: "3"
volumes:
  kafka:
services:
  kafka:
    build:
      context: .
      dockerfile: kafka.dockerfile
    env_file:
      - kafka.env
    ports:
      - 127.0.0.1:9092:29092/tcp
    volumes:
      - kafka:/var/lib/kafka/data:rw
  kafka_ui:
    image: provectuslabs/kafka-ui:latest
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_METRICS_PORT: 9999
      KAFKA_CLUSTERS_0_METRICS_TYPE: JMX
    ports:
      - 127.0.0.1:8080:8080/tcp
    depends_on:
      kafka:
        condition: service_healthy
  kcat:
    image: edenhill/kcat:1.7.1
    entrypoint: ["sh", "-c", "while true; do sleep 1d; done"]
    depends_on:
      kafka:
        condition: service_healthy
```

В ENTRYPOINT образа edenhill/kcat:1.7.1 прописана утилита kcat, поэтому этот контейнер нельзя запустить как сервис. Мы обойдем это ограничение переопределив ENTRYPOINT директивой entrypoint в docker-compose.yml.  
  
Откроем терминал в контейнере kcat:

```
docker-compose exec kcat sh
```

Аналогично мы можем выполнить команду в любом сервисе. Для примера просмотрим метаданные брокеров:

```
kcat -b kafka:29092 -L
```

Закончим на том, что напомним, что детальную информацию можно посмотреть в документации.  
[Спецификация docker-compose.yml](https://docs.docker.com/compose/compose-file/compose-file-v3/)

Домашнее задание

docker-compose:

Напишите docker-compose.yml который запускает наш сервис counter.  
  
Docker-composer должен запустить:  
 

*   [counter-frontend](https://git.devops-teta.ru/materials/counter-frontend)
*   [counter-backend](https://git.devops-teta.ru/materials/counter-backend)
*   nginx

nginx:

  
 

*   Обращения к root локейшену должны попадать в контейнер counter-frontend.
*   Обращение к /api backend должны проксироваться в контейнер counter-backend.
*   Здесь мы воспользуемся результатом генерации нашего SSL сертификата. Контейнер с nginx должен принимать подключение из интернета, по https.

Проверка

Для успешного выполнения задания вам необходимо:  
  
 

1.  Создать репозиторий в git.devops-teta.ru
2.  Загрузить в репозиторий dockerfile для counter-frontend, counter-backend, nginx, если использовалась сборка.
3.  Загрузить в репозиторий docker-compose.yml
4.  Опубликовать http порт, с работающим приложением counter. Передать ссылку на проверку.

Внимание:  
Порт приложения backend и frontend не должны быть публично доступны. Все запросы должны обрабатываться только через nginx.

Пример  
Пример работающего приложения Counter: [http://practice-4.devops-teta.ru](http://practice-4.devops-teta.ru/)

Пример конфигурации nginx:

```
server {
    listen       80;
    server_name  _;
 
    location / {
        proxy_pass      http://frontend:8080;
    }
    location /api {
        proxy_pass      http://backend:8080;
    }
}
```