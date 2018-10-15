# -*- coding: utf8 -*-

import os
import base64
import requests
from urllib.parse import urlencode
#추가
import json
import pymssql
from bs4 import BeautifulSoup
from time import sleep
import datetime, time
import re

# Flask 인스턴스 생성
from flask import Flask
from flask import render_template
from flask import request, session, redirect, url_for, escape
from flask import send_from_directory

app = Flask (__name__)
img_root = 'static/image/'

DB_SERVER = '127.0.0.1:1433\MYTEST'
DB_USER = 'test'
DB_PASS = 'test1234'

@app.route("/test")
def test():
    return render_template("test.html")
# 인덱스  ( 아이디 / 이미지 목록 )
@app.route('/')
def index():
    values = request.values
    result = ''
    connection = pymssql.connect(
        host=DB_SERVER,
        user=DB_USER,
        password=DB_PASS,
        database='testdb',
        port=1433,
        tds_version='7.0'
    )

    try:
        with connection.cursor() as cursor:
            if values.get("search"):
                query = '''
                SELECT * FROM IDLIST WHERE id LIKE %s ORDER BY indate DESC
                '''
                cursor.execute(query,("%"+values.get('search')+"%"))
            else:
                query = '''
                SELECT * FROM IDLIST ORDER BY indate DESC
                '''
                cursor.execute(query)
            result = cursor.fetchall()
    except _mssql.MssqlDatabaseException as e:
        application.logger.error(e)
    except Exception as e:
        application.logger.error(e)
    finally:
        connection.close()

    # 파일명 불러오기
    filenames = []
    for root, dirs, files in os.walk(img_root):
        for file in files:
            filenames.append(file)

    # 현재상태 크롤링
    now = crolling_all(result)

    return render_template('index.html',
    result = result,
    filenames = filenames,
    now=now)

# 데이터베이스 삽입전 추출검사결과 뷰
@app.route('/extraction/')
def result():
    start = time.time()
    result, language, img_count, not_img, extraction_count = sample()
    end = time.time()

    return render_template('result.html',
    result = result,
    language = language,
    img_count = img_count,
    not_img = not_img,
    extraction_count = extraction_count,
    delay = int(end-start)
    )

# 해당 아이디 대쉬보드 상세보기
@app.route('/detail/<id>')
def detail(id):
    # 크롤링
    now = crolling_one(id)
    # 팔로우,언팔로우 그래프 데이터
    grape1 = []
    # 댓글, 공감 그래프 데이터
    grape2 = []
    # 보여줄 데이터수
    total = request.values.get('total')

    connection = pymssql.connect(
        host=DB_SERVER,
        user=DB_USER,
        password=DB_PASS,
        database='testdb',
        port=1433,
        tds_version='7.0'
    )
    try:
        with connection.cursor() as cursor:
            query = '''
            SELECT * FROM DETAILLIST WHERE id=%s ORDER BY indate DESC
            '''
            cursor.execute(query,(id))
            result = cursor.fetchall()

            i = len(result)
            for li in result:
                i=i-1

                if li[2] and li[3] :
                    grape1.append( [ i, int(li[2]), int(li[3]) ] )
                elif (not li[2]) and (not li[3]) :
                    grape1.append( [ i, 0, 0 ] )
                elif not li[2]:
                    grape1.append( [ i, 0, int(li[3]) ] )
                elif not li[3]:
                    grape1.append( [ i, int(li[2]), 0 ] )

                if li[4] and li[5] :
                    grape2.append( [ i, int(li[4]), int(li[5]) ] )
                elif (not li[4]) and (not li[5]) :
                    grape2.append( [ i, 0, 0 ] )
                elif not li[4]:
                    grape2.append( [ i, 0, int(li[5]) ] )
                elif not li[5]:
                    grape2.append( [ i, int(li[4]), 0 ] )

                # 최근 데이터 개수 제한걸기
                if total:
                    if i==0:
                        break
                else:
                    if len(result) < 10:
                        if i==0:
                            break
                    else:
                        if i == (len(result))-10:
                            break

    except _mssql.MssqlDatabaseException as e:
        application.logger.error(e)
    except Exception as e:
        application.logger.error(e)
    finally:
        connection.close()

    if total:
        pass
    else:
        result = result[:10]
    return render_template('detail.html',
    id=id,
    now=now,
    grape1=grape1,
    grape2=grape2,
    result=result,
    total=total)

