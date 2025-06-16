# Copyright 2025 Hersh K. Bhargava (https://hershbhargava.com)
# University of California, San Francisco

import pandas as pd

def get_excel_sheet_names(path: str) -> list[str]:
    """
    Get the names of all sheets in an Excel file.
    
    Args:
        path: Path to the Excel file
        
    Returns:
        List of sheet names
    """
    return pd.ExcelFile(path).sheet_names

def read_sheet_from_study_log_excel(path: str, sheet_name: str) -> pd.DataFrame:
    """
    Read a sheet from a study log Excel file.
    """

    # Read the sheet
    df = pd.read_excel(path, sheet_name=sheet_name, skiprows=5)

    # Drop columns that are all Nan
    df = df.dropna(axis=1, how='all')
    
    return df 

def parse_bodyweight_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse bodyweight data from a DataFrame.

    Expect columns: "Animal ID", "Date", "Value", "Recorded Time", and "Entered by"

    """
    bodyweight_df = df.copy()

    bodyweight_df = bodyweight_df[["Animal ID", "Date", "Value", "Recorded Time", "Entered by"]]

    # cast date columns to datetime
    bodyweight_df['Date'] = pd.to_datetime(bodyweight_df['Date'])
    bodyweight_df['Recorded Time'] = pd.to_datetime(bodyweight_df['Recorded Time'])

    # Add a column to indicate that these records are bodyweight data
    bodyweight_df['Data Type'] = 'Bodyweight'

    return bodyweight_df

def parse_mortality_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse mortality data from a DataFrame.

    Expect columns: "Animal ID", "Date", "Value", "Recorded Time", and "Entered by"

    Note that the Mortality data sheet contains entries only for mice that have died. So the presence of an entry for an
    animal indicates that the animal has died.

    """
    mortality_df = df.copy()

    mortality_df = mortality_df[["Animal ID", "Date", "Value", "Recorded Time", "Entered by"]]

    # cast date columns to datetime
    mortality_df['Date'] = pd.to_datetime(mortality_df['Date'])
    mortality_df['Recorded Time'] = pd.to_datetime(mortality_df['Recorded Time'])

    mortality_df['Data Type'] = 'Mortality'


    return mortality_df

def parse_tumor_volume_data(df: pd.DataFrame, tumor_name='TV') -> pd.DataFrame:
    """
    Parse tumor volume data from a DataFrame.

    Expect columns: "Animal ID", "Date", "Value", "Recorded Time", and "Entered by"

    Parameters
    ----------
    df: pd.DataFrame
        The DataFrame to parse.

    tumor_name: str
        The name of the tumor (important in bilateral flank or other multi-tumor experiments)

    """
    tumor_volume_df = df.copy()

    tumor_volume_df = tumor_volume_df[["Animal ID", "Date", "Value", "Recorded Time", "Entered by"]]

    # cast date columns to datetime
    tumor_volume_df['Date'] = pd.to_datetime(tumor_volume_df['Date'])
    tumor_volume_df['Recorded Time'] = pd.to_datetime(tumor_volume_df['Recorded Time'])

    # Add a column to indicate that these records are tumor volume data
    tumor_volume_df['Data Type'] = 'Tumor Volume %s' % tumor_name

    return tumor_volume_df

def extract_group_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Group ID from Animal ID by taking the first integer before the hyphen.
    
    Args:
        df: DataFrame containing an "Animal ID" column
        
    Returns:
        DataFrame with added "Group ID" column
    """
    df = df.copy()
    df['Group ID'] = df['Animal ID'].str.split('-').str[0].astype(int)
    return df

    
    

    

    