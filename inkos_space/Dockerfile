FROM node:20-slim

# Install basic tools
RUN apt-get update && apt-get install -y git python3 make g++ 

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Clone the latest inkos source
RUN git clone https://github.com/Narcooo/inkos.git /app/inkos

# Build inkos
WORKDIR /app/inkos
RUN pnpm install
RUN pnpm run build

# Setup our custom API wrapper
WORKDIR /app
COPY package.json .
COPY server.js .
RUN npm install

# Expose port 7860 for Hugging Face
EXPOSE 7860
CMD ["node", "server.js"]
