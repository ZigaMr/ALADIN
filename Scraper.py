import requests
import zipfile
import os
import pandas as pd
import xarray as xr
import xml.etree.ElementTree as ET
import cfgrib
from sqlalchemy import create_engine, MetaData, Table, Column, Float, String, text, inspect, Float
from datetime import datetime
import numpy as np

try:
    import ecmwflibs as findlibs
except ImportError:
    import findlibs


class WeatherDataParser:
    def __init__(self,
                 cities: list[str],
                 sql_user: str,
                 sql_password: str,
                 sql_port: str,
                 db_name: str,
                 ):
        self.cities = list(map(lambda x: x.upper(), cities))
        self.zip_url = 'https://meteo.arso.gov.si/uploads/probase/www/model/data/nwp_{}.zip'

        # MySQL connection string
        connection_string = f'mysql+pymysql://{sql_user}:{sql_password}@localhost:{sql_port}/'

        # Create a SQLAlchemy engine
        engine = create_engine(connection_string)
        # Create a database if it doesn't exist
        create_database_query = f'CREATE DATABASE IF NOT EXISTS {db_name}'
        with engine.connect() as connection:
            connection.execute(text(create_database_query))

        self.engine = create_engine('mysql+pymysql://{}:{}@localhost:{}/{}'.format(sql_user,
                                                                                   sql_password,
                                                                                   sql_port,
                                                                                   db_name)
                                    )
        # Create a MetaData object
        metadata = MetaData()
        self.location_table = Table(
            "location",
            metadata,
            Column('latitude', Float, nullable=False),
            Column('longitude', Float, nullable=False),
            Column('location_name', String(255), nullable=False),
        )

        # Create the database if it does not exist
        metadata.create_all(self.engine, checkfirst=True, tables=[self.location_table])

    def parse_xml(self, city: str):
        """
        Get coordinates for a specific town/area
        :param city: The name of the place
        :return: Latitude and longitude pair
        """
        resp = requests.get(
            'https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_{}_latest.xml'.format(
                city))
        root = ET.fromstring(resp.content)
        lat = root.find('metData').find('domain_lat').text
        lon = root.find('metData').find('domain_lon').text
        return [float(lat), float(lon)]

    def download_and_read_grib_files(self, url):
        """
        Download and transform the zip grib files from the url parameter for DB insert
        :param url: ARSO url parameter
        :return: list of pandas dataframes
        """

        if 'data.zip' in os.listdir():
            os.remove("data.zip")
        # Download the ZIP file
        response = requests.get(url)
        if response.status_code != 200:
            return
        with open("data.zip", "wb") as zip_file:
            zip_file.write(response.content)

        if "weather_data" in os.listdir():
            os.system("rm -rf weather_data")
        # Extract the zip file
        with zipfile.ZipFile("data.zip", "r") as zip_ref:
            zip_ref.extractall("weather_data")

        for ind, grib_file in enumerate(os.listdir("weather_data")):
            ds = cfgrib.open_datasets("weather_data/{}".format(grib_file))
            if ind == 0:
                data0 = ds[0].to_dataframe()
                data1 = ds[1].to_dataframe()
                data2 = ds[2].to_dataframe()
                data3 = ds[3].to_dataframe()
                data4 = ds[4].to_dataframe()
            else:
                data0 = pd.concat([data0, ds[0].to_dataframe()])
                data1 = pd.concat([data1, ds[1].to_dataframe()])
                data2 = pd.concat([data2, ds[2].to_dataframe()])
                data3 = pd.concat([data3, ds[3].to_dataframe()])
                data4 = pd.concat([data4, ds[4].to_dataframe()])

        data0 = data0.rename(columns={'r': ds[0].r.GRIB_cfName,
                                      't2m': ds[0].t2m.GRIB_cfName}).drop(columns=['step'])
        data1 = data1.rename(columns={'u10': ds[1].u10.GRIB_cfName,
                                      'v10': ds[1].v10.GRIB_cfName}).drop(columns=['step'])
        data2 = data2.rename(columns={'z': ds[2].z.GRIB_cfName,
                                      't': ds[2].t.GRIB_cfName,
                                      'u': ds[2].u.GRIB_cfName,
                                      'v': ds[2].v.GRIB_cfName,
                                      'r': ds[2].r.GRIB_cfName, }).drop(columns=['step'])
        data3 = data3.rename(columns={'msl': ds[3].msl.GRIB_cfName}).drop(columns=['step'])
        data4 = data4.rename(columns={'sp': ds[4].sp.GRIB_cfName,
                                      'tcc': 'tcc',
                                      'tp': 'tp'}).drop(columns=['step'])

        # Clean up: Delete the downloaded zip file and extracted data
        os.remove("data.zip")
        os.system("rm -rf weather_data")
        return [data0, data1, data2, data3, data4]

    def download_and_insert(self):
        """
        Checks the coordinates for specific locations, filters on .zip data and inserts new rows
        :return: None
        """

        locations = pd.read_sql('select * from location', self.engine)
        cities = [city.upper() for city in self.cities if city.upper() not in locations.location_name.values]
        conn = self.engine.connect()
        for city in cities:
            try:
                # Save coordinates to the database so we don't have to scrape every time
                coords = self.parse_xml(city.upper())
            except Exception as e:
                print(e)
                print(city)
            ins = self.location_table.insert().values(latitude=coords[0],
                                                      longitude=coords[1],
                                                      location_name=city.upper())
            conn.execute(ins)
            conn.commit()
            locations.loc[len(locations)] = coords + [city]
        conn.close()
        # Get the current time
        current_time = datetime.now()
        rounded_time = current_time.replace(hour=(current_time.hour // 6) * 6, minute=0, second=0, microsecond=0)

        url = self.zip_url.format(rounded_time.strftime('%Y%m%d-%H%M'))
        weather_data = self.download_and_read_grib_files(url)
        insp = inspect(self.engine)
        for ind, df in enumerate(weather_data):
            print('Inserting data: %s' % ind)
            # Check if table exists
            table_name = 'data' + str(ind)
            if insp.has_table(table_name):
                with self.engine.connect() as connection:
                    max_date = connection.execute(text(f'select max(time) from {table_name}')).all()[0][0]
                df = df[df.time > np.datetime64(max_date)]
            df_insert = df.reset_index()
            # Merge on latitude and longitude rounded to 1 decimal place
            df_insert = df_insert.merge(locations,
                                        left_on=[df_insert.latitude.round(1),
                                                 df_insert.longitude.round(1)],
                                        right_on=[locations.latitude.round(1),
                                                  locations.longitude.round(1)],
                                        suffixes=['', '_y']
                                        ).drop(columns=['latitude_y',
                                                        'longitude_y',
                                                        'location_name',
                                                        'key_0',
                                                        'key_1'])
            if not df_insert.empty:
                df_insert.to_sql(table_name,
                                 self.engine,
                                 index=False,
                                 if_exists='append')

        return


if __name__ == '__main__':
    import time

    cities_to_scrape = ['Kranj', 'Vogel', 'Ljubl-ana_bezigrad']
    parser = WeatherDataParser(cities_to_scrape,
                               'root',
                               'password',
                               '3306',
                               'Aladin')

    while True:
        parser.download_and_insert()
        # Sleep for 1h
        time.sleep(3600)
