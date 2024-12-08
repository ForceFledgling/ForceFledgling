Системы управления конфигурациями позволяют настраивать существующие компоненты инфраструктуры (в основном виртуальные или физические сервера). Такие системы разделяют на две большие категории по модели их работы:  
  
Push модель — конфигурация загружается на целевой компонент извне, из какой-либо внешней локации (мы толкаем изменения в цель);  
Pull модель — конфигурация загружается на целевой компонент агентом из известного хранилища конфигураций, установленным на этот компонент (цель тянет изменения сама);  
Push модель проще в реализации, т.к. не требует поддержания централизованного хранилища конфигураций (задачи обновления могут запускаться вручную, при помощи CI задач и т. п.), но она хуже масштабируется, т.к. для запуска синхронизации множества целей используются ресурсы одной машины.  
  
Pull модель же сложнее и создает новый класс проблем, связанных с синхронным обновлением конфигурации в кластерах (например при обновлении кластера etcd нужно контролировать, чтобы хосты перезапускались так, чтобы не нарушался кворум), но при этом лучше масштабируется, т.к. для применения конфигурации используются ресурсы целей, а не какой-то одной машины, с которой запускается процесс в Push модели.

Предварительная настройка

На занятиях мы рассмотрим систему управления конфигурациями Ansible, т.к. это самая популярная подобная система и она широко применяется как в МТС, так и за его пределами.  
  
Ansible использует Push модель и поддерживает настройку Linux, Windows хостов, а также других целей при помощи различных плагинов подключения.  
  
На Linux Ansible использует SSH для подключения к хосту и для выполнения операций запускает на целях автоматически сгенерированные скрипты на Python.  
  
Введем основную терминологию Ansible, которая часто встречается в документации:  
Контроллер (controller) — хост, с которого запускается Ansible;  
Цель (target) — хосты, на которых Ansible выполняет действия;  
Инвентарь (inventory) — набор целей, с привязанными к ним параметрами (параметры подключения, переменные для запускаемых скриптов и т. п.);  
Группа (group) — именованное множество целей, с привязанным к нему параметрами;  
Модуль (module) — минимально возможная операция в Ansible;  
Задача (task) — модуль с параметрами запуска (например условиями);  
Роль (role) — переиспользуемая последовательность задач;  
Плей (play) — последовательность ролей и отдельных задач, запускаемых на конкретном множестве целей;  
Плейбук (playbook) -- последовательность плеев.  
  
Обратите внимание, что Ansible четко разделяет что мы запускаем (задачи, роли) от того, где мы это запускаем (плеи, плейбуки, инвентари). Такое разделение позволяет писать переиспользуемые конфигурации.  
  
Познакомимся с названными концепциями подробнее. Мы устанавливали Ansible на первом занятии, приведем команды для установки еще раз:

```
$ sudo apt-add-repository --update ppa:ansible/ansible
$ sudo apt install ansible
```

Создайте рабочую область для Ansible, далее все операции мы будем выполнять в ней:

```
$ mkdir -p ~/projects/ansible
$ cd ~/projects/ansible
```

Начнем с создания Ansible инвентаря, в который добавим наши ВМ.  
  
Создайте файл hosts. yaml в рабочей области:

```
all:
  vars:
    ansible_user: student  # SSH пользователь, используемый Ansible
    ansible_ssh_private_key_file: "~/.ssh/id_rsa"  # Путь к приватному SSH ключу на контроллере
  hosts:
    vm1:
      ansible_host: 10.0.10.1  # Адрес, используемый Ansible для подключения.
                               # Должен быть доступен с контроллера
    vm2:
      ansible_host: 10.0.10.2
  children:
    part1:
    part2:
part1:
  hosts:
    vm1:
part2:
  hosts:
    vm2:
```

В корне YAML файла объявляются группы целей, мы объявили три — all, part1, part2. Если быть точнее, то группу all мы не объявляли — она служебная, существует всегда и содержит все объявленные в инвентаре цели. Из-за этого описывать в ней все обязательные параметры целей (чаще всего параметры подключения) — распространенная практика.  
  
В группе all мы объявили три секции — vars, hosts, children. В vars содержатся переменные группы, в hosts — имена целей с их персональными переменными, в children — имена дочерних групп (родительская группа будет содержать цели и переменные своих дочерних групп). Такая запись children ничего не меняет, т.к. all является родительской группой всех остальных групп по-умолчанию.

