import streamlit as st
from PIL import Image, ImageDraw
from streamlit_drawable_canvas import st_canvas

# Create a 400x400 red image with a black circle in the center
img = Image.new("RGB", (400, 400), "red")
draw = ImageDraw.Draw(img)
draw.ellipse((100, 100, 300, 300), fill="black")

st.image(img, caption="DEBUG: Static image")
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.3)",
    stroke_width=3,
    background_image=img,
    update_streamlit=True,
    height=400,
    width=400,
    drawing_mode="rect",
    key="canvas",
)
