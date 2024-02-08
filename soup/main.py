from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import os

def get_soup(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def get_archives(soup):    
    # On récupère le contenu de la page
    content = soup.select('tr th[colspan="4"] font[color="#FA8800"]')[0].find_next('tr').text.strip()
    archives = []
    date_regex = re.compile(r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b|\b\d{1,2}/\d{1,2}/\d{2}\b)')
    current_date = None
    current_content = ''
    
    # On parcourt le contenu ligne par ligne et on split les archives par date
    for line in content.split('\n'):
        if line != '':
            match = date_regex.search(line)
            if match:
                if current_date:
                    archives.append((current_date, current_content.strip()))
                current_date, current_content = line.split(' - ', 1) if ' - ' in line else (match.group(), line[match.end():].strip())
            else:
                current_content += ' ' + line
    if current_date:
        archives.append((current_date, current_content.strip()))
    
    df = pd.DataFrame.from_records(archives, columns=['date', 'content'])
    
    json_file_path = os.path.join(os.path.dirname(__file__), 'archives.json')
    df.to_json(json_file_path, orient='records')
    
    return archives

def get_crews(url):
    soup = get_soup(url)
    
    crews_table = soup.select('body > font:nth-child(2) > center:nth-child(1) > p:nth-child(2) > table:nth-child(1)')[0]
    
    crews_info = []
    
    # On parcourt le tableau des équipages
    for row in crews_table.find_all('tr')[1:]:
        columns = row.find_all('td')
        
        if len(columns) == 3:
            flight_number = columns[0].text.strip()
            prime_crew = columns[1].text.strip().split('\n')
            backup_crew = columns[2].text.strip().split('\n')
            js_link = columns[0].find('a')['href'] if columns[0].find('a') else None
            
            if js_link:
                file_name = js_link.split("'")[1]
                crew_image_link = f"https://apolloarchive.com/apollo/{file_name}.jpg"
            else:
                crew_image_link = None
            
            # On stocke les informations dans un dictionnaire, pour les membres de l'équipage on split le nom et le rôle
            crew_details = {
                'Crew Image Link': crew_image_link,
                'Flight Number': flight_number,
                'Prime Crew': [{'Name': name.split(' (')[0], 'Role': 'Commander' if idx == 0 else 'Command Module Pilot' if idx == 1 else 'Lunar Module Pilot'} for idx, name in enumerate(prime_crew)],
                'Backup Crew': [{'Name': name.split(' (')[0], 'Role': 'Commander' if idx == 0 else 'Command Module Pilot' if idx == 1 else 'Lunar Module Pilot'} for idx, name in enumerate(backup_crew if backup_crew[0] != '' else [])],
            }
            
            crews_info.append(crew_details)

    df = pd.DataFrame.from_records(crews_info)
    json_file_path = os.path.join(os.path.dirname(__file__), 'crews.json')
    df.to_json(json_file_path, orient='records')
    
    return crews_info

def get_medias(url):
    soup = get_soup(url)
    
    medias_table = soup.select('body > center:nth-child(1)')[0]
    
    media_info = []
    current_mission = None

    fileloc = {
        1: "apollo/",
        2: "apollo/multimedia/",
        3: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a410/",
        4: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/",
        5: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a12/",
        6: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a13/",
        7: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a14/",
        8: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a15/",
        9: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a16/",
        10: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/a17/",
        11: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/misc/",
        12: "http://www.nasa.gov/wp-content/uploads/static/history/alsj/ktclips/",
        13: "apollo/multimedia/"
    }

    filetype = {1: ".mpg", 2: ".wav", 3: ".ram", 4: ".rm", 5: ".mp3"}

    for element in medias_table.find_all('tr'):
        mission_header = element.find('span', class_='secthdr')
        if mission_header:
            current_mission = mission_header.text.strip()
            continue

        columns = element.find_all('td')
        if len(columns) == 5:
            file_type = columns[0].text.strip()
            description_element = columns[3].find('a')
            if description_element:
                onclick_value = description_element.get('href')
                if onclick_value and "loadclip" in onclick_value:
                    params = onclick_value.split('loadclip(')[1].rstrip(')').split(',')
                    locnum = int(params[0])
                    filename = params[1].strip("'")
                    typenum = int(params[2])
                    
                    # Création du lien de téléchargement
                    if locnum in fileloc and typenum in filetype:
                        download_link = f"https://apolloarchive.com/{fileloc[locnum]}{filename}{filetype[typenum]}"
                    else:
                        download_link = None
                else:
                    download_link = None

                media_details = {
                    'Mission': current_mission,
                    'File Type': file_type,
                    'Description': columns[3].text.strip(),
                    'Download Link': download_link
                }
                media_info.append(media_details)

    df = pd.DataFrame.from_records(media_info)
    json_file_path = os.path.join(os.path.dirname(__file__), 'media.json')
    df.to_json(json_file_path, orient='records')

    return media_info

if __name__ == '__main__':
    soup = get_soup('https://apolloarchive.com/aparch_main.html')
    archives = get_archives(soup)
    crews = get_crews('https://apolloarchive.com/aparch_crews.html')
    medias = get_medias('https://apolloarchive.com/aparch_multimedia.html')