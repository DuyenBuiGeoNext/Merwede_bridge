# %%
import os
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from brokenaxes import brokenaxes
from matplotlib.patches import Patch

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
TABLES = ["Basculekelder", "waterlevel", "Weerstation1", "Weerstation2"]

data = {}
for table in TABLES:
    data[table] = extract_table(table)

# %%
df_Basculekelder    = data["Basculekelder"]
df_waterlevel = data["waterlevel"]
df_weer1      = data["Weerstation1"]
df_weer2      = data["Weerstation2"]

for name, df in data.items():
    print(f"{name}: {len(df)} rows, {len(df.columns)} columns")

# %%
# Apply NA cleaning to all tables
for name in data:
    data[name] = data[name].replace("N/A", pd.NA)
    data[name] = data[name].dropna(axis=1, how='all')
    data[name] = data[name].dropna(axis=0, how='all')
    print(f"{name}: {len(data[name])} rows after cleaning")

df_Basculekelder    = data["Basculekelder"]
df_waterlevel = data["waterlevel"]
df_weer1      = data["Weerstation1"]
df_weer2      = data["Weerstation2"]

# %%
GAP_THRESHOLD = pd.Timedelta(days=35)

# Flat temperature period — no measurement
TEMP_FLAT_START = pd.Timestamp('2026-03-08')
TEMP_FLAT_END   = pd.Timestamp('2026-03-31')

def get_gap_periods(df, time_col, threshold):
    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    gaps = []
    for i in range(len(df_sorted) - 1):
        dt = df_sorted[time_col].iloc[i+1] - df_sorted[time_col].iloc[i]
        if dt > threshold:
            gaps.append((df_sorted[time_col].iloc[i], df_sorted[time_col].iloc[i+1]))
    return gaps

def get_xlims_from_gaps(df, time_col, gap_periods, padding_days=5):
    padding = pd.Timedelta(days=padding_days)
    t_min = df[time_col].min()
    t_max = df[time_col].max()
    if not gap_periods:
        return ((t_min, t_max),)
    xlims = []
    seg_start = t_min
    for gap_start, gap_end in gap_periods:
        xlims.append((seg_start - padding, gap_start + padding))
        seg_start = gap_end - padding
    xlims.append((seg_start, t_max + padding))
    return tuple(xlims)

def style_bax(bax, ylabel, title, fontsize=18):
    bax.set_ylabel(ylabel, fontsize=fontsize, labelpad=40)
    bax.axs[0].set_title(title, fontsize=fontsize, fontweight='bold')
    for ax in bax.axs:
        ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=6, symmetric=True))
        ax.grid(True, alpha=0.5, linewidth=1.0, color='gray')
        ax.tick_params(axis='both', labelsize=13)
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=12)
    bax.axhline(0, color='gray', linewidth=0.8, linestyle=':')

# %%
# --- Displacement: IQR outlier removal ---
displacement_cols = ['Brugpunt1_deltax', 'Brugpunt2_deltax', 'Brugpunt1_deltaz', 'Brugpunt2_deltaz', 'delta_y']

df_Basculekelder_clean = df_Basculekelder.copy()
df_Basculekelder_clean['Timestamp'] = pd.to_datetime(df_Basculekelder_clean['Timestamp'])

for col in displacement_cols:
    Q1 = df_Basculekelder_clean[col].quantile(0.25)
    Q3 = df_Basculekelder_clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df_Basculekelder_clean[col] = df_Basculekelder_clean[col].where(
        (df_Basculekelder_clean[col] >= lower) & (df_Basculekelder_clean[col] <= upper), np.nan
    )

# --- Rotation: IQR outlier removal ---
rotation_cols = ['Brug_rotatiex', 'Brug_rotatiey', 'Brug_rotatiez']

df_Basculekelder_rot_clean = df_Basculekelder.copy()
df_Basculekelder_rot_clean['Timestamp'] = pd.to_datetime(df_Basculekelder_rot_clean['Timestamp'])

