from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import time
import pandas as pd
import requests
import sqlite3

from utils import paths_dict, getText_js

# LinkedIn's search is notorious for a few things: displaying irrelevant content, 
# search limits, and protections against web scraping

# I found out that search results seem more accurate when you are not logged in, 
# however when you click on a job for more info, and then click back, 
# you are forced to log in

# so this script is designed to get all the job links, open each link in a new window, 
# extract the data, then close the window and open the next and so on

def main():
    # Set up database to store job links 
    conn = sqlite3.connect('jobs_bank.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs(link TEXT PRIMARY KEY)''')
    cursor.execute("SELECT link FROM jobs")
    data = cursor.fetchall()
    jobsBank = set(item[0] for item in data)

    start_time = time.time()
    # Define your keywords
    fullStackKey = "Full Stack Developer"
    frontEndKey = "Front End Developer"
    backEndKey = "Back End Developer"
    junior = "Junior Developer"
    solutionsEng = "Solutions Engineer"
    integrator = "Software Integrator"
    country_name = "Israel"
    # country_name = "United States"

    # split the names into words, and join them together w url encoding for the space character
    job_url = "%20".join(solutionsEng.split(" "))
    country_url = "%20".join(country_name.split(" "))

    # Define url with desired keywords
    url = "https://www.linkedin.com/jobs/search?keywords={0}&location={1}&geoId=101620260&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0".format(job_url,country_url)
    # Create a webdriver instance and get page (function defined below)
    driver = start_driver_get_url(False, url)
    
    filtersPath = "/html/body/div/section/div/div/div/form/ul"

    # # select remote filter
    # remotePath = f"{filtersPath}/li[6]/div/div"
    # remFilter = driver.find_element(By.XPATH, f"{remotePath}/button")
    # remFilter.click()
    # remote = driver.find_element(By.XPATH, f"{remotePath}/div/div/div/div[3]/input")
    # remote.click()
    # done = driver.find_element(By.XPATH, f"{remotePath}/div/button")
    # done.click()

    # select experience filters
    experPath = f"{filtersPath}/li[5]/div/div"
    # click experience filter
    experFilter = driver.find_element(By.XPATH, f"{experPath}/button")    
    experFilter.click()
    # iterate through list of experience checkboxes and select desired boxes
    parent_div = driver.find_element(By.XPATH, f"{experPath}/div/div/div")
    child_divs = parent_div.find_elements(By.XPATH, "./div")
    desired_labels = ['Internship', 'Entry level']

    for child in child_divs:
        label = child.find_element(By.XPATH, "./label").text
        input = child.find_element(By.XPATH, "./input")
        label_text = label.split('(')[0].strip()

        if label_text in desired_labels:
            input.click()

    # click done
    done = driver.find_element(By.XPATH, f"{experPath}/div/button")
    done.click()

    # Find how many jobs there are
    jobs_num = driver.find_element(By.XPATH,'//*[@id="main-content"]/div/h1/span[1]').get_attribute("innerText")
    # remove the + from the string
    if not jobs_num[-1].isdigit():
        jobs_num = jobs_num[:-1]
        
    if len(jobs_num.split(',')) > 1:
        jobs_num = int(jobs_num.replace(",", ""))
    else:
        jobs_num = int(jobs_num)

    print(jobs_num)
    # Declare variables
    job_link_set = set() # Sets use hash tables to store elements
    job_title_list = []
    company_name_list = []
    location_list = []
    date_list = []
    job_link_list = []
    seniority_list = []
    jd_list = [] #job_description

    # assuming that after scrolling down half as many times as there are listings, 
    # most or all of the remaining listings will have loaded and will be displayed.
    i = 0
    while i <= int(jobs_num/2)+1:
        # Keep scrolling down to the end of the view.
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Track # of scrolls
        i = i + 1
        print("Current at: ", i, "Percentage at: ", ((i+1)/(int(jobs_num/2)+1))*100, "%",end="\r")

        try:
            # Try to click on the load more results button in case it is already displayed.
            infinite_scroller_button = driver.find_element(By.XPATH, ".//button[@aria-label='See more jobs']")
            infinite_scroller_button.click()
            time.sleep(0.1)
        except:
            # If there is no button, there will be an error, and the loop will start again
            time.sleep(0.1)
            pass

    # Get the job list element
    job_list_element = driver.find_element(By.CLASS_NAME,"jobs-search__results-list")
    # go to each job and get its link
    jobs = job_list_element.find_elements(By.TAG_NAME, "li")

    for job in jobs:
        job_aTag = job.find_element(By.TAG_NAME,"a")
        link = job_aTag.get_attribute("href")
        if link not in jobsBank:
            job_link_set.add(link)
            cursor.execute("INSERT INTO jobs (link) VALUES (?)", (link,))
            conn.commit()

    driver.quit()

    levels = ["Mid-Senior level", "Senior level", "Director", "Executive", "Senior developer", "Tech lead" , "Chief technology officer"]
    # Loop over jobs and extract data
    for job_link in job_link_set:
        retry_count = 0
        max_retries = 2
        while retry_count < max_retries:
            try:
                driver = start_driver_get_url(False, job_link)
                # if seniority is too high, go to next job
                seniority_element = driver.find_element(By.XPATH, paths_dict["seniority_path"])
                if seniority_element.text in levels:
                    driver.quit()
                    break
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                driver.quit()
                break

            # To reduce # of calls to browser, get all elements from one parent element
            try:
                parent = driver.find_element(By.XPATH, "/html/body/main/section/div")
                retry_count = max_retries
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                driver.quit()
                break
        
        # collect data from each job
        #job description
        try:
            # click on show more
            show_more_element =  parent.find_element(By.XPATH, paths_dict["show_more_path"])
            show_more_element.click()
            # get job description element
            jd_parent_element = parent.find_element(By.XPATH, paths_dict["jd_parent_path"])
            # get all text from all children elements inside job description
            text_list = driver.execute_script(getText_js, jd_parent_element)
            # join together all text but separate with a new line between elements
            jd_text = '\n'.join(text_list)
