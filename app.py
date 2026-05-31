import streamlit as st
import requests
import re
import xml.etree.ElementTree as ET

# --- HELPER FUNCTIONS ---

def get_drive_id(url):
    """Extracts the unique file ID from a Google Drive URL."""
    match = re.search(r'(?:/d/|id=)([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else None

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
st.write("Paste your publicly viewable Google Drive KML links below (one per line).")

urls_input = st.text_area("Google Drive URLs", height=150)

if st.button("Merge KMLs"):
    urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
    
    if not urls:
        st.warning("Please enter at least one URL.")
    else:
        downloaded_contents = []
        total_urls = len(urls)
        
        # Initialize the progress bar
        progress_bar = st.progress(0, text="Starting download...")
        
        for i, url in enumerate(urls):
            file_id = get_drive_id(url)
            if file_id:
                content = download_kml_from_drive(file_id)
                if content:
                    downloaded_contents.append(content)
            
            # Update progress bar dynamically
            progress_percentage = int(((i + 1) / total_urls) * 100)
            progress_bar.progress(progress_percentage, text=f"Processing files... {progress_percentage}%")
            
        if downloaded_contents:
            merged_xml = merge_kml_contents(downloaded_contents)
            
            # Clear the progress bar and show a single success message
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
            st.error("Could not process any of the provided URLs. Please ensure the links are public.")
