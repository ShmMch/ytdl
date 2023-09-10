const fs = require('fs');
const ytdl = require('ytdl-core');

if (!fs.existsSync('data')) {
    fs.mkdirSync('data');
}

ytdl(process.env.URL, { quality: 18 }).pipe(fs.createWriteStream("data/download.txt"));
