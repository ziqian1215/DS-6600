import numpy as np
import pandas as pd
import requests
import json
import dotenv
import os

class contrans:

    def __init__(self):
        dotenv.load_dotenv()
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
        self.MYSQL_ROOT_PASSWORD = os.getenv('MYSQL_ROOT_PASSWORD')
        self.MONGO_INITDB_ROOT_USERNAME = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        self.MONGO_INITDB_ROOT_PASSWORD = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        self.congresskey = os.getenv('congresskey')
        self.feckey = os.getenv('feckey')

# build crosswalk with ideology

    def get_crosswalk(self):
        url = 'https://voteview.com/static/data/out/members/HS119_members.csv'
        ideology = pd.read_csv(url)

        cols_to_keep = ['bioname','chamber', 'nominate_dim1', 'party_code',
                        'state_abbrev','district_code','icpsr', 'bioguide_id']
        ideology = ideology[cols_to_keep]
        replace_map = {200: 'Republican', 
               100: 'Democrat',
               328: 'Independent'}
        ideology['party'] = ideology['party_code'].replace(replace_map)
        ideology = ideology.drop(['party_code'], axis=1)
        ideology = ideology.rename({'nominate_dim1': 'left_right_ideology'}, axis=1)
        ideology.to_csv('data/ideology.csv', index=False)

    def get_member_info(self, chamber, state, district=None):
        ideology = pd.read_csv('data/ideology.csv')
        if district is not None:
            memberinfo = ideology.query(f"chamber=='{chamber}' & state_abbrev=='{state}' & district_code=={district}")
        else:
            memberinfo = ideology.query(f"chamber=='{chamber}' & state_abbrev=='{state}'")
        return memberinfo

# vote similarity matrix
    def get_vote_similarity_data(self):
        url = 'https://voteview.com/static/data/out/votes/HS119_votes.csv'
        votes = pd.read_csv(url)
        votes = votes.drop(['congress', 'prob'], axis=1)
        vote_compare = pd.merge(votes, votes,
                        on = ['chamber', 'rollnumber'],
                        how = 'inner')
        vote_compare = vote_compare.query("icpsr_x != icpsr_y")
        vote_compare['agree'] = vote_compare['cast_code_x'] == vote_compare['cast_code_y']
        vote_compare = vote_compare.groupby(['icpsr_x', 'icpsr_y']).agg({'agree': 'mean'}).reset_index()
        crosswalk = pd.read_csv('data/ideology.csv')
        vote_compare =pd.merge(vote_compare, crosswalk,
                left_on='icpsr_x',
                right_on='icpsr',
                how='inner')
        vote_compare = vote_compare[['bioname', 'icpsr_y', 'agree']]
        vote_compare =pd.merge(vote_compare, crosswalk,
                left_on='icpsr_y',
                right_on='icpsr',
                how='inner')
        vote_compare = vote_compare[['bioname_x', 'bioname_y', 'agree']]
        vote_compare = vote_compare.rename({'bioname_x': 'bioname',
                                        'bioname_y': 'comparison_member'}, axis=1)
        vote_compare.to_csv('data/vote_compare.csv', index=False)

    def vote_similarity_to_member(self, memberinfo):
        vote_compare = pd.read_csv('data/vote_compare.csv')
        name = memberinfo['bioname'].values[0]
        vote_compare = vote_compare.query(f"bioname=='{name}'")
        vote_compare = vote_compare.sort_values('agree', ascending=False)
        vote_compare = vote_compare[['comparison_member', 'agree']]
        return vote_compare 
        
# get biodata

# get sponsored legislation

# get donors