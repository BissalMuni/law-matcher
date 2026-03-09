FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application
COPY . .

EXPOSE 3000

CMD ["sh", "-c", "rm -rf node_modules/.vite && npm run dev -- --host"]
