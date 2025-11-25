#!/bin/bash
# убиваем всё, что висит на 8000
kill -9 $(lsof -t -i:8000) 2>/dev/null

# запускаем сервер
python manage.py runserver
