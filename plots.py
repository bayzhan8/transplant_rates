import logging
import os
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns

from .plot_style import apply_plot_style, spectral_colors, spectral_rgba_rgb

logger = logging.getLogger(__name__)


def cpra_rate_xy_plot(path_person_times_list, final_epts, final_cpra, donor, name_dict, read_output, step=-1, save_plot=False, name=None):
    """
    Generates a bar plot of CPRA-specific rates for multiple (path, person_times) inputs.

    Inputs:
        path_person_times_list - list of tuples (path, person_times DataFrame)
        final_epts - input parameter for read_output, type varies
        final_cpra - input parameter for read_output, type varies
        donor - input parameter for read_output, type varies
        step - bin size for CPRA bins, default=-1 (uses predefined bins)
    """
    if step == -1:
        cpra_bins = [[0, 0.6], [0.6, 0.8], [0.8, 0.98], [0.98, 1]]
    else:
        cpra_bins = [[lb / 100, (lb + step) / 100] for lb in range(0, 101, step) if (lb + step) <= 100]

    # Prepare data for grouped bar chart
    all_data = {}
    bin_labels = [f"{int(lb*100)}-{int(ub*100)}" for lb, ub in cpra_bins]
    
    for path, person_times in path_person_times_list:
        # Read and preprocess the data
        output = read_output(path, final_epts, final_cpra, donor)

        y = []
        for lb, ub in cpra_bins:
            # Count number of transplants in this CPRA bin
            num_matched = len(output[(lb < output["canhx_cpra"]) & (output["canhx_cpra"] <= ub)])
            # Sum total waitlist time (in days) for candidates in this CPRA bin
            total_time = person_times[(lb <= person_times["canhx_cpra"]) & (person_times["canhx_cpra"] < ub)]["time_difference"].sum()
            # Calculate transplant rate: (transplants / total_days) * 365 = transplants per patient-year
            rate = 365 * num_matched / total_time if total_time > 0 else 0
            y.append(rate)

        # Extract dataset name from the file path
        dataset_name = os.path.basename(path)
        if dataset_name in name_dict.keys():
            dataset_name = name_dict[dataset_name]
        
        all_data[dataset_name] = y

    # Create DataFrame for plotting
    df = pd.DataFrame(all_data, index=bin_labels)
    
    # Use a semi-transparent Spectral palette for consistency with bar plots
    base_palette = sns.color_palette("Spectral", n_colors=len(df.columns))
    color_palette = [(r, g, b, 0.8) for r, g, b in base_palette]
    
    # Plot grouped bar chart
    ax = df.plot(kind='bar', figsize=(12, 6), width=0.8, color=color_palette)
    
    # Add numbers inside each bar
    for container in ax.containers:
        ax.bar_label(container, label_type='center', fmt='%.3f', fontsize=12, color='black', rotation=90)
    
    # Finalize the plot
    # plt.title('Transplant Rates by CPRA')
    plt.xlabel('CPRA')
    plt.ylabel('Transplant Rate (per patient year)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    if save_plot:
        fname = name or "cpra_rate_xy_plot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def age_rate_xy_plot(path_person_times_list, final_epts, final_cpra, donor, name_dict, read_output, step=-1, save_plot=False, name=None):
    """
    Generates a bar plot of age-specific rates for multiple (path, person_times) inputs.

    Inputs:
        path_person_times_list - list of tuples (path, person_times DataFrame)
        step - bin size for age bins, default=-1 (uses predefined age ranges)
    """
    if step == -1:
        age_bins = [(0, 18), (18, 35), (35, 50), (50, 65), (65, 90)]
    else:
        age_bins = [(lb, lb + step) for lb in range(0, 91, step)]

    # Prepare data for grouped bar chart
    all_data = {}
    bin_labels = [f"{int(lb)}-{int(ub)}" for lb, ub in age_bins]
    
    for path, person_times in path_person_times_list:
        # Read and preprocess the data
        output = pd.read_csv(path)
        # Exclude pancreas transplants, keep only kidney transplants
        output = output[output["organ"] != 'pa']
        # Merge with person_times to get age information
        output_with_age = output.merge(person_times[['cand_id', 'real_age', 'time_difference']], on='cand_id', how='left')

        y = []
        for lb, ub in age_bins:
            # Count number of transplants in this age bin
            num_matched = len(output_with_age[(lb < output_with_age["real_age"]) & (output_with_age["real_age"] <= ub)])
            # Sum total waitlist time (in days) for candidates in this age bin
            total_time = person_times[(lb < person_times["real_age"]) & (person_times["real_age"] <= ub)]["time_difference"].sum()
            # Calculate transplant rate: (transplants / total_days) * 365 = transplants per patient-year
            rate = 365 * num_matched / total_time if total_time > 0 else 0
            y.append(rate)

        # Extract dataset name from the file path
        dataset_name = os.path.basename(path)
        if dataset_name in name_dict.keys():
            dataset_name = name_dict[dataset_name]
        
        all_data[dataset_name] = y

    # Create DataFrame for plotting
    df = pd.DataFrame(all_data, index=bin_labels)
    
    # Use a semi-transparent Spectral palette for consistency with bar plots
    base_palette = sns.color_palette("Spectral", n_colors=len(df.columns))
    color_palette = [(r, g, b, 0.8) for r, g, b in base_palette]
    
    # Plot grouped bar chart
    ax = df.plot(kind='bar', figsize=(12, 6), width=0.8, color=color_palette)
    
    # Add numbers inside each bar
    for container in ax.containers:
        ax.bar_label(container, label_type='center', fmt='%.3f', fontsize=12, color='black', rotation=90)
    
    # Finalize the plot
    # plt.title('Transplant Rates by Age')
    plt.xlabel('Age')
    plt.ylabel('Transplant Rates (per patient year)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    if save_plot:
        fname = name or "age_rate_xy_plot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def marginal_xy_plot(paths, final_epts, final_cpra, donor, name_dict, read_output, step=20, save_plot=False, name=None):
    """
    Generates a bar plot for total matches by EPTS bins for multiple input files with labels from paths.

    Inputs:
        paths - a list of paths to OASIM output files, list of strings
        final_epts - input parameter for read_output, type varies
        final_cpra - input parameter for read_output, type varies
        donor - input parameter for read_output, type varies
        step - bin size for EPTS bins, default=20
    """
    # Prepare data for grouped bar chart
    all_data = {}
    bin_labels = None
    
    for path in paths:
        # Extract dataset name from the file path
        dataset_name = os.path.basename(path)
        if dataset_name in name_dict.keys():
            dataset_name = name_dict[dataset_name]
        
        # Read and process the data
        output = read_output(path, final_epts, final_cpra, donor)
        
        # Create bins for EPTS, ensuring 0 and 100 are included
        bins = np.arange(0, 101, step) / 100  # Generate bins in percentage form
        bins[-1] = 1.0  # Ensure the last bin edge is exactly 1 (100%)
        output['epts_bin'] = pd.cut(output['epts_pct'], bins, right=False, include_lowest=True)
        
        # Group by EPTS bins and count matches
        total_matches = output.groupby('epts_bin', observed=False).size()
        
        # Prepare bin labels (only need to do this once)
        if bin_labels is None:
            bin_labels = [f"{int(cat.left*100)}-{int(cat.right*100)}" for cat in total_matches.index.categories]
        
        # Store the data
        all_data[dataset_name] = total_matches.values

    # Create DataFrame for plotting
    df = pd.DataFrame(all_data, index=bin_labels)
    
    # Use a semi-transparent Spectral palette for consistency with bar plots
    base_palette = sns.color_palette("Spectral", n_colors=len(df.columns))
    color_palette = [(r, g, b, 0.8) for r, g, b in base_palette]
    
    # Plot grouped bar chart
    ax = df.plot(kind='bar', figsize=(12, 6), width=0.8, color=color_palette)
    
    # Add numbers inside each bar
    for container in ax.containers:
        ax.bar_label(container, label_type='center', fmt='%d', fontsize=12, color='black', rotation=90)
    
    # Finalize the plot
    # plt.title('Total Matches by EPTS')
    plt.xlabel('EPTS')
    plt.ylabel('Total Matches')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    if save_plot:
        fname = name or "marginal_xy_plot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()




def marginal_difference_heatmap(first_path, second_path, final_epts, final_cpra, donor, read_output, step=20, save_plot=False, name=None):
    """
    Generates a heatmap showing the marginal percentage differences between two datasets.
    Uses the same logic as marginal_xy_plot to count matches per EPTS bin.

    Inputs:
        first_path - a path to the first OASIM output file (reference), string
        second_path - a path to the second OASIM output file (comparison), string
        final_epts - input parameter for read_output, type varies
        final_cpra - input parameter for read_output, type varies
        donor - input parameter for read_output, type varies
        read_output - function to read output data
        step - bin size for EPTS bins, default=20
    """

    # Helper function to count matches per EPTS bin (same logic as marginal_xy_plot)
    def get_matches_per_epts_bin(path):
        output = read_output(path, final_epts, final_cpra, donor)
        # Create bins for EPTS, ensuring 0 and 100 are included
        bins = np.arange(0, 101, step) / 100  # Generate bins in percentage form
        bins[-1] = 1.0  # Ensure the last bin edge is exactly 1 (100%)
        output['epts_bin'] = pd.cut(output['epts_pct'], bins, right=False, include_lowest=True)
        # Group by EPTS bins and count matches
        total_matches = output.groupby('epts_bin', observed=False).size()
        return total_matches

    # Get matches per EPTS bin for both datasets
    matches_first = get_matches_per_epts_bin(first_path)
    matches_second = get_matches_per_epts_bin(second_path)

    # print(matches_first)
    # print(matches_second)
    # Calculate the marginal percentage difference: (comparison - reference) / reference * 100
    # Positive values = more transplants in comparison policy, negative = fewer
    difference = (matches_second - matches_first) / matches_first * 100
    # print(difference)

    # Handle division by zero (where the reference policy has no matches in a bin)
    # Replace infinity with NaN, then fill NaN with 0
    difference = difference.replace([np.inf, -np.inf], np.nan).fillna(0)

    # Convert to DataFrame for heatmap plotting (single column DataFrame)
    # Keep original index for proper ordering
    difference_df = difference.to_frame(name=' ')

    # Generate the heatmap for marginal percentage difference
    plt.figure(figsize=(6, 6))
    ax = sns.heatmap(difference_df, annot=difference_df.applymap(lambda x: f'{x:.2f}%'), fmt="", cmap='RdYlGn', center=0, cbar=True)
    
    # Convert EPTS bin labels from decimal (0-1) to percentage (0-100) for display
    # Get the current y-axis tick labels and convert them
    yticklabels = []
    for interval in difference_df.index:
        if hasattr(interval, 'left') and hasattr(interval, 'right'):
            yticklabels.append(f"{int(interval.left * 100)}-{int(interval.right * 100)}")
        else:
            yticklabels.append(str(interval))
    ax.set_yticklabels(yticklabels)
    # plt.title('Marginal Percentage Difference Heatmap')
    plt.xlabel('Percentage Difference')
    plt.ylabel('EPTS')
    if save_plot:
        fname = name or "marginal_difference_heatmap.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def create_policy_table(data_per_policy):
    """
    Create a table juxtaposing multiple policies.
    
    :param data_per_policy: A dictionary where keys are policy names and values are dictionaries 
                            containing 'age', 'race', 'epts', 'ethnicity', 'gender', 'distance', 
                            'blood type', and 'cpra' dictionaries.
    :return: A pandas DataFrame representing the policies in a tabular format.
    """

    # List of keys we are interested in processing
    attributes = list(data_per_policy[list(data_per_policy.keys())[0]].keys())
    category_map = {
        'age': 'Age',
        'race': 'Race',
        'race_Dan': 'Race_Dan',
        'epts': 'EPTS',
        'ethnicity': 'Ethnicity',
        'gender': 'Gender',
        'distance': 'Distance',
        'abo': 'Blood Type',
        'cpra': 'CPRA'
    }
    for kk in attributes:
        if kk not in category_map:
            category_map[kk] = kk
        

    # Create a dictionary to hold each category's DataFrame
    dfs = []

    # Process each attribute and build the DataFrame for it
    for attr in attributes:
        attr_data = {policy_name: policy_data.get(attr, {}) for policy_name, policy_data in data_per_policy.items()}
        
        # Check if any policy has aggregated metrics (mean, min, max structure)
        has_aggregated = False
        for policy_name, data in attr_data.items():
            if isinstance(data, dict) and data:
                # Check if first value is a dict with mean/min/max keys
                first_value = next(iter(data.values())) if data else None
                if isinstance(first_value, dict) and any(k in first_value for k in ['mean', 'min', 'max']):
                    has_aggregated = True
                    break
        
        if has_aggregated:
            # Handle aggregated metrics - expand mean, min, max into separate columns
            expanded_data = {}
            for policy_name, data in attr_data.items():
                if isinstance(data, dict):
                    for subcat, value in data.items():
                        if isinstance(value, dict) and 'mean' in value:
                            # Create columns for mean, min, max
                            expanded_data[f"{policy_name}_mean"] = expanded_data.get(f"{policy_name}_mean", {})
                            expanded_data[f"{policy_name}_min"] = expanded_data.get(f"{policy_name}_min", {})
                            expanded_data[f"{policy_name}_max"] = expanded_data.get(f"{policy_name}_max", {})
                            expanded_data[f"{policy_name}_mean"][subcat] = value['mean']
                            expanded_data[f"{policy_name}_min"][subcat] = value['min']
                            expanded_data[f"{policy_name}_max"][subcat] = value['max']
                        else:
                            # Regular value, add to mean column
                            expanded_data[f"{policy_name}_mean"] = expanded_data.get(f"{policy_name}_mean", {})
                            expanded_data[f"{policy_name}_mean"][subcat] = value
            attr_df = pd.DataFrame(expanded_data).fillna(0)
        else:
            # Regular metrics (no aggregation)
            attr_df = pd.DataFrame(attr_data).fillna(0)
        
        attr_df['Category'] = category_map[attr]
        attr_df['Subcategory'] = attr_df.index
        dfs.append(attr_df)

    # Concatenate all attribute DataFrames
    final_df = pd.concat(dfs)

    # Set multi-index for better readability
    final_df = final_df.set_index(['Category', 'Subcategory'])

    # Add unit to column names for rates
    # We'll assume that all columns are rates (if not, user can adjust as needed)
    final_df.columns = [f"{col}" for col in final_df.columns]

    return final_df

def kdpi_rates_heatmap(path, final_epts, final_cpra, donor, read_output, step = 20, save_plot=False, name=None, policy_name=None):
    """
    Generates a heatmap for % matches by EPTS

    Inputs:
        path - a path to the OASIM output file, string
        candidate - read cleaned_donor_data, pandas dataframe    
        policy_name - optional name of the policy to include in title
    """

    output = read_output(path, final_epts, final_cpra, donor)
    
    # Create bins for KDPI (0-100 scale) and EPTS (0-1 scale, converted from percentage)
    bins = np.arange(0, 101, step)
    # KDPI is already on 0-100 scale
    output['kdpi_bin'] = pd.cut(output['kdpi_at_allocation'], bins, right=False)
    # EPTS is on 0-1 scale, so divide bins by 100
    output['epts_bin'] = pd.cut(output['epts_pct'], bins / 100, right=False)
    
    # Create cross-tabulation: count of matches for each EPTS-KDPI combination
    crosstab = pd.crosstab(output['epts_bin'], output['kdpi_bin'])
    
    # Convert EPTS bin labels from decimal (0-1) to percentage (0-100) for display
    new_epts_labels = []
    for interval in crosstab.index:
        if hasattr(interval, 'left') and hasattr(interval, 'right'):
            new_epts_labels.append(f"[{int(interval.left * 100)}, {int(interval.right * 100)})")
        else:
            new_epts_labels.append(str(interval))
    crosstab.index = new_epts_labels
    
    # Calculate row sums and add as a new column
    # crosstab['Row_Sum'] = crosstab.sum(axis=1)
    # crosstab.loc['Col_Sum'] = crosstab.sum(axis=0)
    
    # Generate the heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(crosstab, annot=True, fmt="d", cmap="YlGnBu", cbar=True)
    # title = 'Heatmap of KDPI vs EPTS'
    # if policy_name:
    #     title = f'Heatmap of KDPI vs EPTS - {policy_name}'
    # plt.title(title)
    plt.xlabel('KDPI')
    plt.ylabel('EPTS')
    if save_plot:
        fname = name or "kdpi_rates_heatmap.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    


def plot_policies(dataframe, save_plot=False, name=None):
    """
    Generate grouped bar plots where the x-axis represents the subcategories 
    and each group of bars represents different policies.
    
    :param dataframe: A pandas DataFrame containing policy data with multi-index (Category, Subcategory).
    """
    
    categories = dataframe.index.get_level_values('Category').unique()

    for category in categories:
        # Get the data for the current category
        df_category = dataframe.loc[category]
        # Use a semi-transparent Spectral palette for consistency with bar plots
        base_palette = sns.color_palette("Spectral", n_colors=len(df_category.columns))
        color_palette = [(r, g, b, 0.8) for r, g, b in base_palette]

        # Plotting grouped bar chart
        ax = df_category.plot(kind='bar', figsize=(12, 5), color=color_palette, width=0.8)
        
        # Set axis labels based on category
        if category == 'Age':
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Age')
        elif category == 'age at listing':
            plt.ylabel('Transplants per patient year')
            plt.xlabel("Age at Listing")
        elif category == 'epts' or category == 'EPTS':
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Recipient EPTS')
        elif category == "epts (bins of 20)":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Recipient EPTS')
        elif category == "epts (bins of 10)":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Recipient EPTS')
        elif category == "Distance":
            plt.ylabel('Median Distance (nm)')
            plt.xlabel('Subcategory')
        elif category == "Race":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Race')
        elif category == "Ethnicity":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Ethnicity')
        elif category == "Gender":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Gender')
        elif category == "Blood Type":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Blood Type')
        elif category == "CPRA":
            plt.ylabel('Transplants per patient year')
            plt.xlabel('CPRA')
        else:
            plt.ylabel('Transplants per patient year')
            plt.xlabel('Subcategory')

        plt.legend(title='Policy', bbox_to_anchor=(1.05, 1), loc='upper left')

        # Annotate each bar with bigger and bolder text
        for container in ax.containers:
            ax.bar_label(container, label_type='center', fmt='%.3f', fontsize=12, color='black', rotation=90)
        
        plt.grid(True, axis='y', alpha=0.3)
        plt.tight_layout()
        if save_plot:
            base = name or "plot_policies"
            fname = f"{base}_{category}.png"
            if not fname.lower().endswith(".png"):
                fname += ".png"
            plt.savefig(fname, bbox_inches="tight", dpi=300)
        plt.show()


def marginal_heatmap(path, final_epts, final_cpra, donor, read_output, step=20, save_plot=False, name=None):
    """
    Generates a heatmap for % matches by EPTS with all KDPI bins summed into a single column.

    Inputs:
        path - a path to the OASIM output file, string
        candidate - read cleaned_donor_data, pandas dataframe    
    """
    
    output = read_output(path, final_epts, final_cpra, donor)
    
    # Create bins for EPTS (0-1 scale)
    bins = np.arange(0, 101, step) / 100  # Generate bins in percentage form (0.0 to 1.0)
    bins[-1] = 1.0  # Ensure the last bin edge is exactly 1.0 (100%)
    output['epts_bin'] = pd.cut(output['epts_pct'], bins, right=False, include_lowest=True)
    
    # Group by EPTS bins and count total number of transplants in each bin
    total_matches = output.groupby('epts_bin', observed=False).size()
    
    # Convert to DataFrame format required for heatmap plotting (single column)
    total_matches_df = total_matches.reset_index(name='Total_Matches').pivot_table(
        index='epts_bin', values='Total_Matches'
    )
    
    # Generate the heatmap
    plt.figure(figsize=(6, 6))
    sns.heatmap(total_matches_df, annot=True, fmt="d", cmap="YlGnBu", cbar=True)
    # plt.title('Heatmap of Total Matches by EPTS')
    plt.xlabel('Total Matches')
    plt.ylabel('EPTS')
    if save_plot:
        fname = name or "marginal_heatmap.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def median_kdpi_comparison_bar_chart(paths, final_epts, final_cpra, name_dict, donor, read_output, step=20, save_plot=False, name=None):
    """
    Generates a grouped bar chart comparing the median KDPI per EPTS bin across multiple datasets.
    The last part of each path is used for dataset labels, colors are based on Spectral palette, 
    and numbers are displayed inside each column.

    Inputs:
        paths - a list of paths to the OASIM output files, list of strings
        final_epts - list or dataframe of final EPTS values
        donor - dataframe containing donor information
        step - step size for EPTS bins, default is 20
    """

    all_medians = []
    dataset_names = []

    # Iterate through each path and compute the median KDPI per EPTS bin
    for path in paths:
        # Extract the dataset name from the path (assuming it's the last part of the file name)
        dataset_name = os.path.basename(path).split('.')[0]
        dataset_name = os.path.basename(path)
        if dataset_name in name_dict.keys():
            dataset_name = name_dict[dataset_name]
        dataset_names.append(dataset_name)


        output = read_output(path, final_epts, final_cpra, donor)

        # Create bins for EPTS (convert from 0-100 to 0-1 scale for pd.cut)
        bins = np.arange(0, 101, step)
        output['epts_bin'] = pd.cut(output['epts_pct'], bins / 100, right=False)

        # Group by EPTS bin and calculate the median KDPI for transplants in each bin
        median_kdpi = output.groupby('epts_bin', observed=False)['kdpi_at_allocation'].median()

        # Store the result in a DataFrame for easier merging later
        median_kdpi_df = pd.DataFrame(median_kdpi).rename(columns={'kdpi_at_allocation': dataset_name})
        all_medians.append(median_kdpi_df)

    # Merge all median KDPI DataFrames on the EPTS bins
    comparison_df = pd.concat(all_medians, axis=1)

    # Plotting the grouped bar chart
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Use a semi-transparent Spectral palette for consistency with bar plots
    base_palette = sns.color_palette("Spectral", n_colors=len(dataset_names))
    color_palette = [(r, g, b, 0.8) for r, g, b in base_palette]

    comparison_df.plot(kind='bar', ax=ax, width=0.8, color=color_palette)

    # Add numbers inside each column
    for container in ax.containers:
        ax.bar_label(container, label_type='center', fmt='%d', fontsize=12, rotation=90)

    # Customize the chart
    # plt.title('Comparison of Median KDPI per EPTS')
    plt.xlabel('Recipient EPTS')
    plt.ylabel('Median KDPI')
    
    # Convert x-axis labels from decimal (0.0-1.0) to percentage (0-100)
    # The index contains Interval objects, convert them to percentage format
    new_labels = []
    for interval in comparison_df.index:
        if hasattr(interval, 'left') and hasattr(interval, 'right'):
            new_labels.append(f"{int(interval.left * 100)}-{int(interval.right * 100)}")
        else:
            # Fallback for non-interval indices
            new_labels.append(str(interval))
    ax.set_xticklabels(new_labels)
    plt.xticks(rotation=45)
    plt.legend(title='Dataset', labels=dataset_names, bbox_to_anchor=(1.05, 1), loc='upper left')

    # Show the plot
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    if save_plot:
        fname = name or "median_kdpi_comparison_bar_chart.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()

def age_listing_matching_heatmap(path, person_times, final_epts, final_cpra, donor, read_output, step=10, save_plot=False, name=None):
    """
    Generates a heatmap showing the number of matches between candidate age at listing 
    and donor age.

    Inputs:
        path        - path to the OASIM output file, string
        final_epts  - parameter for read_output
        final_cpra  - parameter for read_output
        donor       - donor DataFrame
        read_output - function that loads and merges OASIM output data
        step        - bin size for age bins (in years), default = 10
    """

    # Read output data
    output = read_output(path, final_epts, final_cpra, donor)
    output = output.merge(person_times[['cand_id', 'can_age_at_listing']], on='cand_id', how='left')

    # Validate necessary columns
    required_cols = ['can_age_at_listing', 'don_age']
    for col in required_cols:
        if col not in output.columns:
            raise ValueError(f"Missing required column '{col}' in the output DataFrame.")

    # Define bins for candidate and donor ages
    bins = np.arange(0, 91, step)
    output['cand_age_bin'] = pd.cut(output['can_age_at_listing'], bins, right=False)
    output['donor_age_bin'] = pd.cut(output['don_age'], bins, right=False)

    # Create crosstab of counts (number of matches per age pair)
    crosstab = pd.crosstab(output['cand_age_bin'], output['donor_age_bin'])

    # Generate the heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(
        crosstab,
        annot=True,
        fmt="d",
        cmap="YlGnBu",
        cbar=True,
        annot_kws={'size': 12}
    )
    # plt.title('Heatmap of Matches: Candidate Age at Listing vs Donor Age')
    plt.xlabel('Donor Age')
    plt.ylabel('Candidate Age at Listing')
    plt.tight_layout()
    if save_plot:
        fname = name or "age_listing_matching_heatmap.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def age_difference_percentage_plot(path, person_times, final_epts, final_cpra, donor, read_output, step=5, save_plot=False, name=None, policy_name=None):
    """
    Generates a bar plot showing the distribution of matches 
    by absolute age difference between donor and candidate (at listing).
    
    Inputs:
        policy_name - optional name of the policy to include in title
    """

    # Read and merge data
    output = read_output(path, final_epts, final_cpra, donor)
    output = output.merge(person_times[['cand_id', 'can_age_at_listing']], on='cand_id', how='left')

    # Validate required columns
    required_cols = ['can_age_at_listing', 'don_age']
    for col in required_cols:
        if col not in output.columns:
            raise ValueError(f"Missing required column '{col}' in the output DataFrame.")

    # Compute age difference: positive = donor older, negative = donor younger
    output['age_diff'] = output['don_age']  - output['can_age_at_listing'] 
    # Note: Using signed difference (not absolute) to show direction of age difference

    # Bin by age difference (range: -50 to +50 years)
    bins = np.arange(-50, 51, step)  # Default step=5 creates bins of 5 years
    output['age_diff_bin'] = pd.cut(output['age_diff'], bins, right=False, include_lowest=True)

    # Count number of transplants in each age difference bin
    diff_counts = output['age_diff_bin'].value_counts().sort_index()

    # Convert counts to percentages of total transplants
    total_matches = diff_counts.sum()
    diff_percent = (diff_counts / total_matches * 100).round(2)

    # Convert to DataFrame for plotting
    diff_df = diff_percent.reset_index()
    diff_df.columns = ['Age Difference Bin', 'Percentage of Matches']

    # Plot the distribution (future-proof for Seaborn >= 0.14)
    plt.figure(figsize=(10, 5))
    ax = sns.barplot(
        x='Age Difference Bin',
        y='Percentage of Matches',
        hue='Age Difference Bin',
        data=diff_df,
        palette='Spectral',
        legend=False
    )

    # Annotate each bar with vertical text inside bars, only if they fit
    for container in ax.containers:
        # Get the maximum bar height to determine threshold
        max_height = max([rect.get_height() for rect in container])
        threshold = max_height * 0.05  # Only label bars that are at least 5% of max height
        
        # Only add labels to bars that are tall enough to fit the text
        labels = []
        for rect in container:
            height = rect.get_height()
            if height >= threshold:
                labels.append(f"{height:.1f}%")
            else:
                labels.append("")
        
        ax.bar_label(
            container,
            labels=labels,
            label_type='center',
            fontsize=10,
            color='black',
            rotation=90
        )

    # Finalize plot
    # title = 'Distribution of Matches by Age Difference (Donor - Candidate)'
    # if policy_name:
    #     title = f'Distribution of Matches by Age Difference (Donor - Candidate) - {policy_name}'
    # plt.title(title)
    plt.xlabel('Age Difference (Years)')
    plt.ylabel('% of transplants')
    plt.xticks(rotation=45)
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    if save_plot:
        fname = name or "age_difference_percentage_plot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def age_difference_xy_plot(path_person_times_list, final_epts, final_cpra, donor, name_dict, read_output, step=5, save_plot=False, name=None):
    """
    Generates a grouped bar plot showing the distribution of matches by age difference
    for multiple policies.

    Inputs:
        path_person_times_list - list of tuples (path, person_times DataFrame)
        step - bin size for age difference bins, default=5
    """
    # Bin by age difference
    bins = np.arange(-50, 51, step)
    bin_labels = [f"{int(bins[i])}-{int(bins[i+1])}" for i in range(len(bins)-1)]
    
    # Prepare data for grouped bar chart
    all_data = {}
    
    for path, person_times in path_person_times_list:
        # Read and merge data
        output = read_output(path, final_epts, final_cpra, donor)
        output = output.merge(person_times[['cand_id', 'can_age_at_listing']], on='cand_id', how='left')

        # Validate required columns
        required_cols = ['can_age_at_listing', 'don_age']
        for col in required_cols:
            if col not in output.columns:
                raise ValueError(f"Missing required column '{col}' in the output DataFrame.")

        # Compute age difference: positive = donor older, negative = donor younger
        output['age_diff'] = output['don_age'] - output['can_age_at_listing']
        output['age_diff_bin'] = pd.cut(output['age_diff'], bins, right=False, include_lowest=True)

        # Count number of transplants in each age difference bin
        diff_counts = output['age_diff_bin'].value_counts().sort_index()

        # Convert counts to percentages of total transplants
        total_matches = diff_counts.sum()
        diff_percent = (diff_counts / total_matches * 100).round(2)

        # Extract dataset name from the file path
        dataset_name = os.path.basename(path)
        if dataset_name in name_dict.keys():
            dataset_name = name_dict[dataset_name]
        
        # Align with bin_labels - match intervals from diff_percent
        y = []
        for i in range(len(bins)-1):
            bin_interval = pd.Interval(bins[i], bins[i+1], closed='left')
            # Check if this interval exists in diff_percent
            if bin_interval in diff_percent.index:
                y.append(diff_percent[bin_interval])
            else:
                y.append(0.0)
        
        all_data[dataset_name] = y

    # Create DataFrame for plotting
    df = pd.DataFrame(all_data, index=bin_labels)
    
    # Use a semi-transparent Spectral palette for consistency with bar plots
    base_palette = sns.color_palette("Spectral", n_colors=len(df.columns))
    color_palette = [(r, g, b, 0.8) for r, g, b in base_palette]
    
    # Plot grouped bar chart
    ax = df.plot(kind='bar', figsize=(12, 6), width=0.8, color=color_palette)
    
    # Add numbers inside bars with vertical text, only if they fit
    for container in ax.containers:
        # Get the maximum bar height to determine threshold
        max_height = max([rect.get_height() for rect in container])
        threshold = max_height * 0.05  # Only label bars that are at least 5% of max height
        
        # Only add labels to bars that are tall enough to fit the text
        labels = []
        for rect in container:
            height = rect.get_height()
            if height >= threshold:
                labels.append(f"{height:.1f}%")
            else:
                labels.append("")
        
        ax.bar_label(
            container,
            labels=labels,
            label_type='center',
            fontsize=10,
            color='black',
            rotation=90
        )
    
    # Finalize the plot
    # plt.title('Distribution of Matches by Age Difference (Donor - Candidate)')
    plt.xlabel('Donor Younger than Candidate (Years) <------      Age Difference (Years)      ------> Donor Older than Candidate (Years)')
    plt.ylabel('Percentage of Matches (%)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    if save_plot:
        fname = name or "age_difference_xy_plot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def offer_analysis_plot(paths, name_dict, read_output, *, step=10, cutoff=float("inf"), save_plot=False, name=None):
    """
    Analyse the rank (number of offers before acceptance) across policies.

    Produces three panels:
      1. Histogram of rank distributions per policy.
      2. CDF overlay so you can read off "X% of transplants happen within N offers".
      3. A printed summary table with mean, median, and key percentiles.

    Parameters
    ----------
    paths : list[str]
        Paths to OASIM output files (one per policy).
    name_dict : dict
        Maps path (or basename) → friendly display name.
    read_output : callable
        ``read_output_default`` — returns a filtered DataFrame with a ``rank`` column.
    step : int
        Bin width for the rank histogram (default 10).
    cutoff : int | float
        Ignore transplants where rank exceeds this value (default inf — keep all).
    save_plot : bool
        Whether to persist the figure to disk.
    name : str | None
        Filename when *save_plot* is True.
    """
    apply_plot_style()
    policy_ranks = {}
    for path in paths:
        output = read_output(path)
        if "rank" not in output.columns:
            raise ValueError(f"Output file {path} does not contain a 'rank' column.")
        ranks = output["rank"].dropna().astype(int)
        ranks = ranks[ranks <= cutoff]
        label = os.path.basename(path)
        if label in name_dict:
            label = name_dict[label]
        elif path in name_dict:
            label = name_dict[path]
        policy_ranks[label] = ranks

    color_palette = spectral_colors(len(policy_ranks))

    # --- Summary table (printed) ---
    summary_rows = []
    for label, ranks in policy_ranks.items():
        summary_rows.append({
            "Policy": label,
            "Mean": round(ranks.mean(), 2),
            "Median": round(ranks.median(), 2),
            "Std": round(ranks.std(), 2),
            "Min": int(ranks.min()),
            "Max": int(ranks.max()),
            "P25": round(ranks.quantile(0.25), 2),
            "P75": round(ranks.quantile(0.75), 2),
            "P90": round(ranks.quantile(0.90), 2),
            "P95": round(ranks.quantile(0.95), 2),
        })
    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))

    # --- Figure with 2 panels ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6), facecolor="white")

    # Panel 1: Histogram
    max_rank = max(r.max() for r in policy_ranks.values())
    bins = np.arange(0, max_rank + step + 1, step)

    for (label, ranks), color in zip(policy_ranks.items(), color_palette):
        ax1.hist(ranks, bins=bins, alpha=0.6, label=label, color=color, edgecolor="black", linewidth=0.5)

    ax1.set_xlabel("Rank (# offers before acceptance)")
    ax1.set_ylabel("Number of Transplants")
    ax1.legend()
    ax1.grid(True, axis="y", alpha=0.3)

    # Panel 2: CDF overlay
    for (label, ranks), color in zip(policy_ranks.items(), color_palette):
        sorted_ranks = np.sort(ranks)
        cdf = np.arange(1, len(sorted_ranks) + 1) / len(sorted_ranks)
        ax2.plot(sorted_ranks, cdf, label=label, color=spectral_rgba_rgb(color), linewidth=2)

    ax2.set_xlabel("Rank (# offers before acceptance)")
    ax2.set_ylabel("Cumulative Proportion of Transplants")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_plot:
        fname = name or "offer_analysis.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()

    return summary_df


