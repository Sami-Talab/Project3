import requests
import os
import time
import random
import re
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

#load .env file to get api id and key
load_dotenv()
app_id = os.getenv('APP_ID')
app_key = os.getenv('APP_KEY')

# function to set up Selenium WebDriver with detection avoidance
def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent detection
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # set user-agent to make the request look like a real browser
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    )

    chromedriver_path = os.path.join(os.getcwd(), 'chromedriver')
    if not os.path.exists(chromedriver_path):
        raise FileNotFoundError(f"chromedriver not found at {chromedriver_path}. Please ensure it's in the project directory.")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # mask WebDriver via JavaScript execution
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

# function to perform job scraping from Indeed 
def search_jobs_selenium(job_title='', location='', page=0):
    driver = setup_selenium()

    try:
        base_url = "https://www.indeed.com/jobs"
        params = f"?q={job_title}&l={location}&start={page * 10}"
        search_url = base_url + params
        driver.get(search_url)

        # wait for the page to load and find job cards
        time.sleep(5)
        job_cards = driver.find_elements(By.CLASS_NAME, 'job_seen_beacon')

        job_data = []
        for job_card in job_cards:
            try:
                title = job_card.find_element(By.CLASS_NAME, 'jobTitle').text
                salary = job_card.find_element(By.CLASS_NAME, 'salary-snippet-container').text if job_card.find_elements(By.CLASS_NAME, 'salary-snippet-container') else "Salary not listed"
                location = job_card.find_element(By.CSS_SELECTOR, '[data-testid="text-location"]').text if job_card.find_elements(By.CSS_SELECTOR, '[data-testid="text-location"]') else "Location not listed"
                job_data.append((title, salary, location))
            except Exception as e:
                print(f"Error extracting job details: {e}")

        driver.quit()

        # return the job data as a DataFrame
        df = reformat_job_data(job_data)

        return df
    
    except Exception as e:
        print(f"Error: {e}")
        driver.quit()
        return pd.DataFrame(columns=['Title', 'Location', 'Salary'])

#function to process salary and calculate the average if a range is given
def process_salary(salary_str):
    if not salary_str or "Salary not listed" in salary_str or salary_str.strip() == "":
        return None

    #gandle ranges and single values
    #removing any non-numeric characters except commas and periods
    salary_numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', salary_str)
    if not salary_numbers:  # If no salary numbers were found, return None
        return None
    
    #convert found salary numbers to float after removing commas
    salary_numbers = [float(salary.replace(",", "")) for salary in salary_numbers]

    #calculate average if it's a range, otherwise return the single value
    if len(salary_numbers) == 2:
        avg_salary = sum(salary_numbers) / 2
    elif len(salary_numbers) == 1:
        avg_salary = salary_numbers[0]
    else:
        return None

    #convert hourly salary to yearly salary, assuming 8 hours/day and 260 working days/year
    if "an hour" in salary_str.lower() or "hour" in salary_str.lower():
        avg_salary *= 8 * 260
    elif "a day" in salary_str.lower() or "day" in salary_str.lower():
        avg_salary *= 260
    elif "a week" in salary_str.lower() or "week" in salary_str.lower():
        avg_salary *= 52
    elif "a month" in salary_str.lower() or "month" in salary_str.lower():
        avg_salary *= 12

    return avg_salary

#function to reformat the scraped job data
def reformat_job_data(job_data):
    df = pd.DataFrame(job_data, columns=['Title', 'Salary', 'Location'])
    df['Salary'] = df['Salary'].apply(process_salary)  # Process salary ranges
    return df

#fetch job listings from Adzuna API
def fetch_jobs_from_adzuna(job_title, location, page=1):
    api_url = f'https://api.adzuna.com/v1/api/jobs/us/search/{page}'
    
    params = {
        'app_id': app_id,
        'app_key': app_key,
        'results_per_page': 10,  
        'what': job_title,
        'where': location
    }

    response = requests.get(api_url, params=params)
    
    if response.status_code == 200:
        return response.json()['results']
    else:
        print(f"Error fetching data from Adzuna API: {response.status_code}")
        return None

#function to process Adzuna job data and return a DataFrame
def process_adzuna_data(adzuna_jobs):
    job_data = []
    
    for job in adzuna_jobs:
        title = job.get('title', 'N/A')
        location = ', '.join(job['location']['area']) if 'location' in job else 'N/A'
        salary_min = job.get('salary_min', None)
        salary_max = job.get('salary_max', None)
        if salary_min and salary_max:
            salary = (salary_min + salary_max) / 2  # calculate average salary if both min and max are available
        else:
            salary = salary_min or salary_max  #use available
        
        job_data.append({
            'Title': title,
            'Location': location,
            'Salary': salary
        })
    
    #convert job data into a DataFrame
    df_adzuna = pd.DataFrame(job_data)
    return df_adzuna

# commbine Scraped Data and Adzuna Data
def combine_data(df_scraped, df_adzuna):
    #combine both DataFrames into one for comparison or enhancement
    combined_df = pd.concat([df_scraped, df_adzuna], ignore_index=True)
    return combined_df

# main function to execute the script with pagination and user prompts
def main():
    job_title = input("Enter job title (leave blank to search all jobs): ")
    location = input("Enter location (leave blank to search all locations): ")

    all_data = pd.DataFrame()

    # scraping and fetching data in a loop with user prompts
    page = 0
    while True:
        # fetch jobs from Adzuna API
        adzuna_jobs = fetch_jobs_from_adzuna(job_title, location, page + 1)
        df_adzuna = process_adzuna_data(adzuna_jobs) if adzuna_jobs else pd.DataFrame()

        #scrape jobs from Indeed with pagination
        df_scraped = search_jobs_selenium(job_title=job_title, location=location, page=page)

        #combine both datasets (scraped and Adzuna)
        if not df_scraped.empty or not df_adzuna.empty:
            combined_df = combine_data(df_scraped, df_adzuna)
            all_data = pd.concat([all_data, combined_df], ignore_index=True)

            print("Current Combined Job Data (Scraped + Adzuna):")
            print(all_data)

            #ask if the user wants to load more data
            load_more = input("Do you want to load more jobs? (yes/no): ").strip().lower()
            if load_more == 'no':
                break
        else:
            print("No more jobs found.")
            break

        page += 1  # move to the next page

    # ask if the user wants to save the data as a CSV
    if not all_data.empty:
        save_csv = input("Do you want to save the results to a CSV file? (yes/no): ").strip().lower()
        if save_csv == 'yes':
            all_data.to_csv('combined_job_data.csv', index=False)
            print("Data saved to 'combined_job_data.csv'.")
        else:
            print("Data not saved.")
    else:
        print("No jobs found.")

# run the script
if __name__ == "__main__":
    main()
