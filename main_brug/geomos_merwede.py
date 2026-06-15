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

class bridge_pillar_standard:

    def __init__(self, element_params, element_data, reference_data, timestamp, object_name):
        """"
        Assign methods and parameters for the object
        Args:
            element_params (dict) contain the information of the installed prisms, the bearing of each pillar
            element_data (df) measured data extracted based on a given time block (every 4 h)
            reference_data (df) null measurements
            timestamp (time)
            object_name (str)
        Return:
            a variable with added values
        Notes: roty_capability automatically change?
        """

        #define input variables and parameter constants that will be used during calculations
        self.brigde_log = list()
        self.element_params = element_params
        self.prism_names = element_params["prism_data"]["prism_names"]
        self.prism_dist_constant = element_params["prism_data"]["prism_dist_constant"]
        self.object_constants = element_params["opleg_data"]
        self.reference_data = reference_data
        self.timestamp = timestamp
        self.object_name = object_name
        self.roty_capability = True

        #extract reference data & calculate deltas. Also check measurement availability and raise error when calculations are not possible
        # Calculate the location difference of measured points and null measurements
        self.element_data = self.get_element_deltas(element_data)
        # Retrieve the positions for all prisms
        self.left_high_prism, self.left_high_prism_reference, self.left_low_prism, self.left_low_prism_reference, self.right_high_prism, self.right_high_prism_reference, self.right_low_prism, self.right_low_prism_reference = self.get_input_measurement_points()
        self.check_availability_prisms()
        # Calculate the differences in height of each prism pair
        self.dist_high, self.dist_low, self.dist_left, self.dist_right = self.get_distances()

        #calculate new measurement including the displacement of bearing/prisms, the rotations around x, y, z,
        # delta y, and other values (time stamp, distances,...)
        self.new_measurement = self.calculate_new_measurement()
    
    def calculate_deltas(self, element_data, reference_data):
        """
        Calculate the location difference of measured points and null measurements
        
        Agrs:
            element_params (dict) contain the information of the installed prisms, the bearing of each pillar
            element_data (df) measured data
            
        Return:
            a dataframe with the calculated deltas in x, y, and z dimensions"""
        print(element_data)
        element_indexed = element_data.set_index('Name')
        reference_indexed = reference_data.set_index('Name')
        deltas = element_indexed[['Northing_local','Easting_local','Height']] - reference_indexed[['Northing_local','Easting_local','Height']]
        deltas.columns = ['delta_x', 'delta_y', 'delta_z']
        element_data = element_data.join(deltas, on='Name')

        return element_data
    
    def get_element_deltas(self, element_data):
        """
        Ensure that the reference data always comes from the object data"""

        element_data = self.calculate_deltas(element_data, self.reference_data)

        return element_data
    
    def check_availability_prisms(self):
        """
        Check the availability of the prisms on all piles"""

        if self.left_high_prism.empty and self.left_low_prism.empty and self.right_high_prism.empty and self.right_low_prism.empty:
            raise ValueError(f"All prisms of {self.object_name} from {self.timestamp} have not measured for atleast the last 4 hours")
        elif self.left_high_prism.empty and self.left_low_prism.empty:
            raise ValueError(f"All left sided prisms for {self.object_name} from {self.timestamp} have not measured for atleast the last 4 hours")
        elif self.right_high_prism.empty and self.right_low_prism.empty:
            raise ValueError(f"All right sided prisms for {self.object_name} from {self.timestamp} have not measured for atleast the last 4 hours")
        elif self.left_high_prism.empty or self.right_high_prism.empty or self.right_low_prism.empty or self.left_low_prism.empty:
            if (self.left_high_prism.empty or self.right_high_prism.empty) and (self.right_low_prism.empty or self.left_low_prism.empty):
                raise ValueError(f"No low or high prism pair possible for {self.object_name} from {self.timestamp} for atleast the last 4 hours")
            elif self.left_high_prism.empty and self.right_high_prism.empty:
                self.roty_capability = False
            elif self.right_low_prism.empty and self.left_low_prism.empty:
                self.roty_capability = False
    
    def evaluate_measurement_points(self, element_data, element_name):
        """
        Retrieve the measurement data from a prism + position of the related prism with ['Name', 'Northing_local', 'Easting_local', 'Northing_RD', 'Easting_RD',
      ...ight', 'Timestamp']
        
        Return:
            a dataframe"""

        try:
            return element_data[element_data["Name"] == element_name].iloc[0]
        except IndexError:
            return element_data[element_data["Name"] == element_name]

    def get_input_measurement_points(self):
        """
        Collect the data of all prisms from the measurement and null measurement
        
        Return:
            a tuple of lists"""

        result = []
        for name in self.prism_names:
            result.append(self.evaluate_measurement_points(self.element_data, name))
            result.append(self.evaluate_measurement_points(self.reference_data, name))

        return tuple(result)

    def get_distances(self):
        """
        Calculate the distance between the prismns """

        if not self.left_high_prism.empty and not self.right_high_prism.empty:
            # Calculate the distance in height of each pair of prisms between two sides
            dist_high = abs(Point(self.left_high_prism['Easting_local'], self.left_high_prism['Northing_local']).distance(Point(self.right_high_prism['Easting_local'], self.right_high_prism['Northing_local'])))
        else:
            dist_high = None

        if not self.left_low_prism.empty and not self.right_low_prism.empty:
            dist_low = abs(Point(self.left_low_prism['Easting_local'], self.left_low_prism['Northing_local']).distance(Point(self.right_low_prism['Easting_local'], self.right_low_prism['Northing_local'])))
        else:
            dist_low = None
            # Calculate the distance in height of each pair of prisms on each side
        dist_left = abs(self.left_high_prism["Height"] - self.left_low_prism["Height"])
        dist_right = abs(self.right_high_prism["Height"] - self.right_low_prism["Height"])

        return dist_high, dist_low, dist_left, dist_right

    def calculate_displacement(self, opleg_dist_constant, delta_left, delta_right):
        """
        Calculate the displacement of the bearingss
        
        Args:
            opleg_dist_constant (float): the distance from the outer left to the outer right
            delta_left (float): The difference in an axis of the left measurement compared to those of the left ref
            delta_right (float): The difference in an axis of the right measurement compared to those of the right ref
        Result:
            floats
        
        Notes: There is another calculation called calculate_displacement"""
        
        # Determine the position of the bearing relative to the prisms
        dist_left_oplegpunt1 = (self.prism_dist_constant - opleg_dist_constant) / 2
        dist_left_oplegpunt2 = (self.prism_dist_constant - opleg_dist_constant) / 2 + opleg_dist_constant
        # Determine the displacement of the bearing. Interpolating the displacement of the bearing
        oplegpunt1_delta = delta_left + (dist_left_oplegpunt1 / self.prism_dist_constant) * (delta_right - delta_left)
        oplegpunt2_delta = delta_left + (dist_left_oplegpunt2 / self.prism_dist_constant) * (delta_right - delta_left)

        return oplegpunt1_delta, oplegpunt2_delta

    def get_displacements(self, opleg_type, opleg_dist_constant):
        """
        Calculate the displacement of the bearings in x and z directions. Unit in meter
        Agrs: 
            opleg_type (str)
            opleg_dist_constant (float)
        Return:
            a dict: key-bearing types and values-displacements in x and z per type
            Notes: Y displacement is not calculated here. It is considered to be an average of y displ. on two sides, 
            since an object will move as a whole in one direction"""

        if not self.left_high_prism.empty and not self.right_high_prism.empty:
            oplegpunt1_delta_x, oplegpunt2_delta_x = self.calculate_displacement(opleg_dist_constant, self.left_high_prism["delta_x"], self.right_high_prism["delta_x"])
            oplegpunt1_delta_z, oplegpunt2_delta_z = self.calculate_displacement(opleg_dist_constant, self.left_high_prism["delta_z"], self.right_high_prism["delta_z"])
        else:
            self.brigde_log.append(f"For the calculations of displacements from bridge element {self.object_name}, the lower prism points were used")
            oplegpunt1_delta_x, oplegpunt2_delta_x = self.calculate_displacement(opleg_dist_constant, self.left_low_prism["delta_x"], self.right_low_prism["delta_x"])
            oplegpunt1_delta_z, oplegpunt2_delta_z = self.calculate_displacement(opleg_dist_constant, self.left_low_prism["delta_z"], self.right_low_prism["delta_z"])

        return {f"{opleg_type}punt1_deltax": oplegpunt1_delta_x * 1000, f"{opleg_type}punt2_deltax": oplegpunt2_delta_x * 1000, 
                f"{opleg_type}punt1_deltaz": oplegpunt1_delta_z * 1000, f"{opleg_type}punt2_deltaz": oplegpunt2_delta_z * 1000}
    
    def calculate_opleg_locations(self, opleg_type, opleg_dist_const, opleg_zdiff_west, opleg_zdiff_east, eastingcolumn, northingcolumn, coordsysteem):
        """"
        Notes: The way of calculating the coords is different from the displacement calculation, but still use the same formular. 
        In this way, we do not use delta (measurement vs ref.)
        Why z is considered only one side?
        Determine of the new locations of the bearings after transitioning. Unit in geography (RD and local system)
        Args:
            opleg_type (str)
            opleg_dist_const (float)
            opleg_zdiff_west (float)
            opleg_zdiff_east (float)
            eastingcolumn
            northingcolumn
            coordsysteem
        Return:
            The new coordinates in x, y, and z after movement"""
        # calculate x, and y
        if not self.left_high_prism.empty and not self.right_high_prism.empty:
            x_coordinate1, x_coordinate2 = self.calculate_displacement(opleg_dist_const, self.left_high_prism[eastingcolumn], self.right_high_prism[eastingcolumn])
            print(self.left_high_prism[eastingcolumn], self.right_high_prism[eastingcolumn])
            print("ref", self.left_high_prism_reference[eastingcolumn], self.right_high_prism_reference[eastingcolumn])
            y_coordinate1, y_coordinate2 = self.calculate_displacement(opleg_dist_const, self.left_high_prism[northingcolumn], self.right_high_prism[northingcolumn])
            print(self.left_high_prism[northingcolumn], self.right_high_prism[northingcolumn])
        else:
            x_coordinate1, x_coordinate2 = self.calculate_displacement(opleg_dist_const, self.left_low_prism[eastingcolumn], self.right_low_prism[eastingcolumn])
            y_coordinate1, y_coordinate2 = self.calculate_displacement(opleg_dist_const, self.left_low_prism[northingcolumn], self.right_low_prism[northingcolumn])
        # calculate the height (z) for the new points
        if not self.left_high_prism.empty:
            z_coordinate = self.left_high_prism["Height"] + opleg_zdiff_west
        elif not self.right_high_prism.empty:
            z_coordinate = self.right_high_prism["Height"] + opleg_zdiff_east
        else:
            z_coordinate = self.left_low_prism["Height"] + opleg_zdiff_west + self.left_high_prism_reference['height'] - self.left_low_prism_reference['Height']
        print(self.left_high_prism["Height"])
        return {f"{opleg_type}1_{coordsysteem}_x": x_coordinate1, f"{opleg_type}1_{coordsysteem}_y": y_coordinate1,f"{opleg_type}1_{coordsysteem}_z": z_coordinate,
                f"{opleg_type}2_{coordsysteem}_x": x_coordinate2, f"{opleg_type}2_{coordsysteem}_y": y_coordinate2,f"{opleg_type}2_{coordsysteem}_z": z_coordinate}
    
    def get_opleg_locations(self, opleg_type, opleg_dist_const, opleg_zdiff_west, opleg_zdiff_east):
        """
        Retrieve the local and RD location of each bearing after transitioning
        
        Notes: Easting_local is y and northing_local is x
        "lokaal is just a tring"""

        opleg_locations_local = self.calculate_opleg_locations(opleg_type, opleg_dist_const, opleg_zdiff_west, opleg_zdiff_east,
                                                               "Easting_local", "Northing_local", "lokaal")
        
        opleg_locations_rd = self.calculate_opleg_locations(opleg_type, opleg_dist_const, opleg_zdiff_west, opleg_zdiff_east,
                                                               "Easting_RD", "Northing_RD", "RD")
        
        # merging results
        
        return opleg_locations_local | opleg_locations_rd

    def get_rotation_tuples(self):

        """
        Return the x and z coordinates of a given point"""

        def rot(point):
            return (point["Easting_local"], point["Height"])

        return (
            rot(self.left_high_prism_reference),
            rot(self.left_low_prism_reference),
            rot(self.right_high_prism_reference),
            rot(self.right_low_prism_reference),
            rot(self.left_high_prism),
            rot(self.left_low_prism),
            rot(self.right_high_prism),
            rot(self.right_low_prism),
        )
    
    def interpolate_rotation_around_axis(self, opleg_dist_constant, prism_delta_left, prism_delta_right):
        """
        Calculate the rotation of x and z axes
        Interpolate the bearing points when rotating around x and z axis
        Calculate the displacement in an axis
        Notes: look more like a displacement and not rotation"""
        
        return (opleg_dist_constant / self.prism_dist_constant) * (prism_delta_left - prism_delta_right)
    
    def get_rotationsxz(self, opleg_dist_constant):
        """
        Notes: why the rotations around x and z do not include 2 dimension movements?"""
        
        if not self.left_high_prism.empty and not self.right_high_prism.empty:
            rotationx = self.interpolate_rotation_around_axis(opleg_dist_constant, self.left_high_prism["delta_z"], self.right_high_prism["delta_z"])
            rotationz = self.interpolate_rotation_around_axis(opleg_dist_constant, self.left_high_prism["delta_x"], self.right_high_prism["delta_x"])
        else:
            rotationx = self.interpolate_rotation_around_axis(opleg_dist_constant, self.left_low_prism["delta_z"], self.right_low_prism["delta_z"])
            rotationz = self.interpolate_rotation_around_axis(opleg_dist_constant, self.left_low_prism["delta_x"], self.right_low_prism["delta_x"])
            self.brigde_log.append(f"For the calculations of rotation X and Z from bridge element {self.object_name}, the lower prism points were used")

        return rotationx * 1000, rotationz * 1000
    
    def interpolate_rotation_oplegpunt(self, opleg_zdiff, left_low_prism_roty, left_high_prism_roty, left_low_prism_reference_roty, left_high_prism_reference_roty):
        """
        Calculate the rotation of the bearing/prisms based on the reference data and linear interpolation method
        
        Args:
            opleg_zdiff (float)
            left_low_prism_roty (coord)
            left_high_prism_roty (coord)
            left_low_prism_reference_roty (coord)
            left_high_prism_reference_roty (coord)
        Return:
            a float in meter"""
        # draw a straight line
        current_object_plane = LineString([left_low_prism_roty, left_high_prism_roty])
        reference_object_plane = LineString([left_low_prism_reference_roty, left_high_prism_reference_roty])
        # interpolate the position for the new point
        current_interpolation = current_object_plane.interpolate(current_object_plane.length - abs(opleg_zdiff))
        reference_interpolation = reference_object_plane.interpolate(reference_object_plane.length - abs(opleg_zdiff))
        # the difference between the position of the rotation point and the reference point
        return current_interpolation.x - reference_interpolation.x
    
    def calculate_extrapolation(self, opleg_zdiff, lower_point, higher_point):

        """
        Calculate the locations of the extrapolated points in x and z
        
        Args:
            opleg_zdiff (float) distance from the bearing to highest prism
            lower_point (float) x and z coord of the lower prims
            higher_point (float) x and z coord of the high prims
        Return:
            points"""

        x1, z1 = lower_point
        x2, z2 = higher_point

        dx = x2 - x1
        dz = z2 - z1
        
        # calculate the length of the line
        L = math.sqrt(dx**2 + dz**2)
        # normalize values by the length of the line to 1. If a point travel 1 m along the diagnol line, how far the point
        # will move in the direction x and z
        ux = dx / L
        uz = dz / L

        if abs(uz) < 1e-9:
            raise ValueError("Line is horizontal; cannot reach a higher Y value.")
        # the total number of steps required to travel from the highest prism to the extrapolated point, which is based on the 1 unit cmovement calculated 
        # calculate the ratio 
        s = opleg_zdiff / uz
        x3 = x2 + s * ux
        z3 = z2 + s * uz

        return (x3, z3)

    def extrapolate_rotation_oplegpunt(self, opleg_zdiff, lower_point, higher_point, lower_point_reference, higher_point_reference):
        """
        Calculate the rotation in the position of extrapolated points of the measurement data and those of the ref. data """

        oplegpunt = self.calculate_extrapolation(opleg_zdiff, lower_point, higher_point)
        oplegpunt_reference = self.calculate_extrapolation(opleg_zdiff, lower_point_reference, higher_point_reference)

        return oplegpunt[0] - oplegpunt_reference[0]


    def get_side_rotation_method(self, opleg_zdiff, interpolation, extrapolation):
        """
        The selection of interpolation or extrapolation method based on a given condition"""

        if opleg_zdiff < 0:
            return interpolation
        else:
            return extrapolation
        
    def calculate_rotationy(self, opleg_zdiff_west, opleg_zdiff_east, rotation_method_left, rotation_method_right):

        """
        Calculate the rotation of y base on the movement of x and z for each pillar
        Args:
            opleg_zdiff_west (float)
            opleg_zdiff_east (float)
            rotation_method_left (method)
            rotation_method_right (method)
        Return:
            floats in mm
        """
        # retrieve the x and z coordinates of a given object (in this case an opleg type)
        (left_high_prism_reference_roty, left_low_prism_reference_roty, right_high_prism_reference_roty, right_low_prism_reference_roty,
        left_high_prism_roty, left_low_prism_roty, right_high_prism_roty, right_low_prism_roty) = self.get_rotation_tuples()

        #based on measurement availability and prism opleg correlation calculate the rotation y
        if not self.left_high_prism.empty and not self.left_low_prism.empty and not self.right_high_prism.empty and not self.right_low_prism.empty:

            rotationy_left = rotation_method_left(opleg_zdiff_west, left_low_prism_roty, left_high_prism_roty, 
                                                  left_low_prism_reference_roty, left_high_prism_reference_roty)
            rotationy_right = rotation_method_right(opleg_zdiff_east, right_low_prism_roty, right_high_prism_roty, 
                                                    right_low_prism_reference_roty, right_high_prism_reference_roty)
            
            rotationy = (rotationy_left + rotationy_right) / 2
        elif not self.left_high_prism.empty and not self.left_low_prism.empty:

            rotationy = rotation_method_left(opleg_zdiff_west, left_low_prism_roty, left_high_prism_roty, 
                                             left_low_prism_reference_roty, left_high_prism_reference_roty)
            
            self.brigde_log.append(f"For the calculations of rotation Y from bridge element {self.object_name}, only the left prism points were used")
        else:

            rotationy = rotation_method_right(opleg_zdiff_east, right_low_prism_roty, right_high_prism_roty, 
                                              right_low_prism_reference_roty, right_high_prism_reference_roty)
            
            self.brigde_log.append(f"For the calculations of rotation Y from bridge element {self.object_name}, only the right prism points were used")

        return rotationy * 1000

    def get_rotationy(self, opleg_zdiff_west, opleg_zdiff_east):
        """
        Obtain the rotation of y when x and z moving
        
        Args:
            opleg_zdiff_west ()
            opleg_zdiff_east ()
        Returns:
        """
        # select the right interpolation/exterpolation method
        rotation_method_left = self.get_side_rotation_method(opleg_zdiff_west, self.interpolate_rotation_oplegpunt, self.extrapolate_rotation_oplegpunt)
        rotation_method_right = self.get_side_rotation_method(opleg_zdiff_east, self.interpolate_rotation_oplegpunt, self.extrapolate_rotation_oplegpunt)
        rotation_y = self.calculate_rotationy(opleg_zdiff_west, opleg_zdiff_east, rotation_method_left, rotation_method_right)

        return rotation_y 

    def get_rotations(self, opleg_type, opleg_zdiff_west, opleg_zdiff_east, opleg_dist_constant):
        """
        Calculate the rotations around y, x, and z. 
        Args:
            opleg_type (str)
            opleg_zdiff_west (float)
            opleg_zdiff_east (float)
            opleg_dist_constant (float)
        Return:
            a dictionary
        Notes: when do we activate the roty_capability? For pillar 4 and 8, there is no prisms and only totalstation. 
              Roty_capability is false?      """

        # calculate the rotation of y
        if self.roty_capability:
            rotationy = self.get_rotationy(opleg_zdiff_west, opleg_zdiff_east)
        else:
            rotationy = None
        # calculation the rotation axes x and z
        rotationx, rotationz = self.get_rotationsxz(opleg_dist_constant)
        
        return {f"{opleg_type}_rotatiex": rotationx, f"{opleg_type}_rotatiey": rotationy, f"{opleg_type}_rotatiez": rotationz}
        
    def combine_observations(self, opleg_calculations):
        """
        """

        merged_calculations = {}
        for oplegging in opleg_calculations:
            merged_calculations.update(oplegging)

        return pd.DataFrame([merged_calculations])
    
    def calculate_new_measurement(self):
        """
        Notes: why only average delta_y?"""

        # Average the height difference of each prism pair when compared to the reference points 
        delta_y = (self.left_high_prism["delta_y"] + self.right_high_prism["delta_y"]) / 2 * 1000
        opleg_calculations = list()

        #go through the different opleg types that are present on the bridge object
        for opleg_type, opleg_constants in self.object_constants.items():
            # determine the new coords of bearing points in x, y, and z after transition
            opleg_location_dict = self.get_opleg_locations(opleg_type, opleg_constants["opleg_dist_const"],
                                                           opleg_constants["opleg_zdiff_west"], opleg_constants["opleg_zdiff_east"])
            # calculate the displacement of the bearing in x and z directions
            opleg_displacement_dict = self.get_displacements(opleg_type, opleg_constants["opleg_dist_const"])
            # get the rotation values around x, y, and z for each opleg type?
            opleg_rotation_dict = self.get_rotations(opleg_type, opleg_constants["opleg_zdiff_west"],  opleg_constants["opleg_zdiff_east"], opleg_constants["opleg_dist_const"])
            opleg_rotation_dict[f"{opleg_type}_opleg_dist"] = opleg_constants["opleg_dist_const"]
            opleg_calculations.append(opleg_displacement_dict | opleg_location_dict | opleg_rotation_dict)

        #combine all opleg types and add delta y to the dataframe
        new_measurement = self.combine_observations(opleg_calculations)
        new_measurement["delta_y"] = delta_y
        new_measurement["Prism_dist"] = self.prism_dist_constant
        new_measurement["Timestamp"] = self.timestamp
        new_measurement["Name"] = self.object_name
 
        return new_measurement
    