def plot_offers_per_kidney_distribution(
    counts: pd.Series,
    *,
    title: str = "",
    save_plot: bool = False,
    name: str | None = None,
) -> None:
    """
    Histogram and empirical CDF of *offers per kidney* (one value per kidney).

    Parameters
    ----------
    counts : Series
        Index = kidney key(s), values = number of offers for that kidney.
    """
    if len(counts) == 0:
        logger.warning("plot_offers_per_kidney_distribution: empty counts")
        return
    apply_plot_style()
    c_fill, c_line = spectral_colors(2)
    v = counts.values.astype(float)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor="white")
    max_v = max(int(v.max()), 1)
    bins = np.arange(0.5, max_v + 1.5, 1.0)
    ax1.hist(
        v,
        bins=bins,
        edgecolor="black",
        alpha=0.85,
        color=spectral_rgba_rgb(c_fill),
    )
    ax1.set_xlabel("Number of offers per kidney")
    ax1.set_ylabel("Number of kidneys")
    ax1.grid(True, axis="y", alpha=0.3)
    if title:
        ax1.set_title(title)

    sv = np.sort(v)
    cdf = np.arange(1, len(sv) + 1) / len(sv)
    ax2.plot(sv, cdf, color=spectral_rgba_rgb(c_line), linewidth=2)
    ax2.set_xlabel("Offers per kidney")
    ax2.set_ylabel("Cumulative proportion of kidneys")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_plot:
        fname = name or "offers_per_kidney_distribution.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()


