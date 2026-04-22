import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats


properties=pd.read_csv('/content/egypt_real_estate_listings.csv')

size_split= properties['size'].str.split(' ',expand=True)
properties['sqft_size']=size_split[0]
properties['sqm_size']=size_split[3]
properties['sqft_size'] = properties['sqft_size'].str.replace(',', '').astype(float)
properties['sqm_size'] = properties['sqm_size'].str.replace(',', '').astype(float)

properties['bedrooms'] = properties['bedrooms'].fillna('N/A')

# 2. Split into a list
# This creates a list of strings for every row, even if it's just ['N/A']
properties['beds_list'] = properties['bedrooms'].str.split('+')

# 3. Apply the combined logic
# We use a single function to make it readable and combined
def format_bedrooms(item_list):
    # Strip whitespace from each item in the list
    cleaned = [i.strip() for i in item_list]
    
    # Logic: if only one item (like '3' or 'N/A'), just return it
    if len(cleaned) == 1:
        return cleaned[0]
    
    # Logic: if multiple items (like ['3', 'Maid']), join with ' \ '
    return " \\ ".join(cleaned)

properties['bedrooms_final'] = properties['beds_list'].apply(format_bedrooms)

# Check the result
print(properties[['bedrooms', 'bedrooms_final']].head())

properties = properties.dropna(subset=['bedrooms']).copy()

# 2. Create the beds_list
properties['beds_list'] = properties['bedrooms'].str.split('+')

# 3. Define the custom logic function
def calculate_rooms(b_list):
    # Safety check: if for some reason the list is empty
    if not b_list:
        return 1
    
    first_item = b_list[0].strip()
    
    # CASE: Only one item in the list
    if len(b_list) == 1:
        try:
            return int(first_item)
        except ValueError:
            return 1 # e.g., "Studio" becomes 1
            
    # CASE: More than one item (e.g., "3+ Maid")
    else:
        try:
            return int(first_item) + 1
        except ValueError:
            return 2 # e.g., "SomeText+ Maid" becomes 2

# 4. Apply the function
properties['total_rooms_numeric'] = properties['beds_list'].apply(calculate_rooms)

# Create a boolean (0 or 1) column
properties['has_maid'] = properties['beds_list'].apply(
    lambda x: 1 if any('maid' in str(item).lower() for item in x) else 0
)



properties['available_from'] = pd.to_datetime(properties['available_from'])
properties['available_from']


properties['location'] = properties['location'].fillna('Unknown, Unknown, Unknown')
# Split the location string by comma
loc_split = properties['location'].str.split(',')

# 1. Extract Governorate (Always the last item)
properties['governorate'] = loc_split.str[-1].str.strip()

# 2. Extract City (Usually the second to last item)
properties['city'] = loc_split.str[-2].str.strip()

# 3. Extract Area/Compound (Everything else before the city)
# We join the remaining items back together if there are multiple
properties['area_compound'] = loc_split.apply(lambda x: ", ".join(x[:-2]).strip() if len(x) > 2 else x[0].strip())
# Standardize common words
properties['city'] = properties['city'].str.replace(' City', '', case=False).str.strip()
properties['governorate'] = properties['governorate'].str.replace(' Governorate', '', case=False).str.strip()


# 1. Remove "EGP"
properties['price_numeric'] = properties['price'].str.split().str[0]

# 2. Remove commas so Python sees a clean number
properties['price_numeric'] = properties['price_numeric'].str.replace(',', '')

# 3. Convert to float so you can calculate Averages and Medians
properties['price_numeric'] = properties['price_numeric'].astype(float)

# 1. Strip the '+' and handle the text
# We use .astype(str) first to ensure .str methods work
properties['bathrooms'] = properties['bathrooms'].astype(str).str.replace('+', '', regex=False)

# 2. Convert to numeric, forcing 'non', 'none', or 'nan' strings into actual NaN values
properties['bathrooms'] = pd.to_numeric(properties['bathrooms'], errors='coerce')

# 3. Fill those new NaN values (from 'non') with a default, like 1 or the median
# Most residential listings have at least 1 bathroom
properties['bathrooms'] = properties['bathrooms'].fillna(1).astype(int)


