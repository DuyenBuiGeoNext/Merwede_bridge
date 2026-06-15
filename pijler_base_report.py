# %%
import os
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

load_dotenv()

DB_HOST     = os.getenv("GRAFANA_DB_HOST")
DB_PORT     = int(os.getenv("GRAFANA_DB_PORT", 3306))
DB_USER     = os.getenv("GRAFANA_DB_USER")
DB_PASSWORD = os.getenv("GRAFANA_DB_PASSWORD")
DB_NAME     = os.getenv("GRAFANA_DB_NAME")

# %%
def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )

def extract_table(table: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        query = f"SELECT * FROM `{table}`"
        df = pd.read_sql(query, conn)
        print(f"Extracted {len(df)} rows and {len(df.columns)} columns from '{table}'.")
        print(f"Columns: {list(df.columns)}")
        return df
    finally:
        conn.close()

# %%
TABLES = ["Pijler9", "waterlevel", "Weerstation1", "Weerstation2"]

data = {}
for table in TABLES:
    data[table] = extract_table(table)

# %%
df_pijler9    = data["Pijler9"]
df_waterlevel = data["waterlevel"]
df_weer1      = data["Weerstation1"]
df_weer2      = data["Weerstation2"]

# Quick check
for name, df in data.items():
    print(f"{name}: {len(df)} rows, {len(df.columns)} columns")

# %%
# Apply NA cleaning to all tables
for name in data:
    data[name] = data[name].replace("N/A", pd.NA)
    data[name] = data[name].dropna(axis=1, how='all')
    data[name] = data[name].dropna(axis=0, how='all')
    print(f"{name}: {len(data[name])} rows after cleaning")

# Reassign after cleaning
df_pijler9    = data["Pijler9"]
df_waterlevel = data["waterlevel"]
df_weer1      = data["Weerstation1"]
df_weer2      = data["Weerstation2"]

# %%
GAP_THRESHOLD = pd.Timedelta(days=35)

def insert_gaps(df, time_col, value_cols, threshold):
    rows = []
    for i in range(len(df)):
        rows.append(df.iloc[i])
        if i < len(df) - 1:
            dt = df[time_col].iloc[i+1] - df[time_col].iloc[i]
            if dt > threshold:
                gap_row = df.iloc[i].copy()
                gap_row[time_col] = df[time_col].iloc[i] + dt / 2
                for col in value_cols:
                    gap_row[col] = np.nan
                rows.append(gap_row)
    return pd.DataFrame(rows).reset_index(drop=True)

# %%
# --- Displacement outlier removal ---
displacement_cols = ['Brugpunt1_deltax', 'Brugpunt2_deltax', 'Brugpunt1_deltaz', 'Brugpunt2_deltaz', 'delta_y']

df_pijler9_clean = df_pijler9.copy()
for col in displacement_cols:
    Q1 = df_pijler9_clean[col].quantile(0.25)
    Q3 = df_pijler9_clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df_pijler9_clean[col] = df_pijler9_clean[col].where(
        (df_pijler9_clean[col] >= lower) & (df_pijler9_clean[col] <= upper), np.nan
    )

print(f"Pijler9 displacement: {len(df_pijler9_clean)} rows after outlier removal")

# %%
df_displacement_plot = insert_gaps(df_pijler9_clean, 'Timestamp', displacement_cols, GAP_THRESHOLD)
print(f"Rows after gap insertion: {len(df_displacement_plot)}")

# %%
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
fig.suptitle('XYZ displacements — Pijler 9', fontsize=20, fontweight='bold')

t = df_displacement_plot['Timestamp']

axes[0].plot(t, df_displacement_plot['Brugpunt1_deltax'], color='#378ADD', linewidth=2.5, label='Brugpunt 1')
axes[0].plot(t, df_displacement_plot['Brugpunt2_deltax'], color='#378ADD', linewidth=2.5, linestyle='--', label='Brugpunt 2')
axes[0].set_ylabel('mm', fontsize=20)
axes[0].set_title('Delta X', fontsize=20, fontweight='bold')
axes[0].axhline(0, color='gray', linewidth=0.8, linestyle=':')
axes[0].legend(fontsize=18)
axes[0].grid(True, alpha=0.15)
axes[0].tick_params(axis='both', labelsize=18)

axes[1].plot(t, df_displacement_plot['Brugpunt1_deltaz'], color='#D85A30', linewidth=2.5, label='Brugpunt 1')
axes[1].plot(t, df_displacement_plot['Brugpunt2_deltaz'], color='#D85A30', linewidth=2.5, linestyle='--', label='Brugpunt 2')
axes[1].set_ylabel('mm', fontsize=20)
axes[1].set_title('Delta Z', fontsize=20, fontweight='bold')
axes[1].axhline(0, color='gray', linewidth=0.8, linestyle=':')
axes[1].legend(fontsize=18)
axes[1].grid(True, alpha=0.15)
axes[1].tick_params(axis='both', labelsize=18)

axes[2].plot(t, df_displacement_plot['delta_y'], color='#1D9E75', linewidth=2.5, label='Delta Y')
axes[2].set_ylabel('mm', fontsize=20)
axes[2].set_title('Delta Y', fontsize=20, fontweight='bold')
axes[2].axhline(0, color='gray', linewidth=0.8, linestyle=':')
axes[2].legend(fontsize=18)
axes[2].grid(True, alpha=0.15)
axes[2].tick_params(axis='both', labelsize=18)

axes[2].xaxis.set_major_locator(mdates.MonthLocator())
axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=18)

