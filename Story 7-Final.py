# -*- coding: utf-8 -*-
"""
Created on Sat May 17 00:37:54 2025

@author: para2
"""
import pandas as pd
import numpy as np
import plotly.express as px
import us

# Load and process the data
url = "https://raw.githubusercontent.com/Aconrard/DATA608/refs/heads/main/Story%20%237/final_data.csv"
url2 = "https://raw.githubusercontent.com/Aconrard/DATA608/refs/heads/main/Story%20%237/state_consumption_production.csv"
df = pd.read_csv(url)
df2 = pd.read_csv(url2)

# Clean and process energy generation data
df['generation'] = pd.to_numeric(df['generation'], errors='coerce')

# Filter for 2023 data
df_2024 = df[df['year'] == 2024].copy()

# Create pivot table for generation by state and fuel type
energy_pivot = pd.pivot_table(
    df_2024,
    values='generation',
    index=['location', 'stateDescription'],
    columns=['fuelTypeDescription'],
    aggfunc='sum',
    fill_value=0
)

# Calculate total generation per state
energy_pivot['Total'] = energy_pivot.sum(axis=1)

# Calculate percentages for each fuel type
fuel_types = energy_pivot.columns[:-1]  # exclude Total column
for fuel in fuel_types:
    energy_pivot[f'{fuel}_pct'] = (energy_pivot[fuel] / energy_pivot['Total']) * 100

# Reset index to make state columns accessible
energy_pivot.reset_index(inplace=True)

# Process consumption/production data
def range_to_numeric(range_str):
    if range_str == '<500':
        return 250
    elif range_str == '>7,500':
        return 8750
    else:
        range_str = range_str.replace(',', '')
        lower, upper = map(float, range_str.split('-'))
        return (lower + upper) / 2

# Convert consumption and production ranges to numeric values
df2['Consumption_numeric'] = df2['Consumption'].apply(range_to_numeric)
df2['Production_numeric'] = df2['Production'].apply(range_to_numeric)


# Calculate net energy status
df2['Net_Energy'] = df2['Production_numeric'] - df2['Consumption_numeric']
df2['Status'] = np.select(
    [
        (df2['Net_Energy'] > 0),
        (df2['Net_Energy'] < 0),
        (df2['Net_Energy'] == 0)
    ],
    [
        'Exporter',
        'Importer',
        'Zero'
    ],
    default='Zero'
)

# Rename columns with proper capitalization
column_rename_dict = {
    'location': 'Location',
    'stateDescription': 'State Description',
    'coal, excluding waste coal': 'Coal',
    'natural gas': 'Natural Gas',
    'nuclear': 'Nuclear',
    'petroleum liquids': 'Petroleum',
    'solar': 'Solar',
    'wind': 'Wind',
    'Total': 'Total',
    'coal, excluding waste coal Percentage': 'Coal Percentage',
    'natural gas Percentage': 'Natural Gas Percentage',
    'nuclear Percentage': 'Nuclear Percentage',
    'petroleum liquids Percentage': 'Petroleum Percentage',
    'solar Percentage': 'Solar Percentage',
    'wind Percentage': 'Wind Percentage'
}

# Apply the renaming to energy_pivot
energy_pivot = energy_pivot.rename(columns=column_rename_dict)

# Merge datasets
merged_df = pd.merge(
    energy_pivot,
    df2[['State', 'Status', 'Net_Energy']],
    left_on='Location',
    right_on='State',
    how='left'
)

# Rename the remaining columns in merged_df
merged_df = merged_df.rename(columns={
    'Net_Energy': 'Net Energy'
})

# Add Total Thousands MW column
merged_df['Total Thousands MW'] = merged_df['Total']

# Add state abbreviations
state_abbrev = {state.name: state.abbr for state in us.states.STATES}
merged_df['State Abbreviation'] = merged_df['State Description'].map(state_abbrev)

# Create hover text function
def create_hover_text(row):
    energy_sources = []
    
    # Define the specific fuel columns we want to include
    fuel_columns = ['Coal', 'Natural Gas', 'Nuclear', 'Petroleum', 'Solar', 'Wind']
    
    for fuel in fuel_columns:
        if fuel in row.index and row[fuel] > 0:
            energy_sources.append(f"{fuel}: {row[fuel]:.2f} Thousand MW")
    
    text = f"<b>{row['State Description']}</b><br>"
    text += f"Total Energy: {row['Total Thousands MW']:.2f} Thousand MW<br><br>"
    text += "<b>Energy Sources:</b><br>"
    text += "<br>".join(energy_sources)
    text += f"<br><br><b>Status:</b> Net {row['Status']} of Energy"
    
    return text

