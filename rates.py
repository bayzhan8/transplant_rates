import logging
import pandas as pd
import math
import numpy as np
from typing import Dict, Callable, Union
import os

logger = logging.getLogger(__name__)

def gender_rates(path: Union[str, os.PathLike], person_times: pd.DataFrame, read_output: Callable) -> Dict[str, float]:
    output = read_output(path)

    output_with_groups = output.merge(person_times[['cand_id', 'can_gender']], on='cand_id', how='left')
    group_ratios = {}   
    
    # Compute the matched ratios for KAS.txt for each gender group using the candidate DataFrame for totals
    for group in person_times['can_gender'].dropna().unique():
        num_matched = len(output_with_groups[output_with_groups["can_gender"] == group])
        total_time = person_times[person_times["cand_id"].isin(person_times[person_times["can_gender"] == group]["cand_id"])]["time_difference"].sum()
        if total_time == 0:
            continue  
        group_ratios[group] = 365 * num_matched / total_time

    return group_ratios

def ethnicity_rates(path: Union[str, os.PathLike], person_times: pd.DataFrame, race_df: pd.DataFrame, read_output: Callable) -> Dict[str, float]:
    output = read_output(path)
    output_with_groups = output.merge(race_df[['cand_id', 'can_ethnicity_srtr']], on='cand_id', how='left')
    group_ratios = {}
    
    # Compute the matched ratios for KAS.txt for each ethnicity group using the candidate DataFrame for totals
    if "can_ethnicity_srtr" in person_times.columns:
        for group in person_times['can_ethnicity_srtr'].dropna().unique():
            num_matched = len(output_with_groups[output_with_groups["can_ethnicity_srtr"] == group])
            total_time = person_times[person_times["cand_id"].isin(person_times[person_times["can_ethnicity_srtr"] == group]["cand_id"])]["time_difference"].sum()
            if total_time == 0:
                continue  
            group_ratios[group] = 365 * num_matched / total_time
    else:
        logger.warning("No ethnicity data found in person_times.")
    return group_ratios

def race_rates(path: Union[str, os.PathLike], person_times: pd.DataFrame, race_df: pd.DataFrame, read_output: Callable) -> Dict[str, float]:
    output = read_output(path)
    output = pd.merge(output, race_df[['cand_id', 'can_race_srtr']], on='cand_id', how='left')
    ratios_race = {}
    
    # Compute the matched ratios for KAS.txt for each race group using the candidate DataFrame for totals
    if 'can_race_srtr' in person_times.columns:
        for race in person_times['can_race_srtr'].dropna().unique():
            num_matched = len(output[output["can_race_srtr"] == race])
            total_time = person_times[person_times["cand_id"].isin(person_times[person_times["can_race_srtr"] == race]["cand_id"])]["time_difference"].sum()
            if total_time == 0:
                continue  
            ratios_race[race] = 365 * num_matched / total_time
    else:
        logger.warning("No race data found in person_times.")
        
    return ratios_race

def age_rates(path: Union[str, os.PathLike], person_times: pd.DataFrame, read_output_default: Callable) -> Dict[str, float]:
    output = read_output_default(path)
    output_with_age = output.merge(person_times[['cand_id', 'real_age']], on='cand_id', how='left')
    
    ratios = {}
    
    # Fixed age bins with proper boundary handling
    age_bins = [(0, 18), (18, 35), (35, 50), (50, 65), (65, 90)]
    
    for lb, ub in age_bins:
        # Handle edge cases: include lower bound for first bin, exclude for others

        if ub == 90:  # include 90
            num_matched = len(output_with_age[(output_with_age["real_age"] >= 0) & (output_with_age["real_age"] <= ub)])
            total_time = person_times[(person_times["real_age"] >= 0) & (person_times["real_age"] < ub)]["time_difference"].sum()
        else:
            num_matched = len(output_with_age[(output_with_age["real_age"] >= lb) & (output_with_age["real_age"] < ub)])
            total_time = person_times[(person_times["real_age"] >= lb) & (person_times["real_age"] < ub)]["time_difference"].sum()
        
        ratios[(lb, ub)] = 365 * num_matched / total_time if total_time > 0 else 0
    
    return ratios

def age_at_listing_rates(path, person_times, read_output_default):
    output = read_output_default(path)
    output_with_age = output.merge(person_times[['cand_id', 'can_age_at_listing']], on='cand_id', how='left')
    
    ratios = {}
    
    # Fixed age bins with proper boundary handling
    age_bins = [(0, 18), (18, 35), (35, 50), (50, 65), (65, 90)]
    
    for lb, ub in age_bins:
        # Handle edge cases: include lower bound for first bin, exclude for others
        if ub == 90:  #  include 90
            num_matched = len(output_with_age[(output_with_age["can_age_at_listing"] >= 0) & (output_with_age["can_age_at_listing"] <= ub)])
            total_time = person_times[(person_times["can_age_at_listing"] >= 0) & (person_times["can_age_at_listing"] < ub)]["time_difference"].sum()
        else:
            num_matched = len(output_with_age[(output_with_age["can_age_at_listing"] >= lb) & (output_with_age["can_age_at_listing"] < ub)])
            total_time = person_times[(person_times["can_age_at_listing"] >= lb) & (person_times["can_age_at_listing"] < ub)]["time_difference"].sum()
        
        ratios[(lb, ub)] = 365 * num_matched / total_time if total_time > 0 else 0
    
    return ratios

