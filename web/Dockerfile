FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json

# Avoid installing deps yet; placeholder container

COPY . /app

EXPOSE 3000

CMD ["sh", "-c", "while sleep 3600; do :; done"]

