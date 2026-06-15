FROM node:latest
WORKDIR /app
COPY . .
RUN npm install
ENV API_KEY=sk_live_51HxbakedIntoLayer   # secret persists in image layers, extractable
EXPOSE 3000
CMD ["node", "server.js"]
# no USER -> runs as root; a container escape lands as host root