def abo_rates(path, person_times, read_output):
    output = read_output(path)    
    output_with_abo = output.merge(person_times[['cand_id', 'can_abo_replaced']], on='cand_id', how='left')
    ratios_abo = {}
    
    # Compute the matched ratios for KAS.txt for each abo group using the candidate DataFrame for totals
    for bl_type in person_times['can_abo_replaced'].dropna().unique():
        num_matched = len(output_with_abo[output_with_abo["can_abo_replaced"] == bl_type])
        total_time = person_times[person_times["cand_id"].isin(person_times[person_times["can_abo_replaced"] == bl_type]["cand_id"])]["time_difference"].sum()
        if total_time == 0:
            continue  
        ratios_abo[bl_type] = 365 * num_matched / total_time
    
    return ratios_abo

def epts_rates(path, person_times, final_epts, final_cpra, donor, read_output_epts_cpra, step = 20):
    output = read_output_epts_cpra(path, final_epts, final_cpra, donor)
    ratios = {}
    
    # Ensure step divides 100 evenly to avoid edge cases
    if 100 % step != 0:
        # Adjust step to be a divisor of 100
        step = 20  # Default fallback
        logger.warning(f"Step size adjusted to {step} to ensure even division of 100")
    
    # Create bins from 0 to 100 with proper step size
    for lb in range(0, 100, step): 
        ub = lb + step
        lb_pct = lb / 100  
        ub_pct = ub / 100  
        
        # Handle edge cases: include lower bound for first bin and upper bound for last bin
        if lb == 0:  # First bin: include EPTS_PCT == 0
            num_matched = len(output[(output["epts_pct"] >= lb_pct) & (output["epts_pct"] < ub_pct)])
            total_time = person_times[(person_times["epts_pct"] >= lb_pct) & (person_times["epts_pct"] < ub_pct)]["time_difference"].sum()
        if ub == 100:
            num_matched = len(output[(output["epts_pct"] >= lb_pct) & (output["epts_pct"] <= ub_pct)])
            total_time = person_times[(person_times["epts_pct"] >= lb_pct) & (person_times["epts_pct"] <= ub_pct)]["time_difference"].sum()
        else:
            num_matched = len(output[(output["epts_pct"] >= lb_pct) & (output["epts_pct"] < ub_pct)])
            total_time = person_times[(person_times["epts_pct"] >= lb_pct) & (person_times["epts_pct"] < ub_pct)]["time_difference"].sum()
            
        ratios[(lb, ub)] = 365 * num_matched / total_time if total_time > 0 else 0
    
    return ratios

def cpra_rates(path, person_times, final_epts, final_cpra, donor, read_output_epts_cpra):
    output = read_output_epts_cpra(path, final_epts, final_cpra, donor)
    output['canhx_cpra'] = output['cand_id'].map(final_cpra.set_index('cand_id')['canhx_cpra'])  # change here!
    
    ratios = {}
    
    # Fixed CPRA bins with proper boundary handling
    cpra_bins = [[0.001, 0.6], [0.6, 0.8], [0.8, 0.98], [0.98, 1.001]]  # Added small buffer for upper bound
    
    for lb, ub in cpra_bins:
        # Handle edge cases: include lower bound for first bin, exclude for others
        if lb == -0.001:  # First bin: include CPRA == 0
            num_matched = len(output[(output["canhx_cpra"] >= 0) & (output["canhx_cpra"] < ub)])
            total_time = person_times[(person_times["canhx_cpra"] >= 0) & (person_times["canhx_cpra"] < ub)]["time_difference"].sum()
        else:
            num_matched = len(output[(output["canhx_cpra"] >= lb) & (output["canhx_cpra"] < ub)])
            total_time = person_times[(person_times["canhx_cpra"] >= lb) & (person_times["canhx_cpra"] < ub)]["time_difference"].sum()
        
        ratios[(int(100*lb), int(100*ub))] = 365 * num_matched / total_time if total_time > 0 else 0
        
    return ratios


