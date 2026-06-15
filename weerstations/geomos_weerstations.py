import requests
import time
import math
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
from datetime import datetime, timezone, timedelta
import urllib.parse
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import schedule
from shapely.geometry import Point
import numpy as np
from zoneinfo import ZoneInfo
import traceback
import xml.etree.ElementTree as ET
import json
import ast

def process_observations_xml(api_data):

    xml_data = api_data.text
    root = ET.fromstring(xml_data)

    # Extract namespace from root
    ns = {"ns": root.tag.split("}")[0].strip("{")}

    # -----------------------------
    # 3. Locate all <Observation> elements
    # -----------------------------
    observations = []

    # Iterate through each <Epoch> inside <ObservationsByEpoch>
    for epoch in root.findall(".//ns:ObservationsByEpoch/ns:Epoch", ns):
        obs_elem = epoch.find("ns:Observations", ns)
        if obs_elem is not None:
            for obs in obs_elem.findall("ns:Observation", ns):
                record = {}
                for field in obs:
                    tag = field.tag.split("}")[-1]  # remove namespace
                    record[tag] = field.text
                observations.append(record)

    # -----------------------------
    # 4. Convert to JSON and print
    # -----------------------------
    observations_json = json.dumps(observations, indent=2)

    return observations_json

def process_observation_data(observations):

    processed_observations = list()
    observations = ast.literal_eval(observations)

    for observation in observations:

        if int(observation["ObservationTypeId"]) == 311:  #windspeed

            observation["Windspeed"] = observation["Value"]
            observation["WindDirection"] = None
            observation["Temperature"] = None 
            observation["Humidity"] = None
            processed_observations.append(observation)

        elif int(observation["ObservationTypeId"]) == 310: #Wind direction

            observation["Windspeed"] = None
            observation["WindDirection"] = observation["Value"]
            observation["Temperature"] = None 
            observation["Humidity"] = None
            processed_observations.append(observation)
            
        elif int(observation["ObservationTypeId"]) == 181: #Temperature

            observation["Windspeed"] = None
            observation["WindDirection"] = None
            observation["Temperature"] = observation["Value"] 
            observation["Humidity"] = None
            processed_observations.append(observation)

        elif int(observation["ObservationTypeId"]) == 183: #humidity

            observation["Windspeed"] = None
            observation["WindDirection"] = None
            observation["Temperature"] = None
            observation["Humidity"] = observation["Value"] 
            processed_observations.append(observation)

    return processed_observations

def request_geomos_api(api_url):

    attempt = 1
    while True:
        try:
            if attempt >= 3:
                return {}
            else:
                api_data = requests.get(api_url)
                observations = process_observations_xml(api_data)
                observations = process_observation_data(observations)

                return observations
            
        except Exception as e:
            print(f"Geomos API request failed because of the following error {e}")
            attempt += 1
            time.sleep(0.5)

