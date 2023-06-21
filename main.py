from Scraper import WeatherDataParser

if __name__ == '__main__':
    cities_to_scrape = ['Kranj', 'Vogel', 'Ljubl-ana_bezigrad']
    parser = WeatherDataParser(cities_to_scrape,
                               'root',
                               'password',
                               '3306',
                               'Aladin')
    data = parser.download_and_insert()