FROM node:16-alpine

WORKDIR /usr/src/app

COPY public/package.json .
RUN npm install

COPY server.js .
COPY public /usr/src/app/public

EXPOSE 3000

CMD ["node", "server.js"]