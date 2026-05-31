import streamlit as st
import requests
import re
import xml.etree.ElementTree as ET
from io import BytesIO

# --- HELPER FUNCTIONS ---

def get_drive_id(url):
    """Extracts the unique file ID from a Google Drive URL."""
    # This regular expression looks for the ID after '/d/' or 'id='
    match = re.search(r'(?:/d/|id=)([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def download_kml_from_drive(file_id):
    """Downloads the raw file content from Google Drive using the file ID."""
    download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
    response = requests.get(download_url)
    
    if response.status_code == 200:
        return response.content
    else:
        return None

def merge_kml_contents(kml_contents):
    """Merges multiple KML XML strings into a single KML structure."""
    # KML uses a specific XML namespace. We define it here so the output is valid.
    kml_ns = "http://www.opengis.net/kml/2.2"
    ET.register_namespace('', kml_ns)
    
    # Create the root structure for our new, merged KML
    root = ET.Element(f"{{{kml_ns}}}kml")
    merged_doc = ET.SubElement(root, f"{{{kml_ns}}}Document")
    
    name = ET.SubElement(merged_doc, f"{{{kml_ns}}}name")
    name.text = "Merged_KML_Data"

    # Loop through each downloaded KML file
    for content in kml_contents:
        try:
            # Parse the downloaded text into an XML tree
            tree = ET.fromstring(content)
            
            # Find the main <Document> tag in the source file
            source_doc = tree.find(f".//{{{kml_ns}}}Document")
            
            if source_doc is not None:
                # Append all children (like Placemarks, Folders) to our new merged document
                for child in source_doc:
                    # We skip copying the original document names to avoid clutter
                    if child.tag not in [f"{{{kml_ns}}}name", f"{{{kml_ns}}}description"]:
                        merged_doc.append(child)
            else:
                # If there's no <Document>, just grab everything inside the root <kml> tag
                for child in tree:
                    merged_doc.append(child)
        except Exception as e:
            st.warning(f"Failed to parse one of the files. Ensure it is a valid KML. Error: {e}")

    # Convert the XML tree back into a standard string
    return ET.tostring(root, encoding='utf-8', method='xml')


# --- STREAMLIT USER INTERFACE ---

st.set_page_config(page_title="KML Merger App", page_icon="🌍")

st.title("🌍 Google Drive KML Merger")
st.write("Paste your publicly viewable Google Drive KML links below (one per line). The app will download them, merge them into a single file, and let you download the result.")

# Text box for user input
urls_input = st.text_area("Google Drive URLs", height=150, placeholder="https://drive.google.com/file/d/1A2B3C4D5E6F/view?usp=sharing\nhttps://drive.google.com/file/d/7G8H9I0J/view?usp=sharing")

# Button to trigger the process
if st.button("Merge KMLs"):
    if not urls_input.strip():
        st.error("Please enter at least one URL.")
    else:
        # Split the text area input into a list of individual URLs
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        
        downloaded_contents = []
        
        with st.spinner("Downloading and merging files..."):
            for url in urls:
                file_id = get_drive_id(url)
                if file_id:
                    content = download_kml_from_drive(file_id)
                    if content:
                        downloaded_contents.append(content)
                        st.success(f"Successfully downloaded file ID: {file_id}")
                    else:
                        st.error(f"Failed to download file from URL: {url}. Make sure it is set to 'Anyone with the link can view'.")
                else:
                    st.error(f"Could not extract a valid Google Drive ID from: {url}")
            
            # If we successfully downloaded at least one file, proceed to merge
            if downloaded_contents:
                merged_xml = merge_kml_contents(downloaded_contents)
                
                st.success("Merging complete! You can download your file below.")
                
                # Provide the download button
                st.download_button(
                    label="Download Merged KML",
                    data=merged_xml,
                    file_name="merged_output.kml",
                    mime="application/vnd.google-earth.kml+xml"
                )
