from fetch_pubmed_utils import *

df = pd.read_csv('UCL_ICS.csv')
departments = df['department'].unique()
content_path = 'content'



# Base configuration
config = {
    "baseURL": "https://ti-yao.github.io/publications/",
    "title": "Institute of Cardiovascular Science",
    "menu": {"main": []},
    "params": {
        "description": "",
        "img_home": "img/publications.jpg",
        "img_404": "img/404.jpg"
    }
}


# Generate department pages
for department in departments:
    department_df = df[df['department'] == department]
    department_url = department_df['department_url'].values[0]

    for group, group_url, authors_list in department_df[['group','group_url','authors']].values[:]:
        print(group, group_url)
        authors_list = [name.strip() for name in authors_list.split(',')]
        create_pubs(authors_list, group_url)


    # Department folder
    dept_path = f'{content_path}/{department_url}'
    md_content = {
        "title": department,
        "draft": False,
        "layout": "department",
        "header_img": "img/publications.jpg",
        "subtitle": ' | '.join(department_df['group'].tolist())
    }
    write_yaml(f"{dept_path}/_index.md", md_content)

    # Generate group pages within the department
    for group, group_url, authors in department_df[['group','group_url','authors']].values:
        group_path = f'{dept_path}/{group_url}'
        md_content = {
            "title": group,
            "date": "2024-10-18T17:04:07+01:00",
            "draft": False,
            "layout": "publication",
            "header_img": "img/publications.jpg",
            "file": f"data/pubs_{group_url}.json",
            "department_url": department_url,
            "department": department,
            "subtitle": authors.replace(',', ' |').title()
        }
        write_yaml(f"{group_path}/_index.md", md_content)

        # Add group to config menu
        config["menu"]["main"].append({
            "identifier": group_url,
            "name": group,
            "url": f'/{department_url}/{group_url}'
        })

# Write configuration file
write_yaml("config.yaml", config)
