from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import json
import time
from PIL import Image
import pytesseract
from webdriver_manager.chrome import ChromeDriverManager
import re
import cv2
import numpy as np
import matplotlib.pyplot as plt

def merge_json_files(output_dir):
    """Merge all extracted JSON files into a single JSON file with specific structure"""
    merged_data = {}

    # Walk through the output directory to find all JSON files
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if filename.endswith('.json') and filename != 'merged_data.json':
                file_path = os.path.join(root, filename)
                try:
                    # Load the JSON data from the file
                    with open(file_path, 'r') as json_file:
                        json_data = json.load(json_file)
                    
                    # Extract components from the file path
                    path_parts = os.path.relpath(root, output_dir).split(os.sep)
                    if len(path_parts) >= 2:  # Expecting structure: category/subcategory/mode/
                        category = path_parts[0]
                        subcategory = path_parts[1]
                        
                        # Extract mode from the parent folder name
                        if len(path_parts) >= 3:
                            mode = path_parts[2]
                        else:
                            mode = filename.split('_')[-2]  # Fallback to extract from filename
                        
                        # Extract device type from filename
                        device = filename.split('_')[-1].split('.')[0]
                        
                        # Initialize nested structure if not exists
                        if category not in merged_data:
                            merged_data[category] = {}
                        if subcategory not in merged_data[category]:
                            merged_data[category][subcategory] = {}
                        if mode not in merged_data[category][subcategory]:
                            merged_data[category][subcategory][mode] = {}
                        if device not in merged_data[category][subcategory][mode]:
                            merged_data[category][subcategory][mode][device] = []
                        
                        # Add the extracted numbers
                        merged_data[category][subcategory][mode][device].extend(json_data.get('extracted_numbers', []))
                
                except Exception as e:
                    print(f"Error loading JSON from {file_path}: {str(e)}")
    
    # Convert the dictionary to the desired list format
    formatted_data = []
    for category, subcategories in merged_data.items():
        category_data = {category: []}
        for subcategory, modes in subcategories.items():
            subcategory_data = {subcategory: []}
            for mode, devices in modes.items():
                mode_data = {mode: []}
                for device, values in devices.items():
                    device_data = {device: values}
                    mode_data[mode].append(device_data)
                subcategory_data[subcategory].append(mode_data)
            category_data[category].append(subcategory_data)
        formatted_data.append(category_data)
    
    # Save the merged JSON data to a final output file
    merged_json_path = os.path.join(output_dir, 'merged_data.json')
    with open(merged_json_path, 'w') as merged_file:
        json.dump(formatted_data, merged_file, indent=4)
    
    print(f"Merged JSON saved to: {merged_json_path}")

    # After saving the JSON file, convert it to Excel and create the summary plot
    excel_path = os.path.join(output_dir, 'metrics_report.xlsx')
    # json_to_excel(formatted_data, excel_path)
    
    create_summary_plot(formatted_data, output_dir)

