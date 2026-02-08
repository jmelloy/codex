FROM mcr.microsoft.com/playwright:v1.50.1-noble

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Default command runs all tests
CMD ["npx", "playwright", "test"]
