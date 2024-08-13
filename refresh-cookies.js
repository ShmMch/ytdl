const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    await page.goto('https://youtube.com/login');

    // Automate the login process, possibly handling 2FA if needed.
    // Add your login steps here.

    // Extract cookies after logging in
    const cookies = await page.cookies();
    fs.writeFileSync('cookies.json', JSON.stringify(cookies));

    await browser.close();
})();
