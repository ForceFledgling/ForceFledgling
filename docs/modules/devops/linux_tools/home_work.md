**Домашнее задание №2**

Для выписывания сертификатов используются разные методы и технологии.  
В данном случае мы воспользуемся Let’s Encrypt и выпишем себе личный сертификат, который будем использовать в дальнейшем.  
  
Для этого эффективно будет использо﻿вать snap. [Инструкция](https://certbot.eff.org/instructions?ws=other&os=ubuntufocal) по выписыванию сертификата.  
  
**Дополнительные команды для выписывания сертификата:**  
  
apt install certbot -y  
sudo certbot certonly --standalone --preferred-challenges http -d \<ВАШ DNS>  
  
За своим DNS обратитесь к вашему лектору.