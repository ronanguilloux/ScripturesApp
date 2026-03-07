import os
import xml.etree.ElementTree as ET
from tf.convert.walker import CV
from tf.fabric import Fabric

# Configuration
SOURCE_XML = 'epubs/input/NAV/ar-Aranav-New-Arabic-Ketab-el-hayat.xml'
TF_OUTPUT_DIR = 'epubs/output/NAV/1.0'


# Metadata
slot_type = 'word'
generic_metadata = {
    'title': 'New Arabic Version (Ketab El Hayat)',
    'language': 'ara',
    'version': '1.0',
    'source': 'Zefania XML',
    'description': 'Text-Fabric version of the New Arabic Version (Ketab El Hayat).',
}

# OText definition
otext = {
    'fmt:text-orig-full': '{text}{after}',
    'sectionTypes': 'book,chapter,verse',
    'sectionFeatures': 'title,number,number',
}

# Feature Metadata
feature_metadata = {
    'text': {'description': 'Text of the word'},
    'after': {'description': 'Original whitespace after the word'},
    'number': {'description': 'Number of section'},
    'title': {'description': 'Title of the book'},
}

def director(cv):
    tree = ET.parse(SOURCE_XML)
    root = tree.getroot()

    # Iterate through books
    for book in root.findall('BIBLEBOOK'):
        book_name = book.get('bname')
        
        cur_book = cv.node('book')
        cv.feature(cur_book, title=book_name)

        # Iterate through chapters
        for chapter in book.findall('CHAPTER'):
            chapter_num = int(chapter.get('cnumber'))
            
            cur_chap = cv.node('chapter')
            cv.feature(cur_chap, number=chapter_num)

            # Iterate through verses
            for vers in chapter.findall('VERS'):
                v_num = int(vers.get('vnumber'))
                text = vers.text if vers.text else ""
                
                cur_verse = cv.node('verse')
                cv.feature(cur_verse, number=v_num)

                # Split text into words (basic splitting for now)
                words = text.strip().split()
                for i, w in enumerate(words):
                    s = cv.slot()
                    cv.feature(s, text=w, after=' ' if i < len(words) - 1 else '')
                
                cv.terminate(cur_verse)
            
            cv.terminate(cur_chap)
        
        cv.terminate(cur_book)

if __name__ == '__main__':
    print(f"Converting {SOURCE_XML} to {TF_OUTPUT_DIR}...")
    
    # Ensure output directory exists for Fabric to point to, though it might natively handle it?
    if not os.path.exists(TF_OUTPUT_DIR):
        os.makedirs(TF_OUTPUT_DIR)
        
    TF = Fabric(locations=TF_OUTPUT_DIR)
    cv = CV(TF)
    cv.walk(
        director,
        slot_type,
        otext=otext,
        generic=generic_metadata,
        featureMeta=feature_metadata,
    )
    print("Conversion complete.")
