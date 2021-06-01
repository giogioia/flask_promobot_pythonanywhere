#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Partner Promotions Automation Bot
Glovo Italy

"""

import json
import pandas as pd
import requests
from  datetime import datetime, timedelta
import logging
import sys
import os
import os.path
from get_new_token import *
import time
#from tqdm import tqdm
#from multiprocessing import Manager, Pool, Process, cpu_count
#from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style
#from subprocess import call

class Promobot:
    global bot_name, mode, df_promo, upload_identifier, output_excel, output_path
    bot_name = 'promobot'

    '''Init functions'''
    #Step 1: set path
    def set_path():
        global cwd, token_path, input_path
        cwd = os.getcwd()
        '''
        #if sys has attribute _MEIPASS then script launched by bundled exe.
        if getattr(sys, '_MEIPASS', False):
            cwd = os.path.dirname(os.path.dirname(sys._MEIPASS))
        else:
            cwd = os.getcwd()
        else:
            if "SPY_PYTHONPATH" in os.environ:
                cwd = os.getcwd()
            else:
                cwd = os.path.dirname(sys.path[0])
        print('cwd',cwd)
        print('sys._MEIPASS',sys._MEIPASS)
        print('sys.path[0]',sys.path[0])
        print('os.getcwd()',os.getcwd())
        '''
        token_path = os.path.join(cwd,'my_personal_token.json')


    #Step 2: enable Logger
    def logger_start():
        #log config
        logging.basicConfig(filename = os.path.join(cwd,"my_log.log"),
                            level =  logging.INFO,
                            format = "%(levelname)s %(asctime)s %(message)s",
                            datefmt = '%m/%d/%Y %H:%M:%S',
                            filemode = "a")
        #log start
        global logger
        logger = logging.getLogger()
        logger.info(f"Starting log for {bot_name}")
        #print("Logger started")
        #call(["chflags", "hidden", os.path.join(cwd,"my_log.log")])

    #custom for Step 3: read credentials json
    def read_json():
        global content
        global glovo_email, refresh_token, country
        with open(token_path) as read_file:
            content = json.load(read_file)
        glovo_email = content['glovo_email']
        refresh_token = content['refresh_token']
        country = content['country']

    #Step 3: check login credentials
    def login_check():
        #Check/get login data: check if file 'my personal token' exists and read it to get login data.
        global glovo_email, refresh_token
        #print("Checking login data")
        if os.path.isfile(token_path):
            try:
                Promobot.read_json()
            except Exception:
                get_token()
            else:
                welcome_name = glovo_email[:glovo_email.find("@")].replace("."," ").title()
                print(f"\nWelcome back {welcome_name}")
        #if file does not exist: lauch file creation
        else:
            get_token()

    #Step 4: get fresh api access token
    def refresh():
        global oauth, access_token
        Promobot.read_json()
        #step 2: make request at oauth/refresh
        oauth_data = {'refreshToken' : refresh_token, 'grantType' : 'refresh_token'}
        oauth_request = requests.post('https://adminapi.glovoapp.com/oauth/refresh', json = oauth_data)
        #print(oauth_request.ok)
        if oauth_request.ok:
            access_token = oauth_request.json()['accessToken']
            new_refresh_token = oauth_request.json()['refreshToken']
            oauth = {'authorization' : access_token}
            #print("Token refreshed")
            logger.info('Access Token Refreshed')
            #saving new refresh token
            content['refresh_token'] = new_refresh_token
            with open(token_path, "w") as dst_file:
                json.dump(content, dst_file)
            print("token refreshed")
        else:
            print(f"Token NOT refreshed -> {oauth_request.content}")
            logger.info(f'Access Token NOT Refreshed -> {oauth_request.content}')


    def print_bot_name():
        print('\n' + Fore.RED + Style.BRIGHT + bot_name + Style.RESET_ALL + '\n')

    '''''''''''''''''''''''''''''End Init'''''''''''''''''''''''''''''

    '''''''''''''''''''''''''''Beginning bot'''''''''''''''''''''''''''
    '''Part 1: Get Store Address IDs and set mode'''
    #custom function for set_input(): extracts dataframe once input name is set
    def import_data(input_file):
        global df_promo
        #import data
        df_promo = pd.read_excel(input_file)
        #clean empty rows
        df_promo.dropna(how='all', inplace = True)
        #reset index after deleting empty rows
        df_promo.reset_index(drop = True, inplace = True)
        #clean str columns
        try:
            df_promo.loc[:,'City_Code'] = df_promo.loc[:,'City_Code'].str.strip()
            df_promo.loc[:,'Promo_Name'] = df_promo.loc[:,'Promo_Name'].str.strip()
        except AttributeError:pass
        try:
            df_promo.loc[:,'Promo_Type ("FLAT"/"FREE"/"XX%")'] = df_promo.loc[:,'Promo_Type ("FLAT"/"FREE"/"XX%")'].str.strip()
        except AttributeError:pass
        #add new column for api response status
        #df_promo.loc[:,'Api_Response'] = [None for _ in range(len(df_promo))]
        #add new column for current status
        df_promo.loc[:,'Status'] = None
        #clean dates
        df_promo.loc[:,"Start_Date (dd/mm/yyyy)"] = pd.to_datetime(df_promo.loc[:,"Start_Date (dd/mm/yyyy)"],dayfirst=True)
        df_promo.loc[:,"End_Date (included)"] = pd.to_datetime(df_promo.loc[:,"End_Date (included)"],dayfirst=True)

        if df_promo.loc[:,"%GLOVO"].dtype == 'O':
            df_promo.loc[:,"%GLOVO"]= df_promo.loc[:,"%GLOVO"].str.strip('%')
            df_promo.loc[:,"%GLOVO"].astype('int')
        print(f'Data extracted from {input_file}')

    def set_upload_identifier():
        global upload_identifier
        upload_identifier = input('Promos name or identifier: \t')

    def find_excel_file_path(excel_name):
        #walk in cwd -> return excel path or raise error
        for root, dirs, files in os.walk(cwd):
            if excel_name in files:
                for file in files:
                    if file == excel_name:
                        #print(f'\n{excel_name} found in folder {os.path.basename(root)}')
                        return os.path.join(root,file)
        else:
            #print('File not found in current working directory')
            raise NameError

    #set input name
    def set_input():
        global input_name
        while True:
            input_name = input('Input file name:\t')
            if '.xlsx' not in input_name: input_name = f'{input_name}.xlsx'
            #input_name = f'{bot_name}_input.xlsx'
            try:
                input_path = Promobot.find_excel_file_path(input_name)
            #print('cwd',cwd)
            #print('input_path',input_path)
            except NameError:
                time.sleep(0.5)
                print(f'\nCould not find {input_name} in {os.path.basename(cwd)}\nPlease try again\n')
                continue
            else:
                confirm_path = input(f'Using file {input_name} in folder {os.path.basename(os.path.dirname(input_path))}.\nContinue? [yes,no]\t')
                if confirm_path in ["yes","y","ye","si"]:
                    logger.info(f'Using file {input_name} in folder {os.path.basename(os.path.dirname(input_path))}')
                    break
        try:
            Promobot.import_data(input_path)
        except KeyError as e:
            print(f'Column {e} is missing. Unable to import data.')
            sys.exit(0)


    #Set mode(enable/disable)
    def set_mode():
        time.sleep(0.5)
        global mode
        while True:
            a_or_b = input('Select the type of operation you want to perform:\n[A] - Create Promos\n[B] - Delete Promos\n[C] - Check current Promos status\nPress "A", "B" or "C" then press ENTER:\t').lower().strip()
            if a_or_b in ["a","b","c"]:
                time.sleep(0.5)
                if a_or_b == 'a':
                    print('\nSelected mode is "Create Promos":')
                    print(f'Promos will will be Created for the {len(df_promo)} Store IDs found in {input_name}')
                    time.sleep(2)
                    confirm = input('\nProceed with Promo Creation? [yes/no]\t').strip().lower()
                    print("\n")
                    if confirm in ['yes','ye','y','si']:
                        mode = 'create'
                        break
                elif a_or_b == "b":
                    print('\nSelected mode is "Delete Promos":')
                    print(f'Promos will will be Deleted for the {len(df_promo)} Store IDs found in {input_name}')
                    time.sleep(2)
                    confirm = input('\nProceed with Promo Deletion? [yes/no]\t').strip().lower()
                    print("\n")
                    if confirm in ['yes','ye','y','si']:
                        mode = 'delete'
                        break
                elif a_or_b == "c":
                    print('\nSelected mode is "Promos status check":')
                    print(f'A simple check of current Promo status will be done for the {len(df_promo)} Store IDs found in {input_name}')
                    time.sleep(2)
                    confirm = input('\nProceed [yes]/[no]:\t').strip().lower()
                    print("\n")
                    if confirm in ["yes","y","ye","si"]:
                        mode = 'check'
                        break

    '''promo deletion'''
    def deletion(n):
        if pd.notna(df_promo.at[n,'Promo_ID']):
            if df_promo.at[n,'Status'] == 'deleted':
                print(n,'already deleted')
            else:
                url = f'https://adminapi.glovoapp.com/admin/partner_promotions/{int(df_promo.at[n,"Promo_ID"])}'
                r = requests.delete(url, headers  = {'authorization' : access_token})
                if r.ok:
                    df_promo.at[n,'Status'] = 'deleted'
                    print(f'Promo {n} - deleted')
                else:
                    print(f'Promo {n} - unable to delete', r.content)
        else:
            print(f'Promo {n} - no promo ID to delete')

    '''promo creation'''
    def p_type(promo_type):
        if type(promo_type) == 'str':
            promo_type.strip().upper()
        if promo_type == 'FLAT':
            return 'FLAT_DELIVERY'
        elif promo_type == 'FREE':
            return 'FREE_DELIVERY'
        else:
            return 'PERCENTAGE_DISCOUNT'

    def del_fee(promo_type):
        if promo_type == 'FLAT':
            return 100
        if promo_type == 'FREE':
            return None
        else:
            return None

    def perc(promo_type):
        if Promobot.p_type(promo_type) == 'FLAT_DELIVERY' or Promobot.p_type(promo_type) == 'FREE_DELIVERY':
            return None
        elif Promobot.p_type(promo_type) == 'PERCENTAGE_DISCOUNT':
            if type(promo_type) == 'str':
                return int((promo_type).strip('%'))
            else:
                return int(promo_type)

    def strat(subsidy):
        return f'ASSUMED_BY_{subsidy}'

    def paymentStrat(subsidy):
        if Promobot.strat(subsidy) == "ASSUMED_BY_GLOVO" or Promobot.strat(subsidy) == "ASSUMED_BY_PARTNER":
            return Promobot.strat(subsidy)
        elif Promobot.strat(subsidy) == "ASSUMED_BY_BOTH":
            return "ASSUMED_BY_PARTNER"


    def time_code(x, date):
        if x == 'start':
            hours_added = timedelta(hours = 1)
            future_date = date + hours_added
            stamp = datetime.timestamp(future_date)
            return int(stamp*1000)
        if x == 'end':
            hours_added = timedelta(hours = 25)
            future_date = date + hours_added
            stamp = datetime.timestamp(future_date)
            return int(stamp*1000)

    def products_ID_list(n):
        prods_list = []
        for i in range(1,10):
            try:
                df_promo.at[n,f'Product_ID{i}']
            except KeyError:
                break
            else:
                if pd.isna(df_promo.at[n,f'Product_ID{i}']): continue
                prods_list.append((str(df_promo.at[n,f'Product_ID{i}'])).replace('\ufeff', ''))
        if prods_list == []:
            return None
        else:
            return prods_list

    def store_addresses_ID_list(n):
        sa_ID_list = []
        for o in range(1,10):
            try:
                df_promo.at[n,f'Store_Address{o}']
            except KeyError:
                break
            else:
                if pd.isna(df_promo.at[n,f'Store_Address{o}']): continue
                if type(df_promo.at[n,f'Store_Address{o}']) == str:
                    df_promo.at[n,f'Store_Address{o}'] = df_promo.at[n,f'Store_Address{o}'].replace('\ufeff', '')

                sa_ID_list.append(int(df_promo.at[n,f'Store_Address{o}']))
        if sa_ID_list == []:
            return None
        else:
            return sa_ID_list

    def subsidyValue(subject, n):
        if Promobot.strat((df_promo.at[n,'Subsidized_By (\"PARTNER\"/\"GLOVO\"/\"BOTH\")']).strip().upper()) == 'ASSUMED_BY_GLOVO':
                if subject == 'glovo':
                    return 100
                if subject == 'partner':
                    return 0
        elif Promobot.strat((df_promo.at[n,'Subsidized_By (\"PARTNER\"/\"GLOVO\"/\"BOTH\")']).strip().upper()) == 'ASSUMED_BY_PARTNER':
            if subject == 'glovo':
                return 0
            if subject == 'partner':
                return 100
        elif Promobot.strat((df_promo.at[n,'Subsidized_By (\"PARTNER\"/\"GLOVO\"/\"BOTH\")']).strip().upper()) == 'ASSUMED_BY_BOTH':
            if subject == 'glovo':
                return df_promo.at[n,"%GLOVO"]
            if subject == 'partner':
                return df_promo.at[n,"%PARTNER"]



    def creation(n):
        if df_promo.at[n,'Status'] == 'created':
            print(n,'already created')
        else:
            url = 'https://adminapi.glovoapp.com/admin/partner_promotions'
            payload = {"name": df_promo.at[n,'Promo_Name'],
                       "cityCode": df_promo.at[n,'City_Code'],
                       "type": Promobot.p_type(df_promo.at[n,'Promo_Type ("FLAT"/"FREE"/"XX%")']),
                       "percentage": Promobot.perc(df_promo.at[n,'Promo_Type ("FLAT"/"FREE"/"XX%")']),
                       "deliveryFeeCents": Promobot.del_fee(df_promo.at[n,'Promo_Type ("FLAT"/"FREE"/"XX%")']),
                       "startDate": Promobot.time_code('start',df_promo.at[n,"Start_Date (dd/mm/yyyy)"]),
                       "endDate": Promobot.time_code('end',df_promo.at[n,"End_Date (included)"]),
                       "openingTimes": None,
                       "partners":[{"id": int(df_promo.at[n,'Store_ID']),
                                    "paymentStrategy": Promobot.paymentStrat((df_promo.at[n,'Subsidized_By (\"PARTNER\"/\"GLOVO\"/\"BOTH\")']).strip().upper()),
                                    "externalIds": Promobot.products_ID_list(n),
                                    "addresses": Promobot.store_addresses_ID_list(n),
                                    "commissionOnDiscountedPrice":False,
                                    "subsidyStrategy":"BY_PERCENTAGE",
                                    "sponsors":[{"sponsorId":1,
                                       "sponsorOrigin":"GLOVO",
                                       "subsidyValue":Promobot.subsidyValue("glovo", n)},
                                      {"sponsorId":2,
                                       "sponsorOrigin":"PARTNER",
                                       "subsidyValue":Promobot.subsidyValue("partner", n)}]}],
                       "customerTagId":None,
                       "budget":None}
            p = requests.post(url, headers = {'authorization' : access_token}, json = payload)
            if p.ok is False:
                print(f'Promo {n} NOT PROCESSED')
                try:
                    df_promo.at[n,'Status'] = f"ERROR: {p.json()['error']['message']}"
                except Exception:
                    df_promo.at[n,'Status'] = f"ERROR: {p.content}"
                    if 'Bad request' in str(p.content):
                        print(f'Promo {n} - status: NOT CREATED - INVALID INPUT DATA OR INACTIVE STORE ID')
                finally:
                    print(f'ERROR: {p.text}')
            else:
                df_promo.at[n,'Promo_ID'] = int(p.json()['id'])
                df_promo.at[n,'Status'] = 'created'
                print(f'Promo {n} - status: created; id: {p.json()["id"]}')
                if n == 0:
                    print(f'\nPromo link: https://beta-admin.glovoapp.com/promotions/{p.json()["id"]}')
                    print('Check if promo has been created as expected')
                    confirmation = input(f'Continue promo creation ({len(df_promo)-1} promos left)? [yes,no]\n')
                    print("\n")
                    if confirmation in ['yes','ye','y','si']:
                        pass
                    else:
                        Promobot.df_to_excel()
                        sys.exit(0)

    def checker(n):
        if pd.notna(df_promo.at[n,'Promo_ID']):
            url = f"https://adminapi.glovoapp.com/admin/partner_promotions/{df_promo.at[n,'Promo_ID']}"
            p = requests.get(url, headers = {'authorization' : access_token})
            if p.ok is False:
                try:
                    p.json()['error']['message']
                except Exception:
                    df_promo.at[n,'Status'] = p.text
                    print(p.text)
                else:
                    if 'deleted' in p.json()['error']['message']:
                        df_promo.at[n,'Status'] = 'deleted'
                        print(f'Promo {n} - deleted')
                    else:
                        df_promo.at[n,'Status'] = p.json()['error']['message']
                        print(p.json()['error']['message'])

            else:
                if p.json()['deleted'] == True:
                    df_promo.at[n,'Status'] = 'deleted'
                    print(f'Promo {n} - deleted')
                else:
                    df_promo.at[n,'Status'] = 'active'
                    print(f'Promo {n} - active')
        else:
            print(f'Promo {n} - No promo ID to check')


    def create_output_dir():
        global output_path
        output_path = os.path.join(cwd, upload_identifier)
        try: os.mkdir(output_path)
        except Exception: pass

    '''save to excel'''
    def df_to_excel():
        global output_excel
        tz = datetime.now()
        output_excel = os.path.join(output_path, f'{bot_name}_{mode}_{tz.strftime("%Y_%m_%d_(h%H_%M)")}.xlsx')
        df_promo.loc[:,["Start_Date (dd/mm/yyyy)","End_Date (included)"]] = df_promo.loc[:,["Start_Date (dd/mm/yyyy)","End_Date (included)"]].apply(lambda x: x.dt.strftime('%d/%m/%Y'))
        df_promo.to_excel(output_excel, index = False)
        #saveback to original
        with pd.ExcelWriter('promobot_input.xlsx') as writer:
            df_promo.to_excel(writer, sheet_name = 'Promos', index=False)
            writer.sheets['Promos'].set_default_row(20)
            writer.sheets['Promos'].freeze_panes(1, 0)


    '''launcher'''
    def launch(function):
        for n in df_promo.index:
            function(n)
        Promobot.df_to_excel()

    '''main'''
    def main():
        '''initiation code'''
        Promobot.set_path()
        Promobot.logger_start()
        Promobot.login_check()
        Promobot.refresh()
        Promobot.print_bot_name()
        '''bot code'''
        Promobot.set_input()
        Promobot.set_upload_identifier()
        Promobot.create_output_dir()
        Promobot.set_mode()
        if mode == 'create':
            Promobot.launch(Promobot.creation)
        elif mode == 'delete':
            Promobot.launch(Promobot.deletion)
        elif mode == 'check':
            Promobot.launch(Promobot.checker)
        print(f'\n\n{bot_name} has processed {len(df_promo)} Store Addresses\n\nResults are available in file {os.path.relpath(output_excel)}')