def _suppress_box_whiskers(cat_kwargs: dict, kind: str) -> None:
    """For ``kind="box"`` catplots, hide whiskers, caps, and outlier fliers.

    Leaves just the IQR box and the median line.
    """
    if kind == "box":
        cat_kwargs["whis"] = 0
        cat_kwargs["showcaps"] = False
        cat_kwargs["showfliers"] = False


def offers_epts_kdpi_catplot(
    enriched_frames: List[Tuple[str, pd.DataFrame]],
    *,
    accepted_only: bool = True,
    epts_step: float = 0.1,
    kind: str = "box",
    save_plot: bool = False,
    name: str | None = None,
):
    """
    Catplot: KDPI vs binned EPTS for accepted (or all) offer rows.

    Parameters
    ----------
    enriched_frames : list[tuple[str, pandas.DataFrame]]
        Each (policy_label, df) must include columns ``epts_pct``, ``kdpi_at_allocation``,
        and ``accepted``.
    """
    apply_plot_style()
    parts = []
    for label, df in enriched_frames:
        d = df.copy()
        d["policy"] = label
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)
    n_raw = len(all_df)

    if accepted_only:
        if "accepted" not in all_df.columns:
            raise ValueError("enriched DataFrame must include 'accepted' when accepted_only=True")
        acc = all_df["accepted"]
        if acc.dtype != bool:
            acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
        all_df = all_df[acc]
    n_after_accept = len(all_df)

    all_df["epts_pct"] = pd.to_numeric(all_df["epts_pct"], errors="coerce")
    all_df["kdpi_at_allocation"] = pd.to_numeric(all_df["kdpi_at_allocation"], errors="coerce")

    nan_epts = int(all_df["epts_pct"].isna().sum())
    nan_kdpi = int(all_df["kdpi_at_allocation"].isna().sum())

    all_df = all_df.dropna(subset=["epts_pct", "kdpi_at_allocation"])
    if len(all_df) == 0:
        logger.warning(
            "offers_epts_kdpi_catplot: no rows after filtering — "
            "raw=%s, after accepted filter=%s, NaN epts_pct=%s, NaN kdpi=%s. "
            "Check cand_id/don_id alignment with load_core_data and see enriched_offers() warnings.",
            n_raw,
            n_after_accept,
            nan_epts,
            nan_kdpi,
        )
        return None

    edges = np.arange(0.0, 1.0 + epts_step, epts_step)
    all_df["epts_bin"] = pd.cut(
        all_df["epts_pct"],
        bins=edges,
        include_lowest=True,
        right=True,
    )
    all_df["epts_bin_str"] = all_df["epts_bin"].apply(
        lambda x: f"{max(x.left, 0.0) * 100:.0f}-{x.right * 100:.0f}" if pd.notna(x) else ""
    )

    n_pol = all_df["policy"].nunique()
    pal = [spectral_rgba_rgb(c) for c in spectral_colors(max(n_pol, 1))]

    cat_kwargs: dict = {
        "data": all_df,
        "x": "epts_bin_str",
        "y": "kdpi_at_allocation",
        "kind": kind,
        "height": 6,
        "aspect": max(1.5, min(2.5, 0.2 * all_df["epts_bin_str"].nunique())),
    }
    if n_pol > 1:
        cat_kwargs["hue"] = "policy"
        cat_kwargs["palette"] = pal
        cat_kwargs["legend_out"] = True
    else:
        cat_kwargs["color"] = pal[0]
    _suppress_box_whiskers(cat_kwargs, kind)
    g = sns.catplot(**cat_kwargs)
    g.set_axis_labels("Recipient EPTS percentile", "Donor KDPI at allocation")
    g.set_xticklabels(rotation=45, ha="right")
    if n_pol > 1 and g._legend is not None:
        g._legend.set_title("Policy")
    if n_pol > 1:
        g.fig.subplots_adjust(right=0.72)
    else:
        g.fig.tight_layout()
    if save_plot:
        fname = name or "offers_epts_kdpi_catplot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    return g


