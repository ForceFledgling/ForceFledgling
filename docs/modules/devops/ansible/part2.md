Продолжим изучать конструкции Ansible на примере настройки Nginx.   
На прошлом занятии мы написали простую роль, которая:  
 

1.  устанавливает Nginx;
2.  копирует статичную конфигурацию из файла;
3.  валидирует ее;
4.  запускает systemd службу Nginx.

Сегодня мы модифицируем эту роль так, чтобы конфигурировать Nginx как L7 балансировщик.

Конфигурация L7 балансировки

Добавим возможность настраивать L7 балансировку: добавим в роль переменную с конфигурацией Nginx для HTTP проксирования.  
  
Отредактируем defaults/main.yml:

```
nginx__version: "1.18.0"
nginx__config_src: nginx.conf
nginx__config_dest: /etc/nginx/nginx.conf
nginx__http_config:
  - name: httpbin.org
    port: 80
    vhost: httpbin.org
    locations:
      "/":
        - proxy_pass https://httpbin.org
  - name: google.com
    port: 80
    vhost: google.com
    locations:
      "/":
        - proxy_pass https://google.com
```

Теперь мы будем генерировать конфигурации Nginx из переменной nginx\_\_http\_config. Каждый элемент списка nginx\_\_http\_config — конфигурация виртуального сервера, для которой мы будем создавать отдельный конфиг в /etc/nginx/conf.d.  
  
Для этого внесем основную конфигурацию Nginx внутрь роли и уберем переменную nginx\_\_config\_src, вместо того чтобы принимать ее от пользователя. Также уберем переменную nginx\_\_config\_dest, т.к. Nginx читает конфигурацию из одного места.  
  
Получим такой файл defaults/main.yml:

```
nginx__version: "1.18.0"
nginx__http_config:
  - name: httpbin.org
    port: 80
    vhost: httpbin.org
    locations:
      "/":
        - proxy_pass https://httpbin.org
  - name: google.com
    port: 80
    vhost: google.com
    locations:
      "/":
        - proxy_pass https://google.com
```

