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
from django.http.response import HttpResponse
from django.http import FileResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import status
import mimetypes
from datetime import datetime, timedelta
# import cups
import os, tempfile

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


@api_view(['POST'])
@renderer_classes([JSONRenderer])
def Sql(request, format=None):
    if "parameters" in request.data and "method" in request.data["parameters"]:
        method=request.data["parameters"]["method"]
        func = globals()[method]
        response = func(request, format)
        return response
    return Response({})

def SetUser(request, format=None):
    connection = connections[connMssqlName].cursor()    
    data = request.data['parameters']
    filter = request.data['filter']

    try:
        if "save" in data and data["save"]==True:
            hsh = data.get("hsh") if data.get("hsh") is not None else None
            if hsh is None:
                ts = datetime.now()

                try:
                    os.makedirs(f"""docs/{ts.strftime("%Y%m%d")}""")
                except FileExistsError:
                    pass
                try:
                    os.makedirs(f"""docs/{ts.strftime("%Y%m%d")}/{filter["num"]}""")
                except FileExistsError:
                    pass

                with open(f"""docs/{ts.strftime("%Y%m%d")}/{filter["num"]}/{ts.strftime("%Y%m%d.%H%M%S")}.jpg""", "wb") as fh:
                    fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))
                
                files = []
                for i in os.listdir("../fotos"):
                    if os.path.isfile(os.path.join("../fotos",i)) and filter["num"] in i:
                        files.append(i)
                        break
                if len(files)>0:
                    known_image = face_recognition.load_image_file(os.path.join("../fotos",files[0]))
                    unknown_image = face_recognition.load_image_file(f"""docs/{ts.strftime("%Y%m%d")}/{filter["num"]}/{ts.strftime("%Y%m%d.%H%M%S")}.jpg""")

                    known_encoding = face_recognition.face_encodings(known_image)[0]
                    unknown_encoding = face_recognition.face_encodings(unknown_image)[0]
                    print("FACE RECON")    
                    print(os.path.join("../fotos",files[0]))
                    print(f"""docs/{ts.strftime("%Y%m%d")}/{filter["num"]}/{ts.strftime("%Y%m%d.%H%M%S")}.jpg""")
                    results = face_recognition.compare_faces([known_encoding], unknown_encoding)
                    print(results)

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
                    f = Filters({"num": filter["num"],"hsh": reg[0].get("hsh") })
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
            return Response(response)
    except Exception as error:
        return Response({"status": "error", "title": str(error)})