def offers_epts_age_catplot(
    enriched_frames: List[Tuple[str, pd.DataFrame]],
    *,
    age_column: str = "real_age",
    accepted_only: bool = True,
    epts_step: float = 0.1,
    kind: str = "box",
    save_plot: bool = False,
    name: str | None = None,
):
    """
    **EPTS bins (x) vs age (y)** — same x-axis as the KDPI catplot.

    For **candidate age vs donor age** (joint distribution of offers), use
    :func:`offers_candidate_donor_age_plot` instead.

    Parameters
    ----------
    age_column
        One of ``real_age``, ``can_age_at_listing``, ``don_age`` (must exist on enriched frames).
    """
    allowed = {"real_age", "can_age_at_listing", "don_age"}
    if age_column not in allowed:
        raise ValueError(f"age_column must be one of {allowed}, got {age_column!r}")

    y_labels = {
        "real_age": "Recipient age — real_age (years)",
        "can_age_at_listing": "Recipient age at listing (years)",
        "don_age": "Donor age (years)",
    }
    y_label = y_labels[age_column]

    apply_plot_style()
    parts = []
    for label, df in enriched_frames:
        d = df.copy()
        d["policy"] = label
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)
    n_raw = len(all_df)

    if accepted_only:
        if "accepted" not in all_df.columns:
            raise ValueError("enriched DataFrame must include 'accepted' when accepted_only=True")
        acc = all_df["accepted"]
        if acc.dtype != bool:
            acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
        all_df = all_df[acc]
    n_after_accept = len(all_df)

    if age_column not in all_df.columns:
        raise ValueError(
            f"enriched DataFrame has no column {age_column!r}; run enriched_offers() after load_core_data "
            f"(don_age requires don_age on donor file; real_age/can_age_at_listing require static)."
        )

    all_df["epts_pct"] = pd.to_numeric(all_df["epts_pct"], errors="coerce")
    all_df[age_column] = pd.to_numeric(all_df[age_column], errors="coerce")

    nan_epts = int(all_df["epts_pct"].isna().sum())
    nan_age = int(all_df[age_column].isna().sum())

    all_df = all_df.dropna(subset=["epts_pct", age_column])
    if len(all_df) == 0:
        logger.warning(
            "offers_epts_age_catplot: no rows after filtering — "
            "raw=%s, after accepted=%s, NaN epts_pct=%s, NaN %s=%s.",
            n_raw,
            n_after_accept,
            nan_epts,
            age_column,
            nan_age,
        )
        return None

    edges = np.arange(0.0, 1.0 + epts_step, epts_step)
    all_df["epts_bin"] = pd.cut(
        all_df["epts_pct"],
        bins=edges,
        include_lowest=True,
        right=True,
    )
    all_df["epts_bin_str"] = all_df["epts_bin"].apply(
        lambda x: f"{max(x.left, 0.0) * 100:.0f}-{x.right * 100:.0f}" if pd.notna(x) else ""
    )

    n_pol = all_df["policy"].nunique()
    pal = [spectral_rgba_rgb(c) for c in spectral_colors(max(n_pol, 1))]

    cat_kwargs: dict = {
        "data": all_df,
        "x": "epts_bin_str",
        "y": age_column,
        "kind": kind,
        "height": 6,
        "aspect": max(1.5, min(2.5, 0.2 * all_df["epts_bin_str"].nunique())),
    }
    if n_pol > 1:
        cat_kwargs["hue"] = "policy"
        cat_kwargs["palette"] = pal
        cat_kwargs["legend_out"] = True
    else:
        cat_kwargs["color"] = pal[0]
    _suppress_box_whiskers(cat_kwargs, kind)
    g = sns.catplot(**cat_kwargs)
    g.set_axis_labels("Recipient EPTS percentile", y_label)
    g.set_xticklabels(rotation=45, ha="right")
    if n_pol > 1 and g._legend is not None:
        g._legend.set_title("Policy")
    if n_pol > 1:
        g.fig.subplots_adjust(right=0.72)
    else:
        g.fig.tight_layout()
    if save_plot:
        fname = name or f"offers_epts_age_catplot_{age_column}.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    return g


