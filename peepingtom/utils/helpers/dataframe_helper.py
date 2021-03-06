import numpy as np
import pandas as pd
from eulerangles import euler2matrix

from ..validators import columns_in_df
from ..constants import relion_coordinate_headings_3d, relion_shift_headings_3d, \
    relion_euler_angle_headings, dynamo_table_coordinate_headings, dynamo_table_shift_headings, \
    dynamo_euler_angle_headings

from ..exceptions import DataFrameError


def _check_mode(mode):
    modes = ['relion', 'dynamo']
    if mode not in modes:
        raise ValueError(f'mode can only be one of {modes}; got {mode}')


def df_to_xyz(df: pd.DataFrame, mode: str):
    """

    Parameters
    ----------
    df : RELION format STAR file as DataFrame (usually the result of starfile.read)

    mode: one of 'relion', 'dynamo'

    Returns (n, 3) ndarray of xyz positions from the DataFrame
    -------

    """
    coord_columns = {
        'relion': relion_coordinate_headings_3d,
        'dynamo': dynamo_table_coordinate_headings
    }
    shift_columns = {
        'relion': relion_shift_headings_3d,
        'dynamo': dynamo_table_shift_headings,
    }
    _check_mode(mode)
    # get xyz coordinates from dataframe
    if not columns_in_df(coord_columns[mode], df):
        raise DataFrameError("Could not get coordinates from DataFrame")

    positions = df[coord_columns[mode]] + df.get(shift_columns[mode], 0)

    return positions.to_numpy()


def df_to_euler_angles(df: pd.DataFrame, mode: str):
    """

    Parameters
    ----------
    df : RELION format STAR file as DataFrame (usually the result of starfile.read)

    Returns : (n, 3) ndarray of euler angles rot, tilt, phi from the DataFrame
    -------

    """
    angle_columns = {
        'relion': relion_euler_angle_headings,
        'dynamo': dynamo_euler_angle_headings,
    }
    _check_mode(mode)
    if not columns_in_df(angle_columns[mode], df):
        raise DataFrameError("Could not get euler angles from DataFrame")
    euler_angles = df[angle_columns[mode]]
    return euler_angles.to_numpy()


def euler_angles_to_rotation_matrices(euler_angles: np.ndarray, mode: str):
    """

    Parameters
    ----------
    euler_angles : (n, 3) ndarray or RELION euler angles

    Returns (n, 3, 3) ndarray of rotation matrices which premultiply column vectors [x, y, z]
    -------

    """
    euler_kwargs = {
        'relion': {'axes': 'zyz', 'intrinsic': True, 'positive_ccw': True},
        'dynamo': {'axes': 'zxz', 'intrinsic': True, 'positive_ccw': True}
    }
    _check_mode(mode)
    return euler2matrix(euler_angles, **euler_kwargs[mode])


def df_to_rotation_matrices(df: pd.DataFrame, mode: str):
    """

    Parameters
    ----------
    df : RELION format STAR file as DataFrame (usually the result of starfile.read)

    Returns : (n, 3, 3) ndarray of rotation matrices which premultiply column vectors [x, y, z]
    -------

    """
    euler_angles = df_to_euler_angles(df, mode)
    rotation_matrices = euler_angles_to_rotation_matrices(euler_angles, mode)
    return rotation_matrices


def df_split_on_volume(df: pd.DataFrame):
    """

    Parameters
    ----------
    df : RELION format STAR file as DataFrame (usually the result of starfile.read)

    Returns dict {name : df} of DataFrame objects
            one for each volume in a star file based on the 'rlnMicrographName' column
    -------

    """
    grouped = df.groupby('rlnMicrographName')
    return {name: _df for name, _df in grouped}
