**Домашнее задание №6**

**docker-compose:**  
Напишите docker-compose.yml который запускает наш сервис counter.  
Docker-composer должен запустить:  
 

*   [counter-frontend](https://git.devops-teta.ru/materials/counter-frontend)
*   [counter-backend](https://git.devops-teta.ru/materials/counter-backend)
*   nginx

  
**nginx:**  
 

*   Обращения к root локейшену должны попадать в контейнер counter-frontend.
*   Обращение к /api backend должны проксироваться в контейнер counter-backend.
*   Здесь мы воспользуемся результатом генерации нашего SSL сертификата. Контейнер с nginx должен принимать подключение из интернета, по https.

  
**Проверка**  
Для успешного выполнения задания вам необходимо:  
 

1.  Создать репозиторий в git.devops-teta.ru
2.  Загрузить в репозиторий dockerfile для counter-frontend, counter-backend, nginx, если использовалась сборка.
3.  Загрузить в репозиторий docker-compose.yml
4.  Опубликовать http порт, с работающим приложением counter. Передать ссылку на проверку.

  
**Внимание:**  
Порт приложения backend и frontend не должны быть публично доступны. Все запросы должны обрабатываться только через nginx.  
  
**Пример**  
Пример работающего приложения Counter: [http://practice-4.devops-teta.ru](http://practice-4.devops-teta.ru/)  
  
Пример конфигурации nginx:  
server {  
  listen   80;  
  server\_name \_;  
  
  location / {  
    proxy\_pass   http://frontend:8080;  
  }  
  location /api {  
    proxy\_pass   http://backend:8080;  
  }  
}