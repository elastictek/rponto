import base64
from operator import eq
from pyexpat import features
import re
from typing import List
from wsgiref.util import FileWrapper
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.views import APIView
from django.http import Http404, request
from rest_framework.response import Response
from .decorators import jwt_required
from django.http.response import HttpResponse
from django.http import FileResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import status
import mimetypes
from datetime import datetime, timedelta
# import cups
import os, tempfile
import pickle

from pyodbc import Cursor, Error, connect, lowercase
from datetime import datetime
from django.http.response import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes, renderer_classes
from django.db import connections, transaction
from support.database import encloseColumn, Filters, DBSql, TypeDml, fetchall, Check
from support.myUtils import  ifNull

from rest_framework.renderers import JSONRenderer, MultiPartRenderer, BaseRenderer
from rest_framework.utils import encoders, json
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
import collections
import hmac
import hashlib
import math
from django.core.files.storage import FileSystemStorage
from sistema.settings.appSettings import AppSettings
import time
import requests
import psycopg2
from api.exports import export
import face_recognition

connGatewayName = "postgres"
connMssqlName = "sqlserver"
dbgw = DBSql(connections[connGatewayName].alias)
db = DBSql(connections["default"].alias)
dbmssql = DBSql(connections[connMssqlName].alias)

fotos_base_path = '../fotos'
records_base_path = '../records'
faces_base_path = 'faces'
tolerance = 0.4
jitters = 1
model = 'large'


def filterMulti(data, parameters, forceWhere=True, overrideWhere=False, encloseColumns=True, logicOperator="and"):
    p = {}
    txt = ''
    _forceWhere = forceWhere
    _overrideWhere = overrideWhere
    hasFilters = False
    for mainKey, mainValue in parameters.items():
        if (hasFilters):
            _forceWhere = False
            _overrideWhere = logicOperator
        if data.get(mainKey) is not None:
            sp = {}
            for key in mainValue.get('keys'):
                table = f'{mainValue.get("table")}.' if (mainValue.get("table") and encloseColumns) else mainValue.get("table", '')
                field = f'{table}"{key}"' if encloseColumns else f'{table}{key}'
                sp[key] = {"value": data.get(mainKey).lower(), "field": f'lower({field})'}
            f = Filters(data)
            f.setParameters(sp, True)
            f.where(_forceWhere, _overrideWhere)
            f.auto()
            f.value('or')
            p = {**p, **f.parameters}
            txt = f'{txt}{f.text}'
            if (not hasFilters):
                hasFilters = f.hasFilters
    return {"hasFilters": hasFilters, "text": txt, "parameters": p}

def rangeP(data, key, field, fieldDiff=None,pName=None):
    ret = {}
    if data is None:
        return ret
    if isinstance(key, list):
        hasNone = False
        for i, v in enumerate(data):
            if v is not None:
                ret[f'{pName}{key[i]}_{i}'] = {"key": key[i], "value": v, "field": field}
            else:
                hasNone = True
        if hasNone == False and len(data)==2 and fieldDiff is not None:
            ret[f'{pName}{key[0]}_{key[1]}'] = {"key": key, "value": ">=0", "field": fieldDiff}
    else:    
        for i, v in enumerate(data):
            if v is not None:
                ret[f'{pName}{key}_{i}'] = {"key": key, "value": v, "field": field}
    return ret

def rangeP2(data, key, field1, field2, fieldDiff=None):
    ret = {}
    field=False
    if data is None:
        return ret
    if isinstance(key, list):
        hasNone = False
        for i, v in enumerate(data):
            if v is not None:
                ret[f'{key[i]}_{i}'] = {"key": key[i], "value": v, "field": field1 if field is False else field2}
            else:
                hasNone = True
        if hasNone == False and len(data)==2 and fieldDiff is not None:
            ret[f'{key[0]}_{key[1]}'] = {"key": key, "value": ">=0", "field": fieldDiff}
    else:    
        for i, v in enumerate(data):
            if v is not None:
                ret[f'{key}_{i}'] = {"key": key, "value": v, "field": field1 if field is False else field2}
    return ret

@api_view(['POST'])
@renderer_classes([JSONRenderer])
def Sql(request, format=None):
    print("#############################################")
    if "parameters" in request.data and "method" in request.data["parameters"]:
        method=request.data["parameters"]["method"]
        func = globals()[method]
        response = func(request, format)
        return response
    return Response({})


@api_view(['POST'])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
@jwt_required
def SqlProtected(request):
    if "parameters" in request.data and "method" in request.data["parameters"]:
        method=request.data["parameters"]["method"]
        func = globals()[method]
        response = func(request, format)
        return response
    return Response({})


def Sync(request, format=None):
    faces = loadFaces(faces_base_path,True)
    return Response({"status":"success","nums":faces.get("nums")})


