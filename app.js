const fs = require('fs');
const ytdl = require('ytdl-core');

const dir = './data';
if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir);
}

async function download() {
    try {
        ytdl(process.env.URL, { quality: 18 }).pipe(fs.createWriteStream("data/download.mp4"));
    } catch (err) {
        console.log(err);
    }
}

download();