for col in rotation_cols:
    Q1 = df_Basculekelder_rot_clean[col].quantile(0.25)
    Q3 = df_Basculekelder_rot_clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df_Basculekelder_rot_clean[col] = df_Basculekelder_rot_clean[col].where(
        (df_Basculekelder_rot_clean[col] >= lower) & (df_Basculekelder_rot_clean[col] <= upper), np.nan
    )

# %%
# --- Remove spike period Feb 2026 – 05 March 2026 ---
remove_start = pd.Timestamp('2026-02-01')
remove_end   = pd.Timestamp('2026-03-05')

df_Basculekelder_clean = df_Basculekelder_clean[
    ~((df_Basculekelder_clean['Timestamp'] >= remove_start) &
      (df_Basculekelder_clean['Timestamp'] <= remove_end))
].reset_index(drop=True)

df_Basculekelder_rot_clean = df_Basculekelder_rot_clean[
    ~((df_Basculekelder_rot_clean['Timestamp'] >= remove_start) &
      (df_Basculekelder_rot_clean['Timestamp'] <= remove_end))
].reset_index(drop=True)

print(f"Displacement rows after spike removal: {len(df_Basculekelder_clean)}")
print(f"Rotation rows after spike removal:     {len(df_Basculekelder_rot_clean)}")

# %%
# --- Detect gap periods ---
gap_periods = get_gap_periods(df_Basculekelder_clean, 'Timestamp', GAP_THRESHOLD)

print(f"Found {len(gap_periods)} gap periods:")
for start, end in gap_periods:
    print(f"  {start.date()} → {end.date()}")

# %%
# --- Build xlims for brokenaxes ---
xlims_p9 = get_xlims_from_gaps(df_Basculekelder_clean, 'Timestamp', gap_periods)
print("X segments:", [(str(a.date()), str(b.date())) for a, b in xlims_p9])

# %%
# --- Statistics definitions ---
displacement_definitions = [
    ('Brugpunt1_deltax', 'Delta X — Brugpunt 1', 'mm'),
    ('Brugpunt2_deltax', 'Delta X — Brugpunt 2', 'mm'),
    ('delta_y',          'Delta Y',               'mm'),
    ('Brugpunt1_deltaz', 'Delta Z — Brugpunt 1', 'mm'),
    ('Brugpunt2_deltaz', 'Delta Z — Brugpunt 2', 'mm'),
]

rotation_definitions = [
    ('Brug_rotatiex', 'Rotation X', 'mm'),
    ('Brug_rotatiey', 'Rotation Y', 'mm'),
    ('Brug_rotatiez', 'Rotation Z', 'mm'),
]

# %%
# --- Compute statistics ---
displacement_stats = []
for col, label, unit in displacement_definitions:
    series = df_Basculekelder_clean[col].dropna()
    displacement_stats.append({
        'Sensor':      label,
        'Unit':        unit,
        'Min':         f"{series.min():.3f}",
        'Max':         f"{series.max():.3f}",
        'Mean':        f"{series.mean():.3f}",
        'Std dev (σ)': f"{series.std():.3f}",
    })

rotation_stats = []
for col, label, unit in rotation_definitions:
    series = df_Basculekelder_rot_clean[col].dropna()
    rotation_stats.append({
        'Sensor':      label,
        'Unit':        unit,
        'Min':         f"{series.min():.3f}",
        'Max':         f"{series.max():.3f}",
        'Mean':        f"{series.mean():.3f}",
        'Std dev (σ)': f"{series.std():.3f}",
    })

df_disp_stats = pd.DataFrame(displacement_stats)
df_rot_stats  = pd.DataFrame(rotation_stats)

print("Displacement statistics:")
print(df_disp_stats)
print("\nRotation statistics:")
print(df_rot_stats)

# %%
# --- Save statistics tables as PNG ---
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
    for col in range(n_cols):
        cell = table[0, col]
        cell.set_facecolor('#2C2C2A')
        cell.set_text_props(color='white', fontweight='bold')
        cell.set_height(0.12)
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
save_table_as_png(df_disp_stats, 'Summary statistics — XYZ displacements (Basculekelder)', 'Basculekelder_displacement_stats.png')
save_table_as_png(df_rot_stats,  'Summary statistics — XYZ rotations (Basculekelder)',      'Basculekelder_rotation_stats.png')

