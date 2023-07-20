const fs = require('fs');
const core = require('@actions/core');
const ytdl = require('ytdl-core');
const { url } = require('./source.json');

const dir = './data';
if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir);
}
const nameToGreet = core.getInput('url');
console.log(`Hello ${nameToGreet}!`);

async function download() {
    try {
        ytdl(core.getInput('url'), { quality: 18 }).pipe(fs.createWriteStream("data/download.mp4"));
    } catch (err) {
        console.log(err);
    }
}

download();