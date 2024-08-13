const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    await page.goto('https://youtube.com/login');

    // Automate the login process...

    // Extract cookies after logging in
    let cookies = await page.cookies();

    // Filter out cookies with an expires value of -1
    cookies = cookies.filter(cookie => cookie.expires !== -1);

    // Convert to Netscape format
    const netscapeCookies = cookies.map(cookie => {
        return `${cookie.domain}\tTRUE\t${cookie.path}\t${cookie.secure ? 'TRUE' : 'FALSE'}\t${Math.floor(cookie.expires || 0)}\t${cookie.name}\t${cookie.value}`;
    }).join('\n');

    fs.writeFileSync('cookies.txt', netscapeCookies);

    await browser.close();
})();