def extract_numbers_from_circles(image_cv):
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

    # Use Hough Circle Transform to detect circles
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=50,
        param1=50, param2=30, minRadius=20, maxRadius=60
    )

    extracted_texts = []

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            # Crop the region inside each circle
            x1, y1, x2, y2 = max(0, x - r), max(0, y - r), x + r, y + r
            cropped_circle = image_cv[y1:y2, x1:x2]

            # Preprocess the cropped circle for better OCR
            cropped_gray = cv2.cvtColor(cropped_circle, cv2.COLOR_BGR2GRAY)
            _, thresholded = cv2.threshold(cropped_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Run OCR on the preprocessed circle region
            text = pytesseract.image_to_string(thresholded, config='--psm 10 -c tessedit_char_whitelist=0123456789')
            if text.strip():  # If text is not empty, process it
                # Parse the text as a number
                try:
                    number = int(text.strip())
                    if number > 100:
                        number = 100  
                    extracted_texts.append(number)
                except ValueError:
                    extracted_texts.append(0)  
            else:
                extracted_texts.append(0)

    return extracted_texts

def setup_selenium():
    """Set up Selenium WebDriver with automatic ChromeDriver management"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Automatically download and configure ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver
import json

def take_screenshot_and_ocr(driver, file_path, output_dir):
    """Take a screenshot of the page and perform OCR on the lh-scores__container"""
    driver.get(f"file://{os.path.abspath(file_path)}")
    
    # Wait for the page to load
    time.sleep(2)
    
    # Take a screenshot of the entire page
    screenshot_path = os.path.join(output_dir, "screenshot.png")
    driver.save_screenshot(screenshot_path)
    
    # Locate the lh-scores__container element
    try:
        lh_scores_container = driver.find_element(By.CSS_SELECTOR, '.lh-scores-container')
        
        # Get the location and size of the element
        location = lh_scores_container.location
        size = lh_scores_container.size
        
        # Crop the screenshot to the lh-scores__container element
        image = Image.open(screenshot_path)
        left = max(0, location['x'])
        top = max(0, location['y'])
        right = min(location['x'] + size['width'], image.width)
        bottom = min(location['y'] + size['height'], image.height)

        # Crop with corrected coordinates
        cropped_image = image.crop((left, top, right, bottom))
        cropped_image_path = os.path.join(output_dir, "cropped_screenshot.png")
        cropped_image.save(cropped_image_path)
        
        # Perform OCR on the cropped image
        ocr_text = pytesseract.image_to_string(cropped_image)
        print("OCR Text from lh-scores__container:")
        # print(ocr_text)

        # Extract and print numerical values
        image_cv = cv2.imread(cropped_image_path)
        extracted_numbers = extract_numbers_from_circles(image_cv)
        print(extracted_numbers)

        # Save extracted numbers to JSON file
        json_data = {
            "extracted_numbers": extracted_numbers
        }

        # Use the original HTML filename (without extension) as the JSON filename
        json_filename = os.path.splitext(os.path.basename(file_path))[0] + '.json'
        json_path = os.path.join(output_dir, json_filename)

        # Save the JSON data
        with open(json_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        print(f"Extracted numbers saved to: {json_path}")
        
    except Exception as e:
        print(f"Error during screenshot or OCR: {str(e)}")

def create_plots(json_data, output_dir):
    """Create plots for the metrics"""
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Metric labels
    metric_labels = ['SEO', 'Best Practice', 'Accessibility', 'Performance']
    
    for category in json_data:
        category_name = list(category.keys())[0]
        subcategories = list(category.values())[0]
        
        for subcategory in subcategories:
            subcategory_name = list(subcategory.keys())[0]
            modes = list(subcategory.values())[0]
            
            for mode in modes:
                mode_name = list(mode.keys())[0]
                devices = list(mode.values())[0]
                
                # Prepare data for plotting
                device_data = {}
                for device in devices:
                    device_name = list(device.keys())[0]
                    values = list(device.values())[0]
                    # Ensure we only take the first 4 values
                    device_data[device_name] = values[:4]
                
                # Create plot
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Set up the bar positions
                bar_width = 0.2
                index = np.arange(len(metric_labels))
                
                # Plot bars for each device
                for i, (device, values) in enumerate(device_data.items()):
                    ax.bar(index + i * bar_width, values, bar_width, label=device)
                
                # Add labels, title and custom x-axis tick labels
                ax.set_xlabel('Metrics')
                ax.set_ylabel('Scores')
                ax.set_title(f'{category_name} - {subcategory_name} - {mode_name}')
                ax.set_xticks(index + bar_width * (len(device_data) - 1) / 2)
                ax.set_xticklabels(metric_labels)
                
                # Move legend to top left
                ax.legend(loc='upper left', bbox_to_anchor=(0, 1))
                
                # Save the plot
                plot_filename = f"{category_name}_{subcategory_name}_{mode_name}.png"
                plot_path = os.path.join(output_dir, plot_filename)
                plt.savefig(plot_path, bbox_inches='tight', dpi=300)
                plt.close()
                
                print(f"Plot saved to: {plot_path}")

def create_comparison_plots(json_data, output_dir):
    """Create comparison plots between different modes, pages, subcategories, and categories"""
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Metric labels
    metric_labels = ['SEO', 'Best Practice', 'Accessibility', 'Performance']
    
    # Create a dictionary to store all data for comparison
    comparison_data = {
        'modes': {},
        'pages': {},
        'subcategories': {},
        'categories': {}
    }
    
    # Collect data for comparisons
    for category in json_data:
        category_name = list(category.keys())[0]
        subcategories = list(category.values())[0]
        
        # Initialize category data
        if category_name not in comparison_data['categories']:
            comparison_data['categories'][category_name] = {m: [] for m in metric_labels}
        
        for subcategory in subcategories:
            subcategory_name = list(subcategory.keys())[0]
            modes = list(subcategory.values())[0]
            
            # Initialize subcategory data
            if subcategory_name not in comparison_data['subcategories']:
                comparison_data['subcategories'][subcategory_name] = {m: [] for m in metric_labels}
            
            for mode in modes:
                mode_name = list(mode.keys())[0]
                devices = list(mode.values())[0]
                
                # Initialize mode data
                if mode_name not in comparison_data['modes']:
                    comparison_data['modes'][mode_name] = {m: [] for m in metric_labels}
                
                for device in devices:
                    device_name = list(device.keys())[0]
                    values = list(device.values())[0][:4]
                    
                    # Add data to all comparison categories
                    for i, metric in enumerate(metric_labels):
                        comparison_data['modes'][mode_name][metric].append(values[i])
                        comparison_data['subcategories'][subcategory_name][metric].append(values[i])
                        comparison_data['categories'][category_name][metric].append(values[i])
                        
                        # Use subcategory as page identifier
                        page_key = f"{subcategory_name}_{device_name}"
                        if page_key not in comparison_data['pages']:
                            comparison_data['pages'][page_key] = {m: [] for m in metric_labels}
                        comparison_data['pages'][page_key][metric].append(values[i])
    
    # Create comparison plots
    for comparison_type, data in comparison_data.items():
        for name, metrics in data.items():
            # Create plot
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Calculate average values for each metric
            avg_values = [np.mean(metrics[m]) for m in metric_labels]
            
            # Create bar plot
            index = np.arange(len(metric_labels))
            ax.bar(index, avg_values, width=0.6)
            
            # Add labels and title
            ax.set_xlabel('Metrics')
            ax.set_ylabel('Average Score')
            ax.set_title(f'Comparison of {comparison_type.capitalize()}: {name}')
            ax.set_xticks(index)
            ax.set_xticklabels(metric_labels)
            
            # Add value labels on top of bars
            for i, v in enumerate(avg_values):
                ax.text(i, v + 1, f"{v:.1f}", ha='center')
            
            # Save the plot
            plot_filename = f"comparison_{comparison_type}_{name}.png".replace(" ", "_").replace("/", "_")
            plot_path = os.path.join(output_dir, plot_filename)
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            print(f"Comparison plot saved to: {plot_path}")

def create_summary_plot(json_data, output_dir):
    """Create a single summary plot with all metrics and comparisons"""
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Metric labels
    metric_labels = ['SEO', 'Best Practice', 'Accessibility', 'Performance']
    
    # Prepare data for the summary plot
    summary_data = {
        'categories': {},
        'subcategories': {},
        'modes': {},
        'devices': {}
    }
    
    # Collect data for the summary plot
    for category in json_data:
        category_name = list(category.keys())[0]
        subcategories = list(category.values())[0]
        
        # Initialize category data
        if category_name not in summary_data['categories']:
            summary_data['categories'][category_name] = {m: [] for m in metric_labels}
        
        for subcategory in subcategories:
            subcategory_name = list(subcategory.keys())[0]
            modes = list(subcategory.values())[0]
            
            # Initialize subcategory data
            if subcategory_name not in summary_data['subcategories']:
                summary_data['subcategories'][subcategory_name] = {m: [] for m in metric_labels}
            
            for mode in modes:
                mode_name = list(mode.keys())[0]
                devices = list(mode.values())[0]
                
                # Initialize mode data
                if mode_name not in summary_data['modes']:
                    summary_data['modes'][mode_name] = {m: [] for m in metric_labels}
                
                for device in devices:
                    device_name = list(device.keys())[0]
                    values = list(device.values())[0][:4]
                    
                    # Add data to all summary categories
                    for i, metric in enumerate(metric_labels):
                        summary_data['categories'][category_name][metric].append(values[i])
                        summary_data['subcategories'][subcategory_name][metric].append(values[i])
                        summary_data['modes'][mode_name][metric].append(values[i])
                        
                        # Initialize device data
                        if device_name not in summary_data['devices']:
                            summary_data['devices'][device_name] = {m: [] for m in metric_labels}
                        summary_data['devices'][device_name][metric].append(values[i])
    
    # Create the summary plot
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle('Comprehensive Metrics Summary', fontsize=16, y=1.02)
    
    # Plot 1: Categories Comparison
    ax1 = axes[0, 0]
    for category, metrics in summary_data['categories'].items():
        avg_values = [np.mean(metrics[m]) for m in metric_labels]
        ax1.plot(metric_labels, avg_values, marker='o', label=category)
    ax1.set_title('Categories Comparison')
    ax1.set_ylabel('Average Score')
    ax1.legend(loc='upper left')
    ax1.grid(True)
    
    # Plot 2: Subcategories Comparison
    ax2 = axes[0, 1]
    for subcategory, metrics in summary_data['subcategories'].items():
        avg_values = [np.mean(metrics[m]) for m in metric_labels]
        ax2.plot(metric_labels, avg_values, marker='o', label=subcategory)
    ax2.set_title('Subcategories Comparison')
    ax2.set_ylabel('Average Score')
    ax2.legend(loc='upper left')
    ax2.grid(True)
    
    # Plot 3: Modes Comparison
    ax3 = axes[1, 0]
    for mode, metrics in summary_data['modes'].items():
        avg_values = [np.mean(metrics[m]) for m in metric_labels]
        ax3.plot(metric_labels, avg_values, marker='o', label=mode)
    ax3.set_title('Modes Comparison')
    ax3.set_ylabel('Average Score')
    ax3.legend(loc='upper left')
    ax3.grid(True)
    
    # Plot 4: Devices Comparison
    ax4 = axes[1, 1]
    for device, metrics in summary_data['devices'].items():
        avg_values = [np.mean(metrics[m]) for m in metric_labels]
        ax4.plot(metric_labels, avg_values, marker='o', label=device)
    ax4.set_title('Devices Comparison')
    ax4.set_ylabel('Average Score')
    ax4.legend(loc='upper left')
    ax4.grid(True)
    
    # Adjust layout and save the plot
    plt.tight_layout()
    plot_path = os.path.join(output_dir, 'summary_plot.png')
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    plt.close()
    
    print(f"Summary plot saved to: {plot_path}")

def process_reports_directory(directory='Reports', output_dir='Metrics'):
    """Process all HTML files using Selenium"""
    driver = setup_selenium()
    
    # try:
    #     if not os.path.exists(directory):
    #         print(f"Directory '{directory}' not found!")
    #         return

    #     for root, dirs, files in os.walk(directory):
    #         for filename in files:
    #             if filename.endswith('.html'):
    #                 file_path = os.path.join(root, filename)
    #                 try:                        
    #                     # Create corresponding output path
    #                     relative_path = os.path.relpath(root, directory)
    #                     output_path = os.path.join(output_dir, relative_path, f"{os.path.splitext(filename)[0]}.json")
                        
    #                     # Save metrics
    #                     os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
    #                     # Take screenshot and perform OCR
    #                     take_screenshot_and_ocr(driver, file_path, os.path.dirname(output_path))
                        
    #                 except Exception as e:
    #                     print(f"Error processing {filename}: {str(e)}")
    merge_json_files(output_dir)
    # finally:
    #     driver.quit()

if __name__ == '__main__':
    process_reports_directory()