plt.tight_layout()
plt.savefig('Pijler9_displacements.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Rotation outlier removal ---
rotation_cols = ['Brug_rotatiex', 'Brug_rotatiey', 'Brug_rotatiez']

df_pijler9_rot_clean = df_pijler9.copy()
for col in rotation_cols:
    Q1 = df_pijler9_rot_clean[col].quantile(0.25)
    Q3 = df_pijler9_rot_clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df_pijler9_rot_clean[col] = df_pijler9_rot_clean[col].where(
        (df_pijler9_rot_clean[col] >= lower) & (df_pijler9_rot_clean[col] <= upper), np.nan
    )

# %%
df_rotation_plot = insert_gaps(df_pijler9_rot_clean, 'Timestamp', rotation_cols, GAP_THRESHOLD)

# %%
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
fig.suptitle('XYZ rotations — Pijler 9', fontsize=20, fontweight='bold')

t = df_rotation_plot['Timestamp']
colors = ['#378ADD', '#D85A30', '#1D9E75']
titles = ['Rotation X', 'Rotation Y', 'Rotation Z']

for ax, col, title, color in zip(axes, rotation_cols, titles, colors):
    ax.plot(t, df_rotation_plot[col], color=color, linewidth=2.5, label=col)
    ax.set_ylabel('mm', fontsize=20)
    ax.set_title(title, fontsize=20, fontweight='bold')
    ax.axhline(0, color='gray', linewidth=0.8, linestyle=':')
    ax.legend(fontsize=15)
    ax.tick_params(axis='both', labelsize=15)

    # Y grid: 6 evenly spaced ticks relative to each panel's own data range
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
    ax.grid(True, alpha=0.4, linewidth=0.8, color='gray')

# X axis on bottom panel only (sharex=True)
axes[2].xaxis.set_major_locator(mdates.MonthLocator())
axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=15)

