# Use official Node.js 24 image
FROM node:24-alpine

# Set working directory
WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Copy package files and install dependencies
COPY package.json pnpm-lock.yaml ./
RUN pnpm install

# Copy the rest of the frontend source code
COPY . .

# Expose dev server port
EXPOSE 5173

# Start Vite dev server
CMD ["pnpm", "run", "dev"]