def offers_candidate_donor_age_catplot(
    enriched_frames: List[Tuple[str, pd.DataFrame]],
    *,
    candidate_age_col: str = "real_age",
    accepted_only: bool = True,
    age_bin_years: float = 5.0,
    kind: str = "box",
    save_plot: bool = False,
    name: str | None = None,
):
    """
    **Donor age** (y) vs **binned candidate age** (x) via ``sns.catplot`` — same layout as
    ``offers_epts_kdpi_catplot`` / ``offers_kdpi_by_race_catplot``.

    For a **scatter** of raw candidate age vs donor age, use :func:`offers_candidate_donor_age_plot`.
    """
    allowed = {"real_age", "can_age_at_listing"}
    if candidate_age_col not in allowed:
        raise ValueError(f"candidate_age_col must be one of {allowed}, got {candidate_age_col!r}")
    if age_bin_years <= 0:
        raise ValueError("age_bin_years must be positive")

    x_labels = {
        "real_age": "Candidate age at simulation start (years)",
        "can_age_at_listing": "Candidate age at listing (years)",
    }

    apply_plot_style()
    parts = []
    for label, df in enriched_frames:
        d = df.copy()
        d["policy"] = label
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)
    n_raw = len(all_df)

    if accepted_only:
        if "accepted" not in all_df.columns:
            raise ValueError("enriched DataFrame must include 'accepted' when accepted_only=True")
        acc = all_df["accepted"]
        if acc.dtype != bool:
            acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
        all_df = all_df[acc]

    if candidate_age_col not in all_df.columns or "don_age" not in all_df.columns:
        raise ValueError(
            "Need candidate age column and don_age on enriched rows; run enriched_offers() after load_core_data."
        )

    all_df[candidate_age_col] = pd.to_numeric(all_df[candidate_age_col], errors="coerce")
    all_df["don_age"] = pd.to_numeric(all_df["don_age"], errors="coerce")
    all_df = all_df.dropna(subset=[candidate_age_col, "don_age"])
    if len(all_df) == 0:
        logger.warning("offers_candidate_donor_age_catplot: no rows after filtering (raw=%s)", n_raw)
        return None

    amin = float(all_df[candidate_age_col].min())
    amax = float(all_df[candidate_age_col].max())
    lo = np.floor(amin / age_bin_years) * age_bin_years
    hi = np.ceil(amax / age_bin_years) * age_bin_years
    if hi <= lo:
        hi = lo + age_bin_years
    edges = np.arange(lo, hi + age_bin_years, age_bin_years)
    if len(edges) < 2:
        edges = np.array([lo, lo + age_bin_years])

    all_df["cand_age_bin"] = pd.cut(
        all_df[candidate_age_col],
        bins=edges,
        right=False,
        include_lowest=True,
    )
    all_df["cand_age_bin_str"] = all_df["cand_age_bin"].apply(
        lambda x: f"{int(x.left)}-{int(x.right)}" if pd.notna(x) else ""
    )
    all_df = all_df[all_df["cand_age_bin_str"] != ""]
    if len(all_df) == 0:
        logger.warning("offers_candidate_donor_age_catplot: no rows after binning (raw=%s)", n_raw)
        return None

    def _bin_left(s: str) -> int:
        return int(s.split("-", 1)[0])

    bin_order = sorted(all_df["cand_age_bin_str"].unique(), key=_bin_left)
    n_pol = all_df["policy"].nunique()
    pal = [spectral_rgba_rgb(c) for c in spectral_colors(max(n_pol, 1))]

    cat_kwargs: dict = {
        "data": all_df,
        "x": "cand_age_bin_str",
        "y": "don_age",
        "kind": kind,
        "height": 6,
        "aspect": max(1.5, min(2.8, 0.18 * len(bin_order))),
        "order": bin_order,
    }
    if n_pol > 1:
        cat_kwargs["hue"] = "policy"
        cat_kwargs["palette"] = pal
        cat_kwargs["legend_out"] = True
    else:
        cat_kwargs["color"] = pal[0]
    _suppress_box_whiskers(cat_kwargs, kind)
    g = sns.catplot(**cat_kwargs)
    g.set_axis_labels(x_labels[candidate_age_col], "Donor age (years)")
    g.set_xticklabels(rotation=45, ha="right")
    if n_pol > 1 and g._legend is not None:
        g._legend.set_title("Policy")
    if n_pol > 1:
        g.fig.subplots_adjust(right=0.72)
    else:
        g.fig.tight_layout()
    if save_plot:
        fname = name or "offers_candidate_donor_age_catplot.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    return g