def EmployeesLookup(request, format=None):
    connection = connections[connMssqlName].cursor()
    f = Filters(request.data['filter'])
    f.setParameters({}, True)
    f.where()
    f.auto()
    f.value()

    fmulti = filterMulti(request.data['filter'], {
        'fmulti': {"keys": ['REFNUM_0', "FULLNAME"], "table": 'T.'}
    }, False, "and" if f.hasFilters else "where" ,False)
    parameters = {**f.parameters, **fmulti['parameters']}

    dql = dbmssql.dql(request.data, False)
    cols = f"""*"""
    dql.columns=encloseColumn(cols,False)
    dql.sort = " ORDER BY(SELECT NULL) " if not dql.sort else dql.sort #Obrigatório se PAGING em sqlserver
    sql = lambda p, c, s: (
        f"""  
            select * from (
            select DISTINCT e.REFNUM_0, NAM_0,SRN_0, CONCAT(SRN_0,' ',NAM_0) FULLNAME FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
            JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
            WHERE c.PROPRF_0 = 'STD' 
            ) T
            {f.text} {fmulti["text"]}
            {s(dql.sort)}
             {p(dql.paging)} {p(dql.limit)}
        """
    )
    if ("export" in request.data["parameters"]):
        dql.limit=f"""OFFSET 0 ROWS FETCH NEXT {request.data["parameters"]["limit"]} ROWS ONLY"""
        dql.paging=""
        return export(sql(lambda v:v,lambda v:v,lambda v:v), db_parameters=parameters, parameters=request.data["parameters"],conn_name=AppSettings.reportConn["sage"],dbi=dbmssql,conn=connection)
    try:
        response = dbmssql.executeList(sql, connection, parameters,[],None,f"""
            select * from (
            select DISTINCT e.REFNUM_0, NAM_0,SRN_0, CONCAT(SRN_0,' ',NAM_0) FULLNAME FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
            JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
            WHERE c.PROPRF_0 = 'STD' 
            ) T
            {f.text} {fmulti["text"]}
        """)
    except Exception as error:
        print(str(error))
        return Response({"status": "error", "title": str(error)})
    return Response(response)

def loadFaces(path,sync=False):

    if os.path.isfile(os.path.join("faces.dictionary")) and sync==False:
        with open('faces.dictionary', 'rb') as faces_file:
            return pickle.load(faces_file)
    else:
        faces ={"matrix": [], "nums": []}
        for filename in os.listdir(path):
            f = os.path.join(path, filename)
            if os.path.isfile(f):
                ki = face_recognition.load_image_file(f)
                faces.get("matrix").append(face_recognition.face_encodings(ki,None,jitters,model)[0])
                faces.get("nums").append({"num":filename.split('_')[0],"t_stamp":datetime.today()})
        with open('faces.dictionary', 'wb') as faces_file:
            pickle.dump(faces, faces_file)
        return faces

def getConfig():
    if os.path.isfile(os.path.join("config.json")):
        with open('config.json', 'rb') as config_file:
            return json.load(config_file)

def addFace(path,img):
    faces = {"matrix": [], "nums": []}
    if os.path.isfile(os.path.join("faces.dictionary")):
        with open('faces.dictionary', 'rb') as faces_file:
            faces = pickle.load(faces_file)
    f = os.path.join(path,img)
    if os.path.isfile(f):
        ki = face_recognition.load_image_file(f)
        faces.get("matrix").append(face_recognition.face_encodings(ki,None,jitters,model)[0])
        faces.get("nums").append({"num":img.split('_')[0],"t_stamp":datetime.today()})
        with open('faces.dictionary', 'wb') as faces_file:
            pickle.dump(faces, faces_file)
            return True
    return False

def DelFace(request, format=None):
    filter = request.data['filter']
    if filter.get("num"):
        if os.path.isfile(os.path.join("faces.dictionary")):
            with open('faces.dictionary', 'rb') as faces_file:
                faces = pickle.load(faces_file)
                idx = next((index for (index, d) in enumerate(faces.get("nums")) if d["num"] == filter.get("num")), None)
                if idx is not None:
                    faces.get("matrix").pop(idx)
                    faces.get("nums").pop(idx)
                    with open('faces.dictionary', 'wb') as faces_file:
                        pickle.dump(faces, faces_file)
                    return Response({"status":"success"})
    return Response({"status":"error"})

def filePathByNum(path,num):
    for i in os.listdir(path):
        if os.path.isfile(os.path.join(path,i)) and i.startswith(num):
            return os.path.join("media",i)
    return None

