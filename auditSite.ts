    import { join } from "path";
    import { writeFileSync, mkdirSync, existsSync } from "fs";
    import { launch } from "chrome-launcher";
    import lighthouse, { RunnerResult } from "lighthouse";
    import puppeteerExtra from "puppeteer-extra";
    import puppeteerExtraPluginStealth from "puppeteer-extra-plugin-stealth";
    import dataContent from "./siteMap/data.json";
    import puppeteerType from "lighthouse/types/puppeteer";
    import { KnownDevices } from 'puppeteer';

    const iPhone = KnownDevices['iPhone 15 Pro'];

    puppeteerExtra.use(puppeteerExtraPluginStealth());

    export class LightHouseReporter {
    private chrome: any;
    private currentDateAndTime = new Date().toISOString();
    private reportFolder = join(
        process.cwd(),
        `LighthouseReports/${this.currentDateAndTime}`
    );
    private browser: puppeteerType.Browser;
    private cookies: any[] = []; // Store cookies for authenticated session

    async auditWithLighthouse(): Promise<void> {
        try {
        console.log("Setting up browser...");
        await this.setup();
        console.log("Generating sitemap...");
        await this.generateSiteMap();
        console.log("Fetching URLs...");
        let urls = await this.getUrl();
        console.log("Getting browser config...");
        let options = this.getBrowserConfig();
        console.log("Making report directory...");
        await this.makeReportDirectory();
        console.log("Triggering Lighthouse audits...");
        await this.triggerLightHouseAuditAndGetResults(urls, options);
        console.log("Tearing down session...");
        await this.sessionTearDown();
        console.log("Script completed successfully.");
        } catch (error) {
        console.error("Error in auditWithLighthouse:", error);
        }
    }

    async setup(): Promise<void> {
        try {
        console.log("Launching browser...");
        this.browser = await puppeteerExtra.launch({
            headless: false, // Set to true for headless mode
            args: ["--no-sandbox", "--disable-gpu", "--remote-debugging-port=9222"],
        });
        console.log("Browser launched successfully.");
    
        console.log("Launching Chrome instance...");
        this.chrome = await launch({ chromeFlags: ["--disable-gpu", "--no-sandbox"] });
        console.log("Chrome instance launched successfully.");
    
        // Load cookies if they exist
        this.cookies = await this.loadCookiesFromFile();
        } catch (error) {
        console.error("Error in setup:", error);
        }
    }

    async makeReportDirectory(): Promise<void> {
        try {
        if (!(await existsSync(this.reportFolder))) {
            console.log("Creating report directory...");
            await mkdirSync(this.reportFolder, { recursive: true });
            console.log("Report directory created.");
        }
        } catch (err) {
        console.error("Error creating report directory:", err);
        }
    }

    async getUrl(): Promise<{}[]> {
        return dataContent.APP_NAME;
    }

    async getBrowserConfig(): Promise<{}> {
        return {
        logLevel: "info",
        output: "html",
        port: this.chrome.port,
        };
    }

    async sessionTearDown(): Promise<void> {
        try {
        console.log("Killing Chrome instance...");
        await this.chrome.kill();
        console.log("Closing browser...");
        await this.browser.close();
        console.log("Session torn down successfully.");
        } catch (error) {
        console.error("Error in sessionTearDown:", error);
        }
    }

    async triggerLightHouseAuditAndGetResults(
        testSource: any,
        options: any
      ): Promise<void> {
        try {
          for (let index = 0; index < testSource.length; index++) {
            const pageName = testSource[index]["pageName"].trim();
            const url = testSource[index]["url"];
      
            console.log(`Creating new page for ${url}...`);
            const page = await this.browser.newPage();
      
            const device = "desktop";
      
            console.log(`Setting up device: ${device}...`);
            await this.setupDevice(page, device);
      
            console.log(`Navigating to ${url}...`);
            const response = await page.goto(url, { waitUntil: 'networkidle2' });
      
            // Check for 403 status
            if (response && response.status() === 403) {
              console.log("403 Forbidden detected. Attempting to log in again...");
      
              // Navigate to the login page
              await page.goto("https://erp.agnikul.in/login", { waitUntil: 'networkidle2' });
      
              // Enter login credentials
              console.log("Typing login credentials...");
              await page.type("#login_email", "senthilnathan_selvarajan@agnikul.in");
              await page.type("#login_password", "nathaah@123");
      
              // Wait for the login button to be enabled
              console.log("Waiting for login button to be enabled...");
              await page.waitForFunction(
                'document.querySelector("#login-button").disabled === false',
                { timeout: 0 }
              );
      
              // Click the login button
              console.log("Clicking login button...");
              await page.click("#login-button");
      
              // Wait for navigation to complete
              console.log("Waiting for navigation...");
              await page.waitForNavigation({ waitUntil: 'networkidle2' });
      
              // Retry navigating to the original URL
              console.log(`Retrying navigation to ${url}...`);
              await page.goto(url, { waitUntil: 'networkidle2' });
            }
      
            console.log(`Running Lighthouse audit for ${device} view on ${url}...`);
            let runnerResult: RunnerResult | any = await lighthouse(url, {
              ...options,
              port: this.chrome.port,
            });
      
            console.log(`Saving Lighthouse report for ${pageName}...`);
            let reportHtml = await runnerResult.report;
            await writeFileSync(
              `${this.reportFolder}/${pageName}_${device}.html`,
              reportHtml
            );
      
            console.log(`Lighthouse report for ${device} view saved: ${pageName}`);
            await page.close();
          }
        } catch (error) {
          console.error("Error in triggerLightHouseAuditAndGetResults:", error);
        }
      }

    async setupDevice(page: puppeteerType.Page, device: string): Promise<void> {
        try {
        if (device === "mobile") {
            console.log("Emulating mobile view...");
            await page.emulate(iPhone);
        } else {
            console.log("Emulating desktop view...");
            await page.setViewport({ width: 1920, height: 1080 });
        }
        } catch (error) {
        console.error("Error in setupDevice:", error);
        }
    }

    async generateSiteMap(): Promise<void> {
        try {
        console.log("Generating sitemap...");
        const page = await this.browser.newPage();
    
        // Check if cookies already exist
        this.cookies = await this.loadCookiesFromFile();
    
        if (this.cookies.length === 0) {
            console.log("No existing cookies found. Logging in to get cookies...");
            console.log("Navigating to login page...");
            await page.goto("https://erp.agnikul.in/login", {
            waitUntil: "networkidle2",
            });
            console.log("Typing login credentials...");
            await page.type("#login_email", "senthilnathan_selvarajan@agnikul.in");
            await page.type("#login_password", "nathaah@123");
            console.log("Waiting for login button to be enabled...");
            await page.waitForFunction(
            'document.querySelector("#login-button").disabled === false',
            { timeout: 0 }
            );
            console.log("Clicking login button...");
            await page.click("#login-button");
            console.log("Waiting for navigation...");
            await page.waitForNavigation({ waitUntil: "networkidle2" });
    
            // Save cookies for authenticated session
            console.log("Saving cookies for authenticated session...");
            this.cookies = await page.cookies();
            await this.saveCookiesToFile(this.cookies);
        } else {
            console.log("Using existing cookies for authenticated session...");
            await page.get(...this.cookies);
        }
    
        console.log("Navigating to Payroll Management page...");
        await page.goto("https://erp.agnikul.in/Payroll_Management");
        await page.waitForNavigation({ waitUntil: 'networkidle2' });
        console.log("Collecting links...");
        const links = await page.evaluate(() => {
            return Array.from(document.querySelectorAll("a")).map((a) => a.href);
        });
        console.log("Filtering unique links...");
        const uniqueLinks = [...new Set(links)].filter((link) =>
            link.startsWith("https://erp.agnikul.in")
        );
        console.log("Saving sitemap to data.json...");
        const jsonStructure = {
            "APP_NAME": uniqueLinks.map((link, index) => ({
            pageName: link.split('/').pop(),
            url: link,
            }))
        };
        writeFileSync("siteMap/data.json", JSON.stringify(jsonStructure, null, 2));
        console.log("Sitemap generated and saved as data.json");
        await page.close();
        } catch (error) {
        console.error("Error in generateSiteMap:", error);
        }
    }

    private async saveCookiesToFile(cookies: any[]): Promise<void> {
        const cookiesFilePath = join(process.cwd(), 'cookies.json');
        await writeFileSync(cookiesFilePath, JSON.stringify(cookies, null, 2));
        console.log("Cookies saved to file.");
    }

    private async loadCookiesFromFile(): Promise<any[]> {
        const cookiesFilePath = join(process.cwd(), 'cookies.json');
        if (existsSync(cookiesFilePath)) {
        const cookies = JSON.parse(readFileSync(cookiesFilePath, 'utf-8'));
        console.log("Cookies loaded from file.");
        return cookies;
        }
        return [];
    }
    }

    (async () => {
    try {
        const reporter = new LightHouseReporter();
        await reporter.auditWithLighthouse();
    } catch (error) {
        console.error("Error in main execution:", error);
    }
    })();