# 데이터베이스삽입
@app.route('/insert')
def insert_data():
    result, language, img_count, not_img, extraction_count = sample()

    connection = pymssql.connect(
        host=DB_SERVER,
        user=DB_USER,
        password=DB_PASS,
        database='testdb',
        port=1433,
        tds_version='7.0'
    )

    if os.path.exists("static/mo/"):
        pass
    else:
        os.mkdir("static/mo/")

    try:
        with connection.cursor() as cursor:

            for id in result.keys():
                query = '''
                SELECT * FROM IDLIST WHERE id=%s
                '''
                cursor.execute(query,(id))
                exist = cursor.fetchone()
                # IDLIST에 해당 아이디가 이미 있을 경우 ( 중복 방지 )
                if exist:
                    pass
                else:
                    query = '''
                    INSERT INTO IDLIST(id) values(%s)
                    '''
                    cursor.execute(query,(id))
                    connection.commit()
                for li in result[id]:
                    query = '''
                    INSERT INTO DETAILLIST(id, follwing, unfollwing, reply, likeyou, posting, filename)
                    VALUES(%s, %s, %s, %s, %s, %s, %s)
                    '''
                    cursor.execute(query,(li.get('id'), li.get('follwing'), li.get('unfollwing'), li.get('reply'), li.get('like'), li.get('posting'), li.get('file')))
                    connection.commit()
                    if  os.path.exists(img_root+li.get('file')):
                        os.rename(img_root+li.get('file'), "static/mo/"+li.get('file'))
                    sleep(0.005)

    except _mssql.MssqlDatabaseException as e:
        application.logger.error(e)
    except Exception as e:
        application.logger.error(e)
    finally:
        connection.close()

    return redirect(url_for('index'))

# 전체데이터삭제
@app.route('/deleteall')
def delete_all():
    values = request.values
    connection = pymssql.connect(
        host=DB_SERVER,
        user=DB_USER,
        password=DB_PASS,
        database='testdb',
        port=1433,
        tds_version='7.0'
    )
    try:
        with connection.cursor() as cursor:
            if values.get('id'):
                id = values.get('id')
                query = '''
                DELETE FROM IDLIST WHERE id=%s;
                DELETE FROM DETAILLIST WHERE id=%s;
                '''
                cursor.execute(query,(id,id))
            else:
                query = '''
                DELETE FROM IDLIST;
                DELETE FROM DETAILLIST;
                '''
                cursor.execute(query)
            connection.commit()
    except _mssql.MssqlDatabaseException as e:
        application.logger.error(e)
    except Exception as e:
        application.logger.error(e)
    finally:
        connection.close()

    return redirect(url_for('index'))

# 이미지파일 펼처보기
@app.route('/imglist')
def img_list():
    filenames = []
    for root, dirs, files in os.walk(img_root):
        files.sort()
        for file in files:
            filenames.append(file)

    return render_template('imglist.html',
    filenames = filenames)

