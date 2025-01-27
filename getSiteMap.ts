import puppeteerExtra from "puppeteer-extra";
import puppeteerExtraPluginStealth from "puppeteer-extra-plugin-stealth";
import { writeFileSync } from "fs";

puppeteerExtra.use(puppeteerExtraPluginStealth());

const generateSiteMap = async () => {
  const browser = await puppeteerExtra.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto("https://erp.agnikul.in/login", {
    waitUntil: "networkidle2",
  });

  await page.type("#login_email", "senthilnathan_selvarajan@agnikul.in");
  await page.type("#login_password", "nathaah@123");


  await page.waitForFunction(
    'document.querySelector("#login-button").disabled === false',
    { timeout: 0 } 
  );

  await page.click("#login-button");

  await page.waitForNavigation({ waitUntil: "networkidle2" });

  await page.goto("https://erp.agnikul.in/Payroll_Management");
  await page.waitForNavigation({ waitUntil: 'networkidle2'});

  const links = await page.evaluate(() => {
    return Array.from(document.querySelectorAll("a")).map((a) => a.href);
  });

  const uniqueLinks = [...new Set(links)].filter((link) =>
    link.startsWith("https://erp.agnikul.in")
  );

  const jsonStructure = {
    "APP_NAME": uniqueLinks.map((link, index) => ({
      pageName: link.split('/').pop(),
      url: link,
    }))
  };

  writeFileSync("report/data.json", JSON.stringify(jsonStructure, null, 2));
  console.log("Sitemap generated and saved as sitemap.xml");

  await browser.close();
};

export default generateSiteMap;