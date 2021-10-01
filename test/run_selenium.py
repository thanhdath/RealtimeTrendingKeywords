from selenium import webdriver
import selenium
import time
chrome_options = webdriver.ChromeOptions()
chrome_options.binary_location = r"C:\Program Files (x86)\Google\Chrome Beta\Application\chrome.exe"

prefs = {"profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", prefs)
# chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
driver = webdriver.Chrome(
    executable_path=r"D:/HUST/BI/BI/chromedriver.exe",
    chrome_options=chrome_options
)


driver.get('http://www.google.com/')
time.sleep(5) # Let the user actually see something!
search_box = driver.find_element_by_name('q')
search_box.send_keys('ChromeDriver')
search_box.submit()
time.sleep(5) # Let the user actually see something!
driver.quit()