class bridge_pillar_totalstations(bridge_pillar_standard):

    def __init__(self, element_params, element_data, reference_data, timestamp, object_name):
        super().__init__(element_params, element_data, reference_data, timestamp, object_name)

    def check_availability_prisms(self):

        if self.left_high_prism.empty or self.right_high_prism.empty:
            raise ValueError(f"From one or both of the sides of {self.object_name} a prism observation is missing, calculations not possible")
            
    def get_distances(self):

        dist_high = abs(Point(self.left_high_prism['Easting_local'], self.left_high_prism['Northing_local']).distance(Point(self.right_high_prism['Easting_local'], self.right_high_prism['Northing_local'])))
        dist_low = "N/A"
        dist_left = "N/A"
        dist_right = "N/A"

        return dist_high, dist_low, dist_left, dist_right
    
    def get_rotationy(self, opleg_zdiff_west, opleg_zdiff_east):
        """
        Note: a bit confuse here, why do we need this? there is another function with the same name"""

        return "N/A"

    def calculate_displacement2(self, opleg_dist_constant, delta_left, delta_right):
        """
        Calculate the transition of bearings when the distance of the prisms to the brearing blocks on two sides are not equal
        Args:
            opleg_dist_constant (float): the distance between the two most outer bearings (m)
            delta_left (float): the displacement of the left prism location in a direction versus that of the reference data
            delta_right (float): the displacement of the right prism location in a direction versus that of the reference data
        
        Returns:
            floats: the transitions of the bearings  """

        # offset the location of a prism to the location of the bearing block
        left_prism_offset = self.element_params["prism_data"]["left_prism_offset"]
        right_prism_offset = self.element_params["prism_data"]["right_prism_offset"]

        prism_span = self.prism_dist_constant

        # center of the concrete block between the prisms
        block_center = (prism_span + left_prism_offset - right_prism_offset) / 2

        # construction point positions
        x1 = block_center - (opleg_dist_constant / 2)
        x2 = block_center + (opleg_dist_constant / 2)

        # linear interpolation between prism displacements
        oplegpunt1_delta = delta_left + x1 / prism_span * (delta_right - delta_left)
        oplegpunt2_delta = delta_left + x2 / prism_span * (delta_right - delta_left)

        return oplegpunt1_delta, oplegpunt2_delta

