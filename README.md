# ALADIN

Scraping tool for Arso prediction data https://meteo.arso.gov.si/uploads/meteo/help/sl/NumericniRezultatiGRIB.html.
Set to run every hour, it parses various predictions and stores them in a local MySql DB.

## Description:
The repo contains 2 python scripts, main.py and Scraper.py. The latter contains the scraper tool that is used to pull/transform/insert the data.
It is also set to update the DB every hour if we run the python script (python Scraper.py).
The former main.py script is to be run with a service or from a cronjob and thus does not contain a while loop.

## How to use:

1. Update the setup.sh script on line 29 to absolute path of your repo directory.
    ```
    chmod +x ./setup.sh
    ./setup.sh
    ```
    This repo assumes python 3.10.6. It might work with other versions, but the created environment contains the latest library versions, so best to set it to new python version (you can use pyenv global 3.10.6). Using setup.sh will create a cronjob to run main.py every hour and update the MySql accordingly. It creates the tables and new DB called Aladin. Monitor the db for new inputs.

2. Alternatively skip the setup, if you have MySql installed and know how to set the environment from requirements.txt. Run either main.py to test or Scraper.py to run a loop.


## DB schema    
On first run the tool creates Aladin db, with locations table mapping location to its latitude/longitude coordinates. 5 more tables are created (data0, data1, data2, data3, data4) that correspond to the data that we receive in GRIB format.

