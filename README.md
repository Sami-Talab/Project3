# Job Scraper with Indeed and Adzuna API

This project scrapes job postings from Indeed using Selenium and fetches job data from the Adzuna API. The script allows users to search for job postings by job title and location, combine the results from both sources, and optionally save the data to a CSV file.

## Features

- **Selenium Web Scraping**: The script scrapes job postings from Indeed with the ability to avoid detection by websites.
- **Adzuna API**: Fetch job postings from the Adzuna API by providing job title and location.
- **Data Combination**: Combines job postings from both sources into a single dataset.
- **Salary Processing**: Automatically processes salary ranges and converts them to yearly salaries.
- **User Interaction**: The script includes prompts to allow users to load more job postings and save the results to a CSV file.

## Prerequisites

- Python 3.x
- `chromedriver` must be present in the project directory.
- Adzuna API credentials (`APP_ID` and `APP_KEY`) should be set in a `.env` file.

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-folder>

2. Install the required packages using pip:
    pip install -r requirements.txt

3. Add your Adzuna API credentials to a .env file in the root directory of the project:
    APP_ID=your_adzuna_app_id
    APP_KEY=your_adzuna_app_key

4. Download and place chromedriver in the project directory. Ensure it's compatible with your Chrome browser version

## License
This project is licensed under the MIT License.