Перенесем конфигурацию из плейбука в files/nginx.conf:

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
 
  include /etc/nginx/conf.d/*.conf;  # <- Заменили статичную конфигурацию на включение
}
```

И заменим задачи в tasks/main.yml (на время уберем валидацию, чтобы не усложнять задачи):

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
```

Если в модуле copy указать имя файла вместо пути, то Ansible будет искать файл в нескольких папках из своей конфигурации (аналогично $PATH), files/ — один из таких путей.

Теперь добавим задачу, копирующую конфигурацию виртуальных серверов. Создадим отдельный файл конфигурации для каждого сервера. Чтобы запустить несколько однотипных задач Ansible использует директиву loop — цикл, она принимает на вход список и запускает задачу для каждого его элемента:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Copy Virtual Server config
      ansible.builtin.debug:  # <- Плейсхолдер
        var: item
      loop: "{\{ nginx__http_config \}}"
      notify:
        - Reload Nginx service
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
```

Внутри цикла доступна переменная item, которая хранит значение текущего элемента в цикле. Остается сгенерировать из этой переменной конфигурацию виртуального сервера и скопировать ее на сервер. Для этого в Ansible используется модуль template — он получает на вход файл с шаблоном Jinja2, подставляет в него параметры и копирует на целевой хост:

```
- name: Copy Virtual Server config
  ansible.builtin.template:
    src: http_vhost.conf.j2
    dest: "/etc/nginx/conf.d/{\{ item.name \}}.conf"
    mode: "644"
    owner: root
    group: root
  loop: "{\{ nginx__http_config \}}"
  notify:
    - Reload Nginx service
```

Аналогично copy модуль template, если указать в src имя файла вместо пути, то Ansible будет искать файл с шаблоном в папке templates/ роли.

Шаблонный конфиг

Создадим шаблон templates/http\_vhost.conf.j2 с конфигурацией виртуального сервиса:

```
{\{ ansible_managed | comment \}}
 
server {
  listen {\{ item.port | default(80) | int \}};
  server_name {\{ item.vhost \}};
 
{\% for pattern, options in item.locations.items() \%}
  location {\{ pattern \}} {
{\% for opt in options \%}
    {\{ opt \}};
{\% endfor \%}
  }
{\% endfor \%}
}
```

Рассмотрим шаблон детальнее: блоки {\{ … \}} означают подстановку значения переменной, {\% … \%} - блоки управляющих конструкций, в них можно объявлять переменные, условия и циклы.  
  
Выражения A | B обозначают _Jinja2 фильтры_, такая запись эквивалентна вызову функции B (A) и нужна для улучшения читаемости цепочки вызовов и передачи дополнительных параметров.  
  
Цепочка item. port | default (80) | int означает:  
 

1.  получить значение переменной item. port;
2.  если такой переменной не существует, то заменить значение на 80;
3.  привести значение переменной к целочисленному типу;

В классической записи вызова функций такая цепочка выглядит так: int (default (80)(item.port)), что обращает порядок операций и усложняет чтение.

Несмотря на то, что запись A | B эквивалента вызову функции с одним параметром, _функции_ и _фильтры_в Jinja2 — различные сущности. Фильтры, доступные в Ansible смотри в [документации Jinja2](https://jinja.palletsprojects.com/en/3.0.x/templates/#list-of-builtin-filters) и [документации Ansible](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_filters.html).

Фильтр {\{ ansible\_managed | comment \}} — стандартный способ отметить тот факт, что конфиг был сгенерирован автоматически при помощи Ansible, старайтесь всегда использовать его. Это не всегда возможно, т.к. некоторые конфигурационные форматы не поддерживают комментарии.

Jinja2 написана на Python и поддерживает вызов методов Python на своих объектах: item.locations.items () — пример такого вызова (см. документацию [Python](https://docs.python.org/3/library/stdtypes.html#dict.items)).  
  
Добавим возможность настраивать виртуальные сервера с TLS:

```
{\{ ansible_managed | comment \}}
 
{\% if item.tls is defined and item.tls.enabled and item.tls.insecure_port \%}
server {
  server_name {\{ item.vhost \}};
  listen {\{ item.tls.insecure_port | default(80) | int \}};
  return 301 https://$host$request_uri;
}
{\% endif \%}
 
server {
  server_name {\{ item.vhost \}};
{\% if item.tls is defined and item.tls.enabled \%}
  listen {\{ item.port | default(443) | int \}} ssl http2;
 
  ssl_certificate           {\{ '{}/{}.crt'.format(__ssl_path, item.name) \}};
  ssl_certificate_key       {\{ '{}/{}.key'.format(__ssl_path, item.name) \}};
  ssl_session_cache         shared:SSL:1m;
  ssl_session_timeout       10m;
  ssl_prefer_server_ciphers on;
{\% else \%}
  listen {\{ item.port | default(80) | int \}};
{\% endif \%}
 
{\% for pattern, options in item.locations.items() \%}
  location {\{ pattern \}} {
{\% for opt in options \%}
    {\{ opt \}};
{\% endfor \%}
  }
{\% endfor \%}
}
```

Здесь мы добавили настройки для SSL с использованием условий {\% if PREDICATE \%} STATEMENT {\% endif \%} и вызова метода [str.format](https://docs.python.org/3/library/stdtypes.html#str.format) — '{}/{}.crt'.format (\_\_ssl\_path, [item.name](http://item.name/)).  
  
Зададим значение переменной \_\_ssl\_path в vars/main.yml:

```
__config_temp: "/etc/nginx/nginx.conf.new"
__ssl_path: /etc/nginx/ssl
```

И изменим формат конфигурации виртуального сервера в defaults/main.yml:

```
nginx__version: "1.18.0"
nginx__http_config:
  - name: httpbin.org
    port: 443
    vhost: httpbin.org
    tls:
      enabled: true
      insecure_port: 80
      crt: |-
        SSL CERTIFICATE
      key: |-
        SSL KEY
    locations:
      "/":
        - proxy_pass https://httpbin.org
  - name: google.com
    port: 80
    vhost: google.com
    tls:
      enabled: false
    locations:
      "/":
        - proxy_pass https://google.com
```

Валидация

Мы получили довольно сложную конфигурацию для виртуального сервера. Следует добавить валидацию входных параметров. Мы можем сделать это двумя способами — ручные проверки при помощи [ansible.builtin.assert](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/assert_module.html) и валидация при помощи [ansible.utils.validate](https://docs.ansible.com/ansible/latest/collections/ansible/utils/validate_module.html).  
  
Напишем ручные проверки:

```
- name: Check Virtual Server config
  ansible.builtin.assert:
    that:
      - item.name is string
      - item.name | length > 0
      - (item.port | default(80)) is integer
      # еще миллион проверок на каждый аттрибут...
```

В этом случае ручные проверки довольно громоздки. Заменим их на проверку при помощи [JsonSchema](https://json-schema.org/). Для начала напишем схему в переменной \_\_vhost\_schema:

```
__config_temp: "/etc/nginx/nginx.conf.new"
__ssl_path: /etc/nginx/ssl
__vhost_schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  title: HTTP Virtual Server
  type: object
  required: [name, vhost, location]
  additionalProperties: false
  properties:
    name:
      type: string
    port:
      $ref: "#/$defs/port"
    vhost:
      type: string
    tls:
      type: object
      additionalProperties: false
      properties:
        enabled:
          type: boolean
      if:
        properties:
          enabled:
            const: true
      then:
        required: [crt_path, key_path]
        properties:
          insecure_port:
            $ref: "#/$defs/port"
          crt:
            type: string
          key:
            type: string
    location:
      type: object
      additionalProperties:
        type: array
        items:
          type: string
  $defs:
    port:
      type: integer
      exclusiveMinimum: 0
      exclusiveMaximum: 65536
```

Теперь напишем задачу валидации:

```
- name: Check Virtual Server config
  ansible.utils.validate:
    data: "{\{ item \}}"
    criteria:
      - "{\{ __vhost_schema \}}"
    engine: ansible.utils.jsonschema
```

Установите пакет Python jsonschema на Ansible-контроллер pip install --user jsonschema, чтобы модуль ansible.utils.validate заработал.

Также нам понадобится задача для копирования SSL сертификата и ключа для каждого виртуального сервера:

```
- name: Copy SSL Files
  ansible.builtin.copy:
    content: "{\{ in_item.content \}}"
    dest: "{\{ in_item.dest \}}"
    mode: "0700"
    owner: root
    group: root
  loop:
    - content: "{\{ item.tls.crt \}}"
      dest: "{\{ '{}/{}.crt'.format(__ssl_path, item.name) \}}"
    - content: "{\{ item.tls.key \}}"
      dest: "{\{ '{}/{}.key'.format(__ssl_path, item.name) \}}"
  when: item.tls is defined
  loop_control:
    loop_var: in_item
  no_log: true
  notify:
    - Reload Nginx service
```

Директива content в copy означает что мы не копируем файл с Ansible-контроллера, а сохраняем содержимое строки content в файл dest на цели.

Директива no\_log: true говорит Ansible скрыть возвращаемое значение модуля из лога. Здесь это нужно, чтобы не печатать в лог ключи шифрования.

Как интегрировать эти задачи в нашу роль? Если мы заменим задачу копирования шаблона на block, то увидим ошибку, что block не поддерживает циклы. Чтобы реализовать цикл из нескольких задач воспользуемся модулем динамического включения задач include\_tasks.  
  
Напишем файл с задачами tasks/http\_vhost.yml, содержащий задачи для настройки одного виртуального сервера:

```
- name: Check Virtual Server config
  ansible.utils.validate:
    data: "{\{ item \}}"
    criteria:
      - "{\{ __vhost_schema \}}"
    engine: ansible.utils.jsonschema
- name: Copy SSL Files
  ansible.builtin.copy:
    content: "{\{ item.content \}}"
    dest: "{\{ item.dest \}}"
    mode: "0700"
    owner: root
    group: root
  loop:
    - content: "{\{ item.tls.crt \}}"
      dest: "{\{ '{}/{}.crt'.format(__ssl_path, item.name) \}}"
    - content: "{\{ item.tls.key \}}"
      dest: "{\{ '{}/{}.key'.format(__ssl_path, item.name) \}}"
  when: item.tls is defined
  loop_control:
    loop_var: in_item 
  no_log: true
  notify:
    - Reload Nginx service
- name: Copy Virtual Server config
  ansible.builtin.template:
    src: http_vhost.conf.j2
    dest: "/etc/nginx/conf.d/{\{ item.name \}}.conf"
    mode: "644"
    owner: root
    group: root
  notify:
    - Reload Nginx service
```

И включим ее внутри цикла:

```
- name: Configure Virtual Servers
  ansible.builtin.include_tasks:
    file: http_vhost.yml
  loop: "{\{ nginx__http_config \}}"
```

Получим такие задачи в tasks/main.yml:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Copy new config
      ansible.builtin.copy:
        src: nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
```

Остается вернуть валидацию, но предыдущая схема, где мы копировали новый конфиг с другим именем, валидировали его и затем подменяли старый конфиг, не сработает из-за включений конфигов динамических серверов (т.к. в основном конфиге указана маска \*.conf).  
  
Заменим эту схему на следующую:  
 

1.  найдем все текущие конфиги и переименуем их (добавим .bak в конец);
2.  скопируем новые конфиги в стандартные локации;
3.  если валидация прошла, то удалим старые конфиги, иначе удалим новые конфиги и переименуем старые обратно.

Напишем задачи из п. 1 в отдельном файле tasks/backup\_old\_config.yml:

```
- name: Find Nginx configs
  ansible.builtin.find:
    paths:
      - /etc/nginx
      - /etc/nginx/conf.d
      - "{\{ __ssl_path \}}"
    patterns: "*.conf"
    recurse: false
  register: __find_result
- name: Extract paths
  ansible.builtin.set_fact:
    __old_configs: "{\{ __find_result.files | map(attribute='path') \}}"
- name: Backup old configs
  ansible.builtin.copy:
    src: "{\{ item \}}"
    dest: "{\{ item \}}.bak"
    remote_src: true
  loop: "{\{ __old_configs \}}"
- name: Remove old configs
  ansible.builtin.file:
    path: "{\{ item \}}"
    state: absent
  loop: "{\{ __old_configs \}}"
```

Здесь мы в первый раз столкнулись с модулем set\_fact, создающим переменную во время выполнения сценария. Такие переменные называются _фактами_ и кроме создаваемых вручную фактов Ansible определяет набор стандартных — они содержат информацию о целевых системах (версию ОС, сетевые интерфейсы, диски и т. д.) и собираются вначале каждого плея модулем setup.  
  
Полный список стандартных фактов смотри в [документации](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_vars_facts.html).

Мы не будем выносить задачи Backup old configs и Remove old configs в отдельный файл и подключать при помощи include\_tasks для простоты.

Подключим получившиеся задачи в tasks/main.yml при помощи модуля статического включения файлов import\_tasks:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Backup old config
      ansible.builtin.import_tasks: backup_old_config.yml
    - name: Copy new config
      ansible.builtin.copy:
        src: nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
```

В чем отличие import\_tasks и include\_tasks? Первый модуль подключает задачи во время _чтения сценария_, второй во время _выполнения_. Это разграничивает их возможности и сценарии выполнения.  
  
Например import\_tasks не может использоваться с циклами и условиями, значение которых неизвестно во время чтения сценария (условие, содержащее переменную роли/инвентаря сработает, а факт или результат выполнения модуля — нет).  
  
Для разбиения списка задач следует использовать import\_tasks, а для сложных циклов и задач, которые запускаются в зависимости от состояния цели — include\_tasks.

Теперь добавим валидацию конфига (п.2) и блок rescue, в котором удалим новые конфиги и вернем старые на место (п.3):

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Backup old config
      ansible.builtin.import_tasks: backup_old_config.yml
    - name: Copy new config
      ansible.builtin.copy:
        src: nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t"
      changed_when: false
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
  rescue:
    - name: Restore config
      ansible.builtin.import_tasks: restore_config.yml
```

Задачи в tasks/restore\_config.yml:

```
- name: Find Nginx configs
  ansible.builtin.find:
    paths:
      - /etc/nginx
      - /etc/nginx/conf.d
      - "{\{ __ssl_path \}}"
    patterns: "*.conf"
    recurse: false
  register: __find_result
- name: Extract paths
  ansible.builtin.set_fact:
    __new_configs: "{\{ __find_result.files | map(attribute='path') \}}"
- name: Remove new configs
  ansible.builtin.file:
    path: "{\{ item \}}"
    state: absent
  loop: "{\{ __new_configs \}}"
- name: Restore old configs
  ansible.builtin.copy:
    src: "{\{ item \}}.bak"
    dest: "{\{ item \}}"
    remote_src: true
  loop: "{\{ __old_configs \}}"
  notify:
    - Reload Nginx service
- name: Remove config backups
  ansible.builtin.file:
    path: "{\{ item \}}.bak"
    state: absent
  loop: "{\{ __old_configs \}}"
```

По-умолчанию хендлеры не запускаются при ошибке на цели, но это поведение можно переопределить опцией --force-handlers ([документация](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html#handlers-and-failure)), поэтому следует писать notify даже в задачах, обрабатывающих ошибки.

Добавим базовую проверку работоспособности сервера после запуска. Воспользуемся для этого встроенной в Nginx страницей [stub\_status](https://nginx.org/en/docs/http/ngx_http_stub_status_module.html). Вынесем эту страницу в отдельный виртуальный сервер при помощи следующего конфига:

```
server {
  listen 127.0.0.1:8080;
 
  location = /status {
    stub_status;
  }
}
```

Нам придется отказаться от захардкоженного порта, чтобы избежать конфликтов с пользовательскими виртуальными серверами.  
Вынесем порт со статус-сервером в конфигурацию роли в defaults/main.yml:

```
nginx__version: "1.18.0"
nginx__status_port: 8080  # <- новый параметр
nginx__http_config:
  - name: httpbin.org
    port: 443
    vhost: httpbin.org
    tls:
      enabled: true
      insecure_port: 80
      crt: |-
        SSL CERTIFICATE
      key: |-
        SSL KEY
    locations:
      "/":
        - proxy_pass https://httpbin.org
  - name: google.com
    port: 80
    vhost: google.com
    tls:
      enabled: false
    locations:
      "/":
        - proxy_pass https://google.com
```

И перенесем основной конфиг Nginx из files/nginx.conf в templates/nginx.conf.j2:

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
 
  # Новый блок конфигурации
  server {
    listen 127.0.0.1:{\{ nginx__status_port \}};
 
    location = /status {
      stub_status;
    }
  }
 
  include /etc/nginx/conf.d/*.conf;
}
```

Заменим модуль задачи Copy new config с copy на template:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Backup old config
      ansible.builtin.import_tasks: backup_old_config.yml
    - name: Copy new config
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t"
      changed_when: false
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
  rescue:
    - name: Restore config
      ansible.builtin.import_tasks: restore_config.yml
```

Теперь проверим работает ли Nginx, сделав запрос к http://127.0.0.1:{\{ nginx\_\_status\_port \}}/statusпри помощи модуля [url](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/uri_module.html):

```
- name: Check Nginx
  ansible.builtin.uri:
    url: "http://127.0.0.1:{\{ nginx__status_port \}}/status"
```

Заметим, что при долгом запуске Nginx такая задача упадет и провалит весь плейбук. Нам нужен аналог цикла do-while, чтобы запрашивать страницу пока она не вернется успешно.  
  
Для решения такой задачи в Ansible используется директива набор директив:  
until — условие завершения цикла;  
retries — максимальное число повторов;  
delay — задержка между повторами;  
  
Чтобы воспользоваться результатом выполнения модуля в условии until, нужно зарегистрировать результат выполнения задачи при помощи register.  
  
Напишем новую версию задачи:

```
- name: Check Nginx
  ansible.builtin.uri:
    url: "http://127.0.0.1:{\{ nginx__status_port \}}/status"
  register: __result
  until: __result.status == 200
  retries: 6
  delay: 5
```

Время ожидания задачи равно retries \* delay, таким образом мы ждем запуска Nginx 30 секунд.  
  
Директива until опциональна, если она не указана, то условие выполнения — успешность задачи. Мы можем воспользоваться этим и указать опцию status\_code модуля uri, которая отмечает HTTP статус коды, означающие успешность операции. Здесь мы укажем стандартный код 200 OK:

```
- name: Check Nginx
  ansible.builtin.uri:
    url: "http://127.0.0.1:{\{ nginx__status_port \}}/status"
    status_code: [200]
  retries: 6
  delay: 5
```

Получим следующий список задач:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Backup old config
      ansible.builtin.import_tasks: backup_old_config.yml
    - name: Copy new config
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t"
      changed_when: false
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
    - name: Flush handlers
      meta: flush_handlers
    - name: Check Nginx
      ansible.builtin.uri:
        url: "http://127.0.0.1:{\{ nginx__status_port \}}/status"
        status_code: [200]
      retries: 6
      delay: 5
  rescue:
    - name: Restore config
      ansible.builtin.import_tasks: restore_config.yml
```

Заметим, что проверка работоспособности Nginx выполняется только при успешном копировании конфига.  
  
Вынесем проверку вне блока обработки ошибок:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx package
      ansible.builtin.apt:
        name: "nginx={\{ nginx__version \}}"
        update_cache: true
        state: present
      notify:
        - Restart Nginx
    - name: Backup old config
      ansible.builtin.import_tasks: backup_old_config.yml
    - name: Copy new config
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t -c '{\{ __config_temp \}}'"
      changed_when: false
    - name: Enable Nginx service now
      ansible.builtin.systemd_service:
        name: nginx.service
        enabled: true
        state: started
  rescue:
    - name: Restore config
      ansible.builtin.import_tasks: restore_config.yml
- name: : Flush handlers
  meta: flush_handlers
- name: Check Nginx
  ansible.builtin.uri:
    url: "http://127.0.0.1:{\{ nginx__status_port \}}/status"
    status_code: [200]
  retries: 6
  delay: 5
```

Теперь вынесем блок обработки ошибок в файл tasks/install.yml и уберем из него задачи Install Nginx package и Enable Nginx service now, которые не относятся к копированию конфигурации:

```
- name: Install Nginx package
  ansible.builtin.apt:
    name: "nginx={\{ nginx__version \}}"
    update_cache: true
    state: present
  notify:
    - Restart Nginx
- name: Configure Nginx
  block:
    - name: Backup old config
      ansible.builtin.import_tasks: backup_old_config.yml
    - name: Copy new config
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "644"
      notify:
        - Reload Nginx service
    - name: Configure Virtual Servers
      ansible.builtin.include_tasks:
        file: http_vhost.yml
      loop: "{\{ nginx__http_config \}}"
    - name: Validate new config
      ansible.builtin.command:
        cmd: "nginx -t -c '{\{ __config_temp \}}'"
      changed_when: false
  rescue:
    - name: Restore config
      ansible.builtin.import_tasks: restore_config.yml
- name: Enable Nginx service now
  ansible.builtin.systemd_service:
    name: nginx.service
    enabled: true
    state: started
- name: Flush handlers
  meta: flush_handlers
- name: Check Nginx
  ansible.builtin.uri:
    url: "http://127.0.0.1:{\{ nginx__status_port \}}/status"
    status_code: [200]
  retries: 6
  delay: 5
```

Получим следующие задачи в tasks/main.yml:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx
      ansible.builtin.import_tasks: install.yml
```

Установка экспортера Prometheus

Добавим к установке сервера Nginx [экспортер](https://github.com/nginxinc/nginx-prometheus-exporter) Prometheus, для отдачи метрик в формате Prometheus.

Prometheus — популярная СУБД для хранения временных рядов, написанная для целей мониторинга. Работает по pull модели, вытягивая метрики с заданным периодом из сконфигурированных целей мониторинга.

Создадим файл tasks/exporter.yml с задачами установки экспортера:

```
$ touch tasks/exporter.yml
```

Включим его в tasks/main.yml:

```
- name: Configure Nginx
  become: true
  block:
    - name: Install Nginx
      ansible.builtin.import_tasks: install.yml
    - name: Install exporter
      ansible.builtin.import_tasks: exporter.yml
```

Теперь посмотрим что требуется сделать для установки экспортера. Он поставляется в виде архивов на странице [релизов GitHub](https://github.com/nginxinc/nginx-prometheus-exporter/releases/tag/v1.1.0). Скачаем релиз для нашей платформы (linux\_amd64) и извлечем в отдельную папку:

```
$ curl -LO https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
$ mkdir -p exporter
$ tar -C exporter -xvf ./nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
$ tree ./exporter
./exporter
├── completions
│   ├── nginx-prometheus-exporter.bash
│   └── nginx-prometheus-exporter.zsh
├── manpages
│   └── nginx-prometheus-exporter.1.gz
├── LICENSE
├── nginx-prometheus-exporter
└── README.md
```

Узнаем чем является файл ./exporter/nginx-prometheus-exporter при помощи утилиты file:

```
$ file ./exporter/nginx-prometheus-exporter
./exporter/nginx-prometheus-exporter: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, Go BuildID=Y-OzotAw31Jp9_fD_YLK/KoHx2K4NqplzuDWeyd4A/pnjHuK-zUgRS-EQgAFjv/04u9eYGmKLuFQ_DiB65J, stripped
```

Это исполняемый файл программы, написанной на Go. Обратите внимание на слова statically linked, это значит, что программа не зависит от наличия в системе каких-либо библиотек и лишь от ядра ОС. У нас довольно стандартная конфигурация Linux, поэтому с большой долей вероятности программа запустится без проблем.  
  
Проверим это, выведя справку:

```
$ ./nginx-prometheus-exporter -h
usage: nginx-prometheus-exporter [<flags>]
 
...
```

[Документация Go](https://go.dev/wiki/MinimumRequirements) говорит что для x86\_64 Linux систем минимально допустимая версия ядра -- 2.6.32. Мы можем посмотреть текущую версию ядра командой uname -r:  
$ uname -r  
6.6.0

Получим, что установка экспортера будет состоять из следующих шагов:  
 

1.  cкачать архив с экспортером на Ansible-контроллер;
2.  распаковать архив на контроллер;
3.  скопировать исполнямый файл экспортера на цели;
4.  скопировать systemd службу для запуска экспортера на цели;
5.  запустить systemd службу экспортера;

Мы могли бы скачивать экспортер напрямую на цели и упростить пункты 1−3, но в корпоративном контексте, в котором мы чаще всего запускаем Ansible, целевые хосты не имеют доступа в интернет. Также при большом числе целей мы создаем бесполезную нагрузку на сервер, содержащий файл. Мы можем перегрузить сервер-источник или упереться в ограничение на число загрузок с сервера.  
  
Как запустить задачу на контроллере вместо целевого хоста? Для таких случаев обычно используют директиву delegate\_to, которая заменяет фактический хост выполнения с целевого на хост, указанный как значение этой директивы.  
  
Получим следующую задачу загрузки файла:

```
- name: Download exporter on controller
  delegate_to: localhost
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
```

Мы воспользовались модулем [unarchive](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/unarchive_module.html), чтобы загрузить и распаковать архив в одной задаче.  
  
Заметим, что в нашем инвентаре нет цели localhost. Ansible всегда добавляет цель localhost в плеи специально для случая запуска задач на контроллере. Такая цель называется неявным локалхостом (implicit localhost). Если задать в инвентаре цель с именем localhost, то вместо неявного локалхоста будет использоваться она.  
  
Также обратим внимание, что текущая задача не решает проблему множественной загрузки экспортера, теперь мы качаем его много раз с одного хоста. Чтобы исправить это воспользуемся директивой run\_once, которая указывает, что задачу нужно выполнить один раз на _произвольной_ цели.

```
- name: Download exporter on controller
  delegate_to: localhost
  run_once: true
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
```

Предположим, что в будущем путь к экспортеру в архиве может измениться. Вместо хардкода добавим поиск исполняемого файла в папке-назначении при помощи модуля find:

```
- name: Find exporter executable
  ansible.builtin.find:
    paths: /tmp/nginx-exporter
    file_type: file
    mode: u=x
    recurse: false
  register: __result
- name: Register path to executable
  ansible.builtin.set_fact:
    __executable_file: "{\{ __result.files[0].path \}}
```

Получим такой файл tasks/exporter.yml:

```
- name: Download exporter on controller
  delegate_to: localhost
  run_once: true
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
    - name: Find exporter executable
      ansible.builtin.find:
        paths: /tmp/nginx-exporter
        file_type: file
        mode: u=x
        recurse: false
      register: __result
    - name: Register path to executable
      ansible.builtin.set_fact:
        __executable_file_local: "{\{ __result.files[0].path \}}"
```

Временно добавим в роль задачу, выводящую значение факта \_\_executable\_file и _заменим в плейбуке nginx\_simple.play.yml цели с vm2 на vm2: vm1, чтобы запустить его на двух ВМ_:

```
- name: Download exporter on controller
  delegate_to: localhost
  run_once: true
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
    - name: Find exporter executable
      ansible.builtin.find:
        paths: /tmp/nginx-exporter
        file_type: file
        mode: u=x
        recurse: false
      register: __result
    - name: Register path to executable
      ansible.builtin.set_fact:
        __executable_file_local: "{\{ __result.files[0].path \}}"
- name: Print __executable_file_local
  ansible.builtin.debug:
    var: __executable_file_local
```

Во время запуска увидим ошибку, что факт \_\_executable\_file\_local объявлен только на цели, _c которой были делегированы задачи загрузки экспортера_. Это произошло, т.к. в делегированных задачах Ansible использует набор фактов хоста, на котором задача запустилась бы без директивы delegate\_to. Чтобы использовать набор фактов хоста-делегата задайте флаг delegate\_facts.  
  
В нашем же случае эта директива не нужна, т.к. нас в принципе устраивает сохранение \_\_executable\_file\_localв набор фактов одной из целей, но не устраивает тот факт, что мы не знаем в какую конкретно цель попадет этот факт, т.к. run\_once выбирает цель произвольно.  
  
В таком случае выберем конкретную цель для запуска при помощи when вместо run\_once:

```
- name: Download exporter on controller
  delegate_to: localhost
  when: inventory_hostname == (ansible_play_hosts_all | sort | first)
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
    - name: Find exporter executable
      ansible.builtin.find:
        paths: /tmp/nginx-exporter
        file_type: file
        mode: u=x
        recurse: false
      register: __result
    - name: Register path to executable
      ansible.builtin.set_fact:
        __executable_file_local: "{\{ __result.files[0].path \}}"
- name: Print __executable_file_local
  ansible.builtin.debug:
    var: __executable_file_local
```

В условии мы воспользовались _магическими переменными Ansible_ — переменными, содержащими метаданные о запуске текущего плея/роли/задачи:  
  
 

1.  inventory\_hostname — имя текущей цели в инвентаре;
2.  ansible\_play\_hosts\_all — список всех целей текущего плея.

Остальные такие переменные смотри в [документации](https://docs.ansible.com/ansible/latest/reference_appendices/special_variables.html#special-variables).

Таким образом мы всегда будем делегировать задачу с первого хоста в алфавитном порядке.  
  
Теперь скопируем факт \_\_executable\_file\_local на остальные цели:

```
- name: Propagate fact
  ansible.builtin.set_fact:
    __executable_file: "{\{ hostvars[ansible_play_hosts_all | sort | first].__executable_file_local \}}"
```

Здесь мы воспользовались магической переменной hostvars — словарем, позволяющим получить факты произвольной цели по ее имени. Вынесем выражение ansible\_play\_hosts\_all | sort | first как приватную переменную \_\_first\_host.  
  
Получим такой vars/main.yml:

```
__config_temp: "/etc/nginx/nginx.conf.new"
__ssl_path: /etc/nginx/ssl
__first_host: "{\{ ansible_play_hosts_all | sort | first \}}"
```

И такой tasks/exporter.yml:

```
- name: Download exporter on controller
  delegate_to: localhost
  when: inventory_hostname == __first_host
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
    - name: Find exporter executable
      ansible.builtin.find:
        paths: /tmp/nginx-exporter
        file_type: file
        mode: u=x
        recurse: false
      register: __result
    - name: Register path to executable
      ansible.builtin.set_fact:
        __executable_file_local: "{\{ __result.files[0].path \}}"
- name: Propagate fact
  ansible.builtin.set_fact:
    __executable_file: "{\{ hostvars[__first_host].__executable_file_local \}}"
```

Пункты 3-5 не содержат ничего нового. Напишем их в tasks/exporter.yml:

```
- name: Download exporter on controller
  delegate_to: localhost
  when: inventory_hostname == __first_host
  block:
    - name: Create download dir
      ansible.builtin.file:
        path: /tmp/nginx-exporter
        mode: "777"
        state: directory
    - name: Download exporter
      ansible.builtin.unarchive:
        src: >-
          https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v1.1.0/nginx-prometheus-exporter_1.1.0_linux_amd64.tar.gz
        dest: /tmp/nginx-exporter
        remote_src: true
    - name: Find exporter executable
      ansible.builtin.find:
        paths: /tmp/nginx-exporter
        file_type: file
        mode: u=x
        recurse: false
      register: __result
    - name: Register path to executable
      ansible.builtin.set_fact:
        __executable_file_local: "{\{ __result.files[0].path \}}"
- name: Propagate fact
  ansible.builtin.set_fact:
    __executable_file: "{\{ hostvars[__first_host].__executable_file_local \}}"
- name: Copy exporter executable
  ansible.builtin.copy:
    src: "{\{ __executable_file \}}"
    dest: /usr/local/sbin/nginx-exporter
    mode: "755"
  notify:
    - Restart Nginx exporter
- name: Copy nginx-exporter systemd service
  ansible.builtin.template:
    src: nginx-exporter.service.j2
    dest: /etc/systemd/system/nginx-exporter.service
    mode: "644"
    owner: root
    group: root
  notify:
    - Daemon reload
    - Restart Nginx exporter
- name: Start nginx-exporter systemd service
  ansible.builtin.systemd_service:
    name: nginx-exporter.service
    enabled: true
    state: started
```

Добавим новые хендлеры в handlers/main.yml:

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
- name: Restart Nginx exporter
  ansible.builtin.systemd_service:
    name: nginx-exporter.service
    state: restarted
- name: Daemon reload
  ansible.builtin.systemd_service:
    daemon_reload: true
```

Хендлер Daemon reload нужен, чтобы systemd перечитал содержимое cлужбы после обновления файла /etc/systemd/system/nginx-exporter.service.

До этого мы не писали собственные службы systemd, покажем их содержимое на примере templates/nginx-exporter.service.j2:

```
# Общая конфигурация для всех юнитов
[Unit]
Description=Nginx Prometheus exporter
Documentation=https://github.com/nginxinc/nginx-prometheus-exporter
# Запускать этот юнит, если включем запуск Nginx
Wants=nginx.service
# Запускать этот юнит после Nginx
After=nginx.service
 
# Настройки службы
[Service]
# Служба запускает один процесс, живущий все время работы
Type=simple
# Команда для запуска службы
ExecStart=/usr/local/sbin/nginx-exporter \
  --web.listen-address=:{\{ nginx__exporter_port \}} \
  --nginx.scrape-uri=http://127.0.0.1:{\{ nginx__status_port \}}/status
# Перезапускать при выходе с ошибкой
Restart=on-failure
# Интервал перезапуска
RestartSec=15
 
# Параметры автозапуска
[Install]
# Запускать после инициализации системы, одновременно с экраном входа
WantedBy=multi-user.target
```

Мы не будем подробно рассматривать конфигурацию systemd-служб. Вы можете использовать как примеры службы, входящие в пакеты, например /usr/lib/systemd/system/nginx.service. Также вы найдете множество статей на тему, например [тут](https://linuxhandbook.com/create-systemd-services/), [тут](https://wiki.archlinux.org/title/Systemd#Writing_unit_files) или [тут](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html).

Вынесем слушающий порт экспортера ({\{ nginx\_\_exporter\_port \}}) в параметры defaults/main.yml:

```
nginx__version: "1.18.0"
nginx__status_port: 8080
nginx__exporter_port: 9113  # <- новый параметр
nginx__http_config:
  - name: httpbin.org
    port: 443
    vhost: httpbin.org
    tls:
      enabled: true
      insecure_port: 80
      crt: |-
        SSL CERTIFICATE
      key: |-
        SSL KEY
    locations:
      "/":
        - proxy_pass https://httpbin.org
  - name: google.com
    port: 80
    vhost: google.com
    tls:
      enabled: false
    locations:
      "/":
        - proxy_pass https://google.com
```