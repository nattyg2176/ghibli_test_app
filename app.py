import streamlit as st
import base64
import tempfile
import os
from PIL import Image
from openai import OpenAI

from supabase import create_client, Client

# Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(url, key)

# Login system
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            result = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["authenticated"] = True
            st.success("✅ Login successful!")
            st.experimental_rerun()
        except Exception as e:
            st.error("Login failed. Check your email or password.")
    st.stop()


# Load API key securely from Streamlit secrets
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# Streamlit UI setup
st.set_page_config(page_title="AI Image Stylizer", layout="centered")

# Custom CSS
st.markdown("""
    <style>
    select, button, [role="slider"], textarea, input {
        cursor: pointer !important;
    }
    .preview-img {
        width: 512px;
        height: 512px;
        object-fit: cover;
        border-radius: 12px;
    }
    .thumb {
        width: 150px;
        height: auto;
        border-radius: 8px;
        margin-bottom: 4px;
        cursor: pointer;
        transition: 0.3s;
        position: relative;
    }
    .thumb:hover {
        transform: scale(3);
        z-index: 999;
        position: relative;
        box-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    .thumb-block {
        overflow: visible !important;
    }
    .button-container {
        display: flex;
        gap: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎨 ArtifyAi")

# Upload image
uploaded_file = st.file_uploader("Upload an image (PNG, JPG, or WEBP)", type=["png", "jpg", "jpeg", "webp"], key="uploader")

encoded = ""
image_path = ""
if uploaded_file:
    with Image.open(uploaded_file) as im:
        im = im.convert("RGB")

        # Resize while keeping aspect ratio, then pad to 1024x1024 with black padding
        max_size = 1024
        im.thumbnail((max_size, max_size), Image.LANCZOS)
        background = Image.new("RGB", (max_size, max_size), (0, 0, 0))  # black padding
        offset = ((max_size - im.width) // 2, (max_size - im.height) // 2)
        background.paste(im, offset)
        im = background

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
            im.save(temp.name, format="PNG")
            image_path = temp.name
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
    st.markdown(f"<img class='preview-img' src='data:image/png;base64,{encoded}'/>", unsafe_allow_html=True)

style_options = [
    "None", "Ghibli", "Pixar", "Cyberpunk", "Watercolor", "Oil Painting", "Charcoal Sketch",
    "Cartoon", "Fantasy Art", "Impressionist", "Pop Art", "3D Render", "Photorealistic",
    "Minimalist", "Anime", "Steampunk", "Line Art", "Pixel Art", "Low Poly", "Graffiti", "Digital Painting"
]
style = st.selectbox("Choose a visual style:", options=style_options)
custom_prompt = st.text_input("Or type your own custom style prompt (optional):")

col1, col2 = st.columns(2)
with col1:
    background = st.selectbox("Background:", ["auto", "transparent", "opaque"])
    quality = st.selectbox("Image Quality:", ["auto", "high", "medium", "low"])
with col2:
    n = st.slider("How many images to generate?", min_value=1, max_value=10, value=1)
    size = st.selectbox("Image Size:", ["1024x1024", "1024x1536", "1536x1024", "auto"])

user_id = st.text_input("Optional User ID (for abuse monitoring):", "")

if uploaded_file and style and st.button("Stylize Image"):
    with st.spinner("Stylizing..."):
        prompt = custom_prompt.strip() if custom_prompt else (f"Make this image look like it's in the {style} style, but keep the same pose, background, and tattoo placement" if style != "None" else "Enhance this image while keeping the original style, pose, and composition")
        try:
            response = client.images.edit(
                model="gpt-image-1",
                image=[open(image_path, "rb")],
                prompt=prompt,
                background=background,
                quality=quality,
                n=n,
                size=size,
                user=user_id or None,
            )
            os.makedirs("image_library", exist_ok=True)
            for i, img_data in enumerate(response.data):
                img_bytes = base64.b64decode(img_data.b64_json)
                stylized_b64 = base64.b64encode(img_bytes).decode()

                st.markdown("### Result Preview")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"<img class='preview-img' src='data:image/png;base64,{encoded}'/>", unsafe_allow_html=True)
                    st.caption("Original")
                with col2:
                    st.markdown(f"<img class='preview-img' src='data:image/png;base64,{stylized_b64}'/>", unsafe_allow_html=True)
                    st.caption(f"Stylized - {style}" if not custom_prompt else "Custom Prompt Stylized")

                filename = f"styled_image_{len(os.listdir('image_library')) + 1}.png"
                file_path = os.path.join("image_library", filename)
                with open(file_path, "wb") as f:
                    f.write(img_bytes)

                st.download_button(
                    label=f"Download Image {i+1}",
                    data=img_bytes,
                    file_name=filename,
                    mime="image/png"
                )

        except Exception as e:
            st.error(f"⚠️ Style edit failed: {str(e)}")

# ---
# 🧪 Mix Two Uploaded Images

st.markdown("---")
st.subheader("🧪 Mix Two Uploaded Images")

mix_img1 = st.file_uploader("Upload Image 1 (e.g., a person)", type=["png", "jpg", "jpeg", "webp"], key="mix_img1")
mix_img2 = st.file_uploader("Upload Image 2 (e.g., an object)", type=["png", "jpg", "jpeg", "webp"], key="mix_img2")
mix_prompt = st.text_input("Describe how these two images should be combined:", placeholder="e.g., The woman is carrying the purse.")

if mix_img1:
    with Image.open(mix_img1) as im1:
        im1 = im1.convert("RGB")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp1:
            im1.save(temp1.name, format="PNG")
            with open(temp1.name, "rb") as f1:
                b64_1 = base64.b64encode(f1.read()).decode()
        st.markdown(f"<img class='preview-img' src='data:image/png;base64,{b64_1}'/>", unsafe_allow_html=True)

if mix_img2:
    with Image.open(mix_img2) as im2:
        im2 = im2.convert("RGB")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp2:
            im2.save(temp2.name, format="PNG")
            with open(temp2.name, "rb") as f2:
                b64_2 = base64.b64encode(f2.read()).decode()
        st.markdown(f"<img class='preview-img' src='data:image/png;base64,{b64_2}'/>", unsafe_allow_html=True)

if st.button("Combine Images"):
    if not (mix_img1 and mix_img2 and mix_prompt):
        st.warning("Please upload two images and enter a description.")
    else:
        with st.spinner("Generating combined image..."):
            try:
                combined_paths = []
                for mix in [mix_img1, mix_img2]:
                    with Image.open(mix) as im:
                        im = im.convert("RGB")
                        im.thumbnail((1024, 1024), Image.LANCZOS)
                        bg = Image.new("RGB", (1024, 1024), (0, 0, 0))
                        offset = ((1024 - im.width) // 2, (1024 - im.height) // 2)
                        bg.paste(im, offset)
                        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        bg.save(temp.name, format="PNG")
                        combined_paths.append(temp.name)

                response = client.images.edit(
                    model="gpt-image-1",
                    image=[open(p, "rb") for p in combined_paths],
                    prompt=mix_prompt,
                    n=1,
                    size="1024x1024",
                    background="auto",
                    quality="auto",
                )

                img_base64 = response.data[0].b64_json
                img_bytes = base64.b64decode(img_base64)
                b64_img = base64.b64encode(img_bytes).decode()
                st.markdown(f"<img class='preview-img' src='data:image/png;base64,{b64_img}'/>", unsafe_allow_html=True)
                os.makedirs("image_library", exist_ok=True)
                filename = f"mixed_image_{len(os.listdir('image_library')) + 1}.png"
                with open(f"image_library/{filename}", "wb") as f:
                    f.write(img_bytes)
                st.download_button(
                    label="Download Mixed Image",
                    data=img_bytes,
                    file_name=filename,
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"⚠️ Failed to combine images: {str(e)}")

# Text-to-image generator
st.markdown("---")
st.subheader("🎨 Create an Image from Text Prompt")

text_prompt = st.text_area("Describe the image you want to create:")
style_option = st.selectbox("Choose a visual style:", ["None", "Ghibli", "Pixar", "Watercolor", "Cyberpunk", "Oil Painting", "Sketch"])

if text_prompt and st.button("Generate Image"):
    with st.spinner("Generating..."):
        final_prompt = f"{text_prompt.strip()} in {style_option} style" if style_option != "None" else text_prompt.strip()
        response = client.images.generate(
            model="gpt-image-1",
            prompt=final_prompt,
            n=1,
            size="1024x1024",
        )
        img_base64 = response.data[0].b64_json
        img_bytes = base64.b64decode(img_base64)
        b64_img = base64.b64encode(img_bytes).decode()
        st.markdown(f"<img class='preview-img' src='data:image/png;base64,{b64_img}'/>", unsafe_allow_html=True)
        os.makedirs("image_library", exist_ok=True)
        filename = f"generated_image_{len(os.listdir('image_library')) + 1}.png"
        with open(f"image_library/{filename}", "wb") as f:
            f.write(img_bytes)
        st.download_button(
            label="Download Image",
            data=img_bytes,
            file_name=filename,
            mime="image/png"
        )

# Show image library
st.markdown("---")
st.subheader("🖼 Your Image Library")

if os.path.exists("image_library"):
    image_files = [f for f in sorted(os.listdir("image_library")) if f.endswith(".png")]
    if not image_files:
        st.info("Your image library is empty.")
    else:
        IMAGES_PER_ROW = 4
        for i in range(0, len(image_files), IMAGES_PER_ROW):
            row_files = image_files[i : i + IMAGES_PER_ROW]
            cols = st.columns(len(row_files))
            for col_index, file_name in enumerate(row_files):
                with cols[col_index]:
                    st.markdown("<div class='thumb-block'>", unsafe_allow_html=True)
                    file_path = os.path.join("image_library", file_name)
                    try:
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                            b64_encoded_image = base64.b64encode(file_bytes).decode()
                        st.markdown(
                            f"<img class='thumb' src='data:image/png;base64,{b64_encoded_image}'/>",
                            unsafe_allow_html=True
                        )
                        st.markdown("<div class='button-container'>", unsafe_allow_html=True)
                        download_key = f"download_{file_name.replace('.', '_')}_{i}_{col_index}"
                        st.download_button(
                            label="⬇️ Download",
                            data=file_bytes,
                            file_name=file_name,
                            mime="image/png",
                            key=download_key
                        )
                        button_key = f"delete_{file_name.replace('.', '_')}_{i}_{col_index}"
                        if st.button(f"🗑 Delete", key=button_key):
                            try:
                                os.remove(file_path)
                                st.rerun()
                            except Exception as e_del:
                                st.error(f"Error deleting {file_name}: {e_del}")
                        st.markdown("</div>", unsafe_allow_html=True)
                    except FileNotFoundError:
                        st.error(f"Image file not found: {file_name}")
                    except Exception as e_load:
                        st.error(f"Error loading/processing {file_name}: {e_load}")
                    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("The image library folder ('image_library') does not exist.")
