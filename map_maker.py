import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import json

# --- Config ---
st.set_page_config(page_title="Wafer Mapping Tool", layout="wide")
CANVAS_SIZE = 400  # pixels

# --- Initialize session state for non-widget state ---
if "canvas_reset_counter" not in st.session_state:
    st.session_state["canvas_reset_counter"] = 0
if "drawable_rects" not in st.session_state:
    st.session_state["drawable_rects"] = []

# --- Utility Functions ---
def is_inside_exclusion(x, y, zones):
    return any((x-ex[0])**2 + (y-ex[1])**2 <= ex[2]**2 for ex in zones)

def is_inside_rects(x, y, rects):
    return any((x >= rx and x <= rx + rw and y >= ry and y <= ry + rh)
               for (rx, ry, rw, rh) in rects)

def compute_points(
    wafer_diameter, edge_exclusion, grid_type, spacing_x, spacing_y,
    exclusion_zones, drawable_rects
):
    wafer_radius = wafer_diameter / 2
    points = []
    if grid_type == "Rectangular":
        x_range = np.arange(-wafer_radius + spacing_x/2, wafer_radius, spacing_x)
        y_range = np.arange(-wafer_radius + spacing_y/2, wafer_radius, spacing_y)
        for x in x_range:
            for y in y_range:
                r2 = x**2 + y**2
                if (
                    (r2 <= wafer_radius**2)
                    and (r2 <= (wafer_radius - edge_exclusion)**2)
                    and not is_inside_exclusion(x, y, exclusion_zones)
                    and not is_inside_rects(x, y, drawable_rects)
                ):
                    points.append((x, y))
    else:  # hexagonal
        x_range = np.arange(-wafer_radius + spacing_x/2, wafer_radius, spacing_x)
        for i, x in enumerate(x_range):
            offset = 0 if i % 2 == 0 else spacing_y / 2
            y_range = np.arange(-wafer_radius + spacing_y/2 + offset, wafer_radius, spacing_y)
            for y in y_range:
                r2 = x**2 + y**2
                if (
                    (r2 <= wafer_radius**2)
                    and (r2 <= (wafer_radius - edge_exclusion)**2)
                    and not is_inside_exclusion(x, y, exclusion_zones)
                    and not is_inside_rects(x, y, drawable_rects)
                ):
                    points.append((x, y))
    return np.array(points), len(points)

# --- Fetch all current values (always up-to-date via widget keys) ---
wafer_diameter = st.session_state.get('wafer_diameter', 80.0)
spot_size_x = st.session_state.get('spot_size_x', 0.4)
spot_size_y = st.session_state.get('spot_size_y', 0.4)
edge_exclusion = st.session_state.get('edge_exclusion', 1.0)
grid_type = st.session_state.get('grid_type', "Rectangular")
spacing_x = st.session_state.get('spacing_x', 2.0)
spacing_y = (st.session_state.get('spacing_y', 2.0)
             if grid_type == "Rectangular"
             else spacing_x * np.sqrt(3) / 2)
measurement_time = st.session_state.get('measurement_time', 10.0)
move_time = st.session_state.get('move_time', 1.0)
exclusion_zones = st.session_state.get('exclusion_zones', [])
drawable_rects = st.session_state.get('drawable_rects', [])

wafer_radius = wafer_diameter / 2

# --- Always display point/time estimate at the top ---
points, num_points = compute_points(
    wafer_diameter, edge_exclusion, grid_type, spacing_x, spacing_y,
    exclusion_zones, drawable_rects
)
total_time = num_points * (measurement_time + move_time)
st.info(
    f"**Measurement grid:** {num_points} points &mdash; "
    f"**Estimated total time:** {total_time/60:.2f} min ({total_time/3600:.2f} hr)  "
    f"&mdash; ({measurement_time:.1f}s per point + {move_time:.1f}s move)",
    icon="⏱️"
)

# --- UI Tabs ---
tabs = st.tabs([
    "1. Parameters",
    "2. Draw Rectangular Exclusions",
    "3. Visualization",
    "4. Coordinates"
])

