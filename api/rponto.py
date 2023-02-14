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

@api_view(['POST'])
@renderer_classes([JSONRenderer])
def Sql(request, format=None):
    if "parameters" in request.data and "method" in request.data["parameters"]:
        method=request.data["parameters"]["method"]
        func = globals()[method]
        response = func(request, format)
        return response
    return Response({})


@api_view(['POST'])
@renderer_classes([JSONRenderer])
@jwt_required
def SqlProtected(request):
    if "parameters" in request.data and "method" in request.data["parameters"]:
        method=request.data["parameters"]["method"]
        func = globals()[method]
        response = func(request, format)
        return response
    return Response({})



@api_view(['POST','GET'])
@renderer_classes([JSONRenderer])
def Sync(request, format=None):
    faces = loadFaces(faces_base_path,True)
    return Response({"status":"success","nums":faces.get("nums")})

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
                faces.get("nums").append(filename.split('_')[0])
        with open('faces.dictionary', 'wb') as faces_file:
            pickle.dump(faces, faces_file)
        return faces

def addFace(path,img):
    faces = {"matrix": [], "nums": []}
    if os.path.isfile(os.path.join("faces.dictionary")):
        with open('faces.dictionary', 'rb') as faces_file:
            faces = pickle.load(faces_file)
    f = os.path.join(path,img)
    if os.path.isfile(f):
        ki = face_recognition.load_image_file(f)
        faces.get("matrix").append(face_recognition.face_encodings(ki,None,jitters,model)[0])
        faces.get("nums").append(img.split('_')[0])
        with open('faces.dictionary', 'wb') as faces_file:
            pickle.dump(faces, faces_file)
            return True
    return False

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
                

                #################################################################################################################################

                # result = None
                # filepath = filePathByNum(fotos_base_path,filter["num"])
                # faces = loadFaces(faces_base_path)

                # unknown_image = face_recognition.load_image_file(f"""{records_base_path}/{ts.strftime("%Y%m%d")}/{filter["num"]}/{ts.strftime("%Y%m%d.%H%M%S")}.jpg""")
                # unknown_encoding = face_recognition.face_encodings(unknown_image,None,5,'large')
                # if len(unknown_encoding)==0:
                #         return Response({"status": "error", "title": "Não foi reconhecida nenhuma face!"})
                # unknown_encoding = unknown_encoding[0]

                # try:
                #     results = face_recognition.compare_faces([faces.get("matrix")[faces.get("nums").index(filter["num"])]], unknown_encoding,tolerance=0.33)
                #     if len(results)>0:
                #         result=results[0]
                # except ValueError:
                #     with open(f"""{faces_base_path}/{filter["num"]}_.jpg""", "wb") as fh:
                #         fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                #     return Response({"status": "error", "title": "O funcionário não existe na base de dados do sistema!"})
                
                    
                # valid_nums = []
                # valid_filepaths = []
                # valid_names = []
                # if result==False:
                #     print("A face não corresponde....")
                #     results = face_recognition.compare_faces(faces.get("matrix"), unknown_encoding,tolerance=0.33)
                #     valid_indexes = [i for i, x in enumerate(results) if x]
                #     for x in valid_indexes:
                #         valid_nums.append(faces.get("nums")[x])
                #         valid_filepaths.append(filePathByNum(fotos_base_path,faces.get("nums")[x]))
                #     if len(valid_nums):
                #         sql = lambda: (
                #             f"""
                #                 select DISTINCT e.REFNUM_0, NAM_0,SRN_0 FROM x3peoplesql.PEOPLELTEK.EMPLOID e 
                #                 JOIN x3peoplesql.PEOPLELTEK.EMPLOCTR c on c.REFNUM_0 = e.REFNUM_0 
                #                 WHERE c.PROPRF_0 = 'STD' AND e.REFNUM_0 IN ({','.join(f"'{w}'" for w in valid_nums)})
                #             """
                #         )
                #         response = dbmssql.executeSimpleList(sql, connection, {})
                #         if len(response["rows"])>0:
                #             valid_names=response["rows"]
                
                ####################################################################################################################
                    
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
                results = face_recognition.compare_faces([faces.get("matrix")[faces.get("nums").index(filter["num"])]], unknown_encoding,tolerance)
                if len(results)>0:
                    result=results[0]
            except ValueError:
                existsInBd = False            
                
            if result==False:
                print("A face não corresponde....")
                results = face_recognition.compare_faces(faces.get("matrix"), unknown_encoding,tolerance)
                valid_indexes = [i for i, x in enumerate(results) if x]
                print("%%%%%%%%%%%")
                print(valid_indexes)
                for x in valid_indexes:
                    valid_nums.append(faces.get("nums")[x])
                    valid_filepaths.append(filePathByNum(fotos_base_path,faces.get("nums")[x]))
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
                    return Response({"status": "error", "title": f"""O funcionário não existe na base de dados do sistema! {"Recolha de dados biométricos efetuada." if added else ""}"""})

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
            return Response({**response,"result":result,"foto":filepath,"valid_nums":valid_nums,"valid_filepaths":valid_filepaths,"valid_names":valid_names})
    except Exception as error:
        print(error)
        return Response({"status": "error", "title": str(error)})