def race_rates_dan(path):
    can_link = '/gpfs/data/mankowskilab/OASim/Profiles/Kidney Request profiles/KI2023_01_Data/Candidate_Data/cleaned_static_candidate_data.csv'
    
    can_df = pd.read_csv(can_link, index_col = 'cand_id')
    can_df= can_df.convert_dtypes()
    can_df['can_listing_dt'] = pd.to_datetime(can_df['can_listing_dt'])
    
    can_df = can_df[can_df['wl_org'] != 'PA']
    
    don_link = '/gpfs/data/mankowskilab/OASim/Profiles/Kidney Request profiles/KI2023_01_Data/Donor_Data/cleaned_donor_data.csv'
    don_df = pd.read_csv(don_link, index_col = 'don_id')
    don_df = don_df.convert_dtypes()
    don_df['don_event_datetime'] = pd.to_datetime(don_df['don_event_datetime'])
    
    crm_link = '/gpfs/data/mankowskilab/OASim/Profiles/Kidney Request profiles/KI2023_01_Data/Candidate_Data/generated_removal_candidate_data.csv'
    crm_df = pd.read_csv(crm_link, index_col = 'cand_id')
    crm_df= crm_df.convert_dtypes()
    crm_df['cand_event_datetime'] = pd.to_datetime(crm_df['cand_event_datetime'])
    
    crm_df = crm_df.loc[can_df.index.intersection(crm_df.index)].copy()
    
    
    can_race = pd.read_csv("data_srtr/can_race.csv", index_col='px_id')
    can_race = can_race.convert_dtypes()
    
    valid_keys = can_race.index.intersection(can_df['px_id'])
    len(valid_keys) / len(can_df)
    assert len(valid_keys) / len(can_df) > 0.99
    
    can_df['race'] = 'UNKNOWN'
    race_label = can_df['race'].copy()
    good_indices = can_df['px_id'].isin(can_race.index)
    race_label[good_indices] = can_race.loc[can_df['px_id'][good_indices]]['can_race_srtr']
    can_df['race'] = race_label
    
    
    def read_tx_df(link):
        df = pd.read_csv(link)
        df = df.convert_dtypes()
        df = df.dropna(subset=['cand_id','don_id'])
        df = df[df['organ'] != 'PA']
        return df
    
    df = read_tx_df(path)
    
    n_placements = df['cand_id'].value_counts()
    
    can_df['placed'] = n_placements
    can_df['placed'] = can_df['placed'].fillna(0)
    
    start_time = can_df['can_listing_dt'].clip(lower=pd.to_datetime('2021-03-15'))
    end_time = crm_df['cand_event_datetime'].clip(lower=pd.to_datetime('2021-03-15'), upper=pd.to_datetime('2022-03-15'))
    
    df['end_dt'] = don_df.loc[df['don_id']]['don_event_datetime'].values
    df['start_dt'] = can_df.loc[df['cand_id']]['can_listing_dt'].values
    df['start_dt'] = df['start_dt'].clip(lower=pd.to_datetime('2021-03-15'))
    df['wait_time'] = df['end_dt'] - df['start_dt']
    
    wait_time = pd.DataFrame(df[['cand_id','wait_time']]).set_index('cand_id')['wait_time']
    wait_time = wait_time[~wait_time.index.duplicated(keep='last')]
    removal_time = (end_time - start_time[crm_df.index]).dropna()
    total_time = (pd.to_datetime('2022-03-15') - start_time)
    
    can_df['total_time'] = total_time.copy()
    can_df.loc[removal_time.index, 'total_time'] = removal_time
    can_df.loc[wait_time.index, 'total_time'] = wait_time
    
    can_df['total_time'] = can_df['total_time'] / pd.Timedelta(days=365)
    hist_placement = can_df.groupby('race')[['total_time', 'placed']].sum()
    hist_placement['rate'] = hist_placement['placed'] * 100 / hist_placement['total_time']

    new_dict = dict(hist_placement["rate"])
    del new_dict['UNKNOWN']
    
    return new_dict


def epts_percentages(path, final_epts, final_cpra, donor, read_output_epts_cpra):
    output = read_output_epts_cpra(path, final_epts, final_cpra, donor)
    ratios = {}
    total_num = len(output)
    
    # Fixed EPTS percentage bins with proper boundary handling
    epts_bins = [[-0.001, 0.2], [0.2, 0.4], [0.4, 0.6], [0.6, 0.8], [0.8, 1.001]]  # Added buffer for upper bound
    
    for lb, ub in epts_bins:
        # Handle edge cases: include lower bound for first bin, exclude for others
        if lb == -0.001:  # First bin: include EPTS_PCT == 0
            num_matched = len(output[(output["epts_pct"] >= 0) & (output["epts_pct"] < ub)])
        else:
            num_matched = len(output[(output["epts_pct"] >= lb) & (output["epts_pct"] < ub)])
        
        ratios[(int(100*lb), int(100*ub))] = num_matched / total_num if total_num > 0 else 0
    
    return ratios



def distance(path, final_epts, final_cpra, donor, static, read_output_default):
    def haversine(lat1, lon1, lat2, lon2):
        # Convert latitude and longitude from degrees to radians
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)
    
        # Compute differences
        dlat = lat2 - lat1
        dlon = lon2 - lon1
    
        # Haversine formula
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
    
        # Earth's radius in nautical miles
        r = 6371 / 1.852
    
        # Compute distance
        distance = c * r
        return distance 
    
    df = read_output_default(path)
    df = df.merge(static[['cand_id', 'can_center_longitude', 'can_center_latitude']], on='cand_id', how='left')
    df = df.merge(donor[['don_id', "don_center_longitude", "don_center_latitude"]], on='don_id', how='left')
    
    df['distance'] = df.apply(lambda row: haversine(row['can_center_latitude'], row['can_center_longitude'], row['don_center_latitude'], row['don_center_longitude']), axis=1)

    return {"Median Travel Distance: ": df["distance"].median()}