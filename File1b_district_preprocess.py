import os.path
import pandas as pd
import numpy as np

# Import school spending file
school_envir = pd.read_csv('school_df.csv')

def folder_imports(folder_path): 
    files = os.listdir(folder_path)
    dict = {}
    for file in files:
        new_df = pd.read_csv(os.path.join(folder_path, file))
        dict[file] = new_df
    return dict

# Rounding data to integer by columns
def to_int(df, columns):
  for column in columns:
    df[column] = pd.to_numeric(df[column]).round(0).astype('Int64')

# Select relevant teacher salary information, and format data
def salary_schedule(schedule, year):
    # Select only rows where the Rank is II
    schedule = schedule[schedule['Rank'] == 'II'].copy()
    # Compute the maximum salary for Rank II
    #salary = schedule[['I', 'II', 'III']].max(axis=1, skipna=True)
    salary = schedule[['I', 'II', 'III']].apply(pd.to_numeric, errors='coerce').max(axis=1)
    
    # Add the 'Salary' column
    schedule['Salary'] = salary
    # Split the 'District' column into two columns and convert 'DISTRICT NUMBER' to integer
    schedule[['District Code', 'District']] = schedule['District'].str.split(n=1, expand=True)
    schedule['District Code'] = schedule['District Code'].astype(int)
    # Select only the necessary columns
    new_schedule = schedule.loc[:,['Fiscal Year', 'Years', 'District Code', 'District', 'Salary']].copy()
    # Rename the columns
    new_schedule = new_schedule.rename(columns={
        'Fiscal Year': 'End Year',
        'Years': 'Years of experience',
        'Salary': 'Teacher salary based on experience'})
    new_schedule['End Year'] = year
    return new_schedule

# Use to locate the district teacher salary average
def get_district_average(row):
    district_code = row['District Code']
    end_year = row['End Year']
    return avg_salary.loc[district_code, end_year]

## District Salary Schedules by rank and years of experience
district_salary_schedules = folder_imports('/Users/rosehelfrich/Repos/School_Imports/district')


years = list(range(2010, 2024))
salary_list = []

for year in years:
    # Assuming you have imported the files into district_salary_schedules
    file_key = f'fy {year} salary schedule.csv'
    raw_salary = district_salary_schedules[file_key]
    salary = salary_schedule(raw_salary, year)
    salary_list.append(salary)

salary_by_experience = pd.concat(salary_list).drop_duplicates(ignore_index=True)

# Convert to Int64
to_int(salary_by_experience, ['End Year', 'Years of experience', 'District Code', 'Teacher salary based on experience'])


# ## Teacher salary average per district
avg_salary = district_salary_schedules['Average Classroom Teacher Salaries (1989-2024) ADA.csv'].loc[:, ['Dist No', '2009-10', '2010-11', '2011-12',
                                               '2012-13', '2013-14', '2014-15', '2015-16', '2016-17',
                                               '2017-18', '2018-19', '2019-20', '2020-21', '2021-22',
                                               '2022-23', '2023-24']]

# Rename the columns
new_column_names = ['District Code'] + list(range(2010, 2025))
avg_salary.columns = new_column_names

avg_salary.dropna(inplace=True)

# Convert to Int64
to_int(avg_salary, ['District Code'])
to_int(avg_salary, list(range(2010, 2025)))

# Set district code to index
avg_salary.set_index('District Code', drop=True, inplace=True)


# Combine district avg salary with salaries by experience per year
# This will be used to create an estimate of money spent per school.
df_salary = salary_by_experience.copy()
df_salary['District teacher salary average'] = df_salary.apply(get_district_average, axis=1)
df_salary.drop(['District'], axis =1, inplace=True)

# Convert to Int64
to_int(df_salary, ['District teacher salary average'])


## School and District
# Merge the school and district data.
df_preprocessed = pd.merge(school_envir, df_salary, on=['End Year', 'District Code', 'Years of experience'], how='left')

# Create codes for level and end year
df_preprocessed['Level Code'] = df_preprocessed['Level'].replace(['ES', 'MS', 'HS'], [0, 1, 2])
df_preprocessed['End Year Code'] = df_preprocessed['End Year'] - 2012

#Reorders the columns
reordered_columns = ['End Year', 'End Year Code',
                     'District', 'District Code',
                     'School', 'School Code',
                     'Level', 'Level Code',
                     'Reported Spending per student', 'Student Count',
                     'Educator Count', 'Years of experience',
                     'Teacher salary based on experience', 'District teacher salary average']
df_preprocessed = df_preprocessed[reordered_columns]

# In case duplicates occur.  Right now these don't actually drop any rows.
df_preprocessed.drop_duplicates(inplace=True)
df_preprocessed.dropna(subset=['End Year', 'Level'], inplace=True)
df_preprocessed.reset_index(drop=True, inplace=True)

# Replace the values that appear incorrect with np.Nan
df_preprocessed.loc[df_preprocessed['Reported Spending per student'] < 2000, 'Reported Spending per student'] = np.NaN
df_preprocessed.loc[df_preprocessed['Educator Count'] < 2, 'Educator Count'] = np.NaN
df_preprocessed.loc[df_preprocessed['Student Count'] < 10, 'Student Count'] = np.NaN

#Replace empty values with np.nan (doesn't remove data)
null_mask = pd.isnull(df_preprocessed ['Reported Spending per student'])
df_preprocessed.loc[null_mask, ['Money Difference per school', 'Money Difference per student']] = np.nan

# Calculated estimated spending
df_preprocessed['Money Difference per school'] = ((df_preprocessed['Teacher salary based on experience'] - df_preprocessed['District teacher salary average']) * df_preprocessed['Educator Count'])
df_preprocessed['Money Difference per student'] = (df_preprocessed['Money Difference per school'] / df_preprocessed['Student Count'])
df_preprocessed['Estimated Spending per student'] = (df_preprocessed['Reported Spending per student'] + df_preprocessed['Money Difference per student'])

# Convert to Int64
to_int(df_preprocessed, ['Level Code', 'Money Difference per school', 'Money Difference per student', 'Estimated Spending per student'])

# Round
df_preprocessed = df_preprocessed.round({'Reported Spending per student': -1, 'Money Difference per school': -2})


df_preprocessed.to_csv('preprocessed_df.csv', index = False)