def offers_candidate_donor_age_plot(
    enriched_frames: List[Tuple[str, pd.DataFrame]],
    *,
    candidate_age_col: str = "real_age",
    accepted_only: bool = True,
    max_points: int = 80_000,
    alpha: float = 0.14,
    s: float = 10,
    show_diagonal: bool = True,
    save_plot: bool = False,
    name: str | None = None,
):
    """
    Scatter: **candidate (recipient) age** vs **donor age** for each offer row.

    This is *not* EPTS-stratified — it is the joint distribution of who is offered which
    donor kidneys in terms of ages. Large tables are downsampled for plotting (stratified
    by policy when multiple policies are compared).
    """
    allowed = {"real_age", "can_age_at_listing"}
    if candidate_age_col not in allowed:
        raise ValueError(f"candidate_age_col must be one of {allowed}, got {candidate_age_col!r}")

    x_labels = {
        "real_age": "Candidate age at simulation start (years)",
        "can_age_at_listing": "Candidate age at listing (years)",
    }

    apply_plot_style()
    parts = []
    for label, df in enriched_frames:
        d = df.copy()
        d["policy"] = label
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)

    if accepted_only:
        if "accepted" not in all_df.columns:
            raise ValueError("enriched DataFrame must include 'accepted' when accepted_only=True")
        acc = all_df["accepted"]
        if acc.dtype != bool:
            acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
        all_df = all_df[acc]

    if candidate_age_col not in all_df.columns or "don_age" not in all_df.columns:
        raise ValueError(
            "Need candidate age column and don_age on enriched rows; run enriched_offers() after load_core_data."
        )

    all_df[candidate_age_col] = pd.to_numeric(all_df[candidate_age_col], errors="coerce")
    all_df["don_age"] = pd.to_numeric(all_df["don_age"], errors="coerce")
    all_df = all_df.dropna(subset=[candidate_age_col, "don_age"])
    if len(all_df) == 0:
        logger.warning("offers_candidate_donor_age_plot: no rows after filtering")
        return None

    n_pol = all_df["policy"].nunique()
    if len(all_df) > max_points:
        per = max(1, max_points // max(n_pol, 1))

        def _sample(g: pd.DataFrame) -> pd.DataFrame:
            return g if len(g) <= per else g.sample(n=per, random_state=42)

        plot_df = all_df.groupby("policy", group_keys=False).apply(_sample)
        logger.info(
            "offers_candidate_donor_age_plot: plotting %s of %s rows (max_points=%s, per policy ≈ %s)",
            len(plot_df),
            len(all_df),
            max_points,
            per,
        )
    else:
        plot_df = all_df

    pal = spectral_colors(max(n_pol, 1))
    pal_rgb = [spectral_rgba_rgb(c) for c in pal]

    fig, ax = plt.subplots(figsize=(11, 8), facecolor="white")
    if show_diagonal:
        lo = float(min(plot_df[candidate_age_col].min(), plot_df["don_age"].min()))
        hi = float(max(plot_df[candidate_age_col].max(), plot_df["don_age"].max()))
        pad = 2.0
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "k--", alpha=0.25, linewidth=1, zorder=0)

    if n_pol > 1:
        for i, pol in enumerate(plot_df["policy"].unique()):
            sub = plot_df[plot_df["policy"] == pol]
            c = pal_rgb[i % len(pal_rgb)]
            ax.scatter(
                sub[candidate_age_col],
                sub["don_age"],
                s=s,
                alpha=alpha,
                color=c,
                label=pol,
                linewidths=0,
                rasterized=True,
                zorder=2,
            )
        leg = ax.legend(title="Policy", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True)
        leg.get_frame().set_alpha(0.95)
    else:
        ax.scatter(
            plot_df[candidate_age_col],
            plot_df["don_age"],
            s=s,
            alpha=min(0.25, alpha * 1.5),
            color=spectral_rgba_rgb(pal[0]),
            linewidths=0,
            rasterized=True,
            zorder=2,
        )

    ax.set_xlabel(x_labels[candidate_age_col])
    ax.set_ylabel("Donor age (years)")
    ax.grid(True, alpha=0.3)
    fig.subplots_adjust(right=0.78 if n_pol > 1 else 0.95)
    if save_plot:
        fname = name or "offers_candidate_vs_donor_age.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    return fig, ax