def get_latest_UTC_timestamp(grafana_db_host, grafana_db_user, grafana_db_password,
                             grafana_db_name, grafana_db_port, table_name_measurements):

    max_attempts = 3
    connection_string = (
        f"mysql+pymysql://{grafana_db_user}:{grafana_db_password}"
        f"@{grafana_db_host}:{grafana_db_port}/{grafana_db_name}"
    )

    for attempt in range(1, max_attempts + 1):
        try:
            # Create SQLAlchemy engine
            engine = create_engine(connection_string)
            inspector = inspect(engine)

            # Check if table exists
            if not inspector.has_table(table_name_measurements):
                print(f"⚠️ Table '{table_name_measurements}' does not exist — returning epoch timestamp")
                return datetime(2024, 12, 2, 15, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

            # Query latest timestamp
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT MAX(Timestamp) FROM `{table_name_measurements}`")
                ).fetchone()

            return (
                result[0]
                if result and result[0] else datetime(2024, 15, 2, 12, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            )

        except SQLAlchemyError as e:
            print(f"⚠️ Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt == max_attempts:
                return None
            time.sleep(1)  # wait before retry

def get_project_observations(host, port, api_key, projectid, genericsensorid, latest_UTC_timestamp, current_utc_time):

    project_observations = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/genericsensors/{genericsensorid}/observations?apiKey={api_key}&startTime={latest_UTC_timestamp}&endTime={current_utc_time}")

    if project_observations:
        observation_df = pd.DataFrame(project_observations).astype({"Windspeed": "float64", "WindDirection": "float64", "Temperature": "float64",  
                                                                    "Humidity": "float64"})
        
        observation_df_avg = (
        observation_df.groupby("Epoch", as_index=False)
        .agg({"Windspeed": "mean", "WindDirection": "mean", "Temperature": "mean", "Humidity": "mean"})
        )

        return observation_df_avg
    
def export_data_to_SQL(input_data, grafana_db_host, grafana_db_user, grafana_db_password, grafana_db_name, grafana_db_port, table_name):
    
    attempt = 1
    while True:
        try:
            if attempt > 3:
                print("data upload to database failed")
                break
            else:
                connection_string = f"mysql+pymysql://{grafana_db_user}:{grafana_db_password}@{grafana_db_host}:{grafana_db_port}/{grafana_db_name}"
                engine = create_engine(connection_string)
                if inspect(engine).has_table(table_name):
                    input_data.to_sql(
                        table_name,
                        con=engine,
                        index=False,
                        if_exists="append"     # creates the table if it does not exist
                    )

                    print("Data succesfully pushed to database")
                    break
                else:
                    input_data.to_sql(
                        table_name,
                        con=engine,
                        index=False,
                        if_exists="fail"     # creates the table if it does not exist
                    )

                    print("Data succesfully pushed to database")
                    break
        except:
            time.sleep(1)
            attempt += 1

def structure_timestamps(series):

    s = series.str.rstrip("Z")
    has_fraction = s.str.contains(r"\.")
    main = s.where(~has_fraction, s.str.split(".").str[0])
    frac = s.where(~has_fraction, s.str.split(".").str[1].str[:6])  
    cleaned = main.where(~has_fraction, main + "." + frac)
    dt = pd.to_datetime(cleaned, format="%Y-%m-%dT%H:%M:%S.%f", utc=True)
    dt = dt + pd.Timedelta(seconds=1)

    return dt

def main(geomos_host, geomos_port, geomos_api_key, geomos_projectid,grafana_db_host, grafana_db_user, 
        grafana_db_password, grafana_db_name, grafana_db_port):

    for weerstation_name, weerstation in {"Weerstation1": 11, "Weerstation2": 7}.items():
        latest_UTC_timestamp = get_latest_UTC_timestamp(grafana_db_host, grafana_db_user, grafana_db_password, grafana_db_name, grafana_db_port, weerstation_name)
        current_UTC_time = datetime.now(timezone.utc)
        observations = get_project_observations(geomos_host, geomos_port, geomos_api_key, geomos_projectid, weerstation, 
                                                latest_UTC_timestamp, current_UTC_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z")
        
        observations = observations.rename(columns={'Epoch': 'Timestamp'})
        observations["Timestamp"] = structure_timestamps(observations["Timestamp"])
        observations["Timestamp"] = observations["Timestamp"].dt.tz_localize(None)
        observations["WindDirection"] = observations["WindDirection"] * (200 / np.pi)
        
        export_data_to_SQL(observations, grafana_db_host, grafana_db_user, 
                            grafana_db_password, grafana_db_name, grafana_db_port, weerstation_name)

if __name__ == "__main__":

    load_dotenv()

    # Input configuration for Geomos
    geomos_host = os.getenv("GEOMOS_HOST")
    geomos_port = os.getenv("GEOMOS_PORT")
    geomos_api_key = os.getenv("GEOMOS_API_KEY")
    geomos_projectid = os.getenv("GEOMOS_PROJECTID")

    # Input configuration for Grafana database (output measurements)
    grafana_db_host = os.getenv("GRAFANA_DB_HOST")
    grafana_db_user = os.getenv("GRAFANA_DB_USER")
    grafana_db_password = urllib.parse.quote_plus(os.getenv("GRAFANA_DB_PASSWORD"))
    grafana_db_name = os.getenv("GRAFANA_DB_NAME")
    grafana_db_port = os.getenv("GRAFANA_DB_PORT")

    main(geomos_host, geomos_port, geomos_api_key, geomos_projectid,grafana_db_host, grafana_db_user, 
        grafana_db_password, grafana_db_name, grafana_db_port)

    schedule.every(30).minutes.do(
    main,
    geomos_host=geomos_host,
    geomos_port=geomos_port,
    geomos_api_key=geomos_api_key,
    geomos_projectid=geomos_projectid,
    grafana_db_host=grafana_db_host,
    grafana_db_user=grafana_db_user,
    grafana_db_password=grafana_db_password,
    grafana_db_name=grafana_db_name,
    grafana_db_port=grafana_db_port
)
    
    while True:
        schedule.run_pending()
        time.sleep(10)