def request_geomos_api(api_url):
    """
    Retrieve the measured data from Geomos using url"""

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
    """ Extract all the names and ids of the measurement data via geomos
    Args:
        host (int)
        port (int)
        api_key (int)
        projectid (int)
    Returns:
        a df and a list"""

    project_points_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/pointsjson?apiKey={api_key}")

    if project_points_json:
        project_points_df = pd.DataFrame(project_points_json['Points']).drop(['Easting', 'Northing', "Height", 'ProfileId'], axis=1)
        project_point_ids = project_points_df["Id"].tolist()

        return project_points_df, project_point_ids
    else:
        return pd.DataFrame(),[]

def create_pointIds(project_points_ids):
    """ 
    Convert each id into a string
    
    Args:
        project_points_ids (lst)
    Returns: 
        a list of string
    """

    return [str(point_id) for point_id in project_points_ids] 

def get_point_results(host, port, api_key, projectid, project_points_ids, latest_UTC_timestamp, current_utc_time):
    """
    Retrieve the measured data for each point id at a given time frame from geomos
    
    Returns:
        A dataframe"""

    results_list = list()
    id_strings = create_pointIds(project_points_ids)

    for id_string in id_strings:
        point_result_json = request_geomos_api(f"http://{host}:{port}/v1/projects/{projectid}/resultsjson?pointsIds={id_string}&apiKey={api_key}&startTime={latest_UTC_timestamp}&endTime={current_utc_time}")
        if point_result_json["Results"]:
            results_list.extend(point_result_json["Results"])
    
    result_df = pd.DataFrame(results_list)
    print(result_df)
    return result_df