def offers_kdpi_by_race_catplot(
    enriched_frames: List[Tuple[str, pd.DataFrame]],
    *,
    accepted_only: bool = True,
    kind: str = "box",
    save_plot: bool = False,
    name: str | None = None,
):
    """
    **Donor KDPI** of offered kidneys by **recipient SRTR race** (``can_race_srtr``).

    Requires race columns on enriched frames from ``load_core_data(..., race_path=...)``.
    """
    apply_plot_style()
    parts = []
    for label, df in enriched_frames:
        d = df.copy()
        d["policy"] = label
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)
    n_raw = len(all_df)

    if accepted_only:
        if "accepted" not in all_df.columns:
            raise ValueError("enriched DataFrame must include 'accepted' when accepted_only=True")
        acc = all_df["accepted"]
        if acc.dtype != bool:
            acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
        all_df = all_df[acc]

    if "can_race_srtr" not in all_df.columns:
        raise ValueError(
            "Need can_race_srtr on enriched offers; use load_core_data(..., race_path=...) so race is merged."
        )

    all_df["can_race_srtr"] = all_df["can_race_srtr"].fillna("Unknown").astype(str)
    all_df["kdpi_at_allocation"] = pd.to_numeric(all_df["kdpi_at_allocation"], errors="coerce")
    all_df = all_df.dropna(subset=["kdpi_at_allocation"])
    if len(all_df) == 0:
        logger.warning(
            "offers_kdpi_by_race_catplot: no rows after filtering (raw=%s)",
            n_raw,
        )
        return None

    race_order = sorted(all_df["can_race_srtr"].unique())
    n_pol = all_df["policy"].nunique()
    pal = [spectral_rgba_rgb(c) for c in spectral_colors(max(n_pol, 1))]

    cat_kwargs: dict = {
        "data": all_df,
        "x": "can_race_srtr",
        "y": "kdpi_at_allocation",
        "kind": kind,
        "height": 6,
        "aspect": max(1.8, min(3.2, 0.22 * len(race_order))),
        "order": race_order,
    }
    if n_pol > 1:
        cat_kwargs["hue"] = "policy"
        cat_kwargs["palette"] = pal
        cat_kwargs["legend_out"] = True
    else:
        cat_kwargs["color"] = pal[0]
    _suppress_box_whiskers(cat_kwargs, kind)
    g = sns.catplot(**cat_kwargs)
    g.set_axis_labels("Recipient race (SRTR)", "Donor KDPI (offered kidney)")
    g.set_xticklabels(rotation=45, ha="right")
    if n_pol > 1 and g._legend is not None:
        g._legend.set_title("Policy")
    if n_pol > 1:
        g.fig.subplots_adjust(right=0.72)
    else:
        g.fig.tight_layout()
    if save_plot:
        fname = name or "offers_kdpi_by_race.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    return g