# ajax 단일 샘플링
@app.route('/sampling')
def sample_aj():
    values = request.values
    file = values.get('file')

    headers = {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': AZURE_API_KEY,
    }
    params = urlencode({
        # Request parameters
        'detectOrientation ': 'ture',
    })
    params2 = urlencode({
        # Request parameters
        'language': 'en',
        'detectOrientation ': 'ture',
    })
    url = 'https://eastasia.api.cognitive.microsoft.com/vision/v1.0/ocr'

    mylist = {} # 결과를 따로 저장할 배열
    extraction_count = 0

    if allowed_file(file) :
        with open(img_root+'/'+file, 'rb') as f:
            data = f.read()
        while True:
            try:
                # 한글(자동인식)검사 ko ( id제외 나머지 추출용 )
                response = requests.post(
                    url,
                    headers=headers,
                    params=params,
                    data=data
                )
                # 영문 검사 en ( id추출용 )
                response2 = requests.post(
                    url,
                    headers=headers,
                    params=params2,
                    data=data
                )
                break
            except Exception as e:
                print (e)
                time.sleep(30)

        if response.status_code == 429:
            print ( response)
            time.sleep(30)

        result = response.text # 이미지에서 추출한 텍스트를 json형식의 str타입으로 반환
        re_dict = json.loads(response.text) # str타입을 dict타입으로 변환
        language = re_dict['language']
        data = re_dict['regions']

        result = response2.text
        re_dict = json.loads(response2.text)
        data_en = re_dict['regions']

        if len(id_list(data_en)) == 3:
            oblist = threeSampling(data, id_list(data_en))
        elif len(id_list(data_en)) == 2:
            oblist = twoSampling(data, id_list(data_en))
        elif len(id_list(data_en)) == 1:
            oblist = oneSampling(data, id_list(data_en))
        else:
            oblist = []

        mylist = []
        for ob in oblist:
            if ob:
                mylist.append(ob)

    return "{}".format(mylist)

@app.route('/view/<filename>')
def file_view(filename):
    return send_from_directory(img_root, filename)

################################################################################

AZURE_API_KEY = '1791b966e9b3488f9e54d05e58e0f705'
ALLOWED_EXTENSIONS = set([ 'png', 'jpg', 'jpeg' ])

# 샘플링
def sample():
    headers = {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': AZURE_API_KEY,
    }
    params = urlencode({
        # Request parameters
        'detectOrientation ': 'ture',
    })
    params2 = urlencode({
        # Request parameters
        'language': 'en',
        'detectOrientation ': 'ture',
    })
    url = 'https://eastasia.api.cognitive.microsoft.com/vision/v1.0/ocr'

    mylist = {} # 결과를 따로 저장할 배열
    language = ''
    img_count = 0
    not_img = 0
    extraction_count = 0

    #  모든 파일검사
    for root, dirs, files in os.walk(img_root):
        files.sort()
        for file in files:
            print(file + "  ===== 데이터 추출중... =====\n")
            # 이미지 파일인지 검사
            if allowed_file(file) :
                img_count = img_count + 1
                with open(root+'/'+file, 'rb') as f:
                    data = f.read()

                while True:
                    try:
                        # 한글(자동인식)검사 ko ( id제외 나머지 추출용 )
                        response = requests.post(
                            url,
                            headers=headers,
                            params=params,
                            data=data
                        )
                        # 영문 검사 en ( id추출용 )
                        response2 = requests.post(
                            url,
                            headers=headers,
                            params=params2,
                            data=data
                        )
                        break
                    except Exception as e:
                        print (e)
                        time.sleep(30)

                if response.status_code == 429:
                    print ( response)
                    time.sleep(30)

                result = response.text # 이미지에서 추출한 텍스트를 json형식의 str타입으로 반환
                re_dict = json.loads(response.text) # str타입을 dict타입으로 변환
                # language = re_dict['language']
                data = re_dict['regions']

                result = response2.text
                re_dict = json.loads(response2.text)
                data_en = re_dict['regions']

                # 아이디 개수에 따라 다른 좌표값으로 추출
                if len(id_list(data_en)) == 3:
                    oblist = threeSampling(data, id_list(data_en))
                elif len(id_list(data_en)) == 2:
                    oblist = twoSampling(data, id_list(data_en))
                elif len(id_list(data_en)) == 1:
                    oblist = oneSampling(data, id_list(data_en))
                else:
                    oblist = []

                # 추출한 데이터 리스트에 추가 / 추가 오류검사
                for ob in oblist:
                    if ob:
                        ob['file'] = file
                        ob_id = ob.get('id')

                        if ob_id:
                            extraction_count = extraction_count + 1
                            if ob_id.find('fi') != -1:
                                if not crolling_one(ob_id):
                                    if crolling_one(ob_id.replace("fi","fj")):
                                        ob_id = ob_id.replace("fi","fj")
                                        ob['id'] = ob_id

                            if mylist.get(ob_id):
                                pass
                            else:
                                mylist[ob_id] = []
                            mylist[ob_id].append(ob)
            else:
                not_img = not_img+1
    return mylist, language,img_count,  not_img, extraction_count

