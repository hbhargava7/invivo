# Copyright 2025 Hersh K. Bhargava (https://hershbhargava.com)
# University of California, San Francisco

import re

import pandas as pd


_CANONICAL_ANIMAL_ID_PATTERN = re.compile(r'^(\d+)-(\d+)$')
_GROUP_PREFIXED_ANIMAL_ID_PATTERN = re.compile(r'^Group\s+(\d+)-(\d+)$', re.IGNORECASE)


def normalize_animal_ids(animal_ids: pd.Series) -> pd.Series:
    """Validate animal IDs and return them in canonical ``group-animal`` form.

    Accepted input formats are ``1-2`` and the Studylog-exported
    ``Group 01-002``. Group-prefixed IDs are converted to ``1-2`` so callers
    can use the same identifiers regardless of which Studylog format produced
    the workbook.

    Raises
    ------
    ValueError
        If any value does not match a supported format.
    """
    animal_ids = animal_ids.astype('string').str.strip()
    canonical_matches = animal_ids.str.fullmatch(_CANONICAL_ANIMAL_ID_PATTERN, na=False)
    group_prefixed_matches = animal_ids.str.fullmatch(_GROUP_PREFIXED_ANIMAL_ID_PATTERN, na=False)
    valid_matches = canonical_matches | group_prefixed_matches

    if not valid_matches.all():
        invalid_ids = animal_ids[~valid_matches].drop_duplicates().tolist()
        displayed_ids = ['<missing>' if pd.isna(value) else repr(value) for value in invalid_ids[:5]]
        if len(invalid_ids) > 5:
            displayed_ids.append(f'... and {len(invalid_ids) - 5} more')

        invalid_row_count = int((~valid_matches).sum())
        raise ValueError(
            f'Found {invalid_row_count} record(s) with incompatible Animal ID values: '
            f'{", ".join(displayed_ids)}. Accepted formats are "<group>-<animal>" '
            f'(for example, "1-2") and "Group <group>-<animal>" '
            f'(for example, "Group 01-002"); both portions must contain digits only. '
            f'Correct the Animal ID values in the study log and try again. No records were dropped.'
        )

    normalized_ids = animal_ids.copy()
    prefixed_parts = animal_ids[group_prefixed_matches].str.extract(
        _GROUP_PREFIXED_ANIMAL_ID_PATTERN
    )
    normalized_ids.loc[group_prefixed_matches] = (
        prefixed_parts[0].astype(int).astype(str)
        + '-'
        + prefixed_parts[1].astype(int).astype(str)
    )
    return normalized_ids


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

    Expect columns: "Animal ID", "Date", "Value", "Recorded Time", and "Entered by".
    New-format sheets use "Weight" instead of "Value"; both are accepted.
    """
    bodyweight_df = df.copy()

    if 'Value' not in bodyweight_df.columns and 'Weight' in bodyweight_df.columns:
        bodyweight_df = bodyweight_df.rename(columns={'Weight': 'Value'})

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

    New-format sheets use "Mortality" instead of "Value"; both are accepted.
    """
    mortality_df = df.copy()

    if 'Value' not in mortality_df.columns and 'Mortality' in mortality_df.columns:
        mortality_df = mortality_df.rename(columns={'Mortality': 'Value'})

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

    New-format sheets use "Volume" instead of "Value"; both are accepted.
    """
    tumor_volume_df = df.copy()

    if 'Value' not in tumor_volume_df.columns and 'Volume' in tumor_volume_df.columns:
        tumor_volume_df = tumor_volume_df.rename(columns={'Volume': 'Value'})

    tumor_volume_df = tumor_volume_df[["Animal ID", "Date", "Value", "Recorded Time", "Entered by"]]

    # cast date columns to datetime
    tumor_volume_df['Date'] = pd.to_datetime(tumor_volume_df['Date'])
    tumor_volume_df['Recorded Time'] = pd.to_datetime(tumor_volume_df['Recorded Time'])

    # Add a column to indicate that these records are tumor volume data
    tumor_volume_df['Data Type'] = 'Tumor Volume %s' % tumor_name

    return tumor_volume_df

def extract_group_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize Animal IDs and extract the integer group portion before the hyphen.
    
    Args:
        df: DataFrame containing an "Animal ID" column
        
    Returns:
        DataFrame with added "Group ID" column
    """
    df = df.copy()
    df['Animal ID'] = normalize_animal_ids(df['Animal ID'])
    df['Group ID'] = df['Animal ID'].str.split('-').str[0].astype(int)
    return df