def offers_kdpi_by_wait_catplot(
    enriched_frames: List[Tuple[str, pd.DataFrame]],
    *,
    wait_edges_years: Optional[List[float]] = None,
    accepted_only: bool = True,
    kind: str = "box",
    save_plot: bool = False,
    name: str | None = None,
):
    """
    **Donor KDPI** of offered kidneys by **years waited at this offer** (``offer_wait_years``).

    Each row is one offer; the same candidate can appear in multiple bins. Requires
    ``offer_wait_years`` on enriched frames (from offers file columns and/or
    ``offer_datetime`` − ``can_listing_dt``).
    """
    apply_plot_style()
    edges = (
        list(wait_edges_years)
        if wait_edges_years is not None
        else [0.0, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, float("inf")]
    )
    if len(edges) < 2:
        raise ValueError("wait_edges_years must have at least two values")
    if edges[-1] != float("inf"):
        edges = edges + [float("inf")]

    reps = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if np.isinf(hi):
            reps.append(lo + 1.0)
        else:
            reps.append((lo + hi) / 2)
    bin_order = list(
        pd.cut(
            pd.Series(reps, dtype=float),
            bins=edges,
            right=False,
            include_lowest=True,
        ).cat.categories
    )

    parts = []
    for label, df in enriched_frames:
        d = df.copy()
        d["policy"] = label
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)
    n_raw = len(all_df)

    if accepted_only:
        if "accepted" not in all_df.columns:
            raise ValueError("enriched DataFrame must include 'accepted' when accepted_only=True")
        acc = all_df["accepted"]
        if acc.dtype != bool:
            acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
        all_df = all_df[acc]

    if "offer_wait_years" not in all_df.columns:
        raise ValueError(
            "Need offer_wait_years on enriched offers: add wait_time_years / offer_datetime "
            "to the offers file, or ensure can_listing_dt + offer_datetime merge in enriched_offers."
        )

    all_df["kdpi_at_allocation"] = pd.to_numeric(all_df["kdpi_at_allocation"], errors="coerce")
    all_df["offer_wait_years"] = pd.to_numeric(all_df["offer_wait_years"], errors="coerce")
    all_df = all_df.dropna(subset=["kdpi_at_allocation", "offer_wait_years"])
    all_df["wait_bin"] = pd.cut(
        all_df["offer_wait_years"], bins=edges, right=False, include_lowest=True
    )
    all_df = all_df.dropna(subset=["wait_bin"])
    if len(all_df) == 0:
        logger.warning(
            "offers_kdpi_by_wait_catplot: no rows after filtering (raw=%s)",
            n_raw,
        )
        return None

    n_pol = all_df["policy"].nunique()
    pal = [spectral_rgba_rgb(c) for c in spectral_colors(max(n_pol, 1))]

    cat_kwargs: dict = {
        "data": all_df,
        "x": "wait_bin",
        "y": "kdpi_at_allocation",
        "kind": kind,
        "height": 6,
        "aspect": max(1.8, min(3.2, 0.2 * len(bin_order))),
        "order": bin_order,
    }
    if n_pol > 1:
        cat_kwargs["hue"] = "policy"
        cat_kwargs["palette"] = pal
        cat_kwargs["legend_out"] = True
    else:
        cat_kwargs["color"] = pal[0]
    _suppress_box_whiskers(cat_kwargs, kind)
    g = sns.catplot(**cat_kwargs)
    g.set_axis_labels("Years waited at offer (bin)", "Donor KDPI (offered kidney)")
    g.set_xticklabels(rotation=45, ha="right")
    if n_pol > 1 and g._legend is not None:
        g._legend.set_title("Policy")
    if n_pol > 1:
        g.fig.subplots_adjust(right=0.72)
    else:
        g.fig.tight_layout()
    if save_plot:
        fname = name or "offers_kdpi_by_wait.png"
        if not fname.lower().endswith(".png"):
            fname += ".png"
        plt.savefig(fname, bbox_inches="tight", dpi=300)
    plt.show()
    return g