# Apply the hover text function
merged_df['Hover Text'] = merged_df.apply(create_hover_text, axis=1)

# Create the choropleth map
fig = px.choropleth(
    merged_df,
    locations='State Abbreviation',
    locationmode='USA-states',
    color='Total Thousands MW',
    color_continuous_scale='Portland',
    scope="usa",
    labels={'Total Thousands MW': 'Energy Production<br>(Thousand MW)'},
    custom_data=['Hover Text', 'Status']
)

# Update hover template
fig.update_traces(
    hovertemplate="%{customdata[0]}",
    hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial")
)

# Add state abbreviations with conditional formatting
for i, row in merged_df.iterrows():
    # Set color based on exporter/importer/zero status
    if row['Status'] == 'Exporter':
        text_color = '#FF8C00'  # Brighter orange
    elif row['Status'] == 'Importer':
        text_color = 'lightgray'  # Light gray
    else:
        text_color = '#808080'  # Medium gray for 'Zero'

        
    # Add the state abbreviation with appropriate color
    fig.add_trace(px.scatter_geo(
        lat=[0],
        lon=[0],
        text=[row['State Abbreviation']],
        locations=[row['State Abbreviation']],
        locationmode='USA-states',
    ).data[0])
    
    # Update the appearance
    fig.data[-1].update(
        mode='text',
        textfont=dict(
            color=text_color,
            size=12,
            family='Arial Black, Arial Bold, Helvetica, sans-serif',
            weight='bold'
        ),
        showlegend=False,
        hoverinfo='skip',
        hovertemplate=None
    )


# Add a legend for the color meaning
fig.add_annotation(
    xref="paper", yref="paper",
    x=0.01, y=0.1,
    text="<b>Energy Status:</b><br><span style='color:#FF9500;'><b>Orange</b></span><b> = Net Exporter</b><br><span style='color:lightgray;'><b>Light Gray</b></span><b> = Net Importer</b><br><span style='color:#808080;'><b>Medium Gray</b></span><b> = Zero Net Energy</b>",
    showarrow=False,
    font=dict(
        size=12, 
        color="black",
        family='Arial Black, Arial Bold, Helvetica, sans-serif'
    ),
    align="left",
    bgcolor="rgba(255, 255, 255, 0.7)",
    bordercolor="black",
    borderwidth=1,
    borderpad=4
)


# Update layout with BOLD title
fig.update_layout(
    title={
        'text': '<b>U.S. Energy Production by State (2024)</b>',
        'y':0.95,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': dict(
            size=24,
            family='Arial Black, Arial Bold, Helvetica, sans-serif',
            weight='bold'
        )
    },
    geo=dict(
        showlakes=True,
        lakecolor='rgb(255, 255, 255)',
        landcolor='rgb(240, 240, 240)',
        showland=True,
        showcoastlines=True,
        coastlinecolor='rgb(80, 80, 80)',
        showsubunits=True,
        subunitcolor='rgb(80, 80, 80)',
    ),
    margin={"r":0,"t":50,"l":0,"b":0},
    height=800,
    coloraxis_colorbar=dict(
        title="Energy Production<br>(Thousand MW)",
        thicknessmode="pixels", 
        thickness=20,
        lenmode="fraction", 
        len=0.6,
        outlinecolor='rgb(80, 80, 80)',
        outlinewidth=1
    )
)

# Add instructions
# Add instructions under title
fig.add_annotation(
    xref="paper", yref="paper",
    x=0.55, y=0.97,  # Positioned below title (title is at y=0.95)
    text="<b>Hover over a state to see detailed energy production data.</b>",
    showarrow=False,
    font=dict(
        size=14, 
        color="black",
        family='Arial, sans-serif'
    ),
    align="center",
    bgcolor="rgba(255, 255, 255, 0.7)",
    bordercolor="black",
    borderwidth=1,
    borderpad=4,
    xanchor='center',
    yanchor='top'
)


# Save the figure as an HTML file
fig.write_html(r"C:\Users\para2\Desktop\Energy Data\Energy_Production_Map.html", full_html=True, include_plotlyjs='cdn')

# Display the map
fig.show()

print("Map created and saved as 'energy_production_map.html'")

# For hosting on GitHub or any web server:
print("\nTo host this map online:")
print("1. Upload the HTML file to GitHub")
print("2. Enable GitHub Pages in your repository settings")
print("3. The map will be available at: https://[your-username].github.io/[repo-name]/energy_production_map.html")
