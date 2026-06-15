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
        #project_points_df = project_points_df[project_points_df['Name'].isin(["907_GSL_1_TS1", "908_GSL_1_TS1", "907_GSL_1_TS2", "908_GSL_1_TS2", 
                                                                              #"907_GSL_1_TS3", "908_GSL_1_TS3", "907_GSL_1_TS5", "908_GSL_1_TS4"])]
        project_point_ids = project_points_df["Id"].tolist()
        project_string = ""
        for id_id, project_point_id in enumerate(project_point_ids):
            if id_id + 1 == len(project_point_ids):
                project_string = project_string + str(project_point_id)
            else:
                project_string = project_string + str(project_point_id) + ","
        
        return project_points_df, project_string
    else:
        return pd.DataFrame(),[]
    
def get_tps_measurements(host, port, api_key, projectid, project_string, starttime, endtime):

    tps_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/tpsmeasurementsjson?pointsids={project_string}&apiKey={api_key}&startTime={starttime}&endTime={endtime}")
    print(tps_json)

    return tps_json["TpsMeasurements"]

def main(geomos_host, geomos_port, geomos_api_key, geomos_projectid, starttime, endtime, results_directory):

    project_points_df, project_string = get_project_points(geomos_host, geomos_port, geomos_api_key, geomos_projectid)
    print(project_string)
    tps_data = get_tps_measurements(geomos_host, geomos_port, geomos_api_key, geomos_projectid, project_string, starttime, endtime)
    tps_dataframe = pd.DataFrame(tps_data)
    tps_dataframe["HzAngle"] = tps_dataframe["HzAngle"] * (200 / np.pi)
    tps_dataframe["VAngle"] = tps_dataframe["VAngle"] * (200 / np.pi)
    tps_dataframe["Orientation"] = tps_dataframe["Orientation"] * (200 / np.pi)
    tps_dataframe = tps_dataframe.rename(columns={"EpochLocal": "Timestamp"})
    tps_dataframe["Timestamp"] = pd.to_datetime(tps_dataframe["Timestamp"])
    tps_dataframe = tps_dataframe.drop(columns=["Epoch"])
    #tps_dataframe = tps_dataframe[tps_dataframe["MeasurementPointName"].isin(["907_GSL_1_TS1", "908_GSL_1_TS1", "907_GSL_1_TS2", "908_GSL_1_TS2", 
                                                                              #"907_GSL_1_TS3", "908_GSL_1_TS3", "907_GSL_1_TS5", "908_GSL_1_TS4"])]
    dt_start = datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%SZ")
    result_start = dt_start.strftime("%Y%m%d%H")
    dt_end = datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%SZ")
    result_end = dt_end.strftime("%Y%m%d%H")
    tps_dataframe.to_csv(os.path.join(results_directory, f"rawangles_{result_start}_{result_end}.csv"))
    print(sorted(tps_dataframe["MeasurementPointName"].unique()))

if __name__ == "__main__":

    load_dotenv()

    # Input configuration for Geomos
    geomos_host = os.getenv("GEOMOS_HOST")
    geomos_port = os.getenv("GEOMOS_PORT")
    geomos_api_key = os.getenv("GEOMOS_API_KEY")
    geomos_projectid = os.getenv("GEOMOS_PROJECTID")
    starttime = datetime(2026, 5, 28, 11, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    endtime = datetime(2026, 5, 29, 11, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    # results_directory = r"C:\Users\TimBerenschot\Documents\GitHub\merwedebrug_python_backend\main_brug\raw_angles"
    results_directory =  r"C:\Work\Projecten\Merwegebrug"

    main(geomos_host, geomos_port, geomos_api_key, geomos_projectid, starttime, endtime, results_directory)
    