Ansible нет понятия области видимости переменных — все переменные глобальные и набор переменных конкретной цели формируется слиянием переменных всех групп, в которых состоит хост и его личных переменных.

Далее мы объявляем две группы — part1 и part2 и добавляем vm1 в первую, vm2 — во вторую. Обратите внимание, что мы можем дополнить переменные целей, когда указываем, что они часть группы. Такой прием имеет смысл в больших инвентарях, чтобы группировать переменные по смыслу.  
  
Теперь напишем конфигурацию запуска Ansible. Создайте в рабочей области файл ansible. cfg:

```
[defaults] 
host_key_checking = false 
inventory = ./hosts.yaml
```

Ansible по умолчанию включает проверку ключа хоста. Проверка ключей хоста защищает от подмены сервера и атак «человек посередине», но требует некоторого обслуживания. Если хост переустановлен и имеет другой ключ в «known\_hosts», это приведет к появлению сообщения об ошибке, пока оно не будет исправлено. Если нового хоста нет в «known\_hosts», ваш управляющий узел может запросить подтверждение ключа, что приводит к интерактивному взаимодействию при использовании Ansible.  
  
Отключается через host\_key\_checking = false.  
Проверим, что инвентарь написан корректно. Следующая команда выведет полное содержимое инвентаря во внутреннем формате Ansible:

```
$ ansible-inventory --list
```

И проверим подключение ко всем хостам:

```
$ ansible -m ping all
```

Ручные действия

Ansible позволяет применять изменения к целям из консоли при помощи команды ansible, таким образом мы только что проверили доступность целей инвентаря. Основной синтаксис команды таков:

```
$ ansible <-m | --module-name MODULE_NAME> [-b | --become] [-a | --args MODULE_ARGS] [-e | --extra-args EXTRA_ARGS] <HOST_PATTERN>
```

Здесь:  
\-m | --module-name MODULE\_NAME — имя запускаемого модуля;  
\-b | --become — повысить привилегии до root перед запуском модуля;  
\-a | --args MODULE\_ARGS — аргументы модуля в формате ключ-значение (key1=value1 key2=value2 …);  
\-e | --extra-args EXTRA\_ARGS — дополнительные переменные в формате ключ-значение;  
HOST\_PATTERN — набор целей; здесь можно указывать имена целей и групп, разделяя их.  
  
Эта команда поддерживает множество других параметров, посмотреть которые можно при помощи команды ansible — help.  
Зная синтаксис команды, установим и запустим Nginx на ВМ2:

```
$ ansible -b -m apt -a 'name=nginx update_cache=true state=present' vm2 
$ ansible -b -m systemd_service -a 'name=nginx.service enabled=true state=started' vm2
```

