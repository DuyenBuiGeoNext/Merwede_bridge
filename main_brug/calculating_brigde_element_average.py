import pandas as pd
from sqlalchemy import create_engine
from shapely.geometry import Point
import numpy as np
from dotenv import load_dotenv
import requests
import os
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

def translate_to_bridgesystem(rd_coordinate_x, rd_coordinate_y):
    """
    Convert the coordinates from rd to local projection
    """
    a = np.deg2rad(77.0737)
    rd_x_null = 124280.000
    rd_y_null = 426220.000
    local_x_null = 2000.000
    local_y_null = 5000.000

    local_coordinate_x = np.sin(a) * (rd_coordinate_x - rd_x_null) + np.cos(a) * (rd_coordinate_y - rd_y_null) + local_x_null
    local_coordinate_y = -np.cos(a) * (rd_coordinate_x - rd_x_null) + np.sin(a) * (rd_coordinate_y - rd_y_null) + local_y_null

    return local_coordinate_x, local_coordinate_y

def request_geomos_api(api_url):
    """ Request data from Geomos platform
    
    What type of data is returned?"""

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
    """ Extract projection points from geomos
    
    Args:
        host
        port
        api_key
        projectide
    Returns:
        data frame for the extracted points 
        a list of the ids"""

    project_points_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/pointsjson?apiKey={api_key}")

    if project_points_json:
        project_points_df = pd.DataFrame(project_points_json['Points']).drop(['Easting', 'Northing', "Height", 'ProfileId'], axis=1)
        project_point_ids = project_points_df["Id"].tolist()

        return project_points_df, project_point_ids
    else:
        return pd.DataFrame(),[]

def create_pointIds(project_points_ids):
    """ Convert each id into a string
    
        Args:
            project_points_ids (lst)
        Returns: 
            a list of string
        """

    return [str(point_id) for point_id in project_points_ids] 

def get_point_results(host, port, api_key, projectid, project_points_ids, latest_UTC_timestamp, current_utc_time):
    """"For each """
    results_list = list()
    id_strings = create_pointIds(project_points_ids)

    for id_string in id_strings:
        point_result_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/resultsjson?pointsIds={id_string}&apiKey={api_key}&startTime={latest_UTC_timestamp}&endTime={current_utc_time}")
        if point_result_json["Results"]:
            results_list.extend(point_result_json["Results"])
    
    result_df = pd.DataFrame(results_list)
    
    return result_df

def structure_timestamps(series):

    s = series.str.rstrip("Z")
    has_fraction = s.str.contains(r"\.")
    main = s.where(~has_fraction, s.str.split(".").str[0])
    frac = s.where(~has_fraction, s.str.split(".").str[1].str[:6])  
    cleaned = main.where(~has_fraction, main + "." + frac)
    dt = pd.to_datetime(cleaned, format="%Y-%m-%dT%H:%M:%S.%f", utc=True)
    dt = dt + pd.Timedelta(seconds=1)

    return dt

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
                        if_exists="replace"     # creates the table if it does not exist
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

def main(begin_time, end_time):

    project_points_df, project_points_ids = get_project_points(geomos_host, geomos_port, geomos_api_key, geomos_projectid)
    result_df = get_point_results(geomos_host, geomos_port, geomos_api_key, geomos_projectid, project_points_ids, begin_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z", 
                                    end_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z")
    
    print(result_df)
    lh_data  = [
    ["00c_LHZ_0", 426258.5052349577, 124272.3485204211, 6.4969680549773345],
    ["00d_LHZ_0", 426263.99190695625, 124248.3933529791, 6.811003755911826],
    ["41_LHN_0", 427018.99829734146, 124446.56627471003, 7.905591400775617],
    ["42_LHN_0", 427023.8969975747, 124422.72909349472, 7.766159011851751]
]
    
    if not result_df.empty:
        result_df = result_df.drop(columns=['Id', 'EpochLocal'])
        result_df = result_df.rename(columns={'PointId': 'Id', 'Epoch': 'Timestamp'})
        result_df["Timestamp"] = structure_timestamps(result_df["Timestamp"])
        result_df = result_df.merge(project_points_df, on='Id',how='left')
        result_df['Name'] = result_df['Name'].str.replace(r'_TS.*$', '', regex=True)
        result_df = result_df[~((result_df['Name'].str.contains('ts', case=False)) & (result_df['Type'] == 8))]

        result_df_avg = (
            result_df.groupby("Name", as_index=False)
            .agg({"Northing": "mean", "Easting": "mean", "Height": "mean"})
        )
    
        result_df_avg.rename(columns={"Northing": "Northing_RD", "Easting": "Easting_RD"}, inplace=True)
        result_df_avg = result_df_avg[~result_df_avg['Name'].str.contains('GSL', regex=True, case=False)]
        lh_df = pd.DataFrame(lh_data, columns=result_df_avg.columns)
        result_df_avg = pd.concat([result_df_avg, lh_df], ignore_index=True)
        result_df_avg[['Easting_local', 'Northing_local']] = result_df_avg.apply(
            lambda row: pd.Series(translate_to_bridgesystem(row['Easting_RD'], row['Northing_RD'])),
            axis=1
        )

        result_df_avg["Timestamp"] = end_time
        export_data_to_SQL(result_df_avg, grafana_db_host, grafana_db_user, 
                                                grafana_db_password, grafana_db_name, grafana_db_port, "average_measurements")

        print(result_df_avg)

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

    begin_time = datetime(2025, 12, 2, 11, tzinfo=timezone.utc)
    end_time = datetime(2025, 12, 2, 15, tzinfo=timezone.utc)

    main(begin_time, end_time)