plt.tight_layout()
plt.savefig('Pijler9_rotations.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
df_waterlevel = df_waterlevel.dropna(how='any')
print(df_waterlevel.columns.tolist())
print(df_waterlevel.head())
# %%
# Get the gap periods from df_pijler9_clean (where displacement data is missing)
df_pijler9_clean['Timestamp'] = pd.to_datetime(df_pijler9_clean['Timestamp'])
df_waterlevel['Timestamp']    = pd.to_datetime(df_waterlevel['Timestamp'])

# Find gap periods: consecutive timestamps in pijler9 more than 35 days apart
gap_periods = []
df_p9_sorted = df_pijler9_clean.sort_values('Timestamp').reset_index(drop=True)
for i in range(len(df_p9_sorted) - 1):
    dt = df_p9_sorted['Timestamp'].iloc[i+1] - df_p9_sorted['Timestamp'].iloc[i]
    if dt > GAP_THRESHOLD:
        gap_start = df_p9_sorted['Timestamp'].iloc[i]
        gap_end   = df_p9_sorted['Timestamp'].iloc[i+1]
        gap_periods.append((gap_start, gap_end))

print(f"Found {len(gap_periods)} gap periods:")
for start, end in gap_periods:
    print(f"  {start.date()} → {end.date()}")
# %%
# Apply IQR outlier removal to waterlevel columns
wl_value_cols = ['pressure', 'water_level']

df_waterlevel_clean = df_waterlevel.copy()
for col in wl_value_cols:
    Q1 = df_waterlevel_clean[col].quantile(0.25)
    Q3 = df_waterlevel_clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df_waterlevel_clean[col] = df_waterlevel_clean[col].where(
        (df_waterlevel_clean[col] >= lower) & (df_waterlevel_clean[col] <= upper), np.nan
    )

df_waterlevel_plot = insert_gaps(df_waterlevel_clean, 'Timestamp', wl_value_cols, GAP_THRESHOLD)
print(f"Rows after gap insertion: {len(df_waterlevel_plot)}")

# %%
# Get date range from Pijler9
date_min = df_pijler9_clean['Timestamp'].min()
date_max = df_pijler9_clean['Timestamp'].max()

print(f"Pijler9 range: {date_min} → {date_max}")

# Trim waterlevel to match Pijler9 date range
df_waterlevel_plot = df_waterlevel_plot[
    (df_waterlevel_plot['Timestamp'] >= date_min) &
    (df_waterlevel_plot['Timestamp'] <= date_max)
].reset_index(drop=True)

print(f"Waterlevel trimmed: {df_waterlevel_plot['Timestamp'].min()} → {df_waterlevel_plot['Timestamp'].max()}")
print(f"Rows remaining: {len(df_waterlevel_plot)}")
# %%
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.suptitle('Water conditions — Merwedebrug', fontsize=20, fontweight='bold')

t = df_waterlevel_plot['Timestamp']

# --- Panel 1: Pressure ---
axes[0].plot(t, df_waterlevel_plot['pressure'], color='#378ADD', linewidth=2.5, label='Water pressure')
axes[0].set_ylabel('kPa', fontsize=20)
axes[0].set_title('Water pressure', fontsize=20, fontweight='bold')
axes[0].grid(True, alpha=0.15)
axes[0].tick_params(axis='both', labelsize=15)

# --- Panel 2: Water level ---
axes[1].plot(t, df_waterlevel_plot['water_level'], color='#1D9E75', linewidth=2.5, label='Water level')
axes[1].set_ylabel('m NAP', fontsize=20)
axes[1].set_title('Water level', fontsize=20, fontweight='bold')
axes[1].grid(True, alpha=0.15)
axes[1].tick_params(axis='both', labelsize=15)

# --- Gray out gap periods ---
from matplotlib.patches import Patch
for gap_start, gap_end in gap_periods:
    for ax in axes:
        ax.axvspan(gap_start, gap_end, color='gray', alpha=0.15, label='_nolegend_')

# --- Legends ---
gap_patch = Patch(facecolor='gray', alpha=0.3, label='No displacement data')
axes[0].legend(handles=[axes[0].lines[0], gap_patch], fontsize=15)
axes[1].legend(handles=[axes[1].lines[0], gap_patch], fontsize=15)

# --- X axis labels and grid on every panel ---
for ax in axes:
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
    ax.grid(True, alpha=0.5, linewidth=1.0, color='gray')
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=15)

plt.tight_layout()
plt.savefig('Merwedebrug_waterlevel.png', dpi=150, bbox_inches='tight')
plt.show()
# %%
# Ensure Timestamp is datetime
df_weer1['Timestamp'] = pd.to_datetime(df_weer1['Timestamp'])
df_weer2['Timestamp'] = pd.to_datetime(df_weer2['Timestamp'])