Первый модуль выполнил аналог команды sudo sh -c 'apt update && apt install nginx'.  
Второй — sudo systemctl enable --now nginx. service.  
Информация об аргументах доступна на сайте документации Ansible — [ansible.builtin.apt](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/apt_module.html), [ansible.builtin.systemd\_service](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/systemd_service_module.html#ansible-collections-ansible-builtin-systemd-service-module).  
  
При выполнении ad-hoc операций или тестировании модулей писать каждый раз аргументы ansible и набор целей неудобно. Если вам требуется выполнять такие операции используйте интерактивную консоль ansible-console.  
  
Обратите внимание на вывод команд: каждый вызов ansible запустил по одной задаче на vm2 и завершился со статусом ok или changed. Во время запуска модуля Ansible проверяет нужны ли изменения на целевом хосте и ничего не делает, если действий не требуется.  
  
Статус ok отражает такую ситуацию — хост уже в целевом состоянии, действий не требуется. changed показывает обратную ситуацию — хост не был в целевом состоянии, были выполнены действия для приведения хоста в это состояние. Продемонстрируем это, выполня команду установки Nginx еще раз:

```
$ ansible -b -m apt -a 'name=nginx state=present' vm2
```

Обратите внимание на статус ok и на то как быстро завершился модуль. Ansible проверил что пакет nginx уже установлен и не стал ничего делать.  
Теперь заменим конфигурацию Nginx на nginx. conf, чтобы наш сервер проксировал все запросы на сервис тестирования запросов [httpbin.org](https://httpbin.org/).  
  
Содержимое файла nginx. conf:

```
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;
 
events {
  worker_connections 768;
}
 
http {
  sendfile on;
  tcp_nopush on;
  types_hash_max_size 2048;
 
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
 
  access_log /var/log/nginx/access.log;
  error_log /var/log/nginx/error.log;
 
  gzip on;
 
  server {
    listen 80 default_server;
 
    location / {
      proxy_pass https://httpbin.org;
    }
  }
}
```

Для копирования файла на хост воспользуемся модулем copy:

```
$ ansible -b -m copy -a 'src=nginx.conf dest=/etc/nginx/nginx.conf owner=root group=root mode=644' vm2
```

Чтобы Nginx перечитал конфигурацию подадим процессу команду reload при помощи systemd:

```
$ ansible -b -m systemd_service -a 'name=nginx.service state=reloaded' vm2
```

Проверим корректность конфигурации, сделав запрос к httpbin.org через Nginx при помощи модуля url:

```
$ ansible -m uri -a 'url="http://127.0.0.1/status/200"' vm2
```

Теперь отменим все наши изменения:

```
$ ansible -b -m systemd_service -a 'name=nginx.service enabled=false state=stopped' vm2
$ ansible -b -m apt -a 'name=nginx state=absent' vm2
$ ansible -b -m file -a 'path=/etc/nginx state=absent' vm2
```

Здесь мы использовали модуль file, который используется для работы с файлами и директориями на целевых хостах. С его помощью мы будем изменять атрибуты файлов, создавать директории, создавать пустые папки, удалять файлы и директории.

Плейбуки

Заметим, что при помощи последовательного вызова консольных команд сложно построить какой-либо сценарий автоматизации. Поэтому для для написания сценариев в Ansible используются плеи — последовательности задач, запускаемые на конкретном наборе целей, которые группируются в плейбуки. Написать один плей в Ansible нельзя, поэтому создадим плейбук nginx\_simple.play.yml, повторяющий ручные действия:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: nginx
        update_cache: true
        state: present
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Заметим, что в корне файла находится список плеев (в нашем случае из одного элемента) и каждый плей содержит имя (name), набор целей (hosts) и список задач (tasks). Также указан опциональный параметр become, аналогичный опции -b, чтобы модули выполнялись из-под суперпользователя.  
  
В отличие от ручного запуска модулей настоятельно рекомендуется давать всем задачам и плеям понятные имена, чтобы лог действий Ansible был проще и понятнее.  
Запустим наш плейбук при помощи команды ansible-playbook:

```
$ ansible-playbook nginx_simple.play.yml
```

Параметризуем наш плей, вынеся пути копируемого файла в переменные:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__config_src: nginx.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install nginx package
      ansible.builtin.apt:
        name: nginx
        update_cache: true
        state: present
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Теперь вместо конкретных путей к файлу в задаче Copy config используется шаблон (обратите внимание на {\{ и }\}) внутри которого подставляется значение переменных nginx\_\_config\_src и nginx\_\_config\_dest.  
  
Здесь вместо переменных, указанных напрямую в плее, могут использоваться переменные инвентаря и переменные заданные при запуске команды ansible-playbook аргументом -e. Следовательно мы можем использовать другую конфигурацию, переопределив переменную в инвентаре или командной строке.

Обратите внимание на длинные названия переменных: в Ansible все переменные глобальны, поэтому не используйте простые имена как i, src, dest, target и т. п. Наличие одинаковых переменных в нескольких источниках (переменных роли, плейбука, инвентаря) приведет к их перетиранию и отладочным сессиям, где вы будете выяснять какое именно значение переменной используется при запуске и откуда оно берется.

Ansible использует шаблоны для реализации подстановки значений переменных и любых вычислений во время работы сценария. При помощи шаблонов мы будем, например, запускать задачи только на хостах с определенной конфигурацией или создавать конфиги, зависящие от переменных инвентаря.  
  
В качестве языка шаблонов Ansible использует [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/), который может быть знаком Python разработчикам, т.к. он широко используется в Web фреймворках, таких как Django и Flask для генерации HTML на стороне сервера. Мы обсудим Jinja2 далее, сейчас же рассмотрим основные приемы написания плейбуков.  
  
Заметим, что при повторных запусках плейбука задача Reload Nginx service всегда имеет статус changed как будто он создает изменения. Несложно заметить, что никаких изменений задача не производит, а лишь вынуждает Nginx бесцельно перечитывать свой конфиг. Такие задачи в Ansible называют неидемпотентными, т.к. они не изменяют видимое состояние цели (или Ansible не может отследить это изменение).  
  
Появление таких задач — следствие того, что Ansible не использует для никаких внутренних механизмов для отслеживания состояния целей и возлагает на разработчиков обязанность писать идемпотентные сценарии, т. е. такие сценарии которые переводят цель из одного отслеживаемого состояния в другое такое состояние.  
  
Ключевое свойство идемпотентных сценариев — при повторном запуске сценарий не сделает никаких изменений. Писать неидемпотентный код на Ansible очень просто, например использование модулей command и shell, запускающих произвольные команды, неидемпотентно, т.к. Ansible не может отследить что именно изменили эти команды (и изменили ли вообще).  
  
Исправим неидемпотентность нашего плея: запустим плейбук, включив более подробный вывод (-v) и заметим, что все задачи после запуска выводят какой-то JSON документ — это результат выполнения задачи. Он зависит от модуля, но содержит несколько общих параметров, например статус задачи.  
  
Мы можем записать результат выполнения задачи в переменную Ansible при помощи директивы register. Сохраним результат задачи Copy config, чтобы запускать Reload Nginx service только тогда, когда Copy config выполнила изменения:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__config_src: nginx.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: nginx
        update_cache: true
        state: present
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
      register: __copy_config
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Теперь добавим условие запуска для задачи Reload Nginx service при помощи директивы when -- она принимает как аргумент выражение Jinja2 без скобок ({\{ и }\}), которое должно возвращать true или false.  
  
Наш случай очень прост, т.к. для него в Ansible предусмотрен Jinja2 тест changed. Тесты Jinja2 — это функции, принимающие один аргумент и возвращающие true или false, они вызываются так — ARG is TEST\_NAME и используются для проверки условий.  
  
Добавим when к задаче Reload Nginx service:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__config_src: nginx.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: nginx
        update_cache: true
        state: present
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
      register: __copy_config
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
      when: __copy_config is changed
```

Список тестов Jinja2 смотри в [документации](https://jinja.palletsprojects.com/en/3.0.x/templates/#list-of-builtin-tests), также Ansible определяет свои тесты, такие как changed — [документация](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_tests.html).

Перезапустим плейбук и обратим внимание, что задача Reload Nginx service завершилась со статусом skipped — это статус для задач, пропущенных из-за невыполненного условия when.  
  
Вы можете подумать, что это довольно неуклюжее решение для такой простой проблемы и будете абсолютно правы. Для решения этой проблемы Ansible опрелеляет хендлеры (handlers) —- задачи, запускаемые при изменении в других задачах.  
  
Перенесем задачу Reload Nginx service в секцию handlers плея:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__config_src: nginx.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: nginx
        update_cache: true
        state: present
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
  handlers:
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Мы вынесли задачу Reload Nginx service в отдельный список handlers. Задачи в этом списке независимы и не запускаются последовательно. Вместо этого они запускаются в конце выполнения плея в случае, если они были запрошены одной из основных задач.  
  
Запрос выполняется директивой notify, которая принимает как аргумент имя одного или нескольких хендлеров.  
Изменим конфиг Nginx, добавив комментарий:

```
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;
 
events {
  worker_connections 768;
}
 
http {
  sendfile on;
  tcp_nopush on;
  types_hash_max_size 2048;
 
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
 
  access_log /var/log/nginx/access.log;
  error_log /var/log/nginx/error.log;
 
  gzip on;
 
  server {
    listen 80 default_server;
 
    # Proxy to httpbin.org
    location / {
      proxy_pass https://httpbin.org;
    }
  }
}
```

Перезапустим плейбук:

```
$ ansible-playbook nginx_simple.play.yml
```

Обратите внимание на появившуюся секцию RUNNING HANDLER в выводе ansible-playbook. Запустим плейбук еще раз и заметим, что хендлеры не запустились, т.к. Copy config ничего не изменила.  
  
Также добавим хендлер к задаче Install nginx package, чтобы перезапускать Nginx при обновлении:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__config_src: nginx.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: nginx
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
  handlers:
    - name: Restart Nginx
      ansible.builtin.systemd_service:
        name: nginx.service
        state: restarted
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Приглядимся внимательнее к задаче Install nginx package: как вообще обновить Nginx при помощи этой задачи? Ее параметры говорят, что задача устанавливает Nginx какой-либо версии и если Nginx уже установлен, то ее запуск не создаст изменений.  
Следовательно, после первой установки такой плейбук никогда не обновит Nginx и со временем его использование приведет к дрейфу конфигураций (configuration drift) — ситуации, когда фактическое состояние однотипных целей (настраиваемых при помощи одинаковых сценариев с одинаковым набором переменных) отличается.  
  
В нашей ситуации дрейф наступает при настройке второго хоста через несколько месяцев, после выхода следующего релиза Nginx. На практике дрейф неизбежен и наша задача как разработчиков сценариев автоматизации -- минимизировать его.  
  
Как это сделать здесь? Документация модуля apt говорит о параметре state: latest, который вынудит задачу Install nginx package обновлять Nginx до последней версии при запуске. Такое решение частично решит проблему, но снова сделает плей неидемпотентным, что также нас не устраивает. Фиксация версии пакета в переменной решает обе проблемы:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__version: "1.18.0*"
    nginx__config_src: nginx.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version }\}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
  handlers:
    - name: Restart Nginx
      ansible.builtin.systemd_service:
        name: nginx.service
        state: restarted
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Теперь, чтобы обновить Nginx, нужно обновить версию пакета в плейбуке, что сделает изменение явным. Но фиксация версий всех пакетов хоста и их регулярное обновление — трудоемкая задача, поэтому помните, что лучшее — враг хорошего, и фиксируйте действительно важные для системы параметры.  
\[Версия пакета PostgreSQL на серверах БД должна быть зафиксирована, но, например, службу NetworkManager можно обновлять произвольно.\]  
  
Сейчас мы предполагаем, что конфиг, передаваемый в Copy config корректен, но это часто не так. Текущая реализация, получив некорректный конфиг, заменит старый конфиг и либо уронит Nginx, либо Nginx напишет в лог предупреждение и не заменит конфиг, что вызовет падение при следующем перезапуске Nginx в будущем.  
  
К счастью, Nginx умеет валидировать свои конфиги командой nginx -t -c ABSOLULE\_PATH\_TO\_CONFIG. Модифицируем наш плейбук так, чтобы валидировать конфиг перед обновлением:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__version: "1.18.0"
    nginx__config_src: nginx.conf
    nginx__config_temp: /etc/nginx/nginx.new.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version }\}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_temp }\}"
        owner: root
        group: root
        mode: "644"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t -c '{\{ nginx__config_temp }\}'"
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_temp }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
        remote_src: true
      notify:
        - Reload Nginx service
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
  handlers:
    - name: Restart Nginx
      ansible.builtin.systemd_service:
        name: nginx.service
        state: restarted
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

Здесь мы использовали модуль command, чтобы выполнить произвольную команду на цели и снова сделали плейбук неидемпотентным, т.к. Ansible не знает изменил ли что-либо запуск команды на хосте. Мы же знаем, что эта команда ничего не изменяет.  
  
Чтобы задать это явно используется директива changed\_when, которая принимает выражение Jinja2, возвращающее true, когда команда сделала изменения и false иначе (для вычисления этого выражения часто используют результат выполнения модуля). В нашем случае команда никогда не приводит к изменениям, напишем в условии false:

```
- name: Install Nginx on vm2
  hosts: vm2
  become: true
  vars:
    nginx__version: "1.18.0"
    nginx__config_src: nginx.conf
    nginx__config_temp: /etc/nginx/nginx.new.conf
    nginx__config_dest: /etc/nginx/nginx.conf
  tasks:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version }\}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ nginx__config_temp }\}"
        owner: root
        group: root
        mode: "644"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t -c '{\{ nginx__config_temp }\}'"
      changed_when: false
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ nginx__config_temp }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
        remote_src: true
      notify:
        - Reload Nginx service
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
  handlers:
    - name: Restart Nginx
      ansible.builtin.systemd_service:
        name: nginx.service
        state: restarted
    - name: Reload Nginx service
      ansible.builtin.systemd_service:
        name: nginx.service
        state: reloaded
