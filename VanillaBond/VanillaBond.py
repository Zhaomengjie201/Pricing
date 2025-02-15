import gs_quant.timeseries as ts
from gs_quant.timeseries import Window
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
from datetime import datetime
from selenium import webdriver
import time
import requests 
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import random
from gs_quant.session import Environment, GsSession
from datetime import date
from gs_quant.session import GsSession, Environment
from gs_quant.markets import PricingContext
from openpyxl import load_workbook
import QuantLib as ql
from gs_quant.instrument import Bond
from gs_quant.markets import Market
from gs_quant.datetime import DayCountConvention
import re
import os

############## corrected code
# Load the Excel file
base_path = os.path.dirname(os.path.realpath(__file__))
file_path = os.path.join(base_path,"Bonds_list.xlsx")
sheet_name = "Sheet1"
df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
df.columns = df.columns.str.strip()  # Remove any extra spaces from column names

# Read the Excel file
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Ensure column for bond price exists
price_column_name = "Bond Price"
if price_column_name not in df.columns:
    df[price_column_name] = None  

# Define Bond Parameters by Country
bond_parameters = {
    "UK" or "U.K.": {
        "settlement_days": 2,
        "frequency": ql.Semiannual,
        "day_count": ql.ActualActual(ql.ActualActual.ISMA),
        "calendar": ql.UnitedKingdom(),
        "business_convention": ql.Unadjusted
    },
    "US": {
        "settlement_days": 2,
        "frequency": ql.Semiannual,
        "day_count": ql.ActualActual(ql.ActualActual.Bond),
        "calendar": ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        "business_convention": ql.Following
    },
    # "EU": {
    #     "settlement_days": 2,
    #     "frequency": ql.Annual,
    #     "day_count": ql.Thirty360(ql.Thirty360.EurobondBasis),
    #     "calendar": ql.TARGET(),
    #     "business_convention": ql.ModifiedFollowing
    # },
    "Japan": {
        "settlement_days": 2,
        "frequency": ql.Annual,
        "day_count": ql.ActualActual(ql.ActualActual.ISMA),
        "calendar": ql.Japan(),
        "business_convention": ql.Unadjusted
    },
    # "Canada": {
    #     "settlement_days": 2,
    #     "frequency": ql.Semiannual,
    #     "day_count": ql.ActualActual(ql.ActualActual.Bond),
    #     "calendar": ql.Canada(),
    #     "business_convention": ql.ModifiedFollowing
    # },
    # "Australia": {
    #     "settlement_days": 2,
    #     "frequency": ql.Semiannual,
    #     "day_count": ql.ActualActual(ql.ActualActual.ISMA),
    #     "calendar": ql.Australia(),
    #     "business_convention": ql.Following
    # },
    "Spain": {
        "settlement_days": 3,
        "frequency": ql.Semiannual,
        "day_count": ql.ActualActual(ql.ActualActual.ISMA),
        "calendar": ql.TARGET(),
        "business_convention": ql.Following
    },
    "Germany": {
        "settlement_days": 2,
        "frequency": ql.Semiannual,
        "day_count": ql.ActualActual(ql.ActualActual.ISMA),
        "calendar": ql.Germany(ql.Germany.Eurex),
        "business_convention": ql.ModifiedFollowing
    },
    "Italy": {
        "settlement_days": 2,
        "frequency": ql.Semiannual,
        "day_count": ql.ActualActual(ql.ActualActual.ISMA),
        "calendar": ql.Italy(),
        "business_convention": ql.ModifiedFollowing
    }
}

# Step 2: Function to Extract Country from Bond Name
def extract_country(bond_name):
    
    # Handling both "UK" and "U.K." 
    bond_name = bond_name.replace(".", "").upper()
    for country in bond_parameters.keys():
        country_name = country.replace(".", "").upper() 
        # If the country name is a substring of the bond name, we have found it...
        if country_name in bond_name:
            return country
    return None  # Return None if no country match is found

def CalculatePrice(today=None):
        
    fields = ["Country","Issue","Maturity","Price","Bond"]
    #print(f"{"Price":<10} {"Country":<10} {"Issue":<10}  {"Maturity":<10} {"Bond"}")
    header = " | ".join(f"{field:<{10}}" for field in fields)
    print(header)

    # Step 3: Process Each Bond and Calculate Price
    for index, row in df.iterrows():
        try:
            # Extract bond parameters
            bond_name = row["Bond name"]  # Assuming "Issue Date" is a column
            maturity_date_dt = pd.to_datetime(row["Maturity"])
            coupon_rate = float(row["Coupon rate"])/100
            face_value = float(row["FV"])
            market_yield = float(row["Yield"])/100  

            # Extract country from Bond Name
            country = extract_country(bond_name)
            if not country:
                raise ValueError(f"Could not determine country for bond: {bond_name}")

            # Extract bond term (years) from Bond Name using regex
            match = re.search(r"(\d+)", bond_name)
            if match:
                issue_years = int(match.group(1))
            else:
                raise ValueError(f"Bond Name '{bond_name}' does not contain a valid maturity period (e.g., '10').")

            # Convert Maturity Date to QuantLib.Date
            maturity_date = ql.Date(maturity_date_dt.day, maturity_date_dt.month, maturity_date_dt.year)

            # Calculate Issue Date by subtracting the bond term
            issue_date = maturity_date - ql.Period(issue_years, ql.Years)

            # If we have a supplied an issue date override use that
            if today is not None:
                issue_date = today

            # Get bond parameters based on extracted country
            params = bond_parameters[country]

            #print(country," = ",params)
            #continue

            # Create Fixed Rate Bond Schedule
            schedule = ql.Schedule(
                issue_date,
                maturity_date,
                ql.Period(params["frequency"]),
                params["calendar"],
                params["business_convention"],
                params["business_convention"],
                ql.DateGeneration.Backward,
                False
            )

            # Create the Fixed Rate Bond
            bond = ql.FixedRateBond(
                params["settlement_days"],
                face_value,
                schedule,
                [coupon_rate],
                params["day_count"]
            )

            # Calculate Clean Price of the Bond
            bond_price = ql.BondFunctions.cleanPrice(bond, market_yield, params["day_count"], ql.Compounded, params["frequency"])

            # Store the calculated price in column 14
            df.loc[index, price_column_name] = bond_price

            # Print Results
            #print(f"Bond: {bond_name}, Country: {country}, Issue Date: {issue_date}, Maturity: {maturity_date}, Price: {bond_price:.2f}")

            print(f"{country:<10} | {issue_date.ISO():<10} | {maturity_date.ISO():<10} | {bond_price:10.2f} | {bond_name:<10}")
            
        except Exception as e:
            print(f"Error processing bond at row {index + 1}: {e}")


# Calculate price with default issue date
print("\n\nCalculations using issue date:")
CalculatePrice()

# Calculate price with today as issue date
print("\n\nCalculations using todays date:")
CalculatePrice(ql.Date().todaysDate())

# Step 4: Save Updated Excel File
output_file_path = r"C:\Work\Code\Jefferies\Vanilla bond\Bonds_list-2.xlsx"
df.to_excel(output_file_path, index=False)



       