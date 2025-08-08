import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import time
import sys
import ast  # safer parsing of lists from strings

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
        return b''
    ids = ','.join(id_list)
    params = {
        'db': 'pubmed',
        'id': ids,
        'retmode': 'xml'
    }
    response = requests.get(url, params=params)
    return response.content

def parse_pubmed_xml(xml_data):
    if not xml_data:
        return []
    root = ET.fromstring(xml_data)
    records = []
    for article in root.findall('.//PubmedArticle'):
        try:
            article_title = article.findtext('.//ArticleTitle')
            journal = article.findtext('.//Journal/Title')

            if article_title and len(article_title) < 4:
                article_title = pd.NA

            authors = []
            affiliations = set()

            for author in article.findall('.//AuthorList/Author'):
                last = author.findtext('LastName')
                fore = author.findtext('ForeName')
                if last and fore:
                    authors.append(f"{last} {fore[0]}.")
                elif last:
                    authors.append(last)

                for aff in author.findall('.//AffiliationInfo/Affiliation'):
                    if aff is not None and aff.text:
                        affiliations.add(aff.text.strip())

            authors = ', '.join(authors)
            affiliation_str = '; '.join(affiliations) if affiliations else None

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

    for r in records:
        date_str = r['PublicationDate']
        if date_str:
            r['PublicationDate'] = pd.to_datetime(date_str, errors='coerce')
        else:
            r['PublicationDate'] = pd.NaT
    return records


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py \"['Author One', 'Author Two']\" output_name")
        sys.exit(1)

    # Parse authors list from string safely
    authors_list = ast.literal_eval(sys.argv[1])
    filename = sys.argv[2]

    all_records = []

    for author in authors_list:
        print(f"Processing author: {author}")
        ids = fetch_pubmed_ids(author, retmax=200)
        xml_data = fetch_pubmed_records(ids)
        records = parse_pubmed_xml(xml_data)
        all_records.extend(records)
        time.sleep(0.5)

    df = pd.DataFrame(all_records).drop_duplicates('Title').sort_values('PublicationDate', ascending=False)

    affiliations = [
        "UCL",
        "University College London",
        "Great Ormond Street",
        "Royal Free"
    ]
    affil_pattern = r'(?i)(?<!\w)(?:' + '|'.join(re.escape(a) for a in affiliations) + r')(?!\w)'

    df = df[df['Affiliations'].astype(str).str.contains(affil_pattern, na=False)].dropna()

    df.to_json(f'data/{filename}.json', orient='records')