```

На этом закончим доработки нашего плея.

Роли

Несложно представить, что нам потребуется использовать этот сценарий в нескольких инвентарях или на нескольких независимых целях в одном. Для таких случаев в Ansible предусмотрены роли (roles) — именованные группы задач, у которых явно объявлены входные параметры.  
  
Создадим в рабочей области папку для будущих ролей:

```
$ mkdir -p roles
```

Теперь создадим новую роль при помощи утилиты ansible-galaxy:

```
$ ansible-galaxy init ./roles/nginx
```

Роли Ansible состоят из нескольких компонентов, организованных в фиксированную структуру папок:

```
$ tree ./roles/nginx
./roles/nginx
├── defaults
│   └── main.yml
├── files
├── handlers
│   └── main.yml
├── meta
│   └── main.yml
├── tasks
│   └── main.yml
├── templates
├── tests
│   ├── inventory
│   └── test.yml
├── vars
│   └── main.yml
└── README.md
```

defaults — значения по умолчанию для параметров роли; здесь описываются все переменные, которые может переопределить пользователь роли;  
files — статичные файлы (чаще всего для копирования на цели);  
handlers — хендлеры роли;  
meta — метаданные для публикации в репозитории Ansible ролей;  
tasks — задачи роли;  
templates — шаблонизированные файлы (чаще всего для копирования на хосты параметризованных конфигов);  
tests — тесты роли;  
vars — внутренние переменные роли, которые не должны переопределяться пользователем;  
[README.md](http://readme.md/) — описание роли.

Подробнее смотри в [документации](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html#role-directory-structure).

Мы не будем сегодня рассматривать публикацию ролей и их тестирование, поэтому удалим эти директории (здесь и далее все команды выполняются из папки с ролью):

```
$ rm -rf ./tests ./meta
```

Структура репозитория

```
$ tree .
.
├── inventories
│   └── main
│       ├── group_vars
│       ├── host_vars
│       └── hosts.yaml
├── roles
│   └── nginx
├── ansible.cfg
├── nginx_simple.play.yml
└── README.md
```

Он отличается от текущего тем, что инвентари вынесены в отдельные папки (main) в папке inventories. Изменим инвентарь:

```
$ mkdir -p inventories/main/{group_vars,host_vars}
$ mv hosts.yaml inventories/main/hosts.yaml
```

Также изменим путь к инвентарю по-умолчанию в ansible.cfg:

```
[defaults]
host_key_checking = false
inventory = inventories/main
```

Подробнее о структуре репозитория смотри в [документации](https://docs.ansible.com/ansible/latest/tips_tricks/sample_setup.html#alternative-directory-layout).

Установка Nginx в виде роли

Приступим к написанию роли Nginx. Для начала перенесем плейбук в роль без изменений. Скопируем параметры в defaults/main.yml:

```
nginx__version: "1.18.0"
nginx__config_src: nginx.conf
nginx__config_temp: /etc/nginx/nginx.new.conf
nginx__config_dest: /etc/nginx/nginx.conf
```

Вынесем переменную nginx\_\_config\_temp, т.к. это деталь реализации, которую пользователь может проигнорировать. Перенесем ее в vars/main.yml, переименовав в \_\_config\_temp:

```
__config_temp: "/etc/nginx/nginx.conf.new"
```

Мы продолжаем давать переменным странные имена из-за того, что в Ansible все переменные глобальны и пересечение имен переменных приведет к сложным при отладке ошибкам.

Скопируем задачи в tasks/main.yml:

```
- name: Install Nginx package
  ansible.builtin.apt:
    name: "nginx={\{ nginx__version }\}"
    update_cache: true
    state: present
  notify:
    - Restart Nginx
