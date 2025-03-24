# 1A. Dependencies
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime as dt
import dateparser
import csv
import requests
import Modules.datemodule as datemod
import Modules.nba_teams as teams
import re
import os
import shutil

#import requests_cache
import pandas as pd
import sys

# 1B. def `make_entryname()` function
def make_entryname(source, date, team_abbrev):
    """Create standardized entryname from source, date, and team_abbrev."""
    entryname = '_'.join([source, date, team_abbrev])
    return entryname

# 1C. def `record_entry()` function
def record_entry(dest_list, entryname, source, author, date, url, team, rank, mode='print'):
    """Create standardized power ranking entry."""
    case = {
        "entryname":entryname, 
        "source": source,
        "author": author,
        "date": date, 
        "url":url,
        "teamname":team, 
        "ranking": rank,
        }
    if mode == 'print':
        print(f"--{entryname}: {teams.nba_abbrname(team)} is #{rank} in {source}'s {date} PR")
    
    elif mode == 'write':
        #input_conf = input(f"Write {len(case)} entries to {list}?: Y/N")

        #if input_conf == "Y":
            dest_list.append(case)
            print(f"--{entryname}: {teams.nba_abbrname(team)} is #{rank} in {source}'s {date} PR")
        #else: 
        #    return None

    
    else:
        print("Please specify mode")
        return None

# 1D. Source-Specific Parsing Methods

# 1Di

def get_br_soup(URL):

    cases = []
    
    response = requests.get(URL)
    br_soup = BeautifulSoup(response.content, "lxml")

    # source
    source = 'BR'

    #teams
    br_teams = br_soup.find_all('h2')[1:]

    
    # 3.A.i. author
    author = br_soup.select('span[class=name]')[0].text
    
    # 3.A.ii. date (use 'datemod.file_date' for standardized formatting)
    date_br = br_soup.select('span[class*=date]')[0].text # returns format October 4, 2024
    date = dateparser.parse(date_br)
    
    # 3.B. entry parsing
    for t in br_teams:

        # 3.B.i. team
        team_br=t.text.split('. ')
        if len(team_br) > 1:
            team_br = team_br[1]
        else:
            continue
        
        # remove betting odds if present in team name
        if '(' in team_br:
            team_br = team_br.split(' (')[0]
            #print(f"corrected teamname: {team}")
        else:
            team_br = team_br

        # uniform team naming across sources (use 'teams.nba_tmname()')
        team = teams.nba_tmname(team_br)

        # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
        team_abbrev = teams.nba_abbrname(team_br)
        
        # 3.B.ii. rank
        rank=t.text.split('. ', 1)[0]
    
        # 3.B.iii comments
        """
        text = t.find_next_siblings()
        text = t.find_all("p") # need to join
        text = t.find_next_siblings()
        p_sib = text[1].find_all("p")
        comm_br = '\n'.join(str(p.get_text()) for p in p_sib)
        comments = comm_br
        """

        # 3.B.iv entryname
        entryname = make_entryname(source,date, team_abbrev)

        
        case = {
            "entryname":entryname, 
            "teamname":team, 
            "ranking": rank,
            "author": author,
            "source": source,
            "date": date, 
            "url":URL,
            #"comments": comments
            }
        cases.append(case)
    
    return(cases)

