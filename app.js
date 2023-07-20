const fs = require('fs');
const ytdl = require('ytdl-core');
const { url } = require('./source.json');

const dir = './data';
if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir);
}

async function download() {
    try {
        ytdl(url).pipe(fs.createWriteStream("data/download.mp4"));
    } catch (err) {
        console.log(err);
    }
}

download();