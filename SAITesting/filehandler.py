import os

import pm4py

class FileHandler:
    """
    A class for handling data. call get_from_file(file_path) to get a dataframe from a file, and call write_to_csv(dataframe, output_path) to write a dataframe to a csv file.

    to_sequences makes the dataframe into a list of sequences of events, where each event is a tuple of (activity, other_keys) : other_keys might be empty in the data in which case 0 is default

    filter_activities filters the dataframe so that only on certain activities are other activities included. For example if activities = {'calciumTest': 'Calcium', 'vitamin d': 'Vitamin D'}, then only when activity is calciumTest is the value of column Calcium included, and when activity is vitamin d is the value of column Vitamin D included. any other activities stay but without associated values in the columns Calcium and Vitamin D
    """
    #not sure this works yet and it might be useless
    def handle_url(self, url, target_filename):
        import requests
        print(f"Downloading from {url}...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(target_filename, "wb") as file:
            file.write(response.content)
        print(f"Downloaded and saved to {target_filename}")
        return target_filename
    
    def get_from_file(self, file_path):
        if file_path.endswith('.xes') or file_path.endswith('.xes.gz'):
            log = pm4py.read_xes(file_path)
            dataframe = pm4py.convert_to_dataframe(log)
        elif file_path.endswith('.csv'):
            import pandas as pd
            dataframe = pd.read_csv(file_path)
        else:
            raise ValueError("Unsupported file format. Please provide a .xes, .xes.gz, or .csv file.")
        print(f"got dataframe with {len(dataframe.columns)} columns and {len(dataframe)} rows")
        print(f"head: {dataframe.head()}")
        return dataframe
        
    def write_to_csv(self, dataframe, output_path):
        dataframe.to_csv(output_path)
    def to_sequences(self, dataframe, key='case:concept:name',activity_key='concept:name', time_key='time:timestamp', other_keys:list[str]=[]):
        # Convert the dataframe to sequences of events
        # events being tuple of (activity, other_keys) : other_keys might be empty in which case 0 is default
        sequences = []
        for case_id, group in dataframe.groupby(key):
            sequence = group.sort_values(time_key)[activity_key,other_keys].tolist()
            sequences.append(sequence)
        return sequences
    def filter_activities(self, dataframe, activities:dict[str, str], activity_key='concept:name'):
        """
        Filter the dataframe so that only on certain activities are other activities included (see explanation above)
        """
        filtered_df = dataframe.copy()
        for activity, column in activities.items():
            filtered_df[column] = filtered_df.apply(lambda row: row[column] if row[activity_key] == activity else 0, axis=1)
        return filtered_df