# %%
# --- Plot rotations with broken x axis ---
t = df_Basculekelder_rot_clean['Timestamp']
colors = ['#378ADD', '#D85A30', '#1D9E75']
titles = ['Rotation X', 'Rotation Y', 'Rotation Z']

fig = plt.figure(figsize=(16, 14))
fig.suptitle('XYZ rotations — Basculekelder', fontsize=20, fontweight='bold', y=1.01)

for i, (col, title, color) in enumerate(zip(rotation_cols, titles, colors)):
    bax = brokenaxes(
        xlims=xlims_p9,
        subplot_spec=plt.GridSpec(3, 1, hspace=0.55)[i],
        fig=fig,
        d=0.008,
        tilt=70,
    )
    bax.plot(t, df_Basculekelder_rot_clean[col], color=color, linewidth=2.0, label=col)
    style_bax(bax, 'mm', title)
    bax.legend(fontsize=13, loc='upper left')

plt.savefig('Basculekelder_rotations.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Plot displacements with broken x axis ---
t = df_Basculekelder_clean['Timestamp']

fig = plt.figure(figsize=(16, 14))
fig.suptitle('XYZ displacements — Basculekelder', fontsize=20, fontweight='bold', y=1.01)

panels = [
    ('Brugpunt1_deltax', 'Brugpunt2_deltax', 'Delta X', '#378ADD'),
    ('delta_y',           None,               'Delta Y', '#D85A30'),
    ('Brugpunt1_deltaz', 'Brugpunt2_deltaz', 'Delta Z', '#1D9E75'),
]

for i, (col1, col2, title, color) in enumerate(panels):
    bax = brokenaxes(
        xlims=xlims_p9,
        subplot_spec=plt.GridSpec(3, 1, hspace=0.55)[i],
        fig=fig,
        d=0.008,
        tilt=70,
    )
    bax.plot(t, df_Basculekelder_clean[col1], color=color, linewidth=2.0, label='Brugpunt 1')
    if col2:
        bax.plot(t, df_Basculekelder_clean[col2], color=color, linewidth=2.0,
                 linestyle='--', label='Brugpunt 2')
    style_bax(bax, 'mm', title)
    bax.legend(fontsize=13, loc='upper left')

plt.savefig('Basculekelder_displacements.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Waterlevel: IQR outlier removal and trim ---
df_waterlevel = df_waterlevel.dropna(how='any')
df_waterlevel['Timestamp'] = pd.to_datetime(df_waterlevel['Timestamp'])
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

date_min = df_Basculekelder_clean['Timestamp'].min()
date_max = df_Basculekelder_clean['Timestamp'].max()

df_waterlevel_plot = df_waterlevel_clean[
    (df_waterlevel_clean['Timestamp'] >= date_min) &
    (df_waterlevel_clean['Timestamp'] <= date_max)
].reset_index(drop=True)

print(f"Waterlevel rows after trimming: {len(df_waterlevel_plot)}")

# %%
# --- Plot water conditions with broken x axis ---
t_wl = df_waterlevel_plot['Timestamp']

fig = plt.figure(figsize=(16, 10))
fig.suptitle('Water conditions — Merwedebrug', fontsize=20, fontweight='bold', y=1.01)

wl_panels = [
    ('pressure',    'kPa',   'Water pressure', '#378ADD'),
    ('water_level', 'm NAP', 'Water level',    '#1D9E75'),
]

for i, (col, ylabel, title, color) in enumerate(wl_panels):
    bax = brokenaxes(
        xlims=xlims_p9,
        subplot_spec=plt.GridSpec(2, 1, hspace=0.55)[i],
        fig=fig,
        d=0.008,
        tilt=70,
    )
    bax.plot(t_wl, df_waterlevel_plot[col], color=color, linewidth=2.0, label=title)
    style_bax(bax, ylabel, title)
    bax.legend(fontsize=13, loc='upper left')

plt.savefig('Merwedebrug_waterlevel.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Temperature: trim and IQR outlier removal ---
df_weer1['Timestamp'] = pd.to_datetime(df_weer1['Timestamp'])
df_weer2['Timestamp'] = pd.to_datetime(df_weer2['Timestamp'])

df_weer1_plot = df_weer1[
    (df_weer1['Timestamp'] >= date_min) &
    (df_weer1['Timestamp'] <= date_max)
].reset_index(drop=True)

df_weer2_plot = df_weer2[
    (df_weer2['Timestamp'] >= date_min) &
    (df_weer2['Timestamp'] <= date_max)
].reset_index(drop=True)

# IQR outlier removal
for df in [df_weer1_plot, df_weer2_plot]:
    Q1 = df['Temperature'].quantile(0.25)
    Q3 = df['Temperature'].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 4 * IQR
    upper = Q3 + 4 * IQR
    df['Temperature'] = df['Temperature'].where(
        (df['Temperature'] >= lower) & (df['Temperature'] <= upper), np.nan
    )

# Remove flat no-measurement period by explicit date range
df_weer1_plot.loc[
    (df_weer1_plot['Timestamp'] >= TEMP_FLAT_START) &
    (df_weer1_plot['Timestamp'] <= TEMP_FLAT_END), 'Temperature'
] = np.nan

df_weer2_plot.loc[
    (df_weer2_plot['Timestamp'] >= TEMP_FLAT_START) &
    (df_weer2_plot['Timestamp'] <= TEMP_FLAT_END), 'Temperature'
] = np.nan

print(f"Weerstation1: {len(df_weer1_plot)} rows")
print(f"Weerstation2: {len(df_weer2_plot)} rows")

# %%
# --- Plot temperature with broken x axis and grayed out no-data period ---
fig = plt.figure(figsize=(16, 6))
fig.suptitle('Temperature — Weerstations', fontsize=20, fontweight='bold', y=1.01)

bax = brokenaxes(
    xlims=xlims_p9,
    subplot_spec=plt.GridSpec(1, 1)[0],
    fig=fig,
    d=0.008,
    tilt=70,
)

bax.plot(df_weer1_plot['Timestamp'], df_weer1_plot['Temperature'],
         color='#378ADD', linewidth=2.0, label='Weerstation 1')
bax.plot(df_weer2_plot['Timestamp'], df_weer2_plot['Temperature'],
         color='#D85A30', linewidth=2.0, linestyle='--', label='Weerstation 2')

# Gray out the no-measurement period
for ax in bax.axs:
    ax.axvspan(TEMP_FLAT_START, TEMP_FLAT_END,
               color='gray', alpha=0.25, label='_nolegend_')
    ax.axvline(TEMP_FLAT_START, color='gray', linewidth=1.2,
               linestyle='--', alpha=0.6)
    ax.axvline(TEMP_FLAT_END, color='gray', linewidth=1.2,
               linestyle='--', alpha=0.6)

style_bax(bax, '°C', 'Temperature')
no_data_patch = Patch(facecolor='gray', alpha=0.25, label='Geen data beschikbaar')
bax.legend(
    fontsize=13,
    loc='upper left',
    handles=[bax.axs[0].lines[0], bax.axs[0].lines[1], no_data_patch]
)

plt.savefig('Merwedebrug_temperature.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Save CSV bijlagen ---
os.makedirs('Bijlagen', exist_ok=True)

df_Basculekelder_clean.to_csv('Bijlagen/Bijlage1_Meetdata_Basculekelder.csv', index=False)
df_weer1.to_csv('Bijlagen/Bijlage2_Meetdata_Weerstation1.csv', index=False)
df_weer2.to_csv('Bijlagen/Bijlage2_Meetdata_Weerstation2.csv', index=False)
df_waterlevel.to_csv('Bijlagen/Bijlage3_Meetdata_Waterstand.csv', index=False)
print("All files saved to Bijlagen/")

# %%
# --- Merge structural and environmental data ---
df_Basculekelder_clean['Timestamp']   = pd.to_datetime(df_Basculekelder_clean['Timestamp'])
df_waterlevel_plot['Timestamp'] = pd.to_datetime(df_waterlevel_plot['Timestamp'])
df_weer1_plot['Timestamp']      = pd.to_datetime(df_weer1_plot['Timestamp'])
df_weer2_plot['Timestamp']      = pd.to_datetime(df_weer2_plot['Timestamp'])

# Filter out flat temperature period from weather data before merging
df_weer1_corr = df_weer1_plot[
    ~((df_weer1_plot['Timestamp'] >= TEMP_FLAT_START) &
      (df_weer1_plot['Timestamp'] <= TEMP_FLAT_END))
].reset_index(drop=True)

df_weer2_corr = df_weer2_plot[
    ~((df_weer2_plot['Timestamp'] >= TEMP_FLAT_START) &
      (df_weer2_plot['Timestamp'] <= TEMP_FLAT_END))
].reset_index(drop=True)

df_merged = pd.merge_asof(
    df_Basculekelder_clean.sort_values('Timestamp'),
    df_waterlevel_plot[['Timestamp', 'pressure', 'water_level']].sort_values('Timestamp'),
    on='Timestamp', tolerance=pd.Timedelta('2h'), direction='nearest'
)
df_merged = pd.merge_asof(
    df_merged.sort_values('Timestamp'),
    df_weer1_corr[['Timestamp', 'Temperature']].rename(
        columns={'Temperature': 'Temp_weer1'}).sort_values('Timestamp'),
    on='Timestamp', tolerance=pd.Timedelta('2h'), direction='nearest'
)
df_merged = pd.merge_asof(
    df_merged.sort_values('Timestamp'),
    df_weer2_corr[['Timestamp', 'Temperature']].rename(
        columns={'Temperature': 'Temp_weer2'}).sort_values('Timestamp'),
    on='Timestamp', tolerance=pd.Timedelta('2h'), direction='nearest'
)

df_merged['Temperature'] = df_merged[['Temp_weer1', 'Temp_weer2']].mean(axis=1)
df_merged = df_merged.dropna(subset=['pressure', 'water_level'])
print(f"Merged dataset: {len(df_merged)} rows")

# %%
# --- Merge rotation data with environmental data ---
df_rot_env = pd.merge_asof(
    df_Basculekelder_rot_clean.sort_values('Timestamp'),
    df_waterlevel_plot[['Timestamp', 'pressure', 'water_level']].sort_values('Timestamp'),
    on='Timestamp', tolerance=pd.Timedelta('2h'), direction='nearest'
)
df_rot_env = pd.merge_asof(
    df_rot_env.sort_values('Timestamp'),
    df_weer1_corr[['Timestamp', 'Temperature']].rename(
        columns={'Temperature': 'Temp_weer1'}).sort_values('Timestamp'),
    on='Timestamp', tolerance=pd.Timedelta('2h'), direction='nearest'
)
df_rot_env = pd.merge_asof(
    df_rot_env.sort_values('Timestamp'),
    df_weer2_corr[['Timestamp', 'Temperature']].rename(
        columns={'Temperature': 'Temp_weer2'}).sort_values('Timestamp'),
    on='Timestamp', tolerance=pd.Timedelta('2h'), direction='nearest'
)
df_rot_env['Temperature'] = df_rot_env[['Temp_weer1', 'Temp_weer2']].mean(axis=1)
df_rot_env = df_rot_env.dropna(subset=['pressure', 'water_level'])
print(f"Rotation-environment merged dataset: {len(df_rot_env)} rows")

# %%
# --- Scatter plots: displacement vs environmental variables (no temperature) ---
structural_cols = [
    ('Brugpunt1_deltax', 'Delta X — Brugpunt 1 (mm)'),
    ('delta_y',          'Delta Y (mm)'),
    ('Brugpunt1_deltaz', 'Delta Z — Brugpunt 1 (mm)'),
]

env_cols = [
    ('water_level', 'Water level (m NAP)'),
    ('pressure',    'Water pressure (kPa)'),
]

colors_struct = ['#378ADD', '#D85A30', '#1D9E75']

fig, axes = plt.subplots(len(structural_cols), len(env_cols), figsize=(16, 16))
fig.suptitle('Correlation — structural movement vs environmental conditions',
             fontsize=18, fontweight='bold')

for row, (s_col, s_label) in enumerate(structural_cols):
    for col, (e_col, e_label) in enumerate(env_cols):
        ax = axes[row, col]
        valid = df_merged[[s_col, e_col]].dropna()
        ax.scatter(valid[e_col], valid[s_col],
                   color=colors_struct[row], alpha=0.4, s=25, linewidths=0)
        if len(valid) > 2:
            z = np.polyfit(valid[e_col], valid[s_col], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid[e_col].min(), valid[e_col].max(), 100)
            ax.plot(x_line, p(x_line), color='black', linewidth=2.0,
                    linestyle='--', label=f'R={valid[s_col].corr(valid[e_col]):.2f}')
        ax.set_xlabel(e_label, fontsize=18)
        ax.set_ylabel(s_label, fontsize=18)
        ax.tick_params(axis='both', labelsize=15)
        ax.grid(True, alpha=0.3, linewidth=0.8)
        ax.legend(fontsize=13)

plt.tight_layout()
plt.savefig('Basculekelder_scatter_correlation.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Scatter plots: rotation vs environmental variables (no temperature) ---
rotation_struct_cols = [
    ('Brug_rotatiex', 'Rotation X (mm)'),
    ('Brug_rotatiey', 'Rotation Y (mm)'),
    ('Brug_rotatiez', 'Rotation Z (mm)'),
]

colors_rot = ['#378ADD', '#D85A30', '#1D9E75']

fig, axes = plt.subplots(len(rotation_struct_cols), len(env_cols), figsize=(16, 16))
fig.suptitle('Correlation — structural rotation vs environmental conditions\nBasculekelder',
             fontsize=18, fontweight='bold')

for row, (s_col, s_label) in enumerate(rotation_struct_cols):
    for col, (e_col, e_label) in enumerate(env_cols):
        ax = axes[row, col]
        valid = df_rot_env[[s_col, e_col]].dropna()
        ax.scatter(valid[e_col], valid[s_col],
                   color=colors_rot[row], alpha=0.4, s=25, linewidths=0)
        if len(valid) > 2:
            z = np.polyfit(valid[e_col], valid[s_col], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid[e_col].min(), valid[e_col].max(), 100)
            ax.plot(x_line, p(x_line), color='black', linewidth=2.0,
                    linestyle='--', label=f'R={valid[s_col].corr(valid[e_col]):.2f}')
        ax.set_xlabel(e_label, fontsize=15)
        ax.set_ylabel(s_label, fontsize=15)
        ax.tick_params(axis='both', labelsize=15)
        ax.grid(True, alpha=0.3, linewidth=0.8)
        ax.legend(fontsize=13)

plt.tight_layout()
plt.savefig('Basculekelder_scatter_rotation_correlation.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Save correlation data to CSV ---
disp_corr_cols = ['Timestamp',
                  'Brugpunt1_deltax', 'Brugpunt2_deltax',
                  'delta_y',
                  'Brugpunt1_deltaz', 'Brugpunt2_deltaz',
                  'water_level', 'pressure']

df_merged[disp_corr_cols].to_csv(
    'Bijlagen/Correlation_displacement_environmental.csv', index=False
)
print(f"Saved: Correlation_displacement_environmental.csv — {len(df_merged)} rows")

rot_corr_cols = ['Timestamp',
                 'Brug_rotatiex', 'Brug_rotatiey', 'Brug_rotatiez',
                 'water_level', 'pressure']

df_rot_env[rot_corr_cols].to_csv(
    'Bijlagen/Correlation_rotation_environmental.csv', index=False
)
print(f"Saved: Correlation_rotation_environmental.csv — {len(df_rot_env)} rows")