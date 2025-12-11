# Use official Node image with Debian
FROM node:18-bullseye

# Install system deps for yt-dlp and ffmpeg
RUN apt-get update && apt-get install -y     ffmpeg     python3     python3-pip     ca-certificates     curl  && rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN pip3 install --no-cache-dir yt-dlp

# Create app dir
WORKDIR /usr/src/app
COPY package.json .
RUN npm install --production

# Copy source
COPY . .

# Expose port
EXPOSE 3000
ENV PORT 3000

CMD ["npm", "start"]