with tabs[0]:
    st.header("Measurement & Grid Parameters")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Wafer & Spot")
        wafer_diameter = st.number_input(
            "Wafer diameter (mm)", value=wafer_diameter, min_value=1.0, key="wafer_diameter"
        )
        spot_size_x = st.number_input(
            "Spot width (mm)", value=spot_size_x, min_value=0.01, key="spot_size_x"
        )
        spot_size_y = st.number_input(
            "Spot height (mm)", value=spot_size_y, min_value=0.01, key="spot_size_y"
        )
        edge_exclusion = st.number_input(
            "Edge exclusion (distance to wafer edge, mm)",
            value=edge_exclusion, min_value=0.0,
            help="No grid points will be placed closer than this distance to the wafer edge.",
            key="edge_exclusion"
        )
    with c2:
        st.subheader("Grid")
        grid_type = st.selectbox("Grid pattern", options=["Rectangular", "Hexagonal"], key="grid_type")
        spacing_x = st.number_input(
            "Grid spacing X (mm)", value=spacing_x, min_value=0.01, key="spacing_x"
        )
        if grid_type == "Rectangular":
            spacing_y = st.number_input(
                "Grid spacing Y (mm)", value=spacing_y, min_value=0.01, key="spacing_y"
            )
        else:
            spacing_y = spacing_x * np.sqrt(3) / 2
            st.markdown(f"**Grid spacing Y:** `{spacing_y:.3f}` mm (hexagonal)")

        st.subheader("Timing")
        measurement_time = st.number_input(
            "Measurement time per point (s)", value=measurement_time, min_value=0.01,
            key="measurement_time"
        )
        move_time = st.number_input(
            "Move/settle overhead per point (s)", value=move_time, min_value=0.0,
            key="move_time"
        )

    # Circular Exclusion zones
    st.subheader("Circular Exclusion Zones")
    add_exclusions = st.checkbox("Add circular exclusion zones?", value=bool(exclusion_zones))
    new_exclusion_zones = []
    if add_exclusions:
        num_exclusions = st.number_input("Number of circular exclusion zones", min_value=1, max_value=10,
                                         value=len(exclusion_zones) or 1, key="num_circ_zones")
        ex_cols = st.columns(3)
        for i in range(int(num_exclusions)):
            with ex_cols[0]:
                ex_x = st.number_input(f"Center X (mm) [{i+1}]", value=exclusion_zones[i][0] if i < len(exclusion_zones) else 0.0, key=f"ex_x_{i}")
            with ex_cols[1]:
                ex_y = st.number_input(f"Center Y (mm) [{i+1}]", value=exclusion_zones[i][1] if i < len(exclusion_zones) else 0.0, key=f"ex_y_{i}")
            with ex_cols[2]:
                ex_r = st.number_input(f"Radius (mm) [{i+1}]", value=exclusion_zones[i][2] if i < len(exclusion_zones) else 5.0, min_value=0.1, key=f"ex_r_{i}")
            new_exclusion_zones.append((ex_x, ex_y, ex_r))
    # Save circular zones to session state (they are not directly widget keys)
    st.session_state['exclusion_zones'] = new_exclusion_zones

with tabs[1]:
    st.header("Draw Rectangular Exclusions on Live Wafer Map")
    wafer_diameter = st.session_state['wafer_diameter']
    edge_exclusion = st.session_state['edge_exclusion']
    grid_type = st.session_state['grid_type']
    spacing_x = st.session_state['spacing_x']
    spacing_y = (st.session_state['spacing_y']
                 if grid_type == "Rectangular"
                 else spacing_x * np.sqrt(3) / 2)
    exclusion_zones = st.session_state['exclusion_zones']
    wafer_radius = wafer_diameter / 2

    # Always generate wafer image just-in-time!
    points_for_bg, _ = compute_points(
        wafer_diameter, edge_exclusion, grid_type, spacing_x, spacing_y,
        exclusion_zones, []
    )
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    wafer_circle = plt.Circle((0, 0), wafer_radius, color='lightgray', fill=True, alpha=0.3)
    ax.add_patch(wafer_circle)
    if edge_exclusion > 0:
        edge_circle = plt.Circle((0, 0), wafer_radius - edge_exclusion, color='orange', fill=False, linestyle='--', linewidth=2, alpha=0.7)
        ax.add_patch(edge_circle)
    for ex in exclusion_zones:
        exc = plt.Circle((ex[0], ex[1]), ex[2], color='red', fill=True, alpha=0.2)
        ax.add_patch(exc)
    if points_for_bg.size > 0:
        ax.scatter(points_for_bg[:, 0], points_for_bg[:, 1], s=10, color='blue')
    ax.set_aspect('equal')
    ax.set_xlim(-wafer_radius-5, wafer_radius+5)
    ax.set_ylim(-wafer_radius-5, wafer_radius+5)
    ax.axis('off')
    fig.tight_layout(pad=0)
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0, dpi=100)
    buf.seek(0)
    bg_img = Image.open(buf).convert("RGB")
    plt.close(fig)

    c_reset, c_msg = st.columns([1, 8])
    with c_reset:
        if st.button("Reset Drawing Canvas"):
            st.session_state["canvas_reset_counter"] += 1
            st.rerun()
    with c_msg:
        st.info(
            "If the wafer image does not appear, click 'Reset Drawing Canvas'. "
            "If it *still* doesn't appear, try clearing your browser cache and reloading this page."
        )

    # *** Only the reset counter changes the key! ***
    canvas_key = f"canvas_{st.session_state['canvas_reset_counter']}"

    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.3)",
        stroke_width=3,
        background_image=bg_img,
        update_streamlit=True,
        height=CANVAS_SIZE,
        width=CANVAS_SIZE,
        drawing_mode="rect",
        key=canvas_key,
    )

    # Extract rectangles and save to session state
    drawable_rects = []
    if canvas_result.json_data is not None:
        for obj in canvas_result.json_data["objects"]:
            if obj["type"] == "rect":
                x = obj["left"] * wafer_diameter / CANVAS_SIZE - wafer_radius
                w = obj["width"] * wafer_diameter / CANVAS_SIZE
                h = obj["height"] * wafer_diameter / CANVAS_SIZE
                y_top_canvas = obj["top"] * wafer_diameter / CANVAS_SIZE
                y_flipped = wafer_diameter - y_top_canvas - h - wafer_radius
                drawable_rects.append((x, y_flipped, w, h))
    st.session_state['drawable_rects'] = drawable_rects

