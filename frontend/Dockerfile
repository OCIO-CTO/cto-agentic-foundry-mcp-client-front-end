FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_MCP_URL
ARG VITE_CHAT_URL
ENV VITE_MCP_URL=$VITE_MCP_URL
ENV VITE_CHAT_URL=$VITE_CHAT_URL

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
