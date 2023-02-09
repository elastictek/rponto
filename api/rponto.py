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

connGatewayName = "postgres"
connMssqlName = "sqlserver"
dbgw = DBSql(connections[connGatewayName].alias)
db = DBSql(connections["default"].alias)
dbmssql = DBSql(connections[connMssqlName].alias)


@api_view(['POST'])
@renderer_classes([JSONRenderer])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
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

    if len(response["rows"])>0:
        ts = datetime.now().strftime("%Y%m%d.%H%M%S")
        with open(f"sn.{ts}.jpg", "wb") as fh:
            fh.write(base64.b64decode(data["snapshot"].replace('data:image/jpeg;base64,','')))

    print(response)
    return Response(response)