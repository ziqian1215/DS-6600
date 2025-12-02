import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import requests
import json
import dotenv
import os
import time

class contrans:

    def __init__(self):
        dotenv.load_dotenv()
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
        self.MYSQL_ROOT_PASSWORD = os.getenv('MYSQL_ROOT_PASSWORD')
        self.MONGO_INITDB_ROOT_USERNAME = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        self.MONGO_INITDB_ROOT_PASSWORD = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        self.congresskey = os.getenv('congresskey')
        self.feckey = os.getenv('feckey')
        self.botname = 'contrans'
        self.version = '0.0'
        self.github = 'https://github.com/jkropko/contrans2025'
        self.useragent = f'{self.botname}/{self.version} ({self.github}) python-requests/{requests.__version__}'
        self.headers = {'User-Agent': self.useragent}

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

    def get_bio_data(self, bioguide_id):
        root = 'https://api.congress.gov/v3'
        endpoint = f'/member/{bioguide_id}'

        params = {'format': 'json', 'api_key': self.congresskey} 

        r = requests.get(root + endpoint, headers = self.headers, params = params)
        myjson = json.loads(r.text)['member']
        terms = myjson['terms'] 
        terms = pd.DataFrame(terms)
        terms['bioguide_id'] = bioguide_id
        try:
            terms['endYear'] = terms['endYear'].fillna(2027).astype(int)
        except: 
            terms['endYear'] = 2027
        termdata = terms[['bioguide_id','chamber', 'congress', 'stateCode', 'startYear', 'endYear']]
        try:
            termdata['district'] = terms['district']
        except:
            termdata['district'] = None
        member = {
            'bioguide_id': myjson['bioguideId'],
            'Full name':myjson['directOrderName'],
            'Chamber': myjson['terms'][-1]['chamber'],
            'State': myjson['state'],
            'Party': myjson['partyHistory'][-1]['partyName']}
        try:
            member['District'] = myjson['district']
        except:
            member['District'] = None
        try:
            member['birthYear'] = myjson['birthYear']
        except:
            pass
        try:
            member['image'] = myjson['depiction']['imageUrl']
        except:
            pass
        try:
            member['Office address'] = f'{myjson["addressInformation"]["officeAddress"]}, {myjson["addressInformation"]["city"]}, {myjson["addressInformation"]["district"]} {myjson["addressInformation"]["zipCode"]}'
            member['Phone'] = myjson['addressInformation']['phoneNumber']
            member['Website'] = myjson['officialWebsiteUrl']
        except:
            pass
        return termdata, member   
    
    def save_bio_terms(self):
        ideology = pd.read_csv('data/ideology.csv')
        bioguide_ids = ideology['bioguide_id'].unique()
        memberlist = []
        termslist = []
        i = 0
        for bioguide_id in bioguide_ids:
            if i % 10 == 0:
                print(f'Now uploading legislator {i} ({bioguide_id}) of {len(bioguide_ids)}')
            terms, member = self.get_bio_data(bioguide_id)
            termslist.append(terms)
            memberlist.append(member)
            i += 1
        member = pd.DataFrame(memberlist)
        terms = pd.concat(termslist)
        member.to_csv(f'data/bioinfo.csv', index=False)
        terms.to_csv(f'data/terms.csv', index=False)

# get sponsored legislation
    def get_sponsored_legislation_member(self, bioguide_id):
        root = 'https://api.congress.gov/v3'
        endpoint = f'/member/{bioguide_id}/sponsored-legislation'
        params = {'format': 'json',
          'offset': 0,
          'limit': 250,
          'api_key': self.congresskey}
        r = requests.get(root + endpoint, headers = self.headers, params = params)
        myjson = json.loads(r.text)
        s = [x for x in myjson['sponsoredLegislation'] if x['congress'] == 119]
        s = [{k: v for k, v in x.items() if k in ['introducedDate', 'type', 'number', 'title', 'url']} for x in s]
        spons = pd.DataFrame(s)
        spons['bioguide_id'] = bioguide_id
        return spons
    
    def get_sponsored_legislation(self):
        sl_list = []
        ideology = pd.read_csv('data/ideology.csv')
        bioguide_ids = ideology['bioguide_id'].unique()
        i = 0
        for bioguide_id in bioguide_ids:
            if i % 10 == 0:
                print(f'Now uploading legislator {i} ({bioguide_id}) of {len(bioguide_ids)}')
            spons = self.get_sponsored_legislation_member(bioguide_id)
            sl_list.append(spons)
            i += 1
        spons = pd.concat(sl_list)
        spons.to_csv(f'data/sponsored_legislation.csv', index=False)

    def get_bill_summaries(self, congress=119):
        root = 'https://api.congress.gov/v3'
        endpoint = f'/summaries/{congress}'
        params = {'format': 'json',
          'offset': 0,
          'limit': 250,
          'api_key': self.congresskey,
          'fromDateTime':'2025-01-01T00:00:00Z',
          'toDateTime':'2025-10-21T00:00:00Z'
          }
        r = requests.get(root + endpoint, headers = self.headers, params = params)
        myjson = json.loads(r.text)
        sum_list = [pd.json_normalize(myjson['summaries'])]
        l = len(sum_list)
        i = 250
        while l > 0:
            print(i)
            params['offset'] = i
            r = requests.get(root + endpoint, headers = self.headers, params = params)
            myjson = json.loads(r.text)
            sum_list = sum_list + [pd.json_normalize(myjson['summaries'])]
            l = len(myjson['summaries'])
            i += 250
        summaries = pd.concat(sum_list)
        summaries.to_csv(f'data/bill_summaries.csv', index=False)