- name: Copy new config
  ansible.builtin.copy:
    src: "{\{ nginx__config_src }\}"
    dest: "{\{ __config_temp }\}"
    owner: root
    group: root
    mode: "644"
- name: Validate new config
  ansible.builtin.command:
    cmd: "nginx -t -c '{\{ __config_temp }\}'"
  changed_when: false
- name: Copy config
  ansible.builtin.copy:
    src: "{\{ __config_temp }\}"
    dest: "{\{ nginx__config_dest }\}"
    owner: root
    group: root
    mode: "644"
    remote_src: true
  notify:
    - Reload Nginx service
- name: Enable Nginx service now
  ansible.builtin.systemd_service:
    name: nginx.service
    enabled: true
    state: started
```

Заметим, что теперь нам негде указать become: true, т.к. раньше мы делали это в параметрах плея. Мы можем указать этот параметр в каждой задаче, но это довольно громоздко.  
  
Для вынесения общих параметров группы задач в Ansible используется специальный модуль block — он принимает на вход группу задач и применяет к ним свои директивы:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version }\}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ __config_temp }\}"
        owner: root
        group: root
        mode: "644"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t -c '{\{ __config_temp }\}'"
      changed_when: false
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ __config_temp }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
        remote_src: true
      notify:
        - Reload Nginx service
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
```

