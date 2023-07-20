const fs = require('fs');
const ytdl = require('ytdl-core');
const source = require('./source.json');

const dir = './data';
if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir);
}

const downloadPromise = (url) => new Promise((res, rej) => {
    const chunks = [];
    ytdl(url).on("data", (chunk) => {
        chunks.push(...chunk);
    }).on("end", () => {
        res(chunks.concat());
    }).on("error", (err) => {
        rej(err);
    });
});

async function download() {
    try {
        const bytesStr = await downloadPromise(source.url);
        fs.writeFileSync("data/download.mp4", Buffer.from(bytesStr));
    } catch (err) {
        console.log(err);
    }
}

download();