columns=['url','type','bathrooms','available_from', 'payment_method','sqft_size','sqm_size','total_rooms_numeric','has_maid','governorate','city','area_compound','price_numeric']
properties_cleaned=properties[columns]
properties_cleaned['price_per_sqm'] = properties_cleaned['price_numeric'] / properties_cleaned['sqm_size']
properties_cleaned.head()



# Calculate Median Metrics per Governorate
gov_stats = properties_cleaned.groupby('governorate').agg({
    'price_numeric': 'median',
    'price_per_sqm': 'median'
}).sort_values('price_per_sqm', ascending=False).reset_index()

# Visualization
fig, ax1 = plt.subplots(figsize=(12, 6))

# Bar for Price per SQM (The "Value Density")
sns.barplot(data=gov_stats, x='governorate', y='price_per_sqm', ax=ax1, palette='Blues_r')
ax1.set_ylabel('Median Price per SQM (EGP)', color='blue')
ax1.tick_params(axis='y', labelcolor='blue')

# Line for Total Price (The "Capital Scale")
ax2 = ax1.twinx()
sns.lineplot(data=gov_stats, x='governorate', y='price_numeric', ax=ax2, color='red', marker='o', label='Median Total Price')
ax2.set_ylabel('Median Total Price (EGP)', color='red')
ax2.tick_params(axis='y', labelcolor='red')

plt.title('Market Normalization: Value Density vs. Total Capital')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Filtering out extreme price outliers for a cleaner boxplot
q_low = properties_cleaned["price_numeric"].quantile(0.01)
q_hi  = properties_cleaned["price_numeric"].quantile(0.95)
df_filtered = properties_cleaned[(properties_cleaned["price_numeric"] < q_hi) & (properties_cleaned["price_numeric"] > q_low)]

plt.figure(figsize=(10, 6))
sns.boxplot(data=df_filtered, x='has_maid', y='price_numeric', palette='Set2')
plt.title('The "Service Premium": Impact of Maid Room on Property Price')
plt.xlabel('Has Maid Room')
plt.ylabel('Price (EGP)')
plt.yscale('log') # Log scale helps see the distribution across price tiers
plt.show()


# Create the Efficiency Metric
properties_cleaned['sqm_per_room'] = properties_cleaned['sqm_size'] / properties_cleaned['total_rooms_numeric']

# Analyze by City
efficiency_stats = properties_cleaned.groupby('city')['sqm_per_room'].median().sort_values(ascending=False).head(15).reset_index()

plt.figure(figsize=(12, 6))
sns.barplot(data=efficiency_stats, x='sqm_per_room', y='city', palette='magma')
plt.title('Space Efficiency: Median SQM Allocated per Room by City')
plt.xlabel('Square Meters per Room ($sqm/room$)')
plt.ylabel('City')
plt.tight_layout()
plt.show()


# Create the Efficiency Metric
properties_cleaned['sqm_per_room'] = properties_cleaned['sqm_size'] / properties_cleaned['total_rooms_numeric']

# Analyze by City
efficiency_stats = properties_cleaned.groupby('city')['sqm_per_room'].median().sort_values(ascending=False).head(15).reset_index()

plt.figure(figsize=(12, 6))
sns.barplot(data=efficiency_stats, x='sqm_per_room', y='city', palette='magma')
plt.title('Space Efficiency: Median SQM Allocated per Room by City')
plt.xlabel('Square Meters per Room ($sqm/room$)')
plt.ylabel('City')
plt.tight_layout()
plt.show()

# Calculate Z-Score of Price per SQM within each City
def get_zscore(group):
    return (group - group.mean()) / group.std()

properties_cleaned['deal_score'] = properties_cleaned.groupby('city')['price_per_sqm'].transform(get_zscore)

# "Strong Deals" are those with a Z-Score < -1.5 (Cheaper than 93% of the city)
top_deals = properties_cleaned[properties_cleaned['deal_score'] < -1.5].sort_values('deal_score')

print("TOP 5 UNDERVALUED OPPORTUNITIES:")
print(top_deals[['city', 'price_numeric', 'sqm_size', 'price_per_sqm', 'url']].head(5))