#########################################################  THIS SECTION CAN BE COMMENTED OUT
            # analyse texts and look for "junior" or "entry-level" - continue if false
            titleText = parent.find_element(By.XPATH, paths_dict["job_title_path"]).get_attribute("innerText").lower()
            seniorityText = seniority_element.text.lower()

            fullString = jd_text.lower() + titleText + seniorityText
            if not ("junior" in fullString or "entry level" in fullString or "jr" in fullString):
                driver.quit()
                continue
#######################################################################################################################
            # If applicable, only extract the text after "Requirements"
            if "Requirements" in jd_text:
                following_text = jd_text[jd_text.index("Requirements") + len("Requirements"):].strip()
                jd_list.append(following_text)
            else:
                jd_list.append('\n'.join(text_list))
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            jd_list.append(None)
            driver.quit()
            continue
        #seniority
        custom_append(parent, find_by_xpath, paths_dict["seniority_path"], "innerText", seniority_list)
        #job_title
        custom_append(parent, find_by_xpath, paths_dict["job_title_path"], "innerText", job_title_list)  
        #company_name
        custom_append(parent, find_by_xpath, paths_dict["company_name_path"], "innerText", company_name_list)
        #location
        custom_append(parent, find_by_xpath, paths_dict["location_path"], "innerText", location_list)
        #date
        custom_append(parent, find_by_xpath, paths_dict["date_path"], "innerText", date_list) 
        #job_link
        job_link_list.append(job_link)

        # close the current window
        driver.quit()

    # Create a Pandas dataFrame for the data
    job_data = pd.DataFrame({
        'Date': date_list,
        'Company': company_name_list,
        'Title': job_title_list,
        'Location': location_list,
        'Description': jd_list,
        'Level': seniority_list,
        'Link': job_link_list
    })

    # Shorten URLs in 'Link' column
    job_data['Link'] = job_data['Link'].apply(shorten_url)

    # Create hyperlinks in 'Link' column
    job_data['Link'] = job_data['Link'].apply(lambda x: f'=HYPERLINK("{x}", "{x}")')

    # Reset the index
    job_data.reset_index(drop=True, inplace=True)

    # Write the data to CSV
    csv = "jobs.csv"
    csv_exists = os.path.isfile(csv)
    # Read the existing CSV file (if it exists) to retrieve the maximum index value
    if csv_exists:
        existing_data = pd.read_csv(csv)
        max_index = existing_data.index.max()
    else:
        max_index = -1  # If the file doesn't exist, set the max_index to -1

    # Reset the index starting from the maximum index value + 1
    job_data.reset_index(drop=True, inplace=True)
    job_data.index += max_index + 1

    mode = 'a' if csv_exists else 'w'
    header = not csv_exists  # Include header row only if file doesn't exist
    job_data.to_csv(csv, mode=mode, header=header, encoding='utf-8-sig', escapechar='\\')

    end_time = time.time()
    print(f"Program took {end_time - start_time:.2f} seconds to run.")

    
# Define function to shorten URL using TinyURL API
def shorten_url(url):
    api_url = "https://tinyurl.com/api-create.php?url="
    response = requests.get(api_url + url)
    return response.text

def start_driver_get_url(headlessMode, url):
    s = Service("C:/Users/Pro/Drivers/chromedriver/chromedriver.exe")
    options = Options()
    if headlessMode: 
        options.headless = True
        driver = webdriver.Chrome(service=s, options=options)
    else:
        driver = webdriver.Chrome(service=s)
    # Navigate to job_link
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
    return driver


def find_by_selector(selector_type):
    return lambda driver, val, att: driver.find_element(selector_type, val).get_attribute(att)

find_by_class_name = find_by_selector(By.CLASS_NAME)
find_by_css_selector = find_by_selector(By.CSS_SELECTOR)
find_by_xpath = find_by_selector(By.XPATH)

def custom_append(element, find_func, selector_value, attribute, target_list):
    try:
        data = find_func(element, selector_value, attribute)
        if data:
            target_list.append(data)
        else:
            target_list.append(None)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        target_list.append(None)


main()