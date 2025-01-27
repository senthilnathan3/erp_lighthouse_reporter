import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class LightHouseReporter:
    def __init__(self):

        self.current_date_and_time = datetime.now().isoformat()
        self.report_folder = Path(f"LighthouseReports/{self.current_date_and_time}")
        self.cookies = []  # Store cookies for authenticated session

    def audit_with_lighthouse(self):
        try:
            print("Setting up browser...")
            self.setup()
            print("Generating sitemap...")
            self.generate_site_map()
            print("Fetching URLs...")
            urls = self.get_url()
            print("Making report directory...")
            self.make_report_directory()
            print("Triggering Lighthouse audits...")
            self.trigger_lighthouse_audit_and_get_results(urls)
            print("Tearing down session...")
            self.session_tear_down()
            print("Script completed successfully.")
        except Exception as error:
            print(f"Error in audit_with_lighthouse: {error}")

    def setup(self):
        try:
            print("Launching browser...")
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--remote-debugging-port=9222")
            self.browser = webdriver.Chrome(service=Service(), options=chrome_options)
            print("Browser launched successfully.")

            # Load cookies if they exist
            self.cookies = self.load_cookies_from_file()
        except Exception as error:
            print(f"Error in setup: {error}")

    def make_report_directory(self):
        try:
            if not self.report_folder.exists():
                print("Creating report directory...")
                self.report_folder.mkdir(parents=True, exist_ok=True)
                print("Report directory created.")
        except Exception as err:
            print(f"Error creating report directory: {err}")

    def get_url(self):
        with open("siteMap/data.json", "r") as file:
            data_content = json.load(file)
        return data_content["APP_NAME"]

    def session_tear_down(self):
        try:
            print("Closing browser...")
            self.browser.quit()
            print("Session torn down successfully.")
        except Exception as error:
            print(f"Error in session_tear_down: {error}")

    def trigger_lighthouse_audit_and_get_results(self, test_source):
        try:
            for index in range(len(test_source)):
                page_name = test_source[index]["pageName"].strip()
                url = test_source[index]["url"]

                print(f"Running Lighthouse audit for {url}...")
                report_path = self.report_folder / f"{page_name}_report.html"

                # Run Lighthouse CLI using Node.js
                command = [
                    "lighthouse",
                    url,
                    "--output=html",
                    f"--output-path={report_path}",
                    "--chrome-flags='--no-sandbox --disable-gpu'",
                ]
                subprocess.run(command, check=True)

                print(f"Lighthouse report saved: {report_path}")
        except Exception as error:
            print(f"Error in trigger_lighthouse_audit_and_get_results: {error}")

    def generate_site_map(self):
        try:
            print("Generating sitemap...")
            self.browser.get("https://erp.agnikul.in/login")

            # Check if cookies already exist
            # self.cookies = self.load_cookies_from_file()

            print("No existing cookies found. Logging in to get cookies...")
            print("Navigating to login page...")
            self.browser.get("https://erp.agnikul.in/login")

            print("Typing login credentials...")
            email_input = self.browser.find_element(By.ID, "login_email")
            email_input.send_keys("senthilnathan_selvarajan@agnikul.in")

            password_input = self.browser.find_element(By.ID, "login_password")
            password_input.send_keys("nathaah@123")

            print("Waiting for login button to be enabled...")
            login_button = self.browser.find_element(By.ID, "login-button")
            while login_button.get_attribute("disabled"):
                pass

            print("Clicking login button...")
            login_button.click()

            print("Waiting for navigation...")
            self.browser.implicitly_wait(10)

            # Save cookies for authenticated session
            print("Saving cookies for authenticated session...")
            self.cookies = self.browser.get_cookies()
            self.save_cookies_to_file(self.cookies)
            # else:
            #     print("Using existing cookies for authenticated session...")
            #     for cookie in self.cookies:
            #         self.browser.add_cookie(cookie)

            print("Navigating to Payroll Management page...")
            self.browser.get("https://erp.agnikul.in/Payroll_Management")
            self.browser.implicitly_wait(10)

            print("Collecting links...")
            links = self.browser.find_elements(By.TAG_NAME, "a")
            hrefs = [link.get_attribute("href") for link in links]

            print("Filtering unique links...")
            unique_links = list(set(hrefs))
            unique_links = [link for link in unique_links if link and link.startswith("https://erp.agnikul.in")]

            print("Saving sitemap to data.json...")
            json_structure = {
                "APP_NAME": [{"pageName": link.split('/')[-1], "url": link} for link in unique_links]
            }
            with open("siteMap/data.json", "w") as file:
                json.dump(json_structure, file, indent=2)
            print("Sitemap generated and saved as data.json")
        except Exception as error:
            print(f"Error in generate_site_map: {error}")

    def save_cookies_to_file(self, cookies):
        cookies_file_path = Path("cookies.json")
        with open(cookies_file_path, "w") as file:
            json.dump(cookies, file, indent=2)
        print("Cookies saved to file.")

    def load_cookies_from_file(self):
        cookies_file_path = Path("cookies.json")
        if cookies_file_path.exists():
            with open(cookies_file_path, "r") as file:
                cookies = json.load(file)
            print("Cookies loaded from file.")
            return cookies
        return []

if __name__ == "__main__":
    reporter = LightHouseReporter()
    reporter.audit_with_lighthouse()