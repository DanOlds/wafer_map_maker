# Wafer Mapping Tool

A Streamlit web app for creating and visualizing measurement grids on circular wafers, with flexible exclusion zones and exportable coordinate lists.

## Features

- Interactive wafer grid generation (rectangular or hexagonal)
- Draw exclusion zones (circular or rectangular) directly on wafer image
- Visualize measurement points and exclusions
- Export measurement coordinates to CSV

## Installation

**This project uses [Pixi](https://pixi.sh) for environment management.**

1. **Clone the repository:**
    ```bash
    git clone https://github.com/DanOlds/wafer_map_maker.git
    cd wafer_map_maker
    ```

2. **Install Pixi:**
    ```bash
    curl -fsSL https://pixi.sh/install.sh | bash
    ```

3. **Create and activate the environment:**
    ```bash
    pixi install
    ```

## Usage

Run the Streamlit app:

```bash
pixi run streamlit run map_maker.py
