import requests
import xml.etree.ElementTree as ET
import re
import pandas as pd
from pathlib import Path
import yaml
import time
from datetime import datetime
import warnings
import shutil

warnings.filterwarnings("ignore")

def name_matches(name, author):
    name_parts = name.lower().replace('.', '').split()
    author_parts = author.lower().split()
    return author_parts[0] in name_parts and author_parts[-1] in name_parts


def write_yaml(file_path, content):
    """Write a dictionary to a YAML file with front matter style."""
    p = Path(file_path).parent
    if p.exists():
        shutil.rmtree(p)

    p.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        f.write("---\n")
        yaml.dump(content, f, sort_keys=False)
        f.write("---\n")

def fetch_pubmed_ids(author, retmax=200):
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    params = {
        'db': 'pubmed',
        'term': f'{author}[Author]',
        'retmax': retmax,
        'retmode': 'xml'
    }
    response = requests.get(url, params=params)
    root = ET.fromstring(response.content)
    ids = [id_elem.text for id_elem in root.findall('./IdList/Id')]
    return ids

def fetch_pubmed_records(id_list):
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    if not id_list:
        return b''  # return empty bytes if no IDs
    ids = ','.join(id_list)
    params = {
        'db': 'pubmed',
        'id': ids,
        'retmode': 'xml'
    }
    response = requests.get(url, params=params)
    return response.content

def parse_pubmed_xml(xml_data, author):
    if not xml_data:
        return []
    
    affiliations = [
        "UCL",
        "University College London",
        "Great Ormond Street",
        "Royal Free"
    ]
    
    affil_pattern = r'(?i)(?<!\w)(' + '|'.join(re.escape(a) for a in affiliations) + r')(?!\w)'


    root = ET.fromstring(xml_data)
    records = []
    for article in root.findall('.//PubmedArticle'):
        try:
            article_title = article.findtext('.//ArticleTitle')
            journal = article.findtext('.//Journal/Title')

            if len(article_title) < 4:
                article_title = pd.NA  # you used np.nan, but pandas NA is cleaner in newer versions

            authors = []
            names = []
            affiliations = []


            for author_xml in article.findall('.//AuthorList/Author'):
                last = author_xml.findtext('LastName')
                fore = author_xml.findtext('ForeName')
                if last and fore:
                    authors.append(f"{last} {fore[0]}.")
                elif last:
                    authors.append(last)
                full_name = f"{fore} {last}".strip()
                aff_list = [aff.text for aff in author_xml.findall(".//Affiliation")]
                full_affiliation = "; ".join(aff_list)
                
                names.append(full_name)
                affiliations.append(full_affiliation)

            df = pd.DataFrame({"Name": names, "Affiliation": affiliations})

            authors = ', '.join(authors)
            affiliation_str = '; '.join(affiliations) if affiliations else None


            mask1 = df['Name'].apply(lambda x: name_matches(x, author))
            mask2 = df['Affiliation'].astype(str).str.contains(affil_pattern, regex=True, na=False)

            df = df.loc[mask1 & mask2]
            if len(df) >= 1:
                pub_date_elem = article.find('.//Journal/JournalIssue/PubDate')
                pub_date_str = None
                year = None
                if pub_date_elem is not None:
                    year = pub_date_elem.findtext('Year')
                    medline_date = pub_date_elem.findtext('MedlineDate')
                    month = pub_date_elem.findtext('Month')
                    day = pub_date_elem.findtext('Day')
                    if year:
                        pub_date_str = year
                        if month:
                            pub_date_str += f"-{month}"
                        if day:
                            pub_date_str += f"-{day}"
                    elif medline_date:
                        pub_date_str = medline_date

                doi = None
                for article_id in article.findall('.//ArticleIdList/ArticleId'):
                    if article_id.attrib.get('IdType') == 'doi':
                        doi = article_id.text
                        break

                records.append({
                    'Title': article_title,
                    'Journal': journal,
                    'Authors': authors,
                    'Affiliations': affiliation_str,
                    'Year': year,
                    'DOI': doi,
                    'DocumentType': 'Article',
                    'PublicationDate': pub_date_str
                })

        except Exception:
            continue

    if len('records') > 1:
        for r in records:
            date_str = r['PublicationDate']
            if date_str:
                r['PublicationDate'] = pd.to_datetime(date_str, errors='coerce')
            else:
                r['PublicationDate'] = pd.NaT
    else:
        records = pd.DataFrame()
    return records



def create_pubs(authors_list, url, retmax = 200):

    all_records = []

    for author in authors_list:
        print(f"Processing author: {author}")
        time.sleep(3)
        try:
            ids = fetch_pubmed_ids(author, retmax=retmax)
            if not ids:
                print(f"No IDs found for {author}")
                continue
            xml_data = fetch_pubmed_records(ids)
            records = parse_pubmed_xml(xml_data, author)
            all_records.extend(records)
        except Exception as e:
            print(f"Error processing {author}: {e}")
        time.sleep(3)


    # Convert all records to a DataFrame

    current_year = datetime.now().year

    df = pd.DataFrame(all_records).drop_duplicates('Title')

    if 'PublicationDate' in df.columns:
        df = df.sort_values('PublicationDate', ascending=False)
    df = df.dropna()
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')  # converts invalid/missing to NaN
    df = df.dropna(subset=['Year'])
    df['Year'] = df['Year'].astype(int)

    df = df.loc[(df['Year']< int(current_year + 1)) & (df['Year'] > 2000)]

    df.to_json(f'data/pubs_{url}.json', orient='records')