# get donors
    def get_fec_key_member(self, bioguide_id):
        ideology = pd.read_csv('data/ideology.csv')
        memberdata = ideology.query(f"bioguide_id=='{bioguide_id}'").reset_index()
        params = {'api_key': self.feckey,
          'q': memberdata['bioname'][0].split(',')[0],
          'state': memberdata['state_abbrev'][0],
          'year': '2024'}
        if memberdata['district_code'][0] > 0:
            params['district'] = str(memberdata['district_code'][0].astype(object))
            params['office'] = 'H'
        else:
            params['office'] = 'S'
        
        r = requests.get('https://api.open.fec.gov/v1/candidates/search/', 
                         params = params,
                         headers = self.headers)
        myjson = json.loads(r.text)
        try:
            try:
                mykeys = {'bioguide_id': bioguide_id,
                        'fec_id': myjson['results'][0]['candidate_id']}
            except:
                del params['district']
                r = requests.get('https://api.open.fec.gov/v1/candidates/search/', 
                            params = params,
                            headers = self.headers)
                myjson = json.loads(r.text)
                mykeys = {'bioguide_id': bioguide_id,
                        'fec_id': myjson['results'][0]['candidate_id']}
        except:
            mykeys = {'bioguide_id': bioguide_id,
                    'fec_id': None}
        return mykeys

    
    def get_fec_keys(self):
        fec_list = []
        try:
            fec_ids = pd.read_csv('data/fec_ids.csv')
        except:
            fec_ids = pd.read_csv('data/ideology.csv')
            fec_ids = fec_ids[['bioguide_id']]
            fec_ids['fec_id'] = None

        fec_ids_nonmissing = fec_ids[fec_ids['fec_id'].notna()]
        fec_ids_missing = fec_ids[fec_ids['fec_id'].isna()]

        bioguide_ids = fec_ids_missing['bioguide_id'].unique()
 
        i = 0
        for bioguide_id in bioguide_ids:
            time.sleep(1)
            if i % 1 == 0:
                print(f'Now uploading legislator {i} ({bioguide_id}) of {len(bioguide_ids)}')
            feckey = self.get_fec_key_member(bioguide_id)
            fec_list.append(feckey)
            i += 1
        fecids = pd.DataFrame(fec_list)
        fecids = pd.concat([fec_ids_nonmissing, fecids])
        fecids.to_csv(f'data/fec_ids.csv', index=False)


    def get_contrib_committees(self, fec_id):
        root = 'https://api.open.fec.gov'
        endpoint = f'/v1/candidate/{fec_id}/committees/'
        params = {'api_key': self.feckey, 'cycle': '2024'}
        r = requests.get(root + endpoint, params=params, headers=self.headers)
        while r.status_code != 200:
            time.sleep(10)
            r = requests.get(root + endpoint, params=params, headers=self.headers)
        committee_ids = [x['committee_id'] for x in r.json()['results']]
        return committee_ids

    def get_member_contributions(self, fec_id):

        root = 'https://api.open.fec.gov'
        endpoint = '/v1/schedules/schedule_a/'

        committee_ids = self.get_contrib_committees(fec_id)
        contrib_list = []
        for c in committee_ids:
            
            params = {'api_key': self.feckey,
                      'committee_id': c,
                      'per_page': 100,
                      'sort': '-contribution_receipt_amount'}

            r = requests.get(root + endpoint, params=params, headers=self.headers)

            contrib_list = contrib_list + [{'contributor_name': x['contributor_name'],
                            'contributor_aggregate_ytd': x['contributor_aggregate_ytd'],
                            'memo_text': x['memo_text'],
                            'pdf_url': x['pdf_url']} for x in r.json()['results']]
            lastindex = r.json()['pagination']['last_indexes']

            newrecords = len(r.json()['results'])

            while newrecords > 0:
                print(len(contrib_list))

                params['last_contribution_receipt_amount']=lastindex['last_contribution_receipt_amount']
                params['last_index']=lastindex['last_index']

                r = requests.get(root + endpoint, params=params,headers=self.headers)
                while r.status_code != 200:
                    print(r.text)
                    time.sleep(10)
                    continue

                contrib_list = contrib_list + [{'contributor_name': x['contributor_name'],
                            'contributor_aggregate_ytd': x['contributor_aggregate_ytd'],
                            'memo_text': x['memo_text'],
                            'pdf_url': x['pdf_url'],
                            'fec_committee_id': c} for x in r.json()['results']]
                
                lastindex = r.json()['pagination']['last_indexes']

                newrecords = len(r.json()['results'])


        contrib_df = pd.DataFrame(contrib_list)
        contrib_df['fec_id'] = fec_id
        return contrib_df

    def get_all_contributions(self):
        fec_ids = pd.read_csv('data/fec_ids.csv')
        contrib_df = pd.read_csv('data/contrib.csv')
        fid = fec_ids[fec_ids['fec_id'].notna()]['fec_id'].unique()
        already_have = contrib_df['fec_id'].unique()
        need_to_get = np.setdiff1d(fid, already_have)
        print(f'{len(need_to_get)} legislators still to upload')
        i = 1
        for f in need_to_get:
            print(f'Now uploading legislator {i} ({f}) of {len(need_to_get)}')
            newdata = self.get_member_contributions(f)
            contrib_df = pd.concat([contrib_df, newdata])
            contrib_df.to_csv(f'data/contrib.csv', index=False)
            i += 1
            