К блокам можно применить почти все параметры задач, например when, чтобы выполнить группу задач по условию.  
  
Также блоки можно использовать как аналог try-catch для обработки ошибок при помощи директив always и rescue — они принимают на вход список задач, которые выполняются после блока либо всегда (независимо от того, возникла ли ошибка в одной из задач модуля), либо при ошибке в одной из задач.  
  
Добавим удаление временного конфига ({\{ \_\_config\_temp }\}) при ошибке:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version }\}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: "{\{ nginx__config_src }\}"
        dest: "{\{ __config_temp }\}"
        owner: root
        group: root
        mode: "644"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t -c '{\{ __config_temp }\}'"
      changed_when: false
    - name: Copy config
      ansible.builtin.copy:
        src: "{\{ __config_temp }\}"
        dest: "{\{ nginx__config_dest }\}"
        owner: root
        group: root
        mode: "644"
        remote_src: true
      notify:
        - Reload Nginx service
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
  rescue:
    - name: Remove new config on error
      file:
        path: "{\{ __config_temp }\}"
        state: absent
```

Скопируем хендлеры в handlers/main.yml:

```
- name: Restart Nginx
  ansible.builtin.systemd_service:
    name: nginx.service
    state: restarted
- name: Reload Nginx service
  ansible.builtin.systemd_service:
    name: nginx.service
    state: reloaded
