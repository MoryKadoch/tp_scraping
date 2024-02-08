from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def get_weather():
    # Configuration MongoDB
    mongo_uri = os.getenv('MONGO_URI')
    client = MongoClient(mongo_uri)
    db = client.weather_database
    collection = db.weather

    driver = webdriver.Chrome()
    driver.get('https://www.accuweather.com')

    # Gestion des popups
    popups = [('fc-button-label', By.CLASS_NAME), ('policy-accept', By.CLASS_NAME)]
    for popup_text, by_method in popups:
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by_method, popup_text))).click()
        except Exception as e:
            print(f"Popup {popup_text} non trouvé : {e}")

    cities = ['Paris', 'Bordeaux', 'Marseille', 'Lille']

    for city in cities:
        try:
            search_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, 'search-input')))
            search_input.clear()
            search_input.send_keys(city + Keys.RETURN)

            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, f"//p[@class='location-name' and contains(text(), '{city}')]"))).click()

            temp = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, 'temp'))).text
            conditions = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'span.phrase'))).text

            print(f"La température à {city} est de {temp}")
            print(f"Les conditions météo à {city} sont {conditions}")

            forecasts = collect_forecasts(driver)

            air_quality_text = collect_air_quality(driver, city)

            data = {
                'City': city,
                'Temperature': temp,
                'Conditions': conditions,
                'Forecasts': forecasts,
                'Air Quality': air_quality_text
            }

            save_to_json(data, city)
            save_to_mongo(collection, data)

        except Exception as e:
            print(f"Erreur lors de la recherche pour {city} : {e}")

    driver.quit()

def collect_forecasts(driver):
    all_previsions = []
    previsions = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.daily-list-item')))
    for prevision in previsions:
        date = prevision.find_element(By.CLASS_NAME, 'date').text
        temp_hi = prevision.find_element(By.CLASS_NAME, 'temp-hi').text
        temp_lo = prevision.find_element(By.CLASS_NAME, 'temp-lo').text
        all_previsions.append({
            'Date': date,
            'High': temp_hi,
            'Low': temp_lo
        })
    return all_previsions

def collect_air_quality(driver, city):
    try:
        air_quality_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-qa="airQuality"]')))
        driver.execute_script("arguments[0].click();", air_quality_link)
        air_quality_value = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.aq-number-container')))
        return air_quality_value.text.strip()
    except Exception as e:
        print(f"Impossible de récupérer la qualité de l'air pour {city} : {e}")
        return "Non disponible"

def save_to_json(data, city):
    df = pd.DataFrame.from_records([data])
    json_file_path = os.path.join(os.path.dirname(__file__), f"{city.lower()}.json")
    df.to_json(json_file_path, orient='records')

def save_to_mongo(collection, data):
    collection.insert_one(data)

if __name__ == '__main__':
    get_weather()
