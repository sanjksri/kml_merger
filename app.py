import streamlit as st
import requests
import re
import xml.etree.ElementTree as ET

# --- HELPER FUNCTIONS ---

def get_drive_id(input_string):
    """Extracts the file ID from a URL, or returns the ID if provided directly."""
    # First, check if the input contains a typical Google Drive URL structure
    match = re.search(r'(?:/d/|id=)([a-zA-Z0-9_-]+)', input_string)
    if match:
        return match.group(1)
    
    # If not a URL, check if the string itself looks like a valid Drive ID
    # Google Drive IDs are typically long strings of letters, numbers, hyphens, and underscores.
    if re.match(r'^[a-zA-Z0-9_-]{15,}$', input_string):
        return input_string
        
    # If it matches neither, it's invalid
    return None

def download_kml_from_drive(file_id):
    """Downloads the raw file content from Google Drive."""
    download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
    response = requests.get(download_url)
    return response.content if response.status_code == 200 else None

def merge_kml_contents(kml_contents):
    """Merges multiple KML XML strings into a single KML structure."""
    kml_ns = "http://www.opengis.net/kml/2.2"
    ET.register_namespace('', kml_ns)
    
    root = ET.Element(f"{{{kml_ns}}}kml")
    merged_doc = ET.SubElement(root, f"{{{kml_ns}}}Document")
    
    name = ET.SubElement(merged_doc, f"{{{kml_ns}}}name")
    name.text = "Merged_KML_Data"

    for content in kml_contents:
        try:
            tree = ET.fromstring(content)
            source_doc = tree.find(f".//{{{kml_ns}}}Document")
            
            if source_doc is not None:
                for child in source_doc:
                    if child.tag not in [f"{{{kml_ns}}}name", f"{{{kml_ns}}}description"]:
                        merged_doc.append(child)
            else:
                for child in tree:
                    merged_doc.append(child)
        except Exception:
            # Silently pass over files that fail to parse to keep the UI clean
            pass

    return ET.tostring(root, encoding='utf-8', method='xml')


# --- STREAMLIT USER INTERFACE ---

st.set_page_config(page_title="KML Merger App", page_icon="🌍")

st.title("🌍 Google Drive KML Merger")
st.write("Paste your publicly viewable Google Drive KML **links** or **File IDs** below (one per line).")

urls_input = st.text_area("Google Drive URLs or IDs", height=150)

if st.button("Merge KMLs"):
    inputs = [line.strip() for line in urls_input.split('\n') if line.strip()]
    
    if not inputs:
        st.warning("Please enter at least one URL or File ID.")
    else:
        downloaded_contents = []
        total_inputs = len(inputs)
        
        progress_bar = st.progress(0, text="Starting download...")
        
        for i, user_input in enumerate(inputs):
            file_id = get_drive_id(user_input)
            if file_id:
                content = download_kml_from_drive(file_id)
                if content:
                    downloaded_contents.append(content)
            
            # Update progress bar dynamically
            progress_percentage = int(((i + 1) / total_inputs) * 100)
            progress_bar.progress(progress_percentage, text=f"Processing files... {progress_percentage}%")
            
        if downloaded_contents:
            merged_xml = merge_kml_contents(downloaded_contents)
            
            progress_bar.empty()
            st.success("Merging complete!")
            
            st.download_button(
                label="Download Merged KML",
                data=merged_xml,
                file_name="merged_output.kml",
                mime="application/vnd.google-earth.kml+xml"
            )
        else:
            progress_bar.empty()
            st.error("Could not process any of the provided inputs. Please ensure the links/IDs are public and valid.")
