import requests
import zipfile
import os
import xarray as xr
import xml.etree.ElementTree as ET
import cfgrib
try:
    import ecmwflibs as findlibs
except ImportError:
    import findlibs




class WeatherDataParser:
    def __init__(self, cities):
        self.cities = list(map(lambda x: x.upper(), cities))

    def parse_xml(self, city):
        """
        Get coordinates for a specific town/area
        :param city: The name of the place
        :return: Latitude and longitude pair
        """
        resp = requests.get('https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_{}_latest.xml'.format(city))
        root = ET.fromstring(resp.content)
        lat = root.find('metData').find('domain_lat').text
        lon = root.find('metData').find('domain_lon').text
        return lat, lon

    def download_and_read_grib_files(self, url):
        # Download the ZIP file
        response = requests.get(url)
        zip_filename = 'data.zip'
        with open(zip_filename, 'wb') as zip_file:
            zip_file.write(response.content)

        # Extract and read GRIB files from the ZIP
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            for ind, file_info in enumerate(zip_ref.infolist()):
                with zip_ref.open(file_info) as grib_file:
                    ds = cfgrib.open_datasets(grib_file)
                    if ind == 0:
                        data0 = ds[0].to_dataframe()
                        data1 = ds[1].to_dataframe()
                        data2 = ds[2].to_dataframe()
                        data3 = ds[3].to_dataframe()
                        data4 = ds[4].to_dataframe()
                    else:
                        data0 = data0.append(ds[0].to_dataframe())
                        data1 = data1.append(ds[1].to_dataframe())
                        data2 = data2.append(ds[2].to_dataframe())
                        data3 = data3.append(ds[3].to_dataframe())
                        data4 = data4.append(ds[4].to_dataframe())

                    ds.close()
        data0 = data0.rename(columns={'r': data0.r.GRIB_cfName,
                                                     't2m': data0.t2m.GRIB_cfName}).drop(columns=['step'])
        data1 = data1.rename(columns={'u10': data1.u10.GRIB_cfName,
                                                     'v10': data1.v10.GRIB_cfName}).drop(columns=['step'])
        data2 = data2.rename(columns={'z': data2.z.GRIB_cfName,
                                                     't': data2.t.GRIB_cfName,
                                                     'u': data2.u.GRIB_cfName,
                                                     'v': data2.v.GRIB_cfName,
                                                     'r': data2.r.GRIB_cfName, }).drop(columns=['step'])
        data3 = data3.rename(columns={'msl': data3.u10.GRIB_cfName}).drop(columns=['step'])
        data4 = data4.rename(columns={'sp': data4.sp.GRIB_cfName,
                                      'tcc': data4.tcc.GRIB_cfName,
                                      'tp': data4.up.GRIB_cfName}).drop(columns=['step'])
        # Clean up the downloaded ZIP file
        os.remove(zip_filename)
        return [data0, data1, data2, data3, data4]


# Example usage
cities_to_scrape = ['Vogel', 'Ljubljana', 'Maribor']
xml_url = 'https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_VOGEL_latest.xml'
zip_url = 'https://meteo.arso.gov.si/uploads/probase/www/model/data/nwp_20230616-0600.zip'

if __name__ == '__main__':
    parser = WeatherDataParser(cities_to_scrape)
    parser.parse_xml(xml_url)

    merged_dataframe = parser.read_grib_files(zip_url)
    print(merged_dataframe)