def SetUser(request, format=None):
    connection = connections[connMssqlName].cursor()    
    data = request.data['parameters']
    filter = request.data['filter']
    ts = datetime.now()
    try:
        if "save" in data and data["save"]==True:
            hsh = data.get("hsh") if data.get("hsh") is not None else None
            if hsh is None:

                try:
                    os.makedirs(f"""{records_base_path}/{ts.strftime("%Y%m%d")}""")
                except FileExistsError:
                    pass
                try:
                    os.makedirs(f"""{records_base_path}/{ts.strftime("%Y%m%d")}/{filter["num"]}""")
                except FileExistsError:
                    pass

                with open(f"""{records_base_path}/{ts.strftime("%Y%m%d")}/{filter["num"]}/{ts.strftime("%Y%m%d.%H%M%S")}.jpg""", "wb") as fh:
                    fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                                    
                f = Filters({"num": filter["num"],"dts": ts.strftime("%Y-%m-%d") })
                f.where()
                f.add(f'num = :num', True)
                f.add(f'dts = :dts', True)
                f.value("and")
                reg = dbmssql.executeSimpleList(lambda: (f'SELECT * from rponto.dbo.time_registration {f.text}'), connection, f.parameters)['rows']
                if len(reg)==0:
                    dti = {
                        "num":f.parameters["num"],
                        "nt": 1,
                        "hsh":hashlib.md5(f"""{f.parameters["num"]}-{ts.strftime("%Y-%m-%d")}""".encode('utf-8')).hexdigest(),
                        "dts":ts.strftime("%Y-%m-%d"),
                        "dt":datetime.strptime(data["timestamp"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d"),
                        f"ss_01":ts.strftime("%Y-%m-%d %H:%M:%S"),
                        f"ts_01":data["timestamp"],
                        f"ty_01":"in",
                    }
                    dml = dbmssql.dml(TypeDml.INSERT, dti, "rponto.dbo.time_registration",None,None,False)
                    dbmssql.execute(dml.statement, connection, dml.parameters)
                    return Response({"status":"success","hsh":dti.get("hsh")})
                else:               
                    nt = reg[0].get("nt")
                    if nt==8:
                        raise Exception("Atingiu o número máximo de registos! Por favor entre em contacto com os Recursos Humanos.")
                    dti = {
                        "nt": nt+1,
                        f"ss_{str(nt+1).zfill(2)}":ts.strftime("%Y-%m-%d %H:%M:%S"),
                        f"ts_{str(nt+1).zfill(2)}":data["timestamp"],
                        f"ty_{str(nt+1).zfill(2)}":"in" if reg[0].get(f"ty_{str(nt).zfill(2)}") == "out" else "out"
                    }
                    f = Filters({"num": filter["num"],"hsh": reg[0].get("hsh")})
                    f.where()
                    f.add(f'num = :num', True)
                    f.add(f'hsh = :hsh', True)
                    f.value("and")
                    dml = dbmssql.dml(TypeDml.UPDATE, dti, "rponto.dbo.time_registration",f.parameters,None,False)
                    dbmssql.execute(dml.statement, connection, dml.parameters)
                    return Response({"status":"success","hsh":reg[0].get("hsh")})
            else:
                f = Filters({"num": filter["num"],"hsh": hsh })
                f.where()
                f.add(f'num = :num', True)
                f.add(f'hsh = :hsh', True)
                f.value("and")
                reg = dbmssql.executeSimpleList(lambda: (f'SELECT * from rponto.dbo.time_registration {f.text}'), connection, f.parameters)['rows']
                if len(reg)>0:
                    nt = reg[0].get("nt")
                    dti = {f"ty_{str(nt).zfill(2)}":data.get("type")}
                    dml = dbmssql.dml(TypeDml.UPDATE, dti, "rponto.dbo.time_registration",f.parameters,None,False)
                    dbmssql.execute(dml.statement, connection, dml.parameters)
                    return Response({"status":"success"})
        else:
            existsInBd = True
            result = False
            filepath = filePathByNum(fotos_base_path,filter["num"])
            faces = loadFaces(faces_base_path)

            tmp = tempfile.NamedTemporaryFile(delete=False)
            try:
                tmp.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                unknown_image = face_recognition.load_image_file(tmp)
            finally:
                tmp.close()
                os.unlink(tmp.name)
            
            unknown_encoding = face_recognition.face_encodings(unknown_image,None,jitters,model)
            if len(unknown_encoding)==0:
                    return Response({"status": "error", "title": "Não foi reconhecida nenhuma face!"})
            unknown_encoding = unknown_encoding[0]

            valid_nums = []
            valid_filepaths = []
            valid_names = []
            
            try:
                idx = next((index for (index, d) in enumerate(faces.get("nums")) if d["num"] == filter["num"]), None)
                if idx is not None:
                    results = face_recognition.compare_faces([faces.get("matrix")[idx]], unknown_encoding,tolerance)
                    if len(results)>0:
                        result=results[0]
                else:
                    result=False
                    existsInBd=False
            except ValueError:
                existsInBd = False            
                
            if result==False:
                print("A face não corresponde....")
                results = face_recognition.compare_faces(faces.get("matrix"), unknown_encoding,tolerance)
                valid_indexes = [i for i, x in enumerate(results) if x]
                for x in valid_indexes:
                    valid_nums.append(faces.get("nums")[x].get("num"))
                    valid_filepaths.append(filePathByNum(fotos_base_path,faces.get("nums")[x].get("num")))
                if len(valid_nums):
                    sql = lambda: (
                        f"""
                            select DISTINCT e.REFNUM_0, NAM_0,SRN_0 FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
                            JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
                            WHERE c.PROPRF_0 = 'STD' AND e.REFNUM_0 IN ({','.join(f"'{w}'" for w in valid_nums)})
                        """
                    )
                    response = dbmssql.executeSimpleList(sql, connection, {})
                    if len(response["rows"])>0:
                        valid_names=response["rows"]
                if existsInBd==False:
                    added=False
                    if len(valid_indexes)==0:
                        with open(f"""{faces_base_path}/{filter["num"]}_.jpg""", "wb") as fh:
                            fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                        added = addFace(faces_base_path,f"""{filter["num"]}_.jpg""")
                    return Response({"status": "error", "title": f"""O colaborador indicado não existe no sistema! {"A recolha dos dados biométricos foi efetuada." if added else ""}"""})

            f = Filters(request.data['filter'])
            f.setParameters({
                "REFNUM_0": {"value": lambda v: f"=={v.get('num')}", "field": lambda k, v: f'e.{k}'}
            }, True)
            f.where(False,"and")
            f.auto()
            f.value("and")
            parameters = {**f.parameters}
            dql = dbmssql.dql(request.data, False,False,[])
            sql = lambda: (
                f"""
                    select DISTINCT e.REFNUM_0, NAM_0,SRN_0 FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
                    JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
                    WHERE c.PROPRF_0 = 'STD' {f.text}
                    {dql.limit}
                """
            )
            response = dbmssql.executeSimpleList(sql, connection, parameters)
            return Response({**response,"result":result,"foto":filepath,"valid_nums":valid_nums,"valid_filepaths":valid_filepaths,"valid_names":valid_names,"config":getConfig()})
    except Exception as error:
        print(error)
        return Response({"status": "error", "title": str(error)})

def AutoCapture(request, format=None):
    connection = connections[connMssqlName].cursor()    
    data = request.data['parameters']
    filter = request.data['filter']
    ts = datetime.now()
    try:
        if "save" in data and data["save"]==True:
            hsh = data.get("hsh") if data.get("hsh") is not None else None
            if hsh is None:

                try:
                    os.makedirs(f"""{records_base_path}/{ts.strftime("%Y%m%d")}""")
                except FileExistsError:
                    pass
                try:
                    os.makedirs(f"""{records_base_path}/{ts.strftime("%Y%m%d")}/{filter["num"]}""")
                except FileExistsError:
                    pass

                with open(f"""{records_base_path}/{ts.strftime("%Y%m%d")}/{filter["num"]}/{ts.strftime("%Y%m%d.%H%M%S")}.jpg""", "wb") as fh:
                    fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
            
                f = Filters({"num": filter["num"],"dts": ts.strftime("%Y-%m-%d") })
                f.where()
                f.add(f'num = :num', True)
                f.add(f'dts = :dts', True)
                f.value("and")
                reg = dbmssql.executeSimpleList(lambda: (f'SELECT * from rponto.dbo.time_registration {f.text}'), connection, f.parameters)['rows']
                if len(reg)==0:
                    dti = {
                        "num":f.parameters["num"],
                        "nt": 1,
                        "hsh":hashlib.md5(f"""{f.parameters["num"]}-{ts.strftime("%Y-%m-%d")}""".encode('utf-8')).hexdigest(),
                        "dts":ts.strftime("%Y-%m-%d"),
                        "dt":datetime.strptime(data["timestamp"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d"),
                        f"ss_01":ts.strftime("%Y-%m-%d %H:%M:%S"),
                        f"ts_01":data["timestamp"],
                        f"ty_01":"in",
                    }
                    dml = dbmssql.dml(TypeDml.INSERT, dti, "rponto.dbo.time_registration",None,None,False)
                    dbmssql.execute(dml.statement, connection, dml.parameters)
                    return Response({"status":"success","hsh":dti.get("hsh")})
                else:               
                    nt = reg[0].get("nt")
                    if nt==8:
                        raise Exception("Atingiu o número máximo de registos! Por favor entre em contacto com os Recursos Humanos.")
                    dti = {
                        "nt": nt+1,
                        f"ss_{str(nt+1).zfill(2)}":ts.strftime("%Y-%m-%d %H:%M:%S"),
                        f"ts_{str(nt+1).zfill(2)}":data["timestamp"],
                        f"ty_{str(nt+1).zfill(2)}":"in" if reg[0].get(f"ty_{str(nt).zfill(2)}") == "out" else "out"
                    }
                    f = Filters({"num": filter["num"],"hsh": reg[0].get("hsh")})
                    f.where()
                    f.add(f'num = :num', True)
                    f.add(f'hsh = :hsh', True)
                    f.value("and")
                    dml = dbmssql.dml(TypeDml.UPDATE, dti, "rponto.dbo.time_registration",f.parameters,None,False)
                    dbmssql.execute(dml.statement, connection, dml.parameters)
                    return Response({"status":"success","hsh":reg[0].get("hsh")})
            else:
                f = Filters({"num": filter["num"],"hsh": hsh })
                f.where()
                f.add(f'num = :num', True)
                f.add(f'hsh = :hsh', True)
                f.value("and")
                reg = dbmssql.executeSimpleList(lambda: (f'SELECT * from rponto.dbo.time_registration {f.text}'), connection, f.parameters)['rows']
                if len(reg)>0:
                    nt = reg[0].get("nt")
                    dti = {f"ty_{str(nt).zfill(2)}":data.get("type")}
                    dml = dbmssql.dml(TypeDml.UPDATE, dti, "rponto.dbo.time_registration",f.parameters,None,False)
                    dbmssql.execute(dml.statement, connection, dml.parameters)
                    return Response({"status":"success"})
        else:
            existsInBd = True
            result = False
            #filepath = filePathByNum(fotos_base_path,filter["num"])
            filepath = None
            print(f"1. {datetime.now()}")
            faces = loadFaces(faces_base_path)
            print(f"2. {datetime.now()}")
            tmp = tempfile.NamedTemporaryFile(delete=False)
            try:
                tmp.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                unknown_image = face_recognition.load_image_file(tmp)
            finally:
                tmp.close()
                os.unlink(tmp.name)
            print(f"3. {datetime.now()}")
            unknown_encoding = face_recognition.face_encodings(unknown_image,None,jitters,model)
            if len(unknown_encoding)==0:
                    return Response({"status": "error", "title": "Não foi reconhecida nenhuma face!"})
            unknown_encoding = unknown_encoding[0]

            valid_nums = []
            valid_filepaths = []
            valid_names = []
            
            print(f"4. {datetime.now()}")
            results = face_recognition.compare_faces(faces.get("matrix"), unknown_encoding,tolerance)
            valid_indexes = [i for i, x in enumerate(results) if x]
            for idx,x in enumerate(valid_indexes):
                if idx==0:
                    result=True
                    request.data['filter']["num"] = faces.get("nums")[x].get("num")
                    filepath=filePathByNum(fotos_base_path,faces.get("nums")[x].get("num"))
                else:
                    valid_nums.append(faces.get("nums")[x].get("num"))
                    valid_filepaths.append(filePathByNum(fotos_base_path,faces.get("nums")[x].get("num")))            
            print(f"5. {datetime.now()}")
            if len(valid_nums):
                sql = lambda: (
                    f"""
                        select DISTINCT e.REFNUM_0, NAM_0,SRN_0 FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
                        JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
                        WHERE c.PROPRF_0 = 'STD' AND e.REFNUM_0 IN ({','.join(f"'{w}'" for w in valid_nums)})
                    """
                )
                response = dbmssql.executeSimpleList(sql, connection, {})
                if len(response["rows"])>0:
                    valid_names=response["rows"]
            if existsInBd==False:
                added=False
                if len(valid_indexes)==0:
                    with open(f"""{faces_base_path}/{filter["num"]}_.jpg""", "wb") as fh:
                        fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                    added = addFace(faces_base_path,f"""{filter["num"]}_.jpg""")
                return Response({"status": "error", "title": f"""O colaborador indicado não existe no sistema! {"A recolha dos dados biométricos foi efetuada." if added else ""}"""})

            f = Filters(request.data['filter'])
            f.setParameters({
                "REFNUM_0": {"value": lambda v: f"=={v.get('num')}", "field": lambda k, v: f'e.{k}'}
            }, True)
            f.where(False,"and")
            f.auto()
            f.value("and")
            parameters = {**f.parameters}
            dql = dbmssql.dql(request.data, False,False,[])
            sql = lambda: (
                f"""
                    select DISTINCT e.REFNUM_0, NAM_0,SRN_0 FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
                    JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
                    WHERE c.PROPRF_0 = 'STD' {f.text}
                    {dql.limit}
                """
            )
            response = dbmssql.executeSimpleList(sql, connection, parameters)
            if result==False and request.data['filter'].get("num") is None:
                return Response({"status": "error", "title": "O sistema não o(a) identificou!"})
            return Response({**response,"result":result,"num":request.data['filter'].get("num"),"foto":filepath,"valid_nums":valid_nums,"valid_filepaths":valid_filepaths,"valid_names":valid_names,"config":getConfig()})
    except Exception as error:
        return Response({"status": "error", "title": str(error)})

def BiometriasList(request, format=None):
    bios = []
    if os.path.isfile(os.path.join("faces.dictionary")):
        with open('faces.dictionary', 'rb') as faces_file:
            bios = pickle.load(faces_file).get("nums")
    return Response({"rows":bios})

def UpdateRecords(request, format=None):
    values = request.data["parameters"].get("values")
    print(values)
    try:
        with transaction.atomic():
            with connections[connMssqlName].cursor() as cursor:                  
                dml = dbmssql.dml(TypeDml.UPDATE,{
                    "ss_01":values.get("ss_01"),
                    "ty_01":values.get("ty_01"),
                    "ss_02":values.get("ss_02"),
                    "ty_02":values.get("ty_02"),
                    "ss_03":values.get("ss_03"),
                    "ty_03":values.get("ty_03"),
                    "ss_04":values.get("ss_04"),
                    "ty_04":values.get("ty_04"),
                    "ss_05":values.get("ss_05"),
                    "ty_05":values.get("ty_05"),
                    "ss_06":values.get("ss_06"),
                    "ty_06":values.get("ty_06"),
                    "ss_07":values.get("ss_07"),
                    "ty_07":values.get("ty_07"),
                    "ss_08":values.get("ss_08"),
                    "ty_08":values.get("ty_08")
                    }, "rponto.dbo.time_registration",{"id":f'=={values.get("id")}'},None,False)
                dbmssql.execute(dml.statement, cursor, dml.parameters)
        return Response({"status": "success", "title":f"""Registo atualizado com sucesso!"""})
    except Error as error:
        return Response({"status": "error", "title": str(error)})

def RegistosRH(request, format=None):
    connection = connections[connMssqlName].cursor()
    print(request.data['filter'])
    f = Filters(request.data['filter'])
    f.setParameters({
        **rangeP(f.filterData.get('fdata'), 'dts', lambda k, v: f'CONVERT(DATE, dts)'),
    #    **rangeP(f.filterData.get('fdatain'), 'in_t', lambda k, v: f'DATE(in_t)'),
    #    **rangeP(f.filterData.get('fdataout'), 'out_t', lambda k, v: f'DATE(out_t)'),
    #    "diff": {"value": lambda v: '>0' if "fdataout" in v and v.get("fdataout") is not None else None, "field": lambda k, v: f'TIMESTAMPDIFF(second,in_t,out_t)'},
        "SRN_0": {"value": lambda v: v.get('fnome').lower() if v.get('fnome') is not None else None, "field": lambda k, v: f'lower(EID.{k})'},
        # "carga": {"value": lambda v: v.get('fcarganome').lower() if v.get('fcarganome') is not None else None, "field": lambda k, v: f'lower(sgppl.{k})'},
        "fnum": {"value": lambda v: v.get('fnum').lower() if v.get('fnum') is not None else None, "field": lambda k, v: f'lower(TR.num)'},
        "num": {"value": lambda v: f"=={v.get('num')}" if v.get('num') is not None else None, "field": lambda k, v: f'TR.{k}'},
        # "lar": {"value": lambda v: Filters.getNumeric(v.get('flargura')), "field": lambda k, v: f"j->>'{k}'"},
        # "area_real": {"value": lambda v: Filters.getNumeric(v.get('farea')), "field": lambda k, v: f'sgppl.{k}'},
        # "comp_real": {"value": lambda v: Filters.getNumeric(v.get('fcomp')), "field": lambda k, v: f'sgppl.{k}'},
        # "mes": {"value": lambda v: Filters.getNumeric(v.get('fmes')), "field": lambda k, v: f'mv.{k}'},
        # "disabled": {"value": lambda v: Filters.getNumeric(v.get('fdisabled')), "field": lambda k, v: f'sgppl.{k}'},
        # "ano": {"value": lambda v: Filters.getNumeric(v.get('fano')), "field": lambda k, v: f'mv.{k}'},
        # "diam_avg": {"value": lambda v: Filters.getNumeric(v.get('fdiam_avg')), "field": lambda k, v: f'sgppl.{k}'},
        # "diam_max": {"value": lambda v: Filters.getNumeric(v.get('fdiam_max')), "field": lambda k, v: f'sgppl.{k}'},
        # "diam_min": {"value": lambda v: Filters.getNumeric(v.get('fdiam_min')), "field": lambda k, v: f'sgppl.{k}'},
        # "destino": {"value": lambda v: v.get('fdestinoold').lower() if v.get('fdestinoold') is not None else None, "field": lambda k, v: f'lower(sgppl.{k})'},
        # "peso_bruto": {"value": lambda v: Filters.getNumeric(v.get('fpeso_bruto')), "field": lambda k, v: f'sgppl.{k}'},
        # "peso_liquido": {"value": lambda v: Filters.getNumeric(v.get('fpeso_liquido')), "field": lambda k, v: f'sgppl.{k}'},
        # "carga_id": {"value": lambda v: v.get('fcarga'), "field": lambda k, v: f'sgppl.{k}'},
        # "ISSDHNUM_0": {"value": lambda v: v.get('fdispatched'), "field": lambda k, v: f' mv."SDHNUM_0"'},
        # "SDHNUM_0": {"value": lambda v: v.get('fsdh').lower() if v.get('fsdh') is not None else None, "field": lambda k, v: f'lower(mv."SDHNUM_0")'},
        # "BPCNAM_0": {"value": lambda v: v.get('fclienteexp').lower() if v.get('fclienteexp') is not None else None, "field": lambda k, v: f'lower(mv."{k}")'},
        # "EECICT_0": {"value": lambda v: v.get('feec').lower() if v.get('feec') is not None else None, "field": lambda k, v: f'lower(mv."{k}")'},
       
        # "matricula": {"value": lambda v: v.get('fmatricula').lower() if v.get('fmatricula') is not None else None, "field": lambda k, v: f'lower(mol.{k})'},
        # "matricula_reboque": {"value": lambda v: v.get('fmatricula_reboque').lower() if v.get('fmatricula_reboque') is not None else None, "field": lambda k, v: f'lower(mol.{k})'},
        # "prf": {"value": lambda v: v.get('fprf').lower() if v.get('fprf') is not None else None, "field": lambda k, v: f'lower(mol.{k})'},
        # "iorder": {"value": lambda v: v.get('forder').lower() if v.get('forder') is not None else None, "field": lambda k, v: f'lower(mol.{k})'},


       #mv."BPCNAM_0",mv."ITMREF_0",mv."ITMDES1_0",mv."EECICT_0"

    #    "fof": {"value": lambda v: v.get('fof')},
    #    "vcr_num": {"value": lambda v: v.get('fvcr')},
    #    "qty_lote": {"value": lambda v: v.get('fqty'), "field": lambda k, v: f'{k}'},
    #    "qty_reminder": {"value": lambda v: v.get('fqty_reminder'), "field": lambda k, v: f'{k}'},
    #    "type_mov": {"value": lambda v: v.get('ftype_mov'), "field": lambda k, v: f'{k}'}
    }, True)
    f.where()
    f.auto()
    f.value()
    fmulti = filterMulti(request.data['filter'], {
        # 'flotenw': {"keys": ['lotenwinf', 'lotenwsup'], "table": 'mb.'},
        # 'ftiponw': {"keys": ['tiponwinf', 'tiponwsup'], "table": 'mb.'},
        # 'fbobine': {"keys": ['nome'], "table": 'mb.'},
    }, False, "and" if f.hasFilters else "where" ,False)
    fmulti["text"] = f""" """

    parameters = {**f.parameters, **fmulti['parameters']}
    dql = dbmssql.dql(request.data, False)
    cols = f"""TR.*,EID.SRN_0,EID.NAM_0"""
    dql.columns=encloseColumn(cols,False)
    sql = lambda p, c, s: (
        f"""  
            select {c(f'{dql.columns}')} 
            from rponto.dbo.time_registration TR
            JOIN x3peoplesql.[PEOPLELTEK].EMPLOID EID on EID.REFNUM_0 COLLATE Latin1_General_BIN = TR.num
            {f.text} {fmulti["text"]}
            {s(dql.sort)} {p(dql.paging)} {p(dql.limit)}
        """
    )
    if ("export" in request.data["parameters"]):
        dql.limit=f"""OFFSET 0 ROWS FETCH NEXT {request.data["parameters"]["limit"]} ROWS ONLY"""
        dql.paging=""
        return export(sql(lambda v:v,lambda v:v,lambda v:v), db_parameters=parameters, parameters=request.data["parameters"],conn_name=AppSettings.reportConn["sage"],dbi=dbmssql,conn=connection)
    try:
        response = dbmssql.executeList(sql, connection, parameters,[],None,None)
    except Exception as error:
        print(str(error))
        return Response({"status": "error", "title": str(error)})
    return Response(response)

def CalendarList(request, format=None):
    connection = connections[connMssqlName].cursor()
    f = Filters(request.data['filter'])
    f.setParameters({
        #**rangeP(f.filterData.get('fdata'), 'dts', lambda k, v: f'CONVERT(DATE, dts)'),
        "REFNUM_0": {"value": lambda v: f"==F{str(v.get('fnum')).zfill(5)}" if v.get('fnum') is not None else None, "field": lambda k, v: f'T.{k}'},
        "num": {"value": lambda v: f"=={v.get('num')}" if v.get('num') is not None else None, "field": lambda k, v: f'T.REFNUM_0'},
    }, True)
    f.where("")
    f.auto()
    f.value()

    _year = request.data['filter'].get("y") if request.data['filter'].get("y") is not None else datetime.now().year
    _month = request.data['filter'].get("m") if request.data['filter'].get("m") is not None else None
    f2 = Filters(request.data['filter'])
    f2.setParameters({
        #**rangeP(f.filterData.get('fdata'), 'dts', lambda k, v: f'CONVERT(DATE, dts)'),
        "FULLNAME": {"value": lambda v: v.get('fnome').lower() if v.get('fnome') is not None else None, "field": lambda k, v: f'lower({k})'},
        "y": {"value": lambda v: f"=={_year}", "field": lambda k, v: f'C.{k}'},
        "m": {"value": lambda v: f"=={_month}" if _month is not None else None, "field": lambda k, v: f'C.{k}'}
    }, True)
    f2.where()
    f2.auto()
    f2.value()


    def filterMonthMultiSelect(data,name,operator):
        f = Filters(data)
        fP = {}
        if name in data:
            dt = [o['value'] for o in data[name]]
            for idx,v in enumerate(dt):
                fP[f"m{idx}"] = {"key":"m", "value": f"=={v}", "field": lambda k, v: f'C.{k}'}
        f.setParameters({**fP}, True)
        f.auto()
        f.where(False, operator)
        f.value("or")
        return f
    fmonths = filterMonthMultiSelect(request.data['filter'],'months',"and" if f2.hasFilters else "where")
    
    fmulti = filterMulti(request.data['filter'], {
        # 'flotenw': {"keys": ['lotenwinf', 'lotenwsup'], "table": 'mb.'},
        # 'ftiponw': {"keys": ['tiponwinf', 'tiponwsup'], "table": 'mb.'},
        # 'fbobine': {"keys": ['nome'], "table": 'mb.'},
    }, False, "and" if f.hasFilters else "where" ,False)
    fmulti["text"] = f""" """

    parameters = {**f.parameters, **fmulti['parameters'],**f2.parameters,**fmonths.parameters}
    dql = dbmssql.dql(request.data, False)
    cols = f"""*"""
    dql.columns=encloseColumn(cols,False)
    dql.sort = " ORDER BY(SELECT NULL) " if not dql.sort else dql.sort #Obrigatório se PAGING em sqlserver
    sql = lambda p, c, s: (
        f"""            
            WITH [CTE_CALENDAR] AS
            (SELECT CAST('{_year}-01-01' AS DATE) AS [date]
            union all
            select DATEADD(dd,1,[date]) FROM [CTE_CALENDAR]
            WHERE DATEADD(dd,1,[date]) <= CAST('{_year}-12-31' AS DATE)
            ), [CALENDAR] AS 
            (SELECT 
            [date],
            DATEPART(ISO_WEEK,[date]) isowyear,
            DATEPART(WEEK,[date]) wyear,
            DATEPART(WEEKDAY,[date]) wday,
            FORMAT([date], 'dddd', 'pt-pt') wdayname,
            --DATENAME(WEEKDAY,[date]) wdayname,
            DATEPART(MONTH,[date]) m,
            DATEPART(YEAR,[date]) y,
            CASE WHEN DATEPART(ISO_WEEK,[date])>DATEPART(WEEK,[date]) THEN DATEPART(YEAR,[date])-1 ELSE DATEPART(YEAR,[date]) END isoy
            FROM [CTE_CALENDAR]
            )
            SELECT {c(f'{dql.columns}')} FROM (
            SELECT [YEA_0],[WEEK],[DAYWEEK],[REFNUM_0],[PLNTYP_0], EN_MANHA,SA_MANHA,EN_TARDE,SA_TARDE, SRN_0,NAM_0, CONCAT(SRN_0,' ',NAM_0) FULLNAME
            FROM (
            SELECT T.*,EID.SRN_0, EID.NAM_0 FROM (
            select DISTINCT 1 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_0
            UNION ALL
            select DISTINCT 2 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_1
            UNION ALL
            select DISTINCT 3 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_2
            UNION ALL
            select DISTINCT 4 WEEK,YEA_0, REFNUM_0, STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_3
            UNION ALL
            select DISTINCT 5 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_4
            UNION ALL
            select DISTINCT 6 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_5
            UNION ALL
            select DISTINCT 7 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_6
            UNION ALL
            select DISTINCT 8 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_7
            UNION ALL
            select DISTINCT 9 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_8
            UNION ALL
            select DISTINCT 10 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_9
            UNION ALL
            select DISTINCT 11 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_10
            UNION ALL
            select DISTINCT 12 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_11
            UNION ALL
            select DISTINCT 13 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_12
            UNION ALL
            select DISTINCT 14 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_13
            UNION ALL
            select DISTINCT 15 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_14
            UNION ALL
            select DISTINCT 16 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_15
            UNION ALL
            select DISTINCT 17 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_16
            UNION ALL
            select DISTINCT 18 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_17
            UNION ALL
            select DISTINCT 19 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_18
            UNION ALL
            select DISTINCT 20 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_19
            UNION ALL
            select DISTINCT 21 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_20
            UNION ALL
            select DISTINCT 22 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_21
            UNION ALL
            select DISTINCT 23 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_22
            UNION ALL
            select DISTINCT 24 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_23
            UNION ALL
            select DISTINCT 25 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_24
            UNION ALL
            select DISTINCT 26 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_25
            UNION ALL
            select DISTINCT 27 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_26
            UNION ALL
            select DISTINCT 28 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_27
            UNION ALL
            select DISTINCT 29 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_28
            UNION ALL
            select DISTINCT 30 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_29
            UNION ALL
            select DISTINCT 31 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_30
            UNION ALL
            select DISTINCT 32 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_31
            UNION ALL
            select DISTINCT 33 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_32
            UNION ALL
            select DISTINCT 34 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_33
            UNION ALL
            select DISTINCT 35 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_34
            UNION ALL
            select DISTINCT 36 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_35
            UNION ALL
            select DISTINCT 37 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_36
            UNION ALL
            select DISTINCT 38 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_37
            UNION ALL
            select DISTINCT 39 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_38
            UNION ALL
            select DISTINCT 40 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_39
            UNION ALL
            select DISTINCT 41 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_40
            UNION ALL
            select DISTINCT 42 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_41
            UNION ALL
            select DISTINCT 43 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_42
            UNION ALL
            select DISTINCT 44 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_43
            UNION ALL
            select DISTINCT 45 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_44
            UNION ALL
            select DISTINCT 46 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_45
            UNION ALL
            select DISTINCT 47 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_46
            UNION ALL
            select DISTINCT 48 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_47
            UNION ALL
            select DISTINCT 49 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_48
            UNION ALL
            select DISTINCT 50 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_49
            UNION ALL
            select DISTINCT 51 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_50
            UNION ALL
            select DISTINCT 52 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_51
            UNION ALL
            select DISTINCT 53 WEEK,YEA_0, REFNUM_0,STRTIM0_0, ENDTIM0_0,STRTIM1_0, ENDTIM1_0,STRTIM0_1, ENDTIM0_1,STRTIM1_1, ENDTIM1_1,STRTIM0_2, ENDTIM0_2,STRTIM1_2, ENDTIM1_2,STRTIM0_3, ENDTIM0_3,STRTIM1_3, ENDTIM1_3,
            STRTIM0_4, ENDTIM0_4,STRTIM1_4, ENDTIM1_4,STRTIM0_5, ENDTIM0_5,STRTIM1_5, ENDTIM1_5,STRTIM0_6, ENDTIM0_6,STRTIM1_6, ENDTIM1_6,PLNTYP_0
            from x3peoplesql.[PEOPLELTEK].[EMPLOCTR] CT
            JOIN x3peoplesql.[PEOPLELTEK].PLANTYP PT ON PT.COD_0 = CT.PLNTYP_0
            JOIN x3peoplesql.[PEOPLELTEK].TYPWEEK PW0 ON PW0.COD_0 = PT.WEKTYP_52
            ) T 
            JOIN x3peoplesql.[PEOPLELTEK].EMPLOID EID on EID.REFNUM_0 = T.REFNUM_0
            {f.text} {fmulti["text"]}
            --WHERE T.REFNUM_0='F00085' -- AND YEA_0=2020
            ) MyTable
            CROSS APPLY (
            SELECT DAY_ORDER,DAYWEEK,EN_MANHA,SA_MANHA,EN_TARDE,SA_TARDE
            FROM (VALUES
                (0,2,[STRTIM0_0],[ENDTIM0_0],[STRTIM1_0],[ENDTIM1_0]),
                (1,3,[STRTIM0_1],[ENDTIM0_1],[STRTIM1_1],[ENDTIM1_1]),
                (2,4,[STRTIM0_2],[ENDTIM0_2],[STRTIM1_2],[ENDTIM1_2]),
                (3,5,[STRTIM0_3],[ENDTIM0_3],[STRTIM1_3],[ENDTIM1_3]),
                (4,6,[STRTIM0_4],[ENDTIM0_4],[STRTIM1_4],[ENDTIM1_4]),
                (5,7,[STRTIM0_5],[ENDTIM0_5],[STRTIM1_5],[ENDTIM1_5]),
                (6,1,[STRTIM0_6],[ENDTIM0_6],[STRTIM1_6],[ENDTIM1_6])
            ) AS [SourceTable](DAY_ORDER,DAYWEEK,EN_MANHA,SA_MANHA,EN_TARDE,SA_TARDE)
            ) AS [UnpivotTable]
            ) H
            JOIN CALENDAR AS C ON C.wday=H.DAYWEEK and C.isoy=H.YEA_0 AND C.isowyear=H.WEEK
            {f2.text} {fmonths.text}
            {s(dql.sort)} {p(dql.paging)} {p(dql.limit)}
            OPTION(MAXRECURSION 400)
            
        """
    )
    if ("export" in request.data["parameters"]):
        dql.limit=f"""OFFSET 0 ROWS FETCH NEXT {request.data["parameters"]["limit"]} ROWS ONLY"""
        dql.paging=""
        return export(sql(lambda v:v,lambda v:v,lambda v:v), db_parameters=parameters, parameters={**request.data["parameters"],"filter":request.data.get('filter')},conn_name=AppSettings.reportConn["sage"],dbi=dbmssql,conn=connection)
    try:
        response = dbmssql.executeList(sql, connection, parameters,[],None,None)
    except Exception as error:
        print(str(error))
        return Response({"status": "error", "title": str(error)})
    return Response(response)    

def GetCameraRecords(request, format=None):
    records = []
    parameters = request.data['parameters']
    if parameters.get('date') and parameters.get('num'):
        path = os.path.join(parameters.get('date'),parameters.get('num'))
        for filename in os.listdir(os.path.join(records_base_path,path)):
            v = datetime.strptime(filename.replace(".jpg",""), '%Y%m%d.%H%M%S').strftime("%Y-%m-%d %H:%M:%S")
            records.append({"filename":os.path.join(path,filename).replace("\\","/"),"tstamp":v})
    return Response(records)