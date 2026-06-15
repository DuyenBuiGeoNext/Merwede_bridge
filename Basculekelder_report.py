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
# Save raw extracted data to CSV — one file per dataset, before any cleaning
CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv_exports")
os.makedirs(CSV_DIR, exist_ok=True)
for table, df in data.items():
    path = os.path.join(CSV_DIR, f"{table}_raw.csv")
    df.to_csv(path, index=False)
    print(f"Saved raw data: {path}  ({len(df)} rows)")

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

def remove_outliers_iqr(df, cols=None, multiplier=4):
    """
    Replaces outliers with NaN using the IQR method.
    Any value outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR] is set to NaN.
    The original row is kept — only the outlying value is masked.

    Args:
        df          (pd.DataFrame) - input data
        cols        (list of str)  - columns to clean; if None, all numeric columns are used
        multiplier  (float)        - IQR multiplier for the bounds (default 4, same as pijler report)

    Returns:
        pd.DataFrame - copy with outliers replaced by NaN
    """
    df = df.copy()
    if cols is None:
        cols = df.select_dtypes(include='number').columns.tolist()
    for col in cols:
        Q1    = df[col].quantile(0.25)
        Q3    = df[col].quantile(0.75)
        IQR   = Q3 - Q1
        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR
        before = df[col].notna().sum()
        df[col] = df[col].where((df[col] >= lower) & (df[col] <= upper), np.nan)
        after  = df[col].notna().sum()
        print(f"  {col}: {before - after} outlier(s) removed  (bounds [{lower:.3f}, {upper:.3f}])")
    return df