# Trim to Pijler9 date range
df_weer1_plot = df_weer1[
    (df_weer1['Timestamp'] >= date_min) &
    (df_weer1['Timestamp'] <= date_max)
].reset_index(drop=True)

df_weer2_plot = df_weer2[
    (df_weer2['Timestamp'] >= date_min) &
    (df_weer2['Timestamp'] <= date_max)
].reset_index(drop=True)

# IQR outlier removal on Temperature
for df in [df_weer1_plot, df_weer2_plot]:
    Q1 = df['Temperature'].quantile(0.25)
    Q3 = df['Temperature'].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df['Temperature'] = df['Temperature'].where(
        (df['Temperature'] >= lower) & (df['Temperature'] <= upper), np.nan
    )


# %%
fig, ax = plt.subplots(1, 1, figsize=(14, 5))
fig.suptitle('Temperature — Weerstations', fontsize=20, fontweight='bold')

ax.plot(df_weer1_plot['Timestamp'], df_weer1_plot['Temperature'], color='#378ADD', linewidth=2.5, label='Weerstation 1')
ax.plot(df_weer2_plot['Timestamp'], df_weer2_plot['Temperature'], color='#D85A30', linewidth=2.5, linestyle='--', label='Weerstation 2')
ax.set_ylabel('°C', fontsize=20)
ax.set_title('Temperature', fontsize=20, fontweight='bold')
ax.grid(True, alpha=0.15)
ax.tick_params(axis='both', labelsize=15)

# --- Gray out gap periods ---
from matplotlib.patches import Patch
for gap_start, gap_end in gap_periods:
    ax.axvspan(gap_start, gap_end, color='gray', alpha=0.15, label='_nolegend_')

# --- Legend ---
gap_patch = Patch(facecolor='gray', alpha=0.3, label='No displacement data')
ax.legend(handles=[ax.lines[0], ax.lines[1], gap_patch], fontsize=15)

# --- X axis ---
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=15)

plt.tight_layout()
plt.savefig('Merwedebrug_temperature.png', dpi=150, bbox_inches='tight')
plt.show()
# %%
# %%
# Compute summary statistics for displacement
displacement_stats = []

displacement_definitions = [
    ('Brugpunt1_deltax', 'Delta X — Brugpunt 1', 'mm'),
    ('Brugpunt2_deltax', 'Delta X — Brugpunt 2', 'mm'),
    ('Brugpunt1_deltaz', 'Delta Z — Brugpunt 1', 'mm'),
    ('Brugpunt2_deltaz', 'Delta Z — Brugpunt 2', 'mm'),
    ('delta_y',          'Delta Y',               'mm'),
]

for col, label, unit in displacement_definitions:
    series = df_pijler9_clean[col].dropna()
    total  = len(df_pijler9_clean)
    coverage = f"{(len(series) / total * 100):.1f}%"
    displacement_stats.append({
        'Sensor':         label,
        'Unit':           unit,
        'Min':            f"{series.min():.3f}",
        'Max':            f"{series.max():.3f}",
        'Mean':           f"{series.mean():.3f}",
        'Std dev (σ)':    f"{series.std():.3f}",
        'Data coverage':  coverage,
    })

# Compute summary statistics for rotations
rotation_definitions = [
    ('Brug_rotatiex', 'Rotation X', 'mm'),
    ('Brug_rotatiey', 'Rotation Y', 'mm'),
    ('Brug_rotatiez', 'Rotation Z', 'mm'),
]

rotation_stats = []
for col, label, unit in rotation_definitions:
    series = df_pijler9_rot_clean[col].dropna()
    total  = len(df_pijler9_rot_clean)
    coverage = f"{(len(series) / total * 100):.1f}%"
    rotation_stats.append({
        'Sensor':         label,
        'Unit':           unit,
        'Min':            f"{series.min():.3f}",
        'Max':            f"{series.max():.3f}",
        'Mean':           f"{series.mean():.3f}",
        'Std dev (σ)':    f"{series.std():.3f}",
        'Data coverage':  coverage,
    })

