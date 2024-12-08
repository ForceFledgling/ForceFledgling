**Домашнее задание №5**

Соберите Docker образ для проекта [counter-backend](https://git.devops-teta.ru/materials/counter-backend). В качестве базового образа используйте [python:3.11.6-slim-bookworm](https://hub.docker.com/_/python). Для сборки используйте следующие команды:  
  
**Установка зависимостей для сборки пакета:**  
$ python -m pip install \\  
  --no-color \\  
  --no-cache-dir \\  
  --disable-pip-version-check \\  
  --no-python-version-warning \\  
  --no-warn-script-location \\  
  --break-system-packages \\  
  --progress-bar off \\  
  poetry setuptools wheel  
  
**Загрузка всех зависимостей в папку dist/vendor:**  
$ mkdir -p dist  
$ poetry export \\  
  --without-hashes \\  
  --format constraints.txt \\  
  --output dist/constraints.txt  
$ poetry run \\  
  python -m pip wheel \\  
   --isolated \\  
   --requirement dist/constraints.txt \\  
   --wheel-dir dist/vendor  
  
**Пакетирование проекта в папку dist:**  
$ poetry build --format wheel  
  
**Установка всех зависимостей:**  
$ packages=$(\\  
  find 'dist' 'dist/vendor' \\  
    -maxdepth 1 \\  
    -iname '\*.whl' \\  
    -exec realpath {} \\; \\  
    -print0 \\  
   | xargs --null)  
$ python -m pip install \\  
  --isolated \\  
  --no-index \\  
  --no-color \\  
  --no-cache-dir \\  
  --disable-pip-version-check \\  
  --no-python-version-warning \\  
  --no-warn-script-location \\  
  --no-deps \\  
  --break-system-packages \\  
  --progress-bar off \\  
  ${packages}  
Эти команды находят все пакеты Python собранные предыдущими командами и затем устанавливают их.  
  
**Запуск модуля:**  
$ python -m counter\_backend  
  
**Напишите три варианта Dockerfile:**  
 

*   Без использования многоступенчатой сборки и запуском процесса из-под суперпользователя
*   С использованием многоступенчатой сборки ()
*   С использованием многоступенчатой сборки и понижением привилегий:
*   Загрузите пакеты первым и вторым набором команд, скопируйте в финальный слой и установите в нем;
*   Воспользуйтесь приведенным выше скриптом для создания пользователя

Загрузите написанные Dockerfile в курсовой GitLab, в отдельный репозиторий. Если вы не пользовались ранее Git, то просмотрите краткую справку, приведенную в лонгриде.