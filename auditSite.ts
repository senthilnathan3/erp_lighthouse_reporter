import { join } from "path";
import { writeFileSync, mkdirSync, existsSync, readFileSync } from "fs";
import { launch } from "chrome-launcher";
import puppeteer from "puppeteer";
import dataContent from "./siteMap/data.json";
import lighthouse from "lighthouse";
import generateSiteMap from "./getSiteMap";
import dotenv from "dotenv";
dotenv.config();


const ERP_USER = process.env.ERP_EMAIL
const ERP_PWD = process.env.ERP_PWD

export class LightHouseWrapper {
  private currentDateTime = new Date().toISOString();
  private reportFolder = join(process.cwd(), `Reports/${this.currentDateTime}`);
  private cookieFile = join(process.cwd(), "cookies.txt");
  private chrome: any;
  private browser: any;

  async auditSite(): Promise<void> {
    generateSiteMap();
    // await this.setup();
    // const urls = await this.getUrls();
    // const viewports = this.getViewports();
    // const modes = ["navigation", "snapshot", "timespan"] as const;

    // for (const source of urls) {
    //   console.log(`Running audits for page: ${source.pageName}`);

    //   for (const mode of modes) {
    //     const modeFolder = join(this.reportFolder, source.pageName.trim(), `${mode}_mode`);
    //     this.makeDirectory(modeFolder);

    //     for (const viewport of viewports) {
    //       console.log(`Auditing: ${source.url} | Mode: ${mode} | Viewport: ${JSON.stringify(viewport)}`);
    //       const options = await this.getBrowserConfig(viewport);
    //       await this.runLighthouse(source, options, mode, modeFolder, viewport);
    //     }
    //   }
    // }

    // await this.teardown();
  }

  async runLighthouse(
    source: { url: string; pageName: string },
    options: any,
    mode: "navigation" | "snapshot" | "timespan",
    modeFolder: string,
    viewport: { width: number; height: number }
  ): Promise<void> {
    const config = {
      extends: "lighthouse:default",
      settings: { output: "html", formFactor: options.screenEmulation.mobile ? "mobile" : "desktop" },
    };

    // Adjust config settings based on the mode
    if (mode === "snapshot") {
      config.settings = { ...config.settings, onlyAudits: ["screenshot-thumbnails"] };
    } else if (mode === "timespan") {
      config.settings = { ...config.settings, throttlingMethod: "provided" };
    }

    const runnerResult = await lighthouse(source.url, { ...options, mode }, config);
    const reportHtml = runnerResult.report;

    const viewportName = options.screenEmulation.mobile
      ? "mobile"
      : viewport.width === 768
      ? "tablet"
      : "desktop";

    const reportFileName = `${modeFolder}/${source.pageName.trim()}_${mode}_${viewportName}.html`;
    writeFileSync(reportFileName, reportHtml);
    console.log(`Saved report: ${reportFileName}`);
  }

  async setup(): Promise<void> {
    this.makeDirectory(this.reportFolder);
    this.chrome = await launch({ chromeFlags: [] });

    // Launch Puppeteer for authentication
    const puppeteerOptions = {
      headless: false,
      args: [`--remote-debugging-port=${this.chrome.port}`],
    };
    this.browser = await puppeteer.launch(puppeteerOptions);

    // Authenticate and save cookies
    const page = await this.browser.newPage();
    await page.goto("https://erp.agnikul.in/login", { waitUntil: "networkidle2" });

    await page.type("#login_email", ERP_USER);
    await page.type("#login_password", ERP_PWD);
    await page.click("#login-button");
    await page.waitForNavigation({ waitUntil: "networkidle2", timeout: 0 });

    const cookies = await page.cookies();
    const cookieHeader = cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join("; ");
    writeFileSync(this.cookieFile, cookieHeader);
    console.log("Authentication completed and cookies saved.");
  }

  async getUrls(): Promise<{ url: string; pageName: string }[]> {
    return dataContent.APP_NAME;
  }

  makeDirectory(path: string): void {
    if (!existsSync(path)) {
      mkdirSync(path, { recursive: true });
    }
  }

  async teardown(): Promise<void> {
    await this.browser.close();
    await this.chrome.kill();
  }

  async getBrowserConfig(viewport: { width: number; height: number }): Promise<any> {
    let cookieHeader = "";
    try {
      cookieHeader = readFileSync(this.cookieFile, "utf-8");
    } catch (err) {
      console.error("Error reading cookie file:", err);
    }

    return {
      logLevel: "info",
      output: "html",
      port: this.chrome.port,
      extraHeaders: {
        Cookie: cookieHeader,
      },
      screenEmulation: {
        width: viewport.width,
        height: viewport.height,
        deviceScaleFactor: 1,
        mobile: viewport.width < 768,
      },
    };
  }

  getViewports(): { width: number; height: number }[] {
    return [
      { width: 1920, height: 1080 }, // Desktop
      { width: 768, height: 1024 }, // Tablet
      { width: 375, height: 667 }, // Mobile
    ];
  }
}

// Invoke the function
(async () => {
  try {
    const lightHouseWrapper = new LightHouseWrapper();
    await lightHouseWrapper.auditSite();
    console.log("Audit completed successfully.");
  } catch (error) {
    console.error("Error during audit:", error);
  }
})();