df_disp_stats = pd.DataFrame(displacement_stats)
df_rot_stats  = pd.DataFrame(rotation_stats)

print("Displacement statistics:")
print(df_disp_stats)
print("\nRotation statistics:")
print(df_rot_stats)
# %%
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def save_table_as_png(df, title, filename):
    n_rows, n_cols = df.shape

    fig_height = 0.5 + n_rows * 0.5 + 1.0
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axis('off')

    ax.set_title(title, fontsize=16, fontweight='bold', pad=16)

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center',
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.auto_set_column_width(col=list(range(n_cols)))

    # Style header row
    for col in range(n_cols):
        cell = table[0, col]
        cell.set_facecolor('#2C2C2A')
        cell.set_text_props(color='white', fontweight='bold')
        cell.set_height(0.12)

    # Style data rows with alternating colors
    for row in range(1, n_rows + 1):
        for col in range(n_cols):
            cell = table[row, col]
            cell.set_facecolor('#F1EFE8' if row % 2 == 0 else 'white')
            cell.set_height(0.10)

    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"Saved to {filename}")

# %%
save_table_as_png(df_disp_stats, 'Summary statistics — XYZ displacements (Pijler 9)', 'Pijler9_displacement_stats.png')
save_table_as_png(df_rot_stats,  'Summary statistics — XYZ rotations (Pijler 9)',      'Pijler9_rotation_stats.png')
# %%
fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=False)
fig.suptitle('XYZ rotations — Pijler 9', fontsize=20, fontweight='bold')

t = df_rotation_plot['Timestamp']
colors = ['#378ADD', '#D85A30', '#1D9E75']
titles = ['Rotation X', 'Rotation Y', 'Rotation Z']

for ax, col, title, color in zip(axes, rotation_cols, titles, colors):
    ax.plot(t, df_rotation_plot[col], color=color, linewidth=2.5, label=col)
    ax.set_ylabel('mm', fontsize=20)
    ax.set_title(title, fontsize=20, fontweight='bold')
    ax.axhline(0, color='gray', linewidth=0.8, linestyle=':')
    ax.legend(fontsize=15)
    ax.tick_params(axis='both', labelsize=15)

    # Y grid: 6 evenly spaced ticks relative to each panel's own data range
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
    ax.grid(True, alpha=0.5, linewidth=1.0, color='gray')

    # X axis labels on every panel
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=15)

plt.tight_layout()
plt.savefig('Pijler9_rotations.png', dpi=150, bbox_inches='tight')
plt.show()





fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=False)
fig.suptitle('XYZ displacements — Pijler 9', fontsize=20, fontweight='bold')

t = df_displacement_plot['Timestamp']

# --- Panel 1: Delta X (blue) ---
axes[0].plot(t, df_displacement_plot['Brugpunt1_deltax'], color='#378ADD', linewidth=2.5, label='Brugpunt 1')
axes[0].plot(t, df_displacement_plot['Brugpunt2_deltax'], color='#378ADD', linewidth=2.5, linestyle='--', label='Brugpunt 2')
axes[0].set_ylabel('mm', fontsize=20)
axes[0].set_title('Delta X', fontsize=20, fontweight='bold')
axes[0].axhline(0, color='gray', linewidth=0.8, linestyle=':')
axes[0].legend(fontsize=18)
axes[0].tick_params(axis='both', labelsize=18)
axes[0].yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
axes[0].grid(True, alpha=0.5, linewidth=1.0, color='gray')
axes[0].xaxis.set_major_locator(mdates.MonthLocator())
axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=18)

# --- Panel 2: Delta Y (orange) ---
axes[1].plot(t, df_displacement_plot['delta_y'], color='#D85A30', linewidth=2.5, label='Delta Y')
axes[1].set_ylabel('mm', fontsize=20)
axes[1].set_title('Delta Y', fontsize=20, fontweight='bold')
axes[1].axhline(0, color='gray', linewidth=0.8, linestyle=':')
axes[1].legend(fontsize=18)
axes[1].tick_params(axis='both', labelsize=18)
axes[1].yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
axes[1].grid(True, alpha=0.5, linewidth=1.0, color='gray')
axes[1].xaxis.set_major_locator(mdates.MonthLocator())
axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=18)

