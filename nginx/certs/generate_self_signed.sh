#!/bin/sh
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/meet.zindaki-edu.ru.key \
    -out /etc/nginx/certs/meet.zindaki-edu.ru.crt \
    -subj "/CN=meet.zindaki-edu.ru"