# 아이디리스트 뽑아내기
def id_list(data_en):
    ob1 ={}
    ob2 ={}
    ob3 ={}
    id_list = []
    # 아이디의 유효성을 위해 걸러내는 특수문자들
    arr = ['/', ':', "'", ',', '-', '!', '\"', '•']

    # 아이디 language=en 으로 더 정확하게 잡아내기
    a=0
    for line2 in data_en:
        for li2 in line2['lines']:
            a=a+1
            b=0
            for wo in li2['words']:
                b=b+1
                # 인식율 오류처리
                if wo['text'].find('Ü') != -1 :
                    wo['text'] = wo['text'].replace("Ü","fj")
                if not (any(re.findall('|'.join(arr), wo['text']))) and (not wo['text'].isdigit()):
                    if not ob1.get('id') :
                        if (a==1 and b==2):
                            ob1['id'] = wo['text']
                            id_list.append(ob1)
                    elif not ob2.get('id') :
                        if (a==2 and b==2) or (a==3 and b==2) or (a==4 and b==2) or (a==6 and b==2) or (a==5 and b==2) or (a==7 and b==2):
                            ob2['id'] = wo['text']
                            id_list.append(ob2)
                    elif not ob3.get('id') :
                        if (a==3 and b==2) or (a==5 and b==2) or (a==6 and b==2) or (a==7 and b==2) or (a==8 and b==2) \
                        or (a==9 and b==2) or (a==4 and b==2) or (a==10 and b==2) or (a==12 and b==2):
                            ob3['id'] = wo['text']
                            id_list.append(ob3)

    return id_list