# --- Panel 3: Delta Z (green) ---
axes[2].plot(t, df_displacement_plot['Brugpunt1_deltaz'], color='#1D9E75', linewidth=2.5, label='Brugpunt 1')
axes[2].plot(t, df_displacement_plot['Brugpunt2_deltaz'], color='#1D9E75', linewidth=2.5, linestyle='--', label='Brugpunt 2')
axes[2].set_ylabel('mm', fontsize=20)
axes[2].set_title('Delta Z', fontsize=20, fontweight='bold')
axes[2].axhline(0, color='gray', linewidth=0.8, linestyle=':')
axes[2].legend(fontsize=18)
axes[2].tick_params(axis='both', labelsize=18)
axes[2].yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
axes[2].grid(True, alpha=0.5, linewidth=1.0, color='gray')
axes[2].xaxis.set_major_locator(mdates.MonthLocator())
axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=18)

plt.tight_layout()
plt.savefig('Pijler9_displacements.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
fig.suptitle('Water conditions — Merwedebrug', fontsize=20, fontweight='bold')

t = df_waterlevel_clean['Timestamp']

# --- Panel 1: Pressure ---
axes[0].plot(t, df_waterlevel_clean['pressure'], color='#378ADD', linewidth=2.5, label='Water pressure')
axes[0].set_ylabel('kPa', fontsize=20)
axes[0].set_title('Water pressure', fontsize=20, fontweight='bold')
axes[0].grid(True, alpha=0.5, linewidth=1.0, color='gray')
axes[0].tick_params(axis='both', labelsize=15)
axes[0].yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
axes[0].xaxis.set_major_locator(mdates.MonthLocator())
axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=15)

# --- Panel 2: Water level ---
axes[1].plot(t, df_waterlevel_clean['water_level'], color='#1D9E75', linewidth=2.5, label='Water level')
axes[1].set_ylabel('m NAP', fontsize=20)
axes[1].set_title('Water level', fontsize=20, fontweight='bold')
axes[1].grid(True, alpha=0.5, linewidth=1.0, color='gray')
axes[1].tick_params(axis='both', labelsize=15)
axes[1].yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
axes[1].xaxis.set_major_locator(mdates.MonthLocator())
axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=15)

# --- Gray out gap periods ---
from matplotlib.patches import Patch
for gap_start, gap_end in gap_periods:
    for ax in axes:
        ax.axvspan(gap_start, gap_end, color='gray', alpha=0.15, label='_nolegend_')

# --- Legends ---
gap_patch = Patch(facecolor='gray', alpha=0.3, label='No displacement data')
axes[0].legend(handles=[axes[0].lines[0], gap_patch], fontsize=15)
axes[1].legend(handles=[axes[1].lines[0], gap_patch], fontsize=15)

plt.tight_layout()
plt.savefig('Merwedebrug_waterlevel.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# Bijlage 1: Meetdata Pijler 9
df_pijler9_clean.to_csv('Bijlage1_Meetdata_Pijler9.csv', index=False)
print("Saved: Bijlage1_Meetdata_Pijler9.csv")

# Bijlage 2: Meetdata Weerstation 1 & 2
df_weer1.to_csv('Bijlage2_Meetdata_Weerstation1.csv', index=False)
df_weer2.to_csv('Bijlage2_Meetdata_Weerstation2.csv', index=False)
print("Saved: Bijlage2_Meetdata_Weerstation1.csv")
print("Saved: Bijlage2_Meetdata_Weerstation2.csv")

# Bijlage 3: Meetdata Waterstand
df_waterlevel.to_csv('Bijlage3_Meetdata_Waterstand.csv', index=False)
print("Saved: Bijlage3_Meetdata_Waterstand.csv")