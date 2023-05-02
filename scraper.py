from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import pandas as pd

# LinkedIn's search is notorious for a few things: displaying irrelevant content, 
# search limits, and protections against web scraping

# I found out that search results seem more accurate when you are not logged in, 
# however when you click on a job for more info, and then click back, 
# you are forced to log in

# so this script is designed to get all the job links, open each link in a new window, 
# extract the data, then close the window and open the next and so on

def main():
    start_time = time.time()
    # Define your keywords
    job_name = "Data Analyst"
    country_name = "United States"

    job_url =""
    for item in job_name.split(" "):
        if item != job_name.split(" ")[-1]:
            job_url = job_url + item + "%20"
        else:
            job_url = job_url + item

    country_url =""
    for item in country_name.split(" "):
        if item != country_name.split(" ")[-1]:
            country_url = country_url + item + "%20"
        else:
            country_url = country_url + item

    # Define url with desired keywords
    url = "https://www.linkedin.com/jobs/search?keywords={0}&location={1}&geoId=103644278&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0".format(job_url,country_url)

    # Create a webdriver instance
    s = Service("C:/Users/Pro/Drivers/chromedriver/chromedriver.exe")
    driver = webdriver.Chrome(service=s)

    # Opening the url we have just defined in our browser
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
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
    i = 2
    # while i <= int(jobs_num/2)+1:
    while i <= 2:
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
        job_link_set.add(link)

    driver.quit()

    # Loop over jobs and extract data
    for job_link in job_link_set:
        try:
            driver = webdriver.Chrome()
            # Navigate to job_link
            driver.get(job_link)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
            # time.sleep(3)
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        # To reduce # of calls to browser, get all needed elements
        # in one call
        paths_dict = {
            'show_more_path': '/html/body/main/section/div/div/section/div/div/section/button',
            'seniority_path': '/html/body/main/section/div/div/section/div/ul/li/span',
            'job_title_path': '/html/body/main/section/div/section[2]/div/div/div/h1',
            'company_name_path': '/html/body/main/section/div/section[2]/div/div/div/h4/div/span/a',
            'location_path': '/html/body/main/section/div/section[2]/div/div/div/h4/div/span[2]',
            'date_path': '/html/body/main/section/div/section[2]/div/div/div/h4/div[2]/span',
            'jd_parent_path': '/html/body/main/section/div/div/section/div/div/section'
        }
        
        # collect data from each job
        #seniority
        custom_append(driver, find_by_xpath, paths_dict["seniority_path"], "innerText", seniority_list) 
        #job_title
        custom_append(driver, find_by_xpath, paths_dict["job_title_path"], "innerText", job_title_list)  
        #company_name
        custom_append(driver, find_by_xpath, paths_dict["company_name_path"], "innerText", company_name_list)
        #location
        custom_append(driver, find_by_xpath, paths_dict["location_path"], "innerText", location_list)
        #date
        custom_append(driver, find_by_xpath, paths_dict["date_path"], "innerText", date_list) 
        #job_link
        job_link_list.append(job_link)

        #job description
        try:
            # click on show more
            show_more_element =  driver.find_element(By.XPATH, paths_dict["show_more_path"])
            show_more_element.click()
            # get job description element
            parent_element = driver.find_element(By.XPATH, paths_dict["jd_parent_path"])
            # get all text from all children elements inside job description
            text_list = driver.execute_script("""
                const parent = arguments[0];
                const descendants = parent.childNodes;
                let text_list = [];
                for (let i = 0; i < descendants.length; i++) {
                    const element = descendants[i];
                    if (element.nodeType === Node.ELEMENT_NODE) {
                        const element_text = element.textContent.trim();
                        if (element_text !== '') {
                            text_list.push(element_text);
                        }
                    }
                }
                return text_list;
            """, parent_element)
            # join together all text but separate with a new line between elements
            jd_list.append('\n'.join(text_list))
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            jd_list.append(None)
        # close the current window
        driver.quit()

    print(company_name_list, date_list, seniority_list)
    # Create a Pandas dataFrame for the data
    job_data = pd.DataFrame({
        'Date': date_list,
        'Company': company_name_list,
        'Title': job_title_list,
        'Location': location_list,
        'Description': jd_list,
        'Level': seniority_list,
        'Link': job_link
    })
    # Create your csv buddy
    job_data.to_csv('jobs.csv')

    end_time = time.time()
    print(f"Program took {end_time - start_time:.2f} seconds to run.")
    


def find_by_selector(selector_type):
    return lambda driver, val, att: driver.find_element(selector_type, val).get_attribute(att)

find_by_class_name = find_by_selector(By.CLASS_NAME)
find_by_css_selector = find_by_selector(By.CSS_SELECTOR)
find_by_xpath = find_by_selector(By.XPATH)

def custom_append(job, find_func, selector_value, attribute, target_list):
    try:
        data = find_func(job, selector_value, attribute)
        if data:
            target_list.append(data)
        else:
            target_list.append(None)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        target_list.append(None)


main()
    # # Login and enter the email address and password in the input fields
    # driver.get("https://www.linkedin.com/login")
    # email_field = driver.find_element(By.ID,"username")
    # email_field.send_keys("jeremyleopold.hw@gmail.com")

    # password_field = driver.find_element(By.ID,"password")
    # password_field.send_keys("LeoChief10")
    # # Submit the form by pressing the "Enter" key
    # password_field.send_keys(Keys.RETURN)

    # # Wait for the login process to complete and the page to load
    # time.sleep(3)
    # input("If security check, satisfy and then press enter. Otherwise, just press enter")

    # # Verify that the login was successful by checking the page title
    # assert "LinkedIn" in driver.title