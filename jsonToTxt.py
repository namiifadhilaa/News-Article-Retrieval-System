import os
import json

# Directory containing JSON files
directory_path = './data'
output_directory = os.path.join(directory_path, 'output_txt_files')

# Create output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)

# Function to extract title and article content from a JSON file and save to a TXT file
def extract_and_save_to_txt(file_path, output_directory):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        article_content = data.get('article', {}).get('article', 'No Content')

    # Create a TXT file with the same name as the JSON file
    base_filename = os.path.basename(file_path)
    txt_filename = os.path.splitext(base_filename)[0] + '.txt'
    txt_file_path = os.path.join(output_directory, txt_filename)

    # Write the extracted data to the TXT file
    with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write(f"{article_content}")

# Loop through all files in the directory
for filename in os.listdir(directory_path):
    if filename.endswith('.json'):
        file_path = os.path.join(directory_path, filename)
        extract_and_save_to_txt(file_path, output_directory)

print(f"All JSON files have been processed and saved as TXT in '{output_directory}'")