def split_on_gaps(df, timestamp_col='Timestamp', gap_days=2):
    """
    Splits a DataFrame into continuous segments wherever consecutive rows
    are more than gap_days apart. Returns a list of DataFrames, one per segment.
    Segments separated by a gap > gap_days are kept independent so that
    plots do not draw a connecting line across the missing period.

    Args:
        df           (pd.DataFrame) - input data
        timestamp_col (str)         - name of the datetime column
        gap_days      (int/float)   - gap threshold in days

    Returns:
        list of pd.DataFrame - one DataFrame per continuous segment
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    df = df.sort_values(timestamp_col).reset_index(drop=True)

    gap_mask   = df[timestamp_col].diff() > pd.Timedelta(days=gap_days)
    segment_ids = gap_mask.cumsum()

    segments = [segment.reset_index(drop=True) for _, segment in df.groupby(segment_ids)]
    print(f"Found {len(segments)} continuous segment(s) with gap threshold = {gap_days} days.")
    return segments

# %%
# Remove outliers from all numeric columns using 4×IQR bounds
print("Removing outliers from Basculekelder:")
df_Basculekelder_clean = remove_outliers_iqr(df_Basculekelder)

# Split on time gaps — used for xlims, gap period detection and environmental filtering
df_Basculekelder_segments = split_on_gaps(df_Basculekelder_clean, timestamp_col='Timestamp', gap_days=5)

def split_and_offset(segments, jump_threshold=2.0, center_threshold=1.0, timestamp_col='Timestamp'):
    """
    For each time segment:
      1. Splits further wherever any column's consecutive difference exceeds jump_threshold (mm).
      2. For each resulting sub-segment, checks each column's mean independently:
         - If |mean| > center_threshold → subtracts the mean (centers around 0).
         - If |mean| <= center_threshold → leaves the column unchanged (already near 0).

    Args:
        segments         (list of pd.DataFrame) - output of split_on_gaps()
        jump_threshold   (float) - consecutive-difference threshold to create a new segment (mm)
        center_threshold (float) - if |segment mean| exceeds this, the column is offset to 0 (mm)
        timestamp_col    (str)   - name of the datetime column

    Returns:
        pd.DataFrame - all sub-segments concatenated with selective offsets applied
    """
    value_cols = [
        c for c in segments[0].columns
        if c != timestamp_col and pd.api.types.is_numeric_dtype(segments[0][c])
    ]

    all_sub_segs = []
    for seg in segments:
        seg = seg.copy().sort_values(timestamp_col).reset_index(drop=True)

        # Step 1 — split on jumps > jump_threshold
        jump_mask = pd.Series(False, index=seg.index)
        for col in value_cols:
            jump_mask = jump_mask | (seg[col].diff().abs() > jump_threshold)
        sub_segs = [grp.reset_index(drop=True)
                    for _, grp in seg.groupby(jump_mask.cumsum())]
        if len(sub_segs) > 1:
            print(f"  Jump split (>{jump_threshold}mm): {len(sub_segs) - 1} jump(s)")

        # Step 2 — offset only sub-segments whose column mean is far from 0
        for sub in sub_segs:
            sub = sub.copy()
            for col in value_cols:
                col_mean = sub[col].mean()
                if pd.notna(col_mean) and abs(col_mean) > center_threshold:
                    sub[col] = sub[col] - col_mean
                    print(f"    Offset '{col}': mean was {col_mean:.3f}mm → centered to 0")
            all_sub_segs.append(sub)

    result = pd.concat(all_sub_segs, ignore_index=True)
    print(f"Processed {len(all_sub_segs)} sub-segment(s) → {len(result)} rows total.")
    return result

print("Applying jump split and selective zero-centering:")
df_Basculekelder_processed = split_and_offset(
    df_Basculekelder_segments,
    jump_threshold=2.0,
    center_threshold=1.0,
)

# %%
df_Basculekelder_clean['Timestamp'] = pd.to_datetime(df_Basculekelder_clean['Timestamp'])
with pd.option_context('display.max_rows', None):
    print(df_Basculekelder_clean['Timestamp'])
date_min = df_Basculekelder_clean['Timestamp'].min()
date_max = df_Basculekelder_clean['Timestamp'].max()

print(f"Basculekelder time range after cleaning: {date_min.date()} → {date_max.date()}")

def get_gap_periods_from_segments(segments, timestamp_col='Timestamp'):
    """
    Derives gap periods from a list of continuous segments.
    A gap is the interval between the end of one segment and the start of the next.

    Args:
        segments      (list of pd.DataFrame) - output of split_on_gaps()
        timestamp_col (str)                  - name of the datetime column

    Returns:
        list of (start, end) Timestamp tuples — one per gap between segments
    """
    gaps = []
    for i in range(len(segments) - 1):
        gap_start = segments[i][timestamp_col].max()
        gap_end   = segments[i + 1][timestamp_col].min()
        gaps.append((gap_start, gap_end))
        print(f"  Gap {i + 1}: {gap_start.date()} → {gap_end.date()}")
    return gaps

def trim_to_range(df, timestamp_col, t_min, t_max):
    """
    Keeps only rows where timestamp_col falls within [t_min, t_max].

    Args:
        df            (pd.DataFrame) - input data
        timestamp_col (str)          - name of the datetime column
        t_min         (Timestamp)    - start of the allowed range (inclusive)
        t_max         (Timestamp)    - end of the allowed range (inclusive)

    Returns:
        pd.DataFrame - filtered copy, index reset
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    mask = (df[timestamp_col] >= t_min) & (df[timestamp_col] <= t_max)
    result = df[mask].reset_index(drop=True)
    print(f"  Trimmed to {len(result)} rows ({t_min.date()} → {t_max.date()})")
    return result

