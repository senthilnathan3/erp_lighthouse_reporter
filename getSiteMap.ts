import puppeteerExtra from "puppeteer-extra";
import puppeteerExtraPluginStealth from "puppeteer-extra-plugin-stealth";
import { writeFileSync } from "fs";

puppeteerExtra.use(puppeteerExtraPluginStealth());
import dotenv from "dotenv";
dotenv.config();

const ERP_USER = process.env.ERP_EMAIL;
const ERP_PWD = process.env.ERP_PWD;
const PageName: string = "Cad";

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

  await page.goto("https://erp.agnikul.in/" + PageName, {
    waitUntil: "networkidle2",
  });

  await page.waitForSelector(".preloader", { hidden: true, timeout: 300000 });

  await page.waitForSelector(".menuicons", {
    visible: true,
    timeout: 300000,
  });

  if (PageName === "food") {
    await page.waitForSelector("#Get_started", { visible: true });
    await page.click("#Get_started");
  }

  if (PageName === "quality_desk") {
    await page.waitForSelector(".menu");

    // Click all dropdown menus dynamically
    const dropdownMenus = await page.$$(".menu > div");

    for (const dropdown of dropdownMenus) {
      try {
        // Check if the dropdown contains a menu icon and menu name
        const menuName = await dropdown.$eval(
          ".menuName",
          (el) => el.innerText
        );

        console.log(`Opening dropdown: ${menuName}`);
        await dropdown.click();
        await page.waitForNetworkIdle();
      } catch (error) {
        console.log("Error interacting with dropdown:", error);
      }
    }
  }
  const links = await page.evaluate(() => {
    return Array.from(document.querySelectorAll("a"))
      .map((a) => a.href)
      .filter(Boolean);
  });

  console.log(links);

  const uniqueLinks = [...new Set(links)].filter((link) =>
    link.includes("/" + PageName)
  );

  const jsonStructure = {
    APP_NAME: uniqueLinks.map((link, index) => ({
      pageName: link.split("/").pop(),
      url: link,
    })),
  };

  writeFileSync("siteMap/data.json", JSON.stringify(jsonStructure, null, 2));
  console.log("Sitemap generated and saved as sitemap.xml");
  // const pageContent = await page.content();
  // writeFileSync("siteMap/page.html", pageContent);
  // console.log("Page content saved as page.html");

  await browser.close();
};

export default generateSiteMap;