# 아이디 3개 샘플링
def threeSampling(data, id_list):
    ob = []
    for id in id_list:
        ob.append(id)

    x=0
    for line in data :
        for li in line['lines'] :
            x=x+1
            y=0
            for wo in li['words']:
                y=y+1
                # follwing
                if not ob[0].get('follwing'):
                    if (x==7 and y==3) or (x==8 and y==3):
                        if wo['text'].isdigit():
                            ob[0]['follwing'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('follwing'):
                    if (x==8 and y==3) or (x==10 and y==3) or (x==9 and y==3) or (x==11 and y==3):
                        if wo['text'].isdigit():
                            ob[1]['follwing'] = wo['text']
                        else:
                            pass
                elif not ob[2].get('follwing'):
                    if (x==13 and y==3) or (x==12 and y==3) or (x==9 and y==3) or (x==11 and y==3):
                        if wo['text'].isdigit():
                            ob[2]['follwing'] = wo['text']
                        else:
                            pass

                # unfollwing
                if not ob[0].get('unfollwing'):
                    if (x==7 and y==7) or (x==8 and y==7):
                        if wo['text'].isdigit():
                            ob[0]['unfollwing'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('unfollwing'):
                    if (x==10 and y==7) or (x==8 and y==7) or (x==9 and y==7) or (x==11 and y==7):
                        if wo['text'].isdigit():
                            ob[1]['unfollwing'] = wo['text']
                        else:
                            pass
                elif not ob[2].get('unfollwing'):
                    if (x==12 and y==7) or (x==13 and y==7) or (x==9 and y==7) or (x==11 and y==7):
                        if wo['text'].isdigit():
                            ob[2]['unfollwing'] = wo['text']
                        else:
                            pass

                # reply
                if not ob[0].get('reply'):
                    if x==7 and y==11 :
                        if wo['text'].isdigit():
                            ob[0]['reply'] = wo['text']
                    if x > 7 :
                        ob[0]['reply'] = "0"
                elif not ob[1].get('reply'):
                    if (x==8 and y==11) or (x==10 and y==11) or (x==9 and y==11) or (x==11 and y==11):
                        if wo['text'].isdigit():
                            ob[1]['reply'] = wo['text']
                        else:
                            pass
                elif not ob[2].get('reply'):
                    if (x==13 and y==11) or (x==12 and y==11) or (x==9 and y==11) or (x==11 and y==11):
                        if wo['text'].isdigit():
                            ob[2]['reply'] = wo['text']
                        else:
                            pass

                # like
                if not ob[0].get('like'):
                    if (x==8 and y==2) or (x==9 and y==2) or (x==10 and y==2) or (x==11 and y==2):
                        if wo['text'].isdigit():
                            ob[0]['like'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('like'):
                    if (x==11 and y==2) or (x==10 and y==2) or (x==12 and y==2) or (x==13 and y==2):
                        if wo['text'].isdigit():
                            ob[1]['like'] = wo['text']
                        else:
                            pass
                elif not ob[2].get('like'):
                    if (x==14 and y==2) or (x==12 and y==15) or (x==13 and y==15) or (x==12 and y==2) or (x==13 and y==2) or (x==15 and y==2):
                        if wo['text'].isdigit():
                            ob[2]['like'] = wo['text']
                        else:
                            pass

                # posting
                if not ob[0].get('posting'):
                    if (x==13 and y==1) or (x==14 and y==1) or (x==15 and y==1)\
                    or (x==8 and y==6) or (x==9 and y==6) or (x==10 and y==6):
                        if wo['text'].isdigit():
                            ob[0]['posting'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('posting'):
                    if (x==14 and y==1) or (x==15 and y==1) or (x==16 and y==1):
                        if wo['text'].isdigit():
                            ob[1]['posting'] = wo['text']
                        else:
                            pass
                elif not ob[2].get('posting'):
                    if (x==15 and y==1) or (x==16 and y==1) or (x==17 and y==1):
                        if wo['text'].isdigit():
                            ob[2]['posting'] = wo['text']
                        else:
                            pass
    return ob

# 아이디 2개 샘플링
def twoSampling(data, id_list):
    ob = []
    for id in id_list:
        ob.append(id)

    x=0
    for line in data :
        for li in line['lines'] :
            x=x+1
            y=0
            for wo in li['words']:
                y=y+1
                # follwing
                if not ob[0].get('follwing'):
                    if (x==5 and y==3):
                        if wo['text'].isdigit():
                            ob[0]['follwing'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('follwing'):
                    if (x==6 and y==3) or (x==8 and y==3):
                        if wo['text'].isdigit():
                            ob[1]['follwing'] = wo['text']
                        else:
                            pass

                # unfollwing
                if not ob[0].get('unfollwing'):
                    if (x==5 and y==7):
                        if wo['text'].isdigit():
                            ob[0]['unfollwing'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('unfollwing'):
                    if (x==6 and y==7) or (x==8 and y==7):
                        if wo['text'].isdigit():
                            ob[1]['unfollwing'] = wo['text']
                        else:
                            pass

                # reply
                if not ob[0].get('reply'):
                    if (x==5 and y==11) or (x==5 and y==10) :
                        if wo['text'].isdigit():
                            ob[0]['reply'] = wo['text']
                    if x > 7 :
                        ob[0]['reply'] = "0"
                elif not ob[1].get('reply'):
                    if (x==6 and y==11) or (x==6 and y==10) or (x==8 and y==11):
                        if wo['text'].isdigit():
                            ob[1]['reply'] = wo['text']
                        else:
                            pass

                # like
                if not ob[0].get('like'):
                    if (x==7 and y==2) or (x==6 and y==2):
                        if wo['text'].isdigit():
                            ob[0]['like'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('like'):
                    if (x==8 and y==2) or (x==9 and y==2):
                        if wo['text'].isdigit():
                            ob[1]['like'] = wo['text']
                        else:
                            pass

                # posting
                if not ob[0].get('posting'):
                    if (x==9 and y==1) or (x==10 and y==1) or (x==7 and y==6) or (x==6 and y==6):
                        if wo['text'].isdigit():
                            ob[0]['posting'] = wo['text']
                        else:
                            pass
                elif not ob[1].get('posting'):
                    if (x==10 and y==1) or (x==11 and y==1) or (x==9 and y==6):
                        if wo['text'].isdigit():
                            ob[1]['posting'] = wo['text']
                        else:
                            pass
    return ob

# 아이디 1개 샘플링
def oneSampling(data, id_list):
    ob = []
    for id in id_list:
        ob.append(id)

    x=0
    for line in data :
        for li in line['lines'] :
            x=x+1
            y=0
            for wo in li['words']:
                y=y+1
                # follwing
                if not ob[0].get('follwing'):
                    if (x==5 and y==3):
                        if wo['text'].isdigit():
                            ob[0]['follwing'] = wo['text']
                        else:
                            pass

                # unfollwing
                if not ob[0].get('unfollwing'):
                    if (x==5 and y==7):
                        if wo['text'].isdigit():
                            ob[0]['unfollwing'] = wo['text']
                        else:
                            pass

                # reply
                if not ob[0].get('reply'):
                    if (x==5 and y==11) or (x==5 and y==10) :
                        if wo['text'].isdigit():
                            ob[0]['reply'] = wo['text']
                    if x > 7 :
                        ob[0]['reply'] = "0"

                # like
                if not ob[0].get('like'):
                    if (x==7 and y==2) or (x==6 and y==2):
                        if wo['text'].isdigit():
                            ob[0]['like'] = wo['text']
                        else:
                            pass

                # posting
                if not ob[0].get('posting'):
                    if (x==9 and y==1) or (x==10 and y==1) or (x==7 and y==6) or (x==6 and y==6):
                        if wo['text'].isdigit():
                            ob[0]['posting'] = wo['text']
                        else:
                            pass
    return ob

# 현재 인스타상태 전체 크롤링
def crolling_all(result):
    now = {}
    for id in result:
        r=requests.get("https://www.instagram.com/{}/?hl=ko".format(id[0]))
        if r:
            now[id[0]] = []
            c=r.content
            html = BeautifulSoup(c, "html.parser")
            meta = html.find("meta",{"property":"og:description"})
            beta = meta.get('content')
            beta = beta.split()
            # [1] : 팔로워(명), [3] : 팔로잉(명), [5] : 게시물(개), [7] : 닉네임(님의)
            no_follwer = beta[1][:-2]
            no_follwing = beta[3][:-2]
            no_contents = beta[5][:-1]
            no_nick = beta[7][:-2]
            now[id[0]].append(no_follwer)
            now[id[0]].append(no_follwing)
            now[id[0]].append(no_contents)
            now[id[0]].append(no_nick)
    return now

# 현재 인스타상태 단일 크롤링
def crolling_one(id):
    now = []
    r=requests.get("https://www.instagram.com/{}/?hl=ko".format(id))
    if r:
        c=r.content
        html = BeautifulSoup(c, "html.parser")
        meta = html.find("meta",{"property":"og:description"})
        beta = meta.get('content')
        beta = beta.split()
        # [1] : 팔로워(명), [3] : 팔로잉(명), [5] : 게시물(개), [7] : 닉네임(님의)
        no_follwer = beta[1][:-2]
        no_follwing = beta[3][:-2]
        no_contents = beta[5][:-1]
        no_nick = beta[7][:-2]
        now.append(no_follwer)
        now.append(no_follwing)
        now.append(no_contents)
        now.append(no_nick)
    return now

# 이미지 파일형식인지 검사
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', debug = True, port="5000")