def remove_gap_periods(df, timestamp_col, gap_periods):
    """
    Removes rows whose timestamp falls inside any of the given gap periods.
    Gap boundaries are excluded (strict inequality), so the last point before
    a gap and the first point after are retained.

    Args:
        df            (pd.DataFrame)              - input data
        timestamp_col (str)                       - name of the datetime column
        gap_periods   (list of (start, end) pairs) - output of get_gap_periods_from_segments()

    Returns:
        pd.DataFrame - filtered copy with gap rows removed, index reset
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    before = len(df)
    for gap_start, gap_end in gap_periods:
        in_gap = (df[timestamp_col] > gap_start) & (df[timestamp_col] < gap_end)
        df = df[~in_gap]
    df = df.reset_index(drop=True)
    print(f"  Removed {before - len(df)} rows falling in gap periods → {len(df)} rows remain")
    return df

# Derive gap periods directly from the Basculekelder segments
print("Detected gap periods in Basculekelder data:")
gap_periods = get_gap_periods_from_segments(df_Basculekelder_segments)

# Step 1 — trim to the overall Basculekelder time range
print("Trimming environmental data to overall range:")
df_waterlevel_plot = trim_to_range(df_waterlevel, 'Timestamp', date_min, date_max)
df_weer1_plot      = trim_to_range(df_weer1,      'Timestamp', date_min, date_max)
df_weer2_plot      = trim_to_range(df_weer2,      'Timestamp', date_min, date_max)

# Step 2 — remove rows that fall inside the detected gap periods
print("Removing environmental data within gap periods:")
df_waterlevel_plot = remove_gap_periods(df_waterlevel_plot, 'Timestamp', gap_periods)
df_weer1_plot      = remove_gap_periods(df_weer1_plot,      'Timestamp', gap_periods)
df_weer2_plot      = remove_gap_periods(df_weer2_plot,      'Timestamp', gap_periods)

# %%
def average_to_basculekelder(df_env, df_bask, timestamp_col='Timestamp', window_hours=4):
    """
    For each Basculekelder timestamp T, computes the mean of all environmental
    rows whose timestamp falls in the half-open window (T - window_hours, T].
    Returns a DataFrame with one row per Basculekelder timestamp.

    Args:
        df_env        (pd.DataFrame) - environmental data (waterlevel, temperature, etc.)
        df_bask       (pd.DataFrame) - Basculekelder data; its Timestamp column is the anchor
        timestamp_col (str)          - name of the datetime column in both DataFrames
        window_hours  (int/float)    - size of the averaging window in hours (default 4)

    Returns:
        pd.DataFrame - one row per Basculekelder timestamp, numeric columns are 4-hour means
    """
    df_env  = df_env.copy().sort_values(timestamp_col).reset_index(drop=True)
    anchors = df_bask[timestamp_col].sort_values().reset_index(drop=True)

    rows = []
    for ts in anchors:
        window_start = ts - pd.Timedelta(hours=window_hours)
        # print("window start", window_start)
        # print("window end", ts)
        mask = (df_env[timestamp_col] > window_start) & (df_env[timestamp_col] <= ts)
        window_data = df_env.loc[mask]
        # print(window_data)
        if not window_data.empty:
            averaged = window_data.drop(columns=[timestamp_col]).mean(numeric_only=True)
            averaged[timestamp_col] = ts
            rows.append(averaged)
            # print("last row", rows[-1])

    value_cols = [c for c in df_env.columns if c != timestamp_col]
    result = pd.DataFrame(rows)[[timestamp_col] + value_cols].reset_index(drop=True)
    print(f"  Averaged to {len(result)} rows aligned with Basculekelder timestamps")
    return result

print("Averaging environmental data to Basculekelder 4-hour blocks:")
df_waterlevel_avg = average_to_basculekelder(df_waterlevel_plot, df_Basculekelder_clean)
df_weer1_avg      = average_to_basculekelder(df_weer1_plot,      df_Basculekelder_clean)
df_weer2_avg      = average_to_basculekelder(df_weer2_plot,      df_Basculekelder_clean)

# %%
def get_xlims_from_segments(segments, timestamp_col='Timestamp', padding_days=1):
    """
    Builds the xlims tuple required by brokenaxes from a list of segment DataFrames.
    Each segment becomes one x-axis panel. A small padding is added on each side
    so data points are not cut off at the panel edges.

    Args:
        segments      (list of pd.DataFrame) - output of split_on_gaps()
        timestamp_col (str)                  - name of the datetime column
        padding_days  (int/float)            - padding added to each side in days

    Returns:
        tuple of (start, end) Timestamp pairs — one pair per segment
    """
    padding = pd.Timedelta(days=padding_days)
    return tuple(
        (seg[timestamp_col].min() - padding, seg[timestamp_col].max() + padding)
        for seg in segments
    )

def style_bax(bax, ylabel, title, fontsize=18):
    """
    Applies consistent styling to a brokenaxes object:
    axis labels, grid, tick formatting, and a zero reference line.

    Args:
        bax      (brokenaxes) - the brokenaxes object to style
        ylabel   (str)        - label for the y-axis
        title    (str)        - panel title shown above the first x segment
        fontsize (int)        - base font size (default 18)
    """
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
# Build xlims from the cleaned segments for use with brokenaxes
xlims = get_xlims_from_segments(df_Basculekelder_segments)
print(f"X-axis segments: {[(str(a.date()), str(b.date())) for a, b in xlims]}")

# %%
# --- Rotation plot ---
rotation_cols = [
    ('Brug_rotatiex', 'Rotation X', '#378ADD'),
    ('Brug_rotatiey', 'Rotation Y', '#D85A30'),
    ('Brug_rotatiez', 'Rotation Z', '#1D9E75'),
]

t = df_Basculekelder_processed['Timestamp']

fig = plt.figure(figsize=(16, 14))
fig.suptitle('XYZ rotations — Basculekelder', fontsize=20, fontweight='bold', y=1.01)

for i, (col, title, color) in enumerate(rotation_cols):
    bax = brokenaxes(
        xlims=xlims,
        subplot_spec=plt.GridSpec(3, 1, hspace=0.55)[i],
        fig=fig,
        d=0.008,
        tilt=70,
    )
    bax.plot(t, df_Basculekelder_processed[col], color=color, linewidth=2.0, label=col)
    style_bax(bax, 'mm', title)
    bax.legend(fontsize=13, loc='upper left')

plt.savefig('Basculekelder_rotations.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
def save_table_as_png(df, title, filename):
    """
    Renders a pandas DataFrame as a styled table and saves it as a PNG image.

    Args:
        df       (pd.DataFrame) - data to display; columns become headers
        title    (str)          - title shown above the table
        filename (str)          - output file path, e.g. 'rotation_stats.png'
    """
    n_rows, n_cols = df.shape
    fig_height = 0.5 + n_rows * 0.5 + 1.0
    ax = plt.subplots(figsize=(14, fig_height))[1]
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
    print(f"Saved: {filename}")

# %%
# --- Rotation statistics ---
rotation_stats = []
for col, label, _color in rotation_cols:
    series = df_Basculekelder_processed[col].dropna()
    rotation_stats.append({
        'Sensor':      label,
        'Unit':        'mm',
        'Min':         f"{series.min():.3f}",
        'Max':         f"{series.max():.3f}",
        'Mean':        f"{series.mean():.3f}",
        'Std dev (σ)': f"{series.std():.3f}",
    })

df_rot_stats = pd.DataFrame(rotation_stats)
print(df_rot_stats)

save_table_as_png(
    df_rot_stats,
    'Summary statistics — XYZ rotations (Basculekelder)',
    'Basculekelder_rotation_stats.png'
)

# %%
# Apply IQR outlier removal to temperature columns in the trimmed weather data
df_weer1_plot = remove_outliers_iqr(df_weer1_plot, cols=['Temperature'])
df_weer2_plot = remove_outliers_iqr(df_weer2_plot, cols=['Temperature'])

# %%
# --- Environmental conditions plot: water pressure, water level, temperature ---
t_wl  = df_waterlevel_plot['Timestamp']
t_w1  = df_weer1_plot['Timestamp']
t_w2  = df_weer2_plot['Timestamp']

env_panels = [
    ('pressure',    'kPa',  'Water pressure'),
    ('water_level', 'm NAP','Water level'),
    ('temperature', '°C',   'Temperature'),
]

fig = plt.figure(figsize=(16, 14))
fig.suptitle('Environmental conditions — Merwedebrug', fontsize=20, fontweight='bold', y=1.01)
grid = plt.GridSpec(3, 1, hspace=0.55)

# Panel 0 — water pressure
bax0 = brokenaxes(xlims=xlims, subplot_spec=grid[0], fig=fig, d=0.008, tilt=70)
bax0.plot(t_wl, df_waterlevel_plot['pressure'], color='#378ADD', linewidth=2.0, label='Pressure')
style_bax(bax0, 'kPa', 'Water pressure')
bax0.legend(fontsize=13, loc='upper left')

# Panel 1 — water level
bax1 = brokenaxes(xlims=xlims, subplot_spec=grid[1], fig=fig, d=0.008, tilt=70)
bax1.plot(t_wl, df_waterlevel_plot['water_level'], color='#1D9E75', linewidth=2.0, label='Water level')
style_bax(bax1, 'm NAP', 'Water level')
bax1.legend(fontsize=13, loc='upper left')

# Panel 2 — temperature (both stations)
bax2 = brokenaxes(xlims=xlims, subplot_spec=grid[2], fig=fig, d=0.008, tilt=70)
bax2.plot(t_w1, df_weer1_plot['Temperature'], color='#D85A30', linewidth=2.0, label='Weerstation 1')
bax2.plot(t_w2, df_weer2_plot['Temperature'], color='#9B59B6', linewidth=2.0, linestyle='--', label='Weerstation 2')
style_bax(bax2, '°C', 'Temperature')
bax2.legend(fontsize=13, loc='upper left')

plt.savefig('Basculekelder_environmental.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Displacement plot ---
# Each panel shows one displacement direction; Delta X and Delta Z have two
# measurement points (Brugpunt 1 and 2), Delta Y has one.
# Uses stitched data so each segment continues from where the previous ended.
t = df_Basculekelder_processed['Timestamp']

displacement_panels = [
    ('Brugpunt1_deltax', 'Brugpunt2_deltax', 'Delta X', '#378ADD'),
    ('delta_y',           None,               'Delta Y', '#D85A30'),
    ('Brugpunt1_deltaz', 'Brugpunt2_deltaz', 'Delta Z', '#1D9E75'),
]

fig = plt.figure(figsize=(16, 14))
fig.suptitle('XYZ displacements — Basculekelder', fontsize=20, fontweight='bold', y=1.01)
grid = plt.GridSpec(3, 1, hspace=0.55)

for i, (col1, col2, title, color) in enumerate(displacement_panels):
    bax = brokenaxes(xlims=xlims, subplot_spec=grid[i], fig=fig, d=0.008, tilt=70)
    bax.plot(t, df_Basculekelder_processed[col1], color=color, linewidth=2.0, label='Brugpunt 1')
    if col2:
        bax.plot(t, df_Basculekelder_processed[col2], color=color, linewidth=2.0,
                 linestyle='--', label='Brugpunt 2')
    style_bax(bax, 'mm', title)
    bax.legend(fontsize=13, loc='upper left')

plt.savefig('Basculekelder_displacements.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Displacement statistics ---
displacement_definitions = [
    ('Brugpunt1_deltax', 'Delta X — Brugpunt 1', 'mm'),
    ('Brugpunt2_deltax', 'Delta X — Brugpunt 2', 'mm'),
    ('delta_y',          'Delta Y',               'mm'),
    ('Brugpunt1_deltaz', 'Delta Z — Brugpunt 1', 'mm'),
    ('Brugpunt2_deltaz', 'Delta Z — Brugpunt 2', 'mm'),
]

displacement_stats = []
for col, label, unit in displacement_definitions:
    series = df_Basculekelder_processed[col].dropna()
    displacement_stats.append({
        'Sensor':      label,
        'Unit':        unit,
        'Min':         f"{series.min():.3f}",
        'Max':         f"{series.max():.3f}",
        'Mean':        f"{series.mean():.3f}",
        'Std dev (σ)': f"{series.std():.3f}",
    })

df_disp_stats = pd.DataFrame(displacement_stats)
print(df_disp_stats)

save_table_as_png(
    df_disp_stats,
    'Summary statistics — XYZ displacements (Basculekelder)',
    'Basculekelder_displacement_stats.png'
)

# %%
# --- Merge structural and averaged environmental data ---
# All averaged DataFrames share the same Timestamp values as df_Basculekelder_clean
# so an exact merge on Timestamp is sufficient.
df_merged = pd.merge(
    df_Basculekelder_processed,
    df_waterlevel_avg[['Timestamp', 'pressure', 'water_level']],
    on='Timestamp', how='inner'
)
df_merged = pd.merge(
    df_merged,
    df_weer1_avg[['Timestamp', 'Temperature']].rename(columns={'Temperature': 'Temp_w1'}),
    on='Timestamp', how='inner'
)
df_merged = pd.merge(
    df_merged,
    df_weer2_avg[['Timestamp', 'Temperature']].rename(columns={'Temperature': 'Temp_w2'}),
    on='Timestamp', how='inner'
)
# Average temperature from both stations into one column
df_merged['Temperature'] = df_merged[['Temp_w1', 'Temp_w2']].mean(axis=1)
df_merged = df_merged.drop(columns=['Temp_w1', 'Temp_w2'])
df_merged = df_merged.dropna(subset=['pressure', 'water_level', 'Temperature'])
print(f"Merged dataset for correlation: {len(df_merged)} rows")

# %%
# --- Scatter plots: displacement vs environmental variables ---
disp_cols = [
    ('Brugpunt1_deltax', 'Delta X — Brugpunt 1 (mm)'),
    ('Brugpunt2_deltax', 'Delta X — Brugpunt 2 (mm)'),
    ('delta_y',          'Delta Y (mm)'),
    ('Brugpunt1_deltaz', 'Delta Z — Brugpunt 1 (mm)'),
    ('Brugpunt2_deltaz', 'Delta Z — Brugpunt 2 (mm)'),
]

env_cols = [
    ('pressure',    'Water pressure (kPa)'),
    ('water_level', 'Water level (m NAP)'),
    ('Temperature', 'Temperature (°C)'),
]

colors_disp = ['#378ADD', '#1A5FA8', '#D85A30', '#1D9E75', '#0F6B50']

fig, axes = plt.subplots(len(disp_cols), len(env_cols), figsize=(18, 20))
fig.suptitle('Correlation — displacements vs environmental conditions',
             fontsize=18, fontweight='bold')

for row, (s_col, s_label) in enumerate(disp_cols):
    for col, (e_col, e_label) in enumerate(env_cols):
        ax = axes[row, col]
        valid = df_merged[[s_col, e_col]].dropna()
        ax.scatter(valid[e_col], valid[s_col],
                   color=colors_disp[row], alpha=0.4, s=25, linewidths=0)
        if len(valid) > 2:
            z = np.polyfit(valid[e_col], valid[s_col], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid[e_col].min(), valid[e_col].max(), 100)
            r = valid[s_col].corr(valid[e_col])
            ax.plot(x_line, p(x_line), color='black', linewidth=2.0,
                    linestyle='--', label=f'R = {r:.2f}')
        ax.set_xlabel(e_label, fontsize=13)
        ax.set_ylabel(s_label, fontsize=13)
        ax.tick_params(axis='both', labelsize=11)
        ax.grid(True, alpha=0.3, linewidth=0.8)
        ax.legend(fontsize=11)

plt.tight_layout()
plt.savefig('Basculekelder_correlation_displacement.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# --- Scatter plots: rotation vs environmental variables ---
rot_cols = [
    ('Brug_rotatiex', 'Rotation X (mm)'),
    ('Brug_rotatiey', 'Rotation Y (mm)'),
    ('Brug_rotatiez', 'Rotation Z (mm)'),
]

colors_rot = ['#378ADD', '#D85A30', '#1D9E75']

fig, axes = plt.subplots(len(rot_cols), len(env_cols), figsize=(18, 14))
fig.suptitle('Correlation — rotations vs environmental conditions',
             fontsize=18, fontweight='bold')

for row, (s_col, s_label) in enumerate(rot_cols):
    for col, (e_col, e_label) in enumerate(env_cols):
        ax = axes[row, col]
        valid = df_merged[[s_col, e_col]].dropna()
        ax.scatter(valid[e_col], valid[s_col],
                   color=colors_rot[row], alpha=0.4, s=25, linewidths=0)
        if len(valid) > 2:
            z = np.polyfit(valid[e_col], valid[s_col], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid[e_col].min(), valid[e_col].max(), 100)
            r = valid[s_col].corr(valid[e_col])
            ax.plot(x_line, p(x_line), color='black', linewidth=2.0,
                    linestyle='--', label=f'R = {r:.2f}')
        ax.set_xlabel(e_label, fontsize=13)
        ax.set_ylabel(s_label, fontsize=13)
        ax.tick_params(axis='both', labelsize=11)
        ax.grid(True, alpha=0.3, linewidth=0.8)
        ax.legend(fontsize=11)

plt.tight_layout()
plt.savefig('Basculekelder_correlation_rotation.png', dpi=150, bbox_inches='tight')
plt.show()
# %%