with tabs[2]:
    st.header("Visualization with All Exclusions")
    wafer_diameter = st.session_state['wafer_diameter']
    edge_exclusion = st.session_state['edge_exclusion']
    grid_type = st.session_state['grid_type']
    spacing_x = st.session_state['spacing_x']
    spacing_y = (st.session_state['spacing_y']
                 if grid_type == "Rectangular"
                 else spacing_x * np.sqrt(3) / 2)
    exclusion_zones = st.session_state['exclusion_zones']
    drawable_rects = st.session_state['drawable_rects']
    wafer_radius = wafer_diameter / 2

    points, num_points = compute_points(
        wafer_diameter, edge_exclusion, grid_type, spacing_x, spacing_y,
        exclusion_zones, drawable_rects
    )
    total_time = num_points * (st.session_state['measurement_time'] + st.session_state['move_time'])

    st.markdown(
        f"""
        **Number of measurement points:** `{num_points}`  
        **Estimated total time:** `{total_time/60:.2f}` min  (`{total_time/3600:.2f}` hr)
        """
    )

    fig, ax = plt.subplots(figsize=(6, 6))
    wafer_circle = plt.Circle((0, 0), wafer_radius, color='lightgray', fill=True, alpha=0.3, label='Wafer')
    ax.add_patch(wafer_circle)
    if edge_exclusion > 0:
        edge_circle = plt.Circle((0, 0), wafer_radius - edge_exclusion, color='orange', fill=False, linestyle='--', linewidth=2, alpha=0.7, label='Edge exclusion')
        ax.add_patch(edge_circle)
    for i, ex in enumerate(exclusion_zones):
        exc = plt.Circle((ex[0], ex[1]), ex[2], color='red', fill=True, alpha=0.2, label='Exclusion zone' if i==0 else None)
        ax.add_patch(exc)
    for i, (rx, ry, rw, rh) in enumerate(drawable_rects):
        rect_patch = plt.Rectangle(
            (rx, ry), rw, rh, color='red', fill=True, alpha=0.2, label='Rectangular zone' if i==0 else None
        )
        ax.add_patch(rect_patch)
    if points.size > 0:
        ax.scatter(points[:, 0], points[:, 1], color='blue', s=10, label='Measurement Points')
    ax.set_aspect('equal')
    ax.set_xlim(-wafer_radius-5, wafer_radius+5)
    ax.set_ylim(-wafer_radius-5, wafer_radius+5)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_title('Measurement Grid Map')
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys())
    st.pyplot(fig)

with tabs[3]:
    st.header("Coordinates & Download")
    if num_points > 0:
        df_coords = pd.DataFrame(points, columns=['X (mm)', 'Y (mm)'])
        st.dataframe(df_coords)
        csv = df_coords.to_csv(index=False)
        st.download_button("Download as CSV", csv, "wafer_coords.csv", "text/csv")
    else:
        st.warning("No points to show—check your parameters.")
