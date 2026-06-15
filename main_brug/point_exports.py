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
from shapely.geometry import Point, LineString
import numpy as np
from zoneinfo import ZoneInfo
import traceback
import json
from pathlib import Path

def request_geomos_api(api_url):

    attempt = 1
    while True:
        try:
            if attempt >= 3:
                return {}
            else:
                api_data = requests.get(api_url).json()
                return api_data
        except Exception as e:
            print(f"Geomos API request failed because of the following error {e}")
            attempt += 1
            time.sleep(0.5)

def get_project_points(host, port, api_key, projectid):

    project_points_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/pointsjson?apiKey={api_key}")

    if project_points_json:
        project_points_df = pd.DataFrame(project_points_json['Points']).drop(['Easting', 'Northing', "Height", 'ProfileId'], axis=1)
        project_point_ids = project_points_df["Id"].tolist()

        return project_points_df, project_point_ids
    else:
        return pd.DataFrame(),[]
    
def create_pointIds(project_points_ids):

    return [str(point_id) for point_id in project_points_ids] 

def get_point_results(host, port, api_key, projectid, project_points_ids, latest_UTC_timestamp, current_utc_time):

    results_list = list()
    id_strings = create_pointIds(project_points_ids)

    for id_string in id_strings:
        point_result_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/resultsjson?pointsIds={id_string}&apiKey={api_key}&startTime={latest_UTC_timestamp}&endTime={current_utc_time}")
        if point_result_json["Results"]:
            results_list.extend(point_result_json["Results"])
    
    result_df = pd.DataFrame(results_list)
    
    return result_df

def translate_to_bridgesystem(rd_coordinate_x, rd_coordinate_y):

    a = 77.0737
    rd_x_null = 124280.000
    rd_y_null = 426220.000
    local_x_null = 2000.000
    local_y_null = 5000.000

    local_coordinate_x = np.sin(a) * (rd_coordinate_x - rd_x_null) + np.cos(a) * (rd_coordinate_y - rd_y_null) + local_x_null
    local_coordinate_y = -np.cos(a) * (rd_coordinate_x - rd_x_null) + np.sin(a) * (rd_coordinate_y - rd_y_null) + local_y_null

    return local_coordinate_x, local_coordinate_y

def structure_timestamps(series):

    s = series.str.rstrip("Z")
    has_fraction = s.str.contains(r"\.")
    main = s.where(~has_fraction, s.str.split(".").str[0])
    frac = s.where(~has_fraction, s.str.split(".").str[1].str[:6])  
    cleaned = main.where(~has_fraction, main + "." + frac)
    dt = pd.to_datetime(cleaned, format="%Y-%m-%dT%H:%M:%S.%f", utc=True)
    dt = dt + pd.Timedelta(seconds=1)

    return dt

def evaluate_timestamp(latest_UTC_timestamp):

    if isinstance(latest_UTC_timestamp, str):
        return datetime.fromisoformat(latest_UTC_timestamp.replace("Z", "+00:00"))
    elif isinstance(latest_UTC_timestamp, datetime):
        latest_UTC_timestamp = latest_UTC_timestamp.replace(tzinfo=timezone.utc)
        return latest_UTC_timestamp
    elif latest_UTC_timestamp is None:
        return latest_UTC_timestamp
    else:
        raise ValueError(f"Unknown type for latest UTC timestamp: {type(latest_UTC_timestamp)}")

def main():
    latest_UTC_timestamp = datetime(2026, 2, 3, 12, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    latest_UTC_timestamp = evaluate_timestamp(latest_UTC_timestamp)
    current_UTC_time = datetime.now(timezone.utc)
    project_points_df, project_points_ids = get_project_points(geomos_host, geomos_port, geomos_api_key, geomos_projectid)
    result_df = get_point_results(geomos_host, geomos_port, geomos_api_key, geomos_projectid, project_points_ids, latest_UTC_timestamp.strftime("%Y-%m-%dT%H:%M:%S") + "Z", 
                                                      current_UTC_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z")
    
    result_df = result_df.drop(columns=['Id', 'EpochLocal'])
    result_df = result_df.rename(columns={'PointId': 'Id', 'Epoch': 'Timestamp'})
    result_df["Timestamp"] = structure_timestamps(result_df["Timestamp"])
    result_df = result_df.merge(project_points_df, on='Id',how='left')
    result_df = result_df[~((result_df['Name'].str.contains('ts', case=False)) & (result_df['Type'] == 8))]
    result_df = result_df.sort_values(by="Timestamp")  # optional, ensures earliest timestamp first
    result_df = result_df.drop_duplicates(subset="Name", keep="first")
    result_df['Name'] = result_df['Name'].str.replace(r'_TS.*$', '', regex=True)
    result_df = (
    result_df
    .groupby('Name', as_index=False)
    .agg({
        'Northing': 'mean',
        'Easting': 'mean',
        'Height': 'mean',
        'Timestamp': 'first'
    })

    
)
    result_df[result_df["Name"].str.contains("LHZ|LHN", na=False)][
    ["Name", "Easting", "Northing", "Height", "Timestamp"]
].to_csv(r"D:\monitoring\merwede\data_marcel3\Rdpoints_merwede_LH.csv", index=False)
    
    result_df[["Name", "Easting", "Northing", "Height", "Timestamp"]].to_csv(r"D:\monitoring\merwede\data_marcel3\Rdpoints_merwede.csv", index=False)
    
    result_df[['Easting', 'Northing']] = result_df.apply(
                                lambda row: pd.Series(translate_to_bridgesystem(row['Easting'], row['Northing'])),
                                axis=1
                            )
    
    result_df[["Name", "Easting", "Northing", "Height", "Timestamp"]].to_csv(r"D:\monitoring\merwede\data_marcel3\Localpoints_merwede.csv", index=False)
    

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
    table_name_measurements = os.getenv("TABLE_NAME_MEASUREMENTS")

    #zero-date
    zero_date = os.getenv("ZERO_DATE")
    log_directory = r"D:\monitoring\merwede\test"
    results_directory = r"D:\monitoring\merwede\test"

    main()