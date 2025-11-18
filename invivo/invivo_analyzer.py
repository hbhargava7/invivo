# Copyright 2025 Hersh K. Bhargava (https://hershbhargava.com)
# University of California, San Francisco

from .io import *

import os
import re
import datetime
import warnings
from warnings import warn

import matplotlib.pyplot as plt

class InVivoAnalyzer:

    def __init__(self, data_path: str, ignore_groups: list[int]=None):
        self.data_path = data_path
        self.ignore_groups = ignore_groups
        
        # confirm that the file exists
        if not os.path.exists(self.data_path):
            raise FileNotFoundError('Data file not found: %s' % self.data_path)

        print('Initializing InVivoAnalyzer with data from: %s' % self.data_path)
        print('-'*80)
        print('Finding relevant sheets in the data file...')
        print('-'*80)

        # Get the sheet names and analyze relevant sheets
        sheet_names = get_excel_sheet_names(self.data_path)

        if 'Data BW' in sheet_names:
            print('found bodyweight data in sheet `Data BW`')

        if 'Data MO' in sheet_names:
            print('found mortality data in sheet `Data MO`')

        # Look for sheets corresponding to tumor volume
        tumor_volume_sheets = []
        for sheet_name in sheet_names:
            if 'TV' in sheet_name:
                print(f'found tumor volume data in sheet `{sheet_name}`')
                tumor_volume_sheets.append(sheet_name)

        print('-'*80)
        print('Automatically parsing data from the sheets mentioned above.')
        print('-'*80)

        self.master_data = pd.DataFrame()

        # Parse bodyweight data
        bodyweight_df = parse_bodyweight_data(read_sheet_from_study_log_excel(self.data_path, "Data BW"))
        self.master_data = pd.concat([self.master_data, bodyweight_df])

        # Parse mortality data
        if 'Data MO' in sheet_names:

            mortality_df = parse_mortality_data(read_sheet_from_study_log_excel(self.data_path, "Data MO"))
            self.master_data = pd.concat([self.master_data, mortality_df])
    
        # Parse tumor volume data
        for sheet_name in tumor_volume_sheets:
            tumor_volume_df = parse_tumor_volume_data(read_sheet_from_study_log_excel(self.data_path, sheet_name), tumor_name=sheet_name)
            self.master_data = pd.concat([self.master_data, tumor_volume_df])

        # Move `Data Type` column to front
        self.master_data = self.master_data[['Data Type', *[col for col in self.master_data.columns if col != 'Data Type']]]

        # Convert Animal ID to string
        self.master_data['Animal ID'] = self.master_data['Animal ID'].astype(str)
    
        # Validate Animal ID format
        pattern = r'^\d+-\d+$'
        if not self.master_data['Animal ID'].str.match(pattern).all():
            warn('Warning: There are animal IDs in the spreadsheet that do not match the format "Integer-Integer". Dropping those entires.')

            # drop entries from `self.master_data` where `Animal ID` does not match the pattern
            self.master_data = self.master_data[self.master_data['Animal ID'].str.match(pattern)]

            # raise ValueError('Animal ID column does not match the format "Integer-Integer"')
        
        # Find the min date in the df
        self.min_date = self.master_data['Date'].min()
        print(f'The earliest date in the data is {self.min_date}. Treating this as the start of the experiment.')
        print('To override, call `self.set_study_start_date()` with a datetime object.')
        self.set_study_start_date(self.min_date)

        # Sort by days since start
        self.master_data = self.master_data.sort_values(by='Days Since Start')
 
        # Extract Group ID from Animal ID
        self.master_data['Group ID'] = self.master_data['Animal ID'].str.split('-').str[0].astype(int)

        print('-'*80)
        print('Found the following groups with the following sizes:')
        print(self.groups_summary_df())

        if self.ignore_groups is not None:
            print('-'*80)
            print('Dropping groups per `ignore_groups` parameter: %s' % self.ignore_groups)
            self.master_data = self.master_data[~self.master_data['Group ID'].isin(self.ignore_groups)]

        print('You can assign names to the groups by calling `self.set_group_names()` with an ordered list of group names.')
        print('-'*80)
    
    def set_study_start_date(self, date: datetime.datetime):
        """
        Set the start date of the study.
        """
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            warnings.warn('Date is a string, converting to datetime object')

        self.study_start_date = date
        self.master_data['Days Since Start'] = (self.master_data['Date'] - self.study_start_date).dt.days

    def set_group_names(self, group_names: list[str]):
        """
        Set the names of the groups.
        """
        print('-'*80)
        print('Setting group names (InVivoAnalyzer.set_group_names())...')
        print('-'*80)

        if len(group_names) != len(self.master_data['Group ID'].unique()):
            raise ValueError('Number of group names must match the number of groups')
        
        # Rename the groups in the master data
        original_group_ids = sorted(self.master_data['Group ID'].unique())

        for original_id, new_name in zip(original_group_ids, group_names):
            print('renaming group %s to %s' % (original_id, new_name))
            self.master_data.loc[self.master_data['Group ID'] == original_id, 'Group ID'] = new_name
        print('-'*80)
        print('The groups have been renamed to:')
        print(self.groups_summary_df())
    
    def groups_summary_df(self) -> pd.DataFrame:
        """
        Summarize the groups in the master data.
        
        Returns:
            DataFrame with columns:
                - Group ID: The group identifier
                - Number of Animals: Count of animals in each group
        """
        # get `master data` with only one entry per animal
        master_data_unique = self.master_data.drop_duplicates(subset=['Animal ID'])
        # get the number of animals in each group
        vc = master_data_unique['Group ID'].value_counts()
        # sort by group ID
        vc = vc.sort_index()
        # convert to DataFrame with named columns
        df = pd.DataFrame({
            'Group ID': vc.index,
            'Number of Animals': vc.values
        })
        return df
    
    def plot_survival_curves(self, ax=None, fractional=False, figsize=(6, 5)):
        """
        Plot the survival curves.

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The axes to plot the survival curves on. If None, a new figure and axes will be created.
        fractional: bool
            If True, the survival curves will be plotted as fractional survival (i.e. the proportion of animals surviving at each timepoint).
            If False, the survival curves will be plotted as the number of animals surviving at each timepoint.

        """
        mortality_data = self.master_data[self.master_data['Data Type'] == 'Mortality']

        df_survival = pd.DataFrame(columns=['Group', 'Timepoint', 'N Surviving'])

        all_timepoints = self.master_data['Days Since Start'].unique()

        data = []

        for group_id in self.master_data['Group ID'].unique():

            group_data = self.master_data[self.master_data['Group ID'] == group_id]

            for timepoint in all_timepoints:
                n_alive_at_timepoint = 0

                for animal_id in group_data['Animal ID'].unique():

                    mortalities_to_date = mortality_data[mortality_data['Days Since Start'] <= timepoint]

                    if animal_id not in mortalities_to_date['Animal ID'].unique():
                        n_alive_at_timepoint += 1

                if fractional:
                    data.append({'Group': group_id, 'Days Since Start': timepoint, 'Fraction Surviving': n_alive_at_timepoint / len(group_data['Animal ID'].unique())})
                else:
                    data.append({'Group': group_id, 'Days Since Start': timepoint, 'N Surviving': n_alive_at_timepoint})

        df_survival = pd.DataFrame(data)

        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        
        # Iterate over each group and plot the survival curve as a step plot
        for group in df_survival['Group'].unique():
            _df = df_survival[df_survival['Group'] == group]
            if fractional:
                plt.step(_df['Days Since Start'], _df['Fraction Surviving'], where='post', label="%s" %  group)
            else:
                plt.step(_df['Days Since Start'], _df['N Surviving'], where='post', label="%s" %  group)

        # Rotate the axis labels and set align to right
        plt.xticks(rotation=45, ha='right')

        # Add legend to the right via bbox
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        # Set labels and title
        plt.xlabel('Days Since Study Start')
        if fractional:
            plt.ylabel('Fraction Surviving')
        else:
            plt.ylabel('N Surviving')
        plt.ylim(bottom=0)

        plt.tight_layout()

        if fig is not None:
            return fig, ax

    def plot_data_bygroup(self, measurement_type: str, show_individual_traces:bool=False, ax=None, figsize=(6, 5), dates_to_plot:dict[str, datetime.datetime]=None):
        """
        Plot data by group.

        Parameters
        ----------
        measurement_type: str
            The type of measurement to plot. This should be one of observation types in `self.master_data['Data Type']`.
        show_individual_traces: bool, optional
            If True, the individual traces for each animal will be plotted.
        ax: matplotlib.axes.Axes, optional
            The axes to plot the data on. If None, a new figure and axes will be created.
        figsize: tuple, optional
            The size of the figure. If not provided, a default size will be used.
        dates_to_plot: dict[str, datetime.datetime], optional
            A dictionary of dates to plot. They keys are the annotations and the values are the dates of interest.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        df = self.master_data[self.master_data['Data Type'] == measurement_type]

        # Cast the `Value` column to float
        df['Value'] = df['Value'].astype(float)

        grouped = df.groupby(['Group ID', 'Days Since Start'])['Value'].agg(['mean', 'std']).reset_index()

        for group in df['Group ID'].unique():
            group_data = grouped[grouped['Group ID'] == group]
            ax.plot(group_data['Days Since Start'], group_data['mean'], label=f'({group})', lw=4)
            ax.fill_between(group_data['Days Since Start'], group_data['mean'] - group_data['std'], group_data['mean'] + group_data['std'], alpha=0.1)

        if dates_to_plot is not None:
            for date_label, date in dates_to_plot.items():
                ax.axvline(self.date_to_days_since_start(date), linestyle='--', label=date_label)

        ax.set_title(f'{measurement_type} by Group')
        ax.set_xlabel('Days Since Start')
        ax.set_ylabel(measurement_type)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        if fig is not None:
            return fig, ax
        
    def date_to_days_since_start(self, date: datetime.datetime) -> int:
        """
        Convert a date to days since start.
        """
        if isinstance(date, str):
            # YYYY-MM-DD format to datetime object
            date = datetime.datetime.strptime(date, '%Y-%m-%d')

        return (date - self.study_start_date).days

    def subplot_data_bygroup(
        self,
        measurement_type: str,
        control_group_id: str = None,
        figsize=None,
        individual_traces_for_control=False,
        dates_to_plot: dict[str, datetime.datetime] = None,
        control_group_subplot=True,
        norm_to_first_measurement: bool = False,
    ):
        """
        Plot data by group in a subplot.

        Parameters
        ----------
        measurement_type: str
            The type of measurement to plot. This should be one of observation types in `self.master_data['Data Type']`.
        control_group_id: str, optional
            The ID of the control group. If provided, the control group will be plotted in black.
        figsize: tuple, optional
            The size of the figure. If not provided, a default size will be used.
        individual_traces_for_control: bool, optional
            If True, the individual traces for the control group will be plotted.
        dates_to_plot: dict[str, datetime.datetime], optional
            A dictionary of dates to plot. Keys are annotations and values are the dates of interest.
        control_group_subplot: bool, optional
            If False, skips plotting an individual subplot for the control group.
        norm_to_first_measurement: bool, optional
            If True, normalize each mouse’s values by its first recorded value.
            Default is False.
        """

        df = self.master_data[self.master_data['Data Type'] == measurement_type].copy()
        groups_to_plot = df['Group ID'].unique()

        # --- Normalize to first measurement if requested ---
        if norm_to_first_measurement:
            df['Value'] = df.groupby('Animal ID')['Value'].transform(lambda x: x / x.iloc[0])

        # --- Handle control group logic ---
        if control_group_id is not None:
            if control_group_id not in groups_to_plot:
                raise ValueError('Control group ID not found in the data')

            if not control_group_subplot:
                groups_to_plot = groups_to_plot[groups_to_plot != control_group_id]
            else:
                groups_to_plot = [control_group_id] + [g for g in groups_to_plot if g != control_group_id]

        # --- Figure setup ---
        if figsize is None:
            figsize = (4 * len(groups_to_plot), 4)

        fig, axs = plt.subplots(1, len(groups_to_plot), sharex=True, sharey=True, figsize=figsize)

        if len(groups_to_plot) == 1:
            axs = [axs]  # Ensure iterable

        control_df = df[df['Group ID'] == control_group_id] if control_group_id is not None else None

        # --- Plotting loop ---
        for ax, group_id in zip(axs, groups_to_plot):
            # Plot control traces if needed
            if control_group_id is not None:
                if individual_traces_for_control:
                    for mouse in control_df['Animal ID'].unique():
                        mouse_df = control_df[control_df['Animal ID'] == mouse]
                        ax.plot(mouse_df['Days Since Start'], mouse_df['Value'], color='grey', alpha=0.8, lw=.25)

                ctrl_stats = control_df.groupby('Days Since Start')['Value'].agg(['mean', 'sem']).reset_index()

                # 1. Error bars only
                ax.errorbar(
                    ctrl_stats['Days Since Start'],
                    ctrl_stats['mean'],
                    yerr=ctrl_stats['sem'],
                    fmt='none',               # no markers here
                    ecolor='grey',
                    elinewidth=1.0,
                    capsize=2,
                    capthick=1.0
                )

                # 2. Mean line + open-circle markers
                ax.plot(
                    ctrl_stats['Days Since Start'],
                    ctrl_stats['mean'],
                    color='grey',
                    lw=3,
                    marker='o',
                    mfc='white', mec='grey', mew=2.5, ms=8   # thick edge, open circle
                )


            # Add vertical reference lines if provided
            if dates_to_plot is not None:
                for date_label, date in dates_to_plot.items():
                    ax.axvline(self.date_to_days_since_start(date), color='grey', linestyle='--', label=date_label)

            # Plot current group traces
            group_df = df[df['Group ID'] == group_id]
            for mouse in group_df['Animal ID'].unique():
                mouse_df = group_df[group_df['Animal ID'] == mouse]
                ax.plot(mouse_df['Days Since Start'], mouse_df['Value'], color='#d80032', alpha=0.8, lw=.25)

            # mean_df = group_df[['Days Since Start', 'Value']].groupby('Days Since Start').mean().reset_index()
            # ax.plot(mean_df['Days Since Start'], mean_df['Value'], label=group_id, lw=3, alpha=1, color='#d80032')

            grp_stats = group_df.groupby('Days Since Start')['Value'].agg(['mean', 'sem']).reset_index()
            ax.errorbar(
                grp_stats['Days Since Start'],
                grp_stats['mean'],
                yerr=grp_stats['sem'],
                fmt='none',               # no markers here
                ecolor='#d80032',
                elinewidth=1.0,           # thin error bars
                capsize=2,
                capthick=1.0
            )

            ax.plot(
                grp_stats['Days Since Start'],
                grp_stats['mean'],
                color='#d80032',
                lw=3,
                marker='o',
                mfc='white', mec='#d80032', mew=2.5, ms=8   # thick edge, open circle
            )

            # Titles and labels
            title = f"{group_id} (Control)" if group_id == control_group_id else group_id
            ax.set_title(title)
            ax.set_xlabel('Days Since Start')

            # Adjust y-axis label depending on normalization
            y_label = measurement_type
            if norm_to_first_measurement:
                y_label += " (normalized to first measurement)"
            ax.set_ylabel(y_label)

        plt.tight_layout()

        if fig is not None:
            return fig, axs
