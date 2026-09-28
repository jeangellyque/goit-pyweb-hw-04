# Веб-додаток

## Запуск у Docker

Перейдіть у папку проєкту, зберіть образ і запустіть контейнер:

```bash
docker build -t goit-pyweb-hw-04 .
docker run -d --name goit-pyweb-hw-04-app \
  -p 3000:3000 \
  -v "$PWD/storage:/app/storage" \
  goit-pyweb-hw-04
```

Відкрийте [http://localhost:3000](http://localhost:3000). Каталог `storage`
підключений із хоста, тому повідомлення зберігаються у `storage/data.json`
і залишаються після видалення контейнера. Якщо каталог або файл відсутні,
застосунок створить їх під час запуску.

Зупинити контейнер:

```bash
docker stop goit-pyweb-hw-04-app
```