def get_latest_UTC_timestamp(grafana_db_host, grafana_db_user, grafana_db_password,
                             grafana_db_name, grafana_db_port, table_name_measurements):
    
    """
    Return the timestamp of the last measurement from the database"""

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
                return datetime(2025, 12, 2, 15, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

            # Query latest timestamp
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT MAX(Timestamp) FROM `{table_name_measurements}`")
                ).fetchone()

            print(result)
            return (
                result[0]
                if result and result[0] else datetime(2025, 15, 2, 12, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            )

        except SQLAlchemyError as e:
            print(f"⚠️ Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt == max_attempts:
                return None
            time.sleep(1)  # wait before retry

def structure_timestamps(series):
    """
    Restructure the timestamps format to UTC "%Y-%m-%dT%H:%M:%S.%f"
    
    Args:
        series (str)
    Return:
        a df"""
    # locate the timestamp from a string
    s = series.str.rstrip("Z")
    has_fraction = s.str.contains(r"\.")
    main = s.where(~has_fraction, s.str.split(".").str[0])
    frac = s.where(~has_fraction, s.str.split(".").str[1].str[:6])  
    cleaned = main.where(~has_fraction, main + "." + frac)
    # convert the string into a given timestamp format
    dt = pd.to_datetime(cleaned, format="%Y-%m-%dT%H:%M:%S.%f", utc=True)
    dt = dt + pd.Timedelta(seconds=1)

    return dt

def export_data_to_SQL(input_data, grafana_db_host, grafana_db_user, grafana_db_password, grafana_db_name, grafana_db_port, table_name):
    """
    Export the output to SQL database
    """
    attempt = 1
    while True:
        try:
            if attempt > 3:
                print("data upload to database failed")
                break
            else:
                # create the address to SQL database
                connection_string = f"mysql+pymysql://{grafana_db_user}:{grafana_db_password}@{grafana_db_host}:{grafana_db_port}/{grafana_db_name}"
                # establishing a connection to a database
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
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            traceback_str = traceback.format_exc().splitlines()
            time.sleep(1)
            attempt += 1

def translate_to_bridgesystem(rd_coordinate_x, rd_coordinate_y):
    """
    Convert the coordinates from rd to local projection
    Args:
        rd_coordinate_x (coord): x in RD projection
        rd_coordinate_y (coord): y in RD projection
    Return:
        local coordinates
    """

    a = np.deg2rad(77.0737)
    rd_x_null = 124280.000
    rd_y_null = 426220.000
    local_x_null = 2000.000
    local_y_null = 5000.000

    # translate to local origin and rotate to local grid
    local_coordinate_x = np.sin(a) * (rd_coordinate_x - rd_x_null) + np.cos(a) * (rd_coordinate_y - rd_y_null) + local_x_null
    local_coordinate_y = -np.cos(a) * (rd_coordinate_x - rd_x_null) + np.sin(a) * (rd_coordinate_y - rd_y_null) + local_y_null

    return local_coordinate_x, local_coordinate_y

def get_previous_block_start(ts, block_hours=4):
    """
    Convert the measurement local time to UTC based on the 4h interval
    
    Returns:
        time with minute and second zeroed out
        
    Notes: winter time and summer time are not taken into account"""

    dt_utc = datetime.now(tz=ZoneInfo("UTC"))
    dt_cest = dt_utc.astimezone(ZoneInfo("Europe/Berlin"))
    # Return the difference between UTC and the local time as a time delta object
    timezone_difference = int(dt_cest.utcoffset().total_seconds() // 3600)
    ts_plus_offset = ts + timedelta(minutes=30) # why offset? It might be useful when the time after the conversion lands exactky on a block boundary like 3:59 
    # Identify the time block (00:00, 04:00,..) of the prev. measurement time and shift it back to the UTC time zone
    hour = (((ts_plus_offset.hour + timezone_difference) // block_hours) * block_hours) - timezone_difference # why need to convert to local time?
                                                                                                                # if not convert to the local time first, the (00:00, 04:00,..) (and these time blocks are based on the local time) time block will not match with the UTC time (22:00, 02:00,..) => creating wrong results and confusion
    return ts.replace(hour=hour, minute=0, second=0, microsecond=0)

def get_time_blocks(results_df, block_hours=4):
    """
    Retrieve the records within a requested time frame

    Args:
        results_df (df): contains the measurements for all the piles

    Returns: 
        a list of records
    """

    results_df = results_df.sort_values("Timestamp").reset_index(drop=True)
    # Determine the start and end times of the retrieved values
    block_start = get_previous_block_start(results_df["Timestamp"].iloc[0])
    block_end = block_start + timedelta(hours=block_hours)
    blocks = list()
    current_measurements = list()
    time_block_log = list()
    # Select records that fall in the start and end time
    for _, measurement in results_df.iterrows():
        t = measurement["Timestamp"]
        # append the measurement if it is in the time block
        if block_start <= t < block_end:
            current_measurements.append(measurement)
        else:
            if current_measurements: # if not empty, and the next t is not in the time frame anymore
                block_df = pd.DataFrame(current_measurements)
                # check whether the number of records is sufficient
                if block_df["Timestamp"].iloc[-1] - block_df["Timestamp"].iloc[0] >= timedelta(hours=2) and block_end - block_df["Timestamp"].iloc[-1] <= timedelta(hours=1):
                    if len(block_df) >= 392:
                        blocks.append([block_df, block_end]) # Collecting the records that met the requirements
                    else:
                        time_block_log.append(f"The block {block_start} -- {block_end} is rejected, has too little points ({len(block_df)})")
                else:
                    time_block_log.append(f"The block {block_start} -- {block_end} is rejected, inner time difference is {block_df["Timestamp"].iloc[-1] - block_df["Timestamp"].iloc[0]}")
                    time_block_log.append(f"The block {block_start} -- {block_end} is rejected, time difference with block end is {block_end - block_df["Timestamp"].iloc[-1]}")
            else:
                time_block_log.append(f"The block {block_start} -- {block_end} is rejected, no measurements were found between these timestamps")
            # Reassign the start and end time if t is out of range
            while t >= block_end:
                block_start = block_end
                block_end = block_start + timedelta(hours=block_hours)
            # Reassign the value
            current_measurements = [measurement]
    # if no exception about t, finalize the collected data here
    if current_measurements:
        block_df = pd.DataFrame(current_measurements)
        if block_df["Timestamp"].iloc[-1] - block_df["Timestamp"].iloc[0] >= timedelta(hours=2) and block_end - block_df["Timestamp"].iloc[-1] <= timedelta(hours=1):
            if len(block_df) >= 392:
                blocks.append([block_df, block_end])
            else:
                time_block_log.append(f"The block {block_start} -- {block_end} has too little points ({len(block_df)})")
        else:
            time_block_log.append(f"The block {block_start} -- {block_end} is rejected, inner time difference is {block_df["Timestamp"].iloc[-1] - block_df["Timestamp"].iloc[0]}")
            time_block_log.append(f"The block {block_start} -- {block_end} is rejected, time difference with block end is {block_end - block_df["Timestamp"].iloc[-1]}")
    
    else:
        time_block_log.append(f"The block {block_start} -- {block_end} is rejected, no measurements were found between these timestamps")

    return blocks, time_block_log

def evaluate_timestamp(latest_UTC_timestamp):
    """ Assign the label UTC timezone for the timestamp"""
    if isinstance(latest_UTC_timestamp, str):
        return datetime.fromisoformat(latest_UTC_timestamp.replace("Z", "+00:00")) # convert to proper datetime ISO format #+00:00 is the timezone offset — it tells you how many hours ahead or behind UTC the time is.
    elif isinstance(latest_UTC_timestamp, datetime):
        latest_UTC_timestamp = latest_UTC_timestamp.replace(tzinfo=timezone.utc)
        return latest_UTC_timestamp
    elif latest_UTC_timestamp is None:
        return latest_UTC_timestamp
    else:
        raise ValueError(f"Unknown type for latest UTC timestamp: {type(latest_UTC_timestamp)}")

    
def read_bridge_parameters(parameter_path="brug_parameters.json"):
    """
    Load the parameters of the prisms, and the bearing from the bridge """
    # Adjustment
    # get directory of the current script
    # script_dir = Path(__file__).parent
    script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
    # Adjustment
    # path = script_dir / parameter_path
    path = script_dir + "\\main_brug\\" + parameter_path

    with open(path, "r") as file:
        parameters = json.load(file)

    return parameters

def get_reference_data(connection_string, zero_date):
    
    attempt = 1
    while True:

        if attempt > 5:
            raise ValueError("Cannot make connection to average measurement database")
        
        try:
            time.sleep(0.5)
            engine = create_engine(connection_string)

            query = f"""
            SELECT 
                Name,
                Northing_local,
                Easting_local,
                Northing_RD,
                Easting_RD,
                Height,
                Timestamp
            FROM average_measurements
            WHERE Timestamp = '{zero_date}';
            """

            reference_dataframe = pd.read_sql(query, engine)
            break

        except:
            time.sleep(3)
            attempt += 1

    return reference_dataframe

def get_all_columns(sql_objects, table_name_measurements):
    """
    Extract the all column names 
    Args:
        sql_objects (dict) contain the measurement values + average values for each 4h interval, 
                            and the locations of each brearing
        table_name_measurements (df)
    Return:
        a list"""

    column_names = set()  

    for object_name, sql_list in sql_objects.items():
        if object_name not in [table_name_measurements, "average_measurements", "Oplegging_locaties"]:
            for df in sql_list:
                column_names.update(df.columns)

    column_names = list(column_names)

    return column_names

def pivot_oplegging_data(oplegging_data):

    """
    convert the data into ? format"""

    cols = [
        "Brug1", "Brug2",
        "Hoofd1", "Hoofd2",
        "Neven1", "Neven2",
        "Voorhar1", "Voorhar2"
    ]

    rows = []

    for _, r in oplegging_data.iterrows():
        name = r["Name"]
        timestamp = r["Timestamp"]
        
        for c in cols:
            x = r.get(f"{c}_RD_x")
            y = r.get(f"{c}_RD_y")
            z = r.get(f"{c}_RD_z")
            
            if pd.notna(x):
                rows.append({
                    "Object / oplegging": f"{name} - {c}",
                    "RD_x": x,
                    "RD_y": y,
                    "RD_z": z,
                    "Timestamp": timestamp
                })

    transformed_data = pd.DataFrame(rows)

    return transformed_data

def main(geomos_host, geomos_port, geomos_api_key, geomos_projectid,
         grafana_db_host, grafana_db_user, grafana_db_password,
         grafana_db_name, grafana_db_port, table_name_measurements, zero_date, log_directory, results_directory):
    """
    Export the calculated values (rotations, displacement, id, etc) for the bridge objects to SQL database
    Record all actions for each 4h interval blocks
    Args:
        geomos_host (int)
        geomos_port (int)
        geomos_api_key (int)
        grafana_db_host (int)
        grafana_db_user (str)
        grafana_db_password (str)
        grafana_db_name (str)
        grafana_db_port (int)
        table_name_measurements (df)
        log_directory (str)
        zero_date (str?)
        results_directory (str)"""

    log_list = list()
    project_points_df, project_points_ids = get_project_points(geomos_host, geomos_port, geomos_api_key, geomos_projectid)
    print(project_points_df)
    if not project_points_df.empty:
        # The lasted UTC time from the host is the last measurement of the previous block?
        # adjustment
        # latest_UTC_timestamp = get_latest_UTC_timestamp(grafana_db_host, grafana_db_user, grafana_db_password, grafana_db_name, grafana_db_port, table_name_measurements)
        latest_UTC_timestamp = datetime(2026, 2, 9, 11, 00, 00, tzinfo=timezone.utc)
        latest_UTC_timestamp = evaluate_timestamp(latest_UTC_timestamp)
        if latest_UTC_timestamp is not None:
            print(latest_UTC_timestamp)
            print(type(latest_UTC_timestamp))
            # adjustment 
            # current_UTC_time = datetime.now(timezone.utc)
            current_UTC_time = datetime(2026, 2, 28,  11, 00, 00, tzinfo=timezone.utc)
            time_difference = current_UTC_time - latest_UTC_timestamp

            if time_difference > timedelta(hours=3, minutes=45):
                # Retrieve the measured data for each point id from the lasted UTC time to the current UTC time from geomos
                result_df = get_point_results(geomos_host, geomos_port, geomos_api_key, geomos_projectid, project_points_ids, latest_UTC_timestamp.strftime("%Y-%m-%dT%H:%M:%S") + "Z", 
                                                      current_UTC_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z")
                if not result_df.empty:
                    # Prepare the measured data to the right format and remove unrelated info
                    result_df = result_df.drop(columns=['Id', 'EpochLocal'])
                    result_df = result_df.rename(columns={'PointId': 'Id', 'Epoch': 'Timestamp'})
                    result_df["Timestamp"] = structure_timestamps(result_df["Timestamp"]) # Convert to UTC format
                    result_df = result_df.merge(project_points_df, on='Id',how='left') # Merge with the names of the measure objects
                    result_df['Name'] = result_df['Name'].str.replace(r'_TS.*$', '', regex=True)
                    result_df = result_df[~((result_df['Name'].str.contains('ts', case=False)) & (result_df['Type'] == 8))] # remove the measurement of ts and type 8, why?
                    log_list.append(f"From the API a total amount of {len(result_df)} measurement points were extracted")

                    # Calculate the average results of the last 4 hours and write to average_measurements table
                    # select the records that fall in a given time block
                    result_blocks, time_block_log = get_time_blocks(result_df)
                    log_list.extend(time_block_log)
                    log_list.append(f"The API results were divided in a total amount of {len(result_blocks)} block(s)")

                    # Retrieve the null measurements
                    connection_string = f"mysql+pymysql://{grafana_db_user}:{grafana_db_password}@{grafana_db_host}:{grafana_db_port}/{grafana_db_name}"
                    reference_data = get_reference_data(connection_string, zero_date)
                    # create an object to store in the sql database
                    sql_objects = dict()
                    for result_block_idx, (result_block, result_block_end) in enumerate(result_blocks):
                        log_list.append(f"Processing block {result_block_idx} with {len(result_block)} points and Timestamp {result_block_end}")
                        # write the result of each block into csv
                        result_block.to_csv(os.path.join(results_directory, f"raw_results_block_{result_block_end.strftime("%Y%m%d_%H%M%S")}.csv"))

                        try:
                            # drop the time zone
                            result_block["Timestamp"] = result_block["Timestamp"].dt.tz_localize(None)
                            # add the measured data of the next 4h block
                            if table_name_measurements in sql_objects:
                                sql_objects[table_name_measurements].append(result_block)
                            else:
                                sql_objects[table_name_measurements] = [result_block]
                            
                            # Averaging
                            result_df_avg = (
                                    result_block.groupby("Name", as_index=False)
                                    .agg({"Northing": "mean", "Easting": "mean", "Height": "mean"})
                                )
                            
                            result_df_avg.rename(columns={"Northing": "Northing_RD", "Easting": "Easting_RD"}, inplace=True)
                            # notes: why remove the records with GSL?
                            result_df_avg = result_df_avg[~result_df_avg['Name'].str.contains('GSL', regex=True, case=False)]
                            # assign the end time for each record that accords to its block
                            result_df_avg["Timestamp"] = result_block_end
                            # convert RD to local coords
                            result_df_avg[['Easting_local', 'Northing_local']] = result_df_avg.apply(
                                lambda row: pd.Series(translate_to_bridgesystem(row['Easting_RD'], row['Northing_RD'])),
                                axis=1
                            )

                            result_df_avg.to_csv(os.path.join(results_directory, f"average_results_block_{result_block_end.strftime("%Y%m%d_%H%M%S")}.csv"))
                            # add the averaged measurement of each 4h interval
                            if "average_measurements" in sql_objects:
                                sql_objects["average_measurements"].append(result_df_avg)
                            else:
                                sql_objects["average_measurements"] = [result_df_avg]

                        except Exception:
                            print(traceback.format_exc())
                            traceback_str = traceback.format_exc().splitlines()
                            log_list.append(f"An error occured when processing block {result_block_idx} / Timestamp: {result_block_end}")
                            log_list.extend(traceback_str)

                        
                        #translate the average measurements into results for each bridge element (displacements and rotations for each object)
                        for object_name, object_values in bridge_parameters.items():
                            try:
                                # Pillar 4 and 8 do not contain prisms, but total station -> no rotation around y axis
                                # notes: the roty_capcibility is hard code as True, shouldnt it be False?
                                if object_name in ["Pijler4", "Pijler8"]:
                                    bridge_calculation = bridge_pillar_totalstations(object_values, result_df_avg, reference_data,
                                                                                     result_block_end, object_name)
                                    print(f"Calculation finished for {object_name} / timestamp: {result_block_end}")
                                    # update the logbook
                                    log_list.extend(bridge_calculation.brigde_log)
                                    # create an object for SQL database with the new measurement (displacements (m and coordinate), rotations (m))
                                    if object_name in sql_objects:
                                        sql_objects[object_name].append(bridge_calculation.new_measurement)
                                    else:
                                        sql_objects[object_name] = [bridge_calculation.new_measurement]
                                    # prepare data to have a clear visualization in the Graphana 
                                    if "Oplegging_locaties" in sql_objects:
                                        oplegging_data = bridge_calculation.new_measurement.filter(regex="lokaal|RD|Name|Timestamp")
                                        oplegging_data = pivot_oplegging_data(oplegging_data)
                                        sql_objects["Oplegging_locaties"].append(oplegging_data)
                                    else:
                                        oplegging_data = bridge_calculation.new_measurement.filter(regex="lokaal|RD|Name|Timestamp")
                                        oplegging_data = pivot_oplegging_data(oplegging_data)
                                        sql_objects["Oplegging_locaties"] = [oplegging_data]

                                else:
                                    # calculation for the pillars with prisms and no total stations
                                    # include rotation y
                                    bridge_calculation = bridge_pillar_standard(object_values, result_df_avg, reference_data,
                                                                                result_block_end, object_name)
                                    print(f"Calculation finished for {object_name} / timestamp: {result_block_end}")
                                    # create an object for SQL database with the new measurement (displacements (m and coordinate), rotations (m))
                                    if object_name in sql_objects:
                                        sql_objects[object_name].append(bridge_calculation.new_measurement)
                                    else:
                                        sql_objects[object_name] = [bridge_calculation.new_measurement]

                                    # prepare data to have a clear visualization in the Graphana 
                                    if "Oplegging_locaties" in sql_objects:
                                        oplegging_data = bridge_calculation.new_measurement.filter(regex="lokaal|RD|Name|Timestamp")
                                        oplegging_data = pivot_oplegging_data(oplegging_data)
                                        sql_objects["Oplegging_locaties"].append(oplegging_data)
                                    else:
                                        oplegging_data = bridge_calculation.new_measurement.filter(regex="lokaal|RD|Name|Timestamp")
                                        oplegging_data = pivot_oplegging_data(oplegging_data)
                                        sql_objects["Oplegging_locaties"] = [oplegging_data]

                                    log_list.extend(bridge_calculation.brigde_log)

                            except ValueError as measurement_error:
                                    print(measurement_error)
                            except Exception:
                                print(traceback.format_exc())
                                traceback_str = traceback.format_exc().splitlines()
                                log_list.append(f"An error occured when processing bridge element {object_name} / Timestamp: {result_block_end}")
                                log_list.extend(traceback_str)
                    # determine all column names from an exisiting object
                    sql_columns = get_all_columns(sql_objects, table_name_measurements)
                    for object_name, sql_list in sql_objects.items():
                        # merge into one table
                        sql_data = pd.concat(sql_list)
                        if object_name not in [table_name_measurements, "average_measurements", "Oplegging_locaties"]:
                            for column in sql_columns:
                                # add the extra columns that miss for the calculated measurement data
                                if column not in sql_data.columns:
                                    sql_data[column] = "N/A"
                        # export to SQL
                        export_data_to_SQL(sql_data, grafana_db_host, grafana_db_user, 
                                               grafana_db_password, "Duyen_testing_merwede", grafana_db_port, object_name)

                    now_local = datetime.now()
                    # update the logbook
                    log_filename = os.path.join(log_directory, f"log_{now_local.day:02d}_{now_local.month:02d}.txt")
                    with open(log_filename, "a") as f:
                        for entry in log_list:
                            f.write(entry + "\n")
                    

if __name__ == "__main__":
    # loads environment variables from a .env file 
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
    # measurement data?
    table_name_measurements = os.getenv("TABLE_NAME_MEASUREMENTS")

    #input parameters for the bridge
    bridge_parameters = read_bridge_parameters()

    #zero-date
    zero_date = os.getenv("ZERO_DATE")
    # adjustment
    # log_directory = r"D:\monitoring\merwede\test"
    # results_directory = r"D:\monitoring\merwede\test"
    log_directory = r"C:\Work\Projecten\Merwegebrug\merwedebrug_python_backend\logbook"
    results_directory = r"C:\Work\Projecten\Merwegebrug\merwedebrug_python_backend\logbook"
    # export the output to SQL database
    main(geomos_host, geomos_port, geomos_api_key, geomos_projectid,grafana_db_host, grafana_db_user, 
         grafana_db_password, grafana_db_name, grafana_db_port, table_name_measurements, zero_date, log_directory, results_directory)
    # determine the time blocks
    fixed_times = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
    # for calculate the result for each time block
    for t in fixed_times:
        schedule.every().day.at(t).do(
            main,
            geomos_host=geomos_host,
            geomos_port=geomos_port,
            geomos_api_key=geomos_api_key,
            geomos_projectid=geomos_projectid,
            grafana_db_host=grafana_db_host,
            grafana_db_user=grafana_db_user,
            grafana_db_password=grafana_db_password,
            grafana_db_name=grafana_db_name,
            grafana_db_port=grafana_db_port,
            table_name_measurements=table_name_measurements,
            zero_date=zero_date,
            log_directory=log_directory,
            results_directory=results_directory  
        )

    print("Scheduler started. Running the script every  4 hours.")
    
    while True:
        schedule.run_pending()
        time.sleep(10)
