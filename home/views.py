import asyncio
import base64
import csv
import datetime
import decimal
import io
import json
import os
import re
import shutil
import smtplib
import ssl
import tempfile
import threading
import time
import traceback
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO, StringIO
from math import ceil
from time import sleep
from urllib.parse import unquote
from zipfile import ZipFile

import aiohttp
import pandas as pd
import requests
from aiosmtplib import SMTP
from asgiref.sync import async_to_sync, sync_to_async
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import connection, transaction
from django.db.models import (
    Avg,
    Case,
    DecimalField,
    F,
    FloatField,
    Max,
    Min,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.http.response import JsonResponse
from django.middleware import csrf
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import formats, timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import format_html
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from openpyxl import Workbook
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from requests.exceptions import ConnectTimeout, RequestException
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from .decorators import Broker_only, allowed_users
from .filters import OrderFilter
from .models import (
    Accounting,
    ClientDetail,
    CurrentIpoName,
    CustomUser,
    GroupDetail,
    Order,
    OrderDetail,
    RateList,
)


def expiry_date_processor(request):
    if request.user.is_authenticated:
        try:
            user_profile = CustomUser.objects.get(username=request.user)
            expiry_date = user_profile.Expiry_Date
        except CustomUser.DoesNotExist:
            expiry_date = None
    else:
        expiry_date = None
    return {"expiry_date": expiry_date}


def isValidPAN(Z):
    Result = re.compile("[A-Za-z]{5}\d{4}[A-Za-z]{1}")
    return Result.match(Z)


# @allowed_users(allowed_roles=['Broker'])
@Broker_only
def index(request):
    if request.user.is_anonymous:
        return redirect("/login")
    products = CurrentIpoName.objects.filter(user=request.user).order_by("-id")
    ratelist = []
    for i in products:
        try:
            Ratelistitem = RateList.objects.get(
                user=request.user, RateListIPOName_id=i.id
            )
        except:
            Ratelistitem = 0
        ratelist.append(Ratelistitem)
    params = {"entry": zip(products, ratelist), "product": products}
    return render(request, "index.html", params)


@allowed_users(allowed_roles=["Customer"])
def indexforCustomer(request):
    if request.user.is_anonymous:
        return redirect("/login")
    products = CurrentIpoName.objects.filter(user=request.user.Broker_id)
    ratelist = []
    for i in products:
        try:
            Ratelistitem = RateList.objects.get(
                user=request.user.Broker_id, RateListIPOName_id=i.id
            )
        except:
            Ratelistitem = 0
        ratelist.append(Ratelistitem)
    params = {"entry": zip(products, ratelist), "product": products}
    return render(request, "index.html", params)


# <!--- Allotment Check Start


def linkin_function():
    def getDropDown(url):
        max_attempts = 5
        timeout = 10
        for attempt in range(1, max_attempts + 1):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                }
                response = requests.post(
                    url,
                    headers=headers,
                    verify="./pemfile/my_trust_store.pem",
                    timeout=timeout,
                )
                if response.status_code == 200:
                    json_data = response.json()
                    return json_data
                else:
                    return None
            except requests.RequestException as e:
                print(f"Attempt {attempt}: Error - {e}")
                sleep(0.5)
        return None

    url = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/GetDetails"
    json_data = getDropDown(url)

    if json_data:
        data = json_data
        soup = BeautifulSoup(f"""{data}""", "lxml")

        company_data_dict = {}
        for table in soup.find_all("table"):
            company_id = table.company_id.text
            company_name = table.companyname.text
            company_data_dict[company_name] = company_id
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in company_data_dict.items()
        }
        return normalized_dict


# def kefintech_function():
#     global dropdown_dict
#     def getDropDown(url ,max_attempts=5, timeout=10):
#         for attempt in range(1, max_attempts + 1):
#             try:
#                 response = requests.get(url, verify='./pemfile/kfintech.pem',timeout=timeout)
#                 if response.status_code == 200:
#                     return response.text
#                 else:
#                     return None
#             except RequestException as e:
#                 print(f"Attempt {attempt}: Error - {e}")
#                 sleep(0.5)
#         return None

#     urls = [
#         'https://kprism.kfintech.com/ipostatus/',#server3
#         'https://kosmic.kfintech.com/ipostatus/', #server1
#         'https://evault.kfintech.com/ipostatus/',#server2
#         'https://rti.kfintech.com/ipostatus/',#server5
#         'https://kcasop.kfintech.com/ipostatus/',#server4
#     ]

#     html_content = None
#     for url in urls:
#         html_content = getDropDown(url, max_attempts=5, timeout=10)
#         if html_content:
#             break

#     if html_content:
#         soup = BeautifulSoup(html_content, 'html.parser')
#         dropdown_options = soup.select('#ddl_ipo option')
#         data = [option.text for option in dropdown_options]
#         data2 = [option['value'] for option in dropdown_options]

#         dropdown_dict = dict(zip(data, data2))
#         normalized_dict = {
#             re.sub(r'\s+', ' ', key.strip()): value
#             for key, value in dropdown_dict.items()
#         }
#         return normalized_dict


def kefintech_function():
    global dropdown_dict

    url = "https://crapi.kfintech.com/api/ipos"
    response = requests.get(url)
    ipos = response.json()  # this is already a list of dicts
    dropdown_dict = {ipo["UNIT_NAME"]: ipo["UCDBPRE"] for ipo in ipos}
    # print(dropdown_dict)
    return dropdown_dict


def BigShareDropDown():
    global dropdown_dict

    def getDropDown(url):
        try:
            response = requests.get(url, verify="./pemfile/_.bigshareonline.pem")
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = "https://ipo.bigshareonline.com/IPO_Status.html"
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        dropdown_options = soup.select("#ddlCompany option")
        data = [option.text for option in dropdown_options]
        data2 = [option.get("value", "") for option in dropdown_options]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict


def PurvaDropDown():
    global dropdown_dict

    def getDropDown(url):
        try:
            response = requests.get(url, verify="pemfile/purvashare.pem")
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = "https://www.purvashare.com/investor-service/ipo-query"
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        dropdown_options = soup.select("#company_id option")
        data = [option.text.strip() for option in dropdown_options]
        data2 = [option.get("value", "") for option in dropdown_options]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict


def SkyLineDropDown():
    global dropdown_dict

    def getDropDown(url):
        try:
            response = requests.get(url, verify="pemfile/skylinerta.pem")
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = "https://www.skylinerta.com/ipo.php"
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        dropdown_options = soup.select("#company option")
        data = [option.text.strip() for option in dropdown_options[1:]]
        data2 = [option.get("value", "") for option in dropdown_options[1:]]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict


def IntegratedDropDown():
    global dropdown_dict

    def getDropDown(url):
        try:
            data = {"Req": 1, "Comp": "IPO"}
            response = requests.post(url, data=data, verify="pemfile/integrated.pem")
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = "https://ipostatus.integratedregistry.in/RegistrarsToAjax.aspx"
    html_content = getDropDown(url)
    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        dropdown_dict = {}

        for option in soup.find_all("option"):
            if option["value"] != "0":  # Skip the --select-- option
                dropdown_dict[option.text.strip()] = option["value"]
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict


def MaashitlaDropDown():
    global dropdown_dict

    def getDropDown(url):
        try:
            response = requests.get(url, verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = "https://microservices.maashitla.com/public-issues-service/companies"
    html_content = getDropDown(url)

    if html_content:
        soup = html_content["data"]
        data = [item["companyTitle"] for item in soup]
        data2 = [item["companyId"] for item in soup]
        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict


def CambridgeDropDown():
    global dropdown_dict

    def getDropDown(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = "https://ipostatus1.cameoindia.com/"
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        dropdown_options = soup.select("#drpCompany option")
        data = [option.text.strip() for option in dropdown_options[1:]]
        data2 = [option.get("value", "") for option in dropdown_options[1:]]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r"\s+", " ", key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict


def get_iponame_Dropdown(ipo_register_value):
    if ipo_register_value == "Linkin":
        linkin_company_data = linkin_function()
        register_options = {
            "Linkin": (
                remove_specific_options(
                    list(linkin_company_data.keys()), unwanted_phrases
                )
                if linkin_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "Kfintech":
        kefintech_company_data = kefintech_function()
        register_options = {
            "Kfintech": (
                remove_specific_options(
                    list(kefintech_company_data.keys()), unwanted_phrases
                )
                if kefintech_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "BigShare":
        BigShare_company_data = BigShareDropDown()
        register_options = {
            "BigShare": (
                remove_specific_options(
                    list(BigShare_company_data.keys()), unwanted_phrases
                )
                if BigShare_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "Purva":
        Purva_company_data = PurvaDropDown()
        register_options = {
            "Purva": (
                remove_specific_options(
                    list(Purva_company_data.keys()), unwanted_phrases
                )
                if Purva_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "SkyLine":
        Skyline_company_data = SkyLineDropDown()
        register_options = {
            "SkyLine": (
                remove_specific_options(
                    list(Skyline_company_data.keys()), unwanted_phrases
                )
                if Skyline_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "Integrated":
        Integrated_company_data = IntegratedDropDown()
        register_options = {
            "Integrated": (
                remove_specific_options(
                    list(Integrated_company_data.keys()), unwanted_phrases
                )
                if Integrated_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "Maashitla":
        Maashitla_company_data = MaashitlaDropDown()
        register_options = {
            "Maashitla": (
                remove_specific_options(
                    list(Maashitla_company_data.keys()), unwanted_phrases
                )
                if Maashitla_company_data
                else []
            ),
        }
        return register_options

    if ipo_register_value == "Cambridge":
        Cambridge_company_data = CambridgeDropDown()
        register_options = {
            "Cambridge": (
                remove_specific_options(
                    list(Cambridge_company_data.keys()), unwanted_phrases
                )
                if Cambridge_company_data
                else []
            ),
        }
        return register_options


unwanted_phrases = {
    "Select Company",
    "--Select--",
    "--Select Company--",
    "Select Company",
}


def remove_specific_options(company_list, unwanted_phrases):
    # Remove the first item if it matches any of the unwanted phrases
    if company_list and company_list[0] in unwanted_phrases:
        return company_list[1:]  # Skip the first item
    return company_list


def encVal(vl):
    key = b"8080808080808080"
    iv = b"8080808080808080"

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(vl.encode(), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)

    return base64.b64encode(encrypted_data)


def get_options(request):
    PRI_limit = CustomUser.objects.get(username=request.user)
    is_premium_user = PRI_limit.Allotment_access

    if str(is_premium_user) == "True":
        ipo_register_value = request.GET.get("ipo_register")
        DropDown = get_iponame_Dropdown(ipo_register_value)
        options = DropDown.get(ipo_register_value, [])
        return JsonResponse(options, safe=False)
    else:
        return None


# @sync_to_async
# def bulk_create_or_update(entries):
#     # with transaction.atomic():
#         # Separate entries into those that need to be created and those that need to be updated
#     objects_to_update = []

#     for entry in entries:
#         # Check if the record exists
#         existing_entry = OrderDetail.objects.get(
#             user=entry['user'],
#             Order__OrderIPOName_id=entry['IPOid'],
#             OrderDetailPANNo__PANNo=entry['panno'],
#             Order__OrderType=entry['OrderType'],
#         )
#         if existing_entry:
#             # If the record exists, update it
#             existing_entry.AllotedQty = int(entry['shares_alloted'])
#             objects_to_update.append(existing_entry)

#     if objects_to_update:
#         OrderDetail.objects.bulk_update(objects_to_update, fields=['AllotedQty'])


# @sync_to_async
# def update_database(user, IPOid, panno, shares_alloted,OrderType):
#     entry = OrderDetail.objects.get(user=user, Order__OrderIPOName_id=IPOid, OrderDetailPANNo__PANNo=panno,Order__OrderType=OrderType)
#     entry.AllotedQty = int(shares_alloted)
#     entry.save()


async def update_database(user, IPOid, panno, shares_alloted, OrderType):
    try:
        entry = await sync_to_async(OrderDetail.objects.get)(
            user=user,
            Order__OrderIPOName_id=IPOid,
            OrderDetailPANNo__PANNo=panno,
            Order__OrderType=OrderType,
        )
        entry.AllotedQty = int(shares_alloted)
        await sync_to_async(entry.save)()
    except Exception as e:
        print(f"Error updating database: {e}")


async def linkin_token(session, url, ssl_context, retries=3, timeout=5):
    # ssl_context = ssl.create_default_context(cafile='pemfile/my_trust_store.pem')
    for attempt in range(retries):
        try:
            async with session.post(url, ssl=ssl_context) as response:
                json_data = await asyncio.wait_for(response.text(), timeout)
                data = json.loads(json_data)
                number = data["d"]
                response = number
                encrypted_value = encVal(response)
                token = encrypted_value.decode()
                return token

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"Retrying... (Attempt {attempt + 1}/{retries})")
            attempt = attempt + 1

        except:
            if attempt < retries:
                attempt = attempt + 1


async def Linkin_fetch_allotment(
    user,
    session,
    selected_key,
    panno,
    result,
    IPOid,
    OrderType,
    ssl_context,
    retries=3,
    timeout=5,
):

    # def update_database(user, IPOid, panno, shares_alloted,OrderType):
    #     entry = OrderDetail.objects.get(user=user, Order__OrderIPOName_id=IPOid, OrderDetailPANNo__PANNo=panno,Order__OrderType=OrderType)
    #     entry.AllotedQty = int(shares_alloted)
    #     entry.save()

    tknurl = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/generateToken"

    token = await linkin_token(session, tknurl, ssl_context)
    myobj = {
        "clientid": selected_key,
        "PAN": panno,
        "IFSC": "",
        "CHKVAL": "1",
        "token": token,
    }

    url = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/SearchOnPan"
    # ssl_context = ssl.create_default_context(cafile='pemfile/my_trust_store.pem')
    for attempt in range(retries):
        flag = 0
        try:
            async with session.post(
                url, data=json.dumps(myobj), ssl=ssl_context
            ) as response:
                soup = await response.json()
                soup = BeautifulSoup(f"""{soup}""", "lxml")

                if not soup.find("newdataset").contents:
                    result["QTY1"] = "No Record Found"
                    result["REMRAK"] = "DONE"

                try:
                    msg = soup.msg
                    msg1 = msg.text
                except:
                    msg1 = None

                if msg1 is not None:
                    result["QTY1"] = msg1

                dpclitid = []
                try:
                    dpclitid = [table.dpclitid for table in soup.find_all("table")]
                except:
                    dpclitid.append(None)

                for j, dpclitid1 in enumerate(dpclitid):
                    if dpclitid1 is not None:
                        dpclitid1 = dpclitid1.text
                    result[f"DpID-ClientID{j+1}"] = dpclitid1

                invcode_list = []
                try:
                    invcode_list = [table.invcode for table in soup.find_all("table")]
                except:
                    invcode_list.append(None)

                bankcode_list = []
                try:
                    bankcode_list = [table.bnkcode for table in soup.find_all("table")]
                except:
                    bankcode_list.append(None)

                for j, invcode1 in enumerate(invcode_list):
                    if invcode1 is not None:
                        invcode1 = invcode1.text
                    if bankcode_list[j] is not None:
                        bankcode = bankcode_list[j].text

                    if invcode1 == "91" and bankcode == "0":
                        flag = 1
                        result[f"QTY{j+1}"] = (
                            "Application bidded but amount not blocked"
                        )

                offer_price = []
                try:
                    offer_price = [
                        table.offer_price for table in soup.find_all("table")
                    ]
                except:
                    offer_price.append(None)

                for j, offer_price1 in enumerate(offer_price):
                    if offer_price1 is not None:
                        offer_price1 = offer_price1.text
                    result[f"Cut Off Price{j+1}"] = offer_price1

                allot = []
                try:
                    allot = [table.allot for table in soup.find_all("table")]
                except:
                    allot.append(None)

                Name = []
                try:
                    Name = [table.name1 for table in soup.find_all("table")]
                except:
                    Name.append(None)

                for j, Name1 in enumerate(Name):
                    if Name1 is not None:
                        Name1 = Name1.text
                    result[f"Name{j+1}"] = Name1

                if Name and all(item is None for item in Name):
                    flag = 1

                allotqty = 0
                for i, (j, allot1) in enumerate(zip(range(len(allot)), allot)):
                    if allot1 is not None:
                        allot1 = allot1.text
                        allotqty = int(allot1) + allotqty
                        if flag == 0:
                            if int(allotqty) >= 0:
                                try:
                                    await update_database(
                                        user, IPOid, panno, allotqty, OrderType
                                    )
                                except Exception as e:
                                    print(e)

                            result[f"QTY{j+1}"] = allot1

                pemndg = []
                try:
                    pemndg = [table.pemndg for table in soup.find_all("table")]
                except:
                    pemndg.append(None)

                for j, pemndg1 in enumerate(pemndg):
                    if pemndg1 is not None:
                        pemndg1 = pemndg1.text
                    result[f"Category{j+1}"] = pemndg1

                result["REMRAK"] = "DONE"
                return result

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )

        except Exception as e:
            result["REMRAK"] = e
            return result


async def linkin_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):

    entry = Data
    data_length = len(entry)

    def get_key_by_value(dictionary, value):
        for key, val in dictionary.items():
            if key == value:
                return val

    selected_text = ipo_name
    linkin_company_data = linkin_function()
    IPO_Name_dic = linkin_company_data

    selected_key = get_key_by_value(IPO_Name_dic, selected_text)

    results = []

    ssl_context = ssl.create_default_context(cafile="pemfile/my_trust_store.pem")
    async with aiohttp.ClientSession(
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "Cookie": "_ga=GA1.1.897427883.1703307036; _ga_T3ER3Y8R0E=GS1.1.1705735885.6.1.1705736037.0.0.0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
    ) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            result = {"PAN": panno}
            tasks.append(
                Linkin_fetch_allotment(
                    user,
                    session,
                    selected_key,
                    panno,
                    result,
                    IPOid,
                    OrderType,
                    ssl_context,
                )
            )

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY1' in res:
        #         if res['QTY1'] != 'No Record Found' and res['Name1'] != '' and res['QTY1'] != 'Application bidded but amount not blocked' and res['QTY1'].isdigit() and int(res['QTY1']) >= 0 :
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY1' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def Kfintech_fetch_allotment(
    user, session, myobj, panno, result, IPOid, OrderType, retries=3, timeout=5
):
    url = "https://crapi.kfintech.com/api/ipos"
    for attempt in range(retries):
        flag = 0
        try:
            async with session.post(url, data=myobj) as response:
                soup = await response.json()
                alloti_Qty = 0
                for j, entry in enumerate(soup):
                    appl_no = entry["Appl.No"]
                    name = entry["Name"]
                    if name == "" or name == ".":
                        flag = 1
                    applied = entry["Applied"]
                    alloti = entry["Alloted"]
                    if alloti is not None:
                        if flag == 0:
                            if int(alloti) >= 0:
                                alloti_Qty = alloti_Qty + int(alloti)
                                try:
                                    await update_database(
                                        user, IPOid, panno, alloti, OrderType
                                    )
                                except Exception as e:
                                    print(e)
                                    pass

                    msg = entry["MSG"]
                    ipo_status = entry["IPO_STATUS"]
                    result[f"Appl.No{j+1}"] = appl_no
                    result[f"Name{j+1}"] = name
                    result[f"Applied{j+1}"] = applied
                    result[f"QTY{j+1}"] = alloti
                    if alloti is None:
                        result[f"QTY{j+1}"] = msg
                    result[f"IPO_STATUS{j+1}"] = ipo_status
                result["REMRAK"] = "DONE"
                return result

        except aiohttp.ClientConnectionError:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )

        except Exception as e:
            result["REMRAK"] = "ERROR"
            return result


async def Kfintech_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data

    data_length = len(entry)

    kefintech_company_data = kefintech_function()
    IPO_options_dict = kefintech_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []

    async with aiohttp.ClientSession(
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
    ) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                "ipodets": selected_value,
                "queryby": "P",
                "qval": panno,
            }
            result = {"PAN": panno}
            tasks.append(
                Kfintech_fetch_allotment(
                    user, session, myobj, panno, result, IPOid, OrderType
                )
            )

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY1' in res:
        #         if res['QTY1'] != 'PAN not found' and res['Name1'] != '.' :
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY1' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def BigShare_fetch_allotment(
    session,
    user,
    myobj,
    panno,
    result,
    IPOid,
    OrderType,
    ssl_context,
    retries=3,
    timeout=5,
):
    url = "https://ipo.bigshareonline.com/Data.aspx/FetchIpodetails"
    # ssl_context = ssl.create_default_context(cafile=r'pemfile/_.bigshareonline.pem')
    for attempt in range(retries):
        try:
            async with session.post(
                url, data=json.dumps(myobj), ssl=ssl_context
            ) as response:
                soup = await response.json()
                soup = BeautifulSoup(f"""{soup}""", "lxml")
                tag21 = soup.find("p").text
                try:
                    dpid_data = eval(tag21)["d"]["DPID"]
                    result["DPID"] = dpid_data
                except (AttributeError, KeyError):
                    result["DPID"] = None

                try:
                    App_no = eval(tag21)["d"]["APPLICATION_NO"]
                    result["APPLICATION_NO"] = App_no
                except (AttributeError, KeyError):
                    result["APPLICATION_NO"] = None

                try:
                    Name = eval(tag21)["d"]["Name"]
                    result["Name"] = Name
                except (AttributeError, KeyError):
                    result["Name"] = None

                try:
                    Applied = eval(tag21)["d"]["APPLIED"]
                    result["APPLIED"] = Applied
                except (AttributeError, KeyError):
                    result["APPLIED"] = None

                try:
                    alloted1 = eval(tag21)["d"]["ALLOTED"]
                    if alloted1 == "NON-ALLOTTE":
                        alloted1 = 0
                    result["QTY"] = alloted1
                    if alloted1 != "":
                        if Name != "":
                            if int(alloted1) >= 0:
                                await update_database(
                                    user, IPOid, panno, alloted1, OrderType
                                )
                except (AttributeError, KeyError):
                    result["QTY"] = None

                result["REMRAK"] = "DONE"
                return result

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(
                f"Error in Big share allotment ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})({e})"
            )

        except Exception as e:
            result["REMRAK"] = "ERROR"
            return result


async def BigShare_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):

    entry = Data

    data_length = len(entry)

    BigShare_company_data = BigShareDropDown()
    IPO_options_dict = BigShare_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []

    ssl_context = ssl.create_default_context(cafile=r"pemfile/_.bigshareonline.pem")
    # ssl_context.load_verify_locations(cafile=r'pemfile/_.bigshareonline.pem')

    # connector = aiohttp.TCPConnector(limit=10000)
    async with aiohttp.ClientSession(
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
    ) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                "Applicationno": "",
                "Company": selected_value,
                "SelectionType": "PN",
                "PanNo": panno,
                "txtcsdl": "",
                "txtDPID": "",
                "txtClId": "",
                "ddlType": "0",
                "lang": "en",
            }
            result = {"PAN": panno}
            tasks.append(
                BigShare_fetch_allotment(
                    session, user, myobj, panno, result, IPOid, OrderType, ssl_context
                )
            )

        responses = await asyncio.gather(*tasks)
        valid_responses = [
            response for response in responses if response and "error" not in response
        ]
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'No data found' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def fetch_csrf_token(session, url, retries=3, timeout=5):
    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                html_content = await asyncio.wait_for(response.text(), timeout)
                soup = BeautifulSoup(html_content, "html.parser")
                csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
                csrf_token_value = csrf_token_input["value"]
                return csrf_token_value
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"Retrying... (Attempt {attempt + 1}/{retries})")


async def Purva_fetch_allotment(
    session,
    user,
    selected_value,
    panno,
    result,
    IPOid,
    OrderType,
    ssl_context,
    retries=3,
    timeout=5,
):
    for attempt in range(retries):

        tknurl = "https://www.purvashare.com/investor-service/ipo-query"

        csrf_token_value = await fetch_csrf_token(session, tknurl)
        myobj = {
            "csrfmiddlewaretoken": csrf_token_value,
            "company_id": selected_value,
            "applicationNumber": "",
            "panNumber": panno,
            "submit": "Search",
        }

        url = "https://www.purvashare.com/investor-service/ipo-query"

        flag = 0
        try:
            async with session.post(url, data=myobj, ssl=ssl_context) as response:
                soup = await asyncio.wait_for(response.text(), timeout)
                await asyncio.sleep(2)
                soup = BeautifulSoup(soup, "html.parser")
                td_elements = soup.find("tbody")

                if td_elements.find("tr"):
                    td_elements = soup.find("tbody").find("tr").find_all("td")
                    labels = [
                        "Name",
                        "App_Num",
                        "",
                        "DPID",
                        "Shares Applied",
                        "Shares Allotted",
                        "",
                    ]

                    for label, td in zip(labels, td_elements):
                        if label:
                            if label == "Name":
                                result["Name"] = str(td.text)
                                if str(td.text) == "":
                                    flag = 1

                            if label == "DPID":
                                result["DPID"] = str(td.text)

                            if label == "App_Num":
                                result["Appl.No"] = str(td.text)

                            if label == "Shares Applied":
                                result["Applied"] = str(td.text)

                            if label == "Shares Allotted":
                                result["QTY"] = str(td.text)
                                if flag == 0:
                                    if str(td.text) >= "0":
                                        await update_database(
                                            user, IPOid, panno, int(td.text), OrderType
                                        )
                else:
                    error_message = soup.find(
                        text="Sorry, there was an error processing your request. Please try again."
                    )
                    if error_message:
                        if attempt < retries:
                            attempt += 1
                            continue
                        else:
                            result["REMRAK"] = "ERROR"
                            return result
                    else:
                        result["REMRAK"] = "ERROR"
                        result["QTY"] = "No record found"
                        return result

                result["REMRAK"] = "DONE"
                return result
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )

        except Exception as e:
            traceback.print_exc()
            result["REMRAK"] = "ERROR"
            return result


async def Purva_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data
    data_length = len(entry)

    Purva_company_data = PurvaDropDown()
    IPO_options_dict = Purva_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []
    ssl_context = ssl.create_default_context(cafile="pemfile/purvashare.pem")

    tasks = []
    async with aiohttp.ClientSession(
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.purvashare.com/investor-service/ipo-query",
        }
    ) as session:
        for i in range(data_length):
            panno = entry[i]
            result = {"PAN": panno}
            tasks.append(
                Purva_fetch_allotment(
                    session,
                    user,
                    selected_value,
                    panno,
                    result,
                    IPOid,
                    OrderType,
                    ssl_context,
                )
            )

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'No Record Found' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)
    results = [res for res in results if res is not None]
    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def Integrated_fetch_allotment(
    user, session, myobj, panno, result, IPOid, OrderType, retries=3, timeout=5
):
    url = "https://ipostatus.integratedregistry.in/NCDAllotmentDetailsdataLaodNew.aspx"
    for attempt in range(retries):
        flag = 0
        try:
            async with session.post(url, data=myobj) as response:
                text = await asyncio.wait_for(response.text(), timeout)
                if "Records Not Found...!!!" in text:
                    result["QTY"] = "Records Not Found...!!!"
                    result["REMRAK"] = "DONE"
                    return result
                else:
                    left_div_pattern = re.compile(r"<div class='leftdiv'>(.*?)</div>")
                    right_div_pattern = re.compile(
                        r"<div class='rightdiv'>: (.*?)</div>"
                    )
                    left_divs = left_div_pattern.findall(text)
                    right_divs = right_div_pattern.findall(text)
                    for left, right in zip(left_divs, right_divs):
                        if left.strip() == "Application No.":
                            result["Appl.No"] = right.strip()
                        elif left.strip() == "Category":
                            result["Category"] = right.strip()
                        elif left.strip() == "Dpid Client Id":
                            result["DPID"] = right.strip()
                        elif left.strip() == "Name":
                            result["Name"] = right.strip()
                            if right.strip() == "":
                                flag = 1
                        elif left.strip() == "Applied":
                            result["Applied"] = right.strip()
                        elif left.strip() == "Allotted":
                            result["QTY"] = right.strip()
                            if flag == 0:
                                if right.strip() >= "0":
                                    await update_database(
                                        user,
                                        IPOid,
                                        panno,
                                        int(right.strip()),
                                        OrderType,
                                    )
                    result["REMRAK"] = "DONE"
                    return result
        except aiohttp.ClientConnectionError:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )
        except Exception as e:
            result["REMRAK"] = "ERROR"
            return result


async def Integrated_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data

    data_length = len(entry)

    Integrated_company_data = IntegratedDropDown()
    IPO_options_dict = Integrated_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []

    async with aiohttp.ClientSession(
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
    ) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                "Req": 2,
                "Comp": selected_value,
                "AppNum": "",
                "PANNO": panno,
                "Choice": "3",
                "DPClit": "",
                "TYPE": "IPO",
                "Captcha": "undefined",
            }
            result = {"PAN": panno}
            tasks.append(
                Integrated_fetch_allotment(
                    user, session, myobj, panno, result, IPOid, OrderType
                )
            )

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'Records Not Found...!!!' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def Maashitla_fetch_allotment(
    user,
    session,
    myobj,
    panno,
    result,
    IPOid,
    OrderType,
    ssl_context,
    retries=3,
    timeout=5,
):
    url = "https://maashitla.com/PublicIssues/Search"
    # ssl_context = ssl.create_default_context(cafile='pemfile/maashitla.pem')
    for attempt in range(retries):
        try:
            async with session.get(url, data=myobj, ssl=ssl_context) as response:
                data = await response.json()
                pan = data.get("pan", None)
                if pan != "":
                    dpclitid = data.get("demat_Account_Number", None)
                    result["DPID"] = dpclitid
                    appnum1 = data.get("application_Number", None)
                    result["Appl.No"] = appnum1
                    name = data.get("name", None)
                    result["Name"] = name
                    share_Applied = data.get("share_Applied", None)
                    result["Applied"] = share_Applied
                    share_Alloted = data.get("share_Alloted", None)
                    result["QTY"] = share_Alloted
                    if name != "":
                        if share_Alloted >= 0:
                            await update_database(
                                user, IPOid, panno, int(share_Alloted), OrderType
                            )
                    result["REMRAK"] = "DONE"
                    return result

                else:
                    result["QTY"] = "Records Not Found...!!!"
                    result["REMRAK"] = "DONE"
                    return result
        except aiohttp.ClientConnectionError:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )
        except Exception as e:
            result["REMRAK"] = "ERROR"
            return result


async def Maashitla_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data

    data_length = len(entry)

    Integrated_company_data = MaashitlaDropDown()
    IPO_options_dict = Integrated_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []

    ssl_context = ssl.create_default_context(cafile="pemfile/maashitla.pem")

    async with aiohttp.ClientSession(
        headers={
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
    ) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                "company": selected_value,
                "search": panno,
            }
            result = {"PAN": panno}
            tasks.append(
                Maashitla_fetch_allotment(
                    user, session, myobj, panno, result, IPOid, OrderType, ssl_context
                )
            )

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'Records Not Found...!!!' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def SkyLine_fetch_allotment(
    user,
    session,
    myobj,
    panno,
    result,
    IPOid,
    OrderType,
    ssl_context,
    retries=3,
    timeout=5,
):
    url = "https://www.skylinerta.com/display_application.php"
    # ssl_context = ssl.create_default_context(cafile='pemfile/skylinerta.pem')
    for attempt in range(retries):
        try:
            async with session.post(url, data=myobj, ssl=ssl_context) as response:
                soup = await asyncio.wait_for(response.text(), timeout)
                soup = BeautifulSoup(soup, "lxml")

                if (
                    soup.find("div", class_="fullwidth resultsec").find(
                        "strong", text="Applicant Name : "
                    )
                    is not None
                ):
                    try:
                        applicant_name = (
                            soup.find("div", class_="fullwidth resultsec")
                            .find("strong", text="Applicant Name : ")
                            .next_sibling.strip()
                        )
                    except:
                        applicant_name = None
                    result["Name"] = applicant_name

                    try:
                        client_id = (
                            soup.find("div", class_="fullwidth resultsec")
                            .find("strong", text="DP IP /Client ID : ")
                            .next_sibling.strip()
                        )
                    except:
                        client_id = None
                    result["DPID"] = client_id

                    try:
                        application_number = (
                            soup.find("div", class_="fullwidth resultsec")
                            .find("strong", text="Application Number : ")
                            .next_sibling.strip()
                        )
                    except:
                        application_number = None
                    result["Appl.No"] = application_number

                    table = soup.find("table")
                    headers = [header.text.strip() for header in table.find_all("th")]
                    rows = []
                    for row in table.find_all("tr")[1:]:
                        cells = [cell.text.strip() for cell in row.find_all("td")]
                        rows.append(dict(zip(headers, cells)))

                    DataZip = rows[0]
                    if applicant_name != "":
                        if DataZip["Shares Alloted"] >= "0":
                            result["QTY"] = int(DataZip["Shares Alloted"])
                            await update_database(
                                user, IPOid, panno, DataZip["Shares Alloted"], OrderType
                            )

                    result["Applied"] = DataZip["Shares Applied"]
                    result["Error Reason1"] = DataZip["Reason of Non Allotment"]
                else:
                    result["QTY"] = "Records Not Found...!!!"

                result["REMRAK"] = "DONE"
                return result

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )

        except Exception as e:
            result["REMRAK"] = "ERROR"
            return result


async def SkyLine_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data

    data_length = len(entry)

    Skyline_company_data = SkyLineDropDown()
    IPO_options_dict = Skyline_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []

    ssl_context = ssl.create_default_context(cafile="pemfile/skylinerta.pem")

    async with aiohttp.ClientSession(
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
    ) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                "client_id": "",
                "application_no": "",
                "pan": panno,
                "app": selected_value,
                "action": "search",
                "image": "Search",
            }
            result = {"PAN": panno}
            tasks.append(
                SkyLine_fetch_allotment(
                    user, session, myobj, panno, result, IPOid, OrderType, ssl_context
                )
            )

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'Records Not Found...!!!' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


async def Cambridge_fetch_allotment(
    user,
    panno,
    result,
    IPOid,
    OrderType,
    selected_value,
    ssl_context,
    retries=3,
    timeout=5,
):
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession(
                headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest",
                }
            ) as session:
                myobj1 = {
                    "drpCompany": "0",
                    "ddlUserTypes": "PAN NO",
                    "__ASYNCPOST": "true",
                    "Button1": "Clear",
                }
                url1 = "https://ipostatus1.cameoindia.com/"
                async with session.get(url1, ssl=ssl_context) as response:
                    data1 = await asyncio.wait_for(response.text(), timeout)
                    soup = BeautifulSoup(data1, "html.parser")
                    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})
                    viewstate_generator = soup.find(
                        "input", {"id": "__VIEWSTATEGENERATOR"}
                    )
                    viewstate = soup.find("input", {"id": "__VIEWSTATE"})
                    if not event_validation or not viewstate_generator or not viewstate:
                        if (attempt + 1) == retries:
                            result["REMRAK"] = "ERROR"
                            return result
                        else:
                            continue  # Retry if required fields are missing

                    __EVENTVALIDATION = event_validation["value"]
                    __VIEWSTATEGENERATOR = viewstate_generator["value"]
                    __VIEWSTATE = viewstate["value"]
                    captcha_img = soup.find("img", {"id": "imgCaptcha"})
                    captcha_src = captcha_img.get("src")
                    url2 = f"https://ipostatus1.cameoindia.com/{captcha_src}"
                    async with session.get(url2) as response:
                        img_data = await response.read()
                        img = Image.open(io.BytesIO(img_data))
                        img = img.resize((150, 50))
                        img = img.crop((5, 5, 160, 55))
                        img = img.resize((150, 50))

                        resized_image_bytes = io.BytesIO()
                        img.save(resized_image_bytes, format="PNG")
                        base64_resized = base64.b64encode(
                            resized_image_bytes.getvalue()
                        ).decode("utf-8")

                        cap_pre_url = "http://141.148.204.115:5000/predict"  #  Oci Captcha Prediction
                        dataa = json.dumps({"image_base": base64_resized})
                        # while True:
                        response = requests.get(cap_pre_url, data=dataa)
                        response = response.json()
                        stqw = response["body"]
                        myobj2 = {
                            "__EVENTVALIDATION": __EVENTVALIDATION,
                            "__VIEWSTATEGENERATOR": __VIEWSTATEGENERATOR,
                            "__VIEWSTATE": __VIEWSTATE,
                            "drpCompany": selected_value,
                            "ddlUserTypes": "PAN NO",
                            "txtfolio": panno,
                            "txt_phy_captcha": stqw.upper(),
                            "__ASYNCPOST": "true",
                            "btngenerate": "Submit",
                            "ScriptManager1": "OrdersPanel|btngenerate",
                            "__EVENTTARGET": "",
                            "__EVENTARGUMENT": "",
                        }

                        async with session.post(
                            url1, data=myobj2, ssl=ssl_context
                        ) as response:
                            data2 = await asyncio.wait_for(response.text(), timeout)
                            soup1 = BeautifulSoup(data2, "html.parser")
                            table = soup1.find(
                                "table", {"class": "table table-bordered text-center"}
                            )
                            if table:
                                headers = []
                                header_row = table.find(
                                    "tr", {"class": "table-success"}
                                )
                                if header_row:
                                    headers = [
                                        th.text.strip()
                                        for th in header_row.find_all("th")
                                    ]
                                else:
                                    print("header Not found")

                                rows = []
                                tbody = table.find("tbody")

                                if tbody:
                                    for row in tbody.find_all("tr"):
                                        cells = [
                                            td.text.strip() for td in row.find_all("td")
                                        ]
                                        rows.append(dict(zip(headers, cells)))
                                else:
                                    print("body Not found")
                                for row in rows:
                                    if (
                                        row["HOLD1"]
                                        != "NO DATA FOUND FOR THIS SEARCH KEY"
                                    ):
                                        result["Name"] = row["HOLD1"]
                                        if row["HOLD1"] != "":
                                            result["Qty"] = row["ALLOTED_SHARES"]
                                            if int(row["ALLOTED_SHARES"]) >= 0:
                                                await update_database(
                                                    user,
                                                    IPOid,
                                                    panno,
                                                    int(row["ALLOTED_SHARES"]),
                                                    OrderType,
                                                )

                                        result["Refund Amount"] = row["REFUND_AMOUNT"]
                                        result["Refund Mode"] = row["REFUND_MODE"]
                                        result["PJ_NO"] = row["PJ_NO"]

                                    else:
                                        result["Qty"] = "Records Not Found...!!!"

                                result["REMRAK"] = "DONE"
                                return result
                            else:
                                print("Table not found for PAN", panno)
                                html_content = str(soup1)
                                html_content = html_content.encode().decode(
                                    "unicode_escape"
                                )
                                match = re.search(r"showpop6\('(.+?)'\)", html_content)
                                if match:
                                    error_message = match.group(1)
                                    if error_message:
                                        print(
                                            f"Error message for PAN {panno}: {error_message}"
                                        )
                                        result["Qty"] = error_message
                                        result["REMRAK"] = "ERROR"
                                        return result

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(
                f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})"
            )
            # if attempt == 2:
            result["Qty"] = e
            result["REMRAK"] = "ERROR"
            return result

        except:
            traceback.print_exc()
            result["REMRAK"] = "ERROR"
            return result


async def Cambridge_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data

    data_length = len(entry)

    Cambridge_company_data = CambridgeDropDown()
    IPO_options_dict = Cambridge_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")

    results = []

    ssl_context = ssl.create_default_context(cafile="pemfile/cambridge.pem")

    tasks = []
    for i in range(data_length):
        panno = entry[i]
        result = {"PAN": panno}
        tasks.append(
            Cambridge_fetch_allotment(
                user, panno, result, IPOid, OrderType, selected_value, ssl_context
            )
        )

    responses = await asyncio.gather(*tasks)
    results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    )

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="IPO Allotment")

    return response


def get_pancards(request, IPOid, OrderType, group=None, IPOType=None, InvestType=None):
    if request.method == "POST":
        Pan_chck = request.POST.get("Pannocheck", "")
        Data = []
        Gp_Name = group
        IPOTypefilter = IPOType
        InvestorTypeFilter = InvestType
        if Pan_chck == "All Record":
            entry = OrderDetail.objects.filter(
                user=request.user,
                Order__OrderIPOName_id=IPOid,
                Order__OrderType=OrderType,
            )

        elif Pan_chck == "Pending":
            entry = OrderDetail.objects.filter(
                user=request.user,
                Order__OrderIPOName_id=IPOid,
                Order__OrderType=OrderType,
                AllotedQty__isnull=True,
            )

        if Gp_Name == "All" and IPOTypefilter == "All" and InvestorTypeFilter == "All":
            pass
        elif IPOTypefilter == "All" and Gp_Name == "All":
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        elif IPOTypefilter == "All" and InvestorTypeFilter == "All":
            entry = entry.filter(Order__OrderGroup__GroupName=Gp_Name)
        elif InvestorTypeFilter == "All" and Gp_Name == "All":
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        elif IPOTypefilter == "All":
            entry = entry.filter(
                Order__OrderGroup__GroupName=Gp_Name,
                Order__InvestorType=InvestorTypeFilter,
            )
        elif Gp_Name == "All":
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        elif InvestorTypeFilter == "All":
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Gp_Name
            )
        else:
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__OrderGroup__GroupName=Gp_Name,
                Order__InvestorType=InvestorTypeFilter,
            )

        if Gp_Name != "All" and is_valid_queryparam(Gp_Name):
            entry = entry.filter(Order__OrderGroup__GroupName=Gp_Name)

        if IPOTypefilter != "All" and is_valid_queryparam(IPOTypefilter):
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)

        if InvestorTypeFilter != "All" and is_valid_queryparam(InvestorTypeFilter):
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)

        if entry is not None and entry.exists():
            for order_detail in entry:
                if (
                    order_detail.OrderDetailPANNo
                    and order_detail.OrderDetailPANNo.PANNo
                ):
                    Data.append(order_detail.OrderDetailPANNo.PANNo)

        return JsonResponse({"pancards": list(Data)})
    return JsonResponse({"error": "User not authenticated"}, status=401)


def IPO_Allotment(request, IPOid, OrderType, group=None, IPOType=None, InvestType=None):
    if request.method == "POST":
        ipo_register = request.POST.get("ipo_register", "")
        ipo_name = request.POST.get("secondary_dropdown", "")
        Pan_chck = request.POST.get("Pannocheck", "")
        panlist = request.POST.get("pancards", "")
        if panlist:
            panlist = json.loads(panlist)
        PRI_limit = CustomUser.objects.get(username=request.user)
        is_premium_user = PRI_limit.Allotment_access

        # Gp_Name =  group
        # IPOTypefilter =  IPOType
        # InvestorTypeFilter =  InvestType
        if str(is_premium_user) == "True":
            Data = panlist
            #     Data = []
            #     if Pan_chck == 'All Record':
            #         entry =  OrderDetail.objects.filter(
            #                 user=request.user, Order__OrderIPOName_id=IPOid ,Order__OrderType=OrderType)

            #     elif Pan_chck == 'Pending':
            #         entry =  OrderDetail.objects.filter(
            #                 user=request.user, Order__OrderIPOName_id=IPOid ,Order__OrderType=OrderType,AllotedQty__isnull=True)

            #     if Gp_Name == 'All' and IPOTypefilter == 'All' and InvestorTypeFilter == 'All':
            #         pass
            #     elif IPOTypefilter == 'All' and Gp_Name=='All':
            #         entry =  entry.filter(Order__InvestorType=InvestorTypeFilter)
            #     elif IPOTypefilter == 'All' and InvestorTypeFilter=='All':
            #         entry = entry.filter(Order__OrderGroup__GroupName=Gp_Name)
            #     elif InvestorTypeFilter=='All' and  Gp_Name=='All':
            #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter)
            #     elif IPOTypefilter == 'All':
            #         entry = entry.filter(Order__OrderGroup__GroupName=Gp_Name, Order__InvestorType=InvestorTypeFilter)
            #     elif Gp_Name =='All':
            #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__InvestorType=InvestorTypeFilter)
            #     elif InvestorTypeFilter=='All':
            #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Gp_Name)
            #     else:
            #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Gp_Name,Order__InvestorType=InvestorTypeFilter)

            #     if Gp_Name != 'All'  and is_valid_queryparam(Gp_Name):
            #         entry = entry.filter(Order__OrderGroup__GroupName = Gp_Name)

            #     if IPOTypefilter != 'All'  and is_valid_queryparam(IPOTypefilter):
            #         entry = entry.filter(Order__OrderCategory=IPOTypefilter)

            #     if InvestorTypeFilter != 'All'  and is_valid_queryparam(InvestorTypeFilter):
            #         entry = entry.filter(Order__InvestorType=InvestorTypeFilter)

            #     if entry is not None and entry.exists():
            #         for order_detail in entry:
            #             if order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.PANNo:
            #                 Data.append(order_detail.OrderDetailPANNo.PANNo)

            if ipo_register == "Linkin":
                user = request.user
                response = asyncio.run(
                    linkin_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )
                return response

            elif ipo_register == "Cambridge":
                user = request.user
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response = asyncio.run(
                    Cambridge_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )
                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(linkin_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # except RuntimeError as e:
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(linkin_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # finally:
                #     # Cleanup
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

            elif ipo_register == "Kfintech":
                user = request.user
                response = asyncio.run(
                    Kfintech_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )
                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(Kfintech_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # except RuntimeError as e:
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(Kfintech_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))

                # finally:
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

            elif ipo_register == "BigShare":
                user = request.user
                response = asyncio.run(
                    BigShare_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )
                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(BigShare_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # except RuntimeError as e:
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(BigShare_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))

                # finally:
                #     # Cleanup
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

            elif ipo_register == "Purva":
                user = request.user
                response = asyncio.run(
                    Purva_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )

                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(Purva_allotment(user, IPOid, OrderType, ipo_register, ipo_name ,Data))
                # except RuntimeError as e:
                #     # Handle the case where the loop is already closed
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(Purva_allotment(user, IPOid, OrderType, ipo_register, ipo_name ,Data))

                # finally:
                #     # Cleanup
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

            elif ipo_register == "SkyLine":
                user = request.user
                response = asyncio.run(
                    SkyLine_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )

                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(SkyLine_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # except RuntimeError as e:
                #     # Handle the case where the loop is already closed
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(SkyLine_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))

                # finally:
                #     # Cleanup
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

            elif ipo_register == "Integrated":
                user = request.user
                response = asyncio.run(
                    Integrated_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )

                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(Integrated_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # except RuntimeError as e:
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(Integrated_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))

                # finally:
                #     # Cleanup
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

            elif ipo_register == "Maashitla":
                user = request.user
                response = asyncio.run(
                    Maashitla_allotment(
                        user, IPOid, OrderType, ipo_register, ipo_name, Data
                    )
                )

                # try:
                #     loop = asyncio.get_event_loop()
                # except RuntimeError:
                #     loop = asyncio.new_event_loop()
                #     asyncio.set_event_loop(loop)
                # try:
                #     response = loop.run_until_complete(Maashitla_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                # except RuntimeError as e:
                #     if str(e) == "Event loop is closed":
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         response = loop.run_until_complete(Maashitla_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))

                # finally:
                #     # Cleanup
                #     pending = asyncio.all_tasks(loop)
                #     for task in pending:
                #         task.cancel()
                #     loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                #     loop.close()

                return response

    return redirect(f"/{IPOid}/OrderDetail/{OrderType}/All/All/All")


#  Allotment Check End ----!>
@allowed_users(allowed_roles=["Broker"])
def ChangePassword(request):
    if request.method == "POST":
        NewPassword = request.POST.get("NewPassword", "")
        ConfirmPassword = request.POST.get("ConfirmPassword", "")
        if NewPassword == ConfirmPassword:
            u = User.objects.get(username__exact=request.user)
            u.set_password(ConfirmPassword)
            u.save()
            uuser = authenticate(username=request.user, password=ConfirmPassword)

            login(request, uuser)
            products = CurrentIpoName.objects.filter(user=request.user)
            params = {"product": products}

            return render(request, "index.html", params)

        else:
            messages.error(request, "New Password and Confirm Password is not equal")
            return redirect("/")

    return redirect("/")


@allowed_users(allowed_roles=["Broker"])
def Changepassword(request):
    if request.method == "POST":
        NewPassword = request.POST.get("NewPassword", "")
        ConfirmPassword = request.POST.get("ConfirmPassword", "")
        if NewPassword == ConfirmPassword:
            u = CustomUser.objects.get(username=request.user)
            u.set_password(ConfirmPassword)
            u.save()
            uuser = authenticate(username=request.user, password=ConfirmPassword)

            login(request, uuser)
            products = CurrentIpoName.objects.filter(user=request.user).order_by("-id")
            ratelist = []
            for i in products:
                try:
                    Ratelistitem = RateList.objects.get(
                        user=request.user, RateListIPOName_id=i.id
                    )
                except:
                    Ratelistitem = 0
                ratelist.append(Ratelistitem)

            params = {"entry": zip(products, ratelist), "product": products}

            return render(request, "index.html", params)

        else:
            messages.error(request, "New Password and Confirm Password is not equal")
            return redirect("/")

    return redirect("/")


@allowed_users(allowed_roles=["Broker"])
def IPOSETUP(request):
    products = CurrentIpoName.objects.filter(user=request.user)

    page_obj = None
    try:
        page_size = request.POST.get("Ip_page_size")
        if page_size != "" and page_size is not None:
            request.session["Ip_page_size"] = page_size
        else:
            page_size = request.session["Ip_page_size"]
    except:
        page_size = request.session.get("Ip_page_size", 50)

    Data = []
    if page_size == "All":
        all_rows = True
        paginator = Paginator(products, len(products))
        page_number = request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():

        start_index = (page_obj.number - 1) * page_obj.paginator.per_page

        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "IPOName": order_detail.IPOName,
                "IPOType": order_detail.IPOType,
                "IPOPrice": order_detail.IPOPrice,
                "PreOpenPrice": order_detail.PreOpenPrice,
                "LotSizeRetail": (
                    order_detail.LotSizeRetail
                    if (order_detail.LotSizeRetail is not None)
                    else "-"
                ),
                "LotSizeSHNI": (
                    order_detail.LotSizeSHNI
                    if (order_detail.LotSizeSHNI is not None)
                    else "-"
                ),
                "LotSizeBHNI": (
                    order_detail.LotSizeBHNI
                    if (order_detail.LotSizeBHNI is not None)
                    else "-"
                ),
                "TotalIPOSzie": order_detail.TotalIPOSzie,
                "RetailPercentage": order_detail.RetailPercentage,
                "BHNIPercentage": (
                    order_detail.BHNIPercentage
                    if (order_detail.BHNIPercentage is not None)
                    else "-"
                ),
                "SHNIPercentage": (
                    order_detail.SHNIPercentage
                    if (order_detail.SHNIPercentage is not None)
                    else "-"
                ),
                "Remark": order_detail.Remark,
                "sr_no": start_index + i + 1,
            }
            Data.append(entry_data)

    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = (
        "<thead><tr style='text-align: center;white-space: nowrap; width:100%' >"
    )
    html_table += "<th scope='col' style='width:90px;'>Sr No. &nbsp;</th>"
    html_table += "<th scope='col'>Name &nbsp;</th>"
    html_table += "<th scope='col'>IPO Type &nbsp;</th>"
    html_table += "<th scope='col'>IPO Price &nbsp;</th>"
    html_table += "<th scope='col'>Pre-Open Price &nbsp;</th>"
    html_table += "<th scope='col'>Lot Retail&nbsp;</th>"
    html_table += "<th scope='col'>Lot SHNI&nbsp;</th>"
    html_table += "<th scope='col'>Lot BHNI&nbsp;</th>"
    html_table += "<th scope='col'>Total IPOSize in Cr.&nbsp;</th>"
    html_table += "<th scope='col'>Retail %&nbsp;</th>"
    html_table += "<th scope='col'>BHNI %&nbsp;</th>"
    html_table += "<th scope='col'>SHNI %&nbsp;</th>"
    html_table += "<th scope='col'>Remark&nbsp;</th>"
    html_table += "<th scope='col'>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"

    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td>{row.sr_no}</td>"
        html_table += f"<td><a <a href='/{row.id}/Order'>{row.IPOName}</a></td>"
        html_table += f"<td>{row.IPOType}</td>"
        html_table += f"<td>{row.IPOPrice}</td>"
        html_table += f"<td>{row.PreOpenPrice}</td>"
        html_table += f"<td>{row.LotSizeRetail}</td>"
        html_table += f"<td>{row.LotSizeSHNI }</td>"
        html_table += f"<td>{row.LotSizeBHNI}</td>"
        html_table += f"<td>{row.TotalIPOSzie} </td>"
        html_table += f"<td>{row.RetailPercentage} </td>"
        if row.IPOType == "MAINBOARD":
            html_table += f"<td>{row.BHNIPercentage} </td>"
            html_table += f"<td>{row.SHNIPercentage} </td>"
        else:
            html_table += f"<td> - </td>"
            html_table += f"<td> - </td>"
        html_table += f"<td>{row.Remark} </td>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='edit/{ row.id }?page={page_number}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button>\
            <button type='button' class='btn btn-outline-danger' \
                        onclick='document.getElementById('{ row.id }').style.display='block'' style='width: 72px;'\
                        data-toggle='modal' data-target='#{ row.id }'>Delete</button></td>"

        html_table += "</tr>\n"
    html_table += "</tbody></table>"

    for i, row in df.iterrows():
        html_table += f"""
            <div class="modal fade" id="{ row.id }" tabindex="-1" role="dialog"
                    aria-labelledby="exampleModalLabel" aria-hidden="true">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header" style="border-bottom: 1px solid black;">
                                <b>
                                    <h5 class="modal-title" id="exampleModalLabel">Delete IPO</h5>
                                </b>
                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body" style="white-space: normal;">
                                <center>
                                    <p>Are you sure you want to delete { row.IPOName } IPO?</p>
                                    <div class="form-row">
                                        <div class="form-group col-md-6">
                                            <button type="button" class="btn btn-outline-secondary"
                                                data-dismiss="modal" style="width: 50%;"
                                                class="cancelbtn">Cancel</button>
                                        </div>
                                        <div class="form-group col-md-6">
                                            <button type="button" class="btn btn-outline-danger" style="width: 50%;"
                                                class="deletebtn"
                                                onclick="window.location.href='delete/{ row.id }?page={page_number}';">Delete</button>
                                        </div>
                                </center>
                            </div>
                        </div>
                    </div>
                </div>
        """
    params = {"html_table": html_table, "page_obj": page_obj, "Ip_page_size": page_size}
    return render(request, "IPOSETUP.html", params)


@allowed_users(allowed_roles=["Broker"])
def ClientSetup(request, PanNoId="None"):
    products = ClientDetail.objects.filter(user=request.user)
    Group = GroupDetail.objects.filter(user=request.user)

    page_obj = None
    try:
        page_size = request.POST.get("client_page_size")
        if page_size != "" and page_size is not None:
            request.session["client_page_size"] = page_size
        else:
            page_size = request.session["client_page_size"]
    except:
        page_size = request.session.get("client_page_size", 50)

    Data = []
    if page_size == "All":
        all_rows = True
        paginator = Paginator(products, len(products))
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():

        start_index = (page_obj.number - 1) * page_obj.paginator.per_page

        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "PANNo": order_detail.PANNo,
                "Name": order_detail.Name,
                "Group": order_detail.Group,
                "ClientIdDpId": order_detail.ClientIdDpId,
                "sr_no": start_index + i + 1,
            }
            Data.append(entry_data)
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th scope='col' style='width:90px;'>Sr No. &nbsp;</th>"
    html_table += "<th scope='col'>PAN No. &nbsp;</th>"
    html_table += "<th scope='col'>Name &nbsp;</th>"
    html_table += "<th scope='col'>Group &nbsp;</th>"
    html_table += "<th scope='col'>Client-ID/DP-ID &nbsp;</th>"
    html_table += "<th scope='col'>Action&nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"

    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td>{row.sr_no}</td>"
        html_table += f"<td>{row.PANNo}</td>"
        html_table += f"<td>{row.Name}</td>"
        html_table += f"<td>{row.Group}</td>"
        html_table += f"<td>{row.ClientIdDpId}</td>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='EditClient/{ row.id }?page={page_number}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button>\
            <button type='button' class='btn btn-outline-danger' \
                        onclick='document.getElementById('{ row.id }').style.display='block'' style='width: 72px;'\
                        data-toggle='modal' data-target='#{ row.id }'>Delete</button></td>"

        html_table += "</tr>\n"
    html_table += "</tbody></table>"

    for i, row in df.iterrows():
        html_table += f"""
            <div class="modal fade" id="{ row.id }" tabindex="-1" role="dialog"
                aria-labelledby="exampleModalLabel" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header" style="border-bottom: 1px solid black;">
                            <b>
                                <h5 class="modal-title" id="exampleModalLabel">Delete Client</h5>
                            </b>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body"  style="white-space: normal;">
                            <center>
                                <p>Are you sure you want to delete { row.PANNo } Client?</p>
                                <div class="form-row">
                                    <div class="form-group col-md-6">
                                        <button type="button" class="btn btn-outline-secondary" data-dismiss="modal"
                                        style="width:50%;">Cancel</button>
                                    </div>
                                    <div class="form-group col-md-6">
                                        <button type="button" class="btn btn-outline-danger"
                                        style="width:50%;" onclick="window.location.href='DeleteClient/{ row.id }?page={page_number}';"
                                        autofocus="autofocus" onfocus="this.select()">Delete</button>
                                    </div>
                                </div>
                            </center>
                        </div>
                    </div>
                </div>
            </div>
        """

    if PanNoId != "None":
        employee = ClientDetail.objects.get(id=PanNoId, user=request.user)
        params = {
            "html_table": html_table,
            "Group": Group.order_by("GroupName"),
            "employee": employee,
            "page_obj": page_obj,
            "client_page_size": page_size,
        }
    else:
        params = {
            "html_table": html_table,
            "Group": Group.order_by("GroupName"),
            "page_obj": page_obj,
            "client_page_size": page_size,
        }

    return render(request, "ClientSetup.html", params)


@allowed_users(allowed_roles=["Broker"])
def GroupSetup(request):
    products = GroupDetail.objects.filter(user=request.user)

    page_obj = None
    try:
        page_size = request.POST.get("Gp_page_size")
        if page_size != "" and page_size is not None:
            request.session["Gp_page_size"] = page_size
        else:
            page_size = request.session["Gp_page_size"]
    except:
        page_size = request.session.get("Gp_page_size", 50)

    Data = []
    if page_size == "All":
        all_rows = True
        paginator = Paginator(products, len(products))
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():

        start_index = (page_obj.number - 1) * page_obj.paginator.per_page

        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "GroupName": order_detail.GroupName,
                "MobileNo": order_detail.MobileNo,
                "Email": order_detail.Email,
                "Address": order_detail.Address,
                "Remark": order_detail.Remark,
                "sr_no": start_index + i + 1,
            }
            Data.append(entry_data)
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th scope='col' style='width:90px;'>Sr No. &nbsp;</th>"
    html_table += "<th scope='col'>Group Name &nbsp;</th>"
    html_table += "<th scope='col'>Mobile No &nbsp;</th>"
    html_table += "<th scope='col'>Email &nbsp;</th>"
    html_table += "<th scope='col'>Address &nbsp;</th>"
    html_table += "<th scope='col'>Remark &nbsp;</th>"
    html_table += "<th scope='col'>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"

    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td>{row.sr_no}</td>"
        html_table += f"<td>{row.GroupName}</td>"
        html_table += f"<td>{row.MobileNo}</td>"
        html_table += f"<td>{row.Email}</td>"
        html_table += f"<td>{row.Address}</td>"
        html_table += f"<td>{row.Remark}</td>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='EditGroup/{ row.id }?page={page_number}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button>\
            <button type='button' class='btn btn-outline-danger' \
                        onclick='document.getElementById('{ row.id }').style.display='block'' style='width: 72px;'\
                        data-toggle='modal' data-target='#{ row.id }'>Delete</button></td>"

        html_table += "</tr>\n"
    html_table += "</tbody></table>"

    for i, row in df.iterrows():
        html_table += f"""
            <div class="modal fade" id="{ row.id }" tabindex="-1" role="dialog"
                        aria-labelledby="exampleModalLabel" aria-hidden="true">
                        <div class="modal-dialog">
                            <div class="modal-content">
                                <div class="modal-header" style="border-bottom: 1px solid black;">
                                    <b>
                                        <h5 class="modal-title" id="exampleModalLabel">Delete Kostak Group</h5>
                                    </b>
                                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                        <span aria-hidden="true">&times;</span>
                                    </button>
                                </div>
                                <div class="modal-body" style="white-space: normal;">
                                    <center>
                                        <p>Are you sure you want to delete { row.GroupName } group?</p>
                                        <div class="form-row">
                                            <div class="form-group col-md-6">
                                                <button type="button" class="btn btn-outline-secondary" data-dismiss="modal"
                                                style="width:50%;">Cancel</button>
                                            </div>
                                            <div class="form-group col-md-6">
                                                <button type="button" class="btn btn-outline-danger"
                                                style="width:50%;" onclick="window.location.href='DeleteGroup/{ row.id }?page={page_number}';">Delete</button>
                                            </div>
                                        </div>

                                    </center>
                                </div>
                            </div>
                        </div>
                    </div>
        """
    params = {"html_table": html_table, "page_obj": page_obj, "Gp_page_size": page_size}
    return render(request, "GroupSetup.html", params)


@allowed_users(allowed_roles=["Broker"])
def AddCustomerUser(request):
    group = GroupDetail.objects.filter(user=request.user)
    if request.method == "POST":
        try:
            username = request.POST.get("username", "")
            password = request.POST.get("password", "")
            email = request.POST.get("email", "")
            first_name = request.POST.get("first_name", "")
            last_name = request.POST.get("last_name", "")
            Group1 = request.POST.get("Group", "")
            gid = GroupDetail.objects.get(GroupName=Group1, user=request.user).id
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=email,
                last_name=last_name,
                first_name=first_name,
                Broker_id=request.user.id,
                Group_id=gid,
            )
            user.save()
            group11 = Group.objects.get(name="Customer")
            user.groups.add(group11)
            messages.success(request, "Successfully Added User")
            return redirect("/")

        except:
            messages.error(request, "Error.")
    return render(
        request, "AddCustomerUser.html", {"Group": group.order_by("GroupName")}
    )


@allowed_users(allowed_roles=["Broker"])
def AddIPO(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name", "").upper()
            CurrentIpoName.objects.get(IPOName=name, user=request.user)
            messages.error(request, "IPO Already Exist.")

        except:
            IPOType = request.POST.get("IPOType", "")
            name = request.POST.get("name", "")
            IPOPrice = request.POST.get("IPOPrice", "")
            TotalIPOSize = request.POST.get("TotalIPOSzie", "")
            RetailPercentage = request.POST.get("RetailPercentage", "")
            LotSizeRetail = request.POST.get("LotSizeRetail", "")
            Remark = request.POST.get("Remark", "")

            if IPOType == "MAINBOARD":
                LotSizeSHNI = request.POST.get("LotSizeSHNI")
                LotSizeBHNI = request.POST.get("LotSizeBHNI")
                SHNIPercentage = request.POST.get("SHNIPercentage", "")
                BHNIPercentage = request.POST.get("BHNIPercentage", "")
            else:
                LotSizeSHNI = None
                LotSizeBHNI = None
                SHNIPercentage = ""
                BHNIPercentage = ""

            currentiponame = CurrentIpoName(
                user=request.user,
                IPOType=IPOType,
                IPOName=name,
                IPOPrice=IPOPrice,
                LotSizeRetail=LotSizeRetail,
                LotSizeSHNI=LotSizeSHNI,
                LotSizeBHNI=LotSizeBHNI,
                TotalIPOSzie=TotalIPOSize,
                BHNIPercentage=BHNIPercentage,
                SHNIPercentage=SHNIPercentage,
                RetailPercentage=RetailPercentage,
                Remark=Remark,
                PreOpenPrice=IPOPrice,
            )

            user = request.user
            O_limit = CustomUser.objects.get(username=user)

            if O_limit.IPO_limit is not None:

                user = request.user
                IPO_Count = CurrentIpoName.objects.filter(user=user).count()
                IPO_Limit = int(O_limit.IPO_limit)

                if IPO_Count >= IPO_Limit:
                    messages.error(
                        request,
                        f"You have reached the limit of {IPO_Limit} IPO Limits.",
                    )
                    return redirect("/IPOSETUP")

            currentiponame.save()
            messages.success(request, "IPO Added successfully.")
            return redirect("/IPOSETUP")
    return redirect("/IPOSETUP")


@allowed_users(allowed_roles=["Broker"])
def AddGroup(request):
    if request.method == "POST":
        try:
            GroupName = request.POST.get("GroupName", "").upper()
            groupdetail = GroupDetail.objects.get(
                GroupName=GroupName, user=request.user
            )
            messages.error(request, "Group Already Exist.")

        except:
            GroupName = request.POST.get("GroupName", "")
            Email = request.POST.get("Email", "")
            if Email:
                try:
                    validate_email(Email)
                except:
                    messages.error(request, "Invalid email format.")
                    return redirect("/GroupSetup")

            MobileNo = request.POST.get("MobileNo", "")
            if MobileNo:
                if len(MobileNo) != 10 or not MobileNo.isdigit():
                    # messages.error(request, 'Invalid Mobile No.')
                    messages.error(
                        request,
                        "Invalid Mobile Number. Please enter exactly 10 digits.",
                    )
                    return redirect("/GroupSetup")
                # elif len(MobileNo) == 10:

            Address = request.POST.get("Address", "")
            Remark = request.POST.get("Remark", "")
            groupdetail = GroupDetail(
                user=request.user,
                GroupName=GroupName,
                MobileNo=MobileNo,
                Address=Address,
                Remark=Remark,
                Email=Email,
            )

            user = request.user
            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Group_limit is not None:

                user = request.user
                Group_Count = GroupDetail.objects.filter(user=user).count()
                Gropu_Limit = int(O_limit.Group_limit)

                if Group_Count >= Gropu_Limit:
                    messages.error(
                        request,
                        f"You have reached the limit of {Gropu_Limit} Group Limits.",
                    )
                    return redirect("/GroupSetup")

            groupdetail.save()
            messages.success(request, "Group Added successfully.")
            return redirect("/GroupSetup")
    return redirect("/GroupSetup")


@allowed_users(allowed_roles=["Broker"])
def AddGroupFromPlaceOrder(request, IPOid, Action):
    if request.method == "POST":
        user = request.user
        O_limit = CustomUser.objects.get(username=user)
        try:
            GroupName = request.POST.get("GroupName", "").upper()
            groupdetail = GroupDetail.objects.get(
                GroupName=GroupName, user=request.user
            )
            messages.error(request, "Group Already Exist.")

        except:
            GroupName = request.POST.get("GroupName", "").upper()
            groupdetail = GroupDetail(user=request.user, GroupName=GroupName)
            if O_limit.Group_limit is not None:
                Group_Count = GroupDetail.objects.filter(user=user).count()
                Gropu_Limit = int(O_limit.Group_limit)
                if Group_Count >= Gropu_Limit:
                    messages.error(
                        request,
                        f"You have reached the limit of {Gropu_Limit} Group Limits.",
                    )
                    if Action == "BUY":
                        return redirect(f"/{IPOid}/BUY")
                    elif Action == "SELL":
                        return redirect(f"/{IPOid}/SELL")
            groupdetail.save()
        if Action == "BUY":
            return redirect(f"/BUY/{IPOid}/{GroupName}")
        elif Action == "SELL":
            return redirect(f"/SELL/{IPOid}/{GroupName}")
        else:
            return redirect("/")


@allowed_users(allowed_roles=["Broker"])
def AddClient(request):
    Group = GroupDetail.objects.filter(user=request.user)
    if request.method == "POST":
        try:
            PANNo = request.POST.get("PANNo", "").upper()
            ClientDetail.objects.get(PANNo=PANNo.upper(), user=request.user)
            messages.error(request, "Client Already Exist.")

        except:
            PANNo = request.POST.get("PANNo", "")
            Name = request.POST.get("Name", "")
            Group = request.POST.get("Group", "")
            ClientIdDpId = request.POST.get("ClientIdDpId", "")
            gid = GroupDetail.objects.get(GroupName=Group, user=request.user).id
            currentiponame = ClientDetail(
                user=request.user,
                PANNo=PANNo.upper(),
                Name=Name,
                Group_id=gid,
                ClientIdDpId=ClientIdDpId,
            )

            user = request.user
            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Client_limit is not None:

                user = request.user
                Client_Count = ClientDetail.objects.filter(user=user).count()
                Client_Limit = int(O_limit.Client_limit)

                if Client_Count >= Client_Limit:
                    messages.error(
                        request,
                        f"You have reached the limit of {Client_Limit} Client limits.",
                    )
                    return redirect("/ClientSetup")

            currentiponame.save()
            messages.success(request, "Client Added successfully.")
            return redirect("/ClientSetup")
    return redirect("/ClientSetup")


@allowed_users(allowed_roles=["Broker"])
def edit(request, IPOid):
    page_number = request.GET.get("page", "1")
    employee = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    return render(
        request, "edit.html", {"employee": employee, "page_number": page_number}
    )


@allowed_users(allowed_roles=["Broker"])
def EditClient(request, PanNoId):
    page_number = request.GET.get("page", "1")
    Group = GroupDetail.objects.filter(user=request.user)

    employee = ClientDetail.objects.get(id=PanNoId, user=request.user)
    return render(
        request,
        "EditClient.html",
        {
            "employee": employee,
            "Group": Group.order_by("GroupName"),
            "page_number": page_number,
        },
    )


@allowed_users(allowed_roles=["Broker"])
def EditGroup(request, GroupNameId):
    page_number = request.GET.get("page", "1")

    employee = GroupDetail.objects.get(id=GroupNameId, user=request.user)
    return render(
        request, "EditGroup.html", {"employee": employee, "page_number": page_number}
    )


def EditOrder(request, OrderId, IPOid, Grpf, OrCtf, InTyf):
    page_number = request.GET.get("page")
    order = Order.objects.get(OrderIPOName_id=IPOid, id=OrderId, user=request.user)
    Group = GroupDetail.objects.filter(user=request.user)
    Group_sorted = sorted(Group, key=lambda x: x.GroupName)
    IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    return render(
        request,
        "EditOrder.html",
        {
            "employee": order,
            "Group": Group_sorted,
            "Grpf": Grpf,
            "OrCtf": OrCtf,
            "InTyf": InTyf,
            "IPOid": IPOid,
            "IPOName": IPO,
            "page_number": page_number,
        },
    )


# ipo update fun
@allowed_users(allowed_roles=["Broker"])
def update(request, IPOid):
    page_number = request.GET.get("page", "1")
    employee = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    n = 1
    if request.method == "POST":
        if n == 1:
            name = request.POST.get("name", "").upper()
            for j in CurrentIpoName.objects.filter(user=request.user).values("IPOName"):
                if name == j.get("IPOName"):
                    if name != employee.IPOName:
                        messages.error(request, "IPO Already Exist.")
                        n = 0
                        break
            if n == 0:
                return redirect(f"/edit/{IPOid}")
        if n == 1:
            IPOType = request.POST.get("IPOType", "")
            name = request.POST.get("name", "")
            IPOPrice = request.POST.get("IPOPrice", "")
            LotSizeRetail = request.POST.get("LotSizeRetail", "")
            TotalIPOSize = request.POST.get("TotalIPOSize", "")
            RetailPercentage = request.POST.get("RetailPercentage", "")
            Remark = request.POST.get("Remark", "")
            if IPOType == "MAINBOARD":
                LotSizeBHNI = request.POST.get("LotSizeBHNI")
                LotSizeSHNI = request.POST.get("LotSizeSHNI")
                BHNIPercentage = request.POST.get("BHNIPercentage")
                SHNIPercentage = request.POST.get("SHNIPercentage")
            else:
                LotSizeBHNI = None
                LotSizeSHNI = None
                BHNIPercentage = ""
                SHNIPercentage = ""

            employee.IPOType = IPOType
            employee.IPOName = name
            employee.IPOPrice = IPOPrice
            employee.LotSizeRetail = LotSizeRetail
            employee.TotalIPOSzie = TotalIPOSize
            employee.RetailPercentage = RetailPercentage
            employee.Remark = Remark
            employee.LotSizeBHNI = LotSizeBHNI
            employee.LotSizeSHNI = LotSizeSHNI
            employee.BHNIPercentage = BHNIPercentage
            employee.SHNIPercentage = SHNIPercentage

            employee.save()
            messages.success(request, "IPO Edit successfully.")
            return redirect(f"/IPOSETUP?page={page_number}")
    return render(request, "edit.html", {"employee": employee})


@allowed_users(allowed_roles=["Broker"])
def updatepreopenprice(request, IPOid, group, IPOType, InvestType):
    Groupfilter = unquote(group)
    IPOTypefilter = unquote(IPOType)
    InvestTypefilter = unquote(InvestType)
    employee = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    entry = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName_id=IPOid)

    if request.method == "POST":
        UpdatePreOpenPrice = request.POST.get("PreOpenPrice", "")
        employee.PreOpenPrice = UpdatePreOpenPrice
        entry.update(PreOpenPrice=UpdatePreOpenPrice)
        employee.save()
        calculate(IPOid, request.user)
        return redirect(
            f"/{IPOid}/Billing/{Groupfilter}/{IPOTypefilter}/{InvestTypefilter}"
        )

    return redirect(
        f"/{IPOid}/Billing/{Groupfilter}/{IPOTypefilter}/{InvestTypefilter}"
    )


@sync_to_async
def Entry_calculate_update(i, IPOName):
    if i.Order.OrderCategory == "Kostak":
        if i.AllotedQty is None:
            i.Amount = 0
            i.save()
            return
        else:
            AllotedQty = i.AllotedQty

        if i.Order.OrderType == "BUY":
            i.Order.Amount = (
                i.Order.Amount
                + (
                    (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                    * float(AllotedQty)
                )
                - i.Order.Rate
            )
            i.Amount = (
                (float(i.PreOpenPrice) - float(IPOName.IPOPrice)) * float(AllotedQty)
            ) - i.Order.Rate
        if i.Order.OrderType == "SELL":
            i.Order.Amount = i.Order.Amount + (
                -1
                * (
                    (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - i.Order.Rate
                )
            )
            i.Amount = -1 * (
                ((float(i.PreOpenPrice) - float(IPOName.IPOPrice)) * float(AllotedQty))
                - i.Order.Rate
            )

    if i.Order.OrderCategory == "Subject To":
        if i.AllotedQty is None:
            i.Amount = 0
            i.save()
            return
        else:
            AllotedQty = i.AllotedQty
        if AllotedQty != 0:
            if i.Order.Method == "Premium":
                Order_rate = i.Order.Rate * float(AllotedQty)
            else:
                Order_rate = i.Order.Rate

            if i.Order.OrderType == "BUY":
                i.Order.Amount = (
                    i.Order.Amount
                    + (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - Order_rate
                )
                i.Amount = (
                    (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                    * float(AllotedQty)
                ) - Order_rate

            if i.Order.OrderType == "SELL":
                i.Order.Amount = i.Order.Amount + (
                    -1
                    * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    )
                )
                i.Amount = -1 * (
                    (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - Order_rate
                )

        else:
            i.Order.Amount = i.Order.Amount + 0

    i.Order.save()
    i.save()


async def Entry_calculate_update_sync(i, IPOName):
    await Entry_calculate_update(i, IPOName)


@sync_to_async
def Order_calculate_update(i, IPOName):
    if i.OrderCategory == "Premium":
        if i.OrderType == "BUY":
            i.Amount = (
                float(IPOName.PreOpenPrice) - (float(IPOName.IPOPrice) + float(i.Rate))
            ) * int(i.Quantity)
        if i.OrderType == "SELL":
            i.Amount = -1 * (
                (
                    float(IPOName.PreOpenPrice)
                    - (float(IPOName.IPOPrice) + float(i.Rate))
                )
                * int(i.Quantity)
            )
        i.save()
    # pass


async def Order_calculate_update_sync(j, IPOName):
    await Order_calculate_update(j, IPOName)


async def entry_Order_Update(entry, order, IPOName):
    Entry_tasks = []
    Order_tasks = []
    for i in entry:
        Entry_tasks.append(Entry_calculate_update_sync(i, IPOName))

    await asyncio.gather(*Entry_tasks)

    for j in order:
        Order_tasks.append(Order_calculate_update_sync(j, IPOName))

    await asyncio.gather(*Order_tasks)


def entry_order_Calculate_sync(entry, order, IPOName):
    async_to_sync(entry_Order_Update)(entry, order, IPOName)


def calculate(IPOid, user, Orderid=None):

    if Orderid is None:
        entry = OrderDetail.objects.filter(user=user, Order__OrderIPOName_id=IPOid)
        order = Order.objects.filter(user=user, OrderIPOName_id=IPOid)

    else:
        entry = OrderDetail.objects.filter(
            user=user, Order__OrderIPOName_id=IPOid, Order_id=Orderid
        )
        order = Order.objects.filter(user=user, OrderIPOName_id=IPOid, id=Orderid)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)

    order.update(Amount=0)
    # for e in entry:
    #     e.Amount = 0
    #     e.save()
    entry.update(Amount=0)
    # for o in order:
    #     o.Amount = 0
    #     o.save()

    # entry_order_Calculate_sync(entry,order,IPOName)

    orders_to_update = []
    entries_to_update = []

    amount = {}
    order_update = {}

    for i in entry:
        key = i.Order.id
        if key not in amount:
            amount[key] = 0
            i_amount = i.Order.Amount
        else:
            i_amount = amount[key]

        if i.Order.OrderCategory == "Kostak":
            if i.AllotedQty is None:
                i.Amount = 0
                # i.save()
                entries_to_update.append(i)
                continue
            else:
                AllotedQty = i.AllotedQty
            if i.Order.OrderType == "BUY":
                i_amount = (
                    i_amount
                    + (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - i.Order.Rate
                )
                i.Amount = (
                    (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                    * float(AllotedQty)
                ) - i.Order.Rate
            if i.Order.OrderType == "SELL":
                i_amount = i_amount + (
                    -1
                    * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - i.Order.Rate
                    )
                )
                i.Amount = -1 * (
                    (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - i.Order.Rate
                )

        if i.Order.OrderCategory == "Subject To":
            if i.AllotedQty is None:
                i.Amount = 0
                entries_to_update.append(i)
                # i.save()
                continue
            else:
                AllotedQty = i.AllotedQty
            if AllotedQty != 0:
                if i.Order.Method == "Premium":
                    Order_rate = i.Order.Rate * float(AllotedQty)
                else:
                    Order_rate = i.Order.Rate
                if i.Order.OrderType == "BUY":

                    i_amount = (
                        i_amount
                        + (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    )
                    i.Amount = (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    ) - Order_rate

                if i.Order.OrderType == "SELL":
                    i_amount = i_amount + (
                        -1
                        * (
                            (
                                (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                * float(AllotedQty)
                            )
                            - Order_rate
                        )
                    )
                    i.Amount = -1 * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    )

            else:
                i_amount = i_amount + 0

        # i.Order.save()
        # i.save()

        i.Order.Amount = i_amount
        amount[key] = i_amount
        order_update[key] = i.Order

        entries_to_update.append(i)

    orders_to_update = list(order_update.values())

    for i in order:
        if i.OrderCategory == "Premium":
            if i.OrderType == "BUY":
                i.Amount = (
                    float(IPOName.PreOpenPrice)
                    - (float(IPOName.IPOPrice) + float(i.Rate))
                ) * int(i.Quantity)
            if i.OrderType == "SELL":
                i.Amount = -1 * (
                    (
                        float(IPOName.PreOpenPrice)
                        - (float(IPOName.IPOPrice) + float(i.Rate))
                    )
                    * int(i.Quantity)
                )
            # i.save()
            orders_to_update.append(i)

        elif i.OrderCategory == "CALL":
            if i.OrderType == "BUY":
                diff = (
                    float(IPOName.PreOpenPrice)
                    - (float(IPOName.IPOPrice) + float(i.Method))
                ) * float(i.Quantity)
                if diff < 0:
                    diff_paid = 0
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * (-1 * float(i.Rate))) + diff_paid

            if i.OrderType == "SELL":
                diff = (
                    (
                        float(IPOName.IPOPrice)
                        + float(i.Method)
                        - float(IPOName.PreOpenPrice)
                    )
                ) * float(i.Quantity)
                if diff > 0:
                    diff_paid = 0
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * float(i.Rate)) + diff_paid

            # i.save()
            orders_to_update.append(i)

        elif i.OrderCategory == "PUT":
            if i.OrderType == "BUY":
                diff = (
                    (
                        float(IPOName.IPOPrice)
                        + float(i.Method)
                        - float(IPOName.PreOpenPrice)
                    )
                ) * float(i.Quantity)
                if diff < 0:
                    diff_paid = 0
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * (-1 * float(i.Rate))) + diff_paid

            if i.OrderType == "SELL":
                diff = (
                    float(IPOName.PreOpenPrice)
                    - (float(IPOName.IPOPrice) + float(i.Method))
                ) * float(i.Quantity)
                if diff > 0:
                    diff_paid = 0
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * float(i.Rate)) + diff_paid

            # i.save()
            orders_to_update.append(i)

    Order.objects.bulk_update(orders_to_update, ["Amount"])
    OrderDetail.objects.bulk_update(entries_to_update, ["Amount"])


async def panupload_calculate(IPOid, user, Orderid=None):
    if Orderid is None or not isinstance(Orderid, list):
        Orderid = [Orderid] if Orderid is not None else []

    # Use sync_to_async properly for database queries
    if Orderid:
        entry = await sync_to_async(OrderDetail.objects.filter)(
            user=user, Order__OrderIPOName_id=IPOid, Order_id__in=Orderid
        )
        order = await sync_to_async(Order.objects.filter)(
            user=user, OrderIPOName_id=IPOid, id__in=Orderid
        )
    else:
        entry = await sync_to_async(OrderDetail.objects.filter)(
            user=user, Order__OrderIPOName_id=IPOid
        )
        order = await sync_to_async(Order.objects.filter)(
            user=user, OrderIPOName_id=IPOid
        )

    IPOName = await asyncio.to_thread(CurrentIpoName.objects.get, id=IPOid, user=user)

    # Update orders and entries amounts to zero
    await sync_to_async(order.update)(Amount=0)
    await sync_to_async(entry.update)(Amount=0)

    updated_orders = []
    updated_entries = []
    entry_list = await sync_to_async(list)(entry)

    for i in entry_list:
        order_obj = await sync_to_async(lambda: i.Order)()
        Order_amount = 0
        if order_obj.OrderCategory == "Kostak":
            if i.AllotedQty is None:
                i.Amount = 0
                updated_entries.append(i)
                continue
            AllotedQty = i.AllotedQty
            if order_obj.OrderType == "BUY":
                Order_amount = (
                    Order_amount
                    + (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - order_obj.Rate
                )
                i.Amount = (
                    (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                    * float(AllotedQty)
                ) - order_obj.Rate
            if order_obj.OrderType == "SELL":
                Order_amount = Order_amount + (
                    -1
                    * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - order_obj.Rate
                    )
                )
                i.Amount = -1 * (
                    (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - order_obj.Rate
                )

        if order_obj.OrderCategory == "Subject To":
            if i.AllotedQty is None:
                i.Amount = 0
                updated_entries.append(i)
                continue
            AllotedQty = i.AllotedQty
            if AllotedQty != 0:
                if i.Order.Method == "Premium":
                    Order_rate = order_obj.Rate * float(AllotedQty)
                else:
                    Order_rate = order_obj.Rate
                if order_obj.OrderType == "BUY":
                    Order_amount = (
                        Order_amount
                        + (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    )
                    i.Amount = (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    ) - Order_rate
                if order_obj.OrderType == "SELL":
                    Order_amount = Order_amount + (
                        -1
                        * (
                            (
                                (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                * float(AllotedQty)
                            )
                            - Order_rate
                        )
                    )
                    i.Amount = -1 * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    )
            else:
                Order_amount = Order_amount + 0

        order_obj.Amount = Order_amount
        await sync_to_async(order_obj.save)()
        updated_entries.append(i)

    Order_list = await sync_to_async(list)(order)
    for i in Order_list:
        if i.OrderCategory == "Premium":
            if i.OrderType == "BUY":
                i.Amount = (
                    float(IPOName.PreOpenPrice)
                    - (float(IPOName.IPOPrice) + float(i.Rate))
                ) * int(i.Quantity)
            if i.OrderType == "SELL":
                i.Amount = -1 * (
                    (
                        float(IPOName.PreOpenPrice)
                        - (float(IPOName.IPOPrice) + float(i.Rate))
                    )
                    * int(i.Quantity)
                )
            updated_orders.append(i)

    await sync_to_async(Order.objects.bulk_update)(updated_orders, ["Amount"])
    await sync_to_async(OrderDetail.objects.bulk_update)(updated_entries, ["Amount"])


def EditOrderPreOpenPrice(
    request,
    IPOid,
    OrderDetailId,
    OrderCategory,
    InvestorType,
    group,
    IPOType,
    InvestType,
):
    orderpreopen = OrderDetail.objects.get(user=request.user, id=OrderDetailId)
    page_number = request.GET.get("page", "1")
    if request.method == "POST":
        PreOpenPrice = request.POST.get("PreOpenPrice", "")
        orderpreopen.PreOpenPrice = PreOpenPrice
        orderpreopen.save()
        UdatepreopenpriceAmount(
            request.user, IPOid, OrderDetailId, OrderCategory, InvestorType
        )
        return redirect(
            f"/{IPOid}/Billing/{group}/{IPOType}/{InvestType}?page={page_number}"
        )

    return redirect(
        f"/{IPOid}/Billing/{group}/{IPOType}/{InvestType}?page={page_number}"
    )


def UdatepreopenpriceAmount(user, IPOid, OrderDetailId, OrderCategory, InvestorType):

    entry = OrderDetail.objects.filter(
        id=OrderDetailId, user=user, Order__OrderIPOName_id=IPOid
    )

    O_IPO_p = OrderDetail.objects.get(
        id=OrderDetailId, user=user, Order__OrderIPOName_id=IPOid
    )

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)

    for i in entry:
        if OrderCategory == "Kostak":
            if i.Order.InvestorType == InvestorType:
                if i.AllotedQty is None:
                    i.Amount = 0
                    i.save()
                    continue
                else:
                    AllotedQty = i.AllotedQty
                if i.Order.OrderType == "BUY":
                    i.Order.Amount = (
                        i.Order.Amount
                        + (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - i.Order.Rate
                    ) - i.Amount
                    i.Amount = (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    ) - i.Order.Rate

                if i.Order.OrderType == "SELL":
                    i.Order.Amount = (
                        i.Order.Amount
                        + (
                            -1
                            * (
                                (
                                    (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                    * float(AllotedQty)
                                )
                                - i.Order.Rate
                            )
                        )
                    ) - i.Amount
                    i.Amount = -1 * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - i.Order.Rate
                    )

        if OrderCategory == "Subject To":
            if i.Order.InvestorType == InvestorType:
                if i.AllotedQty is None:
                    i.Amount = 0
                    i.save()
                    continue
                else:
                    AllotedQty = i.AllotedQty

                if i.Order.Method == "Premium":
                    Order_rate = i.Order.Rate * float(AllotedQty)
                else:
                    Order_rate = i.Order.Rate

                if i.Order.OrderType == "BUY":
                    i.Order.Amount = (
                        i.Order.Amount
                        + (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    ) - i.Amount
                    i.Amount = (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    ) - Order_rate

                if i.Order.OrderType == "SELL":
                    i.Order.Amount = (
                        i.Order.Amount
                        + (
                            -1
                            * (
                                (
                                    (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                    * float(AllotedQty)
                                )
                                - Order_rate
                            )
                        )
                    ) - i.Amount
                    i.Amount = -1 * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - Order_rate
                    )
            else:
                i.Order.Amount = i.Order.Amount + 0

        i.Order.save()
        i.save()


@allowed_users(allowed_roles=["Broker"])
def UpdateClient(request, PANNoId):
    page_number = request.GET.get("page", "1")
    employee = ClientDetail.objects.get(id=PANNoId, user=request.user)
    n = 1
    if request.method == "POST":
        if n == 1:
            PanNo = request.POST.get("PANNo", "").upper()

            for j in ClientDetail.objects.filter(user=request.user).values("PANNo"):
                if PanNo == j.get("PANNo"):
                    if PanNo != employee.PANNo:
                        messages.error(request, "Client Already Exist.")
                        n = 0
                        break
            if n == 0:
                return redirect(f"/EditClient/{PANNoId}?page={page_number}")
        if n == 1:
            PANNo = request.POST.get("PANNo", "")
            Name = request.POST.get("Name", "")
            Group = request.POST.get("Group", "")
            gid = GroupDetail.objects.get(GroupName=Group, user=request.user).id
            ClientIdDpId = request.POST.get("ClientIdDpId", "")
            Remark = request.POST.get("Remark", "")
            employee.PANNo = PANNo.upper()
            employee.Name = Name
            employee.Group_id = gid
            employee.ClientIdDpId = ClientIdDpId
            employee.Remark = Remark
            employee.save()
            return redirect(f"/ClientSetup?page={page_number}")
    return render(request, "EditClient.html", {"employee": employee})


@allowed_users(allowed_roles=["Broker"])
def UpdateGroup(request, GroupNameId):
    page_number = request.GET.get("page", "1")

    employee = GroupDetail.objects.get(id=GroupNameId, user=request.user)
    n = 1
    if request.method == "POST":
        if n == 1:
            Groupname = request.POST.get("GroupName", "").upper()

            for j in GroupDetail.objects.filter(user=request.user).values("GroupName"):
                if Groupname == j.get("GroupName"):
                    if Groupname != employee.GroupName:
                        messages.error(request, "Group Already Exist.")
                        n = 0
                        break
            if n == 0:
                return redirect(f"/EditGroup/{GroupNameId}")
        if n == 1:
            GroupName = request.POST.get("GroupName", "")
            MobileNo = request.POST.get("MobileNo", "")
            if MobileNo:
                if len(MobileNo) != 10 or not MobileNo.isdigit():
                    # messages.error(request, 'Invalid Mobile No.')
                    messages.error(
                        request,
                        "Invalid Mobile Number. Please enter exactly 10 digits.",
                    )
                    return redirect("/GroupSetup")
            Address = request.POST.get("Address", "")
            Email = request.POST.get("Email", "")
            if Email:
                try:
                    validate_email(Email)
                except:
                    messages.error(request, "Invalid email format.")
                    return redirect(f"/EditGroup/{GroupNameId}")
            Remark = request.POST.get("Remark", "")
            employee.GroupName = GroupName
            employee.MobileNo = MobileNo
            employee.Address = Address
            employee.Email = Email
            employee.Remark = Remark
            employee.save()
            return redirect(f"/GroupSetup?page={page_number}")
    return render(request, "EditGroup.html", {"employee": employee})


# @allowed_users(allowed_roles=['Broker'])
# def destroy(request, IPOid):
#     page_number = request.GET.get('page','1')
#     OrderDetail.objects.filter(
#         user=request.user, Order__OrderIPOName_id=IPOid).delete()
#     RateList.objects.filter(
#         user=request.user, RateListIPOName_id=IPOid).delete()
#     Order.objects.filter(
#         user=request.user, OrderIPOName_id=IPOid).delete()
#     ipo = CurrentIpoName.objects.get(id=IPOid, user=request.user)
#     Accounting.objects.filter(id=ipo, user=request.user).update(ipo_name = ipo.IPOName,  status=True,ipo=None)
#     ipo.delete()
#     employee = CurrentIpoName.objects.get(
#         id=IPOid, user=request.user)
#     employee.delete()
#     return redirect(f"/IPOSETUP?page={page_number}")


@allowed_users(allowed_roles=["Broker"])
def destroy(request, IPOid):

    try:
        page_number = request.GET.get("page", "1")

        # Delete related records
        OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPOid
        ).delete()
        RateList.objects.filter(user=request.user, RateListIPOName_id=IPOid).delete()
        Order.objects.filter(user=request.user, OrderIPOName_id=IPOid).delete()

        # Update Accounting: keep ipo_name text, set ipo FK = None
        ipo = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        Accounting.objects.filter(ipo=ipo, user=request.user).update(
            ipo_name=ipo.IPOName, status=True, ipo=None
        )

        # Finally delete IPO
        ipo.delete()

        return redirect("GroupWiseDashboard")

    except CurrentIpoName.DoesNotExist:
        return JsonResponse({"success": False, "message": "IPO not found!"}, status=404)
    except Exception as e:
        return redirect("GroupWiseDashboard")


@allowed_users(allowed_roles=["Broker"])
def DeleteClient(request, PANNoId):
    page_number = request.GET.get("page", "1")
    if OrderDetail.objects.filter(user=request.user, OrderDetailPANNo_id=PANNoId):
        PANNo = ClientDetail.objects.get(id=PANNoId, user=request.user)
        messages.error(
            request,
            f"Client-{PANNo} cannot be deleted as it has order(s) In Any IPO. First Remove Order(s).",
        )
    else:
        employee = ClientDetail.objects.get(id=PANNoId, user=request.user)
        employee.delete()
    return redirect(f"/ClientSetup?page={page_number}")


@allowed_users(allowed_roles=["Broker"])
def DeleteAllClient(request):
    # if request.method == "POST":
    page_number = request.GET.get("page", "1")
    all_clients = ClientDetail.objects.filter(user=request.user)
    pan_data = []
    # protected_pans = []
    for client in all_clients:
        is_used = OrderDetail.objects.filter(
            user=request.user, OrderDetailPANNo_id=client.id
        ).exists()
        if not is_used:
            pan_data.append({"PAN": client.PANNo, "Status": "Deleted"})
            client.delete()
        else:
            # protected_pans.append(str(client.PANNo))
            pan_data.append(
                {"PAN": client.PANNo, "Status": "Not Deleted (Used in Orders)"}
            )

    df = pd.DataFrame(pan_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="PAN Deletion Status")
    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="PAN_Deletion_Status.xlsx"'
    response.set_cookie("download_complete", "1", max_age=10)  # <- Add this
    return response

    # if protected_pans:
    #     messages.error(request, f"These PANs were not deleted as they are used in orders: {', '.join(protected_pans)}")

    # return redirect(f"/ClientSetup?page={page_number}")
    # else:
    #     return redirect(f"/ClientSetup?page={page_number}")
    # if OrderDetail.objects.filter(user=request.user, OrderDetailPANNo_id=PANNoId):
    #     PANNo = ClientDetail.objects.get(
    #         id=PANNoId, user=request.user)
    #     messages.error(
    #         request, f"Client-{PANNo} cannot be deleted as it has order(s) In Any IPO. First Remove Order(s).")
    # else:
    #     employee = ClientDetail.objects.get(
    #         id=PANNoId, user=request.user)
    #     employee.delete()


@allowed_users(allowed_roles=["Broker"])
def DeleteGroup(request, GroupNameId):
    page_number = request.GET.get("page", "1")

    GroupName = GroupDetail.objects.get(id=GroupNameId, user=request.user)
    if ClientDetail.objects.filter(Group_id=GroupNameId).exists():
        messages.error(
            request,
            f"Group {GroupName} cannot be deleted as it has client(s). First Remove Client(s).",
        )
    elif Order.objects.filter(user=request.user, OrderGroup_id=GroupNameId):
        messages.error(
            request,
            f"Group {GroupName} cannot be deleted as it has created order(s). First Remove Order(s).",
        )
    else:
        Accounting.objects.filter(group_id=GroupNameId, user=request.user).update(
            group_name=GroupName.GroupName, status=True, group_id=None
        )
        employee = GroupDetail.objects.get(id=GroupNameId, user=request.user)
        employee.delete()
    return redirect(f"/GroupSetup?page={page_number}")


@allowed_users(allowed_roles=["Broker"])
def DeleteOrder(request, IPOid, OrderId, GrpName, OrderCategory, InvestorType):
    page_number = request.GET.get("page", "1")
    employee = OrderDetail.objects.filter(Order_id=OrderId, user=request.user)
    employee.delete()
    ord = Order.objects.get(id=OrderId, user=request.user)
    ord_grp = ord.OrderGroup
    ord.delete()
    last_order = (
        Order.objects.filter(
            OrderIPOName=IPOid, user=request.user, OrderGroup__GroupName=ord_grp
        )
        .order_by("-id")
        .first()
    )  # Use `-id` to get the latest by ID (or `-created_at` if timestamp exists)
    if last_order:
        last_order.Telly = "False"
        last_order.save()

    return redirect(
        f"/{IPOid}/Order/{GrpName}/{OrderCategory}/{InvestorType}?page={page_number}"
    )


@allowed_users(allowed_roles=["Broker", "Customer"])
def BUY(request, IPOid, selectgroup=None):
    userid = request.user
    uid = request.user
    entry = GroupDetail.objects.filter(user=userid)

    product = Order.objects.filter(user=userid, OrderIPOName_id=IPOid).order_by("-id")

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IPOType = IPOName.IPOType
    PreOpenPrice = IPOName.PreOpenPrice

    Ratelist = RateList(
        user=userid,
        RateListIPOName=IPOName,
        kostakBuyRate=0,
        KostakBuyQty=0,
        SubjecToBuyRate=0,
        SubjecToBuyQty=0,
        PremiumBuyRate=0,
        PremiumBuyQty=0,
    )
    if request.method == "POST":
        user = request.user
        Group = request.POST.get("item_id", "")

        gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
        KostakRate = request.POST.get("KostakRate", "")
        SubjectToRate = request.POST.get("SubjectToRate", "")
        PremiumRate = request.POST.get("PremiumRate", "")

        KostakRateBHNI = request.POST.get("KostakRateBHNI", "")
        SubjectToRateBHNI = request.POST.get("SubjectToRateBHNI", "")

        KostakRateSHNI = request.POST.get("KostakRateSHNI", "")
        SubjectToRateSHNI = request.POST.get("SubjectToRateSHNI", "")

        KostakQTY = request.POST.get("KostakQTY", "")
        SubjectToQTY = request.POST.get("SubjectToQTY", "")
        KostakQTYSHNI = request.POST.get("KostakQTYSHNI", "")
        SubjectToQTYSHNI = request.POST.get("SubjectToQTYSHNI", "")
        KostakQTYBHNI = request.POST.get("KostakQTYBHNI", "")
        SubjectToQTYBHNI = request.POST.get("SubjectToQTYBHNI", "")
        PremiumQTY = request.POST.get("PremiumQTY", "")

        CallQty = request.POST.get("CallQTY", "")
        CallRate = request.POST.get("CallRate", "")
        CallStrikePrice = request.POST.get("CallStrikePrice", "")

        PutQTY = request.POST.get("PutQTY", "")
        PutRate = request.POST.get("PutRate", "")
        PutStrikePrice = request.POST.get("PutStrikePrice", "")

        DateTime = request.POST.get("datetime", "")
        OrderDate = DateTime[0:10]
        OrderTime = DateTime[11:19]

        a = 0
        if KostakQTY != "" and KostakQTY != "0" and KostakRate != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="RETAIL",
                OrderCategory="Kostak",
                OrderType="BUY",
                Quantity=KostakQTY,
                Rate=KostakRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTY)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                a = 1

                # Order_Details_update_sync(KostakQTY, uid, order.id, PreOpenPrice)

                for i in range(0, int(KostakQTY)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a == 0

        if KostakQTYSHNI != "" and KostakQTYSHNI != "0" and KostakRateSHNI != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="SHNI",
                OrderCategory="Kostak",
                OrderType="BUY",
                Quantity=KostakQTYSHNI,
                Rate=KostakRateSHNI,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYSHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                a = 1

                # Order_Details_update_sync(KostakQTYSHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(KostakQTYSHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a == 0

        if KostakQTYBHNI != "" and KostakQTYBHNI != "0" and KostakRateBHNI != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="BHNI",
                OrderCategory="Kostak",
                OrderType="BUY",
                Quantity=KostakQTYBHNI,
                Rate=KostakRateBHNI,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYBHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                a = 1

                # Order_Details_update_sync(KostakQTYBHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(KostakQTYBHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a == 0

        if SubjectToQTY != "" and SubjectToQTY != "0" and SubjectToRate != "":
            if (
                request.POST.get("subjectToIsPremiumRetail", "") is not None
                and request.POST.get("subjectToIsPremiumRetail", "") != ""
                and request.POST.get("subjectToIsPremiumRetail", "") == "on"
            ):
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="RETAIL",
                    OrderCategory="Subject To",
                    OrderType="BUY",
                    Quantity=SubjectToQTY,
                    Rate=SubjectToRate,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                    Method="Premium",
                )
            else:
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="RETAIL",
                    OrderCategory="Subject To",
                    OrderType="BUY",
                    Quantity=SubjectToQTY,
                    Rate=SubjectToRate,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTY)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(SubjectToQTY, uid, order.id, PreOpenPrice)
                for i in range(0, int(SubjectToQTY)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a == 0
        if (
            SubjectToQTYSHNI != ""
            and SubjectToQTYSHNI != "0"
            and SubjectToRateSHNI != ""
        ):
            if (
                request.POST.get("subjectToIsPremiumSHNI", "") is not None
                and request.POST.get("subjectToIsPremiumSHNI", "") != ""
                and request.POST.get("subjectToIsPremiumSHNI", "") == "on"
            ):
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="SHNI",
                    OrderCategory="Subject To",
                    OrderType="BUY",
                    Quantity=SubjectToQTYSHNI,
                    Rate=SubjectToRateSHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                    Method="Premium",
                )
            else:
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="SHNI",
                    OrderCategory="Subject To",
                    OrderType="BUY",
                    Quantity=SubjectToQTYSHNI,
                    Rate=SubjectToRateSHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYSHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(SubjectToQTYSHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(SubjectToQTYSHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a == 0
        if (
            SubjectToQTYBHNI != ""
            and SubjectToQTYBHNI != "0"
            and SubjectToRateBHNI != ""
        ):
            if (
                request.POST.get("subjectToIsPremiumBHNI", "") is not None
                and request.POST.get("subjectToIsPremiumBHNI", "") != ""
                and request.POST.get("subjectToIsPremiumBHNI", "") == "on"
            ):
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="BHNI",
                    OrderCategory="Subject To",
                    OrderType="BUY",
                    Quantity=SubjectToQTYBHNI,
                    Rate=SubjectToRateBHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                    Method="Premium",
                )
            else:
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="BHNI",
                    OrderCategory="Subject To",
                    OrderType="BUY",
                    Quantity=SubjectToQTYBHNI,
                    Rate=SubjectToRateBHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYBHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(SubjectToQTYBHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(SubjectToQTYBHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a == 0

        if PremiumQTY != "" and PremiumQTY != "0" and PremiumRate != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="PREMIUM",
                OrderCategory="Premium",
                OrderType="BUY",
                Quantity=PremiumQTY,
                Rate=PremiumRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Premium_Order_limit is not None:
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(
                    user=user, OrderIPOName_id=IPOid, OrderCategory=Order_type
                ).aggregate(Sum("Quantity"))["Quantity__sum"]
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request,
                        f"You have reached the limit of {Limit} Premium shares QTY.",
                    )
                    return redirect(f"/{IPOid}/BUY")
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user, entry2.id)
                a = 1
            except:
                a == 0

        if (
            CallQty != ""
            and CallQty != "0"
            and CallRate != ""
            and CallStrikePrice != ""
        ):
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="OPTIONS",
                OrderCategory="CALL",
                OrderType="BUY",
                Quantity=CallQty,
                Rate=CallRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
                Method=CallStrikePrice,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Premium_Order_limit is not None:
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(
                    user=user, OrderIPOName_id=IPOid, OrderCategory=Order_type
                ).aggregate(Sum("Quantity"))["Quantity__sum"]
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request,
                        f"You have reached the limit of {Limit} Premium shares QTY.",
                    )
                    return redirect(f"/{IPOid}/BUY")

            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user, entry2.id)
                a = 1
            except:
                traceback.print_exc()
                a == 0

        if PutQTY != "" and PutQTY != "0" and PutRate != "" and PutStrikePrice != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="OPTIONS",
                OrderCategory="PUT",
                OrderType="BUY",
                Quantity=PutQTY,
                Rate=PutRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
                Method=PutStrikePrice,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Premium_Order_limit is not None:
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(
                    user=user, OrderIPOName_id=IPOid, OrderCategory=Order_type
                ).aggregate(Sum("Quantity"))["Quantity__sum"]
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request,
                        f"You have reached the limit of {Limit} Premium shares QTY.",
                    )
                    return redirect(f"/{IPOid}/BUY")

            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user, entry2.id)
                a = 1
            except:
                traceback.print_exc()
                a == 0

        if a == 1:
            messages.success(
                request,
                "Buy order placed successfully. Telegram message sent successfully ",
            )
            return JsonResponse(
                {"status": "success", "message": "BUY order placed successfully"}
            )
            # return redirect(f'/{IPOid}/BUY')
        else:
            messages.error(request, "Buy order was not placed. Please try again.")
            return JsonResponse(
                {"status": "fail", "message": "BUY order dose not placed"}
            )

            # return redirect(f'/{IPOid}/BUY')

    if selectgroup is not None:
        selectgroup = unquote(selectgroup)
    else:
        if Order.objects.count() > 0:
            selectgroup = Order.objects.latest("id").OrderGroup.GroupName
        else:
            selectgroup = None

    return render(
        request,
        "buy.html",
        {
            "product": product,
            "entry": entry.order_by("GroupName"),
            "IPOid": IPOid,
            "order_type": "BUY",
            "IPOName": IPOName,
            "Ratelist": Ratelist,
            "selectgroup": selectgroup,
        },
    )


@allowed_users(allowed_roles=["Broker"])
def UpdateOrder(request, IPOid, OrderId, Grpf, OrCtf, InTyf):
    page_number = request.GET.get("page")
    userid = request.user
    uid = request.user
    Grpf = unquote(Grpf)
    OrCtf = unquote(OrCtf)
    entry = GroupDetail.objects.filter(user=userid)
    order = Order.objects.get(user=userid, id=OrderId)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    if request.method == "POST":
        Group = request.POST.get("Group", "")
        gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
        OrderType = request.POST.get("OrderType", "")
        Qty = request.POST.get("Qty", "")
        if IPOName.IPOType != "SME":
            InvestorType = request.POST.get("InvestorType", "")
        else:
            InvestorType = "RETAIL"
        OrderCategory = request.POST.get("OrderCategory", "")
        if OrderCategory == "Subject To":
            Rate = request.POST.get("Sub_Rate", "")
            RateOrPremium = request.POST.get("subjectToIsPremium", "")
        else:
            Rate = request.POST.get("Rate", "")

        if InvestorType == "OPTIONS":
            Strike_price = request.POST.get("optionStrikePrice", "")

        DateTime = request.POST.get("datetime", "")
        OrderDate = DateTime[0:10]
        OrderTime = DateTime[11:19]
        var = 1

        try:
            if OrderCategory == "Subject To":
                print(
                    Order.objects.get(
                        user=uid,
                        OrderGroup_id=gid,
                        OrderIPOName=IPOName,
                        InvestorType=InvestorType,
                        Rate=Rate,
                        OrderCategory=OrderCategory,
                        OrderType=OrderType,
                        Quantity=Qty,
                        OrderDate=OrderDate,
                        OrderTime=OrderTime,
                        Method=RateOrPremium,
                    )
                )
            elif InvestorType == "OPTIONS":
                print(
                    Order.objects.get(
                        user=uid,
                        OrderGroup_id=gid,
                        OrderIPOName=IPOName,
                        InvestorType=InvestorType,
                        Rate=Rate,
                        OrderCategory=OrderCategory,
                        OrderType=OrderType,
                        Quantity=Qty,
                        OrderDate=OrderDate,
                        OrderTime=OrderTime,
                        Method=Strike_price,
                    )
                )
            else:
                print(
                    Order.objects.get(
                        user=uid,
                        OrderGroup_id=gid,
                        OrderIPOName=IPOName,
                        InvestorType=InvestorType,
                        Rate=Rate,
                        OrderCategory=OrderCategory,
                        OrderType=OrderType,
                        Quantity=Qty,
                        OrderDate=OrderDate,
                        OrderTime=OrderTime,
                    )
                )
        except:
            var = 0
            entry = Order.objects.get(user=request.user, id=OrderId)
            orderdetailfilter = OrderDetail.objects.filter(
                user=request.user, Order_id=OrderId, OrderDetailPANNo=None
            )
            orderdetail = orderdetailfilter.count()
            entry.OrderGroup_id = gid
            entry.OrderIPOName = IPOName
            entry.InvestorType = InvestorType
            entry.OrderCategory = OrderCategory
            if OrderCategory == "Subject To":
                if (
                    RateOrPremium is not None
                    and RateOrPremium != ""
                    and RateOrPremium == "on"
                ):
                    entry.Method = "Premium"
                else:
                    entry.Method = None

            if InvestorType == "OPTIONS":
                entry.Method = Strike_price

            entry.OrderType = OrderType
            entry.Rate = Rate
            entry.OrderTime = OrderTime
            entry.OrderDate = OrderDate
            entry.Telly = False

            if order.Quantity == float(Qty):
                entry.Rate = Rate
                entry.Quantity = order.Quantity
                try:
                    entry.save()
                except:
                    var = 3
            elif order.Quantity < float(Qty):
                user = request.user
                O_limit = CustomUser.objects.get(username=user)
                if O_limit.Order_limit is not None:
                    n = int(float(Qty) - order.Quantity)
                    BUY_Count = OrderDetail.objects.filter(
                        user=user, Order__OrderIPOName_id=IPOid
                    ).count()
                    Sum_Qty = int(BUY_Count) + int(n)
                    Limit = int(O_limit.Order_limit)
                    if Sum_Qty >= Limit + 1:
                        messages.error(
                            request,
                            f"You have reached the limit of {Limit} OrderDetail.",
                        )
                        return redirect(
                            f"/{IPOid}/Order/{Grpf}/{OrCtf}/{InTyf}?page={page_number}"
                        )

                entry.Quantity = Qty
                try:
                    entry.save()
                except:
                    var = 3

                if OrderCategory != "Premium" and InvestorType != "OPTIONS":
                    n = int(float(Qty) - order.Quantity)
                    for i in range(0, n):
                        orderdetail1 = OrderDetail(user=uid, Order_id=entry.id)
                        orderdetail1.save()
            else:
                if OrderCategory != "Premium":
                    j = 0
                    k = order.Quantity - float(Qty)

                    if k <= orderdetail:
                        for i in orderdetailfilter:
                            if j < k:
                                i.delete()
                                j += 1
                        entry.Quantity = Qty
                        try:
                            entry.save()
                        except:
                            var = 3

                    else:
                        var = 2
                        if InvestorType == "OPTIONS":
                            entry.Quantity = float(Qty)
                            var = None
                        else:
                            entry.Quantity = order.Quantity
                        try:
                            entry.save()
                        except:
                            var = 3
                else:
                    entry.Quantity = Qty
                    try:
                        entry.save()
                    except:
                        var = 3

            calculate(IPOid, request.user, entry.id)

        if var == 1:
            messages.error(request, "Order values are same")
        elif var == 2:
            messages.success(request, "Order Modified")

            messages.error(
                request, "Error : Only Blank PAN entry in OrderDetail can be deleted"
            )
            error_message = f"No. of Blank PAN Entry: {orderdetail}"
            messages.error(request, error_message)
        elif var == 3:
            messages.error(request, "Order Not Modified")
        else:
            messages.success(request, "Order Modified successfully")

    return redirect(f"/{IPOid}/Order/{Grpf}/{OrCtf}/{InTyf}?page={page_number}")


# change rate fun
@allowed_users(allowed_roles=["Broker"])
def EditOrderRate(request, IPOid, OrderId, GrpName, OrderCategory, InvestorType):
    userid = request.user
    if request.method == "POST":
        Rate = request.POST.get("Rate", "")
        order = Order.objects.get(user=request.user, id=OrderId)
        order.Rate = Rate
        order.save()
        calculate(IPOid, request.user, OrderId)
        messages.success(request, "Order Modified successfully")
    return redirect(f"/{IPOid}/Order/{GrpName}/{OrderCategory}/{InvestorType}")


@allowed_users(allowed_roles=["Broker"])
def SetRate(request, IPOid):
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    try:
        query = RateList.objects.get(RateListIPOName=IPOName, user=request.user)
    except:
        query = 0

    if request.method == "POST":
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        query = RateList.objects.filter(RateListIPOName=IPOName, user=request.user)
        KostakRate = request.POST.get("KostakRate", "")
        KostakSellRate = request.POST.get("KostakSellRate", "")
        SubjectToRate = request.POST.get("SubjectToRate", "")
        SubjectToSellRate = request.POST.get("SubjectToSellRate", "")
        PremiumRate = request.POST.get("PremiumRate", "")
        KostakQTY = request.POST.get("KostakQTY", "")
        KostakSellQTY = request.POST.get("KostakSellQTY", "")
        SubjectToQTY = request.POST.get("SubjectToQTY", "")
        SubjectToSellQTY = request.POST.get("SubjectToSellQTY", "")
        PremiumQTY = request.POST.get("PremiumQTY", "")
        PremiumSellQTY = request.POST.get("PremiumSellQTY", "")
        PremiumSellRate = request.POST.get("PremiumSellRate", "")
        if query.exists():
            query1 = RateList.objects.get(RateListIPOName=IPOName, user=request.user)
            if KostakQTY != "":
                query1.kostakBuyRate = KostakRate
                query1.KostakBuyQty = KostakQTY
                query1.save()
            if KostakSellQTY != "":
                query1.kostakSellRate = KostakSellRate
                query1.KostakSellQty = KostakSellQTY
                query1.save()
            if SubjectToQTY != "":
                query1.SubjecToBuyRate = SubjectToRate
                query1.SubjecToBuyQty = SubjectToQTY
                query1.save()
            if SubjectToSellQTY != "":
                query1.SubjecToSellRate = SubjectToSellRate
                query1.SubjecToSellQty = SubjectToSellQTY
                query1.save()
            if PremiumQTY != "":
                query1.PremiumBuyRate = PremiumRate
                query1.PremiumBuyQty = PremiumQTY
                query1.save()
            if PremiumSellQTY != "":
                query1.PremiumSellRate = PremiumSellRate
                query1.PremiumSellQty = PremiumSellQTY
                query1.save()
        else:
            if KostakQTY == "":
                KostakQTY = 0
            if KostakSellQTY == "":
                KostakSellQTY = 0
            if SubjectToQTY == "":
                SubjectToQTY = 0
            if SubjectToSellQTY == "":
                SubjectToSellQTY = 0
            if PremiumQTY == "":
                PremiumQTY = 0
            if PremiumSellQTY == "":
                PremiumSellQTY = 0
            ratelist = RateList(
                user=request.user,
                RateListIPOName=IPOName,
                kostakBuyRate=KostakRate,
                KostakBuyQty=KostakQTY,
                SubjecToBuyRate=SubjectToRate,
                SubjecToBuyQty=SubjectToQTY,
                PremiumBuyRate=PremiumRate,
                PremiumBuyQty=PremiumQTY,
                PremiumSellRate=PremiumSellRate,
                PremiumSellQty=PremiumSellQTY,
            )
            ratelist.save()
        return redirect("/")
    return render(
        request, "SetRate.html", {"Ratelist": query, "IPOName": IPOName, "IPOid": IPOid}
    )


def is_valid_queryparam(param):
    return param != "" and param is not None


# app-buy & app-sell oder details fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def OrderDetailFunction(
    request,
    IPOid,
    Ordtyp,
    GrpName=None,
    OrderCategory=None,
    InvestorType=None,
    OrderDate=None,
    OrderTime=None,
):

    if request.user.groups.all()[0].name == "Broker":
        entry = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp
        )
        Group = GroupDetail.objects.filter(user=request.user)
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    else:
        entry = OrderDetail.objects.filter(
            user=request.user.Broker_id,
            Order__OrderIPOName_id=IPOid,
            Order__OrderGroup_id=request.user.Group_id,
            Order__OrderType=Ordtyp,
            Order__InvestorType=InvestorType,
        )
        Group = GroupDetail.objects.filter(
            user=request.user.Broker_id, id=request.user.Group_id
        )

        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)

    group_names_list = []
    Panding_Pan_GroupList = []

    entry_for_gp = entry.select_related("OrderDetailPANNo__Group", "Order__OrderGroup")
    for order_detail_entry in entry_for_gp:
        if order_detail_entry.OrderDetailPANNo:  # Check if OrderDetailPANNo is not null
            group_name = order_detail_entry.OrderDetailPANNo.Group.GroupName
            Group_emial = order_detail_entry.OrderDetailPANNo.Group.Email
        else:
            group_name = order_detail_entry.Order.OrderGroup.GroupName
            Group_emial = order_detail_entry.Order.OrderGroup.Email
            if not any(g["group_name"] == group_name for g in Panding_Pan_GroupList):
                Panding_Pan_GroupList.append(
                    {"group_name": group_name, "Group_emial": Group_emial}
                )

        if not any(g["group_name"] == group_name for g in group_names_list):
            group_names_list.append(
                {"group_name": group_name, "Group_emial": Group_emial}
            )

    Od_time = OrderTime
    Od_Date = OrderDate
    if OrderDate == "None":
        OrderDate = None

    if OrderTime == "None":
        OrderTime = None

    if OrderDate is not None:
        OrderDate = OrderDate[0:4] + "-" + OrderDate[4:6] + "-" + OrderDate[6:8]
        entry = entry.filter(Order__OrderDate=OrderDate)

    if OrderTime is not None:
        OrderTime = OrderTime[0:2] + ":" + OrderTime[2:4] + ":" + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime=OrderTime)

    AppTotal = len(entry)
    Appwithoutpan = len(entry.filter(OrderDetailPANNo_id=None))

    if GrpName is None and OrderCategory is None and InvestorType is None:
        Groupfilter = "All"
        IPOTypefilter = "All"
        InvestorTypeFilter = "All"

        if (
            IPOTypefilter == "All"
            and Groupfilter == "All"
            and InvestorTypeFilter == "All"
        ):
            pass
        elif IPOTypefilter == "All" and Groupfilter == "All":
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        elif IPOTypefilter == "All" and InvestorTypeFilter == "All":
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        elif InvestorTypeFilter == "All" and Groupfilter == "All":
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        elif IPOTypefilter == "All":
            entry = entry.filter(
                Order__OrderGroup__GroupName=Groupfilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        elif Groupfilter == "All":
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        elif InvestorTypeFilter == "All":
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__OrderGroup__GroupName=Groupfilter,
            )
        else:
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__OrderGroup__GroupName=Groupfilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        AppTotal = len(entry)
        Appwithoutpan = len(entry.filter(OrderDetailPANNo_id=None))

    else:
        Groupfilter = unquote(GrpName)
        IPOTypefilter = unquote(OrderCategory)
        InvestorTypeFilter = InvestorType

        if (
            IPOTypefilter == "All"
            and Groupfilter == "All"
            and InvestorTypeFilter == "All"
        ):
            pass
        elif IPOTypefilter == "All" and Groupfilter == "All":
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        elif IPOTypefilter == "All" and InvestorTypeFilter == "All":
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        elif InvestorTypeFilter == "All" and Groupfilter == "All":
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        elif IPOTypefilter == "All":
            entry = entry.filter(
                Order__OrderGroup__GroupName=Groupfilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        elif Groupfilter == "All":
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        elif InvestorTypeFilter == "All":
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__OrderGroup__GroupName=Groupfilter,
            )
        else:
            entry = entry.filter(
                Order__OrderCategory=IPOTypefilter,
                Order__OrderGroup__GroupName=Groupfilter,
                Order__InvestorType=InvestorTypeFilter,
            )
        AppTotal = len(entry)
        Appwithoutpan = len(entry.filter(OrderDetailPANNo_id=None))

    if request.method == "POST":
        if request.user.groups.all()[0].name == "Broker":
            entry = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp
            )
        else:
            entry = OrderDetail.objects.filter(
                user=request.user.Broker_id,
                Order__OrderIPOName_id=IPOid,
                Order__OrderGroup_id=request.user.Group_id,
                Order__OrderType=Ordtyp,
            )

        Groupfilter = request.POST.get("Groupfilter", "")
        IPOTypefilter = request.POST.get("IPOTypefilter", "")
        InvestorTypeFilter = request.POST.get("InvestorTypeFilter", "")
        if Groupfilter == "" or Groupfilter is None:
            Groupfilter = "All"
        if IPOTypefilter == "" or IPOTypefilter is None:
            IPOTypefilter = "All"
        if InvestorTypeFilter == "" or InvestorTypeFilter is None:
            InvestorTypeFilter = "All"

        if is_valid_queryparam(Groupfilter) and Groupfilter != "All":
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != "All":
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != "All":
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)

        Groupfilter = Groupfilter
        IPOTypefilter = IPOTypefilter
        InvestorTypeFilter = InvestorTypeFilter
        AppTotal = len(entry)
        Appwithoutpan = len(entry.filter(OrderDetailPANNo_id=None))

        if OrderDate is not None and OrderTime is not None:
            OrderDate = OrderDate[0:4] + OrderDate[5:7] + OrderDate[8:10]
            OrderTime = OrderTime[0:2] + OrderTime[3:5] + OrderTime[6:8]

    page_obj = None
    try:
        page_size = request.POST.get("page_size")
        if page_size != "" and page_size is not None:
            request.session["page_size"] = page_size
        else:
            page_size = request.session["page_size"]
    except:
        page_size = request.session.get("page_size", 50)

    Data = []
    entry = entry.order_by(
        "Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime"
    )
    entry = entry.order_by("-id")
    if entry is not None and entry.exists():
        if page_size == "All":
            paginator = Paginator(entry, len(entry))
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry, page_size)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "OrderGroup": order_detail.Order.OrderGroup,
                "OrderCategory": order_detail.Order.OrderCategory,
                "OrderType": order_detail.Order.OrderType,
                "InvestorType": order_detail.Order.InvestorType,
                "Rate": order_detail.Order.Rate,
                "PANNo": (
                    order_detail.OrderDetailPANNo.PANNo
                    if (
                        order_detail.OrderDetailPANNo
                        and order_detail.OrderDetailPANNo.PANNo is not None
                    )
                    else ""
                ),
                "Name": (
                    order_detail.OrderDetailPANNo.Name
                    if (
                        order_detail.OrderDetailPANNo
                        and order_detail.OrderDetailPANNo.Name is not None
                    )
                    else ""
                ),
                "AllotedQty": (
                    float(order_detail.AllotedQty)
                    if (order_detail.AllotedQty is not None)
                    else ""
                ),
                "DematNumber": (
                    order_detail.DematNumber
                    if (order_detail and order_detail.DematNumber is not None)
                    else ""
                ),
                "ApplicationNumber": (
                    order_detail.ApplicationNumber
                    if (order_detail and order_detail.ApplicationNumber is not None)
                    else ""
                ),
                "Date": order_detail.Order.OrderDate,
                "Time": order_detail.Order.OrderTime,
                "sr_no": start_index + i + 1,
                "Client_id": (
                    order_detail.OrderDetailPANNo.id
                    if order_detail.OrderDetailPANNo is not None
                    else ""
                ),
                "Alloted_qty": (
                    float(order_detail.AllotedQty)
                    if (order_detail.AllotedQty is not None)
                    else ""
                ),
                "Demate_number": (
                    order_detail.DematNumber
                    if (order_detail and order_detail.DematNumber is not None)
                    else ""
                ),
                "Application_Number": (
                    order_detail.ApplicationNumber
                    if (order_detail and order_detail.ApplicationNumber is not None)
                    else ""
                ),
                "client_Name": (
                    order_detail.OrderDetailPANNo.Name
                    if (
                        order_detail.OrderDetailPANNo
                        and order_detail.OrderDetailPANNo.Name is not None
                    )
                    else ""
                ),
                # Add other fields as needed
            }
            Data.append(entry_data)

    else:
        paginator = Paginator([], 1)
        page_obj = paginator.get_page(1)

    # df = pd.DataFrame.from_records(Data)
    # html_table = "<table  >\n"
    # html_table = "<thead><tr style='text-align: center;'>"
    # html_table += "<th>Group</th>"
    # html_table += "<th>Order Category</th>"
    # if IPOName.IPOType == "MAINBOARD":
    #     html_table += "<th>Investor Type</th>"
    # html_table += "<th>Rate</th>"
    # html_table += "<th>PAN No</th>"
    # html_table += "<th>Client Name</th>"
    # html_table += "<th>Alloted Qty</th>"
    # html_table += "<th>Demat No</th>"
    # html_table += "<th>Application No</th>"
    # html_table += "<th>Date and Time</th>"
    # html_table += "<th>Action</th>"
    # html_table += "</tr></thead>\n"

    # html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    # csrf_token = csrf.get_token(request)

    # for i, row in df.iterrows():
    #     datetime_str  = f"{row.Date} {row.Time}"
    #     datetime_obj = datetime.strptime(datetime_str , "%Y-%m-%d %H:%M:%S")
    #     formatted_datetime = datetime_obj.strftime("%b. %d, %Y %I:%M %p")
    #     if IPOName.IPOType == 'MAINBOARD':
    #         update =  f"/{IPOid}/{row.OrderType}/AddPan-{ row.id }/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}/{OrderDate}/{OrderTime}"
    #     else:
    #         update = f'/{IPOid}/{row.OrderType}/AddPan-{ row.id }/{Groupfilter}/{IPOTypefilter}/All/{OrderDate}/{OrderTime}'
    #     html_table += f"<form action='{update}' method='POST'> <tr style='text-align: center;'>"
    #     html_table += f"<input type='hidden' name='csrfmiddlewaretoken' value='{csrf_token}'>"
    #     html_table += f"<td>{row.OrderGroup}</td>"
    #     html_table += f"<td>{row.OrderCategory}</td>"
    #     if IPOName.IPOType == 'MAINBOARD':
    #         html_table += f"<td>{row.InvestorType}</td>"
    #     html_table += f"<td>{row.Rate}</td>"
    #     html_table += f"<td style='width:185px;'><input class='auto' type='text' style='text-transform: uppercase;  width:165px;' maxlength='10' minlength='10' name='PAN' onclick='functiontest({row.id})' required value='{row.PANNo}'></td>"
    #     html_table += f"<td style='width:185px;'><input class='auto1' id='{row.id}' type='text' style='width:165px;' name='clientname' value='{row.Name}'></td>"
    #     html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty' value='{row.AllotedQty}'></td>"
    #     html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='DematNo' value='{row.DematNumber}'></td>"
    #     html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='Application' value='{row.ApplicationNumber}'></td>"
    #     html_table += f"<td>{formatted_datetime}</td>"
    #     html_table += f"<td><button class='btn btn-outline-primary' type='submit' style='width: 72px;'>Update</button></td>"
    #     html_table += "</tr></form>\n"

    # html_table += "</tbody></table>"

    df = pd.DataFrame.from_records(Data)
    # paginator = Paginator(df.to_dict('records'), 10)
    # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_number)

    html_table = "<table>\n"
    html_table = "<thead><tr style='text-align: center;'>"
    # html_table = f"<form action='/{IPOid}/{Ordtyp}/update_pann' method='POST'>\n"
    # csrf_token = csrf.get_token(request)
    # html_table += f"<input type='hidden' name='csrfmiddlewaretoken' value='{csrf_token}'>"
    # html_table += "<div style='text-align: right; margin-top: 0%;margin-bottom: 1%;'>"
    # html_table += "<button class='btn btn-outline-primary' type='submit' style='width: 100px;'>Update</button>"
    # html_table += "</div>\n"
    html_table += "<th>Sr No.</th>"
    html_table += "<th>Group</th>"
    html_table += "<th>Order Category</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th data-sort='input'>PAN No</th>"
    html_table += "<th data-sort='input'>Client Name</th>"
    html_table += "<th data-sort='input'>Alloted Qty</th>"
    html_table += "<th data-sort='input'>Demat No</th>"
    html_table += "<th data-sort='input'>Application No</th>"
    html_table += "<th>Date and Time</th>"
    html_table += "</tr></thead>\n"

    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    if df.empty:
        column_count = 11 if IPOName.IPOType == "MAINBOARD" else 10
        html_table += f"<tr class='odd'><td colspan='{column_count}' valign='top' class='dataTables_empty'>No data available</td></tr>"
    else:
        for i, row in df.iterrows():
            datetime_str = f"{row.Date} {row.Time}"
            datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            formatted_datetime = datetime_obj.strftime("%b. %d, %Y %I:%M %p")
            # if IPOName.IPOType == 'MAINBOARD':
            #     update =  f"/{IPOid}/{row.OrderType}/AddPan-{ row.id }/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}/{OrderDate}/{OrderTime}"
            # else:
            #     update = f'/{IPOid}/{row.OrderType}/AddPan-{ row.id }/{Groupfilter}/{IPOTypefilter}/All/{OrderDate}/{OrderTime}'
            html_table += f"<td>{row.sr_no}</td>"
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.OrderCategory}</td>"
            if IPOName.IPOType == "MAINBOARD":
                html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.InvestorType}</td>"
            html_table += f"<td>{row.Rate}</td>"
            html_table += f"<td style='width:185px;'><input class='auto' type='text' style='text-transform: uppercase;  width:165px;' maxlength='10' minlength='10' name='PAN_{row.id}_{row.Rate}_{row.Client_id}_{row.Alloted_qty}_{row.Demate_number}_{row.Application_Number}_{row.client_Name}' id='PAN_{ row.id }' onclick='functiontest({row.id})' value='{row.PANNo}' onfocus='hideTooltip({ row.id })' onblur='checkPAN({ row.id })'><div id='tooltip_{ row.id }' class='Shadow1' style='display:none;'>Invalid PAN number</div></td>"
            html_table += f"<td style='width:185px;'><input class='auto1' type='text' style='width:165px;' name='clientname_{row.id}' value='{row.Name}' id='clientname_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' ><div id='clientname_tooltip_{row.id}' class='Shadow1' style='display:none; color:red; font-size:12px;'>Only letters, numbers, and . - & / @ _ are allowed</div></td>"
            if row.AllotedQty != "":
                html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty_{row.id}' value='{int(row.AllotedQty) if row.AllotedQty.is_integer() else row.AllotedQty}'></td>"
            else:
                html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty_{row.id}' value=''></td>"
            html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='DematNo_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")'  value='{row.DematNumber}'></td>"
            html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='Application_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' value='{row.ApplicationNumber}'></td>"
            html_table += f"<td>{formatted_datetime}</td>"
            html_table += "</tr>\n"

    html_table += "</tbody>"
    # html_table += "</form>"
    html_table += "</table>"

    PRI_limit = CustomUser.objects.get(username=request.user)
    is_premium_user = PRI_limit.Allotment_access

    if Ordtyp == "BUY":
        return render(
            request,
            "OrderDetail.html",
            {
                "is_premium_user": str(is_premium_user),
                "html_table": html_table,
                "Groupfilter": Groupfilter,
                "IPOTypefilter": IPOTypefilter,
                "group_names_list": json.dumps(group_names_list),
                "Panding_Pan_GroupList": json.dumps(Panding_Pan_GroupList),
                "InvestorTypeFilter": InvestorTypeFilter,
                "IPOName": IPOName,
                "Group": Group.order_by("GroupName"),
                "IPOid": IPOid,
                "AppTotal": AppTotal,
                "Appwithoutpan": Appwithoutpan,
                "OrderDate": Od_Date,
                "OrderTime": Od_time,
                "page_obj": page_obj,
                "page_size": page_size,
            },
        )
    else:
        return render(
            request,
            "OrderDetail - Sell.html",
            {
                "is_premium_user": str(is_premium_user),
                "html_table": html_table,
                "Groupfilter": Groupfilter,
                "IPOTypefilter": IPOTypefilter,
                "InvestorTypeFilter": InvestorTypeFilter,
                "group_names_list": json.dumps(group_names_list),
                "Panding_Pan_GroupList": json.dumps(Panding_Pan_GroupList),
                "IPOName": IPOName,
                "Group": Group.order_by("GroupName"),
                "IPOid": IPOid,
                "AppTotal": AppTotal,
                "Appwithoutpan": Appwithoutpan,
                "OrderDate": Od_Date,
                "OrderTime": Od_time,
                "page_obj": page_obj,
                "page_size": page_size,
            },
        )


# groupwise to move order page fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def filterfromstatus(
    request, IPOid, Groupfilter, OrderCategoryFilter, InvestorTypeFilter
):

    Groupfilter = unquote(Groupfilter)
    OrderCategoryFilter = unquote(OrderCategoryFilter)

    if request.user.groups.all()[0].name == "Broker":
        userid = request.user
        products = Order.objects.filter(user=userid, OrderIPOName_id=IPOid)
    else:
        userid = request.user.Broker_id
        products = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid, OrderGroup_id=request.user.Group_id
        )
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)

    Group = GroupDetail.objects.filter(user=userid)
    if is_valid_queryparam(Groupfilter) and Groupfilter != "All":
        products = products.filter(OrderGroup__GroupName=Groupfilter)
    if is_valid_queryparam(OrderCategoryFilter) and OrderCategoryFilter != "All":
        products = products.filter(OrderCategory=OrderCategoryFilter)
    if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != "All":
        products = products.filter(InvestorType=InvestorTypeFilter)

    InvestorTypeFilter = InvestorTypeFilter
    Groupfilter = Groupfilter
    OrderCategoryFilter = OrderCategoryFilter

    if InvestorTypeFilter == "" or InvestorTypeFilter is None:
        InvestorTypeFilter = "All"

    if Groupfilter == "" or Groupfilter is None:
        Groupfilter = "All"

    if OrderCategoryFilter == "" or OrderCategoryFilter is None:
        OrderCategoryFilter = "All"

    OrdCat = ["Kostak", "SubjectTo", "CALL", "PUT"]
    InvTyp = ["RETAIL", "SHNI", "BHNI", "OPTIONS"]
    OrdTyp = ["BUY", "SELL"]

    strike_dict = {}
    dict_count = {}
    dict_avg = {}
    dict_amount = {}

    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                if ordercategory == "SubjectTo":
                    x = products.filter(
                        OrderType=ordertype,
                        OrderCategory="Subject To",
                        InvestorType=investortype,
                    )
                else:
                    x = products.filter(
                        OrderType=ordertype,
                        OrderCategory=ordercategory,
                        InvestorType=investortype,
                    )
                count = x.aggregate(Sum("Quantity"))["Quantity__sum"]
                if count is None:
                    dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                    z = 0
                else:
                    dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = count
                    z = count

                amount = 0
                for i in x:
                    if i.OrderCategory == "Subject To":
                        if i.Method == "Premium":
                            if investortype == "RETAIL":
                                lot_size = IPO.LotSizeRetail
                            if investortype == "SHNI":
                                lot_size = IPO.LotSizeSHNI
                            if investortype == "BHNI":
                                lot_size = IPO.LotSizeBHNI
                            amount = ((lot_size * i.Rate) * i.Quantity) + amount
                        else:
                            amount = i.Rate + amount
                    # 🔹 Special handling for OPTIONS CALL/PUT with StrikePrice
                    elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:

                        strike = getattr(i, "Method", None) or "NA"

                        # Initialize dict structure
                        if strike not in strike_dict:
                            strike_dict[strike] = {
                                "CALL": {
                                    "BUY": {"count": 0, "amount": 0, "avg": 0},
                                    "SELL": {"count": 0, "amount": 0, "avg": 0},
                                },
                                "PUT": {
                                    "BUY": {"count": 0, "amount": 0, "avg": 0},
                                    "SELL": {"count": 0, "amount": 0, "avg": 0},
                                },
                            }
                        # Update values
                        strike_dict[strike][ordercategory][ordertype][
                            "count"
                        ] += i.Quantity
                        strike_dict[strike][ordercategory][ordertype]["amount"] += (
                            i.Rate * i.Quantity
                        )

                        # Net = (BUY amount - SELL amount) for that side
                        buy_amt = strike_dict[strike][ordercategory]["BUY"]["amount"]
                        sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                        strike_dict[strike][ordercategory]["BUY"]["net"] = (
                            buy_amt - sell_amt
                        )
                        strike_dict[strike][ordercategory]["SELL"]["net"] = (
                            sell_amt - buy_amt
                        )

                        amount = (i.Rate * i.Quantity) + amount

                    else:
                        amount = (i.Rate * i.Quantity) + amount

                if z == 0:
                    dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = 0
                else:
                    dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = (
                        amount / z
                    )

                dict_amount[f"{ordercategory}{investortype}{ordertype}Amount"] = amount

    net_count = {}
    net_avg = {}
    net_amount = {}

    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"

            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0

            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)

    PremiumBuyfilter = products.filter(OrderType="BUY", OrderCategory="Premium")
    PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum("Quantity"))
    PremiumBuyCount1 = PremiumBuyCount11["Quantity__sum"]
    if PremiumBuyCount1 is None:
        PremiumBuyCount = 0
    else:
        PremiumBuyCount = PremiumBuyCount1

    PremiumBuyAmount = 0
    for i in PremiumBuyfilter:
        PremiumBuyAmount = (i.Quantity * i.Rate) + PremiumBuyAmount

    if PremiumBuyCount == 0:
        PremiumBuyAvg = 0
    else:
        PremiumBuyAvg = PremiumBuyAmount / PremiumBuyCount

    PremiumSellfilter = products.filter(OrderType="SELL", OrderCategory="Premium")
    PremiumSellCount11 = PremiumSellfilter.aggregate(Sum("Quantity"))
    PremiumSellCount1 = PremiumSellCount11["Quantity__sum"]
    if PremiumSellCount1 is None:
        PremiumSellCount = 0
    else:
        PremiumSellCount = PremiumSellCount1

    PremiumSellAmount = 0
    for i in PremiumSellfilter:
        PremiumSellAmount = (i.Quantity * i.Rate) + PremiumSellAmount

    if PremiumSellCount == 0:
        PremiumSellAvg = 0
    else:
        PremiumSellAvg = PremiumSellAmount / PremiumSellCount

    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
    Premiumavg2 = PremiumSellCount * PremiumSellAvg
    pri_net_avg = Premiumavg1 - Premiumavg2
    if PremiumNetCount != 0:
        PremiumNetAvg = pri_net_avg / PremiumNetCount
    else:
        PremiumNetAvg = 0

    PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    strike_prices = []
    grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
    for strike, cats in strike_dict.items():
        # CALL
        call_buy_count = cats["CALL"]["BUY"]["count"]
        call_sell_count = cats["CALL"]["SELL"]["count"]
        call_buy_amount = cats["CALL"]["BUY"]["amount"]
        call_sell_amount = cats["CALL"]["SELL"]["amount"]

        call_net_count = call_buy_count - call_sell_count
        call_avg1 = call_buy_amount - call_sell_amount
        call_avg2 = call_sell_amount - call_buy_amount
        call_net_avg = call_avg1 - call_avg2
        # call_net_amount = call_buy_amount - call_sell_amount
        if call_net_count != 0:
            call_avg = call_net_avg / call_net_count
            call_net_amount = call_buy_amount - call_sell_amount
        else:
            call_avg = 0
            call_net_amount = call_sell_amount - call_buy_amount

        # PUT
        put_buy_count = cats["PUT"]["BUY"]["count"]
        put_sell_count = cats["PUT"]["SELL"]["count"]
        put_buy_amount = cats["PUT"]["BUY"]["amount"]
        put_sell_amount = cats["PUT"]["SELL"]["amount"]

        put_net_count = put_buy_count - put_sell_count
        put_avg1 = put_buy_amount - put_sell_amount
        put_avg2 = put_sell_amount - put_buy_amount
        put_net_avg = put_avg1 - put_avg2
        # put_net_amount = put_buy_amount - put_sell_amount
        if put_net_count != 0:
            put_avg = put_net_avg / put_net_count
            put_net_amount = put_buy_amount - put_sell_amount
        else:
            put_avg = 0
            put_net_amount = put_sell_amount - put_buy_amount

        strike_prices.append(
            {
                "value": strike,
                "call_total_count": call_net_count,
                "call_avg": (call_net_amount / call_net_count) if call_net_count else 0,
                "call_net_amount": call_net_amount,
                "put_total_count": put_net_count,
                "put_avg": (put_net_amount / put_net_count) if put_net_count else 0,
                "put_net_amount": put_net_amount,
            }
        )
        grand_call_count += call_net_count
        grand_call_amount += call_net_amount
        grand_put_count += put_net_count
        grand_put_amount += put_net_amount

    grand_total = {
        "call_total_count": grand_call_count,
        "call_avg": (grand_call_amount / grand_call_count) if grand_call_count else 0,
        "call_net_amount": grand_call_amount,
        "put_total_count": grand_put_count,
        "put_avg": grand_put_amount / grand_put_count if grand_put_count else 0,
        "put_net_amount": grand_put_amount,
    }

    category_totals = {
        "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
        "PUT": {"count": grand_put_count, "avg": grand_total["put_avg"]},
    }

    page_obj = None
    try:
        page_size = request.POST.get("Order_page_size")
        if page_size != "" and page_size is not None:
            request.session["Order_page_size"] = page_size
        else:
            page_size = request.session["Order_page_size"]
    except:
        page_size = request.session.get("Order_page_size", 50)

    Data = []
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    products = products.order_by("-OrderDate", "-OrderTime")
    if page_size == "All":
        all_rows = True
        paginator = Paginator(products, max(len(products), 1))
        page_number = request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page

        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "OrderGroup": order_detail.OrderGroup.GroupName,
                "OrderType": order_detail.OrderType,
                "OrderCategory": order_detail.OrderCategory,
                "InvestorType": order_detail.InvestorType,
                "Quantity": int(order_detail.Quantity),
                "Method": order_detail.Method,
                "Rate": order_detail.Rate,
                "Date": order_detail.OrderDate,
                "Time": order_detail.OrderTime,
                "sr_no": start_index + i + 1,
            }
            Data.append(entry_data)

    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th>Sr No.</th>"
    html_table += "<th>Group Name</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>InvestorType</th>"
    html_table += "<th> Qty</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th>Date and Time</th>"
    html_table += "<th>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    for i, row in df.iterrows():
        datetime_str = f"{row.Date} {row.Time}"
        datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        formatted_datetime = datetime_obj.strftime("%b. %d, %Y | %I:%M:%S %p")
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td>{row.sr_no}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this group\">{row.OrderGroup}</td>"
        html_table += f"<td>{row.OrderType}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        if row.OrderCategory != "Premium":
            method_value = row.Method if row.Method else "Application"
            html_table += f"<td>{method_value}</td>"
        else:
            html_table += f"<td>-</td>"

        if IPOName.IPOType == "MAINBOARD":
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        if row.OrderCategory != "Premium" and row.InvestorType != "OPTIONS":
            html_table += f"<td><a href='/{IPOid}/OrderDetail/{row.OrderType}/{row.OrderGroup}/{ row.OrderCategory }/{row.InvestorType}/{ row.Date.strftime('%Y%m%d') }/{row.Time.strftime('%H%M%S')}{row.id}' style='color:blue; text-decoration: underline; '> {row.Quantity} </a></td>"
        else:
            html_table += f"<td>{row.Quantity }</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td>{formatted_datetime} </td>"
        if IPOName.IPOType == "MAINBOARD":
            url = f"/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}"
        else:
            InvestorTypeFilter = "All"
            url = f"/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='{url}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button></td>"

        html_table += "</tr>\n"
    html_table += "</tbody></table>"

    # return render(request, 'Order.html', {'Group': Group.order_by('GroupName'), 'html_table': html_table, 'IPOid': IPOid, 'IPOName': IPO, 'Groupfilter': Groupfilter,'PremiumSellAmount':PremiumSellAmount,'PremiumNetAmount':PremiumNetAmount,'PremiumBuyAmount':PremiumBuyAmount,'net_count':net_count,'net_avg':net_avg,'net_amount':net_amount  ,'OrderCategoryFilter': OrderCategoryFilter,'InvestorTypeFilter': InvestorTypeFilter, 'dict_count': dict_count, 'dict_avg': dict_avg, 'dict_amount':dict_amount, 'PremiumBuyCount':PremiumBuyCount,'PremiumSellCount':PremiumSellCount,'PremiumNetCount':PremiumNetCount,'PremiumNetAvg':PremiumNetAvg,'PremiumNetAvg':"{:.2f}".format(PremiumNetAvg),'PremiumNetCount':"{:.2f}".format(PremiumNetCount), 'PremiumSellAvg':"{:.2f}".format(PremiumSellAvg),'PremiumBuyAvg':"{:.2f}".format(PremiumBuyAvg),'page_obj': page_obj,'Order_page_size':page_size})
    return render(
        request,
        "Order.html",
        {
            "Group": Group.order_by("GroupName"),
            "html_table": html_table,
            "IPOid": IPOid,
            "IPOName": IPO,
            "Groupfilter": Groupfilter,
            "OrderCategoryFilter": OrderCategoryFilter,
            "category_totals": category_totals,
            "strike_prices": strike_prices,
            "grand_total": grand_total,
            "InvestorTypeFilter": InvestorTypeFilter,
            "PremiumBuyAmount": PremiumBuyAmount,
            "PremiumNetAmount": PremiumNetAmount,
            "PremiumSellAmount": PremiumSellAmount,
            "dict_count": dict_count,
            "net_count": net_count,
            "net_avg": net_avg,
            "net_amount": net_amount,
            "dict_amount": dict_amount,
            "dict_avg": dict_avg,
            "PremiumNetCount": PremiumNetCount,
            "PremiumNetCount": "{:.2f}".format(PremiumNetCount),
            "PremiumNetAvg": PremiumNetAvg,
            "PremiumNetAvg": "{:.2f}".format(PremiumNetAvg),
            "PremiumBuyCount": PremiumBuyCount,
            "PremiumSellCount": PremiumSellCount,
            "PremiumSellAvg": "{:.2f}".format(PremiumSellAvg),
            "PremiumBuyAvg": "{:.2f}".format(PremiumBuyAvg),
            "page_obj": page_obj,
            "Order_page_size": page_size,
        },
    )


@allowed_users(allowed_roles=["Broker"])
def filterfromstatusforsubjectto(request, IPOid, Groupfilter):
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    entry = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName_id=IPOid)
    Group = GroupDetail.objects.filter(user=request.user)
    try:
        gid = GroupDetail.objects.get(GroupName=Groupfilter, user=request.user).id
    except:
        pass
    IPOTypefilter = "Subject To"

    if is_valid_queryparam(Groupfilter) and Groupfilter != "All":
        entry = entry.filter(user=request.user, Order__OrderGroup_id=gid)
    if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != "All":
        entry = entry.filter(IPOType=IPOTypefilter)
    IPOTypefilterList = {"Kostak", "Subject To"}
    return render(
        request,
        "OrderDetail.html",
        {
            "entry": entry,
            "Groupfilter": Groupfilter,
            "IPOTypefilter": IPOTypefilter,
            "IPOTypefilter": IPOTypefilterList,
            "IPOName": IPOName,
            "Group": Group.order_by("GroupName"),
            "IPOid": IPOid,
        },
    )


def UpdateOrderAmount(IPOid, user):
    entry = OrderDetail.objects.filter(user=user, Order__OrderIPOName_id=IPOid)
    order = Order.objects.filter(user=user, OrderIPOName_id=IPOid)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    order.update(Amount=0)
    for i in entry:
        if i.Order.OrderCategory == "Kostak":
            if i.AllotedQty is None:
                continue
            else:
                AllotedQty = i.AllotedQty
            if i.Order.OrderType == "BUY":
                i.Order.Amount = (
                    i.Order.Amount
                    + (
                        (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                        * float(AllotedQty)
                    )
                    - i.Order.Rate
                )
            if i.Order.OrderType == "SELL":
                i.Order.Amount = i.Order.Amount + (
                    -1
                    * (
                        (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - i.Order.Rate
                    )
                )

        if i.Order.OrderCategory == "Subject To":
            if i.AllotedQty is None:
                continue
            else:
                AllotedQty = i.AllotedQty
            if AllotedQty != 0:
                if i.Order.OrderType == "BUY":
                    i.Order.Amount = (
                        i.Order.Amount
                        + (
                            (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                            * float(AllotedQty)
                        )
                        - i.Order.Rate
                    )
                if i.Order.OrderType == "SELL":
                    i.Order.Amount = i.Order.Amount + (
                        -1
                        * (
                            (
                                (float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                * float(AllotedQty)
                            )
                            - i.Order.Rate
                        )
                    )

            else:
                i.Order.Amount = i.Order.Amount + 0
        i.Order.save()
    for i in order:
        if i.OrderCategory == "Premium":
            if i.OrderType == "BUY":
                i.Amount = (
                    float(IPOName.PreOpenPrice)
                    - (float(IPOName.IPOPrice) + float(i.Rate))
                ) * int(i.Quantity)
            if i.OrderType == "SELL":
                i.Amount = -1 * (
                    (
                        float(IPOName.PreOpenPrice)
                        - (float(IPOName.IPOPrice) + float(i.Rate))
                    )
                    * int(i.Quantity)
                )
            i.save()


@csrf_exempt
def update_telly_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            updateType = data.get("updateType")
            IPOId = data.get("IPO_id")
            status = data.get("status")  # This is True or False (from JS)
            try:
                if updateType == "All":
                    Order_entry = Order.objects.filter(
                        user=request.user, OrderIPOName=IPOId
                    )
                    if Order_entry.exists():
                        Order_entry.update(Telly=status)
                    return JsonResponse({"success": True})

                else:
                    groupname = data.get("groupname")
                    Group_entry = GroupDetail.objects.get(
                        user=request.user, GroupName=groupname
                    )
                    Order_entry = Order.objects.filter(
                        user=request.user, OrderGroup=Group_entry.id, OrderIPOName=IPOId
                    )
                    if Order_entry.exists():
                        Order_entry.update(Telly=status)
                        # messages.success(request, 'Tally Status updated successfully.')
                        return JsonResponse({"success": True})
                    else:
                        # messages.error(request, 'No orders found for this group')
                        return JsonResponse(
                            {
                                "success": False,
                                "error": "No orders found for this group",
                            }
                        )
                    # Update all entries with this group name
                    # entries = YourModel.objects.filter(user=request.user, OrderGroup=groupname)
                    # if entries.exists():
                    #     entries.update(Telly=status)
                    #     return JsonResponse({'success': True})
                    # else:
                    #     return JsonResponse({'success': False, 'error': 'No matching entries'})
            except Exception as e:
                traceback.print_exc()
                # messages.error(request, f'Error occurred: {str(e)}')
                return JsonResponse({"success": False, "error": str(e)})
        except Exception as e:
            traceback.print_exc()
            # messages.error(request, f'Error occurred: {str(e)}')
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


# groupwise billing fun
@allowed_users(allowed_roles=["Broker"])
def Status(request, IPOid):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    orderdetail = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName_id=IPOid
    )
    order = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
    Group = GroupDetail.objects.filter(user=request.user)

    page_obj = None
    try:
        page_size = request.POST.get("status_page_size")
        if page_size != "" and page_size is not None:
            request.session["status_page_size"] = page_size
        else:
            page_size = request.session["status_page_size"]
    except:
        page_size = request.session.get("status_page_size", 50)

    if IPOName.IPOType == "SME":
        sme_entry_list = []
        grpname = []
        noofapp = []
        AvgRate = []
        TotalKostak = []
        TotalAllotedKostak = []
        TotalSubjectTo = []
        TotalAllotedSubjectTo = []
        noofappsubjectto = []
        AvgRatesubjectto = []
        AvgRatepremium = []
        TtotalQtypremium = []
        TtotalAmountpremium = []
        BuyKostakApp = []
        BuyKostakAllotedApp = []
        BuyKostakAmount = []
        BuySubjectToApp = []
        BuySubjectToAllotedApp = []
        BuySubjectToAmount = []
        BuyPremiumApp = []
        BuyPremiumAmount = []
        SellKostakApp = []
        SellKostakAllotedApp = []
        SellKostakAmount = []
        SellSubjectToApp = []
        SellSubjectToAllotedApp = []
        SellSubjectToAmount = []
        SellPremiumApp = []
        SellPremiumAmount = []
        TotalAmount = []
        TotalShare = []
        TotalKostakAllotedShare = []
        TotalSubjectToAllotedShare = []
        BuyKostakAllotedShare = []
        SellKostakAllotedShare = []
        BuySubjectToAllotedShare = []
        SellSubjectToAllotedShare = []
        Group_telly_status = {}
        for GroupName in Group:
            total = 0
            totalofsubjectto = 0
            entry = order.filter(user=request.user, OrderGroup=GroupName)
            if len(entry) == 0:
                continue

            sme_entry_list.append(GroupName)

        if page_size == "All":
            all_rows = True
            paginator = Paginator(sme_entry_list, len(sme_entry_list))
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(sme_entry_list, page_size)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

        for GroupName in page_obj:
            entry = order.filter(user=request.user, OrderGroup=GroupName)
            if entry.exists():
                all_true = all(e.Telly == "True" for e in entry)
                Group_telly_status[GroupName] = all_true
            else:
                Group_telly_status[GroupName] = False

            Kostakentry = entry.filter(OrderCategory="Kostak")
            NOBUYKostak = Kostakentry.filter(OrderType="BUY")
            NOBUYKostak11 = NOBUYKostak.aggregate(Sum("Quantity"))
            NOBUYKostak1 = NOBUYKostak11["Quantity__sum"]
            if NOBUYKostak1 is None:
                NOBUYKostakentry = 0
            else:
                NOBUYKostakentry = NOBUYKostak1
            NOBUYKostakentry = NOBUYKostakentry

            NOBUYKostakAllotedentry = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Kostak",
                Order__OrderType="BUY",
            ).count()

            BUYKostakentry = Kostakentry.filter(OrderType="BUY")
            BUYKostakentrytotal11 = BUYKostakentry.aggregate(Sum("Amount"))
            BUYKostakentrytotal1 = BUYKostakentrytotal11["Amount__sum"]
            if BUYKostakentrytotal1 is None:
                BUYKostakentrytotal = 0
            else:
                BUYKostakentrytotal = BUYKostakentrytotal1

            NOSELLKostak = Kostakentry.filter(OrderType="SELL")
            NOSELLKostak11 = NOSELLKostak.aggregate(Sum("Quantity"))
            NOSELLKostak1 = NOSELLKostak11["Quantity__sum"]
            if NOSELLKostak1 is None:
                NOSELLKostakentry = 0
            else:
                NOSELLKostakentry = NOSELLKostak1
            NOSELLKostakentry = NOSELLKostakentry
            NOSELLKostakAllotedentry = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Kostak",
                Order__OrderType="SELL",
            ).count()

            SELLKostakentry = Kostakentry.filter(OrderType="SELL")
            SELLKostakentrytotal11 = SELLKostakentry.aggregate(Sum("Amount"))
            SELLKostakentrytotal1 = SELLKostakentrytotal11["Amount__sum"]
            if SELLKostakentrytotal1 is None:
                SELLKostakentrytotal = 0
            else:
                SELLKostakentrytotal = SELLKostakentrytotal1

            no = NOBUYKostakentry - NOSELLKostakentry
            total = BUYKostakentrytotal + SELLKostakentrytotal
            grpname.append(GroupName)
            noofapp.append(no)
            TotalAllotedKostakt = NOBUYKostakAllotedentry - NOSELLKostakAllotedentry
            TotalAllotedKostak.append(TotalAllotedKostakt)
            BuyKostakApp.append(NOBUYKostakentry)
            BuyKostakAllotedApp.append(NOBUYKostakAllotedentry)
            SellKostakApp.append(NOSELLKostakentry)
            SellKostakAllotedApp.append(NOSELLKostakAllotedentry)
            BuyKostakAmount.append(BUYKostakentrytotal)
            SellKostakAmount.append(SELLKostakentrytotal)
            TotalKostak.append(total)

            SubjectToentry = entry.filter(OrderCategory="Subject To")
            NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum("Quantity"))
            NOBUYSubjectTo1 = NOBUYSubjectTo11["Quantity__sum"]
            if NOBUYSubjectTo1 is None:
                NOBUYSubjectToentry = 0
            else:
                NOBUYSubjectToentry = NOBUYSubjectTo1

            NOBUYSubjectToAllotedentry = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Subject To",
                Order__OrderType="BUY",
            ).count()

            NOBUYSubjectToentry = NOBUYSubjectToentry
            BUYSubjectToentry = SubjectToentry.filter(OrderType="BUY")
            BUYSubjectToentry11 = BUYSubjectToentry.aggregate(Sum("Amount"))
            BUYSubjectToentry1 = BUYSubjectToentry11["Amount__sum"]
            if BUYSubjectToentry1 is None:
                BUYSubjectToentrytotal = 0
            else:
                BUYSubjectToentrytotal = BUYSubjectToentry1

            NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum("Quantity"))
            NOSELLSubjectTo1 = NOSELLSubjectTo11["Quantity__sum"]
            if NOSELLSubjectTo1 is None:
                NOSELLSubjectToentry = 0
            else:
                NOSELLSubjectToentry = NOSELLSubjectTo1
            NOSELLSubjectToentry = NOSELLSubjectToentry

            SELLSubjectToentry = SubjectToentry.filter(OrderType="SELL")
            SELLSubjectToentry11 = SELLSubjectToentry.aggregate(Sum("Amount"))
            SELLSubjectToentry1 = SELLSubjectToentry11["Amount__sum"]
            if SELLSubjectToentry1 is None:
                SELLSubjectToentrytotal = 0
            else:
                SELLSubjectToentrytotal = SELLSubjectToentry1

            NOSELLSubjectToAllotedentry = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Subject To",
                Order__OrderType="SELL",
            ).count()

            nosubjectto = NOBUYSubjectToentry - NOSELLSubjectToentry

            totalofsubjectto = BUYSubjectToentrytotal + SELLSubjectToentrytotal

            SubjectToAllotedShare1 = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Subject To",
                Order__OrderType="BUY",
            )
            SubjectToAllotedShare11 = SubjectToAllotedShare1.aggregate(
                Sum("AllotedQty")
            )
            SubjectToAllotedShare = SubjectToAllotedShare11["AllotedQty__sum"]
            if SubjectToAllotedShare is None:
                SubjectToBuyAllotedShare = 0
            else:
                SubjectToBuyAllotedShare = SubjectToAllotedShare

            KostakAllotedShare1 = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Kostak",
                Order__OrderType="BUY",
            )
            KostakAllotedShare11 = KostakAllotedShare1.aggregate(Sum("AllotedQty"))
            KostakAllotedShare = KostakAllotedShare11["AllotedQty__sum"]
            if KostakAllotedShare is None:
                KostakBuyAllotedShare = 0
            else:
                KostakBuyAllotedShare = KostakAllotedShare

            SubjectToAllotedShare1 = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Subject To",
                Order__OrderType="SELL",
            )
            SubjectToAllotedShare11 = SubjectToAllotedShare1.aggregate(
                Sum("AllotedQty")
            )
            SubjectToAllotedShare = SubjectToAllotedShare11["AllotedQty__sum"]
            if SubjectToAllotedShare is None:
                SubjectToSellAllotedShare = 0
            else:
                SubjectToSellAllotedShare = SubjectToAllotedShare

            KostakAllotedShare1 = orderdetail.filter(
                ~Q(AllotedQty=None),
                ~Q(AllotedQty=0),
                Order__OrderGroup=GroupName,
                Order__OrderCategory="Kostak",
                Order__OrderType="SELL",
            )
            KostakAllotedShare11 = KostakAllotedShare1.aggregate(Sum("AllotedQty"))
            KostakAllotedShare = KostakAllotedShare11["AllotedQty__sum"]
            if KostakAllotedShare is None:
                KostakSellAllotedShare = 0
            else:
                KostakSellAllotedShare = KostakAllotedShare

            noofappsubjectto.append(nosubjectto)
            TotalAllotedSubjectTot = (
                NOBUYSubjectToAllotedentry - NOSELLSubjectToAllotedentry
            )
            TotalAllotedSubjectTo.append(TotalAllotedSubjectTot)
            BuySubjectToAllotedApp.append(NOBUYSubjectToAllotedentry)
            BuySubjectToApp.append(NOBUYSubjectToentry)
            SellSubjectToApp.append(NOSELLSubjectToentry)
            SellSubjectToAllotedApp.append(NOSELLSubjectToAllotedentry)
            BuySubjectToAmount.append(BUYSubjectToentrytotal)
            SellSubjectToAmount.append(SELLSubjectToentrytotal)

            TotalSubjectTo.append(totalofsubjectto)

            entry1 = order.filter(
                user=request.user, OrderGroup=GroupName, OrderCategory="Premium"
            )
            BUYPRODUCTS = entry1.filter(OrderType="BUY")
            BAvgRate = BUYPRODUCTS.aggregate(Avg("Rate"))
            BTtotalQty = BUYPRODUCTS.aggregate(Sum("Quantity"))
            BTtotalAmount = BUYPRODUCTS.aggregate(Sum("Amount"))

            SELLPRODUCTS = entry1.filter(OrderType="SELL")
            SAvgRate = SELLPRODUCTS.aggregate(Avg("Rate"))
            STtotalQty = SELLPRODUCTS.aggregate(Sum("Quantity"))
            STtotalAmount = SELLPRODUCTS.aggregate(Sum("Amount"))
            if STtotalQty["Quantity__sum"] is not None:
                STotalQty = STtotalQty["Quantity__sum"]
            else:
                STotalQty = 0
            if BTtotalQty["Quantity__sum"] is not None:
                BTotalQty = BTtotalQty["Quantity__sum"]
            else:
                BTotalQty = 0

            TtotalQtypremiumv = BTotalQty - STotalQty
            if BTtotalAmount["Amount__sum"] is not None:
                BTotalAmount = BTtotalAmount["Amount__sum"]
            else:
                BTotalAmount = 0
            if STtotalAmount["Amount__sum"] is not None:
                STotalAmount = STtotalAmount["Amount__sum"]
            else:
                STotalAmount = 0
            TtotalAmountpremiumv = BTotalAmount + STotalAmount
            TTotalKostakAllotedShare = KostakBuyAllotedShare - KostakSellAllotedShare
            TTotalSubjectToAllotedShare = (
                SubjectToBuyAllotedShare - SubjectToSellAllotedShare
            )
            TTotalShare = (
                TtotalQtypremiumv
                + TTotalKostakAllotedShare
                + TTotalSubjectToAllotedShare
            )
            TotalShare.append(TTotalShare)
            TotalKostakAllotedShare.append(TTotalKostakAllotedShare)
            TotalSubjectToAllotedShare.append(TTotalSubjectToAllotedShare)
            BuyKostakAllotedShare.append(KostakBuyAllotedShare)
            SellKostakAllotedShare.append(KostakSellAllotedShare)
            BuySubjectToAllotedShare.append(SubjectToBuyAllotedShare)
            SellSubjectToAllotedShare.append(SubjectToSellAllotedShare)
            TtotalQtypremium.append(TtotalQtypremiumv)
            BuyPremiumApp.append(BTotalQty)
            SellPremiumApp.append(STotalQty)
            BuyPremiumAmount.append(BTotalAmount)
            SellPremiumAmount.append(STotalAmount)
            TtotalAmountpremium.append(TtotalAmountpremiumv)

            TtotalAmount = total + totalofsubjectto + TtotalAmountpremiumv
            TotalAmount.append(TtotalAmount)
        Data = {
            "noofapp": noofapp,
            "TotalAllotedKostak": TotalAllotedKostak,
            "grpname": grpname,
            "BuyKostakApp": BuyKostakApp,
            "BuyKostakAllotedApp": BuyKostakAllotedApp,
            "BuyKostakAllotedShare": BuyKostakAllotedShare,
            "SellKostakApp": SellKostakApp,
            "SellKostakAllotedApp": SellKostakAllotedApp,
            "SellKostakAllotedShare": SellKostakAllotedShare,
            "BuyKostakAmount": BuyKostakAmount,
            "SellKostakAmount": SellKostakAmount,
            "noofappsubjectto": noofappsubjectto,
            "TotalAllotedSubjectTo": TotalAllotedSubjectTo,
            "BuySubjectToApp": BuySubjectToApp,
            "BuySubjectToAllotedApp": BuySubjectToAllotedApp,
            "BuySubjectToAllotedShare": BuySubjectToAllotedShare,
            "SellSubjectToApp": SellSubjectToApp,
            "SellSubjectToAllotedApp": SellSubjectToAllotedApp,
            "SellSubjectToAllotedShare": SellSubjectToAllotedShare,
            "BuySubjectToAmount": BuySubjectToAmount,
            "SellSubjectToAmount": SellSubjectToAmount,
            "TotalKostak": TotalKostak,
            "TotalSubjectTo": TotalSubjectTo,
            "TtotalQtypremium": TtotalQtypremium,
            "BuyPremiumApp": BuyPremiumApp,
            "SellPremiumApp": SellPremiumApp,
            "BuyPremiumAmount": BuyPremiumAmount,
            "SellPremiumAmount": SellPremiumAmount,
            "TtotalAmountpremium": TtotalAmountpremium,
            "TotalKostakAllotedShare": TotalKostakAllotedShare,
            "TotalSubjectToAllotedShare": TotalSubjectToAllotedShare,
            "TotalShare": TotalShare,
            "TotalAmount": TotalAmount,
        }
        df = pd.DataFrame.from_records(Data)
        html_table = "<table id='example' class='table table-bordered table-hover table-striped'style=\"max-width: 97vw;\">\n"
        html_table += "<thead><tr >"
        html_table += "<th rowspan='2' scope='col' class='tableline'>Tally &nbsp;</th>"
        html_table += (
            "<th rowspan='2' scope='col' class='tableline'>Group Name &nbsp;</th>"
        )
        html_table += "<th colspan='3'>Kostak &nbsp;</th>"
        html_table += "<th colspan='3'>Subject To &nbsp;</th>"
        html_table += "<th colspan='2'>Premium &nbsp;</th>"
        html_table += (
            "<th rowspan='2' scope='col' class='tableline'>Total Share &nbsp;</th>"
        )
        html_table += (
            "<th rowspan='2' scope='col' class='tableline'>Total Amount &nbsp;</th>"
        )
        html_table += "</tr>\n"
        html_table += "<tr>"
        # html_table += "<td></td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Billing</td>"
        # html_table += "<td></td>"
        # html_table += "<td></td>"

        html_table += "</tr></thead>"
        float_format = "{:.1f}"
        html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
        for i, row in df.iterrows():
            html_table += "<tr style='text-align: center;'>"
            checked_attr = (
                "checked" if Group_telly_status.get(row.grpname, False) else ""
            )
            html_table += f"<th><input type='checkbox' name='selectGroup' value='{row.grpname}' class='group-checkbox' {checked_attr} onchange='updateTellyStatus(this)'></th>"
            html_table += f"<th>{row.grpname}</th>"
            html_table += f"<td>"
            if row.noofapp != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.grpname}/Kostak/All" data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuyKostakApp}     SELL:{row.SellKostakApp}">'
                html_table += f"{int(row.noofapp)}</a>"
            else:
                html_table += f"{int(row.noofapp)}"
            html_table += f"</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuyKostakAllotedApp}     SELL:{row.SellKostakAllotedApp} &#013;&#010;BUY:{row.BuyKostakAllotedShare}     SELL:{row.SellKostakAllotedShare}">{row.TotalAllotedKostak}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuyKostakAmount}     SELL:{row.SellKostakAmount}">{float_format.format(row.TotalKostak)}</td>'
            html_table += f"<td>"
            if row.noofappsubjectto != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.grpname}/Subject To/All" data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuySubjectToApp}     SELL:{row.SellSubjectToApp}">'
                html_table += f"{int(row.noofappsubjectto)}</a>"
            else:
                html_table += f"{int(row.noofappsubjectto)}"
            html_table += f"</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuySubjectToAllotedApp}    SELL:{row.SellSubjectToAllotedApp} &#013;&#010;BUY:{row.BuySubjectToAllotedShare}     SELL:{row.SellSubjectToAllotedShare}">{row.TotalAllotedSubjectTo}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuySubjectToAmount}     SELL:{row.SellSubjectToAmount}">{float_format.format(row.TotalSubjectTo)}</td>'

            html_table += f"<td>"
            if row.TtotalQtypremium != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.grpname}/Premium/All" data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuyPremiumApp}     SELL:{row.SellPremiumApp}">'
                html_table += f"{int(row.TtotalQtypremium)}</a>"
            else:
                html_table += f"{int(row.TtotalQtypremium)}"
            html_table += f"</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY:{row.BuyPremiumAmount}     SELL:{row.SellPremiumAmount}">{float_format.format(row.TtotalAmountpremium)}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="Kostak:{row.TotalKostakAllotedShare}    Subject To:{row.TotalSubjectToAllotedShare}     Premium:{row.TtotalQtypremium}">{int(row.TotalShare)}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto">{float_format.format(row.TotalAmount)}</td>'
            html_table += "</tr>\n"
        html_table += "</tbody></table>"

        return render(
            request,
            "Status.html",
            {
                "html_table": html_table,
                "IPOName": IPOName,
                "IPOid": IPOid,
                "page_obj": page_obj,
                "status_page_size": page_size,
            },
        )
    else:
        OrderCategoryList = ["Kostak", "Subject To"]
        InvestorTypeList = ["RETAIL", "SHNI", "BHNI"]
        OrderTypeList = ["BUY", "SELL"]
        GrpName = []
        entry_list = []

        # Kostak Variables
        KostakRetailCount = []
        KostakRetailCountBuy = []
        KostakRetailCountSell = []

        KostakRetailAlloted = []
        KostakRetailAllotedBuy = []
        KostakRetailAllotedSell = []

        KostakRetailBilling = []
        KostakRetailBillingBuy = []
        KostakRetailBillingSell = []

        KostakSHNICount = []
        KostakSHNICountBuy = []
        KostakSHNICountSell = []

        KostakSHNIAlloted = []
        KostakSHNIAllotedBuy = []
        KostakSHNIAllotedSell = []

        KostakSHNIBilling = []
        KostakSHNIBillingBuy = []
        KostakSHNIBillingSell = []

        KostakBHNICount = []
        KostakBHNICountBuy = []
        KostakBHNICountSell = []

        KostakBHNIAlloted = []
        KostakBHNIAllotedBuy = []
        KostakBHNIAllotedSell = []

        KostakBHNIBilling = []
        KostakBHNIBillingBuy = []
        KostakBHNIBillingSell = []

        # SubjecTo Variables
        SubjectToRetailCount = []
        SubjectToRetailCountBuy = []
        SubjectToRetailCountSell = []

        SubjectToRetailAlloted = []
        SubjectToRetailAllotedBuy = []
        SubjectToRetailAllotedSell = []

        SubjectToRetailBilling = []
        SubjectToRetailBillingBuy = []
        SubjectToRetailBillingSell = []

        SubjectToSHNICount = []
        SubjectToSHNICountBuy = []
        SubjectToSHNICountSell = []

        SubjectToSHNIAlloted = []
        SubjectToSHNIAllotedBuy = []
        SubjectToSHNIAllotedSell = []

        SubjectToSHNIBilling = []
        SubjectToSHNIBillingBuy = []
        SubjectToSHNIBillingSell = []

        SubjectToBHNICount = []
        SubjectToBHNICountBuy = []
        SubjectToBHNICountSell = []

        SubjectToBHNIAlloted = []
        SubjectToBHNIAllotedBuy = []
        SubjectToBHNIAllotedSell = []

        SubjectToBHNIBilling = []
        SubjectToBHNIBillingBuy = []
        SubjectToBHNIBillingSell = []

        KostakShares = []
        SubjectToShares = []

        KostakRetailBuyShares = []
        KostakBHNIBuyShares = []
        KostakSHNIBuyShares = []

        SubjectToRetailBuyShares = []
        SubjectToBHNIBuyShares = []
        SubjectToSHNIBuyShares = []

        KostakRetailSellShares = []
        KostakBHNISellShares = []
        KostakSHNISellShares = []

        SubjectToRetailSellShares = []
        SubjectToBHNISellShares = []
        SubjectToSHNISellShares = []

        PremiumShares = []
        PremiumBuyShares = []
        PremiumSellShares = []

        PremiumBilling = []
        PremiumBuyBilling = []
        PremiumSellBilling = []

        CallBilling = []
        CallBuyBilling = []
        CallSellBilling = []

        PutBilling = []
        PutBuyBilling = []
        PutSellBilling = []

        Totalshares = []
        TotalAmount = []
        Group_telly_status = {}

        i = 0
        for GroupName in Group:
            entry = order.filter(user=request.user, OrderGroup=GroupName)
            if len(entry) == 0:
                continue

            entry_list.append(GroupName)

        if page_size == "All":
            all_rows = True
            paginator = Paginator(entry_list, len(entry_list))
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry_list, page_size)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

        for GroupName in page_obj:
            GrpName.append(GroupName)
            entry = order.filter(user=request.user, OrderGroup=GroupName)

            if entry.exists():
                all_true = all(e.Telly == "True" for e in entry)
                Group_telly_status[GroupName] = all_true
            else:
                Group_telly_status[GroupName] = False

            for Ordcat in OrderCategoryList:

                for InvTyp in InvestorTypeList:

                    # for BUY order
                    a = entry.filter(
                        OrderType="BUY", OrderCategory=Ordcat, InvestorType=InvTyp
                    )
                    b = a.aggregate(Sum("Quantity"))
                    BuyEntryCount = b["Quantity__sum"]
                    if BuyEntryCount is None:
                        BuyEntryCount = 0

                    BuyAllotedCount = orderdetail.filter(
                        ~Q(AllotedQty=None),
                        ~Q(AllotedQty=0),
                        Order__OrderGroup=GroupName,
                        Order__OrderCategory=Ordcat,
                        Order__OrderType="BUY",
                        Order__InvestorType=InvTyp,
                    ).count()

                    d = a.aggregate(Sum("Amount"))
                    BuyEntryTotal = d["Amount__sum"]
                    if BuyEntryTotal is None:
                        BuyEntryTotal = 0

                    a1 = entry.filter(
                        OrderType="SELL", OrderCategory=Ordcat, InvestorType=InvTyp
                    )
                    b1 = a1.aggregate(Sum("Quantity"))
                    SellEntryCount = b1["Quantity__sum"]
                    if SellEntryCount is None:
                        SellEntryCount = 0

                    SellAllotedCount = orderdetail.filter(
                        ~Q(AllotedQty=None),
                        ~Q(AllotedQty=0),
                        Order__OrderGroup=GroupName,
                        Order__OrderCategory=Ordcat,
                        Order__OrderType="SELL",
                        Order__InvestorType=InvTyp,
                    ).count()

                    d1 = a1.aggregate(Sum("Amount"))
                    SellEntryTotal = d1["Amount__sum"]
                    if SellEntryTotal is None:
                        SellEntryTotal = 0

                    EntryCount = BuyEntryCount - SellEntryCount
                    AllotedCount = BuyAllotedCount - SellAllotedCount
                    EntryTotal = BuyEntryTotal + SellEntryTotal

                    if Ordcat == "Kostak":
                        if InvTyp == "RETAIL":
                            KostakRetailCount.append(EntryCount)
                            KostakRetailCountBuy.append(BuyEntryCount)
                            KostakRetailCountSell.append(SellEntryCount)
                            KostakRetailAlloted.append(AllotedCount)
                            KostakRetailAllotedBuy.append(BuyAllotedCount)
                            KostakRetailAllotedSell.append(SellAllotedCount)
                            KostakRetailBilling.append(EntryTotal)
                            KostakRetailBillingBuy.append(BuyEntryTotal)
                            KostakRetailBillingSell.append(SellEntryTotal)

                        elif InvTyp == "SHNI":
                            KostakSHNICount.append(EntryCount)
                            KostakSHNICountBuy.append(BuyEntryCount)
                            KostakSHNICountSell.append(SellEntryCount)
                            KostakSHNIAlloted.append(AllotedCount)
                            KostakSHNIAllotedBuy.append(BuyAllotedCount)
                            KostakSHNIAllotedSell.append(SellAllotedCount)
                            KostakSHNIBilling.append(EntryTotal)
                            KostakSHNIBillingBuy.append(BuyEntryTotal)
                            KostakSHNIBillingSell.append(SellEntryTotal)

                        else:
                            KostakBHNICount.append(EntryCount)
                            KostakBHNICountBuy.append(BuyEntryCount)
                            KostakBHNICountSell.append(SellEntryCount)
                            KostakBHNIAlloted.append(AllotedCount)
                            KostakBHNIAllotedBuy.append(BuyAllotedCount)
                            KostakBHNIAllotedSell.append(SellAllotedCount)
                            KostakBHNIBilling.append(EntryTotal)
                            KostakBHNIBillingBuy.append(BuyEntryTotal)
                            KostakBHNIBillingSell.append(SellEntryTotal)
                    else:
                        if InvTyp == "RETAIL":
                            SubjectToRetailCount.append(EntryCount)
                            SubjectToRetailCountBuy.append(BuyEntryCount)
                            SubjectToRetailCountSell.append(SellEntryCount)
                            SubjectToRetailAlloted.append(AllotedCount)
                            SubjectToRetailAllotedBuy.append(BuyAllotedCount)
                            SubjectToRetailAllotedSell.append(SellAllotedCount)
                            SubjectToRetailBilling.append(EntryTotal)
                            SubjectToRetailBillingBuy.append(BuyEntryTotal)
                            SubjectToRetailBillingSell.append(SellEntryTotal)

                        elif InvTyp == "SHNI":
                            SubjectToSHNICount.append(EntryCount)
                            SubjectToSHNICountBuy.append(BuyEntryCount)
                            SubjectToSHNICountSell.append(SellEntryCount)
                            SubjectToSHNIAlloted.append(AllotedCount)
                            SubjectToSHNIAllotedBuy.append(BuyAllotedCount)
                            SubjectToSHNIAllotedSell.append(SellAllotedCount)
                            SubjectToSHNIBilling.append(EntryTotal)
                            SubjectToSHNIBillingBuy.append(BuyEntryTotal)
                            SubjectToSHNIBillingSell.append(SellEntryTotal)

                        else:
                            SubjectToBHNICount.append(EntryCount)
                            SubjectToBHNICountBuy.append(BuyEntryCount)
                            SubjectToBHNICountSell.append(SellEntryCount)
                            SubjectToBHNIAlloted.append(AllotedCount)
                            SubjectToBHNIAllotedBuy.append(BuyAllotedCount)
                            SubjectToBHNIAllotedSell.append(SellAllotedCount)
                            SubjectToBHNIBilling.append(EntryTotal)
                            SubjectToBHNIBillingBuy.append(BuyEntryTotal)
                            SubjectToBHNIBillingSell.append(SellEntryTotal)

            a3 = entry.filter(
                user=request.user,
                OrderGroup=GroupName,
                OrderCategory="Premium",
                OrderType="BUY",
            )
            b3 = a3.aggregate(Sum("Quantity"))
            BuyPremiumShares = b3["Quantity__sum"]
            if BuyPremiumShares is None:
                BuyPremiumShares = 0

            c3 = a3.aggregate(Sum("Amount"))
            BuyPremiumAmount = c3["Amount__sum"]
            if BuyPremiumAmount is None:
                BuyPremiumAmount = 0

            a4 = entry.filter(
                user=request.user,
                OrderGroup=GroupName,
                OrderCategory="Premium",
                OrderType="SELL",
            )
            b4 = a4.aggregate(Sum("Quantity"))
            SellPremiumShares = b4["Quantity__sum"]
            if SellPremiumShares is None:
                SellPremiumShares = 0

            c4 = a4.aggregate(Sum("Amount"))
            SellPremiumAmount = c4["Amount__sum"]
            if SellPremiumAmount is None:
                SellPremiumAmount = 0

            PremiumSharesTotal = BuyPremiumShares - SellPremiumShares
            PremiumBillingTotal = BuyPremiumAmount + SellPremiumAmount

            PremiumShares.append(PremiumSharesTotal)
            PremiumBuyShares.append(BuyPremiumShares)
            PremiumSellShares.append(SellPremiumShares)
            PremiumBilling.append(PremiumBillingTotal)
            PremiumBuyBilling.append(BuyPremiumAmount)
            PremiumSellBilling.append(SellPremiumAmount)

            Call_Buy = entry.filter(
                user=request.user,
                OrderGroup=GroupName,
                OrderCategory="CALL",
                OrderType="BUY",
            )
            c5 = Call_Buy.aggregate(Sum("Amount"))
            Call_BuyAmount = c5["Amount__sum"]
            if Call_BuyAmount is None:
                Call_BuyAmount = 0

            Call_Sell = entry.filter(
                user=request.user,
                OrderGroup=GroupName,
                OrderCategory="CALL",
                OrderType="SELL",
            )
            c6 = Call_Sell.aggregate(Sum("Amount"))
            Call_SellAmount = c6["Amount__sum"]
            if Call_SellAmount is None:
                Call_SellAmount = 0

            CallBillingTotal = Call_BuyAmount + Call_SellAmount
            CallBilling.append(CallBillingTotal)
            CallBuyBilling.append(Call_BuyAmount)
            CallSellBilling.append(Call_SellAmount)

            Put_Buy = entry.filter(
                user=request.user,
                OrderGroup=GroupName,
                OrderCategory="PUT",
                OrderType="BUY",
            )
            c7 = Put_Buy.aggregate(Sum("Amount"))
            Put_BuyAmount = c7["Amount__sum"]
            if Put_BuyAmount is None:
                Put_BuyAmount = 0

            Put_Sell = entry.filter(
                user=request.user,
                OrderGroup=GroupName,
                OrderCategory="PUT",
                OrderType="SELL",
            )
            c8 = Put_Sell.aggregate(Sum("Amount"))
            Put_SellAmount = c8["Amount__sum"]
            if Put_SellAmount is None:
                Put_SellAmount = 0

            PutBillingTotal = Put_BuyAmount + Put_SellAmount
            PutBilling.append(PutBillingTotal)
            PutBuyBilling.append(Put_BuyAmount)
            PutSellBilling.append(Put_SellAmount)

            y = orderdetail.filter(
                ~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderGroup=GroupName
            )
            x = y.filter(Order__OrderType="BUY", Order__OrderCategory="Kostak")

            RetailKostakBuyShares = x.filter(Order__InvestorType="RETAIL").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if RetailKostakBuyShares is None:
                RetailKostakBuyShares = 0
            SHNIKostakBuyShares = x.filter(Order__InvestorType="SHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if SHNIKostakBuyShares is None:
                SHNIKostakBuyShares = 0
            BHNIKostakBuyShares = x.filter(Order__InvestorType="BHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if BHNIKostakBuyShares is None:
                BHNIKostakBuyShares = 0

            x1 = y.filter(Order__OrderType="BUY", Order__OrderCategory="Subject To")

            RetailSubjectToBuyShares = x1.filter(
                Order__InvestorType="RETAIL"
            ).aggregate(Sum("AllotedQty"))["AllotedQty__sum"]
            if RetailSubjectToBuyShares is None:
                RetailSubjectToBuyShares = 0
            SHNISubjectToBuyShares = x1.filter(Order__InvestorType="SHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if SHNISubjectToBuyShares is None:
                SHNISubjectToBuyShares = 0
            BHNISubjectToBuyShares = x1.filter(Order__InvestorType="BHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if BHNISubjectToBuyShares is None:
                BHNISubjectToBuyShares = 0

            x3 = y.filter(Order__OrderType="SELL", Order__OrderCategory="Kostak")

            RetailKostakSellShares = x3.filter(Order__InvestorType="RETAIL").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if RetailKostakSellShares is None:
                RetailKostakSellShares = 0
            SHNIKostakSellShares = x3.filter(Order__InvestorType="SHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if SHNIKostakSellShares is None:
                SHNIKostakSellShares = 0
            BHNIKostakSellShares = x3.filter(Order__InvestorType="BHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if BHNIKostakSellShares is None:
                BHNIKostakSellShares = 0

            x4 = y.filter(Order__OrderType="SELL", Order__OrderCategory="Subject To")

            RetailSubjectToSellShares = x4.filter(
                Order__InvestorType="RETAIL"
            ).aggregate(Sum("AllotedQty"))["AllotedQty__sum"]
            if RetailSubjectToSellShares is None:
                RetailSubjectToSellShares = 0
            SHNISubjectToSellShares = x4.filter(Order__InvestorType="SHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if SHNISubjectToSellShares is None:
                SHNISubjectToSellShares = 0
            BHNISubjectToSellShares = x4.filter(Order__InvestorType="BHNI").aggregate(
                Sum("AllotedQty")
            )["AllotedQty__sum"]
            if BHNISubjectToSellShares is None:
                BHNISubjectToSellShares = 0

            KostakRetailBuyShares.append(RetailKostakBuyShares)
            KostakBHNIBuyShares.append(BHNIKostakBuyShares)
            KostakSHNIBuyShares.append(SHNIKostakBuyShares)

            SubjectToRetailBuyShares.append(RetailSubjectToBuyShares)
            SubjectToBHNIBuyShares.append(BHNISubjectToBuyShares)
            SubjectToSHNIBuyShares.append(SHNISubjectToBuyShares)

            KostakRetailSellShares.append(RetailKostakSellShares)
            KostakBHNISellShares.append(BHNIKostakSellShares)
            KostakSHNISellShares.append(SHNIKostakSellShares)

            SubjectToRetailSellShares.append(RetailSubjectToSellShares)
            SubjectToBHNISellShares.append(BHNISubjectToSellShares)
            SubjectToSHNISellShares.append(SHNISubjectToSellShares)

            TotalAmt = (
                PremiumBillingTotal
                + KostakRetailBilling[i]
                + KostakSHNIBilling[i]
                + KostakBHNIBilling[i]
                + SubjectToRetailBilling[i]
                + SubjectToSHNIBilling[i]
                + SubjectToBHNIBilling[i]
                + CallBillingTotal
                + PutBillingTotal
            )

            Totalshrs = (
                RetailKostakBuyShares
                + BHNIKostakBuyShares
                + SHNIKostakBuyShares
                + RetailSubjectToBuyShares
                + BHNISubjectToBuyShares
                + SHNISubjectToBuyShares
                - (
                    RetailKostakSellShares
                    + BHNIKostakSellShares
                    + SHNIKostakSellShares
                    + RetailSubjectToSellShares
                    + BHNISubjectToSellShares
                    + SHNISubjectToSellShares
                )
                + PremiumSharesTotal
            )

            TotalKostakShares = (
                RetailKostakBuyShares
                + BHNIKostakBuyShares
                + SHNIKostakBuyShares
                - (RetailKostakSellShares + BHNIKostakSellShares + SHNIKostakSellShares)
            )
            TotalSubjectToShares = (
                RetailSubjectToBuyShares
                + BHNISubjectToBuyShares
                + SHNISubjectToBuyShares
                - (
                    RetailSubjectToSellShares
                    + BHNISubjectToSellShares
                    + SHNISubjectToSellShares
                )
            )

            KostakShares.append(TotalKostakShares)
            SubjectToShares.append(TotalSubjectToShares)
            Totalshares.append(Totalshrs)
            TotalAmount.append(TotalAmt)
            i = i + 1

        Data = {
            "KostakRetailBuyShares": KostakRetailBuyShares,
            "KostakBHNIBuyShares": KostakBHNIBuyShares,
            "KostakSHNIBuyShares": KostakSHNIBuyShares,
            "SubjectToRetailBuyShares": SubjectToRetailBuyShares,
            "SubjectToBHNIBuyShares": SubjectToBHNIBuyShares,
            "SubjectToSHNIBuyShares": SubjectToSHNIBuyShares,
            "KostakRetailSellShares": KostakRetailSellShares,
            "KostakBHNISellShares": KostakBHNISellShares,
            "KostakSHNISellShares": KostakSHNISellShares,
            "SubjectToRetailSellShares": SubjectToRetailSellShares,
            "SubjectToBHNISellShares": SubjectToBHNISellShares,
            "SubjectToSHNISellShares": SubjectToSHNISellShares,
            "PremiumBuyBilling": PremiumBuyBilling,
            "PremiumSellBilling": PremiumSellBilling,
            "CallSellBilling": CallSellBilling,
            "CallBuyBilling": CallBuyBilling,
            "PutSellBilling": PutSellBilling,
            "PutBuyBilling": PutBuyBilling,
            "SubjectToBHNIAllotedSell": SubjectToBHNIAllotedSell,
            "SubjectToBHNIBillingBuy": SubjectToBHNIBillingBuy,
            "SubjectToBHNIAllotedBuy": SubjectToBHNIAllotedBuy,
            "SubjectToBHNIBillingSell": SubjectToBHNIBillingSell,
            "SubjectToSHNIAllotedSell": SubjectToSHNIAllotedSell,
            "SubjectToSHNIBillingBuy": SubjectToSHNIBillingBuy,
            "SubjectToSHNIAllotedBuy": SubjectToSHNIAllotedBuy,
            "SubjectToSHNIBillingSell": SubjectToSHNIBillingSell,
            "SubjectToRetailAllotedSell": SubjectToRetailAllotedSell,
            "SubjectToRetailBillingBuy": SubjectToRetailBillingBuy,
            "SubjectToRetailBillingBuy": SubjectToRetailBillingBuy,
            "SubjectToRetailAllotedBuy": SubjectToRetailAllotedBuy,
            "SubjectToRetailBillingSell": SubjectToRetailBillingSell,
            "KostakBHNIAllotedSell": KostakBHNIAllotedSell,
            "KostakBHNIBillingBuy": KostakBHNIBillingBuy,
            "KostakBHNIAllotedBuy": KostakBHNIAllotedBuy,
            "KostakBHNIBillingSell": KostakBHNIBillingSell,
            "KostakSHNIAllotedSell": KostakSHNIAllotedSell,
            "KostakSHNIBillingBuy": KostakSHNIBillingBuy,
            "KostakSHNIAllotedBuy": KostakSHNIAllotedBuy,
            "KostakSHNIBillingSell": KostakSHNIBillingSell,
            "KostakRetailAllotedSell": KostakRetailAllotedSell,
            "KostakRetailBillingBuy": KostakRetailBillingBuy,
            "KostakRetailAllotedBuy": KostakRetailAllotedBuy,
            "KostakRetailBillingSell": KostakRetailBillingSell,
            "KostakShares": KostakShares,
            "SubjectToShares": SubjectToShares,
            "PremiumBuyShares": PremiumBuyShares,
            "PremiumSellShares": PremiumSellShares,
            "SubjectToRetailCountSell": SubjectToRetailCountSell,
            "SubjectToSHNICountSell": SubjectToSHNICountSell,
            "SubjectToBHNICountSell": SubjectToBHNICountSell,
            "SubjectToBHNICountSell": SubjectToBHNICountSell,
            "SubjectToRetailCountBuy": SubjectToRetailCountBuy,
            "SubjectToSHNICountBuy": SubjectToSHNICountBuy,
            "SubjectToBHNICountBuy": SubjectToBHNICountBuy,
            "KostakRetailCountSell": KostakRetailCountSell,
            "KostakSHNICountSell": KostakSHNICountSell,
            "KostakBHNICountSell": KostakBHNICountSell,
            "KostakRetailCountBuy": KostakRetailCountBuy,
            "KostakSHNICountBuy": KostakSHNICountBuy,
            "KostakBHNICountBuy": KostakBHNICountBuy,
            "Totalshares": Totalshares,
            "TotalAmount": TotalAmount,
            "PremiumShares": PremiumShares,
            "PremiumBilling": PremiumBilling,
            "CallBilling": CallBilling,
            "PutBilling": PutBilling,
            "GrpName": GrpName,
            "KostakRetailCount": KostakRetailCount,
            "KostakRetailAlloted": KostakRetailAlloted,
            "KostakRetailBilling": KostakRetailBilling,
            "KostakSHNICount": KostakSHNICount,
            "KostakSHNIAlloted": KostakSHNIAlloted,
            "KostakSHNIBilling": KostakSHNIBilling,
            "KostakBHNICount": KostakBHNICount,
            "KostakBHNIAlloted": KostakBHNIAlloted,
            "KostakBHNIBilling": KostakBHNIBilling,
            "SubjectToRetailCount": SubjectToRetailCount,
            "SubjectToRetailAlloted": SubjectToRetailAlloted,
            "SubjectToRetailBilling": SubjectToRetailBilling,
            "SubjectToRetailBilling": SubjectToRetailBilling,
            "SubjectToSHNICount": SubjectToSHNICount,
            "SubjectToSHNIAlloted": SubjectToSHNIAlloted,
            "SubjectToSHNIBilling": SubjectToSHNIBilling,
            "SubjectToBHNICount": SubjectToBHNICount,
            "SubjectToBHNIAlloted": SubjectToBHNIAlloted,
            "SubjectToBHNIBilling": SubjectToBHNIBilling,
        }

        all_groups_checked = (
            all(Group_telly_status.values()) if Group_telly_status else False
        )
        df = pd.DataFrame.from_records(Data)

        html_table = '<table id="example" class="table table-bordered table-hover table-striped" style="max-width: 100vw;" >\n'
        html_table += "<thead><tr >"
        # html_table += "<th rowspan='3' style='text-align: center;'>Tally</th>"
        html_table += f"<th rowspan='3' scope='col' class='tableline'><input type='checkbox' id='master-tally-checkbox' {'checked' if all_groups_checked else ''} onchange='updateAllTellyStatus(this)'> Tally &nbsp;</th>"
        html_table += "<th rowspan='3' style='text-align: center;'>Group Name</th>"
        html_table += "<td colspan='9'>Kostak &nbsp;</td>"
        html_table += "<td colspan='9'>Subject To &nbsp;</td>"
        html_table += "<td colspan='2' rowspan='2' ><b>Premium &nbsp;</b></td>"
        html_table += "<td colspan='2' rowspan='2' ><b>OPTIONS &nbsp;</b></td>"
        html_table += (
            "<td colspan='2' rowspan='2' scope='col'  class='tableline'>Total</td>"
        )
        html_table += "</tr>\n"

        html_table += "<tr>"
        html_table += (
            '<td colspan="3"  data-sort-type="numeric" scope="col"><b>Retail</b></td>'
        )
        html_table += (
            '<td colspan="3"  data-sort-type="numeric" scope="col"><b>SHNI</b></td>'
        )
        html_table += (
            '<td colspan="3"  data-sort-type="numeric" scope="col"><b>BHNI</b></td>'
        )
        html_table += (
            '<td colspan="3"  data-sort-type="numeric" scope="col"><b>Retail</b></td>'
        )
        html_table += (
            '<td colspan="3"  data-sort-type="numeric" scope="col"><b>SHNI</b></td>'
        )
        html_table += (
            '<td colspan="3"  data-sort-type="numeric" scope="col"><b>BHNI</b></td>'
        )
        # html_table += '<td colspan="2"  data-sort-type="numeric" scope="col"> </td>'
        # html_table += '<td colspan="2" scope="col"  class="tableline"><b>Total</b></td>'
        html_table += "</tr>\n"

        html_table += "<tr>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Shares</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Call Amount</td>"
        html_table += "<td>Put Amount</td>"
        html_table += "<td>Shares</td>"
        html_table += "<td>Amount</td>"
        html_table += "</tr></thead>"

        float_format = "{:.1f}"
        html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
        for i, row in df.iterrows():
            html_table += "<tr style='text-align: center;'>"
            checked_attr = (
                "checked" if Group_telly_status.get(row.GrpName, False) else ""
            )
            html_table += f"<th><input type='checkbox' name='selectGroup' value='{row.GrpName}' class='group-checkbox' {checked_attr} onchange='updateTellyStatus(this)' ></th>"
            html_table += f"<th>{row.GrpName}</th>"
            html_table += f"<td>"
            if row.KostakRetailCount != 0:
                html_table += f'<a style=\'color:blue; text-decoration-line: underline;\'   href="/{IPOid}/Order/{row.GrpName}/Kostak/RETAIL" data-toggle="tooltip" data-placement="auto" title="BUY:{float_format.format(row.KostakRetailCountBuy)}     SELL:{float_format.format(row.KostakRetailCountSell)}">'
                html_table += f"{int(row.KostakRetailCount)}</a>"
            else:
                html_table += f"{int(row.KostakRetailCount)}"
            html_table += "</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY-K: {float_format.format(row.KostakRetailAllotedBuy)}     SELL-K: {float_format.format(row.KostakRetailAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.KostakRetailBuyShares)}    SELL-Sh:{float_format.format(row.KostakRetailSellShares)}">{row.KostakRetailAlloted}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.KostakRetailBillingBuy)}     SELL: {float_format.format(row.KostakRetailBillingSell)}">{float_format.format(row.KostakRetailBilling)}</td>'

            html_table += f"<td>"
            if row.KostakSHNICount != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.GrpName}/Kostak/SHNI" data-toggle="tooltip" data-placement="auto" title="BUY:{float_format.format(row.KostakSHNICountBuy)}     SELL:{float_format.format(row.KostakSHNICountSell)}">'
                html_table += f"{int(row.KostakSHNICount)}</a>"
            else:
                html_table += f"{int(row.KostakSHNICount)}"
            html_table += "</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY-K: {float_format.format(row.KostakSHNIAllotedBuy)}     SELL-K: {float_format.format(row.KostakSHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.KostakSHNIBuyShares)}    SELL-Sh:{float_format.format(row.KostakSHNISellShares)}">{row.KostakSHNIAlloted}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.KostakSHNIBillingBuy)}     SELL: {float_format.format(row.KostakSHNIBillingSell)}">{float_format.format(row.KostakSHNIBilling)}</td>'

            html_table += f"<td>"
            if row.KostakBHNICount != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.GrpName}/Kostak/BHNI" data-toggle="tooltip" data-placement="auto" title="BUY:{float_format.format(row.KostakBHNICountBuy)}     SELL:{float_format.format(row.KostakBHNICountSell)}">'
                html_table += f"{int(row.KostakBHNICount)}</a>"
            else:
                html_table += f"{int(row.KostakBHNICount)}"
            html_table += "</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY-K: {float_format.format(row.KostakBHNIAllotedBuy)}     SELL-K: {float_format.format(row.KostakBHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.KostakBHNIBuyShares)}    SELL-Sh:{float_format.format(row.KostakBHNISellShares)}">{row.KostakBHNIAlloted}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.KostakBHNIBillingBuy)}     SELL: {float_format.format(row.KostakBHNIBillingBuy)}">{float_format.format(row.KostakBHNIBilling)}</td>'

            html_table += f"<td>"
            if row.SubjectToRetailCount != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.GrpName}/Subject To/RETAIL" data-toggle="tooltip" data-placement="auto" title="BUY:{float_format.format(row.SubjectToRetailCountBuy)}     SELL:{float_format.format(row.SubjectToRetailCountSell)}">'
                html_table += f"{int(row.SubjectToRetailCount)}</a>"
            else:
                html_table += f"{int(row.SubjectToRetailCount)}"
            html_table += "</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY-S: {float_format.format(row.SubjectToRetailAllotedBuy)}     SELL-S: {float_format.format(row.SubjectToRetailAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.SubjectToRetailBuyShares)}    SELL-Sh:{float_format.format(row.SubjectToRetailSellShares)}">{row.SubjectToRetailAlloted}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.SubjectToRetailBillingBuy)}     SELL: {float_format.format(row.SubjectToRetailBillingSell)}">{float_format.format(row.SubjectToRetailBilling)}</td>'

            html_table += f"<td>"
            if row.SubjectToSHNICount != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.GrpName}/Subject To/SHNI" data-toggle="tooltip" data-placement="auto" title="BUY:{float_format.format(row.SubjectToSHNICountBuy)}     SELL:{float_format.format(row.SubjectToSHNICountSell)}">'
                html_table += f"{int(row.SubjectToSHNICount)}</a>"
            else:
                html_table += f"{int(row.SubjectToSHNICount)}"
            html_table += "</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY-S: {float_format.format(row.SubjectToSHNIAllotedBuy)}     SELL-S: {float_format.format(row.SubjectToSHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.SubjectToSHNIBuyShares)}    SELL-Sh:{float_format.format(row.SubjectToSHNISellShares)}">{float_format.format(row.SubjectToSHNIAlloted)}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.SubjectToSHNIBillingBuy)}     SELL: {float_format.format(row.SubjectToSHNIBillingSell)}">{float_format.format(row.SubjectToSHNIBilling)}</td>'

            html_table += f"<td>"
            if row.SubjectToBHNICount != 0:
                html_table += f'<a style="color:blue; text-decoration-line: underline;"   href="/{IPOid}/Order/{row.GrpName}/Subject To/BHNI"0 data-toggle="tooltip" data-placement="auto" title="BUY:{float_format.format(row.SubjectToBHNICountBuy)}     SELL:{float_format.format(row.SubjectToBHNICountSell)}">'
                html_table += f"{int(row.SubjectToBHNICount)}</a>"
            else:
                html_table += f"{int(row.SubjectToBHNICount)}"
            html_table += "</td>"
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY-S: {float_format.format(row.SubjectToBHNIAllotedBuy)}     SELL-S: {float_format.format(row.SubjectToBHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.SubjectToBHNIBuyShares)}    SELL-Sh:{float_format.format(row.SubjectToBHNISellShares)}">{row.SubjectToBHNIAlloted}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.SubjectToBHNIBillingBuy)}     SELL: {float_format.format(row.SubjectToBHNIBillingSell)}">{float_format.format(row.SubjectToBHNIBilling)}</td>'

            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.PremiumBuyShares)}     SELL: {float_format.format(row.PremiumSellShares)}">{int(row.PremiumShares)}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {row.PremiumBuyBilling}     SELL: {float_format.format(row.PremiumSellBilling)}">{float_format.format(row.PremiumBilling)}</td>'

            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.CallBuyBilling)}     SELL: {float_format.format(row.CallSellBilling)}">{float_format.format(row.CallBilling)}</td>'
            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="BUY: {float_format.format(row.PutBuyBilling)}     SELL: {float_format.format(row.PutSellBilling)}">{float_format.format(row.PutBilling)}</td>'

            html_table += f'<td data-toggle="tooltip" data-placement="auto" title="Kostak:{float_format.format(row.KostakShares)}     Subject To:{float_format.format(row.SubjectToShares)}     Premium:{float_format.format(row.PremiumShares)}" >{float_format.format(row.Totalshares)}</td>'
            html_table += f"<td>{float_format.format(row.TotalAmount)}</td>"
            html_table += "</tr>\n"
        html_table += "</tbody></table>"
        return render(
            request,
            "Status.html",
            {
                "html_table": html_table,
                "IPOName": IPOName,
                "IPOid": IPOid,
                "page_obj": page_obj,
                "status_page_size": page_size,
            },
        )


# group wise dashboard payment fun
@allowed_users(allowed_roles=["Broker"])
def AddPayment(request):
    Group = GroupDetail.objects.filter(user=request.user)
    if request.method == "POST":
        GroupName = request.POST.get("Group", "")
        Amount = request.POST.get("Amount", "")

        group = Group.get(GroupName=GroupName, user=request.user)
        group.Collection = group.Collection + float(Amount)
        group.save()
    return redirect("/GroupWiseDashboard")


@allowed_users(allowed_roles=["Broker"])
def GroupWiseDashboard(request):
    Group = GroupDetail.objects.filter(user=request.user)
    IPO = CurrentIpoName.objects.filter(user=request.user)
    ipos = CurrentIpoName.objects.filter(user=request.user)
    groups = GroupDetail.objects.filter(user=request.user)
    grpname = []
    Collectionlist = []
    IPOName = []
    IPOAmount = []
    nlist = []
    l = []
    Total = 0
    all_grpname = []
    JV_list = []

    for Group_name in Group:
        all_grpname.append(Group_name)

    page_obj = None
    try:
        page_size = request.POST.get("GWD_page_size")
        if page_size != "" and page_size is not None:
            request.session["GWD_page_size"] = page_size
        else:
            page_size = request.session["GWD_page_size"]
    except:
        page_size = request.session.get("GWD_page_size", 50)

    # page_size = request.POST.get('GWD_page_size') or request.session.get('GWD_page_size', 50)

    # if page_size == 'All':
    #     paginator = Paginator(Group, len(Group))
    # else:
    #     paginator = Paginator(Group, int(page_size))

    # # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_size)  # <-- page_obj is now safe to use

    if page_size == "All":
        all_rows = True
        paginator = Paginator(Group, len(Group))
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(Group, page_size)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    for GroupName in page_obj:
        credit = (
            Accounting.objects.filter(
                user=request.user, group=GroupName, jv=True, amount_type="credit"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Sum of debits
        debit = (
            Accounting.objects.filter(
                user=request.user, group=GroupName, jv=True, amount_type="debit"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        # jv_total = credit - debit
        JV_list.append(credit - debit)

    for IpoName in IPO:
        entry = Order.objects.filter(user=request.user, OrderIPOName=IpoName)
        total = 0
        for i in entry:
            total = total + i.Amount
        Total = Total + total
        # if (total):
        if IpoName.IPOPrice != IpoName.PreOpenPrice:
            IPOAmount.append(total)
        else:
            total = 0
            IPOAmount.append(total)
        IPOName.append(IpoName)

    lenofipo = len(IPOName)
    for j in range(0, lenofipo):
        l.append(j)
    SumCollection = 0
    for GroupName, jv in zip(page_obj, JV_list):
        total_collection = GroupName.Collection + float(jv)  # Collection + JV
        SumCollection += total_collection
        Collectionlist.append(total_collection)  # use this for table
        grpname.append(GroupName)

    accountingTotal = {}
    # accounting_amount_dict = {}
    for GroupName in page_obj:
        IPOTotal = []
        # accountingTotal = []
        for IpoName in IPOName:
            if IpoName.IPOName in accountingTotal:
                total1 = accountingTotal[IpoName.IPOName]
            else:
                total1 = 0

            if IpoName.IPOPrice != IpoName.PreOpenPrice:

                total = 0
                DueAmount = 0
                entry = Order.objects.filter(
                    user=request.user, OrderGroup=GroupName, OrderIPOName=IpoName
                )

                accounting_amount = (
                    Accounting.objects.filter(
                        group=GroupName, ipo=IpoName, user=request.user
                    ).aggregate(
                        total=Sum(
                            Case(
                                When(amount_type="credit", then=F("amount")),
                                When(amount_type="debit", then=-F("amount")),
                                output_field=DecimalField(),
                            )
                        )
                    )[
                        "total"
                    ]
                    or 0
                )
                accounting_amount = float(accounting_amount)
                # accounting_amount_dict[(GroupName.id, IpoName.id)] = accounting_amount
                total1 = total1 + float(accounting_amount)
                for i in entry:
                    total = total + i.Amount
            else:
                total = 0
                # accounting_amount_dict[(GroupName.id, IpoName.id)] = 0
            IPOTotal.append(total)
            # accountingTotal.append(total1)
            accountingTotal[IpoName.IPOName] = total1
        nlist.append(IPOTotal)

    # total_jv = sum(JV_list)
    accounting_dict = {}

    all_groups = GroupDetail.objects.filter(user=request.user)

    qs = (
        Accounting.objects.filter(
            user=request.user, group__in=all_groups, ipo__in=IPOName
        )
        .values("group", "ipo")
        .annotate(
            total=Sum(
                Case(
                    When(amount_type="credit", then=F("amount")),
                    When(amount_type="debit", then=-F("amount")),
                    output_field=DecimalField(),
                )
            )
        )
    )

    accounting_dict = {
        (entry["group"], entry["ipo"]): entry["total"] or 0 for entry in qs
    }
    # Precompute due amounts for all group-IPO combinations
    due_dict = {}  # (group.id, ipo.id) -> due_amount

    for group in all_groups:
        for ipo, ipo_amount in zip(IPOName, IPOAmount):
            # Skip IPOs where IPOPrice == PreOpenPrice
            if ipo.IPOPrice != ipo.PreOpenPrice:
                total_order_amount = (
                    Order.objects.filter(
                        user=request.user, OrderGroup=group, OrderIPOName=ipo
                    ).aggregate(total=Sum("Amount"))["total"]
                    or 0
                )

                accounting_amount1 = accounting_dict.get((group.id, ipo.id), 0)
                due_amount = float(total_order_amount) - float(accounting_amount1)

                due_dict[(group.id, ipo.id)] = due_amount
            else:
                due_dict[(group.id, ipo.id)] = 0
    # print(due_dict)

    dfi = pd.DataFrame({"IPOAmount": IPOAmount})
    df = pd.DataFrame(nlist, columns=IPOName, index=grpname)
    df["JV"] = JV_list  # <-- new JV column
    df["Total"] = df[IPOName].sum(axis=1)
    df["Collection"] = Collectionlist
    df["Due Amount"] = df["Total"] - df["Collection"]
    DueAmountSum = Total - SumCollection

    html_table = "<table  >\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th class='sticky-col'>Group Name</th>"

    for i, ipo in enumerate(IPOName):

        all_due_zero = True
        # for index, row in df.iterrows():
        for group in all_groups:
            # accounting_amount1 = Accounting.objects.filter(
            #     user=request.user,
            #     group=index,
            #     ipo=ipo
            # ).aggregate(
            #     total=Sum(
            #         Case(
            #             When(amount_type='credit', then=F('amount')),
            #             When(amount_type='debit', then=-F('amount')),
            #             output_field=DecimalField()
            #         )
            #     )
            # )['total'] or 0
            # accounting_amount1 = accounting_dict.get((index.id, ipo.id), 0)
            # due_amount = float(row[ipo]) - float(accounting_amount1)
            due_amount = due_dict.get((group.id, ipo.id), 0)
            if float(due_amount) != 0:
                all_due_zero = False
                break
        html_table += "<th>"
        html_table += f"{ipo.IPOName} "

        if all_due_zero:
            html_table += f"""
                <button class="btn btn-sm btn-outline-danger"
                    data-toggle="modal" data-target="#deleteModal-{ipo.id}">
                    Delete
                </button>
            """

        html_table += "</th>"

    html_table += "<th>JV</th><th>Total</th><th>Collection</th><th>Due Amount</th>"
    # for col in df.columns:
    #     html_table += f"<td style='background :rgb(182, 182, 158)'>{col}</td>"
    html_table += "</tr></thead>\n"

    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    float_format = "{:.1f}"
    for index, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<th>{index}</th>"
        for col_name, cell in row.items():
            if (
                col_name != "JV"
                and col_name != "Total"
                and col_name != "Collection"
                and col_name != "Due Amount"
            ):
                # For IPO amount cells, add data attributes
                ipo = IPOName[list(df.columns).index(col_name)]
                # Calculate accounting amount **only for this group and IPO**
                # accounting_amount1 = Accounting.objects.filter(
                #     user=request.user,
                #     group=index,
                #     ipo=ipo
                # ).aggregate(
                #     total=Sum(
                #         Case(
                #             When(amount_type='credit', then=F('amount')),
                #             When(amount_type='debit', then=-F('amount')),
                #             output_field=DecimalField()
                #         )
                #     )
                # )['total'] or 0
                accounting_amount1 = accounting_dict.get((index.id, ipo.id), 0)
                due_amount = float(cell) - float(accounting_amount1)

                html_table += f'<td class="amount-cell" data-ipo-id="{ipo.id}" data-ipo-name="{col_name}" data-group-id="{index.id}" data-group-name="{index}">{float_format.format(cell)}<br>Acc: {float_format.format(accounting_amount1)}Due: {float_format.format(due_amount)}</td>'
            else:
                # For other cells, keep as is
                html_table += f"<td>{float_format.format(cell)}</td>"

        html_table += "</tr>\n"
    html_table += "</tbody>"
    html_table += "<tfoot><tr>"
    html_table += "<th style='width:90px;'>Total</th>"
    for i, row in dfi.iterrows():
        html_table += f"<td ondblclick=\"transaction_title()\">{float_format.format(row['IPOAmount'])}</td>"
    html_table += f"<td>{float_format.format(sum(JV_list))}</td>"
    html_table += f"<td>{float_format.format(Total)}</td>"
    html_table += f"<td>{float_format.format(SumCollection)}</td>"
    html_table += f"<td>{float_format.format(DueAmountSum)}</td>"
    html_table += "</tr></tfoot>"
    html_table += "</table>"

    entry_sorted = sorted(all_grpname, key=lambda x: x.GroupName.lower())
    return render(
        request,
        "GroupWiseDashboard.html",
        {
            "entry_sorted": entry_sorted,
            "entry": grpname,
            "lenofipo": l,
            "ipos": ipos,
            "groups": groups,
            "IPOName": IPOName,
            "html_table": html_table,
            "IPOAmount": IPOAmount,
            "Total": Total,
            "SumCollection": SumCollection,
            "DueAmountSum": DueAmountSum,
            "page_obj": page_obj,
            "GWD_page_size": page_size,
        },
    )


def BackUp(request):
    user = request.user
    entry = CurrentIpoName.objects.filter(user=request.user)

    entry = entry.order_by("-id")

    page_obj = None
    try:
        page_size = request.POST.get("Backup_page_size")
        if page_size != "" and page_size is not None:
            request.session["Backup_page_size"] = page_size
        else:
            page_size = request.session["Backup_page_size"]
    except:
        page_size = request.session.get("Backup_page_size", 50)

    Data = []
    if entry is not None and entry.exists():

        if page_size == "All":
            all_rows = True
            paginator = Paginator(entry, len(entry))
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry, page_size)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "IPOName": order_detail.IPOName,
                "sr_no": start_index + i + 1,
            }
            Data.append(entry_data)
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >"
    html_table = "<thead class=\"table-sortable\"><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th scope='col' style='width:10%;'>Sr No. &nbsp;</th>"
    html_table += "<th scope='col' style=\"width:75%;\">IPO Name &nbsp;</th>"
    html_table += "<th scope='col' style=\"width:15%;\">Action&nbsp;</th>"
    html_table += "</tr></thead>"
    html_table += "<tbody>"

    for i, row in df.iterrows():
        html_table += "<tr >"
        html_table += f"<th>{row.sr_no}</th>"
        html_table += f"<th>{row.IPOName}</th>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='/{ row.id }/Backup/';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Backup</button></td> "

        html_table += "</tr>"
    html_table += "</tbody></table>"

    return render(
        request,
        "Backup.html",
        {
            "html_table": html_table,
            "user": user,
            "page_obj": page_obj,
            "Backup_page_size": page_size,
        },
    )


@allowed_users(allowed_roles=["Broker"])
def panalloted(request):
    Client = ClientDetail.objects.filter(user=request.user)
    IPO = CurrentIpoName.objects.filter(user=request.user)
    grpname = []
    IPOName = []
    nlist = []
    l = []
    for IpoName in IPO:
        IPOName.append(IpoName)
    lenofipo = len(IPOName)
    for j in range(0, lenofipo):
        l.append(j)
    for GroupName in Client:
        grpname.append(GroupName.PANNo)
    lenofgroup = len(grpname)

    for ClientPan in Client:
        IPOTotal = []
        for IpoName in IPO:
            try:
                entry = OrderDetail.objects.get(
                    user=request.user,
                    OrderDetailPANNo=ClientPan,
                    Order__OrderIPOName=IpoName,
                )
                a = entry.AllotedQty
            except:
                a = None
            IPOTotal.append(a)
        nlist.append(IPOTotal)

    df = pd.DataFrame(nlist, columns=IPOName, index=grpname)
    return render(
        request,
        "panalloted.html",
        {
            "entry": grpname,
            "lenofipo": l,
            "IPOTotal": IPOTotal,
            "IPOName": IPOName,
            "df": df,
        },
    )


@allowed_users(allowed_roles=["Broker"])
def autocomplete(request):
    if "term" in request.GET:
        qs = ClientDetail.objects.filter(
            user=request.user, PANNo__istartswith=request.GET.get("term")
        )
        titles = list()
        for product in qs:
            titles.append(f"{product.PANNo}-{product.Name}")

        return JsonResponse(titles, safe=False)


@allowed_users(allowed_roles=["Broker"])
def autocomplete1(request):
    PAN = request.POST.get("PAN", "")
    q = ClientDetail.objects.filter(PANNo=PAN, user=request.user)
    Clients = list()
    for product in q:
        Clients.append(product.Name)
    return JsonResponse(Clients, safe=False)


async def handle_single_row(
    userid,
    PAN,
    clientname,
    allotedqty,
    DematNo,
    Application,
    rate,
    request,
    row_id,
    IPOid,
    OrderType,
    Groupfilter,
    IPOTypefilter,
    InvestorTypefilter,
    page_number,
    Order_idlist,
):
    # try:
    # Fetch employee and order group in parallel if possible
    employee_task = asyncio.to_thread(OrderDetail.objects.get, user=userid, id=row_id)
    employee = await employee_task
    query_task = asyncio.to_thread(
        ClientDetail.objects.filter, PANNo=PAN.upper(), user=userid
    )

    # employee = await employee_task
    order_group = await asyncio.to_thread(lambda: employee.Order.OrderGroup)
    query = await query_task

    if PAN:
        if await asyncio.to_thread(query.exists):
            query1 = await asyncio.to_thread(
                ClientDetail.objects.get, PANNo=PAN.upper(), user=userid
            )
            if order_group != await asyncio.to_thread(lambda: query1.Group):
                query1.Group = employee.Order.OrderGroup
            query1.Name = clientname
            await asyncio.to_thread(query1.save)
        else:
            user = request.user
            O_limit = await asyncio.to_thread(CustomUser.objects.get, username=user)
            if O_limit.Client_limit:
                Client_Count = await sync_to_async(
                    lambda: ClientDetail.objects.filter(user=user).count()
                )()
                Client_Limit = int(O_limit.Client_limit)

                if Client_Count >= Client_Limit:
                    messages.success(
                        request,
                        f"You have reached the limit of {Client_Limit} Client limits.",
                    )
                    return redirect(
                        f"/{IPOid}/OrderDetail/{OrderType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypefilter}?page={page_number}"
                    )

            PANNUMBER = ClientDetail(
                user=userid, PANNo=PAN.upper(), Name=clientname, Group=order_group
            )
            await asyncio.to_thread(PANNUMBER.save)

        r = 1
        query2 = await asyncio.to_thread(
            ClientDetail.objects.get, PANNo=PAN.upper(), user=userid
        )
        pan_exists_task = asyncio.to_thread(
            OrderDetail.objects.filter,
            user=userid,
            Order__OrderIPOName_id=IPOid,
            Order__OrderType=OrderType,
            OrderDetailPANNo=query2.id,
        )
        pan_exists = await pan_exists_task

        if await asyncio.to_thread(pan_exists.exists):
            if employee.OrderDetailPANNo_id != query2.id:
                messages.error(
                    request,
                    f"Row ['{employee.Order.OrderGroup}','{employee.Order.OrderCategory}','{employee.Order.InvestorType}','{rate}','{PAN}','{clientname}','{allotedqty}','{DematNo}','{Application}', 'PAN No already exists'] has PAN no. that already exists.",
                )
                r = 0
            else:
                r = 1

        if r == 1:
            employee.OrderDetailPANNo_id = query2.id
            employee.AllotedQty = None if allotedqty == "" else allotedqty
            employee.DematNumber = DematNo
            employee.ApplicationNumber = Application
            await asyncio.to_thread(employee.save)

        if employee.Order_id not in Order_idlist:
            Order_idlist.append(employee.Order_id)
            # calculate(IPOid, request.user,employee.Order_id)


# except Exception as e:
#     traceback.print_exc()
# Log the error and handle it appropriately
# print(f"Error handling row {row_id}: {e}")


async def process_data(
    request,
    userid,
    pan_data,
    IPOid,
    OrderType,
    Groupfilter,
    IPOTypefilter,
    InvestorTypefilter,
    page_number,
):
    tasks = []
    Order_idlist = []
    for row_id, data in pan_data.items():
        PAN = data["PAN"]
        if PAN == "":
            continue
        clientname = data["ClientName"]
        if data["AllotedQty"] != "":
            allotedqty = float(data["AllotedQty"])
        else:
            allotedqty = None
        DematNo = data["DematNumber"]
        Application = data["ApplicationNumber"]
        rate = data["Rate"]
        if data["PAN_id"] != "":
            PAN_id = int(data["PAN_id"])
        else:
            PAN_id = None
        if data["Pan_Qty"] != "":
            Pan_Qty = float(data["Pan_Qty"])
        else:
            Pan_Qty = None
        Pan_Demat = data["Pan_Demat"]
        Pan_App = data["Pan_App"]
        Pan_Client = data["Pan_Client"]
        if PAN != "":
            # employee_task = asyncio.to_thread(OrderDetail.objects.get, user=userid, id=row_id)
            # employee = await employee_task
            if PAN_id is not None:
                try:
                    query_task_id = asyncio.to_thread(
                        ClientDetail.objects.get, PANNo=PAN.upper(), user=userid
                    )
                    query_id = await query_task_id
                    cq_id = query_id.id
                except:
                    cq_id = None
            else:
                cq_id = None

            if (
                (PAN_id != cq_id or cq_id is None)
                or allotedqty != Pan_Qty
                or DematNo != Pan_Demat
                or Application != Pan_App
                or clientname != Pan_Client
            ):
                if PAN and isValidPAN(PAN):
                    task = handle_single_row(
                        userid,
                        PAN,
                        clientname,
                        allotedqty,
                        DematNo,
                        Application,
                        rate,
                        request,
                        row_id,
                        IPOid,
                        OrderType,
                        Groupfilter,
                        IPOTypefilter,
                        InvestorTypefilter,
                        page_number,
                        Order_idlist,
                    )
                    tasks.append(task)

    # All_time = datetime.now()

    if tasks:
        await asyncio.gather(*tasks)
        All_time = datetime.now()
        await panupload_calculate(IPOid, request.user, Order_idlist)

    # for O_id in Order_idlist:
    #     await sync_to_async(calculate)(IPOid, request.user, O_id)


def Update_pann(
    request, IPOid, OrderType, GrpName=None, OrderCategory=None, InvestorType=None
):
    userid = request.user
    pan_data = {}
    page_number = request.GET.get("page", "1")
    Groupfilter = unquote(GrpName)
    IPOTypefilter = unquote(OrderCategory)
    InvestorTypefilter = unquote(InvestorType)
    for key, value in request.POST.items():
        if key == "csrfmiddlewaretoken":
            continue

        if key.startswith("PAN_"):
            text_split = key.split("_")
            row_id = text_split[1]
            Rate = text_split[2]
            Pan_id = text_split[3]
            Pan_Qty = text_split[4]
            Pan_Demat = text_split[5]
            Pan_App = text_split[6]
            Pan_Client = text_split[7]
            if row_id:
                pan_data[row_id] = {
                    "PAN": value.upper(),
                    "Rate": Rate,
                    "PAN_id": Pan_id,
                    "Pan_Qty": Pan_Qty,
                    "Pan_Demat": Pan_Demat,
                    "Pan_App": Pan_App,
                    "Pan_Client": Pan_Client,
                }

        if key.startswith("allotedqty_"):
            row_id = key.split("_")[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}

            pan_data[row_id]["AllotedQty"] = value if value else ""

        if key.startswith("DematNo_"):
            row_id = key.split("_")[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}

            pan_data[row_id]["DematNumber"] = value if value else ""

        if key.startswith("clientname_"):
            row_id = key.split("_")[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}

            pan_data[row_id]["ClientName"] = value if value else ""

        if key.startswith("Application_"):
            row_id = key.split("_")[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}

            pan_data[row_id]["ApplicationNumber"] = value if value else ""

    # if tasks:
    # sync_to_async(await asyncio.gather(*tasks))
    # now_time = datetime.now()
    asyncio.run(
        process_data(
            request,
            userid,
            pan_data,
            IPOid,
            OrderType,
            Groupfilter,
            IPOTypefilter,
            InvestorTypefilter,
            page_number,
        )
    )

    # tasks = []
    # for row_id, data in pan_data.items():
    #     PAN  =  data['PAN']
    #     clientname  =  data['ClientName']
    #     allotedqty  =  data['AllotedQty']
    #     DematNo  =  data['DematNumber']
    #     Application  =  data['ApplicationNumber']
    #     rate  =  data['Rate']

    #     if PAN != '':
    #         if isValidPAN(PAN):
    #             task = handle_single_row(userid, PAN, clientname, allotedqty, DematNo,Application,rate, request,row_id,IPOid,OrderType,Groupfilter,IPOTypefilter,InvestorTypefilter,page_number)
    #             tasks.append(task)

    #         # else:
    #         #     Od_e.append(row_id)
    #             # messages.error(request, f"Row ['{Od_e.Order.OrderGroup}','{Od_e.Order.OrderCategory}','{Od_e.Order.InvestorType}','{rate}','{PAN}','{clientname}','{allotedqty}','{DematNo}','{Application}', 'Invalid PAN'] has Invalid PAN No.")
    # if tasks:
    # #     # asyncio.gather(*tasks)
    #     try:
    #         loop = asyncio.get_event_loop()
    #     except RuntimeError:
    #         loop = asyncio.new_event_loop()
    #         asyncio.set_event_loop(loop)
    #     try:
    #         loop.run_until_complete(asyncio.gather(*tasks))
    #     except RuntimeError as e:
    #         if str(e) == "Event loop is closed":
    #             loop = asyncio.new_event_loop()
    #             asyncio.set_event_loop(loop)
    #             loop.run_until_complete(asyncio.gather(*tasks))

    #     finally:
    #         pending = asyncio.all_tasks(loop)
    #         for task in pending:
    #             task.cancel()
    #         loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    #         loop.close()

    # async def run_tasks():
    #     await asyncio.gather(*tasks)

    # asyncio.run(run_tasks())

    # loop.run_until_complete(asyncio.gather(*tasks))

    return redirect(
        f"/{IPOid}/OrderDetail/{OrderType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypefilter}?page={page_number}"
    )


# app-buy and sell order details add pan or update fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def AddPan(
    request,
    OrderDetailId,
    IPOid,
    OrderType,
    GrpName=None,
    OrderCategory=None,
    InvestorType=None,
    OrderDate=None,
    OrderTime=None,
):
    if request.user.groups.all()[0].name == "Broker":
        userid = request.user
    else:
        userid = request.user.Broker_id
    employee = OrderDetail.objects.get(user=userid, id=OrderDetailId)

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    PAN = request.POST.get("PAN", "").upper()
    clientname = request.POST.get("clientname", "")
    allotedqty = request.POST.get("allotedqty", "")
    Application = request.POST.get("Application", "")
    DematNo = request.POST.get("DematNo", "")
    Groupfilter = request.POST.get("Groupfilter", "")
    IPOTypefilter = request.POST.get("IPOTypefilter", "")
    InvestorTypeFilter = request.POST.get("InvestorTypeFilter", "")
    if request.method == "POST":
        rate = "{:.0f}".format(employee.Order.Rate)

        if PAN == "":
            employee.OrderDetailPANNo_id = None
            employee.AllotedQty = None
            employee.DematNumber = ""
            employee.ApplicationNumber = ""
            employee.save()
            return redirect(
                f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}"
            )

        elif not isValidPAN(PAN):
            messages.error(
                request,
                f"Row ['{employee.Order.OrderGroup}','{employee.Order.OrderCategory}','{employee.Order.InvestorType}','{rate}','{PAN}','{clientname}','{allotedqty}','{DematNo}','{Application}', 'Invalid PAN'] has Invalid PAN No.",
            )
            return redirect(
                f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}"
            )

        elif PAN != "":
            query = ClientDetail.objects.filter(PANNo=PAN.upper(), user=userid)
            if query.exists():
                query1 = ClientDetail.objects.get(PANNo=PAN.upper(), user=userid)
                if employee.Order.OrderGroup == query1.Group:
                    pass
                else:
                    query1.Group = employee.Order.OrderGroup
                query1.Name = clientname
                query1.save()
            else:
                PANNUMBER = ClientDetail(
                    user=userid,
                    PANNo=PAN.upper(),
                    Name=clientname,
                    Group=employee.Order.OrderGroup,
                )
                PANNUMBER.save()
            r = 1
            query2 = ClientDetail.objects.get(PANNo=PAN.upper(), user=userid)
            for j in OrderDetail.objects.filter(
                user=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType
            ).values("OrderDetailPANNo__PANNo"):
                if PAN.upper() == j.get("OrderDetailPANNo__PANNo"):
                    if employee.OrderDetailPANNo_id != query2.id:
                        messages.error(
                            request,
                            f"Row ['{employee.Order.OrderGroup}','{employee.Order.OrderCategory}','{employee.Order.InvestorType}','{rate}','{PAN}','{clientname}','{allotedqty}','{DematNo}','{Application}', 'Pan_exist_already'] has PAN no. that already exists.",
                        )

                        r = 0
                        break

            if r == 1:
                panno = ClientDetail.objects.get(PANNo=PAN.upper(), user=userid)
                employee.OrderDetailPANNo_id = panno.id
                if allotedqty == "":
                    employee.AllotedQty = None
                else:
                    employee.AllotedQty = allotedqty
                employee.DematNumber = DematNo
                employee.ApplicationNumber = Application
                employee.save()
                calculate(IPOid, request.user, employee.Order_id)

        else:
            pass
    return redirect(
        f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}"
    )


@allowed_users(allowed_roles=["Broker", "Customer"])
def FirmAllotment(request, IPOid, OrderType, GrpName, OrderCategory, InvestorType):
    if request.user.groups.all()[0].name == "Broker":
        userid = request.user
    else:
        userid = request.user.Broker_id
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    if request.method == "POST":
        AllotedQtyv = request.POST.get("AllotedQty", "")
        Group = request.POST.get("Group", "")
        if IPOName.IPOType == "MAINBOARD":
            InvestorTypeFilter = request.POST.get("InvestorType", "")
        else:
            InvestorTypeFilter = "All"

        if AllotedQtyv != "":

            if Group == "All" and InvestorTypeFilter == "All":
                j = OrderDetail.objects.filter(
                    user=userid,
                    Order__OrderIPOName_id=IPOid,
                    Order__OrderType=OrderType,
                )

            elif Group == "All":
                j = OrderDetail.objects.filter(
                    user=userid,
                    Order__OrderIPOName_id=IPOid,
                    Order__OrderType=OrderType,
                    Order__InvestorType=InvestorTypeFilter,
                )

            elif InvestorTypeFilter == "All":
                gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
                j = OrderDetail.objects.filter(
                    user=userid,
                    Order__OrderIPOName_id=IPOid,
                    Order__OrderType=OrderType,
                    Order__OrderGroup_id=gid,
                )

            else:
                gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
                j = OrderDetail.objects.filter(
                    user=userid,
                    Order__OrderIPOName_id=IPOid,
                    Order__OrderType=OrderType,
                    Order__OrderGroup_id=gid,
                    Order__InvestorType=InvestorTypeFilter,
                )

            j.update(AllotedQty=AllotedQtyv)

            calculate(IPOid, request.user)

    if GrpName == "None" and OrderCategory == "None" and InvestorType == "None":
        return redirect(f"/{IPOid}/OrderDetail/{OrderType}")
    return redirect(
        f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}"
    )


# client wise billing fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def Billing(request, IPOid):
    if request.user.groups.all()[0].name == "Broker":
        userid = request.user
        entry = OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid)
        Group = GroupDetail.objects.filter(user=userid)
    else:
        userid = request.user.Broker_id
        entry = OrderDetail.objects.filter(
            user=userid,
            Order__OrderIPOName_id=IPOid,
            Order__OrderGroup_id=request.user.Group_id,
        )
        Group = GroupDetail.objects.filter(user=userid, id=request.user.Group_id)
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)
    total = 0

    IPO_Name = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IpoName = IPO_Name.IPOName

    # orderpreopen = OrderDetail.objects.filter(Order__OrderIPOName_id=IPOid, user=request.user, PreOpenPrice=0)
    # orderpreopen.update(PreOpenPrice = IPO_Name.PreOpenPrice)

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)

    order = Order.objects.filter(user=userid, OrderIPOName_id=IPOid).filter(
        Q(OrderCategory="Premium") | Q(OrderCategory="CALL") | Q(OrderCategory="PUT")
    )

    Total1 = order.aggregate(Sum("Amount"))
    Total = Total1["Amount__sum"]
    if Total is None:
        Total = 0
    else:
        Total = Total
    totalorder = total + Total
    Total1 = entry.aggregate(Sum("Amount"))
    Total = Total1["Amount__sum"]
    if Total is None:
        Total = 0
    total = total + Total
    total = total + totalorder

    IPOTypefilterList = {
        "Kostak",
        "Subject To",
        "CALL",
        "PUT",
        "Premium",
    }
    InvestorTypeFilterList = {"RETAIL", "SHNI", "BHNI", "OPTIONS", "PREMIUM"}
    Groupfilter = "All"
    IPOTypefilter = "All"
    InvestorTypeFilter = "All"

    if request.method == "POST":
        Groupfilter = request.POST.get("Groupfilter", "")
        IPOTypefilter = request.POST.get("IPOTypefilter", "")
        InvestorTypeFilter = request.POST.get("InvestorTypeFilter", "")

        if Groupfilter == "" and IPOTypefilter == "" and InvestorTypeFilter == "":
            Groupfilter = "All"
            IPOTypefilter = "All"
            InvestorTypeFilter = "All"

        total = 0
        if is_valid_queryparam(Groupfilter) and Groupfilter != "All":
            gid = GroupDetail.objects.get(GroupName=Groupfilter, user=userid).id
            entry = entry.filter(Order__OrderGroup_id=gid)
            order = order.filter(OrderGroup_id=gid)
        if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != "All":
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
            order = order.filter(OrderCategory=IPOTypefilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != "All":
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
            order = order.filter(InvestorType=InvestorTypeFilter)
        Total1 = order.aggregate(Sum("Amount"))
        Total = Total1["Amount__sum"]
        if Total is None:
            Total = 0
        else:
            Total = Total
        totalorder = total + Total
        Total1 = entry.aggregate(Sum("Amount"))
        Total = Total1["Amount__sum"]
        if Total is None:
            Total = 0
        total = total + Total
        total = total + totalorder

    page_obj = None
    try:
        page_size = request.POST.get("Billing_page_size")
        if page_size != "" and page_size is not None:
            request.session["Billing_page_size"] = page_size
        else:
            page_size = request.session["Billing_page_size"]
    except:
        page_size = request.session.get("Billing_page_size", 50)

    Data = []

    entry_count = entry.count() if entry else 0
    order_count = order.count() if order else 0
    total_count = entry_count + order_count

    # page_size = page_size if page_size != 'All' else total_count
    display_page_size = page_size if page_size != "All" else total_count
    paginator = Paginator(range(total_count), display_page_size)

    # Get current page number and calculate start/end indices
    page_number = request.GET.get("page", "1")
    page_obj = paginator.get_page(page_number)
    start_index = page_obj.start_index() - 1
    end_index = page_obj.end_index()

    entry_toatal_amount = 0

    if start_index < entry_count:
        if entry_count != 0:
            entry_end = min(end_index, entry_count)
            entry_page_data = entry[start_index:entry_end]

            for order_detail in entry_page_data:
                entry_toatal_amount = entry_toatal_amount + order_detail.Amount
                entry_data = {
                    "id": order_detail.id,
                    "OrderGroup": order_detail.Order.OrderGroup,
                    "OrderCategory": order_detail.Order.OrderCategory,
                    "InvestorType": order_detail.Order.InvestorType,
                    "OrderType": order_detail.Order.OrderType,
                    "Rate": order_detail.Order.Rate,
                    "Method": order_detail.Order.Method,
                    "PANNo": (
                        order_detail.OrderDetailPANNo.PANNo
                        if (
                            order_detail.OrderDetailPANNo
                            and order_detail.OrderDetailPANNo.PANNo is not None
                        )
                        else ""
                    ),
                    "PreOpenPrice": order_detail.PreOpenPrice,
                    "AllotedQty": (
                        float(order_detail.AllotedQty)
                        if (order_detail.AllotedQty is not None)
                        else ""
                    ),
                    "Amount": order_detail.Amount,
                    # Add other fields as needed
                }
                Data.append(entry_data)

    if end_index > entry_count:
        if order_count != 0:
            order_start = max(0, start_index - order_count)
            order_end = end_index - entry_count
            order_page_data = order[order_start:order_end]

            for order_detail in order_page_data:
                entry_toatal_amount = entry_toatal_amount + order_detail.Amount
                order_data = {
                    "id": order_detail.id,
                    "OrderGroup": order_detail.OrderGroup,
                    "OrderCategory": order_detail.OrderCategory,
                    "InvestorType": order_detail.InvestorType,
                    "OrderType": order_detail.OrderType,
                    "Rate": order_detail.Rate,
                    "Method": order_detail.Method,
                    "PANNo": "-",
                    "PreOpenPrice": IPO.PreOpenPrice,
                    "AllotedQty": float(order_detail.Quantity),
                    "Amount": order_detail.Amount,
                }
                Data.append(order_data)

    # if Data:
    # if entry is not None and entry.exists():
    df = pd.DataFrame.from_records(Data)
    if "InvestorType" in df.columns:
        df = df.sort_values(
            by="InvestorType", key=lambda x: x == "PREMIUM"
        ).reset_index(drop=True)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th>Group</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th>PAN No</th>"
    html_table += "<th>PreOpen Price</th>"
    html_table += "<th>Alloted Qty</th>"
    html_table += "<th>Amount</th>"
    html_table += "</tr></thead>\n"
    # Add rows
    float_format = "{:.1f}"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        if row.OrderCategory != "Premium":
            method = row.Method if row.Method else "Application"
            html_table += f"<td>{method}</td>"
        else:
            html_table += f"<td>-</td>"
        if not pd.isna(row.id):
            row_id = int(row.id)
        else:
            row_id = None

        if IPOName.IPOType == "MAINBOARD":
            action_url = f"/{IPOid}/{row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}?page={page_number}"
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        else:
            action_url = f"/{IPOid}/{ row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All?page={page_number}"

        html_table += f"<td>{row.OrderType}</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td>{row.PANNo}</td>"
        pre_open_price = (
            row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
        )
        if row.OrderCategory != "Premium" and row.InvestorType != "OPTIONS":
            html_table += f"<td><a href='#' style='color: #007bff;' data-id='{row.id}' data-preopen-price='{pre_open_price}' data-action-url='{action_url}' data-toggle='modal' data-target='#edit-modal'> {pre_open_price} </a></td>"
        else:
            html_table += f"<td>{pre_open_price}</td>"

        html_table += f"<td>{row.AllotedQty}</td>"
        html_table += f"<td>{float_format.format(row.Amount)}</td>"
        html_table += "</tr>\n"

    html_table += "</tbody>"
    html_table += "<tfoot><tr>"
    html_table += "<th>Total</th>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += f"<th style='text-align: center;'>{float_format.format(entry_toatal_amount)}</th>"
    html_table += "</tr></tfoot>"
    html_table += "</table>"

    # if entry is not None and entry.exists():
    #     for i, row in df.iterrows():
    #         pre_open_price = row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
    #         csrf_token = csrf.get_token(request)

    #         if not pd.isna(row.id):
    #             row_id = int(row.id)
    #         else:
    #             row_id = None
    #         if IPOName.IPOType == "MAINBOARD":
    #             action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}'
    #         else:
    #             action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All'

    #         html_table += f"""
    #             <div class="modal fade" id="edit-{ row.id }" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabels"
    #                 aria-hidden="true">
    #                 <div class="modal-dialog" role="document">
    #                     <div class="modal-content">
    #                         <div class="modal-header" style="border-bottom: 1px solid black;">
    #                             <h5 class="modal-title" id="exampleModalLabels">PreOpen Price Edit</h5>
    #                             <button type="button" class="close" data-dismiss="modal" aria-label="Close">
    #                                 <span aria-hidden="true">&times;</span>
    #                             </button>
    #                         </div>
    #                         <div class="modal-body" style="border-bottom: 1px solid black;">
    #                             <form action="{action_url}"  method="POST"
    #                                 enctype="multipart/form-data" style="margin: 15px 22px;" class="need-validation"
    #                                 novalidate>

    #                                 <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    #                                 <label for="category"><b>PreOpenPrice : </b></label>
    #                                 <input type="text" value="{pre_open_price}" name="PreOpenPrice"
    #                                     oninput="this.value = this.value.replace(/[^0-9.]/g, '').replace(/(\..?)\../g, '$1');" / style="height: 37px;">
    #                                 <button type="submit" class="btn btn-outline-primary">Submit</button>
    #                             </form>
    #                         </div>
    #                     </div>
    #                 </div>
    #             </div>
    #         """

    return render(
        request,
        "Billing.html",
        {
            "Group": Group.order_by("GroupName"),
            "html_table": html_table,
            "select": IPOTypefilterList,
            "select2": InvestorTypeFilterList,
            "total": "{:.2f}".format(total),
            "Groupfilter": Groupfilter,
            "IPOName": IPO,
            "IPOTypefilter": IPOTypefilter,
            "InvestorTypeFilter": InvestorTypeFilter,
            "IPO": IPO,
            "IPOid": IPOid,
            "page_obj": page_obj,
            "Billing_page_size": page_size,
        },
    )
    return render(
        request,
        "Billing.html",
        {
            "Group": Group.order_by("GroupName"),
            "select": IPOTypefilterList,
            "select2": InvestorTypeFilterList,
            "total": "{:.2f}".format(total),
            "Groupfilter": Groupfilter,
            "IPOName": IPO,
            "IPOTypefilter": IPOTypefilter,
            "InvestorTypeFilter": InvestorTypeFilter,
            "IPO": IPO,
            "IPOid": IPOid,
            "page_obj": page_obj,
            "Billing_page_size": page_size,
        },
    )


def FileterBilling(request, IPOid, group, IPOType, InvestType):
    if request.user.groups.all()[0].name == "Broker":
        userid = request.user
        entry = OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid)
        Group = GroupDetail.objects.filter(user=userid)
    else:
        userid = request.user.Broker_id
        entry = OrderDetail.objects.filter(
            user=userid,
            Order__OrderIPOName_id=IPOid,
            Order__OrderGroup_id=request.user.Group_id,
        )
        Group = GroupDetail.objects.filter(user=userid, id=request.user.Group_id)
    Groupfilter = unquote(group)
    IPOTypefilter = unquote(IPOType)
    InvestorTypeFilter = unquote(InvestType)

    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)
    total = 0

    IPO_Name = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IpoName = IPO_Name.IPOName

    orderpreopen = OrderDetail.objects.filter(
        Order__OrderIPOName_id=IPOid, user=request.user, PreOpenPrice=0
    )
    orderpreopen.update(PreOpenPrice=IPO_Name.PreOpenPrice)

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)

    # order = Order.objects.filter(
    #     user=userid, OrderIPOName_id=IPOid, OrderCategory="Premium")

    order = Order.objects.filter(user=userid, OrderIPOName_id=IPOid).filter(
        Q(OrderCategory="Premium") | Q(OrderCategory="CALL") | Q(OrderCategory="PUT")
    )

    IPOTypefilterList = {"Kostak", "Subject To", "CALL", "PUT", "Premium"}
    InvestorTypeFilterList = {"RETAIL", "SHNI", "BHNI", "OPTIONS", "PREMIUM"}

    total = 0
    if is_valid_queryparam(Groupfilter) and Groupfilter != "All":
        gid = GroupDetail.objects.get(GroupName=Groupfilter, user=userid).id
        entry = entry.filter(Order__OrderGroup_id=gid)
        order = order.filter(OrderGroup_id=gid)
    if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != "All":
        entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        order = order.filter(OrderCategory=IPOTypefilter)
    if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != "All":
        entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        order = order.filter(InvestorType=InvestorTypeFilter)
    Total1 = order.aggregate(Sum("Amount"))
    Total = Total1["Amount__sum"]
    if Total is None:
        Total = 0
    else:
        Total = Total
    totalorder = total + Total
    Total1 = entry.aggregate(Sum("Amount"))
    Total = Total1["Amount__sum"]
    if Total is None:
        Total = 0
    total = total + Total
    total = total + totalorder

    page_obj = None
    try:
        page_size = request.POST.get("Billing_page_size")
        if page_size != "" and page_size is not None:
            request.session["Billing_page_size"] = page_size
        else:
            page_size = request.session["Billing_page_size"]
    except:
        page_size = request.session.get("Billing_page_size", 50)

    Data = []

    entry_toatal_amount = 0

    entry_count = entry.count() if entry else 0
    order_count = order.count() if order else 0
    total_count = entry_count + order_count

    # page_size = page_size if page_size != 'All' else total_count
    display_page_size = page_size if page_size != "All" else total_count
    paginator = Paginator(range(total_count), display_page_size)

    # Get current page number and calculate start/end indices
    page_number = request.GET.get("page", "1")
    page_obj = paginator.get_page(page_number)
    start_index = page_obj.start_index() - 1
    end_index = page_obj.end_index()
    if start_index < entry_count:
        if entry_count != 0:
            entry_end = min(end_index, entry_count)
            entry_page_data = entry[start_index:entry_end]

        for order_detail in entry_page_data:
            entry_toatal_amount = entry_toatal_amount + order_detail.Amount
            entry_data = {
                "id": order_detail.id,
                "OrderGroup": order_detail.Order.OrderGroup,
                "OrderCategory": order_detail.Order.OrderCategory,
                "InvestorType": order_detail.Order.InvestorType,
                "OrderType": order_detail.Order.OrderType,
                "Rate": order_detail.Order.Rate,
                "Method": order_detail.Order.Method,
                "PANNo": (
                    order_detail.OrderDetailPANNo.PANNo
                    if (
                        order_detail.OrderDetailPANNo
                        and order_detail.OrderDetailPANNo.PANNo is not None
                    )
                    else ""
                ),
                "PreOpenPrice": order_detail.PreOpenPrice,
                "AllotedQty": (
                    float(order_detail.AllotedQty)
                    if (order_detail.AllotedQty is not None)
                    else ""
                ),
                "Amount": order_detail.Amount,
            }
            Data.append(entry_data)
    if end_index > entry_count:
        if order_count != 0:
            order_start = max(0, start_index - entry_count)
            order_end = end_index - entry_count
            order_page_data = order[order_start:order_end]

            for order_detail in order_page_data:
                entry_toatal_amount = entry_toatal_amount + order_detail.Amount
                order_data = {
                    "id": order_detail.id,
                    "OrderGroup": order_detail.OrderGroup,
                    "OrderCategory": order_detail.OrderCategory,
                    "InvestorType": order_detail.InvestorType,
                    "OrderType": order_detail.OrderType,
                    "Rate": order_detail.Rate,
                    "Method": order_detail.Method,
                    "PANNo": "-",
                    "PreOpenPrice": IPO.PreOpenPrice,
                    "AllotedQty": float(order_detail.Quantity),
                    "Amount": order_detail.Amount,
                }
                Data.append(order_data)

    df = pd.DataFrame.from_records(Data)
    if "InvestorType" in df.columns:
        df = df.sort_values(
            by="InvestorType", key=lambda x: x == "PREMIUM"
        ).reset_index(drop=True)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th>Group</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th>PAN No</th>"
    html_table += "<th>PreOpen Price</th>"
    html_table += "<th>Alloted Qty</th>"
    html_table += "<th>Amount</th>"
    html_table += "</tr></thead>\n"
    # Add rows
    float_format = "{:.1f}"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        if row.OrderCategory != "Premium":
            method = row.Method if row.Method else "Application"
            html_table += f"<td>{method}</td>"
        else:
            html_table += f"<td>-</td>"
        if not pd.isna(row.id):
            row_id = int(row.id)
        else:
            row_id = None

        if IPOName.IPOType == "MAINBOARD":
            action_url = f"/{IPOid}/{row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}?page={page_number}"
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        else:
            action_url = f"/{IPOid}/{ row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All?page={page_number}"

        html_table += f"<td>{row.OrderType}</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td>{row.PANNo}</td>"
        pre_open_price = (
            row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
        )
        if row.OrderCategory != "Premium" and row.InvestorType != "OPTIONS":
            html_table += f"<td><a href='#' style='color: #007bff;' data-id='{row.id}' data-preopen-price='{pre_open_price}' data-action-url='{action_url}' data-toggle='modal' data-target='#edit-modal'> {pre_open_price} </a></td>"
        else:
            html_table += f"<td>{pre_open_price}</td>"

        html_table += f"<td>{row.AllotedQty}</td>"
        html_table += f"<td>{float_format.format(row.Amount)}</td>"
        html_table += "</tr>\n"

    html_table += "</tbody>"
    html_table += "<tfoot><tr>"
    html_table += "<th>Total</th>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += f"<th style='text-align: center;'>{float_format.format(entry_toatal_amount)}</th>"
    html_table += "</tr></tfoot>"
    html_table += "</table>"

    # for i, row in df.iterrows():
    #     pre_open_price = row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
    #     csrf_token = csrf.get_token(request)

    #     if not pd.isna(row.id):
    #         row_id = int(row.id)
    #     else:
    #         row_id = None

    #     if IPOName.IPOType == "MAINBOARD":
    #         action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}'
    #     else:
    #         action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All'

    #     html_table += f"""
    #         <div class="modal fade" id="edit-{ row.id }" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabels"
    #             aria-hidden="true">
    #             <div class="modal-dialog" role="document">
    #                 <div class="modal-content">
    #                     <div class="modal-header" style="border-bottom: 1px solid black;">
    #                         <h5 class="modal-title" id="exampleModalLabels">PreOpen Price Edit</h5>
    #                         <button type="button" class="close" data-dismiss="modal" aria-label="Close">
    #                             <span aria-hidden="true">&times;</span>
    #                         </button>
    #                     </div>
    #                     <div class="modal-body" style="border-bottom: 1px solid black;">
    #                         <form action="{action_url}" id="form-id2" method="POST"
    #                             enctype="multipart/form-data" style="margin: 15px 22px;" class="need-validation"
    #                             novalidate>

    #                             <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    #                             <label for="category"><b>PreOpenPrice : </b></label>
    #                             <input type="text" value="{pre_open_price}" name="PreOpenPrice"
    #                                 oninput="this.value = this.value.replace(/[^0-9.]/g, '').replace(/(\..?)\../g, '$1');" / style="height: 37px;">
    #                             <button type="submit" class="btn btn-outline-primary">Submit</button>
    #                         </form>
    #                     </div>
    #                 </div>
    #             </div>
    #         </div>
    #     """

    return render(
        request,
        "Billing.html",
        {
            "Group": Group,
            "html_table": html_table,
            "select": IPOTypefilterList,
            "select2": InvestorTypeFilterList,
            "total": "{:.2f}".format(total),
            "Groupfilter": Groupfilter,
            "IPOName": IPO,
            "IPOTypefilter": IPOTypefilter,
            "InvestorTypeFilter": InvestorTypeFilter,
            "IPO": IPO,
            "IPOid": IPOid,
            "page_obj": page_obj,
            "Billing_page_size": page_size,
        },
    )
    # return render(request, 'Billing.html', {'entry': entry, 'order': order, 'Group': Group.order_by('GroupName'), 'select': IPOTypefilterList, 'select2': InvestorTypeFilterList, "total": "{:.2f}".format(total), 'Groupfilter': Groupfilter, "IPOName": IPO, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter': InvestorTypeFilter,  "IPO": IPO, "IPOid": IPOid})


# client wise biling filter wise download fun
@allowed_users(allowed_roles=["Broker"])
def exportBillingFilter(request, IPOid, group=None, IPOType=None, InvestorType=None):
    group = unquote(group)
    IPOType = unquote(IPOType)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    response = HttpResponse(content_type="text/csv")
    entry = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName=IPOName)
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid, OrderCategory="Premium"
    )

    writer = csv.writer(response)
    if IPOName.IPOType == "MAINBOARD":
        writer.writerow(
            [
                "Group",
                "Order Category",
                "Investor Type",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount Difference",
                "PAN No",
                "Client Name",
            ]
        )
    else:
        writer.writerow(
            [
                "Group",
                "Order Category",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount Difference",
                "PAN No",
                "Client Name",
            ]
        )

    if group != "None" and group != "All":
        gid = GroupDetail.objects.get(GroupName=group, user=request.user).id
        entry = entry.filter(Order__OrderGroup_id=gid)
        order = order.filter(OrderGroup_id=gid)
    if IPOType != "None" and IPOType != "All":
        entry = entry.filter(Order__OrderCategory=IPOType)
        order = order.filter(OrderCategory=IPOType)

    if IPOName.IPOType == "MAINBOARD":
        if InvestorType != "None" and InvestorType != "All":
            entry = entry.filter(Order__InvestorType=InvestorType)
            order = order.filter(InvestorType=InvestorType)
        for member in entry.filter().values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__InvestorType",
            "Order__OrderType",
            "Order__Rate",
            "AllotedQty",
            "PreOpenPrice",
            "Amount",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
        ):
            writer.writerow(member)
        for member in order.filter().values_list(
            "OrderGroup__GroupName",
            "OrderCategory",
            "InvestorType",
            "OrderType",
            "Rate",
            "Quantity",
            "OrderIPOName__PreOpenPrice",
            "Amount",
        ):
            writer.writerow(member)
    else:
        for member in entry.filter().values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__OrderType",
            "Order__Rate",
            "AllotedQty",
            "PreOpenPrice",
            "Amount",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
        ):
            writer.writerow(member)
        for member in order.filter().values_list(
            "OrderGroup__GroupName",
            "OrderCategory",
            "OrderType",
            "Rate",
            "Quantity",
            "OrderIPOName__PreOpenPrice",
            "Amount",
        ):
            writer.writerow(member)

    response["Content-Disposition"] = f'attachment; filename="{IPOName}-Billing.csv"'

    return response


# Group Wise Dashboard  billing download PDF fun
def exportGroupwise(request):

    Group = GroupDetail.objects.filter(user=request.user)
    IPO = CurrentIpoName.objects.filter(user=request.user)
    response = HttpResponse(content_type="text/csv")

    grpname = []
    Collectionlist = []
    IPOName = []
    IPOAmount = []
    nlist = []
    Total = 0
    l = []
    for IpoName in IPO:
        entry = Order.objects.filter(user=request.user, OrderIPOName=IpoName)
        total = 0
        for i in entry:
            total = total + i.Amount
        Total = Total + total
        if total != 0:
            IPOAmount.append(total)
            IPOName.append(IpoName)

    lenofipo = len(IPOName)
    for j in range(0, lenofipo):
        l.append(j)
    SumCollection = 0
    for GroupName in Group:
        SumCollection = SumCollection + GroupName.Collection
        grpname.append(GroupName)
        Collectionlist.append(GroupName.Collection)
    lenofgroup = len(grpname)

    for GroupName in Group:
        IPOTotal = []
        for IpoName in IPOName:

            total = 0
            DueAmount = 0
            entry = Order.objects.filter(
                user=request.user, OrderGroup=GroupName, OrderIPOName=IpoName
            )
            for i in entry:

                total = total + i.Amount
            IPOTotal.append(total)
        nlist.append(IPOTotal)

    DueAmountSum = float(Total) - float(SumCollection)
    df = pd.DataFrame(nlist, columns=IPOName, index=grpname)
    df["Total"] = df[IPOName].sum(axis=1)
    df["Collection"] = Collectionlist
    df["Due Amount"] = df["Total"] - df["Collection"]

    grpdict = dict(zip(IPOName, IPOAmount))
    grpdict.update(
        {"Total": Total, "Collection": SumCollection, "Due Amount": float(DueAmountSum)}
    )
    df.loc["Total"] = grpdict

    Groupwise = BytesIO()
    with pd.ExcelWriter(Groupwise, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1")

    response["Content-Disposition"] = f'attachment; filename="GroupWiseDashboard.xlsx"'
    Groupwise.seek(0)
    response.write(Groupwise.read())
    return response


def exportAccountingFilter(
    request, IPOid=None, group=None, date_from=None, date_to=None, jv=None
):
    # Decode URL params
    group = unquote(group) if group else None
    IPOid = int(IPOid) if IPOid and IPOid.isdigit() else None

    # Base queryset
    entries = Accounting.objects.filter(user=request.user).select_related(
        "group", "ipo"
    )

    # Apply filters
    if IPOid:
        entries = entries.filter(ipo_id=IPOid)

    if group and group not in ["None", "All"]:
        try:
            gid = GroupDetail.objects.get(GroupName=group, user=request.user).id
            entries = entries.filter(group_id=gid)
        except GroupDetail.DoesNotExist:
            pass

    if date_from and date_from != "None":
        entries = entries.filter(date__gte=date_from)

    if date_to and date_to != "None":
        entries = entries.filter(date__lte=date_to)

    if jv and jv not in ["None", "All"]:
        entries = entries.filter(jv=(jv.lower() == "true"))

    # Prepare CSV response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="Accounting.csv"'
    writer = csv.writer(response)

    # Header row
    writer.writerow(["Date", "Group", "IPO", "Amount", "JV", "Remarks"])

    # Data rows
    for e in entries:
        writer.writerow(
            [
                e.date.strftime("%Y-%m-%d") if e.date else "",
                e.group.GroupName if e.group else "",
                e.ipo.IPOName if e.ipo else "",
                e.amount,
                "Yes" if e.jv else "No",
                e.remarks if hasattr(e, "remarks") else "",
            ]
        )

    return response


def exportAccountiong(request):
    # Fetch all accounting entries with related data
    entries = Accounting.objects.filter(user=request.user).select_related(
        "group", "ipo", "user"
    )

    # Apply filters from request
    group_id = request.GET.get("group_id")
    ipo_id = request.GET.get("ipo_id")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    jv_filter = request.GET.get("jv")

    if group_id:
        entries = entries.filter(group_id=group_id)
    if ipo_id:
        entries = entries.filter(ipo_id=ipo_id)
    if date_from:
        date_from_obj = datetime.fromisoformat(date_from).date()
        entries = entries.filter(date_time__date__gte=date_from_obj)
    if date_to:
        date_to_obj = datetime.fromisoformat(date_to).date()
        entries = entries.filter(date_time__date__lte=date_to_obj)
    if jv_filter == "1":
        entries = entries.filter(jv=True)
    elif jv_filter == "0":
        entries = entries.filter(jv=False)

    # Prepare data for dataframe
    data = []
    for e in entries:
        # Get IPO name with fallback
        ipo_display = e.ipo.IPOName if e.ipo else (e.ipo_name or "")

        # Get group name with fallback
        group_name = e.group.GroupName if e.group else (e.group_name or "")

        data.append(
            {
                "Date": (
                    timezone.localtime(e.date_time).strftime("%d-%m-%Y")
                    if e.date_time
                    else ""
                ),
                "Time": (
                    timezone.localtime(e.date_time).strftime("%H:%M:%S")
                    if e.date_time
                    else ""
                ),
                "IPO": ipo_display,
                "Group": group_name,
                "Type": e.amount_type.upper(),
                "Amount": float(e.amount) if e.amount else 0.0,
                "JV": "Yes" if e.jv else "No",
                "Remarks": e.remark or "",
                "User": e.user.username if e.user else "System",
            }
        )

    # Create dataframe
    df = pd.DataFrame(data)

    # Reorder columns for better readability
    columns_order = [
        "Date",
        "Time",
        "Group",
        "IPO",
        "Type",
        "Amount",
        "JV",
        "Remarks",
        "User",
    ]
    df = df[columns_order]

    # Export to Excel with formatting
    output = BytesIO()
    with pd.ExcelWriter(
        output, engine="xlsxwriter", datetime_format="dd/mm/yyyy"
    ) as writer:
        df.to_excel(
            writer, sheet_name="Accounting", index=False, startrow=1, header=False
        )

        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets["Accounting"]

        # Define formats
        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "top",
                "fg_color": "#4472C4",
                "font_color": "white",
                "border": 1,
            }
        )

        # Write the column headers with the defined format.
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Add number formatting for amount column
        amount_format = workbook.add_format({"num_format": "#,##0.00"})
        worksheet.set_column("F:F", 15, amount_format)  # Format Amount column

        # Set column widths
        worksheet.set_column("A:A", 12)  # Date
        worksheet.set_column("B:B", 10)  # Time
        worksheet.set_column("C:C", 25)  # Group
        worksheet.set_column("D:D", 25)  # IPO
        worksheet.set_column("E:E", 10)  # Type
        worksheet.set_column("F:F", 15)  # Amount
        worksheet.set_column("G:G", 8)  # JV
        worksheet.set_column("H:H", 40)  # Remarks
        worksheet.set_column("I:I", 20)  # User

        # Add autofilter
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

        # Freeze the first row
        worksheet.freeze_panes(1, 0)

    # Prepare HTTP response
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="Accounting_Export_{timestamp}.xlsx"'
    )
    output.seek(0)
    response.write(output.read())
    return response


def exportBillingFilterpdf(request, IPOid, group=None, IPOType=None, InvestorType=None):
    group = unquote(group)
    IPOType = unquote(IPOType)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    userid = request.user

    entry = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName=IPOName)
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid, OrderCategory="Premium"
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{IPOName}-Billing.PDF"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))

    # Create a centered title for your PDF
    styles = getSampleStyleSheet()
    title = f"<u>{IPOName}</u>"
    centered_title = Paragraph(title, styles["Title"])
    centered_title.alignment = 1  # Center alignment

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IpoPrePrice = IPOName.PreOpenPrice
    IpoPrice = IPOName.IPOPrice

    order = Order.objects.filter(
        user=userid, OrderIPOName_id=IPOid, OrderCategory="Premium"
    )

    total = 0
    Total1 = order.aggregate(Sum("Amount"))
    Total = Total1["Amount__sum"]
    if Total is None:
        Total = 0
    else:
        Total = Total
    totalorder = total + Total
    Total1 = entry.aggregate(Sum("Amount"))
    Total = Total1["Amount__sum"]
    if Total is None:
        Total = 0
    total = total + Total
    total = total + totalorder

    head = []
    head.append(
        [
            "IPO PRICE",
            IpoPrice,
            "PRE OPEN PRICE",
            IpoPrePrice,
            "TOTAL",
            "{:.2f}".format(total),
        ]
    )

    blank = [""]

    if group != "None" and group != "All":
        gid = GroupDetail.objects.get(GroupName=group, user=request.user).id
        entry = entry.filter(Order__OrderGroup_id=gid)
        order = order.filter(OrderGroup_id=gid)
    if IPOType != "None" and IPOType != "All":
        entry = entry.filter(Order__OrderCategory=IPOType)
        order = order.filter(OrderCategory=IPOType)

    table_data = []

    if IPOName.IPOType == "MAINBOARD":
        table_data.append(
            [
                "Group",
                "Order Category",
                "Investor Type",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount",
                "PAN No",
                "Client Name",
            ]
        )
    else:
        table_data.append(
            [
                "Group",
                "Order Category",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount Diff.",
                "PAN No",
                "Client Name",
            ]
        )

    if IPOName.IPOType == "MAINBOARD":
        if InvestorType != "None" and InvestorType != "All":
            entry = entry.filter(Order__InvestorType=InvestorType)
            order = order.filter(InvestorType=InvestorType)
        for member in entry.filter().values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__InvestorType",
            "Order__OrderType",
            "Order__Rate",
            "AllotedQty",
            "PreOpenPrice",
            "Amount",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
        ):
            table_data.append(member)
        for member in order.filter().values_list(
            "OrderGroup__GroupName",
            "OrderCategory",
            "InvestorType",
            "OrderType",
            "Rate",
            "Quantity",
            "OrderIPOName__PreOpenPrice",
            "Amount",
        ):
            table_data.append(member)
    else:
        for member in entry.filter().values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__OrderType",
            "Order__Rate",
            "AllotedQty",
            "PreOpenPrice",
            "Amount",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
        ):
            table_data.append(member)
        for member in order.filter().values_list(
            "OrderGroup__GroupName",
            "OrderCategory",
            "OrderType",
            "Rate",
            "Quantity",
            "OrderIPOName__PreOpenPrice",
            "Amount",
        ):
            table_data.append(member)

    table_width = 10.5 * inch

    table = Table(
        table_data, colWidths=[table_width / len(table_data[0])] * len(table_data[0])
    )
    h_table = Table(head, colWidths=[table_width / len(head[0])] * len(head[0]))
    h_blank = Table(blank)

    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),  # Header row background color
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),  # Header row text color
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # Center align all cells
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Header font
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Header padding
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),  # Data row background color
            ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Table grid
        ]
    )
    table.setStyle(style)

    h_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.bisque),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("TEXTCOLOR", (0, 0), (0, 0), colors.black),
        ]
    )
    h_table.setStyle(h_style)

    elements = []
    elements.append(centered_title)  # Add the centered title
    elements.append(Spacer(1, 12))  # Add some space between title and table

    elements.append(h_blank)
    elements.append(table)
    elements.append(h_blank)
    elements.append(h_table)
    doc.build(elements)
    return response


@allowed_users(allowed_roles=["Broker"])
def Backup(request, IPOid):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    response = HttpResponse(content_type="text/csv")

    entry = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName=IPOName)
    order1 = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid, OrderCategory="Premium"
    )
    # Orders download pdf func

    data1 = []
    if IPOName.IPOType == "MAINBOARD":
        data1Header = [
            "Group",
            "OrderType",
            "Order Category",
            "Investor Type",
            "Qty",
            "Rate",
            "Amount",
            "Order Date",
            "Order Time",
        ]
    else:
        data1Header = [
            "Group",
            "OrderType",
            "Order Category",
            "Qty",
            "Rate",
            "Amount",
            "Order Date",
            "Order Time",
        ]

    if IPOName.IPOType == "MAINBOARD":

        for member in order1.filter().values_list(
            "OrderGroup__GroupName",
            "OrderType",
            "OrderCategory",
            "InvestorType",
            "Quantity",
            "Rate",
            "Amount",
            "OrderDate",
            "OrderTime",
        ):
            data1.append(member)
    else:
        for member in order1.filter().values_list(
            "OrderGroup__GroupName",
            "OrderType",
            "OrderCategory",
            "Quantity",
            "Rate",
            "Amount",
            "OrderDate",
            "OrderTime",
        ):
            data1.append(member)

    # Client wise billing download pdf func

    data2 = []

    if entry:
        if IPOName.IPOType == "MAINBOARD":
            data2Header = [
                "Group",
                "Order Category",
                "Investor Type",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount",
                "PAN No",
                "Client Name",
            ]
        else:
            data2Header = [
                "Group",
                "Order Category",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount Diff.",
                "PAN No",
                "Client Name",
            ]

    else:
        if IPOName.IPOType == "MAINBOARD":
            data2Header = [
                "Group",
                "Order Category",
                "Investor Type",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount",
            ]
        else:
            data2Header = [
                "Group",
                "Order Category",
                "Order Type",
                "Rate",
                "AllotedQty",
                "PreOpen Price",
                "Amount Diff.",
            ]

    if IPOName.IPOType == "MAINBOARD":
        for member in entry.filter().values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__InvestorType",
            "Order__OrderType",
            "Order__Rate",
            "AllotedQty",
            "PreOpenPrice",
            "Amount",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
        ):
            data2.append(member)
        for member in order.filter().values_list(
            "OrderGroup__GroupName",
            "OrderCategory",
            "InvestorType",
            "OrderType",
            "Rate",
            "Quantity",
            "OrderIPOName__PreOpenPrice",
            "Amount",
        ):
            data2.append(member)
    else:
        for member in entry.filter().values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__OrderType",
            "Order__Rate",
            "AllotedQty",
            "PreOpenPrice",
            "Amount",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
        ):
            data2.append(member)
        for member in order.filter().values_list(
            "OrderGroup__GroupName",
            "OrderCategory",
            "OrderType",
            "Rate",
            "Quantity",
            "OrderIPOName__PreOpenPrice",
            "Amount",
        ):
            data2.append(member)

    df1 = pd.DataFrame(data1, columns=data1Header)
    df2 = pd.DataFrame(data2, columns=data2Header)

    with pd.ExcelWriter(
        f'{request.user}-{IPOName}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx',
        engine="xlsxwriter",
    ) as writer:
        df1.to_excel(writer, sheet_name="Sheet1", index=False)
        df2.to_excel(writer, sheet_name="Sheet2", index=False)

    with open(
        f'{request.user}-{IPOName}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx',
        "rb",
    ) as excel_file:
        response = HttpResponse(
            excel_file.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename={IPOName} {datetime.now().strftime("%d-%m-%Y- %H-%M")} .xlsx'
        )

    # Delete the Excel file from the server
    file_path = (
        f'{request.user}-{IPOName}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx'
    )

    if os.path.exists(file_path):
        os.remove(file_path)
    return response


def AllIpoBackup(request):
    user = request.user
    IPOs = CurrentIpoName.objects.filter(user=user)

    # Specify the common folder path where you want to save the client-specific folders
    common_folder_path = "path/to/common/folder"

    # Create a common folder if it doesn't exist
    if not os.path.exists(common_folder_path):
        os.makedirs(common_folder_path)

    for IPO in IPOs:
        IPOid = IPO.id
        current_IPO = CurrentIpoName.objects.get(id=IPOid, user=user)
        response = HttpResponse(content_type="text/csv")

        entry = OrderDetail.objects.filter(user=user, Order__OrderIPOName=current_IPO)
        order1 = Order.objects.filter(user=user, OrderIPOName_id=IPOid)
        order = Order.objects.filter(
            user=user, OrderIPOName_id=IPOid, OrderCategory="Premium"
        )

        data1 = []
        if current_IPO.IPOType == "MAINBOARD":
            data1Header = [
                "Group",
                "OrderType",
                "Order Category",
                "Investor Type",
                "Qty",
                "Rate",
                "Amount",
                "Order Date",
                "Order Time",
            ]
        else:
            data1Header = [
                "Group",
                "OrderType",
                "Order Category",
                "Qty",
                "Rate",
                "Amount",
                "Order Date",
                "Order Time",
            ]

        if current_IPO.IPOType == "MAINBOARD":
            for member in order1.filter().values_list(
                "OrderGroup__GroupName",
                "OrderType",
                "OrderCategory",
                "InvestorType",
                "Quantity",
                "Rate",
                "Amount",
                "OrderDate",
                "OrderTime",
            ):
                data1.append(member)
        else:
            for member in order1.filter().values_list(
                "OrderGroup__GroupName",
                "OrderType",
                "OrderCategory",
                "Quantity",
                "Rate",
                "Amount",
                "OrderDate",
                "OrderTime",
            ):
                data1.append(member)

        data2 = []

        if entry:
            if current_IPO.IPOType == "MAINBOARD":
                data2Header = [
                    "Group",
                    "Order Category",
                    "Investor Type",
                    "Order Type",
                    "Rate",
                    "AllotedQty",
                    "PreOpen Price",
                    "Amount",
                    "PAN No",
                    "Client Name",
                ]
            else:
                data2Header = [
                    "Group",
                    "Order Category",
                    "Order Type",
                    "Rate",
                    "AllotedQty",
                    "PreOpen Price",
                    "Amount Diff.",
                    "PAN No",
                    "Client Name",
                ]
        else:
            if current_IPO.IPOType == "MAINBOARD":
                data2Header = [
                    "Group",
                    "Order Category",
                    "Investor Type",
                    "Order Type",
                    "Rate",
                    "AllotedQty",
                    "PreOpen Price",
                    "Amount",
                ]
            else:
                data2Header = [
                    "Group",
                    "Order Category",
                    "Order Type",
                    "Rate",
                    "AllotedQty",
                    "PreOpen Price",
                    "Amount Diff.",
                ]

        if current_IPO.IPOType == "MAINBOARD":
            for member in entry.filter().values_list(
                "Order__OrderGroup__GroupName",
                "Order__OrderCategory",
                "Order__InvestorType",
                "Order__OrderType",
                "Order__Rate",
                "AllotedQty",
                "PreOpenPrice",
                "Amount",
                "OrderDetailPANNo__PANNo",
                "OrderDetailPANNo__Name",
            ):
                data2.append(member)
            for member in order.filter().values_list(
                "OrderGroup__GroupName",
                "OrderCategory",
                "InvestorType",
                "OrderType",
                "Rate",
                "Quantity",
                "OrderIPOName__PreOpenPrice",
                "Amount",
            ):
                data2.append(member)
        else:
            for member in entry.filter().values_list(
                "Order__OrderGroup__GroupName",
                "Order__OrderCategory",
                "Order__OrderType",
                "Order__Rate",
                "AllotedQty",
                "PreOpenPrice",
                "Amount",
                "OrderDetailPANNo__PANNo",
                "OrderDetailPANNo__Name",
            ):
                data2.append(member)
            for member in order.filter().values_list(
                "OrderGroup__GroupName",
                "OrderCategory",
                "OrderType",
                "Rate",
                "Quantity",
                "OrderIPOName__PreOpenPrice",
                "Amount",
            ):
                data2.append(member)

        df1 = pd.DataFrame(data1, columns=data1Header)
        df2 = pd.DataFrame(data2, columns=data2Header)

        # Create a client-specific folder within the common folder
        client_folder_path = os.path.join(common_folder_path, str(user))
        if not os.path.exists(client_folder_path):
            os.makedirs(client_folder_path)

        file_name = (
            f'{user}-{current_IPO}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx'
        )
        file_path = os.path.join(client_folder_path, file_name)

        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            df1.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Sheet2", index=False)

    # Provide a zip file containing all Excel files
    zip_filename = f'backup_files-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.zip'
    zip_path = os.path.join(common_folder_path, zip_filename)
    with ZipFile(zip_path, "w") as zipf:
        for root, dirs, files in os.walk(common_folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    # Provide the zip file for download
    with open(zip_path, "rb") as zip_file:
        response = HttpResponse(zip_file.read(), content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={zip_filename}"

    # Clean up: remove the common folder and its contents
    shutil.rmtree(common_folder_path)

    return response


# app buy-sell panding pan download fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def export(
    request,
    IPOid,
    OrderType,
    group=None,
    IPOType=None,
    InvestorType=None,
    OrderDate=None,
    OrderTime=None,
):
    group = unquote(group)
    IPOType = unquote(IPOType)
    response = HttpResponse(content_type="text/csv")
    if request.user.groups.all()[0].name == "Broker":
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        entry = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPOid
        )
        if group != "None" and group != "All":
            gid = GroupDetail.objects.get(GroupName=group, user=request.user).id
            entry = entry.filter(Order__OrderGroup_id=gid)
    else:
        entry = OrderDetail.objects.filter(
            user=request.user.Broker_id,
            Order__OrderIPOName_id=IPOid,
            Order__OrderGroup_id=request.user.Group_id,
        )
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)
        if group != "None" and group != "All":
            gid = GroupDetail.objects.get(id=request.user.Group_id).id
            entry = entry.filter(Order__OrderGroup_id=gid)

    if OrderDate is not None and OrderDate != "None":
        OrderDate = OrderDate[0:4] + "-" + OrderDate[4:6] + "-" + OrderDate[6:8]
        entry = entry.filter(Order__OrderDate=OrderDate)

    if OrderTime is not None and OrderTime != "None":
        OrderTime = OrderTime[0:2] + ":" + OrderTime[2:4] + ":" + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime=OrderTime)

    if OrderType == "BUY":
        entry = entry.filter(Order__OrderType="BUY")
    if OrderType == "SELL":
        entry = entry.filter(Order__OrderType="SELL")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Group",
            "Order Category",
            "Investor Type",
            "Rate",
            "PAN No",
            "Client Name",
            "Alloted Qty",
            "Demat Number",
            "Application Number",
            "Order Date",
            " Order Time",
        ]
    )

    if IPOType != "None" and IPOType != "All":
        entry = entry.filter(Order__OrderCategory=IPOType)
    if InvestorType != "None" and InvestorType != "All":
        entry = entry.filter(Order__InvestorType=InvestorType)

    for member in entry.filter(OrderDetailPANNo_id=None).values_list(
        "Order__OrderGroup__GroupName",
        "Order__OrderCategory",
        "Order__InvestorType",
        "Order__Rate",
        "OrderDetailPANNo__PANNo",
        "OrderDetailPANNo__Name",
        "AllotedQty",
        "DematNumber",
        "ApplicationNumber",
        "Order__OrderDate",
        "Order__OrderTime",
    ):
        List = list(member)
        List[9] = str(List[9].strftime("%d/%m/%Y"))
        if List[7] != "":
            List[7] = "'" + List[7]
        member = tuple(List)
        writer.writerow(member)

    response["Content-Disposition"] = (
        f'attachment; filename="{IPOName}-OrderDetail.csv"'
    )

    return response


@allowed_users(allowed_roles=["Broker", "Customer"])
def Group_wise_export(
    request,
    IPOid,
    OrderType,
    IPOType=None,
    InvestorType=None,
    OrderDate=None,
    OrderTime=None,
):
    IPOType = unquote(IPOType) if IPOType else "All"
    InvestorType = unquote(InvestorType) if InvestorType else "All"

    # Get IPOName
    if request.user.groups.all()[0].name == "Broker":
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        all_groups = GroupDetail.objects.filter(
            user=request.user,
        )
    else:
        # Assuming customers only see their assigned group's data
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)
        all_groups = GroupDetail.objects.filter(id=request.user.Group_id)

    # Create a temporary directory to store CSV files
    temp_dir_name = f'ipo_group_exports_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    temp_dir_path = os.path.join(
        "/tmp", temp_dir_name
    )  # Using /tmp for temporary files, consider a more robust path for production
    os.makedirs(temp_dir_path, exist_ok=True)

    csv_files_to_zip = []

    for group in all_groups:
        entry = OrderDetail.objects.filter(
            Order__OrderIPOName_id=IPOid,
            Order__OrderType=OrderType,
            Order__OrderGroup=group,
        )

        if request.user.groups.all()[0].name == "Broker":
            entry = entry.filter(user=request.user)
        else:
            entry = entry.filter(user=request.user.Broker_id)

        # Apply additional filters if provided
        if OrderDate is not None and OrderDate != "None":
            OrderDate = OrderDate[0:4] + "-" + OrderDate[4:6] + "-" + OrderDate[6:8]
            entry = entry.filter(Order__OrderDate=OrderDate)

        if OrderTime is not None and OrderTime != "None":
            OrderTime = OrderTime[0:2] + ":" + OrderTime[2:4] + ":" + OrderTime[4:6]
            entry = entry.filter(Order__OrderTime=OrderTime)

        if IPOType != "None" and IPOType != "All":
            entry = entry.filter(Order__OrderCategory=IPOType)
        if InvestorType != "None" and InvestorType != "All":
            entry = entry.filter(Order__InvestorType=InvestorType)

        if entry.exists():
            # Create a CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "Group",
                    "Order Category",
                    "Investor Type",
                    "Rate",
                    "PAN No",
                    "Client Name",
                    "Alloted Qty",
                    "Demat Number",
                    "Application Number",
                    "Order Date",
                    "Order Time",
                ]
            )

            # Write data rows
            for member in entry.filter(OrderDetailPANNo_id=None).values_list(
                "Order__OrderGroup__GroupName",
                "Order__OrderCategory",
                "Order__InvestorType",
                "Order__Rate",
                "OrderDetailPANNo__PANNo",
                "OrderDetailPANNo__Name",
                "AllotedQty",
                "DematNumber",
                "ApplicationNumber",
                "Order__OrderDate",
                "Order__OrderTime",
            ):
                List = list(member)
                if List[9]:  # Check if OrderDate is not None
                    List[9] = str(List[9].strftime("%d/%m/%Y"))
                if List[7]:  # Check if DematNumber is not None/empty
                    List[7] = "'" + str(
                        List[7]
                    )  # Ensure it's a string before prepending "'"
                writer.writerow(List)

            # Save the in-memory CSV to a temporary file
            csv_filename = f"{iponame_obj.IPOName}_{group.GroupName}.csv"
            csv_filepath = os.path.join(temp_dir_path, csv_filename)
            with open(csv_filepath, "w", newline="", encoding="utf-8") as f:
                f.write(output.getvalue())
            csv_files_to_zip.append(csv_filepath)

    # Create a zip file
    zip_filename = f'{iponame_obj.IPOName}_GroupWiseOrders_{datetime.now().strftime("%Y%m%d%H%M")}.zip'
    zip_filepath = os.path.join(
        "/tmp", zip_filename
    )  # Using /tmp for temporary files, adjust as needed

    with ZipFile(zip_filepath, "w") as zipf:
        for file_path in csv_files_to_zip:
            zipf.write(file_path, arcname=os.path.basename(file_path))

    # Provide the zip file for download
    with open(zip_filepath, "rb") as zf:
        response = HttpResponse(zf.read(), content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={zip_filename}"

    # Clean up: remove the temporary directory and the zip file
    shutil.rmtree(temp_dir_path)
    os.remove(zip_filepath)

    return response


# app buy-sell all pan download fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def exportall(
    request,
    IPOid,
    OrderType,
    group=None,
    IPOType=None,
    InvestorType=None,
    OrderDate=None,
    OrderTime=None,
):
    group = unquote(group)
    IPOType = unquote(IPOType)
    response = HttpResponse(content_type="text/csv")
    if request.user.groups.all()[0].name == "Broker":
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        entry = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPOid
        )
        if group != "None" and group != "All":
            gid = GroupDetail.objects.get(GroupName=group, user=request.user).id
            entry = entry.filter(Order__OrderGroup_id=gid)
    else:
        entry = OrderDetail.objects.filter(
            user=request.user.Broker_id,
            Order__OrderIPOName_id=IPOid,
            Order__OrderGroup_id=request.user.Group_id,
        )
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)
        if group != "None" and group != "All":
            gid = GroupDetail.objects.get(id=request.user.Group_id).id
            entry = entry.filter(Order__OrderGroup_id=gid)

    if OrderDate is not None and OrderDate != "None":
        OrderDate = OrderDate[0:4] + "-" + OrderDate[4:6] + "-" + OrderDate[6:8]
        entry = entry.filter(Order__OrderDate=OrderDate)

    if OrderTime is not None and OrderTime != "None":
        OrderTime = OrderTime[0:2] + ":" + OrderTime[2:4] + ":" + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime=OrderTime)

    if OrderType == "BUY":
        entry = entry.filter(Order__OrderType="BUY")
    if OrderType == "SELL":
        entry = entry.filter(Order__OrderType="SELL")

    writer = csv.writer(response)
    writer.writerow(
        [
            "Group",
            "IPO Type",
            "Investor Type",
            "Rate",
            "PAN No",
            "Client Name",
            "AllotedQty",
            "Demat Number",
            "Application Number",
            "Order Date",
            "Order Time",
        ]
    )

    if IPOType != "None" and IPOType != "All":
        entry = entry.filter(Order__OrderCategory=IPOType)
    if InvestorType != "None" and InvestorType != "All":
        entry = entry.filter(Order__InvestorType=InvestorType)

    entry = entry.order_by("Order__OrderGroup__GroupName", "Order__Rate")
    for member in entry.filter().values_list(
        "Order__OrderGroup__GroupName",
        "Order__OrderCategory",
        "Order__InvestorType",
        "Order__Rate",
        "OrderDetailPANNo__PANNo",
        "OrderDetailPANNo__Name",
        "AllotedQty",
        "DematNumber",
        "ApplicationNumber",
        "Order__OrderDate",
        "Order__OrderTime",
    ):
        List = list(member)
        List[9] = str(List[9].strftime("%d/%m/%Y"))
        if List[7] != "":
            List[7] = "'" + List[7]
        member = tuple(List)
        writer.writerow(member)
    response["Content-Disposition"] = (
        f'attachment; filename="{IPOName}-OrderDetail-AllRecords.csv"'
    )

    return response


@allowed_users(allowed_roles=["Broker", "Customer"])
def Group_wise_exportall(
    request,
    IPOid,
    OrderType,
    IPOType=None,
    InvestorType=None,
    OrderDate=None,
    OrderTime=None,
):
    IPOType = unquote(IPOType) if IPOType else "All"
    InvestorType = unquote(InvestorType) if InvestorType else "All"

    # Get IPOName
    if request.user.groups.all()[0].name == "Broker":
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        all_groups = GroupDetail.objects.filter(
            user=request.user,
        )
    else:
        # Assuming customers only see their assigned group's data
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)
        all_groups = GroupDetail.objects.filter(id=request.user.Group_id)

    # Create a temporary directory to store CSV files
    temp_dir_name = f'ipo_group_exports_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    temp_dir_path = os.path.join(
        "/tmp", temp_dir_name
    )  # Using /tmp for temporary files, consider a more robust path for production
    os.makedirs(temp_dir_path, exist_ok=True)

    csv_files_to_zip = []

    for group in all_groups:
        entry = OrderDetail.objects.filter(
            Order__OrderIPOName_id=IPOid,
            Order__OrderType=OrderType,
            Order__OrderGroup=group,
        )

        if request.user.groups.all()[0].name == "Broker":
            entry = entry.filter(user=request.user)
        else:
            entry = entry.filter(user=request.user.Broker_id)

        # Apply additional filters if provided
        if OrderDate is not None and OrderDate != "None":
            OrderDate = OrderDate[0:4] + "-" + OrderDate[4:6] + "-" + OrderDate[6:8]
            entry = entry.filter(Order__OrderDate=OrderDate)

        if OrderTime is not None and OrderTime != "None":
            OrderTime = OrderTime[0:2] + ":" + OrderTime[2:4] + ":" + OrderTime[4:6]
            entry = entry.filter(Order__OrderTime=OrderTime)

        if IPOType != "None" and IPOType != "All":
            entry = entry.filter(Order__OrderCategory=IPOType)
        if InvestorType != "None" and InvestorType != "All":
            entry = entry.filter(Order__InvestorType=InvestorType)

        if entry.exists():
            # Create a CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "Group",
                    "Order Category",
                    "Investor Type",
                    "Rate",
                    "PAN No",
                    "Client Name",
                    "Alloted Qty",
                    "Demat Number",
                    "Application Number",
                    "Order Date",
                    "Order Time",
                ]
            )

            # Write data rows
            for member in entry.values_list(
                "Order__OrderGroup__GroupName",
                "Order__OrderCategory",
                "Order__InvestorType",
                "Order__Rate",
                "OrderDetailPANNo__PANNo",
                "OrderDetailPANNo__Name",
                "AllotedQty",
                "DematNumber",
                "ApplicationNumber",
                "Order__OrderDate",
                "Order__OrderTime",
            ):
                List = list(member)
                if List[9]:  # Check if OrderDate is not None
                    List[9] = str(List[9].strftime("%d/%m/%Y"))
                if List[7]:  # Check if DematNumber is not None/empty
                    List[7] = "'" + str(
                        List[7]
                    )  # Ensure it's a string before prepending "'"
                writer.writerow(List)

            # Save the in-memory CSV to a temporary file
            csv_filename = f"{iponame_obj.IPOName}_{group.GroupName}.csv"
            csv_filepath = os.path.join(temp_dir_path, csv_filename)
            with open(csv_filepath, "w", newline="", encoding="utf-8") as f:
                f.write(output.getvalue())
            csv_files_to_zip.append(csv_filepath)

    # Create a zip file
    zip_filename = f'{iponame_obj.IPOName}_GroupWiseOrders_{datetime.now().strftime("%Y%m%d%H%M")}.zip'
    zip_filepath = os.path.join(
        "/tmp", zip_filename
    )  # Using /tmp for temporary files, adjust as needed

    with ZipFile(zip_filepath, "w") as zipf:
        for file_path in csv_files_to_zip:
            zipf.write(file_path, arcname=os.path.basename(file_path))

    # Provide the zip file for download
    with open(zip_filepath, "rb") as zf:
        response = HttpResponse(zf.read(), content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={zip_filename}"

    # Clean up: remove the temporary directory and the zip file
    shutil.rmtree(temp_dir_path)
    os.remove(zip_filepath)

    return response


@allowed_users(allowed_roles=["Broker", "Customer"])
def Error_csv(request):
    msg = messages.get_messages(request)
    response = HttpResponse(content_type="text/csv")
    writer = csv.writer(response)

    if request.method == "POST":
        msg = request.POST.get("name", "")
        list1 = msg.split("Row [")

        writer.writerow(
            [
                "Group",
                "Order Category",
                "Investor Type",
                "Rate",
                "PAN No",
                "Client Name",
                "AllotedQty",
                "Demat Number",
                "Application Number",
                "Order Date",
                "Order Time",
                "Error",
            ]
        )

        for i in list1:
            list2 = [""]
            list3 = ""

            idx = i.find("]")
            for j in i[idx:]:
                list3 = list3 + j

            y = i.replace(list3, "")
            elements = y.split(",")
            elements = [element.strip().strip("'").strip('"') for element in elements]
            if elements != list2:
                writer.writerow(elements)

        response["Content-Disposition"] = (
            f'attachment; filename="Errors_in_Upload-{datetime.now().strftime("%d-%m-%Y- %H-%M-%S")}.csv"'
        )

        return response


# app buy-sell bulk order upload fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def OrderDetail_upload(
    request,
    IPOid,
    OrderType,
    GrpName,
    OrderCategory,
    InvestorType,
    OrderDate,
    OrderTime,
):
    csv_file = request.FILES["file"]
    if not csv_file.name.endswith(".csv"):
        messages.info(request, "THIS IS NOT A CSV FILE")
    else:
        data_set = csv_file.read().decode("windows-1252")
        io_string = io.StringIO(data_set)
        next(io_string)
        try:
            for column in csv.reader(io_string, delimiter=",", quotechar="|"):
                Demate_no = column[7].replace("'", "")
                try:
                    try:
                        Date_split = column[9].split("/")
                        Date = Date_split[2] + "-" + Date_split[1] + "-" + Date_split[0]
                    except:
                        Date_split = column[9].split("-")
                        Date = Date_split[2] + "-" + Date_split[1] + "-" + Date_split[0]

                    variable = column[4].upper().strip()
                    IsUpdated = 0
                    if variable == "":
                        column.append("No PAN")
                        messages.error(request, f"Row {column} Does not have PAN no.")
                    elif not isValidPAN(variable):
                        column.append("Invalid PAN")
                        messages.error(request, f"Row {column} has Invaild PAN no.")
                    else:
                        if IsUpdated == 0:
                            if OrderType == "BUY":
                                PANExists1 = OrderDetail.objects.filter(
                                    user=request.user,
                                    Order__OrderIPOName_id=IPOid,
                                    Order__OrderGroup__GroupName=column[0],
                                    Order__OrderCategory=column[1],
                                    Order__InvestorType=column[2],
                                    Order__Rate=column[3],
                                    OrderDetailPANNo__PANNo=variable,
                                    Order__OrderType="BUY",
                                    Order__OrderDate=Date,
                                    Order__OrderTime=column[10],
                                )
                            if OrderType == "SELL":
                                PANExists1 = OrderDetail.objects.filter(
                                    user=request.user,
                                    Order__OrderIPOName_id=IPOid,
                                    Order__OrderGroup__GroupName=column[0],
                                    Order__OrderCategory=column[1],
                                    Order__InvestorType=column[2],
                                    Order__Rate=column[3],
                                    OrderDetailPANNo__PANNo=variable,
                                    Order__OrderType="SELL",
                                    Order__OrderDate=Date,
                                    Order__OrderTime=column[10],
                                )
                            if PANExists1.exists():
                                PANExists = PANExists1.first()
                                if column[4] != "":
                                    gid = GroupDetail.objects.get(
                                        GroupName=column[0], user=request.user
                                    ).id
                                    if ClientDetail.objects.filter(
                                        user=request.user, PANNo=variable
                                    ).exists():
                                        employee = ClientDetail.objects.get(
                                            user=request.user, PANNo=variable
                                        )

                                        if employee.Name == "":
                                            employee.Name = column[5]
                                        if employee.Group != column[0]:
                                            employee.Group_id = gid
                                            employee.save()
                                        employee.save()

                                    else:
                                        PANNUMBER = ClientDetail(
                                            user=request.user,
                                            PANNo=variable,
                                            Name=column[5],
                                            Group_id=gid,
                                        )
                                        PANNUMBER.save()

                                r = 1
                                for j in OrderDetail.objects.filter(
                                    user=request.user,
                                    Order__OrderIPOName_id=IPOid,
                                    Order__OrderType=OrderType,
                                ).values("OrderDetailPANNo__PANNo"):
                                    if variable == j.get("OrderDetailPANNo__PANNo"):
                                        column.append("PAN exist already")
                                        messages.error(
                                            request,
                                            f"Row {column} has PAN no. that already exists:",
                                        )
                                        r = 0
                                        break

                                PANExists.ClientName = column[5]
                                if column[6] == "":
                                    AllotedQty = None
                                else:
                                    AllotedQty = column[6]
                                PANExists.AllotedQty = AllotedQty
                                PANExists.DematNumber = Demate_no
                                PANExists.ApplicationNumber = column[8]

                                PANExists.save()
                                IsUpdated = 1
                        if IsUpdated == 0:
                            if OrderType == "BUY":
                                PANNotExists1 = OrderDetail.objects.filter(
                                    user=request.user,
                                    Order__OrderIPOName_id=IPOid,
                                    Order__OrderGroup__GroupName=column[0],
                                    Order__OrderCategory=column[1],
                                    Order__InvestorType=column[2],
                                    Order__Rate=column[3],
                                    OrderDetailPANNo__PANNo=None,
                                    Order__OrderType="BUY",
                                    Order__OrderDate=Date,
                                    Order__OrderTime=column[10],
                                )
                            if OrderType == "SELL":
                                PANNotExists1 = OrderDetail.objects.filter(
                                    user=request.user,
                                    Order__OrderIPOName_id=IPOid,
                                    Order__OrderGroup__GroupName=column[0],
                                    Order__OrderCategory=column[1],
                                    Order__InvestorType=column[2],
                                    Order__Rate=column[3],
                                    OrderDetailPANNo__PANNo=None,
                                    Order__OrderType="SELL",
                                    Order__OrderDate=Date,
                                    Order__OrderTime=column[10],
                                )

                            if PANNotExists1.exists():
                                PANNotExists = PANNotExists1.first()
                                if column[4] != "":
                                    gid = GroupDetail.objects.get(
                                        GroupName=column[0], user=request.user
                                    ).id
                                    if ClientDetail.objects.filter(
                                        user=request.user, PANNo=variable
                                    ).exists():
                                        employee = ClientDetail.objects.get(
                                            user=request.user, PANNo=variable
                                        )

                                        if employee.Name == "":
                                            employee.Name = column[5]
                                        if employee.Group != column[0]:
                                            employee.Group_id = gid
                                            employee.save()
                                        employee.save()

                                    else:
                                        PANNUMBER = ClientDetail(
                                            user=request.user,
                                            PANNo=variable,
                                            Name=column[5],
                                            Group_id=gid,
                                        )
                                        PANNUMBER.save()
                                r = 1
                                for j in OrderDetail.objects.filter(
                                    user=request.user,
                                    Order__OrderIPOName_id=IPOid,
                                    Order__OrderType=OrderType,
                                ).values("OrderDetailPANNo__PANNo"):
                                    if variable == j.get("OrderDetailPANNo__PANNo"):
                                        column.append("PAN exist already")
                                        messages.error(
                                            request,
                                            f"Row {column} has PAN no. that already exists:",
                                        )
                                        r = 0
                                        break

                                if r == 1:
                                    cid = ClientDetail.objects.get(
                                        user=request.user, PANNo=variable
                                    ).id

                                    PANNotExists.OrderDetailPANNo_id = cid

                                    if column[6] == "":
                                        AllotedQty = None
                                    else:
                                        AllotedQty = column[6]
                                    PANNotExists.AllotedQty = AllotedQty
                                    PANNotExists.DematNumber = Demate_no
                                    PANNotExists.ApplicationNumber = column[8]
                                    PANNotExists.save()

                except:
                    column.append("Error")
                    messages.error(request, f"Row {column} has error.")

        except:
            traceback.print_exc()
            column.append("Error")
            messages.error(request, "File Details are invaild.")
        calculate(IPOid, request.user)
    if GrpName == "None" and OrderCategory == "None" and InvestorType == "None":
        return redirect(f"/{IPOid}/OrderDetail/{OrderType}")
    return redirect(
        f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}"
    )


def Sempale_Order(request, IPOid):
    response = HttpResponse(content_type="text/csv")
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    writer = csv.writer(response)
    if IPOName.IPOType == "MAINBOARD":
        writer.writerow(
            [
                "GroupName",
                "Ordertype",
                "OrderCategory",
                "InvestorType",
                "Quantity",
                "Rate",
                "StrikPrice",
            ]
        )
    else:
        writer.writerow(
            [
                "GroupName",
                "Ordertype",
                "OrderCategory",
                "InvestorType",
                "Quantity",
                "Rate",
                "StrikPrice",
            ]
        )

    response["Content-Disposition"] = f'attachment; filename="Order-Sample.csv"'

    return response


def Order_upload(request, IPOid, Groupfilter, Ordercatagoryfilter, InvestorTypefilter):
    csv_file = request.FILES["file"]
    if not csv_file.name.endswith(".csv"):
        messages.info(request, "THIS IS NOT A CSV FILE", extra_tags="error")
    else:
        data_set = csv_file.read().decode("windows-1252")

        io_string = io.StringIO(data_set)
        next(io_string)
        try:
            uid = request.user
            user = request.user
            IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
            PreOpenPrice = IPOName.PreOpenPrice

            for column in csv.reader(io_string, delimiter=",", quotechar="|"):

                if len(column) >= 6:
                    column_mappings = {
                        1: {"BUY": "BUY", "SELL": "SELL"},
                        2: {
                            "KOSTAK": "Kostak",
                            "SUBJECT TO": "Subject To",
                            "PREMIUM": "Premium",
                            "CALL": "CALL",
                            "CALL": "CALL",
                        },
                        3: {
                            "BHNI": "BHNI",
                            "PREMIUM": "PREMIUM",
                            "RETAIL": "RETAIL",
                            "SHNI": "SHNI",
                            "OPTIONS": "OPTIONS",
                        },
                    }

                    # Iterate over the columns and apply the mapping
                    for col_index, mapping in column_mappings.items():
                        column_value = column[col_index].strip().upper()
                        if column_value in mapping:
                            column[col_index] = mapping[column_value]
                    if (
                        (column[1].strip() in ["BUY", "SELL"])
                        and (
                            column[2].strip()
                            in ["Kostak", "Subject To", "Premium", "CALL", "PUT"]
                        )
                        and (
                            column[3].strip()
                            in ["BHNI", "PREMIUM", "RETAIL", "SHNI", "OPTIONS"]
                        )
                    ):

                        try:
                            GroupName = column[0].strip().upper()
                            gid = GroupDetail.objects.get(
                                GroupName=GroupName, user=user
                            ).id
                            O_type = column[1]
                            O_Category = column[2]
                            if IPOName.IPOType == "MAINBOARD":
                                O_InvestorType = column[3].strip()
                                O_Quantity = int(column[4].strip())
                                if O_Quantity <= 0:
                                    raise ValueError(
                                        "O_Quantity must be a positive value greater than zero."
                                    )
                                O_Rate = float(column[5].strip())
                                O_StrikePrice = column[6].strip()
                                if O_Rate <= 0:
                                    raise ValueError(
                                        "O_Quantity must be a positive value greater than zero."
                                    )
                            else:
                                O_InvestorType = "RETAIL"
                                O_Quantity = column[4]
                                O_Rate = column[5]
                                O_StrikePrice = column[6].strip()

                            O_Date = datetime.now().strftime("%Y-%m-%d")
                            O_Time = datetime.now().strftime("%H:%M:%S")

                            if O_type == "BUY":
                                a = 0
                                if (
                                    O_Category.strip().upper() != "PREMIUM"
                                    and O_InvestorType.strip().upper() != "PREMIUM"
                                    and O_InvestorType.strip().upper() != "CALL"
                                    and O_Category.strip().upper() == "PUT"
                                    and O_InvestorType.strip().upper() != "OPTIONS"
                                ):
                                    if (
                                        O_Quantity != ""
                                        and O_Quantity != "0"
                                        and O_Rate != ""
                                    ):
                                        order = Order(
                                            user=uid,
                                            OrderGroup_id=gid,
                                            OrderIPOName=IPOName,
                                            InvestorType=O_InvestorType,
                                            OrderCategory=O_Category,
                                            OrderType=O_type,
                                            Quantity=O_Quantity,
                                            Rate=O_Rate,
                                            OrderDate=O_Date,
                                            OrderTime=O_Time,
                                        )

                                        O_limit = CustomUser.objects.get(username=user)
                                        if O_limit.Order_limit is not None:
                                            BUY_Count = OrderDetail.objects.filter(
                                                user=user, Order__OrderIPOName_id=IPOid
                                            ).count()
                                            Sum_Qty = int(BUY_Count) + int(O_Quantity)
                                            Limit = int(O_limit.Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(
                                                    request,
                                                    f"You have reached the limit of {Limit} Order.",
                                                )
                                                return redirect(f"/{IPOid}/BUY")

                                        order.save()
                                        a = 1
                                        Order_Details_update_sync(
                                            O_Quantity, uid, order.id, PreOpenPrice
                                        )
                                        # for i in range(0, int(O_Quantity)):
                                        #     orderdetail = OrderDetail( user=user, Order_id=order.id , PreOpenPrice = PreOpenPrice)
                                        #     orderdetail.save()
                                elif (
                                    O_Category.strip().upper() == "PREMIUM"
                                    and O_InvestorType.strip().upper() == "PREMIUM"
                                ):
                                    if (
                                        O_Quantity != ""
                                        and O_Quantity != "0"
                                        and O_Rate != ""
                                    ):
                                        order = Order(
                                            user=uid,
                                            OrderGroup_id=gid,
                                            OrderIPOName=IPOName,
                                            InvestorType="PREMIUM",
                                            OrderCategory="Premium",
                                            OrderType="BUY",
                                            Quantity=O_Quantity,
                                            Rate=O_Rate,
                                            OrderDate=O_Date,
                                            OrderTime=O_Time,
                                        )

                                        O_limit = CustomUser.objects.get(username=user)
                                        if O_limit.Premium_Order_limit is not None:
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(
                                                user=user,
                                                OrderIPOName_id=IPOid,
                                                OrderCategory=Order_type,
                                            ).aggregate(Sum("Quantity"))[
                                                "Quantity__sum"
                                            ]
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit = int(O_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(
                                                    request,
                                                    f"You have reached the limit of {Limit} Order.",
                                                )
                                                return redirect(f"/{IPOid}/BUY")

                                        order.save()
                                elif (
                                    O_Category.strip().upper() in ("CALL", "PUT")
                                    and O_InvestorType.strip().upper() == "OPTIONS"
                                ):
                                    if (
                                        O_Quantity != ""
                                        and O_Quantity != "0"
                                        and O_Rate != ""
                                    ):
                                        order = Order(
                                            user=uid,
                                            OrderGroup_id=gid,
                                            OrderIPOName=IPOName,
                                            InvestorType="OPTIONS",
                                            OrderCategory=O_Category.strip().upper(),
                                            OrderType="BUY",
                                            Quantity=O_Quantity,
                                            Rate=O_Rate,
                                            OrderDate=O_Date,
                                            OrderTime=O_Time,
                                            Method=O_StrikePrice,
                                        )

                                        O_limit = CustomUser.objects.get(username=user)
                                        if O_limit.Premium_Order_limit is not None:
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(
                                                user=user,
                                                OrderIPOName_id=IPOid,
                                                OrderCategory=Order_type,
                                            ).aggregate(Sum("Quantity"))[
                                                "Quantity__sum"
                                            ]
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit = int(O_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(
                                                    request,
                                                    f"You have reached the limit of {Limit} Order.",
                                                )
                                                return redirect(f"/{IPOid}/BUY")

                                        order.save()

                                else:
                                    column.append("Error")
                                    messages.error(
                                        request,
                                        f"Row {column} has error.",
                                        extra_tags="error",
                                    )
                            else:
                                a = 0
                                # if O_Category != 'Premium' and O_Category != 'premium' and O_Category != 'PREMIUM' and O_InvestorType.strip().upper() != 'PREMIUM':
                                if (
                                    O_Category.strip().upper() != "PREMIUM"
                                    and O_InvestorType.strip().upper() != "PREMIUM"
                                    and O_InvestorType.strip().upper() != "CALL"
                                    and O_Category.strip().upper() == "PUT"
                                    and O_InvestorType.strip().upper() != "OPTIONS"
                                ):
                                    if (
                                        O_Quantity != ""
                                        and O_Quantity != "0"
                                        and O_Rate != ""
                                    ):
                                        order = Order(
                                            user=uid,
                                            OrderGroup_id=gid,
                                            OrderIPOName=IPOName,
                                            InvestorType=O_InvestorType,
                                            OrderCategory=O_Category,
                                            OrderType="SELL",
                                            Quantity=O_Quantity,
                                            Rate=O_Rate,
                                            OrderDate=O_Date,
                                            OrderTime=O_Time,
                                        )

                                        O_limit = CustomUser.objects.get(username=user)

                                        if O_limit.Order_limit is not None:
                                            BUY_Count = OrderDetail.objects.filter(
                                                user=user, Order__OrderIPOName_id=IPOid
                                            ).count()
                                            Sum_Qty = int(BUY_Count) + int(O_Quantity)
                                            Limit = int(O_limit.Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(
                                                    request,
                                                    f"You have reached the limit of {Limit} Order.",
                                                )
                                                return redirect(f"/{IPOid}/BUY")

                                        order.save()
                                        a = 1
                                        Order_Details_update_sync(
                                            O_Quantity, uid, order.id, PreOpenPrice
                                        )
                                        # for i in range(0, int(O_Quantity)):
                                        #     orderdetail = OrderDetail( user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                                        #     orderdetail.save()
                                elif (
                                    O_Category.strip().upper() == "PREMIUM"
                                    and O_InvestorType.strip().upper() == "PREMIUM"
                                ):
                                    if (
                                        O_Quantity != ""
                                        and O_Quantity != "0"
                                        and O_Rate != ""
                                    ):
                                        order = Order(
                                            user=uid,
                                            OrderGroup_id=gid,
                                            OrderIPOName=IPOName,
                                            InvestorType="PREMIUM",
                                            OrderCategory="Premium",
                                            OrderType="SELL",
                                            Quantity=O_Quantity,
                                            Rate=O_Rate,
                                            OrderDate=O_Date,
                                            OrderTime=O_Time,
                                        )

                                        PRI_limit = CustomUser.objects.get(
                                            username=user
                                        )

                                        if PRI_limit.Premium_Order_limit is not None:
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(
                                                user=user,
                                                OrderIPOName_id=IPOid,
                                                OrderCategory=Order_type,
                                            ).aggregate(Sum("Quantity"))[
                                                "Quantity__sum"
                                            ]
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit = int(PRI_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(
                                                    request,
                                                    f"You have reached the limit of {Limit} Order.",
                                                )
                                                return redirect(f"/{IPOid}/BUY")

                                        order.save()

                                elif (
                                    O_Category.strip().upper() in ("CALL", "PUT")
                                    and O_InvestorType.strip().upper() == "OPTIONS"
                                ):
                                    if (
                                        O_Quantity != ""
                                        and O_Quantity != "0"
                                        and O_Rate != ""
                                    ):
                                        order = Order(
                                            user=uid,
                                            OrderGroup_id=gid,
                                            OrderIPOName=IPOName,
                                            InvestorType="OPTIONS",
                                            OrderCategory=O_Category.strip().upper(),
                                            OrderType="SELL",
                                            Quantity=O_Quantity,
                                            Rate=O_Rate,
                                            OrderDate=O_Date,
                                            OrderTime=O_Time,
                                            Method=O_StrikePrice,
                                        )

                                        O_limit = CustomUser.objects.get(username=user)
                                        if O_limit.Premium_Order_limit is not None:
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(
                                                user=user,
                                                OrderIPOName_id=IPOid,
                                                OrderCategory=Order_type,
                                            ).aggregate(Sum("Quantity"))[
                                                "Quantity__sum"
                                            ]
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit = int(O_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(
                                                    request,
                                                    f"You have reached the limit of {Limit} Order.",
                                                )
                                                return redirect(f"/{IPOid}/BUY")

                                        order.save()

                                else:
                                    column.append("Error")
                                    messages.error(
                                        request,
                                        f"Row {column} has error.",
                                        extra_tags="error",
                                    )
                        except:
                            column.append("Error")
                            messages.error(
                                request, f"Row {column} has error.", extra_tags="error"
                            )
                    else:
                        column.append("Error")
                        messages.error(
                            request, f"Row {column} has error.", extra_tags="error"
                        )
                else:
                    column.append("Error")
                    messages.error(
                        request, "File Details are invaild.", extra_tags="error"
                    )

        except:
            column.append("Error")
            messages.error(request, "File Details are invaild.", extra_tags="error")
        calculate(IPOid, request.user)

    return redirect(
        f"/{IPOid}/Order/{Groupfilter}/{Ordercatagoryfilter}/{InvestorTypefilter}"
    )


# dashboard form fun
@allowed_users(allowed_roles=["Broker"])
def dashboardform(request, IPOid, value):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    if IPOName.IPOType == "SME":
        if request.method == "POST":
            ExpecetdRetailApplication = request.POST.get(
                "ExpecetdRetailApplication", ""
            )
            ProfitMargin = request.POST.get("ProfitMargin", "")
            Premium = request.POST.get("Premium", "")
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            o_IPO = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid
            )
            if ExpecetdRetailApplication != "":
                IPO.ExpecetdRetailApplication = ExpecetdRetailApplication
            if ProfitMargin != "":
                IPO.ProfitMargin = ProfitMargin
            if Premium != "":
                if value == "A" or value == "B":
                    IPO.Premium = Premium
                if value == "C":
                    IPO.PreOpenPrice = Premium
                    o_IPO.update(PreOpenPrice=Premium)
            IPO.save()
            if value == "A":
                return redirect(f"/{IPOid}/Dashboard/A")
            if value == "B":
                return redirect(f"/{IPOid}/Dashboard/B")
            if value == "C":
                calculate(IPOid, request.user)
                return redirect(f"/{IPOid}/Dashboard/C")
        return redirect(f"/{IPOid}/Dashboard/A")

    else:
        if request.method == "POST":
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            o_IPO = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid
            )

            if value == "A":
                ExpecetdRetailApplication = request.POST.get(
                    "ExpecetdRetailApplication", ""
                )
                ExpecetdSHNIApplication = request.POST.get(
                    "ExpecetdSHNIApplication", ""
                )
                ExpecetdBHNIApplication = request.POST.get(
                    "ExpecetdBHNIApplication", ""
                )

                if ExpecetdRetailApplication != "":
                    IPO.ExpecetdRetailApplication = ExpecetdRetailApplication

                if ExpecetdSHNIApplication != "":
                    IPO.ExpecetdSHNIApplication = ExpecetdSHNIApplication
                else:
                    IPO.ExpecetdSHNIApplication = None

                if ExpecetdBHNIApplication != "":
                    IPO.ExpecetdBHNIApplication = ExpecetdBHNIApplication
                else:
                    IPO.ExpecetdBHNIApplication = None

            ProfitMargin = request.POST.get("ProfitMargin", "")

            Premium = request.POST.get("Premium", "")

            if ProfitMargin != "":
                IPO.ProfitMargin = ProfitMargin
            if Premium != "":
                if value == "A" or value == "B":
                    IPO.Premium = Premium
                if value == "C":
                    IPO.PreOpenPrice = Premium
                    o_IPO.update(PreOpenPrice=Premium)
            IPO.save()
            if value == "A":
                return redirect(f"/{IPOid}/Dashboard/A")
            if value == "B":
                return redirect(f"/{IPOid}/Dashboard/B")
            if value == "C":
                calculate(IPOid, request.user)
                return redirect(f"/{IPOid}/Dashboard/C")
        return redirect(f"/{IPOid}/Dashboard/A")


# dashboard fun
@allowed_users(allowed_roles=["Broker"])
def dashboard(request, IPOid, value):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    if IPOName.IPOType == "SME":

        if value == "B":
            ActualallottedQtyBuy = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType="BUY"
            ).aggregate(Sum("AllotedQty"))
            ActualallottedQtyBuy = ActualallottedQtyBuy["AllotedQty__sum"]

            if ActualallottedQtyBuy is None:
                ActualallottedQtyBuy = 0

            ActualallottedQtySell = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType="SELL"
            ).aggregate(Sum("AllotedQty"))
            ActualallottedQtySell = ActualallottedQtySell["AllotedQty__sum"]

            if ActualallottedQtySell is None:
                ActualallottedQtySell = 0

            ActualallottedQty = ActualallottedQtyBuy - ActualallottedQtySell

            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            try:
                IPOPremium = float(IPO.Premium)
                if IPOPremium is None:
                    IPOPremium = 0
            except:
                IPOPremium = 0
            if IPO.ProfitMargin is None:
                IPO.ProfitMargin = 15
            IPO.save()
            try:
                LotValue = float(IPO.IPOPrice) * float(IPO.LotSizeRetail)
                RetailSize = (
                    (float(IPO.TotalIPOSzie)) * float(IPO.RetailPercentage)
                ) / 100
                ApplicationFor1Time = (float(RetailSize) * 10000000) / LotValue
            except:
                LotValue = 0
                RetailSize = 0
                ApplicationFor1Time = 0
            try:
                ProfitMargin = float(IPO.ProfitMargin)
            except:
                ProfitMargin = None
            try:
                ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
            except:
                ExpecetdRetailApplication = None
            try:
                NumberOfTimeIPO = ExpecetdRetailApplication / ApplicationFor1Time
            except:
                NumberOfTimeIPO = 0
            try:
                AvgShare = float(IPO.LotSizeRetail) / NumberOfTimeIPO
            except:
                AvgShare = 0
            if AvgShare > IPO.LotSizeRetail:
                AvgShare = IPO.LotSizeRetail
            try:
                BaseKostakRate = float(IPOPremium) * AvgShare
            except:
                BaseKostakRate = 0
            try:
                kostakRateForCustomer = BaseKostakRate - (
                    (BaseKostakRate * float(IPO.ProfitMargin)) / 100
                )
            except:
                kostakRateForCustomer = 0
            try:
                BaseSubjectToRate = float(IPOPremium) * float(IPO.LotSizeRetail)
            except:
                BaseSubjectToRate = 0
            try:
                SubjectToRateForCustomer = BaseSubjectToRate - (
                    (BaseSubjectToRate * float(IPO.ProfitMargin)) / 100
                )
            except:
                SubjectToRateForCustomer = 0

            # ShareSellAgainestKostak = AvgShare * noofkostakapplication
            order = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
            Kostakentry = order.filter(OrderCategory="Kostak")
            NOBUYKostak = Kostakentry.filter(OrderType="BUY")
            NOBUYKostak11 = NOBUYKostak.aggregate(Sum("Quantity"))
            NOBUYKostak1 = NOBUYKostak11["Quantity__sum"]
            if NOBUYKostak1 is None:
                CountofBUYKostak = 0
            else:
                CountofBUYKostak = NOBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            NOSELLKostak = Kostakentry.filter(OrderType="SELL")
            NOSELLKostak11 = NOSELLKostak.aggregate(Sum("Quantity"))
            NOSELLKostak1 = NOSELLKostak11["Quantity__sum"]
            if NOSELLKostak1 is None:
                CountofSELLKostak = 0
            else:
                CountofSELLKostak = NOSELLKostak1

            try:
                CountOfKostak = CountofBUYKostak - CountofSELLKostak
            except:
                CountOfKostak = 0

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountBUYKostak = Kostakentry.filter(OrderType="BUY")
            AmountBUYKostak11 = AmountBUYKostak.aggregate(Sum("Amount"))
            AmountBUYKostak1 = AmountBUYKostak11["Amount__sum"]
            if AmountBUYKostak1 is None:
                AmountofBUYKostak = 0
            else:
                AmountofBUYKostak = AmountBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountSELLKostak = Kostakentry.filter(OrderType="SELL")
            AmountSELLKostak11 = AmountSELLKostak.aggregate(Sum("Amount"))
            AmountSELLKostak1 = AmountSELLKostak11["Amount__sum"]
            if AmountSELLKostak1 is None:
                AmountofSELLKostak = 0
            else:
                AmountofSELLKostak = AmountSELLKostak1
            try:
                TotalKostakValue = AmountofBUYKostak + AmountofSELLKostak
            except:
                TotalKostakValue = 0
            try:
                KostakAvg = float(TotalKostakValue) / float(CountOfKostak)
            except:
                KostakAvg = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum("Quantity"))
            NOBUYSubjectTo1 = NOBUYSubjectTo11["Quantity__sum"]
            if NOBUYSubjectTo1 is None:
                CountofBUYSubjectTo = 0
            else:
                CountofBUYSubjectTo = NOBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum("Quantity"))
            NOSELLSubjectTo1 = NOSELLSubjectTo11["Quantity__sum"]
            if NOSELLSubjectTo1 is None:
                CountofSELLSubjectTo = 0
            else:
                CountofSELLSubjectTo = NOSELLSubjectTo1

            try:
                CountOfSubjectTo = CountofBUYSubjectTo - CountofSELLSubjectTo
            except:
                CountOfSubjectTo = 0

            try:
                TotalApplication = CountOfKostak + CountOfSubjectTo
            except:
                TotalApplication = 0
            try:
                ShareTOBeSell = AvgShare * TotalApplication
            except:
                ShareTOBeSell = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            AmountBUYSubjectTo11 = AmountBUYSubjectTo.aggregate(Sum("Amount"))
            AmountBUYSubjectTo1 = AmountBUYSubjectTo11["Amount__sum"]
            if AmountBUYSubjectTo1 is None:
                AmountofBUYSubjectTo = 0
            else:
                AmountofBUYSubjectTo = AmountBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            AmountSELLSubjectTo11 = AmountSELLSubjectTo.aggregate(Sum("Amount"))
            AmountSELLSubjectTo1 = AmountSELLSubjectTo11["Amount__sum"]
            if AmountSELLSubjectTo1 is None:
                AmountofSELLSubjectTo = 0
            else:
                AmountofSELLSubjectTo = AmountSELLSubjectTo1

            try:
                TotalSubjectToValue = AmountofBUYSubjectTo + AmountofSELLSubjectTo
            except:
                TotalSubjectToValue = 0
            try:

                SubjectToAvg = float(TotalSubjectToValue) / float(CountOfSubjectTo)
            except:
                SubjectToAvg = 0
            TotalCount = CountOfSubjectTo + CountOfKostak

            KostakShareQty = ActualallottedQty

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYBUYPremium = Premiumentry.filter(OrderType="BUY")
            QTYBUYPremium11 = QTYBUYPremium.aggregate(Sum("Quantity"))
            QTYBUYPremium1 = QTYBUYPremium11["Quantity__sum"]
            if QTYBUYPremium1 is None:
                TotalBuyPremiumShareQty = 0
            else:
                TotalBuyPremiumShareQty = QTYBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYSELLPremium = Premiumentry.filter(OrderType="SELL")
            QTYSELLPremium11 = QTYSELLPremium.aggregate(Sum("Quantity"))
            QTYSELLPremium1 = QTYSELLPremium11["Quantity__sum"]
            if QTYSELLPremium1 is None:
                TotalSellPremiumShareQty = 0
            else:
                TotalSellPremiumShareQty = QTYSELLPremium1
            try:
                n1 = (KostakAvg / AvgShare) / 2
                n2 = (SubjectToAvg / float(IPO.LotSizeRetail)) / 2
                KostakShareAvg = n1 + n2
            except:
                KostakShareAvg = 0

            try:
                CountOfPremium = TotalBuyPremiumShareQty - TotalSellPremiumShareQty
            except:
                CountOfPremium = 0

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountBUYPremium = Premiumentry.filter(OrderType="BUY")
            AmountBUYPremium11 = AmountBUYPremium.aggregate(Sum("Amount"))
            AmountBUYPremium1 = AmountBUYPremium11["Amount__sum"]
            if AmountBUYPremium1 is None:
                TotalBuyPremiumShareAmount = 0
            else:
                TotalBuyPremiumShareAmount = AmountBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountSELLPremium = Premiumentry.filter(OrderType="SELL")
            AmountSELLPremium11 = AmountSELLPremium.aggregate(Sum("Amount"))
            AmountSELLPremium1 = AmountSELLPremium11["Amount__sum"]
            if AmountSELLPremium1 is None:
                TotalSellPremiumShareAmount = 0
            else:
                TotalSellPremiumShareAmount = AmountSELLPremium1
            try:
                BuyPremiumShareAvg = float(TotalBuyPremiumShareAmount) / float(
                    TotalBuyPremiumShareQty
                )
            except:
                BuyPremiumShareAvg = 0
            try:
                SellPremiumShareAvg = float(TotalSellPremiumShareAmount) / float(
                    TotalSellPremiumShareQty
                )
            except:
                SellPremiumShareAvg = 0
            try:
                DiffereneQty = (TotalBuyPremiumShareQty + KostakShareQty) - float(
                    TotalSellPremiumShareQty
                )
            except:
                DiffereneQty = 0
            try:
                ProfitOrLoss = (
                    (SellPremiumShareAvg * TotalSellPremiumShareQty)
                    - (
                        (KostakShareQty * KostakShareAvg)
                        + (TotalBuyPremiumShareQty * BuyPremiumShareAvg)
                    )
                    + DiffereneQty * float(IPOPremium)
                )
            except:
                ProfitOrLoss = 0
            return render(
                request,
                "Bdashboard_sme.html",
                {
                    "ActualallottedQty": "{:.2f}".format(ActualallottedQty),
                    "ActualallottedQtyBuy": "{:.2f}".format(ActualallottedQtyBuy),
                    "ActualallottedQtySell": "{:.2f}".format(ActualallottedQtySell),
                    "CountofBUYKostak": "{:.2f}".format(CountofBUYKostak),
                    "CountofSELLKostak": "{:.2f}".format(CountofSELLKostak),
                    "CountOfKostak": "{:.2f}".format(CountOfKostak),
                    "KostakAvg": "{:.2f}".format(KostakAvg),
                    "CountofBUYSubjectTo": "{:.2f}".format(CountofBUYSubjectTo),
                    "CountofSELLSubjectTo": "{:.2f}".format(CountofSELLSubjectTo),
                    "CountOfSubjectTo": "{:.2f}".format(CountOfSubjectTo),
                    "SubjectToAvg": "{:.2f}".format(SubjectToAvg),
                    "KostakShareQty": "{:.2f}".format(KostakShareQty),
                    "TotalBuyPremiumShareQty": "{:.2f}".format(TotalBuyPremiumShareQty),
                    "TotalSellPremiumShareQty": "{:.2f}".format(
                        TotalSellPremiumShareQty
                    ),
                    "CountOfPremium": "{:.2f}".format(CountOfPremium),
                    "IPOName": IPO,
                    "IPOid": IPOid,
                    "BaseSubjectToRate": "{:.2f}".format(BaseSubjectToRate),
                    "SubjectToRateForCustomer": "{:.2f}".format(
                        SubjectToRateForCustomer
                    ),
                    "ProfitMargin": ProfitMargin,
                    "Premium": IPOPremium,
                    "KostakShareAvg": "{:.2f}".format(KostakShareAvg),
                    "BuyPremiumShareAvg": "{:.2f}".format(BuyPremiumShareAvg),
                    "SellPremiumShareAvg": "{:.2f}".format(SellPremiumShareAvg),
                    "DiffereneQty": "{:.2f}".format(DiffereneQty),
                    "ProfitOrLoss": "{:.0f}".format(ProfitOrLoss),
                },
            )
        if value == "C":

            products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)

            ActualallottedQtyBuy = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType="BUY"
            ).aggregate(Sum("AllotedQty"))
            ActualallottedQtyBuy = ActualallottedQtyBuy["AllotedQty__sum"]

            if ActualallottedQtyBuy is None:
                ActualallottedQtyBuy = 0

            ActualallottedQtySell = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType="SELL"
            ).aggregate(Sum("AllotedQty"))
            ActualallottedQtySell = ActualallottedQtySell["AllotedQty__sum"]

            if ActualallottedQtySell is None:
                ActualallottedQtySell = 0

            ActualallottedQty = ActualallottedQtyBuy - ActualallottedQtySell

            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            try:
                IPOPremium = float(IPO.Premium)
            except:
                IPOPremium = 0
            if IPO.ProfitMargin is None:
                IPO.ProfitMargin = 15
            if IPO.ExpecetdRetailApplication is None:
                IPO.ExpecetdRetailApplication = 2500000
            IPO.save()
            try:
                LotValue = float(IPO.IPOPrice) * float(IPO.LotSizeRetail)
                RetailSize = (
                    (float(IPO.TotalIPOSzie)) * float(IPO.RetailPercentage)
                ) / 100
                ApplicationFor1Time = (float(RetailSize) * 10000000) / LotValue
            except:
                LotValue = 0
                RetailSize = 0
                ApplicationFor1Time = 0
            try:
                ProfitMargin = float(IPO.ProfitMargin)
            except:
                ProfitMargin = None
            try:
                ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
            except:
                ExpecetdRetailApplication = None
            try:
                NumberOfTimeIPO = ExpecetdRetailApplication / ApplicationFor1Time
            except:
                NumberOfTimeIPO = 0
            try:
                AvgShare = float(IPO.LotSizeRetail) / NumberOfTimeIPO
            except:
                AvgShare = 0
            if AvgShare > IPO.LotSizeRetail:
                AvgShare = IPO.LotSizeRetail
            try:
                BaseKostakRate = float(IPOPremium) * AvgShare
            except:
                BaseKostakRate = 0
            try:
                kostakRateForCustomer = BaseKostakRate - (
                    (BaseKostakRate * float(IPO.ProfitMargin)) / 100
                )
            except:
                kostakRateForCustomer = 0
            try:
                BaseSubjectToRate = float(IPOPremium) * float(IPO.LotSizeRetail)
            except:
                BaseSubjectToRate = 0
            try:
                SubjectToRateForCustomer = BaseSubjectToRate - (
                    (BaseSubjectToRate * float(IPO.ProfitMargin)) / 100
                )
            except:
                SubjectToRateForCustomer = 0

            order = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
            Kostakentry = order.filter(OrderCategory="Kostak")
            NOBUYKostak = Kostakentry.filter(OrderType="BUY")
            NOBUYKostak11 = NOBUYKostak.aggregate(Sum("Quantity"))
            NOBUYKostak1 = NOBUYKostak11["Quantity__sum"]
            if NOBUYKostak1 is None:
                CountofBUYKostak = 0
            else:
                CountofBUYKostak = NOBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            NOSELLKostak = Kostakentry.filter(OrderType="SELL")
            NOSELLKostak11 = NOSELLKostak.aggregate(Sum("Quantity"))
            NOSELLKostak1 = NOSELLKostak11["Quantity__sum"]
            if NOSELLKostak1 is None:
                CountofSELLKostak = 0
            else:
                CountofSELLKostak = NOSELLKostak1

            try:
                CountOfKostak = CountofBUYKostak - CountofSELLKostak
            except:
                CountOfKostak = 0

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountBUYKostak = Kostakentry.filter(OrderType="BUY")
            AmountBUYKostak11 = AmountBUYKostak.aggregate(Sum("Amount"))
            AmountBUYKostak1 = AmountBUYKostak11["Amount__sum"]
            if AmountBUYKostak1 is None:
                AmountofBUYKostak = 0
            else:
                AmountofBUYKostak = AmountBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountSELLKostak = Kostakentry.filter(OrderType="SELL")
            AmountSELLKostak11 = AmountSELLKostak.aggregate(Sum("Amount"))
            AmountSELLKostak1 = AmountSELLKostak11["Amount__sum"]
            if AmountSELLKostak1 is None:
                AmountofSELLKostak = 0
            else:
                AmountofSELLKostak = AmountSELLKostak1
            try:
                TotalKostakValue = AmountofBUYKostak + AmountofSELLKostak
            except:
                TotalKostakValue = 0
            try:
                KostakAvg = float(TotalKostakValue) / float(CountOfKostak)
            except:
                KostakAvg = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum("Quantity"))
            NOBUYSubjectTo1 = NOBUYSubjectTo11["Quantity__sum"]
            if NOBUYSubjectTo1 is None:
                CountofBUYSubjectTo = 0
            else:
                CountofBUYSubjectTo = NOBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum("Quantity"))
            NOSELLSubjectTo1 = NOSELLSubjectTo11["Quantity__sum"]
            if NOSELLSubjectTo1 is None:
                CountofSELLSubjectTo = 0
            else:
                CountofSELLSubjectTo = NOSELLSubjectTo1

            try:
                CountOfSubjectTo = CountofBUYSubjectTo - CountofSELLSubjectTo
            except:
                CountOfSubjectTo = 0

            try:
                TotalApplication = CountOfKostak + CountOfSubjectTo
            except:
                TotalApplication = 0
            try:
                ShareTOBeSell = AvgShare * TotalApplication
            except:
                ShareTOBeSell = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            AmountBUYSubjectTo11 = AmountBUYSubjectTo.aggregate(Sum("Amount"))
            AmountBUYSubjectTo1 = AmountBUYSubjectTo11["Amount__sum"]
            if AmountBUYSubjectTo1 is None:
                AmountofBUYSubjectTo = 0
            else:
                AmountofBUYSubjectTo = AmountBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            AmountSELLSubjectTo11 = AmountSELLSubjectTo.aggregate(Sum("Amount"))
            AmountSELLSubjectTo1 = AmountSELLSubjectTo11["Amount__sum"]
            if AmountSELLSubjectTo1 is None:
                AmountofSELLSubjectTo = 0
            else:
                AmountofSELLSubjectTo = AmountSELLSubjectTo1

            try:
                TotalSubjectToValue = AmountofBUYSubjectTo + AmountofSELLSubjectTo
            except:
                TotalSubjectToValue = 0
            try:

                SubjectToAvg = float(TotalSubjectToValue) / float(CountOfSubjectTo)
            except:
                SubjectToAvg = 0
            TotalCount = CountOfSubjectTo + CountOfKostak

            KostakShareQty = ActualallottedQty

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYBUYPremium = Premiumentry.filter(OrderType="BUY")
            QTYBUYPremium11 = QTYBUYPremium.aggregate(Sum("Quantity"))
            QTYBUYPremium1 = QTYBUYPremium11["Quantity__sum"]
            if QTYBUYPremium1 is None:
                TotalBuyPremiumShareQty = 0
            else:
                TotalBuyPremiumShareQty = QTYBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYSELLPremium = Premiumentry.filter(OrderType="SELL")
            QTYSELLPremium11 = QTYSELLPremium.aggregate(Sum("Quantity"))
            QTYSELLPremium1 = QTYSELLPremium11["Quantity__sum"]
            if QTYSELLPremium1 is None:
                TotalSellPremiumShareQty = 0
            else:
                TotalSellPremiumShareQty = QTYSELLPremium1
            try:
                n1 = (KostakAvg / AvgShare) / 2
                n2 = (SubjectToAvg / float(IPO.LotSizeRetail)) / 2
                KostakShareAvg = n1 + n2
            except:
                KostakShareAvg = 0
            try:
                CountOfPremium = TotalBuyPremiumShareQty - TotalSellPremiumShareQty
            except:
                CountOfPremium = 0

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountBUYPremium = Premiumentry.filter(OrderType="BUY")
            AmountBUYPremium11 = AmountBUYPremium.aggregate(Sum("Amount"))
            AmountBUYPremium1 = AmountBUYPremium11["Amount__sum"]
            if AmountBUYPremium1 is None:
                TotalBuyPremiumShareAmount = 0
            else:
                TotalBuyPremiumShareAmount = AmountBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountSELLPremium = Premiumentry.filter(OrderType="SELL")
            AmountSELLPremium11 = AmountSELLPremium.aggregate(Sum("Amount"))
            AmountSELLPremium1 = AmountSELLPremium11["Amount__sum"]
            if AmountSELLPremium1 is None:
                TotalSellPremiumShareAmount = 0
            else:
                TotalSellPremiumShareAmount = AmountSELLPremium1
            try:
                BuyPremiumShareAvg = float(TotalBuyPremiumShareAmount) / float(
                    TotalBuyPremiumShareQty
                )
            except:
                BuyPremiumShareAvg = 0
            try:
                SellPremiumShareAvg = float(TotalSellPremiumShareAmount) / float(
                    TotalSellPremiumShareQty
                )
            except:
                SellPremiumShareAvg = 0
            try:
                DiffereneQty = (TotalBuyPremiumShareQty + KostakShareQty) - float(
                    TotalSellPremiumShareQty
                )
            except:
                DiffereneQty = 0
            try:
                Amountsum = products.aggregate(Sum("Amount"))["Amount__sum"]
                ProfitOrLoss = float(Amountsum)
            except:
                ProfitOrLoss = 0
            return render(
                request,
                "Cdashboard_sme.html",
                {
                    "ActualallottedQty": "{:.2f}".format(ActualallottedQty),
                    "ActualallottedQtyBuy": "{:.2f}".format(ActualallottedQtyBuy),
                    "ActualallottedQtySell": "{:.2f}".format(ActualallottedQtySell),
                    "CountofBUYKostak": "{:.2f}".format(CountofBUYKostak),
                    "CountofSELLKostak": "{:.2f}".format(CountofSELLKostak),
                    "CountOfKostak": "{:.2f}".format(CountOfKostak),
                    "KostakAvg": "{:.2f}".format(KostakAvg),
                    "CountofBUYSubjectTo": "{:.2f}".format(CountofBUYSubjectTo),
                    "CountofSELLSubjectTo": "{:.2f}".format(CountofSELLSubjectTo),
                    "CountOfSubjectTo": "{:.2f}".format(CountOfSubjectTo),
                    "SubjectToAvg": "{:.2f}".format(SubjectToAvg),
                    "KostakShareQty": "{:.2f}".format(KostakShareQty),
                    "TotalBuyPremiumShareQty": "{:.2f}".format(TotalBuyPremiumShareQty),
                    "TotalSellPremiumShareQty": "{:.2f}".format(
                        TotalSellPremiumShareQty
                    ),
                    "CountOfPremium": "{:.2f}".format(CountOfPremium),
                    "IPOName": IPO,
                    "IPOid": IPOid,
                    "Premium": IPO.Premium,
                    "KostakShareAvg": "{:.2f}".format(KostakShareAvg),
                    "BuyPremiumShareAvg": "{:.2f}".format(BuyPremiumShareAvg),
                    "SellPremiumShareAvg": "{:.2f}".format(SellPremiumShareAvg),
                    "DiffereneQty": "{:.2f}".format(DiffereneQty),
                    "ProfitOrLoss": "{:.0f}".format(ProfitOrLoss),
                },
            )

        IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        try:
            IPOPremium = float(IPO.Premium)
        except:
            IPOPremium = 0
        if IPO.ProfitMargin is None:
            IPO.ProfitMargin = 15
        if IPO.ExpecetdRetailApplication is None:
            IPO.ExpecetdRetailApplication = 2500000
        IPO.save()
        try:
            LotValue = float(IPO.IPOPrice) * float(IPO.LotSizeRetail)
            RetailSize = ((float(IPO.TotalIPOSzie)) * float(IPO.RetailPercentage)) / 100
            ApplicationFor1Time = (float(RetailSize) * 10000000) / LotValue
        except:
            LotValue = 0
            RetailSize = 0
            ApplicationFor1Time = 0
        try:
            ProfitMargin = float(IPO.ProfitMargin)
        except:
            ProfitMargin = None
        try:
            ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
        except:
            ExpecetdRetailApplication = None
        try:
            NumberOfTimeIPO = ExpecetdRetailApplication / ApplicationFor1Time
        except:
            NumberOfTimeIPO = 0
        try:
            AvgShare = float(IPO.LotSizeRetail) / NumberOfTimeIPO
        except:
            AvgShare = 0
        if AvgShare > IPO.LotSizeRetail:
            AvgShare = IPO.LotSizeRetail
        try:
            BaseKostakRate = float(IPOPremium) * AvgShare
        except:
            BaseKostakRate = 0
        try:
            kostakRateForCustomer = BaseKostakRate - (
                (BaseKostakRate * float(IPO.ProfitMargin)) / 100
            )
        except:
            kostakRateForCustomer = 0
        try:
            BaseSubjectToRate = float(IPOPremium) * float(IPO.LotSizeRetail)
        except:
            BaseSubjectToRate = 0
        try:
            SubjectToRateForCustomer = BaseSubjectToRate - (
                (BaseSubjectToRate * float(IPO.ProfitMargin)) / 100
            )
        except:
            SubjectToRateForCustomer = 0

        order = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
        Kostakentry = order.filter(OrderCategory="Kostak")
        NOBUYKostak = Kostakentry.filter(OrderType="BUY")
        NOBUYKostak11 = NOBUYKostak.aggregate(Sum("Quantity"))
        NOBUYKostak1 = NOBUYKostak11["Quantity__sum"]
        if NOBUYKostak1 is None:
            CountofBUYKostak = 0
        else:
            CountofBUYKostak = NOBUYKostak1

        Kostakentry = order.filter(OrderCategory="Kostak")
        NOSELLKostak = Kostakentry.filter(OrderType="SELL")
        NOSELLKostak11 = NOSELLKostak.aggregate(Sum("Quantity"))
        NOSELLKostak1 = NOSELLKostak11["Quantity__sum"]
        if NOSELLKostak1 is None:
            CountofSELLKostak = 0
        else:
            CountofSELLKostak = NOSELLKostak1

        try:
            CountOfKostak = CountofBUYKostak - CountofSELLKostak
        except:
            CountOfKostak = 0

        Kostakentry = order.filter(OrderCategory="Kostak")
        AmountBUYKostak = Kostakentry.filter(OrderType="BUY")
        AmountBUYKostak11 = AmountBUYKostak.aggregate(Sum("Amount"))
        AmountBUYKostak1 = AmountBUYKostak11["Amount__sum"]
        if AmountBUYKostak1 is None:
            AmountofBUYKostak = 0
        else:
            AmountofBUYKostak = AmountBUYKostak1

        Kostakentry = order.filter(OrderCategory="Kostak")
        AmountSELLKostak = Kostakentry.filter(OrderType="SELL")
        AmountSELLKostak11 = AmountSELLKostak.aggregate(Sum("Amount"))
        AmountSELLKostak1 = AmountSELLKostak11["Amount__sum"]
        if AmountSELLKostak1 is None:
            AmountofSELLKostak = 0
        else:
            AmountofSELLKostak = AmountSELLKostak1
        try:
            TotalKostakValue = AmountofBUYKostak + AmountofSELLKostak
        except:
            TotalKostakValue = 0
        try:
            KostakAvg = float(TotalKostakValue) / float(CountOfKostak)
        except:
            KostakAvg = 0

        SubjectToentry = order.filter(OrderCategory="Subject To")
        NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
        NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum("Quantity"))
        NOBUYSubjectTo1 = NOBUYSubjectTo11["Quantity__sum"]
        if NOBUYSubjectTo1 is None:
            CountofBUYSubjectTo = 0
        else:
            CountofBUYSubjectTo = NOBUYSubjectTo1

        SubjectToentry = order.filter(OrderCategory="Subject To")
        NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
        NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum("Quantity"))
        NOSELLSubjectTo1 = NOSELLSubjectTo11["Quantity__sum"]
        if NOSELLSubjectTo1 is None:
            CountofSELLSubjectTo = 0
        else:
            CountofSELLSubjectTo = NOSELLSubjectTo1

        try:
            CountOfSubjectTo = CountofBUYSubjectTo - CountofSELLSubjectTo
        except:
            CountOfSubjectTo = 0

        try:
            TotalApplication = CountOfKostak + CountOfSubjectTo
        except:
            TotalApplication = 0
        try:
            ShareTOBeSell = AvgShare * TotalApplication
        except:
            ShareTOBeSell = 0

        SubjectToentry = order.filter(OrderCategory="Subject To")
        AmountBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
        AmountBUYSubjectTo11 = AmountBUYSubjectTo.aggregate(Sum("Amount"))
        AmountBUYSubjectTo1 = AmountBUYSubjectTo11["Amount__sum"]
        if AmountBUYSubjectTo1 is None:
            AmountofBUYSubjectTo = 0
        else:
            AmountofBUYSubjectTo = AmountBUYSubjectTo1

        SubjectToentry = order.filter(OrderCategory="Subject To")
        AmountSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
        AmountSELLSubjectTo11 = AmountSELLSubjectTo.aggregate(Sum("Amount"))
        AmountSELLSubjectTo1 = AmountSELLSubjectTo11["Amount__sum"]
        if AmountSELLSubjectTo1 is None:
            AmountofSELLSubjectTo = 0
        else:
            AmountofSELLSubjectTo = AmountSELLSubjectTo1

        try:
            TotalSubjectToValue = AmountofBUYSubjectTo + AmountofSELLSubjectTo
        except:
            TotalSubjectToValue = 0
        try:

            SubjectToAvg = float(TotalSubjectToValue) / float(CountOfSubjectTo)
        except:
            SubjectToAvg = 0
        TotalCount = CountOfSubjectTo + CountOfKostak

        KostakShareQty = TotalCount * AvgShare

        Premiumentry = order.filter(OrderCategory="Premium")
        QTYBUYPremium = Premiumentry.filter(OrderType="BUY")
        QTYBUYPremium11 = QTYBUYPremium.aggregate(Sum("Quantity"))
        QTYBUYPremium1 = QTYBUYPremium11["Quantity__sum"]
        if QTYBUYPremium1 is None:
            TotalBuyPremiumShareQty = 0
        else:
            TotalBuyPremiumShareQty = QTYBUYPremium1

        Premiumentry = order.filter(OrderCategory="Premium")
        QTYSELLPremium = Premiumentry.filter(OrderType="SELL")
        QTYSELLPremium11 = QTYSELLPremium.aggregate(Sum("Quantity"))
        QTYSELLPremium1 = QTYSELLPremium11["Quantity__sum"]
        if QTYSELLPremium1 is None:
            TotalSellPremiumShareQty = 0
        else:
            TotalSellPremiumShareQty = QTYSELLPremium1
        try:
            n1 = (KostakAvg / AvgShare) / 2
            n2 = (SubjectToAvg / float(IPO.LotSizeRetail)) / 2
            KostakShareAvg = n1 + n2
        except:
            KostakShareAvg = 0

        try:
            CountOfPremium = TotalBuyPremiumShareQty - TotalSellPremiumShareQty
        except:
            CountOfPremium = 0

        Premiumentry = order.filter(OrderCategory="Premium")
        AmountBUYPremium = Premiumentry.filter(OrderType="BUY")
        AmountBUYPremium11 = AmountBUYPremium.aggregate(Sum("Amount"))
        AmountBUYPremium1 = AmountBUYPremium11["Amount__sum"]
        if AmountBUYPremium1 is None:
            TotalBuyPremiumShareAmount = 0
        else:
            TotalBuyPremiumShareAmount = AmountBUYPremium1

        Premiumentry = order.filter(OrderCategory="Premium")
        AmountSELLPremium = Premiumentry.filter(OrderType="SELL")
        AmountSELLPremium11 = AmountSELLPremium.aggregate(Sum("Amount"))
        AmountSELLPremium1 = AmountSELLPremium11["Amount__sum"]
        if AmountSELLPremium1 is None:
            TotalSellPremiumShareAmount = 0
        else:
            TotalSellPremiumShareAmount = AmountSELLPremium1
        try:
            BuyPremiumShareAvg = float(TotalBuyPremiumShareAmount) / float(
                TotalBuyPremiumShareQty
            )
        except:
            BuyPremiumShareAvg = 0
        try:
            SellPremiumShareAvg = float(TotalSellPremiumShareAmount) / float(
                TotalSellPremiumShareQty
            )
        except:
            SellPremiumShareAvg = 0
        try:
            DiffereneQty = (TotalBuyPremiumShareQty + KostakShareQty) - float(
                TotalSellPremiumShareQty
            )
        except:
            DiffereneQty = 0
        try:
            ProfitOrLoss = (
                (SellPremiumShareAvg * TotalSellPremiumShareQty)
                - (
                    (KostakShareQty * KostakShareAvg)
                    + (TotalBuyPremiumShareQty * BuyPremiumShareAvg)
                )
                + DiffereneQty * float(IPOPremium)
            )
        except:
            ProfitOrLoss = 0
        return render(
            request,
            "dashboard_sme.html",
            {
                "AvgShare": "{:.2f}".format(AvgShare),
                "NumberOfTimeIPO": "{:.2f}".format(NumberOfTimeIPO),
                "IpoPricePerShare": "{:.0f}".format(IPO.IPOPrice),
                "ApplicationFor1Time": "{:.0f}".format(ApplicationFor1Time),
                "CountofBUYKostak": "{:.2f}".format(CountofBUYKostak),
                "CountofSELLKostak": "{:.2f}".format(CountofSELLKostak),
                "CountOfKostak": "{:.2f}".format(CountOfKostak),
                "KostakAvg": "{:.2f}".format(KostakAvg),
                "CountofBUYSubjectTo": "{:.2f}".format(CountofBUYSubjectTo),
                "CountofSELLSubjectTo": "{:.2f}".format(CountofSELLSubjectTo),
                "CountOfSubjectTo": "{:.2f}".format(CountOfSubjectTo),
                "SubjectToAvg": "{:.2f}".format(SubjectToAvg),
                "KostakShareQty": "{:.2f}".format(KostakShareQty),
                "TotalBuyPremiumShareQty": "{:.2f}".format(TotalBuyPremiumShareQty),
                "TotalSellPremiumShareQty": "{:.2f}".format(TotalSellPremiumShareQty),
                "CountOfPremium": "{:.2f}".format(CountOfPremium),
                "IPOName": IPO,
                "IPOid": IPOid,
                "BaseKostakRate": "{:.2f}".format(BaseKostakRate),
                "kostakRateForCustomer": "{:.2f}".format(kostakRateForCustomer),
                "BaseSubjectToRate": "{:.2f}".format(BaseSubjectToRate),
                "SubjectToRateForCustomer": "{:.2f}".format(SubjectToRateForCustomer),
                "ExpecetdRetailApplication": ExpecetdRetailApplication,
                "ProfitMargin": ProfitMargin,
                "Premium": IPOPremium,
                "ShareTOBeSell": "{:.2f}".format(ShareTOBeSell),
                "KostakShareAvg": "{:.2f}".format(KostakShareAvg),
                "BuyPremiumShareAvg": "{:.2f}".format(BuyPremiumShareAvg),
                "SellPremiumShareAvg": "{:.2f}".format(SellPremiumShareAvg),
                "DiffereneQty": "{:.2f}".format(DiffereneQty),
                "ProfitOrLoss": "{:.0f}".format(ProfitOrLoss),
            },
        )

    else:
        if value == "B":

            retail = {}
            shni = {}
            bhni = {}

            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            try:
                IPOPremium = float(IPO.Premium)
                if IPOPremium is None:
                    IPOPremium = 0
            except:
                IPOPremium = 0
            if IPO.ProfitMargin is None:
                IPO.ProfitMargin = 15
            IPO.save()

            try:
                ProfitMargin = float(IPO.ProfitMargin)
            except:
                ProfitMargin = None

            try:
                Premium = float(IPO.Premium)
            except:
                Premium = None

            try:
                retail["BaseSubjectToRate"] = float(IPOPremium) * float(
                    IPO.LotSizeRetail
                )
                shni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeSHNI)
                bhni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeBHNI)
            except:
                retail["BaseSubjectToRate"] = 0
                shni["BaseSubjectToRate"] = 0
                bhni["BaseSubjectToRate"] = 0

            try:
                retail["SubjectToRateForCustomer"] = retail["BaseSubjectToRate"] - (
                    (retail["BaseSubjectToRate"] * float(IPO.ProfitMargin)) / 100
                )
                shni["SubjectToRateForCustomer"] = shni["BaseSubjectToRate"] - (
                    (shni["BaseSubjectToRate"] * float(IPO.ProfitMargin)) / 100
                )
                bhni["SubjectToRateForCustomer"] = bhni["BaseSubjectToRate"] - (
                    (bhni["BaseSubjectToRate"] * float(IPO.ProfitMargin)) / 100
                )
            except:
                retail["SubjectToRateForCustomer"] = 0
                shni["SubjectToRateForCustomer"] = 0
                bhni["SubjectToRateForCustomer"] = 0

            count = {}

            OrdCat = ["Kostak", "SubjectTo"]
            InvTyp = ["RETAIL", "SHNI", "BHNI"]
            OrdTyp = ["BUY", "SELL"]
            products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)

            for ordercategory in OrdCat:
                for investortype in InvTyp:
                    for ordertype in OrdTyp:
                        if ordercategory == "SubjectTo":
                            x = products.filter(
                                OrderType=ordertype,
                                OrderCategory="Subject To",
                                InvestorType=investortype,
                            )
                        else:
                            x = products.filter(
                                OrderType=ordertype,
                                OrderCategory=ordercategory,
                                InvestorType=investortype,
                            )

                        count1 = x.aggregate(Sum("Quantity"))["Quantity__sum"]

                        if count1 is None:
                            count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                        else:
                            count[f"{ordercategory}{investortype}{ordertype}Count"] = (
                                count1
                            )

                    count[f"{ordercategory}{investortype}Net"] = (
                        count[f"{ordercategory}{investortype}BUYCount"]
                        - count[f"{ordercategory}{investortype}SELLCount"]
                    )

            x = products.filter(OrderType="BUY", OrderCategory="Premium")

            PremiumBUY = x.aggregate(Sum("Quantity"))["Quantity__sum"]
            if PremiumBUY is None:
                count["PremiumBUYCount"] = 0
            else:
                count["PremiumBUYCount"] = PremiumBUY

            y = products.filter(OrderType="SELL", OrderCategory="Premium")

            PremiumSELL = y.aggregate(Sum("Quantity"))["Quantity__sum"]
            if PremiumSELL is None:
                count["PremiumSELLCount"] = 0
            else:
                count["PremiumSELLCount"] = PremiumSELL

            count["PremiumNet"] = count["PremiumBUYCount"] - count["PremiumSELLCount"]
            count["PremiumDiff"] = count["PremiumBUYCount"] - count["PremiumSELLCount"]

            shares = {}

            shares["SELLTotal"] = 0
            shares["BUYTotal"] = 0
            Qtyfilter = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid
            )
            for ordercategory in OrdCat:
                for investortype in InvTyp:
                    for ordertype in OrdTyp:
                        if ordercategory == "SubjectTo":
                            x = Qtyfilter.filter(
                                Order__OrderType=ordertype,
                                Order__InvestorType=investortype,
                                Order__OrderCategory="Subject To",
                            )
                        else:
                            x = Qtyfilter.filter(
                                Order__OrderType=ordertype,
                                Order__InvestorType=investortype,
                                Order__OrderCategory=ordercategory,
                            )

                        quantity = x.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

                        if quantity is None:
                            shares[
                                f"{ordercategory}{investortype}{ordertype}Shares"
                            ] = 0
                        else:
                            shares[
                                f"{ordercategory}{investortype}{ordertype}Shares"
                            ] = quantity

                    shares["BUYTotal"] = (
                        shares["BUYTotal"]
                        + shares[f"{ordercategory}{investortype}BUYShares"]
                    )
                    shares["SELLTotal"] = (
                        shares["SELLTotal"]
                        + shares[f"{ordercategory}{investortype}SELLShares"]
                    )
                    shares[f"{ordercategory}{investortype}Net"] = (
                        shares[f"{ordercategory}{investortype}BUYShares"]
                        - shares[f"{ordercategory}{investortype}SELLShares"]
                    )

            shares["Diff_Qty"] = (
                shares["BUYTotal"] - shares["SELLTotal"] + count["PremiumDiff"]
            )

            AmountSum = products.aggregate(Sum("Amount"))["Amount__sum"]
            if AmountSum is None:
                AmountSum = 0

            try:
                ExpectedProfitLoss = float(shares["Diff_Qty"]) * float(
                    IPO.Premium
                ) + float(AmountSum)
            except:
                ExpectedProfitLoss = 0

            # RETAIL
            y = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="RETAIL")
            qty = y.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty is None:
                shares["RETAILBUYAlloted"] = 0
            else:
                shares["RETAILBUYAlloted"] = qty

            z = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="RETAIL")
            qtys = z.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qtys is None:
                shares["RETAILSELLAlloted"] = 0
            else:
                shares["RETAILSELLAlloted"] = qtys

            shares["RETAILAlloted"] = (
                shares["RETAILBUYAlloted"] - shares["RETAILSELLAlloted"]
            )

            # SHNI
            y1 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="SHNI")
            qty = y1.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty is None:
                shares[f"SHNIBUYAlloted"] = 0
            else:
                shares[f"SHNIBUYAlloted"] = qty

            z1 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="SHNI")
            qty1s = z1.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty1s is None:
                shares[f"SHNISELLAlloted"] = 0
            else:
                shares[f"SHNISELLAlloted"] = qty1s

            shares["SHNIAlloted"] = shares["SHNIBUYAlloted"] - shares["SHNISELLAlloted"]

            # BHNI
            y2 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="BHNI")
            qty2 = y2.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty2 is None:
                shares[f"BHNIBUYAlloted"] = 0
            else:
                shares[f"BHNIBUYAlloted"] = qty2

            z2 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="BHNI")
            qty2s = z2.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty2s is None:
                shares[f"BHNISELLAlloted"] = 0
            else:
                shares[f"BHNISELLAlloted"] = qty2s

            shares["BHNIAlloted"] = shares["BHNIBUYAlloted"] - shares["BHNISELLAlloted"]

            shares["ALLOTED"] = (
                shares["RETAILAlloted"] + shares["SHNIAlloted"] + shares["BHNIAlloted"]
            )
            shares["ALLOTEDBUY"] = (
                shares["RETAILBUYAlloted"]
                + shares["SHNIBUYAlloted"]
                + shares["BHNIBUYAlloted"]
            )
            shares["ALLOTEDSELL"] = (
                shares["RETAILSELLAlloted"]
                + shares["SHNISELLAlloted"]
                + shares["BHNISELLAlloted"]
            )

            return render(
                request,
                "Bdashboard.html",
                {
                    "Premium": IPOPremium,
                    "ProfitMargin": ProfitMargin,
                    "retail": retail,
                    "shni": shni,
                    "bhni": bhni,
                    "ExpectedProfitLoss": ExpectedProfitLoss,
                    "shares": shares,
                    "count": count,
                    "IPOName": IPO,
                    "IPOid": IPOid,
                },
            )

        if value == "C":
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)

            retail = {}
            shni = {}
            bhni = {}
            count = {}

            OrdCat = ["Kostak", "SubjectTo"]
            InvTyp = ["RETAIL", "SHNI", "BHNI"]
            OrdTyp = ["BUY", "SELL"]
            products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)

            for ordercategory in OrdCat:
                for investortype in InvTyp:
                    for ordertype in OrdTyp:
                        if ordercategory == "SubjectTo":
                            x = products.filter(
                                OrderType=ordertype,
                                OrderCategory="Subject To",
                                InvestorType=investortype,
                            )
                        else:
                            x = products.filter(
                                OrderType=ordertype,
                                OrderCategory=ordercategory,
                                InvestorType=investortype,
                            )

                        count1 = x.aggregate(Sum("Quantity"))["Quantity__sum"]

                        if count1 is None:
                            count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                        else:
                            count[f"{ordercategory}{investortype}{ordertype}Count"] = (
                                count1
                            )

                    count[f"{ordercategory}{investortype}Net"] = (
                        count[f"{ordercategory}{investortype}BUYCount"]
                        - count[f"{ordercategory}{investortype}SELLCount"]
                    )

            x = products.filter(OrderType="BUY", OrderCategory="Premium")

            PremiumBUY = x.aggregate(Sum("Quantity"))["Quantity__sum"]
            if PremiumBUY is None:
                count["PremiumBUYCount"] = 0
            else:
                count["PremiumBUYCount"] = PremiumBUY

            y = products.filter(OrderType="SELL", OrderCategory="Premium")

            PremiumSELL = y.aggregate(Sum("Quantity"))["Quantity__sum"]
            if PremiumSELL is None:
                count["PremiumSELLCount"] = 0
            else:
                count["PremiumSELLCount"] = PremiumSELL

            count["PremiumNet"] = count["PremiumBUYCount"] - count["PremiumSELLCount"]
            count["PremiumDiff"] = count["PremiumBUYCount"] - count["PremiumSELLCount"]

            shares = {}

            shares["SELLTotal"] = 0
            shares["BUYTotal"] = 0
            Qtyfilter = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid
            )
            for ordercategory in OrdCat:
                for investortype in InvTyp:
                    for ordertype in OrdTyp:
                        if ordercategory == "SubjectTo":
                            x = Qtyfilter.filter(
                                Order__OrderType=ordertype,
                                Order__InvestorType=investortype,
                                Order__OrderCategory="Subject To",
                            )
                        else:
                            x = Qtyfilter.filter(
                                Order__OrderType=ordertype,
                                Order__InvestorType=investortype,
                                Order__OrderCategory=ordercategory,
                            )

                        quantity = x.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

                        if quantity is None:
                            shares[
                                f"{ordercategory}{investortype}{ordertype}Shares"
                            ] = 0
                        else:
                            shares[
                                f"{ordercategory}{investortype}{ordertype}Shares"
                            ] = quantity

                    shares["BUYTotal"] = (
                        shares["BUYTotal"]
                        + shares[f"{ordercategory}{investortype}BUYShares"]
                    )
                    shares["SELLTotal"] = (
                        shares["SELLTotal"]
                        + shares[f"{ordercategory}{investortype}SELLShares"]
                    )
                    shares[f"{ordercategory}{investortype}Net"] = (
                        shares[f"{ordercategory}{investortype}BUYShares"]
                        - shares[f"{ordercategory}{investortype}SELLShares"]
                    )

            shares["Diff_Qty"] = (
                shares["BUYTotal"] - shares["SELLTotal"] + count["PremiumDiff"]
            )

            AmountSum = products.aggregate(Sum("Amount"))["Amount__sum"]
            if AmountSum is None:
                AmountSum = 0

            try:
                ExpectedProfitLoss = float(AmountSum)
            except:
                ExpectedProfitLoss = 0

            # Alloted quantity Retail, shni, bhni
            # RETAIL
            y = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="RETAIL")
            qty = y.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty is None:
                shares["RETAILBUYAlloted"] = 0
            else:
                shares["RETAILBUYAlloted"] = qty

            z = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="RETAIL")
            qtys = z.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qtys is None:
                shares["RETAILSELLAlloted"] = 0
            else:
                shares["RETAILSELLAlloted"] = qtys

            shares["RETAILAlloted"] = (
                shares["RETAILBUYAlloted"] - shares["RETAILSELLAlloted"]
            )

            # SHNI
            y1 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="SHNI")
            qty = y1.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty is None:
                shares[f"SHNIBUYAlloted"] = 0
            else:
                shares[f"SHNIBUYAlloted"] = qty

            z1 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="SHNI")
            qty1s = z1.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty1s is None:
                shares[f"SHNISELLAlloted"] = 0
            else:
                shares[f"SHNISELLAlloted"] = qty1s

            shares["SHNIAlloted"] = shares["SHNIBUYAlloted"] - shares["SHNISELLAlloted"]

            # BHNI
            y2 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="BHNI")
            qty2 = y2.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty2 is None:
                shares[f"BHNIBUYAlloted"] = 0
            else:
                shares[f"BHNIBUYAlloted"] = qty2

            z2 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="BHNI")
            qty2s = z2.aggregate(Sum("AllotedQty"))["AllotedQty__sum"]

            if qty2s is None:
                shares[f"BHNISELLAlloted"] = 0
            else:
                shares[f"BHNISELLAlloted"] = qty2s

            shares["BHNIAlloted"] = shares["BHNIBUYAlloted"] - shares["BHNISELLAlloted"]

            shares["ALLOTED"] = (
                shares["RETAILAlloted"] + shares["SHNIAlloted"] + shares["BHNIAlloted"]
            )
            shares["ALLOTEDBUY"] = (
                shares["RETAILBUYAlloted"]
                + shares["SHNIBUYAlloted"]
                + shares["BHNIBUYAlloted"]
            )
            shares["ALLOTEDSELL"] = (
                shares["RETAILSELLAlloted"]
                + shares["SHNISELLAlloted"]
                + shares["BHNISELLAlloted"]
            )

            return render(
                request,
                "Cdashboard.html",
                {
                    "retail": retail,
                    "shni": shni,
                    "bhni": bhni,
                    "ExpectedProfitLoss": ExpectedProfitLoss,
                    "shares": shares,
                    "count": count,
                    "IPOName": IPO,
                    "IPOid": IPOid,
                },
            )

        IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        retail = {}
        shni = {}
        bhni = {}

        try:
            IPOPremium = float(IPO.Premium)
        except:
            IPOPremium = 0
        if IPO.ProfitMargin is None:
            IPO.ProfitMargin = 15
        if IPO.ExpecetdRetailApplication == "":
            IPO.ExpecetdRetailApplication = 2500000
        if IPO.ExpecetdSHNIApplication is None:
            IPO.ExpecetdSHNIApplication = 150000
        if IPO.ExpecetdBHNIApplication is None:
            IPO.ExpecetdBHNIApplication = 50000
        IPO.save()

        try:
            LotValueRetail = float(IPO.IPOPrice) * float(IPO.LotSizeRetail)
            RetailSize = ((float(IPO.TotalIPOSzie)) * float(IPO.RetailPercentage)) / 100
            retail["ApplicationFor1Time"] = (
                float(RetailSize) * 10000000
            ) / LotValueRetail

            LotValueSHNI = float(IPO.IPOPrice) * float(IPO.LotSizeSHNI)
            SHNISize = ((float(IPO.TotalIPOSzie)) * float(IPO.SHNIPercentage)) / 100
            shni["ApplicationFor1Time"] = (float(SHNISize) * 10000000) / LotValueSHNI

            LotValueBHNI = float(IPO.IPOPrice) * float(IPO.LotSizeBHNI)
            BHNISize = ((float(IPO.TotalIPOSzie)) * float(IPO.BHNIPercentage)) / 100
            bhni["ApplicationFor1Time"] = (float(BHNISize) * 10000000) / LotValueBHNI
        except:
            LotValueRetail = 0
            RetailSize = 0
            retail["ApplicationFor1Time"] = 0

            LotValueSHNI = 0
            SHNISize = 0
            shni["ApplicationFor1Time"] = 0

            LotValueBHNI = 0
            BHNISize = 0
            bhni["ApplicationFor1Time"] = 0

        try:
            ProfitMargin = float(IPO.ProfitMargin)
        except:
            ProfitMargin = None

        try:
            ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
            ExpecetdSHNIApplication = int(IPO.ExpecetdSHNIApplication)
            ExpecetdBHNIApplication = int(IPO.ExpecetdBHNIApplication)
        except:
            ExpecetdRetailApplication = None
            ExpecetdBHNIApplication = None
            ExpecetdSHNIApplication = None

        try:
            retail["NumberOfTimeIPO"] = (
                ExpecetdRetailApplication / retail["ApplicationFor1Time"]
            )
            shni["NumberOfTimeIPO"] = (
                ExpecetdSHNIApplication / shni["ApplicationFor1Time"]
            )
            bhni["NumberOfTimeIPO"] = (
                ExpecetdBHNIApplication / bhni["ApplicationFor1Time"]
            )
        except:
            retail["NumberOfTimeIPO"] = 0
            shni["NumberOfTimeIPO"] = 0
            bhni["NumberOfTimeIPO"] = 0

        try:
            retail["AvgShare"] = float(IPO.LotSizeRetail) / retail["NumberOfTimeIPO"]
            shni["AvgShare"] = float(IPO.LotSizeSHNI) / shni["NumberOfTimeIPO"]
            bhni["AvgShare"] = float(IPO.LotSizeBHNI) / bhni["NumberOfTimeIPO"]
        except:
            retail["AvgShare"] = 0
            shni["AvgShare"] = 0
            bhni["AvgShare"] = 0

        if retail["AvgShare"] > IPO.LotSizeRetail:
            retail["AvgShare"] = IPO.LotSizeRetail
        if shni["AvgShare"] > IPO.LotSizeSHNI:
            shni["AvgShare"] = IPO.LotSizeSHNI
        if bhni["AvgShare"] > IPO.LotSizeBHNI:
            bhni["AvgShare"] = IPO.LotSizeBHNI

        try:
            retail["BaseKostakRate"] = float(IPOPremium) * retail["AvgShare"]
            shni["BaseKostakRate"] = float(IPOPremium) * shni["AvgShare"]
            bhni["BaseKostakRate"] = float(IPOPremium) * bhni["AvgShare"]
        except:
            retail["BaseKostakRate"] = 0
            shni["BaseKostakRate"] = 0
            bhni["BaseKostakRate"] = 0

        try:
            retail["kostakRateForCustomer"] = retail["BaseKostakRate"] - (
                (retail["BaseKostakRate"] * float(IPO.ProfitMargin)) / 100
            )
            shni["kostakRateForCustomer"] = shni["BaseKostakRate"] - (
                (shni["BaseKostakRate"] * float(IPO.ProfitMargin)) / 100
            )
            bhni["kostakRateForCustomer"] = bhni["BaseKostakRate"] - (
                (bhni["BaseKostakRate"] * float(IPO.ProfitMargin)) / 100
            )
        except:
            retail["kostakRateForCustomer"] = 0
            shni["kostakRateForCustomer"] = 0
            bhni["kostakRateForCustomer"] = 0

        try:
            retail["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeRetail)
            shni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeSHNI)
            bhni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeBHNI)
        except:
            retail["BaseSubjectToRate"] = 0
            shni["BaseSubjectToRate"] = 0
            bhni["BaseSubjectToRate"] = 0

        try:
            retail["SubjectToRateForCustomer"] = retail["BaseSubjectToRate"] - (
                (retail["BaseSubjectToRate"] * float(IPO.ProfitMargin)) / 100
            )
            shni["SubjectToRateForCustomer"] = shni["BaseSubjectToRate"] - (
                (shni["BaseSubjectToRate"] * float(IPO.ProfitMargin)) / 100
            )
            bhni["SubjectToRateForCustomer"] = bhni["BaseSubjectToRate"] - (
                (bhni["BaseSubjectToRate"] * float(IPO.ProfitMargin)) / 100
            )
        except:
            retail["SubjectToRateForCustomer"] = 0
            shni["SubjectToRateForCustomer"] = 0
            bhni["SubjectToRateForCustomer"] = 0

        count = {}

        OrdCat = ["Kostak", "SubjectTo"]
        InvTyp = ["RETAIL", "SHNI", "BHNI"]
        OrdTyp = ["BUY", "SELL"]
        products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)

        for ordercategory in OrdCat:
            for investortype in InvTyp:
                for ordertype in OrdTyp:

                    if ordercategory == "SubjectTo":
                        x = products.filter(
                            OrderType=ordertype,
                            OrderCategory="Subject To",
                            InvestorType=investortype,
                        )
                    else:
                        x = products.filter(
                            OrderType=ordertype,
                            OrderCategory=ordercategory,
                            InvestorType=investortype,
                        )

                    count1 = x.aggregate(Sum("Quantity"))["Quantity__sum"]

                    if count1 is None:
                        count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                    else:
                        count[f"{ordercategory}{investortype}{ordertype}Count"] = count1

                count[f"{ordercategory}{investortype}Net"] = (
                    count[f"{ordercategory}{investortype}BUYCount"]
                    - count[f"{ordercategory}{investortype}SELLCount"]
                )

        x = products.filter(OrderType="BUY", OrderCategory="Premium")

        PremiumBUY = x.aggregate(Sum("Quantity"))["Quantity__sum"]
        if PremiumBUY is None:
            count["PremiumBUYCount"] = 0
        else:
            count["PremiumBUYCount"] = PremiumBUY

        y = products.filter(OrderType="SELL", OrderCategory="Premium")

        PremiumSELL = y.aggregate(Sum("Quantity"))["Quantity__sum"]
        if PremiumSELL is None:
            count["PremiumSELLCount"] = 0
        else:
            count["PremiumSELLCount"] = PremiumSELL

        count["PremiumNet"] = count["PremiumBUYCount"] - count["PremiumSELLCount"]
        count["PremiumDiff"] = count["PremiumBUYCount"] - count["PremiumSELLCount"]

        shares = {}
        shares["SELLTotal"] = 0
        shares["BUYTotal"] = 0
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                for ordertype in OrdTyp:
                    if investortype == "RETAIL":
                        shares[f"{ordercategory}{investortype}{ordertype}Shares"] = (
                            float(
                                count[f"{ordercategory}{investortype}{ordertype}Count"]
                            )
                            * float(retail["AvgShare"])
                        )

                    if investortype == "SHNI":
                        shares[f"{ordercategory}{investortype}{ordertype}Shares"] = (
                            float(
                                count[f"{ordercategory}{investortype}{ordertype}Count"]
                            )
                            * float(shni["AvgShare"])
                        )

                    if investortype == "BHNI":
                        shares[f"{ordercategory}{investortype}{ordertype}Shares"] = (
                            float(
                                count[f"{ordercategory}{investortype}{ordertype}Count"]
                            )
                            * float(bhni["AvgShare"])
                        )

                shares["BUYTotal"] = (
                    shares["BUYTotal"]
                    + shares[f"{ordercategory}{investortype}BUYShares"]
                )
                shares["SELLTotal"] = (
                    shares["SELLTotal"]
                    + shares[f"{ordercategory}{investortype}SELLShares"]
                )
                shares[f"{ordercategory}{investortype}Net"] = (
                    shares[f"{ordercategory}{investortype}BUYShares"]
                    - shares[f"{ordercategory}{investortype}SELLShares"]
                )

        shares["Diff_Qty"] = (
            shares["BUYTotal"] - shares["SELLTotal"] + count["PremiumDiff"]
        )

        BuyRate = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType="BUY"
        ).aggregate(Sum("Order__Rate"))["Order__Rate__sum"]
        if BuyRate is None:
            BuyRate = 0

        SellRate = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType="SELL"
        ).aggregate(Sum("Order__Rate"))["Order__Rate__sum"]
        if SellRate is None:
            SellRate = 0

        try:
            ExpectedProfitLoss = (
                float(shares["Diff_Qty"]) * float(IPO.Premium)
                + float(SellRate)
                - float(BuyRate)
            )
        except:
            ExpectedProfitLoss = 0

        return render(
            request,
            "dashboard.html",
            {
                "ExpectedProfitLoss": ExpectedProfitLoss,
                "shares": shares,
                "count": count,
                "retail": retail,
                "shni": shni,
                "bhni": bhni,
                "IPOName": IPO,
                "IPOid": IPOid,
                "ExpecetdSHNIApplication": ExpecetdSHNIApplication,
                "ExpecetdBHNIApplication": ExpecetdBHNIApplication,
                "ExpecetdRetailApplication": ExpecetdRetailApplication,
                "IpoPricePerShare": "{:.0f}".format(IPO.IPOPrice),
                "ProfitMargin": ProfitMargin,
                "Premium": IPOPremium,
            },
        )


@sync_to_async
def Od_DataUpdate_save(u_id, O_id, PreOpenPrice):
    orderdetail = OrderDetail(user=u_id, Order_id=O_id, PreOpenPrice=PreOpenPrice)
    orderdetail.save()


async def Od_DataUpdate(u_id, O_id, PreOpenPrice):
    await Od_DataUpdate_save(u_id, O_id, PreOpenPrice)


async def Order_Details_update(Qty, u_id, O_id, PreOpenPrice):
    tasks = []
    for i in range(int(Qty)):
        tasks.append(Od_DataUpdate(u_id, O_id, PreOpenPrice))

    await asyncio.gather(*tasks)


def Order_Details_update_sync(Qty, u_id, O_id, PreOpenPrice):
    async_to_sync(Order_Details_update)(Qty, u_id, O_id, PreOpenPrice)


@allowed_users(allowed_roles=["Broker", "Customer"])
def sell(request, IPOid, selectgroup=None):

    userid = request.user
    uid = request.user
    entry = GroupDetail.objects.filter(user=userid)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IPOType = IPOName.IPOType
    PreOpenPrice = IPOName.PreOpenPrice
    Ratelist = RateList(
        user=userid,
        RateListIPOName=IPOName,
        kostakSellRate=0,
        KostakSellQty=0,
        SubjecToSellRate=0,
        SubjecToSellQty=0,
        PremiumSellRate=0,
        PremiumSellQty=0,
    )

    product = Order.objects.filter(user=userid, OrderIPOName_id=IPOid).order_by("-id")

    if request.method == "POST":
        user = request.user
        Group = request.POST.get("item_id", "")
        gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
        KostakRate = request.POST.get("KostakRate", "")
        SubjectToRate = request.POST.get("SubjectToRate", "")
        PremiumRate = request.POST.get("PremiumRate", "")
        KostakRateBHNI = request.POST.get("KostakRateBHNI", "")
        SubjectToRateBHNI = request.POST.get("SubjectToRateBHNI", "")
        KostakRateSHNI = request.POST.get("KostakRateSHNI", "")
        SubjectToRateSHNI = request.POST.get("SubjectToRateSHNI", "")
        KostakQTY = request.POST.get("KostakQTY", "")
        SubjectToQTY = request.POST.get("SubjectToQTY", "")
        KostakQTYSHNI = request.POST.get("KostakQTYSHNI", "")
        SubjectToQTYSHNI = request.POST.get("SubjectToQTYSHNI", "")
        KostakQTYBHNI = request.POST.get("KostakQTYBHNI", "")
        SubjectToQTYBHNI = request.POST.get("SubjectToQTYBHNI", "")
        PremiumQTY = request.POST.get("PremiumQTY", "")

        CallQty = request.POST.get("CallQTY", "")
        CallRate = request.POST.get("CallRate", "")
        CallStrikePrice = request.POST.get("CallStrikePrice", "")

        PutQTY = request.POST.get("PutQTY", "")
        PutRate = request.POST.get("PutRate", "")
        PutStrikePrice = request.POST.get("PutStrikePrice", "")

        DateTime = request.POST.get("datetime", "")
        OrderDate = DateTime[0:10]
        OrderTime = DateTime[11:19]
        a = 0

        if KostakQTY != "" and KostakQTY != "0" and KostakRate != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="RETAIL",
                OrderCategory="Kostak",
                OrderType="SELL",
                Quantity=KostakQTY,
                Rate=KostakRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTY)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(KostakQTY, uid, order.id, PreOpenPrice)
                # sync_to_async(Order_Details_update_sync)(KostakQTY, uid, order.id, PreOpenPrice)
                # asyncio.create_task(Order_Details_update(KostakQTY,uid,order.id,PreOpenPrice))

                for i in range(0, int(KostakQTY)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a = 0

        if KostakQTYSHNI != "" and KostakQTYSHNI != "0" and KostakRateSHNI != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="SHNI",
                OrderCategory="Kostak",
                OrderType="SELL",
                Quantity=KostakQTYSHNI,
                Rate=KostakRateSHNI,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYSHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                a = 1

                # Order_Details_update_sync(KostakQTYSHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(KostakQTYSHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a = 0

        if KostakQTYBHNI != "" and KostakQTYBHNI != "0" and KostakRateBHNI != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="BHNI",
                OrderCategory="Kostak",
                OrderType="SELL",
                Quantity=KostakQTYBHNI,
                Rate=KostakRateBHNI,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYBHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(KostakQTYBHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(KostakQTYBHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a = 0

        if SubjectToQTY != "" and SubjectToQTY != "0" and SubjectToRate != "":
            if (
                request.POST.get("subjectToIsPremiumRetail", "") is not None
                and request.POST.get("subjectToIsPremiumRetail", "") != ""
                and request.POST.get("subjectToIsPremiumRetail", "") == "on"
            ):
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="RETAIL",
                    OrderCategory="Subject To",
                    OrderType="SELL",
                    Quantity=SubjectToQTY,
                    Rate=SubjectToRate,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                    Method="Premium",
                )
            else:
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="RETAIL",
                    OrderCategory="Subject To",
                    OrderType="SELL",
                    Quantity=SubjectToQTY,
                    Rate=SubjectToRate,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                )

            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTY)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(SubjectToQTY, uid, order.id, PreOpenPrice)
                for i in range(0, int(SubjectToQTY)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a = 0

        if (
            SubjectToQTYSHNI != ""
            and SubjectToQTYSHNI != "0"
            and SubjectToRateSHNI != ""
        ):
            if (
                request.POST.get("subjectToIsPremiumSHNI", "") is not None
                and request.POST.get("subjectToIsPremiumSHNI", "") != ""
                and request.POST.get("subjectToIsPremiumSHNI", "") == "on"
            ):
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="SHNI",
                    OrderCategory="Subject To",
                    OrderType="SELL",
                    Quantity=SubjectToQTYSHNI,
                    Rate=SubjectToRateSHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                    Method="Premium",
                )
            else:
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="SHNI",
                    OrderCategory="Subject To",
                    OrderType="SELL",
                    Quantity=SubjectToQTYSHNI,
                    Rate=SubjectToRateSHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                )

            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYBHNI)
                Limit = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(SubjectToQTYSHNI, uid, order.id, PreOpenPrice)
                for i in range(0, int(SubjectToQTYSHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a = 0

        if (
            SubjectToQTYBHNI != ""
            and SubjectToQTYBHNI != "0"
            and SubjectToRateBHNI != ""
        ):
            if (
                request.POST.get("subjectToIsPremiumBHNI", "") is not None
                and request.POST.get("subjectToIsPremiumBHNI", "") != ""
                and request.POST.get("subjectToIsPremiumBHNI", "") == "on"
            ):
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="BHNI",
                    OrderCategory="Subject To",
                    OrderType="SELL",
                    Quantity=SubjectToQTYBHNI,
                    Rate=SubjectToRateBHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                    Method="Premium",
                )
            else:
                order = Order(
                    user=uid,
                    OrderGroup_id=gid,
                    OrderIPOName=IPOName,
                    InvestorType="BHNI",
                    OrderCategory="Subject To",
                    OrderType="SELL",
                    Quantity=SubjectToQTYBHNI,
                    Rate=SubjectToRateBHNI,
                    OrderDate=OrderDate,
                    OrderTime=OrderTime,
                )

            O_limit = CustomUser.objects.get(username=user)

            if O_limit.Order_limit is not None:
                BUY_Count = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid
                ).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYBHNI)
                Limit = int(O_limit.Order_limit)

                if BUY_Count >= Limit + 1:
                    messages.error(
                        request, f"You have reached the limit of {Limit} OrderDetail."
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(SubjectToQTYBHNI, uid, order.id, PreOpenPrice)

                for i in range(0, int(SubjectToQTYBHNI)):
                    orderdetail = OrderDetail(
                        user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice
                    )
                    orderdetail.save()
            except:
                a = 0

        if PremiumQTY != "" and PremiumQTY != "0" and PremiumRate != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="PREMIUM",
                OrderCategory="Premium",
                OrderType="SELL",
                Quantity=PremiumQTY,
                Rate=PremiumRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
            )

            PRI_limit = CustomUser.objects.get(username=user)

            if PRI_limit.Premium_Order_limit is not None:
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(
                    user=user, OrderIPOName_id=IPOid, OrderCategory=Order_type
                ).aggregate(Sum("Quantity"))["Quantity__sum"]
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit = int(PRI_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request,
                        f"You have reached the limit of {Limit} Premium shares QTY.",
                    )
                    return redirect(f"/{IPOid}/SELL")
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user, entry2.id)
                a = 1
            except:
                a = 0

        if (
            CallQty != ""
            and CallQty != "0"
            and CallRate != ""
            and CallStrikePrice != ""
        ):
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="OPTIONS",
                OrderCategory="CALL",
                OrderType="SELL",
                Quantity=CallQty,
                Rate=CallRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
                Method=CallStrikePrice,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Premium_Order_limit is not None:
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(
                    user=user, OrderIPOName_id=IPOid, OrderCategory=Order_type
                ).aggregate(Sum("Quantity"))["Quantity__sum"]
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request,
                        f"You have reached the limit of {Limit} Premium shares QTY.",
                    )
                    return redirect(f"/{IPOid}/SELL")

            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user, entry2.id)
                a = 1
            except:
                traceback.print_exc()
                a == 0

        if PutQTY != "" and PutQTY != "0" and PutRate != "" and PutStrikePrice != "":
            order = Order(
                user=uid,
                OrderGroup_id=gid,
                OrderIPOName=IPOName,
                InvestorType="OPTIONS",
                OrderCategory="PUT",
                OrderType="SELL",
                Quantity=PutQTY,
                Rate=PutRate,
                OrderDate=OrderDate,
                OrderTime=OrderTime,
                Method=PutStrikePrice,
            )

            O_limit = CustomUser.objects.get(username=user)
            if O_limit.Premium_Order_limit is not None:
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(
                    user=user, OrderIPOName_id=IPOid, OrderCategory=Order_type
                ).aggregate(Sum("Quantity"))["Quantity__sum"]
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(
                        request,
                        f"You have reached the limit of {Limit} Premium shares QTY.",
                    )
                    return redirect(f"/{IPOid}/SELL")

            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user, entry2.id)
                a = 1
            except:
                traceback.print_exc()
                a == 0

        if a == 1:
            messages.success(
                request,
                "Sell order placed successfully. Telegram message sent successfully ",
            )
            return JsonResponse(
                {"status": "success", "message": "SELL order placed successfully"}
            )
            # return render(request, 'sell.html')

        else:
            messages.error(request, "Sell order was not placed. Please try again.")
            return JsonResponse(
                {"status": "error", "message": "SELL order dose not placed"}
            )

    if selectgroup is not None:
        selectgroup = unquote(selectgroup)
    else:
        if Order.objects.count() > 0:
            selectgroup = Order.objects.latest("id").OrderGroup.GroupName
        else:
            selectgroup = None

    return render(
        request,
        "sell.html",
        {
            "product": product,
            "Group": entry.order_by("GroupName"),
            "Ratelist": Ratelist,
            "IPOName": IPOName,
            "IPOid": IPOid,
            "order_type": "SELL",
            "selectgroup": selectgroup,
        },
    )


# order fun
@allowed_users(allowed_roles=["Broker", "Customer"])
def OrderFunction(request, IPOid):
    if request.user.groups.all()[0].name == "Broker":
        userid = request.user
        products = Order.objects.filter(user=userid, OrderIPOName_id=IPOid)
    else:
        userid = request.user.Broker_id
        products = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid, OrderGroup_id=request.user.Group_id
        )
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)
    Group = GroupDetail.objects.filter(user=userid)
    Groupfilter = "All"
    OrderCategoryFilter = "All"
    InvestorTypeFilter = "All"

    OrdCat = ["Kostak", "SubjectTo", "CALL", "PUT"]
    InvTyp = ["RETAIL", "SHNI", "BHNI", "OPTIONS"]
    OrdTyp = ["BUY", "SELL"]

    strike_dict = {}
    dict_count = {}
    dict_avg = {}
    dict_amount = {}

    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                if ordercategory == "SubjectTo":
                    x = products.filter(
                        OrderType=ordertype,
                        OrderCategory="Subject To",
                        InvestorType=investortype,
                    )
                else:
                    x = products.filter(
                        OrderType=ordertype,
                        OrderCategory=ordercategory,
                        InvestorType=investortype,
                    )
                count = x.aggregate(Sum("Quantity"))["Quantity__sum"]
                if count is None:
                    dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                    z = 0
                else:
                    dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = count
                    z = count

                amount = 0
                for i in x:
                    if i.OrderCategory == "Subject To":
                        if i.Method == "Premium":
                            if investortype == "RETAIL":
                                lot_size = IPO.LotSizeRetail
                            if investortype == "SHNI":
                                lot_size = IPO.LotSizeSHNI
                            if investortype == "BHNI":
                                lot_size = IPO.LotSizeBHNI
                            amount = ((lot_size * i.Rate) * i.Quantity) + amount
                        else:
                            amount = (i.Rate * i.Quantity) + amount

                    # 🔹 Special handling for OPTIONS CALL/PUT with StrikePrice
                    elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:

                        strike = getattr(i, "Method", None) or "NA"

                        # Initialize dict structure
                        if strike not in strike_dict:
                            strike_dict[strike] = {
                                "CALL": {
                                    "BUY": {"count": 0, "amount": 0, "avg": 0},
                                    "SELL": {"count": 0, "amount": 0, "avg": 0},
                                },
                                "PUT": {
                                    "BUY": {"count": 0, "amount": 0, "avg": 0},
                                    "SELL": {"count": 0, "amount": 0, "avg": 0},
                                },
                            }
                        # Update values
                        strike_dict[strike][ordercategory][ordertype][
                            "count"
                        ] += i.Quantity
                        strike_dict[strike][ordercategory][ordertype]["amount"] += (
                            i.Rate * i.Quantity
                        )

                        # Net = (BUY amount - SELL amount) for that side
                        buy_amt = strike_dict[strike][ordercategory]["BUY"]["amount"]
                        sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                        strike_dict[strike][ordercategory]["BUY"]["net"] = (
                            buy_amt - sell_amt
                        )
                        strike_dict[strike][ordercategory]["SELL"]["net"] = (
                            sell_amt - buy_amt
                        )

                        amount = (i.Rate * i.Quantity) + amount

                    else:
                        amount = (i.Rate * i.Quantity) + amount

                if z == 0:
                    dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = 0
                else:
                    dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = (
                        amount / z
                    )

                dict_amount[f"{ordercategory}{investortype}{ordertype}Amount"] = amount

    net_count = {}
    net_avg = {}
    net_amount = {}

    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"

            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0

            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)

    product = products.order_by("-OrderDate", "-OrderTime")

    PremiumBuyfilter = products.filter(OrderType="BUY", OrderCategory="Premium")
    PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum("Quantity"))
    PremiumBuyCount1 = PremiumBuyCount11["Quantity__sum"]
    if PremiumBuyCount1 is None:
        PremiumBuyCount = 0
    else:
        PremiumBuyCount = PremiumBuyCount1

    PremiumBuyAmount = 0
    for i in PremiumBuyfilter:
        PremiumBuyAmount = (i.Quantity * i.Rate) + PremiumBuyAmount

    if PremiumBuyCount == 0:
        PremiumBuyAvg = 0
    else:
        PremiumBuyAvg = PremiumBuyAmount / PremiumBuyCount

    PremiumSellfilter = products.filter(OrderType="SELL", OrderCategory="Premium")
    PremiumSellCount11 = PremiumSellfilter.aggregate(Sum("Quantity"))
    PremiumSellCount1 = PremiumSellCount11["Quantity__sum"]
    if PremiumSellCount1 is None:
        PremiumSellCount = 0
    else:
        PremiumSellCount = PremiumSellCount1

    PremiumSellAmount = 0
    for i in PremiumSellfilter:
        PremiumSellAmount = (i.Quantity * i.Rate) + PremiumSellAmount

    if PremiumSellCount == 0:
        PremiumSellAvg = 0
    else:
        PremiumSellAvg = PremiumSellAmount / PremiumSellCount

    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
    Premiumavg2 = PremiumSellCount * PremiumSellAvg
    pri_net_avg = Premiumavg1 - Premiumavg2
    if PremiumNetCount != 0:
        PremiumNetAvg = pri_net_avg / PremiumNetCount
        PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    else:
        PremiumNetAvg = 0
        PremiumNetAmount = PremiumSellAmount - PremiumBuyAmount

    # Initialize category totals
    # category_totals = {cat: {'count': 0, 'amount': 0, 'avg': 0} for cat in ['CALL', 'PUT']}
    # Strike prices and grand totals
    # strike_prices = []
    # grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
    # for strike, cats in strike_dict.items():
    #     call_count = cats["CALL"]["BUY"]["count"] + cats["CALL"]["SELL"]["count"]
    #     call_amount = cats["CALL"]["BUY"]["amount"] + cats["CALL"]["SELL"]["amount"]
    #     put_count = cats["PUT"]["BUY"]["count"] + cats["PUT"]["SELL"]["count"]
    #     put_amount = cats["PUT"]["BUY"]["amount"] + cats["PUT"]["SELL"]["amount"]
    #     strike_prices.append({
    #         "value": strike,
    #         "call_total_count": call_count,
    #         "call_avg": call_amount/call_count if call_count else 0,
    #         "put_total_count": put_count,
    #         "put_avg": put_amount/put_count if put_count else 0,
    #     })
    #     grand_call_count += call_count
    #     grand_call_amount += call_amount
    #     grand_put_count += put_count
    #     grand_put_amount += put_amount

    # grand_total = {
    #     "call_total_count": grand_call_count,
    #     "call_avg": grand_call_amount/grand_call_count if grand_call_count else 0,
    #     "put_total_count": grand_put_count,
    #     "put_avg": grand_put_amount/grand_put_count if grand_put_count else 0,
    # }
    # category_totals = {
    #     "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
    #     "PUT":  {"count": grand_put_count, "avg": grand_total["put_avg"]},
    # }

    if request.method == "POST":
        strike_dict = {}
        Groupfilter = request.POST.get("Groupfilter", "")
        OrderCategoryFilter = request.POST.get("OrderCategoryFilter", "")
        InvestorTypeFilter = request.POST.get("InvestorTypeFilter", "")

        if InvestorTypeFilter == "" or InvestorTypeFilter is None:
            InvestorTypeFilter = "All"

        if Groupfilter == "" or Groupfilter is None:
            Groupfilter = "All"

        if OrderCategoryFilter == "" or OrderCategoryFilter is None:
            OrderCategoryFilter = "All"

        if is_valid_queryparam(Groupfilter) and Groupfilter != "All":
            products = products.filter(OrderGroup__GroupName=Groupfilter)
        if is_valid_queryparam(OrderCategoryFilter) and OrderCategoryFilter != "All":
            products = products.filter(OrderCategory=OrderCategoryFilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != "All":
            products = products.filter(InvestorType=InvestorTypeFilter)
        Groupfilter = Groupfilter
        OrderCategoryFilter = OrderCategoryFilter
        InvestorTypeFilter = InvestorTypeFilter

        for ordercategory in OrdCat:
            for investortype in InvTyp:
                for ordertype in OrdTyp:
                    if ordercategory == "SubjectTo":
                        x = products.filter(
                            OrderType=ordertype,
                            OrderCategory="Subject To",
                            InvestorType=investortype,
                        )
                    else:
                        x = products.filter(
                            OrderType=ordertype,
                            OrderCategory=ordercategory,
                            InvestorType=investortype,
                        )
                    count = x.aggregate(Sum("Quantity"))["Quantity__sum"]
                    if count is None:
                        dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                    else:
                        dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = (
                            count
                        )

                    amount = 0
                    for i in x:
                        if i.OrderCategory == "Subject To":
                            if i.Method == "Premium":
                                if investortype == "RETAIL":
                                    lot_size = IPO.LotSizeRetail
                                if investortype == "SHNI":
                                    lot_size = IPO.LotSizeSHNI
                                if investortype == "BHNI":
                                    lot_size = IPO.LotSizeBHNI
                                amount = ((lot_size * i.Rate) * i.Quantity) + amount
                            else:
                                amount = (i.Rate * i.Quantity) + amount
                        # 🔹 Special handling for OPTIONS CALL/PUT with StrikePrice
                        elif investortype == "OPTIONS" and ordercategory in [
                            "CALL",
                            "PUT",
                        ]:
                            # print("OPTIONS CALL/PUT detected")
                            # x = products.filter(OrderType=ordertype, InvestorType="OPTIONS")
                            strike = getattr(i, "Method", None) or "NA"

                            # Initialize dict structure
                            if strike not in strike_dict:
                                strike_dict[strike] = {
                                    "CALL": {
                                        "BUY": {"count": 0, "amount": 0, "avg": 0},
                                        "SELL": {"count": 0, "amount": 0, "avg": 0},
                                    },
                                    "PUT": {
                                        "BUY": {"count": 0, "amount": 0, "avg": 0},
                                        "SELL": {"count": 0, "amount": 0, "avg": 0},
                                    },
                                }
                            # Update values
                            strike_dict[strike][ordercategory][ordertype][
                                "count"
                            ] += i.Quantity
                            strike_dict[strike][ordercategory][ordertype]["amount"] += (
                                i.Rate * i.Quantity
                            )

                            amount = (i.Rate * i.Quantity) + amount

                        else:
                            amount = (i.Rate * i.Quantity) + amount

                    if count == 0 or count is None:
                        dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = 0
                    else:
                        dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = (
                            amount / count
                        )

                    dict_amount[f"{ordercategory}{investortype}{ordertype}Amount"] = (
                        amount
                    )

        for ordercategory in OrdCat:
            for investortype in InvTyp:
                # Keys for BUY and SELL
                buy_key_count = f"{ordercategory}{investortype}BUYCount"
                sell_key_count = f"{ordercategory}{investortype}SELLCount"

                buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
                sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

                # Get counts (default 0 if missing)
                buy_count = dict_count.get(buy_key_count, 0)
                sell_count = dict_count.get(sell_key_count, 0)
                net_c = buy_count - sell_count

                # Get amounts (Count * Avg)
                buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
                sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
                net_amt = buy_amount - sell_amount

                # Calculate net average
                if net_c != 0:
                    net_a = net_amt / net_c
                else:
                    net_a = 0

                if net_c == 0:
                    net_amt = sell_amount - buy_amount
                # Store results
                key_prefix = f"{ordercategory}{investortype}Net"
                net_count[f"{key_prefix}Count"] = net_c
                net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
                net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)

        product = products.order_by("-OrderDate", "-OrderTime")

        PremiumBuyfilter = products.filter(OrderType="BUY", OrderCategory="Premium")
        PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum("Quantity"))
        PremiumBuyCount1 = PremiumBuyCount11["Quantity__sum"]
        if PremiumBuyCount1 is None:
            PremiumBuyCount = 0
        else:
            PremiumBuyCount = PremiumBuyCount1

        PremiumBuyAmount = 0
        for i in PremiumBuyfilter:
            PremiumBuyAmount = (i.Quantity * i.Rate) + PremiumBuyAmount

        if PremiumBuyCount == 0:
            PremiumBuyAvg = 0
        else:
            PremiumBuyAvg = PremiumBuyAmount / PremiumBuyCount

        PremiumSellfilter = products.filter(OrderType="SELL", OrderCategory="Premium")
        PremiumSellCount11 = PremiumSellfilter.aggregate(Sum("Quantity"))
        PremiumSellCount1 = PremiumSellCount11["Quantity__sum"]
        if PremiumSellCount1 is None:
            PremiumSellCount = 0
        else:
            PremiumSellCount = PremiumSellCount1

        PremiumSellAmount = 0
        for i in PremiumSellfilter:
            PremiumSellAmount = (i.Quantity * i.Rate) + PremiumSellAmount

        if PremiumSellCount == 0:
            PremiumSellAvg = 0
        else:
            PremiumSellAvg = PremiumSellAmount / PremiumSellCount

        PremiumNetCount = PremiumBuyCount - PremiumSellCount
        Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
        Premiumavg2 = PremiumSellCount * PremiumSellAvg
        pri_net_avg = Premiumavg1 - Premiumavg2
        if PremiumNetCount != 0:
            PremiumNetAvg = pri_net_avg / PremiumNetCount
            PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
        else:
            PremiumNetAvg = 0
            PremiumNetAmount = PremiumSellAmount - PremiumBuyAmount

    strike_prices = []
    grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
    for strike, cats in strike_dict.items():
        # CALL
        call_buy_count = cats["CALL"]["BUY"]["count"]
        call_sell_count = cats["CALL"]["SELL"]["count"]
        call_buy_amount = cats["CALL"]["BUY"]["amount"]
        call_sell_amount = cats["CALL"]["SELL"]["amount"]

        call_net_count = call_buy_count - call_sell_count
        call_avg1 = call_buy_amount - call_sell_amount
        call_avg2 = call_sell_amount - call_buy_amount
        call_net_avg = call_avg1 - call_avg2
        # call_net_amount = call_buy_amount - call_sell_amount
        if call_net_count != 0:
            call_avg = call_net_avg / call_net_count
            call_net_amount = call_buy_amount - call_sell_amount
        else:
            call_avg = 0
            call_net_amount = call_sell_amount - call_buy_amount

        # PUT
        put_buy_count = cats["PUT"]["BUY"]["count"]
        put_sell_count = cats["PUT"]["SELL"]["count"]
        put_buy_amount = cats["PUT"]["BUY"]["amount"]
        put_sell_amount = cats["PUT"]["SELL"]["amount"]

        put_net_count = put_buy_count - put_sell_count
        put_avg1 = put_buy_amount - put_sell_amount
        put_avg2 = put_sell_amount - put_buy_amount
        put_net_avg = put_avg1 - put_avg2
        # put_net_amount = put_buy_amount - put_sell_amount
        if put_net_count != 0:
            put_avg = put_net_avg / put_net_count
            put_net_amount = put_buy_amount - put_sell_amount
        else:
            put_avg = 0
            put_net_amount = put_sell_amount - put_buy_amount

        strike_prices.append(
            {
                "value": strike,
                "call_total_count": call_net_count,
                "call_avg": (call_net_amount / call_net_count) if call_net_count else 0,
                "call_net_amount": call_net_amount,
                "put_total_count": put_net_count,
                "put_avg": (put_net_amount / put_net_count) if put_net_count else 0,
                "put_net_amount": put_net_amount,
            }
        )
        grand_call_count += call_net_count
        grand_call_amount += call_net_amount
        grand_put_count += put_net_count
        grand_put_amount += put_net_amount

    grand_total = {
        "call_total_count": grand_call_count,
        "call_avg": (grand_call_amount / grand_call_count) if grand_call_count else 0,
        "call_net_amount": grand_call_amount,
        "put_total_count": grand_put_count,
        "put_avg": grand_put_amount / grand_put_count if grand_put_count else 0,
        "put_net_amount": grand_put_amount,
    }

    category_totals = {
        "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
        "PUT": {"count": grand_put_count, "avg": grand_total["put_avg"]},
    }

    page_obj = None
    try:
        page_size = request.POST.get("Order_page_size")
        if page_size != "" and page_size is not None:
            request.session["Order_page_size"] = page_size
        else:
            page_size = request.session["Order_page_size"]
    except:
        page_size = request.session.get("Order_page_size", 50)

    Data = []
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    products = product
    if page_size == "All":
        all_rows = True
        paginator = Paginator(products, max(len(products), 1))
        page_number = request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        for i, order_detail in enumerate(page_obj):
            entry_data = {
                "id": order_detail.id,
                "OrderGroup": order_detail.OrderGroup.GroupName,
                "OrderType": order_detail.OrderType,
                "OrderCategory": order_detail.OrderCategory,
                "InvestorType": order_detail.InvestorType,
                "Quantity": int(order_detail.Quantity),
                "Method": order_detail.Method,
                "Rate": order_detail.Rate,
                "Date": order_detail.OrderDate,
                "Time": order_detail.OrderTime,
                "sr_no": start_index + i + 1,
            }
            Data.append(entry_data)

    df = pd.DataFrame.from_records(Data)
    html_table = '<table class="table-bordered sortable" >'
    html_table = "<thead><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th>Sr No.</th>"
    html_table += "<th>Group Name</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th> Qty</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th>Date and Time</th>"
    html_table += "<th>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    for i, row in df.iterrows():
        datetime_str = f"{row.Date} {row.Time}"
        datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        formatted_datetime = datetime_obj.strftime("%b. %d, %Y | %I:%M:%S %p")
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td>{row.sr_no}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
        html_table += f"<td >{row.OrderType}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        # if row.InvestorType == 'OPTIONS':
        #     html_table += f"<td>{row.Method}</td>"
        if row.OrderCategory != "Premium":
            method_value = row.Method if row.Method else "Application"
            html_table += f"<td>{method_value}</td>"
        else:
            html_table += f"<td>-</td>"
        if IPOName.IPOType == "MAINBOARD":
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        if row.OrderCategory != "Premium" and row.InvestorType != "OPTIONS":
            html_table += f"<td><a href='/{IPOid}/OrderDetail/{row.OrderType}/{row.OrderGroup}/{ row.OrderCategory }/{row.InvestorType}/{ row.Date.strftime('%Y%m%d') }/{row.Time.strftime('%H%M%S')}{row.id}' style='color:blue; text-decoration: underline; '> {row.Quantity} </a></td>"
        else:
            html_table += f"<td>{row.Quantity}</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td>{formatted_datetime} </td>"
        if IPOName.IPOType == "MAINBOARD":
            url = f"/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}"
        else:
            InvestorTypeFilter = "All"
            url = f"/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='{url}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button></td>"
        html_table += "</tr>\n"
    html_table += "</tbody></table>"

    return render(
        request,
        "Order.html",
        {
            "Group": Group.order_by("GroupName"),
            "html_table": html_table,
            "IPOid": IPOid,
            "IPOName": IPO,
            "Groupfilter": Groupfilter,
            "OrderCategoryFilter": OrderCategoryFilter,
            "category_totals": category_totals,
            "strike_prices": strike_prices,
            "grand_total": grand_total,
            "InvestorTypeFilter": InvestorTypeFilter,
            "PremiumBuyAmount": PremiumBuyAmount,
            "PremiumNetAmount": PremiumNetAmount,
            "PremiumSellAmount": PremiumSellAmount,
            "dict_count": dict_count,
            "net_count": net_count,
            "net_avg": net_avg,
            "net_amount": net_amount,
            "dict_amount": dict_amount,
            "dict_avg": dict_avg,
            "PremiumNetCount": PremiumNetCount,
            "PremiumNetCount": "{:.2f}".format(PremiumNetCount),
            "PremiumNetAvg": PremiumNetAvg,
            "PremiumNetAvg": "{:.2f}".format(PremiumNetAvg),
            "PremiumBuyCount": PremiumBuyCount,
            "PremiumSellCount": PremiumSellCount,
            "PremiumSellAvg": "{:.2f}".format(PremiumSellAvg),
            "PremiumBuyAvg": "{:.2f}".format(PremiumBuyAvg),
            "page_obj": page_obj,
            "Order_page_size": page_size,
        },
    )


def loginUser(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user is not None:
            Ex_Date = CustomUser.objects.get(username=user)
            Ex_Date = Ex_Date.Expiry_Date
            if Ex_Date < now().date():
                messages.error(
                    request, "Your account has expired. Please contact support."
                )
                return render(request, "login.html")
            login(request, user)
            return redirect("/")

        else:
            messages.error(request, "Username or Password is Incorrect")
            return render(request, "login.html")

    return render(request, "login.html")


def logoutUser(request):
    logout(request)
    return redirect("/login")


# Temporary storage for OTP session
OTP_SESSIONS = {}


@csrf_exempt
def send_telegram_otp(request):
    if request.method == "POST":
        user = request.user
        custom_user = CustomUser.objects.get(username=user)
        # print(f"Custom User: {custom_user}")
        # Validate required fields
        if (
            not custom_user.TelegramApi_id
            or not custom_user.TelegramApi_key
            or not custom_user.Mobileno
        ):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Telegram API ID, API Key, or Mobile number is missing.",
                },
                status=400,
            )

        try:
            api_id = int(custom_user.TelegramApi_id)
        except ValueError:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Telegram API ID must be a valid integer.",
                },
                status=400,
            )
        api_hash = custom_user.TelegramApi_key
        phone = custom_user.Mobileno

        async def send_code():
            session = StringSession()
            client = TelegramClient(session, api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                sent = await client.send_code_request(phone)
                OTP_SESSIONS[user.username] = {
                    "client": client,
                    "session": session,
                    "phone": phone,
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "phone_code_hash": sent.phone_code_hash,
                }
                return {
                    "status": "ok",
                    "message": "OTP sent successfully",
                    "phone": phone,
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "session_string": session.save(),  # Save as string
                    "phone_code_hash": sent.phone_code_hash,
                }
            return {"status": "already", "message": "User is already authorized"}

        try:
            result = asyncio.run(send_code())
            messages.success(request, "Otp sent successfully")

            return JsonResponse(result)
        except Exception as e:
            messages.error(request, f"Error sending OTP: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)})


@csrf_exempt
def verify_telegram_otp(request):
    if request.method == "POST":
        user = request.user
        otp = request.POST.get("otp")
        phone = request.POST.get("phone")
        api_id = request.POST.get("api_id")
        api_hash = request.POST.get("api_hash")
        session_string = request.POST.get("session_string")
        phone_code_hash = request.POST.get("phone_code_hash")

        # print(f"OTP_SESSIONS: {OTP_SESSIONS}")
        # session_data = OTP_SESSIONS.get(user.username)

        # if not session_data:
        #     return JsonResponse({'status': 'error', 'message': 'No OTP session found'})
        if not all([otp, phone, api_id, api_hash, session_string, phone_code_hash]):
            return JsonResponse({"status": "error", "message": "Missing required data"})

        async def verify_code():
            try:
                # Rebuild the session and client
                client = TelegramClient(
                    StringSession(session_string), int(api_id), api_hash
                )
                await client.connect()

                if not await client.is_user_authorized():
                    messages.error(
                        request, "Client is not authorized. Please request OTP again."
                    )
                    await client.sign_in(
                        phone=phone, code=otp, phone_code_hash=phone_code_hash
                    )

                # Save session string to DB
                print("")
                session_str = client.session.save()
                print(f"Session String: {session_str}")
                print(len(session_str))
                # custom_user = CustomUser.objects.get(username=user)
                # custom_user.Telegram_session = session_str
                # custom_user.save()
                custom_user = await sync_to_async(CustomUser.objects.get)(username=user)
                custom_user.Telegram_session = session_str
                await sync_to_async(custom_user.save)()

                await client.disconnect()
                messages.success(request, "Telegram authorized and session saved")
                return {
                    "status": "success",
                    "message": "Telegram authorized and session saved",
                }
            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Error verifying OTP: {str(e)}")
                return {"status": "error", "message": str(e)}

        try:
            result = asyncio.run(verify_code())
            messages.success(request, "Telegram Session Created Successfully")
            return JsonResponse(result)
        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"Error verifying OTP: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)})


@login_required
def user_profile(request):
    user = request.user
    user_detail = CustomUser.objects.get(username=user)
    context = {
        "user": user,
        "user_detail": user_detail,
        "expiry_date": user.Expiry_Date,
    }
    return render(request, "user_profile.html", context)


@login_required
def update_user_profile(request):
    if request.method == "POST":
        user = request.user
        custom_user = CustomUser.objects.get(username=user)

        # Only update fields that are present in the submitted form
        if "email" in request.POST:
            custom_user.email = request.POST.get("email")

        if "app_password" in request.POST:
            custom_user.AppPassword = request.POST.get("app_password")

        if "telegram_api" in request.POST:
            custom_user.TelegramApi_id = request.POST.get("telegram_api")

        if "telegram_api_key" in request.POST:
            custom_user.TelegramApi_key = request.POST.get("telegram_api_key")

        if "mobile_number" in request.POST:
            custom_user.Mobileno = request.POST.get("mobile_number")

        custom_user.save()
        # return JsonResponse({"status": "success", "message": "Profile updated successfully!"})
        # print(request.headers)  # Debugging line to check headers
        # print(request.headers.get('x-requested-with'))
        # # ✅ Check if request is AJAX
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            messages.success(request, "Profile updated successfully!")
            return JsonResponse({"status": "success"})
        else:
            messages.success(request, "Profile updated successfully!")
            return redirect("user_profile")

    messages.error(request, "Invalid request method.")
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


# in case you need to make paths dynamic


@login_required
@csrf_exempt
def place_order_view(request, IPOid, order_type):

    if request.method == "POST":
        form_data = {
            key: value
            for key, value in request.POST.items()
            if key != "csrfmiddlewaretoken"
        }
        user = request.user

        order_type = order_type.upper()
        try:
            custom_user = CustomUser.objects.get(username=user)
        except CustomUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User not found"})

        # Get IPO name
        try:
            ipo_obj = CurrentIpoName.objects.get(id=IPOid, user=user)
            ipo_name = ipo_obj.IPOName
        except CurrentIpoName.DoesNotExist:
            ipo_name = "Unknown IPO"
        # print(f"Placing order for IPO ID: {IPOid}, Type: {order_type}")
        # Get form fields
        group_id = request.POST.get("item_id")
        datetime_val = request.POST.get("datetime")
        premium_qty = request.POST.get("PremiumQTY")
        premium_rate = request.POST.get("PremiumRate")
        # Convert string to datetime object first
        datetime_obj = datetime.strptime(datetime_val, "%Y-%m-%dT%H:%M:%S")

        # Now format as you like
        datetime_str = datetime_obj.strftime(" %I:%M:%S %p %d-%m-%Y ")

        try:
            group_detail = GroupDetail.objects.get(GroupName=group_id, user=user)
            group_name = group_detail.GroupName
            phone = group_detail.MobileNo
        except GroupDetail.DoesNotExist:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Please select a valid group with mobile number.",
                }
            )

        # Helper for qty-rate formatting with premium checkbox status
        def format_qty_rate(qty, rate, label_emoji="", label_name="", is_premium=False):
            if qty.strip() or rate.strip():
                premium_indicator = " (Premium Rate)" if is_premium else ""
                return f"{label_emoji} {label_name}: Qty {qty or '—'} @ ₹{rate or '—'}{premium_indicator}"
            return None

        # Build the message lines
        header_lines = [
            f"**📢 IPO Name: {ipo_name}**",
            f"**📦 Order : {order_type}  From 👥 {group_id}**",
            f"**🕒 Date & Time: {datetime_str}**",
            "",
        ]

        lines = []
        # Kostak
        kostak_lines = []
        k_retail = format_qty_rate(
            request.POST.get("KostakQTY", ""),
            request.POST.get("KostakRate", ""),
            " ",
            "Retail",
        )
        k_shni = format_qty_rate(
            request.POST.get("KostakQTYSHNI", ""),
            request.POST.get("KostakRateSHNI", ""),
            " ",
            "SHNI",
        )
        k_bhni = format_qty_rate(
            request.POST.get("KostakQTYBHNI", ""),
            request.POST.get("KostakRateBHNI", ""),
            " ",
            "BHNI",
        )
        for l in (k_retail, k_shni, k_bhni):
            if l:
                kostak_lines.append(l)
        if kostak_lines:
            lines.append("**🔹 Kostak**")
            # lines.extend(kostak_lines)
            lines.extend([f"  {item}" for item in kostak_lines])
            lines.append("")

        # Subject To - Check premium checkbox status
        subject_lines = []
        # Check if premium checkboxes are checked
        is_premium_retail = request.POST.get("subjectToIsPremiumRetail") == "on"
        is_premium_shni = request.POST.get("subjectToIsPremiumSHNI") == "on"
        is_premium_bhni = request.POST.get("subjectToIsPremiumBHNI") == "on"

        s_retail = format_qty_rate(
            request.POST.get("SubjectToQTY", ""),
            request.POST.get("SubjectToRate", ""),
            " ",
            "Retail",
            is_premium_retail,
        )
        s_shni = format_qty_rate(
            request.POST.get("SubjectToQTYSHNI", ""),
            request.POST.get("SubjectToRateSHNI", ""),
            " ",
            "SHNI",
            is_premium_shni,
        )
        s_bhni = format_qty_rate(
            request.POST.get("SubjectToQTYBHNI", ""),
            request.POST.get("SubjectToRateBHNI", ""),
            " ",
            "BHNI",
            is_premium_bhni,
        )
        for l in (s_retail, s_shni, s_bhni):
            if l:
                subject_lines.append(l)
        if subject_lines:
            lines.append("**🔹 Subject To**")
            # lines.extend(subject_lines)
            lines.extend([f"  {item}" for item in subject_lines])

            lines.append("")

        # Premium
        premium_line = None
        if (
            request.POST.get("PremiumQTY", "").strip()
            or request.POST.get("PremiumRate", "").strip()
        ):
            premium_line = f" Qty {request.POST.get('PremiumQTY', '—')} @ ₹{request.POST.get('PremiumRate', '—')}"
        if premium_line:
            lines.append("**🔹 Premium Deal**")
            lines.append(f"    Share:{premium_line}")
            lines.append("")

        # Options
        call_line = None
        if (
            request.POST.get("CallQTY", "").strip()
            or request.POST.get("CallRate", "").strip()
        ):
            call_line = f" Call: Qty {request.POST.get('CallQTY', '—')} | Strike ₹{request.POST.get('CallStrikePrice', '—')} | Rate ₹{request.POST.get('CallRate', '—')}"
        put_line = None
        if (
            request.POST.get("PutQTY", "").strip()
            or request.POST.get("PutRate", "").strip()
        ):
            put_line = f" Put: Qty {request.POST.get('PutQTY', '—')} | Strike ₹{request.POST.get('PutStrikePrice', '—')} | Rate ₹{request.POST.get('PutRate', '—')}"

        if call_line or put_line:
            lines.append("**🔹 Options**")
            if call_line:
                lines.append(f"    {call_line}")
            if put_line:
                lines.append(f"    {put_line}")

        if not lines and not custom_user.Telegram_session:
            messages.error(
                request,
                f"{order_type} order could not be placed. Telegram session not created. Please set up a Telegram session to send messages.",
            )
            return JsonResponse(
                {"status": "error", "message": "Telegram session not verified yet"}
            )

        if not lines:
            # Buy order could not be placed. Please complete all required fields and try again
            messages.error(
                request,
                f"{order_type} order could not be placed. Please fill at least one field and try again.",
            )
            return JsonResponse(
                {
                    "status": "error",
                    "message": "No fields entered to send. Please fill at least one field.",
                }
            )

        if not custom_user.Telegram_session:
            messages.warning(
                request,
                f"{order_type} order placed successfully. Telegram session not created. Please set up a Telegram session to send messages.",
            )
            return JsonResponse(
                {"status": "error", "message": "Telegram session not verified yet"}
            )

        if not phone:
            messages.warning(
                request,
                f"{order_type} order placed successfully, but failed to send Telegram message: group mobile number missing.",
            )
            return JsonResponse(
                {
                    "status": "missing_phone",
                    "message": "Order placed successfully, but no group mobile number found. Please add a number to send Telegram message.",
                }
            )

        # Final message
        # message = "\n".join(lines)
        message = "\n".join(header_lines + lines)

        async def send_message():
            async with TelegramClient(
                StringSession(custom_user.Telegram_session),
                int(custom_user.TelegramApi_id),
                custom_user.TelegramApi_key,
            ) as client:
                entity = await client.get_entity(f"+91{phone}")
                await client.send_message(entity, message, parse_mode="markdown")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_message())
            loop.close()
            # Sell order placed successfully. Telegram message sent successfully
            success_msg = f" {order_type} order placed successfully. Telegram message sent successfully."
            messages.success(request, success_msg)
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Message sent via Telegram with premium rate information.",
                }
            )
        except Exception as e:
            # Buy order placed successfully, but failed to send Telegram message: contact not found in group details.
            messages.error(
                request,
                f"{order_type} order placed, but failed to send Telegram message: Contact not found in group details.",
            )
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Failed to send Telegram message: {str(e)}",
                }
            )

    return JsonResponse({"status": "error", "message": "Invalid request method"})


# home/views.py


@login_required
@csrf_exempt
def share_status_telegram(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    IPOid = data.get("IPO_id")
    group_names = data.get("group_names", [])
    share_all = data.get("all", False)
    if not IPOid:
        return JsonResponse(
            {"status": "error", "message": "IPO_id required"}, status=400
        )

    # auth + session
    user = request.user
    try:
        custom_user = CustomUser.objects.get(username=user)
    except CustomUser.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "User not found"}, status=404
        )
    if not custom_user.Telegram_session:
        return JsonResponse(
            {
                "status": "session_expired",
                "message": "Telegram session not verified yet",
            },
            status=400,
        )

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    groups_qs = GroupDetail.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)

    # group selection
    if share_all or not group_names:
        groups_to_share = list(
            groups_qs.filter(id__in=orders.values("OrderGroup").distinct()).values_list(
                "GroupName", flat=True
            )
        )
    else:
        groups_to_share = list(group_names)
    if not groups_to_share:
        return JsonResponse(
            {"status": "error", "message": "No groups to share"}, status=400
        )

    # helpers
    def sum_qty(qs):
        return qs.aggregate(total=Sum("Quantity"))["total"] or 0

    def sum_amt(qs):
        return qs.aggregate(total=Sum("Amount"))["total"] or 0

    # Compute net qty and weighted avg rate like Buy
    def net_qty_and_rate(qs):
        bq = sum_qty(qs.filter(OrderType="BUY"))
        sq = sum_qty(qs.filter(OrderType="SELL"))
        net_q = bq - sq
        amt = sum_amt(qs.filter(OrderType__in=["BUY", "SELL"]))
        rate = round(amt / net_q, 2) if net_q else None
        return net_q, rate

    def line(label, net_q, rate):
        if not (net_q or rate):
            return None
        rt = f"₹{rate:.2f}" if isinstance(rate, (int, float, float)) else "—"
        return f" {label}: Qty {int(net_q) if net_q else 0} @ {rt}"

    payloads, pre = [], []
    now_s = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    for gname in groups_to_share:
        grp = groups_qs.filter(GroupName=gname).first()
        if not grp or not grp.MobileNo:
            pre.append(f"Failed {gname}: Group/Mobile missing")
            continue

        go = orders.filter(OrderGroup=grp)

        # Kostak (Retail/SHNI/BHNI)
        k_r_q, k_r_r = net_qty_and_rate(
            go.filter(OrderCategory="Kostak", InvestorType="RETAIL")
        )
        k_s_q, k_s_r = net_qty_and_rate(
            go.filter(OrderCategory="Kostak", InvestorType="SHNI")
        )
        k_b_q, k_b_r = net_qty_and_rate(
            go.filter(OrderCategory="Kostak", InvestorType="BHNI")
        )

        # Subject To (Retail/SHNI/BHNI)
        s_r_q, s_r_r = net_qty_and_rate(
            go.filter(OrderCategory="Subject To", InvestorType="RETAIL")
        )
        s_s_q, s_s_r = net_qty_and_rate(
            go.filter(OrderCategory="Subject To", InvestorType="SHNI")
        )
        s_b_q, s_b_r = net_qty_and_rate(
            go.filter(OrderCategory="Subject To", InvestorType="BHNI")
        )

        # Premium (net shares + effective rate)
        p_q, p_r = net_qty_and_rate(go.filter(OrderCategory="Premium"))

        # Options (amounts only)
        call_amt = sum_amt(go.filter(OrderCategory="CALL"))
        put_amt = sum_amt(go.filter(OrderCategory="PUT"))

        # Build Buy-style message
        lines = [f"**🆔 Group Name: {gname}**", f"**🕒 Date & Time: {now_s}**", ""]

        kostak_lines = list(
            filter(
                None,
                [
                    line("Retail", k_r_q, k_r_r),
                    line("SHNI", k_s_q, k_s_r),
                    line("BHNI", k_b_q, k_b_r),
                ],
            )
        )
        if kostak_lines:
            lines.append("**🔹 Kostak**")
            lines.extend(kostak_lines)
            lines.append("")

        subj_lines = list(
            filter(
                None,
                [
                    line("Retail", s_r_q, s_r_r),
                    line("SHNI", s_s_q, s_s_r),
                    line("BHNI", s_b_q, s_b_r),
                ],
            )
        )
        if subj_lines:
            lines.append("**🔹 Subject To**")
            lines.extend(subj_lines)
            lines.append("")

        if p_q or p_r:
            lines.append("**🔹 Premium Deal**")
            rt = f"₹{p_r:.2f}" if isinstance(p_r, (int, float, float)) else "—"
            lines.append(f"Qty {int(p_q) if p_q else 0} @ {rt}")
            lines.append("")

        if call_amt or put_amt:
            lines.append("**🔹 Options**")
            lines.append(f" Call Amt: ₹{call_amt:.1f}")
            lines.append(f" Put Amt: ₹{put_amt:.1f}")

        payloads.append(
            {"name": gname, "phone": grp.MobileNo, "message": "\n".join(lines)}
        )

    if not payloads:
        return JsonResponse(
            {"status": "error", "message": "; ".join(pre) or "Nothing to send"},
            status=400,
        )

    async def run_send():
        out = pre[:]
        async with TelegramClient(
            StringSession(custom_user.Telegram_session),
            int(custom_user.TelegramApi_id),
            custom_user.TelegramApi_key,
        ) as client:
            for p in payloads:
                try:
                    entity = await client.get_entity(
                        f'+91{p["phone"]}'
                    )  # adjust prefix if needed
                    await client.send_message(
                        entity, p["message"], parse_mode="markdown"
                    )
                    out.append(f"Shared: {p['name']}")
                except Exception as e:
                    out.append(f"Failed {p['name']}: {e}")
        return out

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sent = loop.run_until_complete(run_send())
        loop.close()
        return JsonResponse({"status": "success", "results": sent})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@csrf_exempt
def send_status_to_telegram(request, IPOid):
    """Send status details to Telegram"""
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Only POST method allowed"}, status=405
        )

    try:
        user = request.user
        custom_user = CustomUser.objects.get(username=user)
    except CustomUser.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "User not found"}, status=404
        )

    if not custom_user.Telegram_session:
        messages.error(request, "Telegram session not verified yet")
        return JsonResponse(
            {
                "status": "session_expired",
                "message": "Telegram session not verified yet",
            },
            status=400,
        )

    try:
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    except CurrentIpoName.DoesNotExist:
        return JsonResponse({"status": "error", "message": "IPO not found"}, status=404)

    # Get all orders for this IPO
    products = Order.objects.filter(user=user, OrderIPOName_id=IPOid)

    # Initialize dictionaries for calculations
    dict_count = {}
    dict_avg = {}
    dict_amount = {}

    # Define order types and categories
    OrdTyp = ["BUY", "SELL"]
    OrdCat = ["Kostak", "SubjectTo"]
    InvTyp = (
        ["RETAIL", "SHNI", "BHNI"] if IPOName.IPOType == "MAINBOARD" else ["RETAIL"]
    )

    # Calculate counts, averages, and amounts
    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                if ordercategory == "SubjectTo":
                    x = products.filter(
                        OrderType=ordertype,
                        OrderCategory="Subject To",
                        InvestorType=investortype,
                    )
                else:
                    x = products.filter(
                        OrderType=ordertype,
                        OrderCategory=ordercategory,
                        InvestorType=investortype,
                    )

                count = x.aggregate(Sum("Quantity"))["Quantity__sum"]
                if count is None:
                    dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = 0
                    z = 0
                else:
                    dict_count[f"{ordercategory}{investortype}{ordertype}Count"] = count
                    z = count

                amount = 0
                for i in x:
                    if i.OrderCategory == "Subject To":
                        if i.Method == "Premium":
                            if investortype == "RETAIL":
                                lot_size = IPOName.LotSizeRetail
                            if investortype == "SHNI":
                                lot_size = IPOName.LotSizeSHNI
                            if investortype == "BHNI":
                                lot_size = IPOName.LotSizeBHNI
                            amount = ((lot_size * i.Rate) * i.Quantity) + amount
                        else:
                            amount = i.Rate + amount
                    else:
                        amount = i.Rate + amount

                if z == 0:
                    dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = 0
                else:
                    dict_avg[f"{ordercategory}{investortype}{ordertype}Avg"] = (
                        amount / z
                    )

                dict_amount[f"{ordercategory}{investortype}{ordertype}Amount"] = amount

    # Calculate net values
    net_count = {}
    net_avg = {}
    net_amount = {}

    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"

            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0

            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)

    # Calculate Premium data
    PremiumBuyfilter = products.filter(OrderType="BUY", OrderCategory="Premium")
    PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum("Quantity"))
    PremiumBuyCount1 = PremiumBuyCount11["Quantity__sum"]
    PremiumBuyCount = PremiumBuyCount1 if PremiumBuyCount1 is not None else 0

    PremiumBuyAmount = 0
    for i in PremiumBuyfilter:
        PremiumBuyAmount = (i.Quantity * i.Rate) + PremiumBuyAmount

    PremiumBuyAvg = PremiumBuyAmount / PremiumBuyCount if PremiumBuyCount != 0 else 0

    PremiumSellfilter = products.filter(OrderType="SELL", OrderCategory="Premium")
    PremiumSellCount11 = PremiumSellfilter.aggregate(Sum("Quantity"))
    PremiumSellCount1 = PremiumSellCount11["Quantity__sum"]
    PremiumSellCount = PremiumSellCount1 if PremiumSellCount1 is not None else 0

    PremiumSellAmount = 0
    for i in PremiumSellfilter:
        PremiumSellAmount = (i.Quantity * i.Rate) + PremiumSellAmount

    PremiumSellAvg = (
        PremiumSellAmount / PremiumSellCount if PremiumSellCount != 0 else 0
    )

    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    PremiumNetAvg = PremiumNetAmount / PremiumNetCount if PremiumNetCount != 0 else 0

    # Build Telegram message
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"**📊 {IPOName.IPOName} - Status Report**",
        f"**🕒 Generated: {now_str}**",
        "",
    ]

    if IPOName.IPOType == "MAINBOARD":
        # Kostak section for MAINBOARD
        lines.append("**�� Kostak**")
        lines.append("**BUY:**")
        lines.append(
            f"  Retail: {dict_count.get('KostakRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILBUYAmount', 0):.2f}"
        )
        lines.append(
            f"  SHNI: {dict_count.get('KostakSHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakSHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakSHNIBUYAmount', 0):.2f}"
        )
        lines.append(
            f"  BHNI: {dict_count.get('KostakBHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakBHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakBHNIBUYAmount', 0):.2f}"
        )
        lines.append("")
        lines.append("**SELL:**")
        lines.append(
            f"  Retail: {dict_count.get('KostakRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILSELLAmount', 0):.2f}"
        )
        lines.append(
            f"  SHNI: {dict_count.get('KostakSHNISELLCount', 0):.0f} @ ₹{dict_avg.get('KostakSHNISELLAvg', 0):.2f} = ₹{dict_amount.get('KostakSHNISELLAmount', 0):.2f}"
        )
        lines.append(
            f"  BHNI: {dict_count.get('KostakBHNISELLCount', 0):.0f} @ ₹{dict_avg.get('KostakBHNISELLAvg', 0):.2f} = ₹{dict_amount.get('KostakBHNISELLAmount', 0):.2f}"
        )
        lines.append("")
        lines.append("**NET:**")
        lines.append(
            f"  Retail: {net_count.get('KostakRETAILNetCount', 0):.0f} @ ₹{net_avg.get('KostakRETAILNetAvg', 0):.2f} = ₹{net_amount.get('KostakRETAILNetAmount', 0):.2f}"
        )
        lines.append(
            f"  SHNI: {net_count.get('KostakSHNINetCount', 0):.0f} @ ₹{net_avg.get('KostakSHNINetAvg', 0):.2f} = ₹{net_amount.get('KostakSHNINetAmount', 0):.2f}"
        )
        lines.append(
            f"  BHNI: {net_count.get('KostakBHNINetCount', 0):.0f} @ ₹{net_avg.get('KostakBHNINetAvg', 0):.2f} = ₹{net_amount.get('KostakBHNINetAmount', 0):.2f}"
        )
        lines.append("")

        # Subject To section for MAINBOARD
        lines.append("**🔹 Subject To**")
        lines.append("**BUY:**")
        lines.append(
            f"  Retail: {dict_count.get('SubjectToRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILBUYAmount', 0):.2f}"
        )
        lines.append(
            f"  SHNI: {dict_count.get('SubjectToSHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToSHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToSHNIBUYAmount', 0):.2f}"
        )
        lines.append(
            f"  BHNI: {dict_count.get('SubjectToBHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToBHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToBHNIBUYAmount', 0):.2f}"
        )
        lines.append("")
        lines.append("**SELL:**")
        lines.append(
            f"  Retail: {dict_count.get('SubjectToRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILSELLAmount', 0):.2f}"
        )
        lines.append(
            f"  SHNI: {dict_count.get('SubjectToSHNISELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToSHNISELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToSHNISELLAmount', 0):.2f}"
        )
        lines.append(
            f"  BHNI: {dict_count.get('SubjectToBHNISELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToBHNISELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToBHNISELLAmount', 0):.2f}"
        )
        lines.append("")
        lines.append("**NET:**")
        lines.append(
            f"  Retail: {net_count.get('SubjectToRETAILNetCount', 0):.0f} @ ₹{net_avg.get('SubjectToRETAILNetAvg', 0):.2f} = ₹{net_amount.get('SubjectToRETAILNetAmount', 0):.2f}"
        )
        lines.append(
            f"  SHNI: {net_count.get('SubjectToSHNINetCount', 0):.0f} @ ₹{net_avg.get('SubjectToSHNINetAvg', 0):.2f} = ₹{net_amount.get('SubjectToSHNINetAmount', 0):.2f}"
        )
        lines.append(
            f"  BHNI: {net_count.get('SubjectToBHNINetCount', 0):.0f} @ ₹{net_avg.get('SubjectToBHNINetAvg', 0):.2f} = ₹{net_amount.get('SubjectToBHNINetAmount', 0):.2f}"
        )
        lines.append("")
    else:
        # Kostak section for SME
        lines.append("**�� Kostak**")
        lines.append("**BUY:**")
        lines.append(
            f"  Count: {dict_count.get('KostakRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILBUYAmount', 0):.2f}"
        )
        lines.append("**SELL:**")
        lines.append(
            f"  Count: {dict_count.get('KostakRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILSELLAmount', 0):.2f}"
        )
        lines.append("**NET:**")
        lines.append(
            f"  Count: {net_count.get('KostakRETAILNetCount', 0):.0f} @ ₹{net_avg.get('KostakRETAILNetAvg', 0):.2f} = ₹{net_amount.get('KostakRETAILNetAmount', 0):.2f}"
        )
        lines.append("")

        # Subject To section for SME
        lines.append("**🔹 Subject To**")
        lines.append("**BUY:**")
        lines.append(
            f"  Count: {dict_count.get('SubjectToRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILBUYAmount', 0):.2f}"
        )
        lines.append("**SELL:**")
        lines.append(
            f"  Count: {dict_count.get('SubjectToRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILSELLAmount', 0):.2f}"
        )
        lines.append("**NET:**")
        lines.append(
            f"  Count: {net_count.get('SubjectToRETAILNetCount', 0):.0f} @ ₹{net_avg.get('SubjectToRETAILNetAvg', 0):.2f} = ₹{net_amount.get('SubjectToRETAILNetAmount', 0):.2f}"
        )
        lines.append("")

    # Premium section
    lines.append("**🔹 Premium**")
    lines.append("**BUY:**")
    lines.append(
        f"  Count: {PremiumBuyCount:.0f} @ ₹{PremiumBuyAvg:.2f} = ₹{PremiumBuyAmount:.2f}"
    )
    lines.append("**SELL:**")
    lines.append(
        f"  Count: {PremiumSellCount:.0f} @ ₹{PremiumSellAvg:.2f} = ₹{PremiumSellAmount:.2f}"
    )
    lines.append("**NET:**")
    lines.append(
        f"  Count: {PremiumNetCount:.0f} @ ₹{PremiumNetAvg:.2f} = ₹{PremiumNetAmount:.2f}"
    )

    message = "\n".join(lines)

    async def send_message():
        try:
            async with TelegramClient(
                StringSession(custom_user.Telegram_session),
                int(custom_user.TelegramApi_id),
                custom_user.TelegramApi_key,
            ) as client:
                # Send to saved messages (yourself)
                await client.send_message("me", message, parse_mode="markdown")
                return {
                    "status": "success",
                    "message": "Status sent to Telegram successfully!",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    try:
        result = asyncio.run(send_message())
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@csrf_exempt
def send_status_to_telegram_image(request, IPOid):
    start_time = time.time()
    """Send status table as image to a single Telegram group"""
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Only POST method allowed"}, status=405
        )

    # ✅ Validate user
    try:
        user = request.user
        custom_user = CustomUser.objects.get(username=user)
    except CustomUser.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "User not found"}, status=404
        )

    if not custom_user.Telegram_session:
        messages.error(request, "Telegram session not verified yet")
        return JsonResponse(
            {
                "status": "session_expired",
                "message": "Telegram session not verified yet",
            },
            status=400,
        )

    # ✅ Validate IPO
    try:
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    except CurrentIpoName.DoesNotExist:
        return JsonResponse({"status": "error", "message": "IPO not found"}, status=404)

    # ✅ Validate image
    if "image" not in request.FILES:
        messages.error(request, "No image file provided")
        return JsonResponse(
            {"status": "error", "message": "No image file provided"}, status=400
        )

    image_file = request.FILES["image"]
    # from django.core.files.storage import default_storage
    # file_path = default_storage.save(f"{IPOid}_status.png", image_file)

    # ✅ Get Group ID (primary key) from POST
    group_id = request.POST.get("group_id")
    if not group_id:
        messages.error(request, "Group ID is required")
        return JsonResponse(
            {"status": "error", "message": "Group ID is required"}, status=400
        )

    try:
        group_detail = GroupDetail.objects.get(GroupName=group_id, user=request.user)
        group_name = group_detail.GroupName
        phone = group_detail.MobileNo
    except (GroupDetail.DoesNotExist, ValueError):
        messages.error(request, "Please select a valid group with mobile number")
        return JsonResponse(
            {"status": "error", "message": "Selected group not found"}, status=404
        )
    # ✅ Caption
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    caption = f"📊 {IPOName.IPOName} - Status Report\n🕒 Generated: {now_str}\n👥 Group: {group_name}"

    async def send_image():

        # async with TelegramClient(
        #     StringSession(custom_user.Telegram_session),
        #     int(custom_user.TelegramApi_id),
        #     custom_user.TelegramApi_key
        # ) as client:
        #     # Send to entity (group/user by phone)
        #     entity = await client.get_entity(f'+91{phone}')
        #     await client.send_file(
        #         entity,
        #         image_file,
        #         caption=caption,
        #         parse_mode='markdown'
        #     )

        #     messages.success(request, 'Status image sent to Telegram successfully!');
        #     return {'status': 'success', 'message': 'Status image sent to Telegram successfully!'}
        client = TelegramClient(
            StringSession(custom_user.Telegram_session),
            int(custom_user.TelegramApi_id),
            custom_user.TelegramApi_key,
        )
        await client.start()

        entity = await client.get_entity(f"+91{phone}")
        await client.send_file(
            entity, image_file, caption=caption, parse_mode="markdown"
        )

        await client.disconnect()

    # ✅ Save uploaded file temporarily
    try:
        # with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        #     for chunk in image_file.chunks():
        #         tmp.write(chunk)
        #     temp_path = tmp.name

        # Run async safely
        # result = async_to_sync(send_image)()
        asyncio.run(send_image())
        messages.success(request, "Status image sent to Telegram successfully!")

        return JsonResponse(
            {
                "status": "success",
                "message": "Status image sent to Telegram successfully!",
            }
        )

    except Exception as e:
        messages.error(
            request, f" Please enter a mobile number for the {group_name} group ."
        )
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def accounting_view(request):
    show_all = request.GET.get("show_all")
    entries = Accounting.objects.filter(user=request.user)
    IPO_DropDown = []
    for entry in entries:
        name = entry.ipo_name
        if name and name not in IPO_DropDown:
            IPO_DropDown.append(name)

    Group_DropDown = []
    for entry in entries:
        gname = entry.group_name
        if gname and gname not in Group_DropDown:
            Group_DropDown.append(gname)
        # if entry.ipo_id:  # FK exists
        #     IPO_DropDown.append(entry.ipo.IPOName)  # from related IPO table
        # else:
        #     IPO_DropDown.append(entry.ipo_name or "")  # from local field

    # group_id = request.GET.get("group_id")
    # ipo_id = request.GET.get("ipo_id")
    group_name = request.GET.get("group_name")  # string instead of group_id
    ipo_name = request.GET.get("ipo_name")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    # if group_id:
    #     entries = entries.filter(group_id=group_id)
    # if ipo_id:
    #     entries = entries.filter(ipo_id=ipo_id)
    # if date_from:
    #     date_from_obj = datetime.fromisoformat(date_from).date()  # extract date only
    #     entries = entries.filter(date_time__date__gte=date_from_obj)
    # if date_to:
    #     date_to_obj = datetime.fromisoformat(date_to).date()  # extract date only
    #     entries = entries.filter(date_time__date__lte=date_to_obj)
    # grouped_entries = {}
    if ipo_name:
        entries = entries.filter(
            Q(ipo__IPOName__iexact=ipo_name) | Q(ipo_name__iexact=ipo_name)
        )

    # --- filter by group_name string ---
    if group_name:
        entries = entries.filter(
            Q(group__GroupName__iexact=group_name) | Q(group_name__iexact=group_name)
        )

    # --- filter by dates ---
    if date_from:
        date_from_obj = datetime.fromisoformat(date_from).date()
        entries = entries.filter(date_time__date__gte=date_from_obj)

    if date_to:
        date_to_obj = datetime.fromisoformat(date_to).date()
        entries = entries.filter(date_time__date__lte=date_to_obj)
    # for e in entries:
    #     group_name = e.group.GroupName if e.group else "N/A"
    #     grouped_entries.setdefault(group_name, []).append(e)
    # print("jv", entries.filter(jv=True).count())
    # print("jv", entries.filter(jv=False).count())
    # print("total", entries.count())
    # Build HTML table

    jv_filter = request.GET.get("jv")
    if jv_filter == "1":
        entries = entries.filter(jv=True)
    elif jv_filter == "0":
        entries = entries.filter(jv=False)

    order_by = request.GET.get("order_by")  # column name to sort
    order_dir = request.GET.get("order_dir", "asc")  # 'asc' or 'desc'
    if order_by:
        if order_by == "ipo":
            sort_field = "ipo__IPOName"
        elif order_by == "group":
            sort_field = "group__GroupName"
        else:
            sort_field = order_by
        if order_dir == "desc":
            sort_field = f"-{sort_field}"
        entries = entries.order_by(sort_field)

    # Calculate total credit, debit, and net per group (JV=True)
    jv_sums = (
        Accounting.objects.filter(jv=True)
        .values("group__GroupName")
        .annotate(
            total_credit=Sum(
                Case(
                    When(amount_type="credit", then=F("amount")),
                    default=0,
                    output_field=FloatField(),
                )
            ),
            total_debit=Sum(
                Case(
                    When(amount_type="debit", then=F("amount")),
                    default=0,
                    output_field=FloatField(),
                )
            ),
            net=Sum(
                Case(
                    When(amount_type="credit", then=F("amount")),
                    When(amount_type="debit", then=-F("amount")),
                    output_field=FloatField(),
                )
            ),
        )
    )
    jv_sum_dict = {item["group__GroupName"]: item for item in jv_sums}
    ipo_name = request.GET.get("ipo_name")

    # # Check in database
    # if e.ipo:
    #     ipo_display = e.ipo.IPOName
    # elif ipo_obj:
    #     ipo_display = ipo_obj.ipo.IPOName if ipo_obj.ipo else ipo_obj.ipo_name
    # else:
    #     ipo_display = ''

    rows = ""
    credit_amount = 0
    debit_amount = 0
    for e in entries:
        if e.amount_type == "credit":
            credit_amount = credit_amount + e.amount
        else:
            debit_amount = debit_amount + e.amount
        # Priority 1: Use IPO from entry
        if e.ipo:  # If FK exists
            ipo_display = e.ipo.IPOName
        elif e.ipo_name:  # Fallback to stored field
            ipo_display = e.ipo_name
        else:
            ipo_display = "JV"
        if e.group:  # FK exists
            group_name1 = e.group.GroupName
        else:
            group_name1 = e.group_name or ""
        group_jv_total = jv_sum_dict.get(group_name1, 0)  # Only sum for jv=True
        rows += f"""
        <tr>
            <td>{ipo_display}</td>
            <td>{group_name1}</td>
            <td><span class="badge {'bg-success' if e.amount_type=='credit' else 'bg-danger'}">{e.amount_type}</span></td>
            <td>{e.amount}</td>
            <td><textarea class="form-control form-control-sm" readonly>{e.remark or ''}</textarea></td>
            
            <td>{timezone.localtime(e.date_time).strftime("%d-%m-%y %H:%M:%S")}</td>
            
        </tr>
        """

    net_amount = credit_amount - debit_amount
    html_table = "<table >\n"
    html_table = (
        "<thead><tr style='text-align: center;white-space: nowrap; width:100%' >"
    )
    html_table += "<th>IPO</th>"
    html_table += "<th>Group</th>"
    html_table += "<th>Amount Type</th>"
    html_table += "<th>Amount</th>"
    html_table += "<th>Remark</th>"
    html_table += "<th>Date Time</th>"
    html_table += "</tr></thead>\n"
    html_table += (
        f"<tbody style='text-align: center;white-space: nowrap;'> {rows} </tbody>\n"
    )
    html_table += "</table>"

    # html_table = f"""
    # <table id="example" class="table table-bordered table-hover table-striped dataTable no-footer">
    #     <thead>
    #         <tr>
    #             <th>IPO</th>
    #             <th>Group</th>
    #             <th>Amount Type</th>
    #             <th>Amount</th>
    #             <th>Remark</th>
    #             <th>Date Time</th>
    #         </tr>
    #     </thead>
    #     <tbody>
    #         {rows}
    #     </tbody>
    # </table>
    # """

    ipos_master = CurrentIpoName.objects.filter(user=request.user)
    groups_master = GroupDetail.objects.filter(user=request.user)

    return render(
        request,
        "accounting.html",
        {
            "entries": entries,  # Pass the entries queryset to the template
            "html_table": format_html(html_table),
            "ipos": IPO_DropDown,
            "groups": Group_DropDown,
            "ipos1": ipos_master,  # For Add JV Transaction modal
            "groups1": groups_master,
            "selected_group": group_name,
            "selected_ipo": ipo_name,
            "date_from": date_from,
            "date_to": date_to,
            "debit_amount": debit_amount,
            "credit_amount": credit_amount,
            "Net_amount": net_amount,
        },
    )


def get_accounting_entries(request):
    try:
        group_id = request.GET.get("group_id")
        ipo_id = request.GET.get("ipo_id")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        entries = Accounting.objects.filter(user=request.user).order_by("-date_time")

        if group_id:
            entries = entries.filter(group_id=group_id)
        if ipo_id:
            entries = entries.filter(ipo_id=ipo_id)
        if date_from and date_to:
            entries = entries.filter(date_time__date__range=[date_from, date_to])

        # Include ipo_id and group_id for JS
        entries_data = [
            {
                "ipo": entry.ipo.IPOName if entry.ipo else "N/A",
                "ipo_id": entry.ipo.id if entry.ipo else None,
                "group": entry.group.GroupName if entry.group else "N/A",
                "group_id": entry.group.id if entry.group else None,
                "amount_type": entry.amount_type.lower(),
                "amount": str(entry.amount),
                "remark": entry.remark or "",
                "jv": "Yes" if entry.jv else "No",
                "date_time": entry.date_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for entry in entries
        ]

        return JsonResponse(
            {
                "data": entries_data,
                "ipos": [
                    {"id": ipo.id, "name": ipo.IPOName}
                    for ipo in CurrentIpoName.objects.filter(user=request.user)
                ],
                "groups": [
                    {"id": g.id, "name": g.GroupName}
                    for g in GroupDetail.objects.filter(user=request.user)
                ],
            }
        )
    except Exception as e:
        messages.error(request, f" Error fetching accounting entries .")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def delete_accounting_entries(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            entry_ids = data.get("entry_ids", [])

            if not entry_ids:
                return JsonResponse(
                    {"status": "error", "message": "No entries selected for deletion"},
                    status=400,
                )

            # Delete the entries
            deleted_count = Accounting.objects.filter(
                id__in=entry_ids,
                user=request.user,  # Ensure user can only delete their own entries
            ).delete()[0]

            if deleted_count > 0:
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"Successfully deleted {deleted_count} entries",
                    }
                )
            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "No entries found or you do not have permission to delete them",
                    },
                    status=400,
                )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            print(f"Error deleting accounting entries: {e}")

            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )


# views.py


def save_transaction(request):
    if request.method == "POST":
        user = request.user
        ipo_id = request.POST.get("ipo_id")
        group_id = request.POST.get("group_id")
        amount_type = request.POST.get("amount_type")
        amount = request.POST.get("amount")
        remark = request.POST.get("remark") or ""
        date_time = request.POST.get("date_time")
        date_time = parse_datetime(date_time) if date_time else timezone.now()

        jv_group_id = request.POST.get("jv_group_id")
        # jv_remark: $('#jv_remark').val(),
        jv_remark1 = request.POST.get("jv_remark")

        # Get IPO and Group names
        ipo_obj = CurrentIpoName.objects.filter(id=ipo_id).first()
        group_obj = GroupDetail.objects.filter(id=group_id).first()
        ipo_name = ipo_obj.IPOName if ipo_obj else f"IPO ID {ipo_id}"
        group_name = group_obj.GroupName if group_obj else f"Group ID {group_id}"

        # default_remark = f"JV from {group_name} for {ipo_name}"
        # jv_remark1 = f"{default_remark}  {jv_remark}"

        try:
            # Non-JV entry
            first_entry = Accounting.objects.create(
                user=user,
                ipo_id=ipo_id,
                group_id=group_id,
                amount=amount,
                amount_type=amount_type,
                remark=remark,
                date_time=date_time,
                jv=0,
            )

            # JV entry
            # Second entry (opposite - JV=1)
            opposite_type = "debit" if amount_type == "credit" else "credit"

            second_entry = Accounting.objects.create(
                user=user,
                ipo_id=None,
                group_id=jv_group_id,
                amount=amount,
                amount_type=opposite_type,
                remark=jv_remark1,
                date_time=date_time,
                jv=1,
            )

            return redirect("accounting")
            # return JsonResponse({"status": "success"})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})


def save_transaction_group(request):
    if request.method == "POST":
        user = request.user
        ipo_id = request.POST.get("ipo_id")
        group_id = request.POST.get("group_id")
        amount_type = request.POST.get("amount_type")
        amount = request.POST.get("amount")
        remark = request.POST.get("remark") or ""
        date_time = request.POST.get("date_time")
        date_time = parse_datetime(date_time) if date_time else timezone.now()

        jv_group_id = request.POST.get("jv_group_id")
        # jv_remark: $('#jv_remark').val(),
        jv_remark1 = request.POST.get("jv_remark")

        # Get IPO and Group names
        ipo_obj = CurrentIpoName.objects.filter(id=ipo_id).first()
        group_obj = GroupDetail.objects.filter(id=group_id).first()
        ipo_name = ipo_obj.IPOName if ipo_obj else f"IPO ID {ipo_id}"
        group_name = group_obj.GroupName if group_obj else f"Group ID {group_id}"

        # default_remark = f"JV from {group_name} for {ipo_name}"
        # jv_remark1 = f"{default_remark}  {jv_remark}"

        try:
            # Non-JV entry
            first_entry = Accounting.objects.create(
                user=user,
                ipo_id=ipo_id,
                group_id=group_id,
                amount=amount,
                amount_type=amount_type,
                remark=remark,
                date_time=date_time,
                jv=0,
            )

            # JV entry
            # Second entry (opposite - JV=1)
            opposite_type = "debit" if amount_type == "credit" else "credit"

            second_entry = Accounting.objects.create(
                user=user,
                ipo_id=None,
                group_id=jv_group_id,
                amount=amount,
                amount_type=opposite_type,
                remark=jv_remark1,
                date_time=date_time,
                jv=1,
            )

            return redirect("GroupWiseDashboard")
            # return JsonResponse({"status": "success"})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})


def add_transaction(request):
    user = request.user
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")

        jv = 1 if request.POST.get("jv") == "1" else 0

        ipo_id = request.POST.get("ipo_id") if jv == 0 else None
        group_id = request.POST.get("group_id")
        amount_type = request.POST.get("amount_type")
        amount = request.POST.get("amount")
        remark = request.POST.get("remark")
        date_time_str = request.POST.get("date_time")

        # date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M")
        # date_time = timezone.make_aware(date_time)  # optional if using timezone-aware field
        # date_time = parse_datetime(date_time_str) if date_time_str else timezone.now()
        if date_time_str:
            # Add seconds if missing
            if len(date_time_str) == 16:  # "YYYY-MM-DDTHH:MM"
                date_time_str += ":00"
            date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M:%S")

            # make timezone aware
            if timezone.is_aware(date_time):
                date_time = timezone.make_aware(
                    date_time, timezone.get_current_timezone()
                )
        else:
            date_time = timezone.localtime().replace(tzinfo=None)

        Accounting.objects.create(
            user=user,
            ipo_id=ipo_id,
            group_id=group_id,
            amount_type=amount_type,
            amount=amount,
            remark=remark,
            date_time=date_time,
            jv=jv,
        )
        return redirect("accounting")  # reload the same page after save

    # if GET request → render form
    from .models import IPO, Group

    ipos = IPO.objects.filter(user=request.user)
    groups = Group.objects.filter(user=request.user)
    return render(
        request,
        "accounting/Accounting.html",
        {"ipos": ipos, "groups": groups, "now": timezone.localtime()},
    )


def add_transaction_group(request):
    user = request.user
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")

        jv = 1 if request.POST.get("jv") == "1" else 0

        ipo_id = request.POST.get("ipo_id") if jv == 0 else None
        group_id = request.POST.get("group_id")
        amount_type = request.POST.get("amount_type")
        amount = request.POST.get("amount")
        remark = request.POST.get("remark")
        date_time_str = request.POST.get("date_time")

        # date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M")
        # date_time = timezone.make_aware(date_time)  # optional if using timezone-aware field
        # date_time = parse_datetime(date_time_str) if date_time_str else timezone.now()
        if date_time_str:
            # Add seconds if missing
            if len(date_time_str) == 16:  # "YYYY-MM-DDTHH:MM"
                date_time_str += ":00"
            date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M:%S")

            # make timezone aware
            if timezone.is_aware(date_time):
                date_time = timezone.make_aware(
                    date_time, timezone.get_current_timezone()
                )
        else:
            date_time = timezone.localtime().replace(tzinfo=None)

        Accounting.objects.create(
            user=user,
            ipo_id=ipo_id,
            group_id=group_id,
            amount_type=amount_type,
            amount=amount,
            remark=remark,
            date_time=date_time,
            jv=jv,
        )
        return redirect("GroupWiseDashboard")  # reload the same page after save

    # if GET request → render form
    from .models import IPO, Group

    ipos = IPO.objects.filter(user=request.user)
    groups = Group.objects.filter(user=request.user)
    return render(
        request,
        "GroupWiseDashboard.html",
        {"ipos": ipos, "groups": groups, "now": timezone.localtime()},
    )


def send_group_email(
    request,
    group_data,
    IPOName,
    entry,
    record_type,
    user_email,
    user_app_pw,
    request_user,
    OrderType,
):
    try:
        group = unquote(group_data["name"])
        group_email = group_data["email"]

        GP = GroupDetail.objects.get(GroupName=group, user=request_user)
        gid = GP.id
        if not group_email:
            group_email = GP.Email
        if not group_email:
            messages.info(request, f"Email ID is not avaliable for '{group}' Group ,")
            return  # Skip if no email
        try:
            validate_email(group_email)
        except ValidationError:
            messages.info(
                request,
                f"Failed to share Group Details: '{group}' has an invalid email address.",
            )
            return  # Skip if not valid email

        filtered_entry = entry.filter(Order__OrderGroup_id=gid)
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(
            [
                "Group",
                "IPO Type",
                "Investor Type",
                "Rate",
                "PAN No",
                "Client Name",
                "AllotedQty",
                "Demat Number",
                "Application Number",
                "Order Date",
                "Order Time",
            ]
        )

        if record_type == "Pending PAN":
            rows = filtered_entry.filter(OrderDetailPANNo_id=None)
        else:
            rows = filtered_entry

        for member in rows.values_list(
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__InvestorType",
            "Order__Rate",
            "OrderDetailPANNo__PANNo",
            "OrderDetailPANNo__Name",
            "AllotedQty",
            "DematNumber",
            "ApplicationNumber",
            "Order__OrderDate",
            "Order__OrderTime",
        ):
            List = list(member)
            List[9] = str(List[9].strftime("%d/%m/%Y"))
            if List[7] != "":
                List[7] = "'" + List[7]
            writer.writerow(tuple(List))

        csv_content = csv_buffer.getvalue()
        msg = MIMEMultipart()
        msg["Subject"] = "Update Required – Missing Details in Attached File"
        msg["From"] = user_email
        msg["To"] = group_email

        if OrderType == "BUY":

            body = f"""\
                Dear {group},\n
                Please find the attached document which requires your input. We kindly ask you to provide the following missing information:

                • PAN Number (Mandatory)
                • Name
                • Client ID
                • DP ID
                • Application Number

                Once completed, please reply to this email with the updated file.

                """
        else:
            body = f"""\
                Dear {group},\n
                Please find attached the Excel related to your recent orders.\n

                Regards,\n
                
                """

        msg.attach(MIMEText(body, "plain"))

        part = MIMEApplication(csv_content, Name=f"{group}_{IPOName.IPOName}.csv")
        part["Content-Disposition"] = (
            f'attachment; filename="{group}_{IPOName.IPOName}.csv"'
        )
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(user_email, user_app_pw)
            smtp.send_message(msg)

    except ValidationError:
        messages.info(request, f"Invalid email: {group_email}")
    except Exception as e:
        messages.info(request, f"Failed to send email to group {group}: {e}")


def GroupBillShare(request, IPOid):
    if request.method == "POST":
        # Ensure the user is authenticated to get their email
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to share bills.")
            return redirect("login_url")  # Redirect to your login page

        group_name = request.POST.get("GroupName", "Default Group")

        # Get the currently logged-in user's email
        # This email will be used as the 'From' address in the email header.
        EMAIL_ADDRESS = "dipakbhadaniya09@gmail.com"  # Your personal email
        EMAIL_PASSWORD = "dpxw slhx hqiy dtyu"  # App password (not your login password)

        subject = f"Bill for {group_name} - IPO ID: {IPOid}"
        message = f"""
        Dear Customer,

        Please find the bill details for {group_name} related to IPO ID {IPOid}.

        [Insert actual bill content here.]

        Thank you.
        """
        # The 'from_email' parameter is set to the current user's email
        recipient_list = [
            "bhadaniyadb2001@gmail.com"
        ]  # Replace with actual recipient email(s)

        try:
            msg = MIMEMultipart()  # Change EmailMessage to MIMEMultipart
            msg["Subject"] = subject
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = "bhadaniyadb2001@gmail.com"  # Change to the receiver's email

            text_content = MIMEText(message)
            msg.attach(text_content)

            file_path = "home/views.py"  # Replace with the path to your file

            with open(file_path, "rb") as f:
                file_data = f.read()
                file_name = f.name

            attached_file = MIMEApplication(
                file_data, _subtype="json"
            )  # Adjust _subtype if necessary (e.g., 'pdf', 'jpeg')
            attached_file.add_header(
                "Content-Disposition", "attachment", filename=file_name
            )
            msg.attach(attached_file)

            # Send the email using Gmail's SMTP server
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)

            messages.success(
                request,
                f'Bill for {group_name} shared successfully from {EMAIL_ADDRESS} to {", ".join(recipient_list)}!',
            )
        except Exception as e:
            messages.error(request, f"Failed to share bill: {e}")

        return redirect("Status", IPOid=IPOid)
    else:
        messages.error(request, "Invalid request method for sharing bill.")
        return redirect("Status", IPOid=IPOid)


@csrf_exempt
def Share_AppDetails(request):
    if request.method == "POST":
        group_name_list_json = request.POST.get("selected_records", "Default Group")
        group_name_list = json.loads(group_name_list_json)
        record_type = request.POST.get("record_type", "All Record")
        IPO_id = request.POST.get("IPO_id", "")
        OrderType = request.POST.get("OrderType", "")

        Custom_user = CustomUser.objects.get(username=request.user)
        user_email = Custom_user.email
        user_app_pw = Custom_user.AppPassword
        # user_app_pw = ''

        if not user_email:
            messages.info(request, f"Email configuration is pending for {request.user}")
            return JsonResponse("Success", safe=False)
        if not user_app_pw:
            messages.info(request, f"Email configuration is pending for {request.user}")
            return JsonResponse("Success", safe=False)

        IPOName = CurrentIpoName.objects.get(id=IPO_id, user=request.user)
        entry = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPO_id
        )

        if OrderType == "BUY":
            entry = entry.filter(Order__OrderType="BUY")
        if OrderType == "SELL":
            entry = entry.filter(Order__OrderType="SELL")

        # for group_data in group_name_list:
        #     group = unquote(group_data['name'])
        #     group_email = group_data['email']

        #     GP = GroupDetail.objects.get(
        #         GroupName=group, user=request.user)

        #     gid = GP.id
        #     if not group_email:
        #         group_email = GP.Email

        #     if not group_email:
        #         messages.error(request, f"Failed to share Group Details: '{group}' has no associated email address.")
        #         continue
        #     try:
        #         validate_email(group_email)
        #     except ValidationError:
        #         messages.error(request, f"Failed to share Group Details: '{group}' has an invalid email address.")
        #         continue

        #     entry_forGp = entry.filter(Order__OrderGroup_id=gid)

        #     csv_buffer = StringIO()

        #     writer = csv.writer(csv_buffer)
        #     writer.writerow(['Group', 'IPO Type', 'Investor Type', 'Rate', 'PAN No',
        #                     'Client Name', 'AllotedQty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time'])

        #     if record_type == 'Pending PAN':
        #         for member in entry_forGp.filter(OrderDetailPANNo_id=None).values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType','Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty','DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime'):
        #             List = list(member)
        #             List[9] = str(List[9].strftime('%d/%m/%Y'))
        #             if List[7] != "":
        #                 List[7] = "'" + List[7]
        #             member = tuple(List)
        #             writer.writerow(member)
        #     else:
        #         for member in entry_forGp.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType','Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty','DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime'):
        #             List = list(member)
        #             List[9] = str(List[9].strftime('%d/%m/%Y'))
        #             if List[7] != "":
        #                 List[7] = "'" + List[7]
        #             member = tuple(List)
        #             writer.writerow(member)

        #     csv_content = csv_buffer.getvalue()

        #     # recipient_list = [group_email]

        #     try:
        #         msg = MIMEMultipart()  # Change EmailMessage to MIMEMultipart
        #         msg['Subject'] = f'IPO Details for Group: {group} ({IPOName.IPOName})'
        #         msg['From'] = user_email
        #         msg['To'] = group_email

        #         msg.attach(MIMEText('Please find the attached IPO details CSV.', 'plain'))

        #         part = MIMEApplication(csv_content, Name=f'{group}_{IPOName.IPOName}.csv')
        #         part['Content-Disposition'] = f'attachment; filename="{group}_{IPOName.IPOName}.csv"'
        #         msg.attach(part)

        #         with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        #             smtp.login(user_email, user_app_pw)
        #             smtp.send_message(msg)

        #         # messages.success(request, f'Bill for {group} shared successfully from {user_email} to {", ".join(recipient_list)}!')

        #     except Exception as e:
        #         traceback.print_exc()
        #         messages.error(request, f'Failed to share Group Details: {e}')

        # if group_name_list:
        threads = []
        for group_data in group_name_list:
            t = threading.Thread(
                target=send_group_email,
                args=(
                    request,
                    group_data,
                    IPOName,
                    entry,
                    record_type,
                    user_email,
                    user_app_pw,
                    request.user,
                    OrderType,
                ),
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        return JsonResponse("Success", safe=False)
