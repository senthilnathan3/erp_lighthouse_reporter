import puppeteerExtra from "puppeteer-extra";
import puppeteerExtraPluginStealth from "puppeteer-extra-plugin-stealth";
import { writeFileSync } from "fs";

puppeteerExtra.use(puppeteerExtraPluginStealth());

const ERP_USER = process.env.ERP_USER;
const ERP_PWD = process.env.ERP_PWD;
const PageName = "Payroll_Management";

const generateSiteMap = async () => {
  const browser = await puppeteerExtra.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto("https://erp.agnikul.in/login", {
    waitUntil: "networkidle2",
  });

  await page.type("#login_email", ERP_USER);
  await page.type("#login_password", ERP_PWD);


  await page.waitForFunction(
    'document.querySelector("#login-button").disabled === false',
    { timeout: 0 } 
  );

  await page.click("#login-button");

  await page.waitForNavigation({ waitUntil: "networkidle2" });

  await page.goto("https://erp.agnikul.in/" + PageName);
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

  writeFileSync("siteMap/data.json", JSON.stringify(jsonStructure, null, 2));
  console.log("Sitemap generated and saved as sitemap.xml");

  await browser.close();
};

export default generateSiteMap;