```

Столкнемся с проблемой, аналогичной задачам: негде указать become: true. Но в отличие от задач мы не можем объединять хендлеры в блоки, т.к. каждый хендлер — независимая задача. Напишем become: true явно в каждом:

```
- name: Restart Nginx
  ansible.builtin.systemd_service:
    name: nginx.service
    state: restarted
  become: true
- name: Reload Nginx service
  ansible.builtin.systemd_service:
    name: nginx.service
    state: reloaded
  become: true
```

Мы переделали наш плей в роль, заменим задачи в плейбуке nginx\_simple.play.yml на вызов роли:

```
- name: Install Nginx on vm2
  hosts: vm2
  roles:
    - nginx
```

Наша роль подойдет для настройки Nginx в качестве простой TCP прокси, но Nginx чаще используют для сложных сценариев L7 балансировки, когда за прокси скрывается множество HTTP сервисов. Пользователю роли в таком случае придется написать полный конфиг руками, что не очень удобно и чревато ошибками.  
  
На следующем занятии переработаем роль для установки Nginx как L7 балансировщика.

Домашнее задание

Напишите роль для установки PostgreSQL и плейбук, устанавливающий СУБД на ВМ2.  
  
Роль должна выполнять следующие операции:  
 

1.  Установку пакета PostgreSQL из стандартных репозиториев Ubuntu (подключать deb-репозитории PostgreSQL не нужно);
2.  Настройку директорий с данными PostgreSQL (роль должна принимать директорию с данными как параметр, значение по-умолчанию -- /data/postgres/data);
3.  Первичную инициализацию БД при помощи команды pg\_ctl initdb -D $PGDATA;
4.  Конфигурация PostgreSQL при помощи файла $PGDATA/postgresql.conf (роль должна принимать параметры конфигурации PostgreSQL в виде словаря);
5.  Конфигурация параметров авторизации при помощи файла $PGDATA/pg\_hba.conf (роль должна принимать последовательность правил авторизации в виде списка словарей);
6.  Запуск PostgreSQL как systemd-службы;
7.  Проверку работоспособности PostgreSQL при помощи выполнения в СУБД запроса SELECT 1;
8.  Создание пользовательских БД;
9.  Создание пользователей;
10.  Установку [postgres-exporter](https://github.com/prometheus-community/postgres_exporter) на цели;
11.  Запуск postgres-exporter как systemd-службы;

  
Для проверки предоставьте:  
  
 

*   Ссылку на исходный код роли в репозитории оформленном в соответствии структуры из занятия 3;
*   Ссылку на исходный код плейбука в том же репозитории;

Пояснения

Права директорий PostgreSQL  
В пункте 2 убедитесь, что создаете папку /data с владельцем root: root и правами 0755, чтобы избежать ограничений доступа при просмотре корня файловой системы. Директорию /data/postgres создавайте с владельцем postgres: postgres и правами 0700.  
  
Директива creates для отслеживания изменений в модулях command и shell  
В третьей практике мы обсуждали один из способов выполнить модули command и shell идемпотентно — задать условие changed\_when вручную. Во втором пункте такое решение неоптимально, т.к. оно полагается на парсинг вывода команды pg\_ctl initdb.  
  
Вместо него используйте директиву creates, которая принимает как аргумент путь на цели и считает, что указанный модуль должен создать этот путь. Т. е. задача считается changed, если до запуска этого пути не было, а после -- появился. Если же путь существовал до запуска, то задача пропускается со статусом ok.  
  
Пример:

```
- name: Create directory via command
  ansible.builtin.command:
    cmd: mkdir /data
  creates: /data
