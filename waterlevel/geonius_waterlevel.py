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
                return datetime(2024, 3, 29, 20, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

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

def request_waterlevel_api(api_key, api_url):

    headers = {'apikey': api_key}
    attempt = 1
    amount_of_data = 0
    api_data = list()

    while True:
        try:
            if attempt > 3:
                return {}
            else:
                results = requests.request("GET", api_url, headers=headers).json()

                if results['continuationtoken'] is None:
                    api_data.extend(results['data'])
                    break
                else:
                    api_data.extend(results['data'])
                    headers['continuationtoken'] = results['continuationtoken']
                    attempt = 1
                    amount_of_data += 500
                    print(f"Extracted {amount_of_data} measurement points")

        except Exception as e:
            print(f"Waterlevel API request failed because of the following error {e}")
            attempt += 1
            time.sleep(0.5)

    return api_data

def process_api_data(api_data):

    raw_api_df = pd.DataFrame(api_data)
    raw_api_df = raw_api_df[raw_api_df["condition"] != "intern"]

    pivoted_api_df = raw_api_df.pivot(
    index="datetime",
    columns="quantity",
    values="value"
).reset_index()

    pivoted_api_df["datetime"] = pd.to_datetime(pivoted_api_df["datetime"], utc=True, format="ISO8601")
    pivoted_api_df = pivoted_api_df.set_index("datetime")
    
    waterlevel_results = pivoted_api_df.resample(
        "h",
        label="right",
        closed="right"
    ).mean()

    waterlevel_results = waterlevel_results.reset_index()
    waterlevel_results.columns.name = None
    waterlevel_results = waterlevel_results.rename(columns={"datetime": "Timestamp"})
    waterlevel_results["Timestamp"] = waterlevel_results["Timestamp"].dt.tz_localize(None)

    return waterlevel_results

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
        except Exception:
            traceback.print_exc()
            time.sleep(1)
            attempt += 1

def main(waterlevel_host, waterlevel_api_key, waterlevel_projectid,grafana_db_host, grafana_db_user, 
        grafana_db_password, grafana_db_name, grafana_db_port, table_name_measurements):

    latest_utc_timestamp = get_latest_UTC_timestamp(grafana_db_host, grafana_db_user, grafana_db_password,
                             grafana_db_name, grafana_db_port, table_name_measurements)

    print("Starting requesting the api")
    api_url = f"{waterlevel_host}/{waterlevel_projectid}/values?startdate={latest_utc_timestamp}"
    api_data = request_waterlevel_api(waterlevel_api_key, api_url)
    if not api_data:
        print("Failed getting waterlevel data from API, waiting for next cycle in an hour")
    else:
        print("Finished requesting the api")
        waterlevel_results = process_api_data(api_data)
        print("Finished processing the api_results")
        export_data_to_SQL(waterlevel_results, grafana_db_host, grafana_db_user, grafana_db_password, grafana_db_name, grafana_db_port, table_name_measurements)

if __name__ == "__main__":

    load_dotenv()

    # Input configuration for waterlevel
    waterlevel_host = os.getenv("WATERLEVEL_HOST")
    waterlevel_api_key = os.getenv("WATERLEVEL_API_KEY")
    waterlevel_projectid = os.getenv("WATERLEVEL_PROJECTID")

    # Input configuration for Grafana database (output measurements)
    grafana_db_host = os.getenv("GRAFANA_DB_HOST")
    grafana_db_user = os.getenv("GRAFANA_DB_USER")
    grafana_db_password = urllib.parse.quote_plus(os.getenv("GRAFANA_DB_PASSWORD"))
    grafana_db_name = os.getenv("GRAFANA_DB_NAME")
    grafana_db_port = os.getenv("GRAFANA_DB_PORT")
    table_name_measurements = os.getenv("TABLE_NAME_MEASUREMENTS")

    fixed_times = [f"{h:02d}:00" for h in range(24)]
    
    for t in fixed_times:
        schedule.every().day.at(t).do(
            main,
            waterlevel_host=waterlevel_host,
            waterlevel_api_key=waterlevel_api_key,
            waterlevel_projectid=waterlevel_projectid,
            grafana_db_host=grafana_db_host,
            grafana_db_user=grafana_db_user,
            grafana_db_password=grafana_db_password,
            grafana_db_name=grafana_db_name,
            grafana_db_port=grafana_db_port,
            table_name_measurements=table_name_measurements
        )
    
    while True:
        schedule.run_pending()
        time.sleep(10)