def get_br_soup2(URL):
    """Extract power rankings information from new CBS Sports format (no table)."""
    cases = []
    

    headers={"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # `source` has already been defined
    source = 'BR'

    # still works
    # 3.A.i. author
  
    author = soup.find("span", {"id":"id/article/header/author"}).text
 
    #print(author)


    # still works
    # 3.A.ii. date (use 'datemod.file_date' for standardized formatting)

    # 3.A.ii. date (use 'datemod.file_date' for standardized formatting)
    date_br = soup.find("span", {"id":"id/article/header/post_date"}).get_text().strip()
    date = datemod.file_date(date_br)


    text_article = soup.find_all('span', class_=re.compile(r'small__headings__title__large'))

    # 3.B. entry parsing
    for section in text_article:
        
        entry_comment=[]
        
        section_break = section.get_text()
    
        try:
            section_break = section_break.split(' (')[0] # removing the records (w-l)
            section_break = section_break.split('. ') # splitting by period, giving up clean values for rank and team


            # uniform team naming across sources (use 'teams.nba_tmname()')
            team_br = section_break[1].strip()
            team_br = teams.nba_tmname(team_br)
            team = team_br
            
            # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
            team_abbrev = teams.nba_abbrname(team)
        
            # 3.B.ii. rank
            rank_br = section_break[0].strip()
            rank = int(rank_br)

            # 3.B. iii comments
            """
            for each in section.find_next_siblings('div'):
                each = each.text.strip()
                if len(each) >= 2:
                    entry_comment.append(each)
                else:
                    continue
            
            comments = entry_comment
            """

            entryname = make_entryname(source,date, team_abbrev)
                    
            case = {
                "entryname":entryname, 
                "teamname":team, 
                "ranking": rank,
                "author": author,
                "source": source,
                "date": date, 
                "url":URL,
                #"comments": comments
                }
            cases.append(case)
        

        except:
            pass

    return cases

def get_cbs_soup(URL):

    cases = []
    
    response = requests.get(URL)
    cbs_soup = BeautifulSoup(response.content, "lxml") 
    
    cbs_table = cbs_soup.find('table', {"class":"table-power-rankings"})

    # `url` has already been defined
    source = 'CBS'

    # 3.A.i. author
    author = cbs_soup.find("a", {"class":"ArticleAuthor-name--link"}).text

    # 3.A.ii. date (use 'datemod.file_date' for standardized formatting)
    date_cbs = cbs_soup.find("time").text.strip()
    date_cbs = ' '.join(date_cbs.split())
    date = datemod.file_date(date_cbs)
    
    # 3.B. entry parsing
    rows = cbs_table.select("tr")
    
    for r in rows[1:]:
        # 3.B.i. team
        team_cbs = r.find('span', {"class":"team-name"}).text.strip()
        
        # uniform team naming across sources (use 'teams.nba_tmname()')
        team = teams.nba_tmname(team_cbs)

        # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
        team_abbrev = teams.nba_abbrname(team)
        
        # 3.B.ii. rank
        rank = r.find("span", {"class":"rank"}).text.strip()
        
        # 3.B. iii comments
        #comm_cbs = r.find("td", {"class": "cell-left dek"}).text.strip()
        #comments = comm_cbs


        entryname = make_entryname(source,date, team_abbrev)

        case = {
            "entryname":entryname, 
            "teamname":team, 
            "ranking": rank,
            "author": author,
            "source": source,
            "date": date, 
            "url":URL,
            #"comments": comments
        }
        cases.append(case)
    return((cases))

def get_cbs_soup2(URL):
    """Extract power rankings information from new CBS Sports format (no table)."""
    cases = []
    

    headers={"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.content, 'lxml')
    
    # `source` has already been defined
    source = 'CBS'

    # still works
    # 3.A.i. author
    author = soup.find("a", {"class":"ArticleAuthor-name--link"}).text


    # still works
    # 3.A.ii. date (use 'datemod.file_date' for standardized formatting)
    date_cbs = soup.find("time").text.strip()
    date_cbs = ' '.join(date_cbs.split()[:-1]) # excluding "ET"
    date = datemod.file_date(date_cbs)

    # 3.B. entry parsing
    # in 2nd CBS format, article is nested in a div with class "Article-content"
    article_div = soup.find_all('div', class_='Article-content')

    # and power rankings are li in uls
    lis = article_div[0].find_all('li')
    lis = [li.text for li in lis]

    for li in lis:
        # rank will be followed by a '.', which will precede a space and a team ranking...
        li = re.split(r'\. ', li)

        if len(li) >= 2:
            team_cbs = li[1].strip()
            rank_cbs = li[0].strip()

            # uniform team naming across sources (use 'teams.nba_tmname()')
            team = teams.nba_tmname(team_cbs)
            # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
            team_abbrev = teams.nba_abbrname(team)
        
            # 3.B.ii. rank
            rank = int(rank_cbs)
        
            # 3.B. iii comments
            # skipping this since each team doesnt get its own comments
            """
            comm_cbs = r.find("td", {"class": "cell-left dek"}).text.strip()
            comments = comm_cbs
            comments = ''
            """

            entryname = make_entryname(source,date, team_abbrev)

            case = {
                "entryname":entryname, 
                "teamname":team, 
                "ranking": rank,
                "author": author,
                "source": source,
                "date": date, 
                "url":URL,
                #"comments": comments
            }
            cases.append(case)
            #print(case)
            
        else:
            continue

    return(cases)

def get_espn_soup(URL):

    cases = []

    headers={"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    espn_soup = BeautifulSoup(response.content, "lxml")
    #print(espn_soup)

    # `url` has already been defined
    # 2C source
    source = 'ESPN'

    # 3.A.i. author
    author = 'Staff'
    
    # 3.A.ii. date (format '12-Oct-24')
    date_espn = espn_soup.find_all("span", class_="timestamp", string=lambda text: "ET" in text if text else False)
    date_espn = date_espn[0].get_text(strip=True)
    date = datemod.file_date(str(date_espn))

    # 3.B. entry parsing
    espn_teams = []
    for p in espn_soup.find_all('p'):
        text = p.text
        if text and text[0].isdigit() and text.split()[1].isalpha():
            text_split = text.split('. ', 1)

            # 3.B.i. team
            team_espn = text_split[1].strip()

            # uniform team naming across sources (use 'teams.nba_tmname()')
            team = teams.nba_tmname(team_espn)

            # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
            team_abbrev = teams.nba_abbrname(team_espn)

            # 3.B.ii. rank
            rank = text_split[0].strip()
            
            # 3.B.iii comments
            """
            next_p = p.find_next_sibling("p").get_text()
            comments_espn = next_p
            comments = comments_espn
            """

            # 3.B.iv entryname
            entryname = make_entryname(source,date, team_abbrev)

            case = {
                "entryname":entryname, 
                "teamname":team, 
                "ranking": rank,
                "author": author,
                "source": source,
                "date": date, 
                "url":URL,
                #"comments": comments
            }
            cases.append(case)
    #print(type(cases))
    return(cases)

def get_nba_soup(URL):
    cases = []
    
    headers={"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    nba_soup = BeautifulSoup(response.content, "lxml")

    # `url` has already been defined
    # 2C source
    source = 'NBA'

    # 3.A.i. author
    # p with class starting with 'ArticleAuthor_authorName'
    author = nba_soup.select_one('p[class*="_authorName"]').get_text()
    
    
    # 3.A.ii. date (format '[Updated] October 28, 2024 10:21 AM')

    date_nba = nba_soup.select_one('time').get_text(strip=True)
    if "Updated " in date_nba:
        date_nba=date_nba.split("Updated on ")[1]
        date = datemod.file_date(date_nba)

    else:
        date = datemod.file_date(date_nba)


    # 3.B. entry parsing
    # entry header contained in div with class _starting_ `ArticlePowerRankings_pr`
    nba_entries = nba_soup.select('div[class*="ArticlePowerRankings_pr_"]')
    #print(nba_entries)
    
    for count, i in enumerate(nba_entries):
        # 3.B.i. team
        # ArticlePowerRankings_prTeam
        team_nba = i.select_one('a[class*="ArticlePowerRankings_prTeam"]')
        team_nba = team_nba.get_text(strip=True)
    
        # uniform team naming across sources (use 'teams.nba_tmname()')
        team = teams.nba_tmname(team_nba)

        # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
        team_abbrev = teams.nba_abbrname(team_nba)
        
        # 3.B.ii. rank just doing it via enumeration — NBA ranks low to hi (meaning most to least powerful)
        rank = count +1

        # 3.B.iii comments
        """
        # in following div with class _starting_ `ArticleContent_article__`
        comments_nba = i.select('div[class*="ArticleContent_article__"]')
        comments_nba = '\n'.join([graf.text for graf in comments_nba])
        comments = comments_nba
        """   
        
        # 3.B.iv entryname
        entryname = make_entryname(source,date, team_abbrev)

        
        case = {
            "entryname":entryname, 
            "teamname":team, 
            "ranking": rank,
            "author": author,
            "source": source,
            "date": date, 
            "url":URL,
            #"comments": comments
        }
        cases.append(case)
    return(cases)

def get_score_soup(URL):

    cases = []

    response = requests.get(URL)
    score_soup = BeautifulSoup(response.content, "lxml")


    # `url` has already been defined
    # 2C source 
    source = 'Score'
     
    # 3.A.i. author 
    author = 'Staff'

    # 3.A.ii. date (format '12-Oct-24')
    date_score = score_soup.find('time').get('datetime')
    date = datemod.file_date(date_score)
    

    # 3.B. entry parsing 

    teams_split = score_soup.find_all('h3')
   
    for t in teams_split:
        t1 = t.get_text()
        t_split = t1.split('. ',1)
    
        # 3.B.ii. rank 
        score_rank = t_split[0]
        rank = score_rank
    
        # 3.B.i. team 
        score_team = t_split[1].strip()
        score_team = score_team.split(' (',1)[0].strip()
        #print(team)
        
        # uniform team naming across sources
        team = teams.nba_tmname(score_team)
        #print(team)
        
        # 3.B.i.1a team_abbrev AND 3.B.i.1b team_abbrev cancel  
        team_abbrev = teams.nba_abbrname(score_team)

        # 3.B.iii comments
        """
        paragraphs = t.find_next_siblings('p', limit=2)
        comments_score = '\n'.join([p.get_text() for p in paragraphs])
        comments = comments_score
        """
        
        # 3.B.iv entryname 
        entryname = '_'.join([source, date, team_abbrev])
        
        case = {
            "entryname":entryname, 
            "teamname":team, 
            "ranking": rank,
            "author": author,
            "source": source,
            "date": date, 
            "url":URL,
            #"comments": comments
        }
        cases.append(case)
    return(cases)

def get_fox_soup(URL):

    cases = []

    headers={"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    #response = requests.get(URL)
    fox_soup = BeautifulSoup(response.content, "lxml")
    
    #return fox_soup
    teams_si = fox_soup.find_all('h2')
    

    # `url` has already been defined
    # 2C source 
    source = 'Fox'
     
    # 3.A.i. author 
    #auth_si_class="link_13bb9r0"
    author = fox_soup.find("div", {"class":'contributor-name'}).text.strip()

    # 3.A.ii. date (format '241011')
    div_tag = fox_soup.find("div", {"class":'info-text'})
    date_fox = div_tag.find_all("span")[1]
    #date = datemod.file_date(date_fox)
    date_fox= date_fox.text.strip()[:-3]
    #date = pd.to_datetime(date_fox)
    date = datemod.file_date(date_fox)

    # 3.B. entry parsing 

    # featured in numbered list
    pr_header = fox_soup.find(text='NBA POWER RANKINGS')
    pr_list = pr_header.find_next("ol")
    pr_list = pr_list.find_all('li')

    for index, team_fox in enumerate(pr_list):

        # 3.B.i. team 
        # uniform team naming across sources (use 'teams.nba_tmname()')
        team_fox = team_fox.get_text().strip()
        team = teams.nba_tmname(team_fox)

        # 3.B.i.1a get team abbreviation (use 'teams.nba_abbrname()')
        team_abbrev = teams.nba_abbrname(team)

        # 3.B.ii. rank 
        rank = index + 1

        # 3.B.iii comments
        """comm_fox = ""
        comments = comm_fox
        """

        # 3.B.iv entryname 
        entryname = make_entryname(source, str(date), team_abbrev)
        
        case = {
            "entryname":entryname, 
            "teamname":team, 
            "ranking": rank,
            "author": author,
            "source": source,
            "date": date, 
            "url":URL,
            #"comments": comments
        }
        cases.append(case)
    return(cases)

def find_latest_file(folder_path,format=''):
    """Find most recent file in specified folder."""
    try:
        # Get all files in the folder
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        
        if not files:
            return None  # Return None if no files are found

        # Find the latest file based on modification time
        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(folder_path, f)))
    except FileNotFoundError:
        print(f"Folder not found: {folder_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
    if format == 'path':
        return 'Weekly_PowerRankings/' + latest_file
    else:
        return latest_file

def get_today(input=''):
    "Get today's date, filename, pathname, or fullpath."
    if input == 'file':
        return f"{datemod.file_date()}_powerrankings.csv"
    
    elif input == 'path':
        return f"Weekly_PowerRankings/{datemod.file_date()}_powerrankings.csv"
    
    elif input == 'fullpath':
        return f"/Users/keegan/Projects/NBA Power Rankings/Weekly_PowerRankings/{datemod.file_date()}_powerrankings.csv"

    return f"{datemod.file_date()}"


print(f"Today path: {get_today('file')}")

def filename_already_exists(filename_input=get_today('file')):
    """Check if filename already exists"""
    folder_path='Weekly_Powerrankings'
    file_path = find_latest_file(folder_path)

    filename_exists = filename_input == file_path
    print(f"{filename_input} already exists? {filename_exists}")
    return filename_exists

def copy_and_rename(src_path, dest_path):
    """Copy and rename file to specified path."""
    # copy file
    shutil.copy(src_path, dest_path)
    print(f"Successfully duplicated '{src_path}' and renamed to '{dest_path}'")

def duplicate():
    #
    pass 

#if filename_already_exists(get_today('file')):
#    # Pass
#    pass
#else:
#    copy_and_rename(find_latest_file('Weekly_PowerRankings'),(get_today()+ '_powerrankings.csv'))

#print(f"Latest file: {find_latest_file('Weekly_PowerRankings')}")
#print(filename_contains_string(find_latest_file('Weekly_PowerRankings'), str(get_today())))
    



#### WRITING TO CSV ####
    ## FIND LATEST FILE IN '/Users/keegan/Projects/NBA Power Rankings/Weekly_PowerRankings'
    ## IS THE FILE FROM TODAY?
        ## IF NO, DUPLICATE _existing file_ to _current date file_
            ## CONFIRM entry is not duplicate in _current date file_
            ## INPUT CONFIRMATION then WRITE ROWS from `DEST` to _current date file_
            ## PRINT `print(f"File has {len(file)} entries, or {len(file)/30} power rankings")`
            ## UPDATE 'Dash_Deploy/support/data/latest_powerrankings.csv' with content of 'dest_filename'
        ## IF YES, skip duplication
            ## CONFIRM entry is not duplicate in _current date file_
            ## INPUT CONFIRMATION then WRITE ROWS from `DEST` to _current date file_
            ## PRINT `print(f"File has {len(file)} entries, or {len(file)/30} power rankings")`
            ## UPDATE 'Dash_Deploy/support/data/latest_powerrankings.csv' with content of 'dest_filename'



def get_rankings(URL):
    """Input URL and then get rankings based on URL source."""
    dest = []
    # 2C
    source = urlparse(URL).netloc.split('.')[-2]
 
    if source == 'espn':
        print(f"Source is {source}... now beginning sub-function")
        soup = get_espn_soup(URL)
    
    elif source == 'bleacherreport':
        print(f"Source is {source}... now beginning sub-function")
        try:
            soup = get_br_soup(URL)
        
        except Exception as e:
            print(f"Error: Could not complete. Error message: ---{e}--- Trying method 2")
            soup = get_br_soup2(URL)
        
    elif source == 'cbssports':
        print(f"Source is {source}... now beginning sub-function")
        try:
            soup = get_cbs_soup(URL)

        except Exception as e:
            print(f"Error: Could not complete. Error message: ---{e}--- Trying method 2")
            soup = get_cbs_soup2(URL)

    elif source == 'si':
        print(f"Source is {source}... Sports Illustrated not currently supported")
        return None

    elif source == 'theringer':
        print(f"Source is {source}... The Ringer not currently supported")
        return None
    
    elif source == 'yahoo':
        print(f"Source is {source}... Yahoo not currently supported")
        return None

    elif source == 'thescore':
        print(f"Source is {source}... now beginning sub-function")
        soup = get_score_soup(URL)

    elif source == 'nba':
        print(f"Source is {source}... now beginning sub-function")
        soup = get_nba_soup(URL)

    elif source =='foxsports':
        print(f"Source is {source}... now beginning sub-function")
        soup = get_fox_soup(URL)
    
    else: 
        print('Source not yet defined')
        return None

    #print(type(soup))
    # Creating 'temp_dest'
    temp_dest =[]

    #return(soup)
    
    ## Using 'record_entry()' to write case entries to 'temp_dest'
    for row in soup:

        record_entry(temp_dest, row['entryname'],row['source'],row['author'],row['date'],row['url'],row['teamname'], row['ranking'], 'write')

    ## Confirming want to write 'temp_dest' entries to 'dest'
    for row in temp_dest:
        dest.append(row)
    return dest

def count_csv_rows(file_path):
    """Count rows in CSV file."""
    try:
        with open(file_path, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            row_count = sum(1 for row in csv_reader)
        return row_count
    except FileNotFoundError:
        print (f"Error: '{file_path}' not found.")
    except Exception as e:
        print(f"An error occured: {e}")

def entry_occurrences_in_file(file_path, entryname):
    """Avoid duplicates, count occurences of entryname in file."""
    try:
        count = 0
        with open(file_path, 'r') as file:
            for line in file:
                count += line.count(entryname)
        return count
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return 0
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0

def append_rows(dest, dest_filename):
    """Append rows to CSV."""
    fieldnames = ['entryname', 'source', 'author', 'date', 'url', 'teamname', 'ranking']
    #fieldnames = ['entryname', 'source', 'author', 'date', 'url', 'teamname', 'ranking', 'comments']
    input_conf = input (f"{'-'*30}\nAppend {len(dest)} rows to destination: {dest_filename}? Y/N  ")
    #print(input_conf)
    if  input_conf.lower() in ("y", "yes"):
        # Check if dest is already in ranking file (by entryname)
        first_entryname = (dest[0]['entryname'])
        if entry_occurrences_in_file(find_latest_file('Weekly_PowerRankings','path'), first_entryname) != 0:
            print('\nATTENTION:\nThis set of rankings has already been added')
            return 0
            
        else:
            with open(dest_filename, 'a') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerows(dest)
                print(f"Successfully appended {len(dest)} rows to '{dest_filename}'\n{'-'*30}")
            return 1
        #print(f"Successfully appended {len(dest)} rows to '{dest_filename}'\n\n'{dest_filename}' now has {count_csv_rows('250313_powrrankings.csv')} rows\n{'-'*30}")
    else:
        print('Operation canceled')
        return 0
        

def writing_rankings(rankings):
    filename = get_today('file')
    filepath = get_today('path')

    if not filename_already_exists(filename):
        latest_file_path = find_latest_file('Weekly_PowerRankings', 'path')
        if latest_file_path:
            if os.path.isfile(latest_file_path) and os.access(latest_file_path, os.R_OK):
                copy_and_rename(latest_file_path, filepath)
            else:
                print(f"Error: '{latest_file_path}' is not accessible or readable.")
        else:
            print("No latest file found to copy.")
            return

    b = append_rows(rankings, filepath)
    if b == 0:
        print(f'\nNo rankings to write')
        return
    else:
        row_count = int(count_csv_rows(filepath)-1)
        power_rankings_count = row_count / 30
        #print(f"File '{filename}' now has {count_csv_rows(filepath)} entries, or {power_rankings_count} power rankings")
        print(f"File '{filename}' now has {row_count} entries, or {power_rankings_count} power rankings")
        return filepath, b



#writing_rank

def overwrite_latest(new_file):
    """Overwrite Latest PR File with specified file."""
    try:
        filepath, confirmation = new_file
    except TypeError:
        try:
            filepath = new_file
            confirmation = None
        
        except:
            print(f'\nNo file to overwrite\n\nEnding operation\n{"-"*40}')
            return

    if confirmation == 0:
        print(f'\nNo file to overwrite\n\nEnding operation\n{"-"*40}')
        return

    latest_filename = 'Dash_Deploy/support/data/latest_powerrankings.csv'

    # Validate the source file
    if not os.path.isfile(filepath):
        raise ValueError(f"The path {filepath} is not a valid file.")

    # Validate the destination directory
    if not os.path.exists(os.path.dirname(latest_filename)):
        raise ValueError(f"The directory for {latest_filename} does not exist.")

    # Count rows in both files
    try:
        rows_outcome = count_csv_rows(latest_filename)-1
        rows_new = count_csv_rows(filepath)-1
    except Exception as e:
        print(f'\nError counting rows: {e}\n\nEnding operation\n{"-"*40}')
        return

    # Check if the new file has more rows
    if rows_new <= rows_outcome:
        print(f"Aborted. New file ({rows_new} rows) should be longer than old file ({rows_outcome} rows).")
        return

    # Interactive confirmation
    if sys.stdin.isatty():  # True if running in a terminal
        confirmation = input(
            f"Overwrite '{latest_filename}' ({rows_outcome} rows; {rows_outcome / 30:.2f} PR sets) "
            f"with '{filepath}' ({rows_new} rows; {rows_new / 30:.2f} PR sets)? Y/N: "
        )
        if confirmation.lower() not in ('yes', 'y'):
            print("Aborted. Confirmation not received.")
            return

    # Overwrite the file
    shutil.copyfile(filepath, latest_filename)
    print(
        f"Confirmed\n'{filepath}' has overwritten '{latest_filename}'\n"
        f"'{latest_filename}' had {rows_outcome} rows but now contains {count_csv_rows(latest_filename)-1} rows "
        f"or {int((count_csv_rows(latest_filename) - 1) / 30)} complete PR sets."
    )



#writing_rankings(get(rankgi))


def main(URL_input):
    return overwrite_latest(writing_rankings(get_rankings(URL_input)))
    #return writing_rankings(get_rankings(URL_input))
    #print(writing_rankings(get_rankings('https://www.espn.com/nba/story/_/page/nbapowerrankings44254378/nba-power-rankings-30-teams-less-month-regular-season')))
    #return get_rankings(URL_input)


if __name__ == '__main__':
    #print(get_rankings('https://www.espn.com/nba/story/_/page/nbapowerrankings44254378/nba-power-rankings-30-teams-less-month-regular-season'))

    if len(sys.argv) >=1:
        main(sys.argv[1])
    else:
        print("Please provide a url")