```

Не делайте так, используйте модуль file со state: directory.

Сохранение значений по умолчанию   
в конфиге PostgreSQL

Обратите внимание, что initdb создает непустой конфиг postgresql. conf и вам нужно позаботиться о сохранении значений по-умолчанию. Вы можете подойти к этой задаче двумя способами:  
  
 

1.  Генерация полного конфига при помощи [template](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/template_module.html). Значения по-умолчанию подставляются из приватных переменных роли путем слияния с пользовательскими параметрами;
2.  Точечная замена конфигурационных опций при помощи модуля [lineinfile](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/lineinfile_module.html);

  
Первый способ выглядит так:  
Объявляем пользовательские переменные в defaults/main.yml:

```
postgres__opts:
  param1: value1
  param2: value2
```

И параметры по-умолчанию в vars/main.yml (скопируйте их из сгенерированного конфига):

```
__opts_default:
  param1: value1_default
  param3: value3_default
```

Затем сливаем их при помощи фильтра [combine](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/combine_filter.html) в шаблоне templates/postgresql.conf.j2:

```
{\% set opts = __opts_default | combine(postgres__opts) \%}
```

И копируем конфиг при помощи модуля [template](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/template_module.html).  
Во втором способе будем использовать модуль [lineinfile](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/lineinfile_module.html), который использует регулярное выражение, чтобы найти строку с нашей опцией и заменить ее на пользовательское значение.  
Аналогично объявим пользовательские переменные в defaults/main.yml:

```
postgres__opts:
  param1: value1
  param2: value2
```

Теперь напишем цикл по параметрам с поиском каждого из них:

```
- name: Edit postgresql.conf
  ansible.builtin.lineinfile:
    path: "{\{ postgres__data_dir }\}/postgresql.conf"
    regexp: "^#?{\{ item.key | regex_escape() }\}\s*="
    line: "{\{ item.key }\} = {\{ item.value }\}"
    create: false
  loop: "{\{ postgres__opts | dict2items }\}"
  loop_control:
    label: "{\{ item.key }\}"
```

Здесь мы использовали следующие фильтры:  
  
 

*   dict2items — конвертирует словарь в список словарей с ключами key и value, нужен для использования словарей как параметров циклов;
*   regex\_escape () — экранирование спец-символов регулярных выражений в строке, нужно чтобы все символы в item. key воспринимались буквально.

Коллекция community.postrgesql

Для выполнения пунктов 5, 7, 8, 9 можете воспользоваться коллекцией community.postgresql, установку которой обсудили на пятой практике. Обратите внимание, что коллекция требует установки на цели Python пакета psycopg2. Установите его в первом пункте вместе с пакетами PostgreSQL, если планируете использовать. Название пакета в дистрибутиве Ubuntu: python3-psycopg2.

Значения по умолчанию   
в модулях community.postgresql

Довольно часто мы предоставляем в ролях интерфейсы к модулям со своими значениями по-умолчанию. Чтобы не дублировать эти значения в фильтре default так:

```
- name: Create Databases
  community.postgresql.postgresql_db:
    name: "{\{ item.name }\}"
    encoding: "{\{ item.encoding | default('') }\}"
    state: "{\{ item.state | default('present') }\}"
  loop: "{\{ postgres__databases }\}"
```

используйте специальную константу [omit](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_filters.html#making-variables-optional) — если эта константа является результатом шаблона в параметре модуля, то Ansible игнорирует этот параметр будто он не был написан вовсе.  
  
Получим:

```
- name: Create Databases
  community.postgresql.postgresql_db:
    name: "{\{ item.name }\}"
    encoding: "{\{ item.encoding | default(omit) }\}"
    state: "{\{ item.state | default(omit) }\}"
  loop: "{\{ postgres__databases }\}"
```

Таким образом, если элементом цикла будет {"name": «database"}, то после подстановки шаблона получим такую задачу:

```
- name: Create Databases
  community.postgresql.postgresql_db:
    name: "database"
```