FROM mcr.microsoft.com/playwright:v1.58.2-noble

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Default command runs all tests
CMD ["npx", "playwright", "test"]
