import os
from sqlite3 import Cursor
import sys
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sistema.settings")
django.setup()

from socket import timeout
from django.contrib.auth.models import User, Group
from threading import Timer
from asgiref.sync import async_to_sync
from django.core.cache import cache
from channels.generic.websocket import WebsocketConsumer
import channels.layers
import json
import random
import hashlib
from django.db import connections
from support.database import encloseColumn, Filters, DBSql, TypeDml, fetchall, Check

connMssqlName = "sqlserver"
connGatewayName = "postgres"
dbmssql = DBSql(connections[connMssqlName].alias)
dbgw = DBSql(connections[connGatewayName].alias)
db = DBSql(connections["default"].alias)

def getCurrentSettingsId():
    with connections["default"].cursor() as cursor:
        return db.executeSimpleList(lambda: (f"""		
                SELECT acs.id,acs.agg_of_id 
                from producao_currentsettings cs
                join audit_currentsettings acs on cs.id=acs.contextid
                where cs.status=3
                order by acs.id desc
                limit 1
            """), cursor, {})['rows']

def executeAlerts():
    group_name = 'broadcast'
    channel_layer = channels.layers.get_channel_layer()

    rows = getCurrentSettingsId()
    dataInProd = rows[0] if len(rows)>0 else {}

    with connections["default"].cursor() as cursor:
        rows = db.executeSimpleList(lambda: (f'SELECT MAX(id) mx FROM ig_bobinagens'), cursor, {})['rows']
    dataig_bobinagens = json.dumps(rows[0],default=str)

    with connections["default"].cursor() as cursor:
        rows = db.executeSimpleList(lambda: (f'SELECT MAX(id) mx FROM ig_bobinagens'), cursor, {})['rows']
    dataig_bobinagens = json.dumps(rows[0],default=str)

    with connections["default"].cursor() as cursor:
        rows = db.executeSimpleList(lambda: (f'SELECT MAX(id) mx, count(*) cnt FROM producao_bobinagem pbm where valid = 0'), cursor, {})['rows']
    data = json.dumps(rows[0],default=str)

    if dataInProd:
        with connections["default"].cursor() as cursor:
            rows = db.executeSimpleList(lambda: (f"""
            SELECT avg(line_speed) over () avg_line_speed, 
            STDDEV(line_speed) over () stdev_line_speed,
            MIN(line_speed) over () min_line_speed,
            MAX(line_speed) over () max_line_speed,
            ig.* 
            FROM ig_linelog_params ig where agg_of_id={dataInProd["agg_of_id"]} ORDER BY ID DESC limit 1"""
            ), cursor, {})['rows']
        datalinelog_params = json.dumps(rows[0] if len(rows)>0 else {},default=str)
    else:
        datalinelog_params=json.dumps({})
    #with connections["default"].cursor() as cursor:
    #    rows = db.executeSimpleList(lambda: (f'SELECT MAX(ig_doseadores_ndx) mx FROM ig_doseadores'), cursor, {})['rows']
    #dataDosersSets = json.dumps(rows[0],default=str)

    with connections["default"].cursor() as cursor:
        rows = db.executeSimpleList(lambda: (f"""		
                SELECT acs.id 
                from audit_currentsettings acs
                order by acs.id desc
                limit 1
         """), cursor, {})['rows']
    dataAuditCs = json.dumps(rows[0] if len(rows)>0 else {},default=str)

    if dataInProd:
        with connections["default"].cursor() as cursor:
            rows = db.executeSimpleList(lambda: (f"""
                    with paletes as(
                    SELECT
                    sum(num_bobines_act) npaletes
                    FROM planeamento_ordemproducao op
                    join producao_palete pl on pl.ordem_id=op.id and pl.num_bobines_act=pl.num_bobines
                    where op.agg_of_id_id = {dataInProd["agg_of_id"]}
                    ),
                    bobines as(
                    select 
                    count(*) nbobines
                    from producao_bobine pb
                    where pb.agg_of_id = {dataInProd["agg_of_id"]}
                    )
                    select * 
                    from paletes
                    cross join bobines
            """), cursor, {})['rows']
        dataEstadoProducao = json.dumps(rows[0] if len(rows)>0 else {},default=str)
    else:
        dataEstadoProducao = json.dumps({},default=str)
    dataInProd = json.dumps(dataInProd,default=str)

    #with connections["default"].cursor() as cursor:
    #    rows = db.executeSimpleList(lambda: (f"""		
    #            select max(t_stamp) from lotesdosers limit 1
    #     """), cursor, {})['rows']
    #dataDosers = json.dumps(rows[0],default=str)

    #with connections[connGatewayName].cursor() as cursor:
    #    rows = dbgw.executeSimpleList(lambda:(f"""SELECT ST."UPDDATTIM_0" FROM "SAGE-PROD"."STOCK" ST Where ST."STOFCY_0" = 'E01' and ("LOC_0"='BUFFER' OR "ITMREF_0" LIKE 'R000%%') ORDER BY ST."UPDDATTIM_0" DESC LIMIT 1"""),cursor,{})['rows']
    #dataBuffer = json.dumps(rows[0],default=str)

    #with connections["default"].cursor() as cursor:
    #    rows = db.executeSimpleList(lambda: (f"""		
    #        select SUM(t.qty_lote_available) available FROM (
    #        SELECT qty_lote + SUM(DOSERS.qty_consumed) over (PARTITION BY LOTES.artigo_cod,LOTES.n_lote) qty_lote_available
    #        FROM (
    #        select * from(
    #            select
    #            l.*,
    #            l.t_stamp lt_stamp ,MAX(l.t_stamp) over (PARTITION BY l.artigo_cod,l.n_lote) max_t_stamp
    #            FROM loteslinha l
    #        ) t WHERE max_t_stamp=lt_stamp and `status`=1 and `group` is not null
    #        ) LOTES
    #        LEFT JOIN lotesdosers DOSERS ON LOTES.id=DOSERS.loteslinha_id  #and LOTES.`group`=DOSERS.group_id 
    #        WHERE DOSERS.status=1
    #        ) t
    #     """), cursor, {})['rows']
    #dataLotesAvailability = json.dumps(rows[0],default=str)

    async_to_sync(channel_layer.group_send)(group_name,{
        'type': "getAlerts", "data":{
            "igbobinagens":dataig_bobinagens,
            "bobinagens":data,
            "auditcs":dataAuditCs,
            #"buffer":dataBuffer,
            "inproduction":dataInProd,
            "datalinelog_params":datalinelog_params,
            #"dosers":dataDosers,
            #"availability":dataLotesAvailability, 
            #"doserssets":dataDosersSets
            }, 
            "hash":{
                "hash_igbobinagens":hashlib.md5(dataig_bobinagens.encode()).hexdigest(),
                "hash_bobinagens":hashlib.md5(data.encode()).hexdigest(),
                "hash_auditcs":hashlib.md5(dataAuditCs.encode()).hexdigest(),
                #"hash_buffer":hashlib.md5(dataBuffer.encode()).hexdigest(),
                "hash_inproduction":hashlib.md5(dataInProd.encode()).hexdigest(),
                "hash_estadoproducao":hashlib.md5(dataEstadoProducao.encode()).hexdigest(),
                "hash_linelog_params":hashlib.md5(datalinelog_params.encode()).hexdigest()
                
                #"hash_dosers":hashlib.md5(dataDosers.encode()).hexdigest(),
                #"hash_lotes_availability":hashlib.md5(dataLotesAvailability.encode()).hexdigest(),
                #"hash_doserssets":hashlib.md5(dataDosersSets.encode()).hexdigest()
            }
    })
    #self.send(text_data=json.dumps({"val":val},default=str))
    Timer(5,executeAlerts).start()
executeAlerts()

class RealTimeAlerts(WebsocketConsumer):

    room_group_name = 'broadcast'

    #def initAlerts(self,data):
    #    pass
        #self.executeAlerts()
    
   # def executeAlerts(self):
   #     self.getNewBobinagens({})
        #Timer(5,self.executeAlerts).start()

    def getAlerts(self, data):
        #val = random.randint(100000, 999999)
        #print(f"{val} - {self.channel_name}")
        
        #lotePicked = data['value']
        #cs = data['cs']
        #lotes = cache.get(f'lotes-{cs}')
        #code = [d for d in lotes if d['LOT_0'] == lotePicked]
        self.send(text_data=json.dumps(data,default=str))

    commands = {
        #'getBobinagens':getNewBobinagens,
        #'initAlerts':initAlerts
    }

    def connect(self):
        print("USER")
        #user = User.objects.get(username=self.scope['user']) # get Some User.
        
        async_to_sync(self.channel_layer.group_add)(self.room_group_name,self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name,self.channel_name)

    def receive(self, text_data):
        dt = json.loads(text_data)
        self.commands[dt['cmd']](self, dt)

class RealTimeOfs(WebsocketConsumer):

    def loadPaletes(self, data):
        fof = data['value']['of_id'] if "of_id" in data['value'] else data['value']['ofs_id'] if "ofs_id" in data['value'] else None
        print("GETTING PALETES")
        print(fof)
        if fof:
            connection = connections["default"].cursor()
            rows = dbgw.executeSimpleList(lambda:(f"""
                    SELECT
                    op.op,op.id,
                    op.num_paletes_total,
                    op.num_paletes_stock_in,
                    op.num_paletes_produzidas,
                    count(*) cnt
                    FROM sistema.planeamento_ordemproducao op
                    left join sistema.producao_palete pl on pl.ordem_id=op.id and pl.num_bobines_act=pl.num_bobines
                    where pl.num_bobines=pl.num_bobines_act and op.id in ({fof})
                    group by op.id
            """),connection,{})['rows']
        else:
            rows=[]
        hsh = json.dumps(rows,default=str)
        self.send(text_data=json.dumps({"rows":rows,"item":"paletes","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))
    
    commands = {
        'loadpaletes':loadPaletes
    }

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        dt = json.loads(text_data)
        self.commands[dt['cmd']](self, dt)

class RealTimeGeneric(WebsocketConsumer):

    def checkStockAvailable(self, data):
        connection = connections["default"].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT id
            FROM produto_stock_disponivel
            order by t_stamp_edit desc
        """),connection,{})['rows']
        hsh = json.dumps(rows,default=str)
        self.send(text_data=json.dumps({"rows":rows,"item":"stockavailable","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))

    def checkReciclado(self, data):
        print("GETTING RECICLADO")
        connection = connections["default"].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT id
            FROM producao_reciclado
            order by timestamp desc
        """),connection,{})['rows']
        hsh = json.dumps(rows,default=str)
        self.send(text_data=json.dumps({"rows":rows,"item":"reciclado","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))
    
    def checkGranulado(self, data):
        connection = connections["default"].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT id
            FROM lotesdoserslinha
            order by t_stamp desc
        """),connection,{})['rows']
        hsh = json.dumps(rows,default=str)
        self.send(text_data=json.dumps({"rows":rows,"item":"granulado","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))

    def checkNW(self, data):
        connection = connections["default"].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT id
            FROM lotesnwlinha
            order by t_stamp desc
        """),connection,{})['rows']
        hsh = json.dumps(rows,default=str)
        self.send(text_data=json.dumps({"rows":rows,"item":"nw","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))
    
    def checkCores(self, data):
        connection = connections["default"].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT id
            FROM lotescorelinha
            order by t_stamp desc
        """),connection,{})['rows']
        hsh = json.dumps(rows,default=str)
        self.send(text_data=json.dumps({"rows":rows,"item":"cores","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))
    
    def checkLineEvents(self, data):
        with connections["default"].cursor() as cursor:
            rows = db.executeSimpleList(lambda: (f'SELECT MAX(id) mx FROM ig_bobinagens'), cursor, {})['rows']
            hsh = json.dumps(rows,default=str)
            self.send(text_data=json.dumps({"rows":rows,"item":"checklineevents","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))

    def checkBufferIn(self,data):
        print("IM CHECKING")
        with connections[connMssqlName].cursor() as cursor:
            rows = dbmssql.executeSimpleList(lambda:(f"""
            
                SELECT TOP 1 ST."CREDATTIM_0",ST."VCRNUM_0", ST."ITMREF_0",ST."LOT_0",ST."QTYPCU_0",ST."PCU_0", IM."ITMDES1_0", ST."LOC_0"
                FROM ELASTICTEK."STOJOU" ST 
                JOIN ELASTICTEK."ITMMASTER" IM on IM."ITMREF_0" = ST."ITMREF_0"
                WHERE ST."LOC_0"='BUFFER' AND ST."QTYPCU_0">0 AND ST.VCRTYP_0 NOT IN (28) AND ST."CREUSR_0"='PDA1' ORDER BY ST."ROWID" DESC
            
            """),cursor,{})['rows']
            hsh = json.dumps(rows,default=str)
            self.send(text_data=json.dumps({"rows":rows,"item":"checkbufferin","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))

    def checkBobinagens(self,data):
        with connections["default"].cursor() as cursor:
            rows = db.executeSimpleList(lambda: (f'SELECT MAX(id) mx, count(*) cnt FROM producao_bobinagem pbm where valid = 0'), cursor, {})['rows']
            hsh = json.dumps(rows,default=str)
            self.send(text_data=json.dumps({"rows":rows,"item":"checkbobinagens","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))

    def checkCurrentSettings(self,data):
        value = data["value"] if "value" in data else {"status":3}
        f = Filters(value)
        f.where()
        f.add(f'cs.agg_of_id = :agg_of_id', lambda v: v is not None)
        f.add(f'cs.id = :cs_id', lambda v: v is not None)
        f.add(f'cs.status = :status', lambda v: v is not None)
        f.value("and")
        with connections["default"].cursor() as cursor:
            rows = db.executeSimpleList(lambda: (f'SELECT max(acs.id) mx from producao_currentsettings cs join audit_currentsettings acs on cs.id=acs.contextid {f.text}'), cursor, f.parameters)['rows']
            hsh = json.dumps(rows,default=str)
            self.send(text_data=json.dumps({"rows":rows,"item":"checkcurrentsettings","hash":hashlib.md5(hsh.encode()).hexdigest()},default=str))

    commands = {
        'checkreciclado':checkReciclado,
        'checkgranulado':checkGranulado,
        'checkstockavailable':checkStockAvailable,
        'checknw':checkNW,
        'checkcores':checkCores,
        'checklineevents':checkLineEvents,
        'checkbobinagens':checkBobinagens,
        'checkbufferin':checkBufferIn,
        'checkcurrentsettings':checkCurrentSettings
    }

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        dt = json.loads(text_data)
        self.commands[dt['cmd']](self, dt)

class LotesPickConsumer(WebsocketConsumer):

    def getLoteQuantity(self, data):
        usr = User.objects.get(username=self.scope['user'])
        au = authUser(usr)

        lote = data['lote']
        type= data["type"]
        unit= data["unit"]
        if type=='elasticband':
            connection = connections["default"].cursor()
            rows = dbgw.executeSimpleList(lambda:(f"""
            select round(pb.comp_actual*pl.largura/1000,2) qtd,estado from producao_bobine pb 
            join producao_largura pl on pl.id=pb.largura_id
            where nome = '{lote}' and estado in ('R','DM')"""),connection,{})['rows']
            if len(rows)>0:
                if rows[0]["qtd"] == 0:
                    self.send(text_data=json.dumps({"error":"A quantidade tem de ser maior que zero!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))
                elif rows[0]["estado"] == "DM" and (("producao" not in au["items"] or au["items"]["producao"]<200) and au["isAdmin"]==False):
                    self.send(text_data=json.dumps({"error":"Não tem permissões para adicionar bobines em estado DM!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))
                else:
                    self.send(text_data=json.dumps({"error":None,"row":{"qtd":rows[0]["qtd"],"source":type, "unit":unit, "lote":lote}},default=str))
            else:
                self.send(text_data=json.dumps({"error":"O lote não existe, ou não está definido como R ou DM!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))
        elif type=='bobinagem':
            connection = connections["default"].cursor()
            rows = dbgw.executeSimpleList(lambda:(f"""
            
                select estado,cnttotal - count(*) over () cnt from (
                SELECT 
                count(*) over () cnttotal, pb.estado
                FROM producao_bobinagem pbm
                join producao_bobine pb on pb.bobinagem_id=pbm.id
                where pbm.nome = '{lote}'
                ) t 
                where t.estado in ('R','BA')
            
            """),connection,{})['rows']
            if len(rows)>0:
                if rows[0]["cnt"] > 0 :
                    self.send(text_data=json.dumps({"error":"O estado da bobinagem tem de ser R ou BA!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))
                else:
                    self.send(text_data=json.dumps({"error":None,"row":{"qtd":0,"source":f'{type}_{rows[0]["estado"].lower()}', "unit":"kg", "lote":lote}},default=str))
            else:
                self.send(text_data=json.dumps({"error":"O lote não existe!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))
        else:
            connection = connections["default"].cursor()
            rows = dbgw.executeSimpleList(lambda:(f"""SELECT SUM(CASE WHEN lotenwsup='{lote}' THEN nwsup ELSE nwinf END) comp FROM sistema.producao_bobinagem where lotenwsup='{lote}' or lotenwinf='{lote}'"""),connection,{})['rows']
            if len(rows)>0:
                comp = rows[0]["comp"]
                conngw = connections[connGatewayName].cursor()
                rows = dbgw.executeSimpleList(lambda:(f""" 
                    select round((ABS(sto."QTYPCU_0")/itm."TSICOD_3"::decimal)*1000,2) comp,itm."ITMREF_0" itm,itm."ITMDES1_0" itm_des
			        from "SAGE-PROD"."STOJOU" sto
			        join "SAGE-PROD"."ITMMASTER" itm on itm."ITMREF_0"=sto."ITMREF_0"
			        where sto."LOT_0"='{lote}' order by "IPTDAT_0" DESC LIMIT 1
                """),conngw,{})['rows']
                if len(rows)>0:
                    qtd = rows[0]["comp"] - comp
                    self.send(text_data=json.dumps({"error":None,"row":{"qtd":qtd,"source":type, "unit":unit, "lote":lote, "itm":rows[0]["itm"],"itm_des":rows[0]["itm_des"] }},default=str))
                else:
                    self.send(text_data=json.dumps({"error":"O lote de Nonwoven não existe!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))
            else:
                self.send(text_data=json.dumps({"error":"O lote de Nonwoven não existe ou nunca foi utilizado!","row":{"qtd":0,"source":type, "unit":unit, "lote":lote}},default=str))

    def getNWLoteQuantity(self,data):
        lote = data['lote']
        conngw = connections[connGatewayName].cursor()
        sageAlias = dbgw.dbAlias.get("sage")
        rows = dbgw.executeSimpleList(lambda:(f"""
            SELECT * FROM(
                SELECT
                ST."ROWID" lote_id,ST."CREDATTIM_0",ST."ITMREF_0" artigo_cod,ST."LOT_0" n_lote,ST."LOC_0",ST."VCRNUM_0" vcr_num,
                SUM (ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0") QTY_SUM,
                ST."QTYPCU_0" qty_lote,
                mprima."TSICOD_3"::decimal largura,
                round((ABS(ST."QTYPCU_0")/mprima."TSICOD_3"::decimal)*1000,2) comp,
                ST."PCU_0" unit,mprima."ITMDES1_0" artigo_des
                FROM {sageAlias}."STOJOU" ST
                JOIN {sageAlias}."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
                where ST."LOT_0" = '{lote}' and mprima."ITMREF_0" like 'N%%' AND ST."LOC_0" in ('BUFFER') AND ST."CREDATTIM_0">= now() - INTERVAL '5 DAYS'
            ) t
            where (QTY_SUM > 0) 
        """),conngw,{})["rows"]

        

        if len(rows)>0:            
            conn = connections["default"].cursor()
            rowsx = db.executeSimpleList(lambda:(f"""select id from lotesnwlinha where n_lote = '{lote}' and artigo_cod='{rows[0]["artigo_cod"]}'"""),conn,{})['rows']
            if len(rowsx)>0:
                self.send(text_data=json.dumps({"error":"O lote de Nonwoven já foi registado!","row":{"qty_lote":rows[0]["qty_lote"],"unit":"m2", "n_lote":lote}},default=str))
            self.send(text_data=json.dumps({"error":None,"row":{**rows[0], "unit":"m2", "n_lote":lote }},default=str))
        else:
            self.send(text_data=json.dumps({"error":"O lote de Nonwoven não existe ou não se enconta em buffer!","row":{"qty_lote":0, "unit":"m2", "n_lote":lote}},default=str))


    def getGranuladoLoteQuantity(self,data):

            


            # SELECT * FROM(
            #     SELECT
            #         ST."ROWID" lote_id,ST."VCRNUM_0",ST."LOC_0", mprima."ITMDES1_0" artigo_des,
            #         SUM(ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0") "QTYPCU_0"
            #     FROM {sageAlias}."STOCK" STK
            #     JOIN {sageAlias}."STOJOU" ST ON ST."ITMREF_0"=STK."ITMREF_0" AND ST."LOT_0"=STK."LOT_0" AND ST."LOC_0"=STK."LOC_0"
            #     JOIN {sageAlias}."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
            #     WHERE ST."VCRNUM_0"='{values[4]}'
            # ) t
            # where ("QTYPCU_0" > 0)
            # AND NOT EXISTS (SELECT 1 FROM {sgpAlias}.lotesgranuladolinha ll where ll.vcr_num = "VCRNUM_0") 
            


            # SELECT
            # ST."ROWID" lote_id,ST."VCRNUM_0",ST."LOC_0",ST."QTYPCU_0", mprima."ITMDES1_0" artigo_des
            # FROM {sageAlias}."STOJOU" ST
            # JOIN {sageAlias}."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
            # WHERE ST."VCRNUM_0"='{values[4]}' AND ST."QTYPCU_0">0
            # AND NOT EXISTS (SELECT 1 FROM {sgpAlias}.lotesgranuladolinha ll where ll.vcr_num = ST."VCRNUM_0") 



            # SELECT * FROM(
            #     SELECT
            #     ST."ROWID" lote_id,ST."CREDATTIM_0",ST."ITMREF_0" artigo_cod,ST."LOT_0" n_lote,ST."LOC_0",ST."VCRNUM_0" vcr_num,
            #     SUM (ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0") QTY_SUM,
            #     ST."QTYPCU_0" qty_lote,
            #     round(ST."QTYPCU_0",2) peso,
            #     ST."PCU_0" unit,mprima."ITMDES1_0" artigo_des
            #     FROM {sageAlias}."STOJOU" ST
            #     JOIN {sageAlias}."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
            #     where ST."LOT_0" = '{lote}' and (LOWER(mprima."ITMDES1_0") NOT LIKE 'nonwo%%' AND LOWER(mprima."ITMDES1_0") NOT LIKE 'core%%') AND (mprima."ACCCOD_0" = 'PT_MATPRIM') AND ST."LOC_0" in ('BUFFER') AND ST."CREDATTIM_0">= now() - INTERVAL '4 DAYS'
            #     AND NOT EXISTS (SELECT 1 FROM {sgpAlias}.lotesgranuladolinha ll where ll.vcr_num = ST."VCRNUM_0")
            # ) t
            # where (QTY_SUM > 0)


        values = data['value'].split(";")
        conngw = connections[connGatewayName].cursor()
        sageAlias = dbgw.dbAlias.get("sage")
        sgpAlias = dbgw.dbAlias.get("sgp")
        print("CONSUMERRRRRRRRRRRRRRRRRRRRRRRRRRRR")
        print(f"""

            SELECT * FROM(
            SELECT
                ST."ROWID" lote_id,ST."CREDATTIM_0",ST."ITMREF_0",ST."LOT_0",ST."LOC_0",ST."VCRNUM_0",mprima."ITMDES1_0" artigo_des,
                LAST_VALUE(ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0" ORDER BY ST."ROWID" RANGE BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) "QTYPCU_0",
                --SUM (ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0") QTY_SUM,
                ST."PCU_0",mprima."ITMDES1_0"
                FROM {sageAlias}."STOCK" STK
                JOIN {sageAlias}."STOJOU" ST ON ST."ITMREF_0"=STK."ITMREF_0" AND ST."LOT_0"=STK."LOT_0" AND ST."LOC_0"=STK."LOC_0"
                JOIN {sageAlias}."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
                WHERE ST."VCRNUM_0"='{values[4]}'
            ) t
            where ("QTYPCU_0" > 0)
            and "LOC_0" in ('BUFFER')
            AND NOT EXISTS (SELECT 1 FROM {sgpAlias}.lotesgranuladolinha ll where ll.vcr_num = "VCRNUM_0") 


        """)
        rows = dbgw.executeSimpleList(lambda:(f"""

            SELECT * FROM(
            SELECT
                ST."ROWID" lote_id,ST."CREDATTIM_0",ST."ITMREF_0",ST."LOT_0",ST."LOC_0",ST."VCRNUM_0",mprima."ITMDES1_0" artigo_des,
                LAST_VALUE(ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0" ORDER BY ST."ROWID" RANGE BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) "QTYPCU_0",
                --SUM (ST."QTYPCU_0") OVER (PARTITION BY ST."ITMREF_0",ST."LOT_0",ST."VCRNUM_0") QTY_SUM,
                ST."PCU_0",mprima."ITMDES1_0"
                FROM {sageAlias}."STOCK" STK
                JOIN {sageAlias}."STOJOU" ST ON ST."ITMREF_0"=STK."ITMREF_0" AND ST."LOT_0"=STK."LOT_0" AND ST."LOC_0"=STK."LOC_0"
                JOIN {sageAlias}."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
                WHERE ST."VCRNUM_0"='{values[4]}'
            ) t
            where ("QTYPCU_0" > 0)
            and "LOC_0" in ('BUFFER')
            AND NOT EXISTS (SELECT 1 FROM {sgpAlias}.lotesgranuladolinha ll where ll.vcr_num = "VCRNUM_0") 


        """),conngw,{})["rows"]
        if len(rows)>0:            
            conn = connections["default"].cursor()
            rowsx = db.executeSimpleList(lambda:(f"""select id from lotesnwlinha where n_lote = '{values[1]}' and artigo_cod='{values[0]}' and vcr_num='{values[4]}'"""),conn,{})['rows']
            if len(rowsx)>0:
                self.send(text_data=json.dumps({"error":"O lote de Granulado já foi registado!","row":{"qty_lote":values[2],"unit":values[3], "n_lote":values[1]}},default=str))
            obs = values[5] if len(values)>5 else ''
            self.send(text_data=json.dumps({"error":None,"row":{"lote_id":rows[0]["lote_id"],"obs":obs, "artigo_des":rows[0]["artigo_des"], "artigo_cod":values[0], "qty_lote":values[2], "vcr_num":values[4], "unit":values[3], "n_lote":values[1] }},default=str))
        else:
            self.send(text_data=json.dumps({"error":"O lote de Granulado não existe ou não se enconta em buffer!","row":{"qty_lote":0, "unit":values[3], "n_lote":values[1]}},default=str))





    def getLote(self, data):
        lotePicked = data['value']
        cs = data['cs']
        lotes = cache.get(f'lotes-{cs}')
        code = [d for d in lotes if d['LOT_0'] == lotePicked]
        self.send(text_data=json.dumps(code,default=str))
    
    def loadMatPrimas(self, data):
        matPrimas = data['value']
        cs=data['cs']   
        connection = connections[connGatewayName].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT ST."ITMREF_0", ST."UPDDATTIM_0",ST."LOT_0", ST."QTYPCU_0", ST."PCUORI_0",ST."LOC_0"
            FROM "SAGE-PROD"."STOCK" ST Where ST."STOFCY_0" = 'E01' and ("LOC_0"='BUFFER' OR "ITMREF_0" LIKE 'R000%%')
            and "ITMREF_0" in (
            {matPrimas}
            )
            ORDER BY ST."UPDDATTIM_0" DESC
         """),connection,{})['rows']
        
        if len(rows)>0:
            cache.set(f'lotes-{cs}',rows,timeout=None)
        self.send(text_data=json.dumps({"status":"success"}))
    
    def loadBuffer(self, data):
        connection = connections[connGatewayName].cursor()
        rows = dbgw.executeSimpleList(lambda:(f"""		
            SELECT ST."ROWID",ST."ITMREF_0", ST."UPDDATTIM_0",ST."LOT_0", ST."QTYPCU_0", ST."PCUORI_0",ST."LOC_0", mprima."ITMDES1_0"
            FROM "SAGE-PROD"."STOCK" ST
            JOIN "SAGE-PROD"."ITMMASTER" mprima on ST."ITMREF_0"= mprima."ITMREF_0"
            Where ST."STOFCY_0" = 'E01' and ("LOC_0"='BUFFER' OR ST."ITMREF_0" LIKE 'R000%%')
            ORDER BY ST."UPDDATTIM_0" DESC
         """),connection,{})['rows']
        
        if len(rows)>0:
            self.send(text_data=json.dumps({"rows":rows,"item":"buffer"},default=str))

    def loadInProductionSettings(self, data):
        connection = connections["default"].cursor()
        rows = db.executeSimpleList(lambda:(f"""		
            select * from
                (
                SELECT acs.*, max(acs.id) over () mx_id, cs.id cs_id 
                from producao_currentsettings cs
                join audit_currentsettings acs on cs.id=acs.contextid
                where cs.status=3
                ) t
                where id=mx_id
         """),connection,{})['rows']
        
        if len(rows)>0:
            self.send(text_data=json.dumps({"rows":rows,"item":"inproduction"},default=str))
    
    # def loadLotesDosers(self, data):
    #     print("loadlotesdosers")
    #     connection = connections["default"].cursor()
    #     rows = db.executeSimpleList(lambda:(f"""		
    #         WITH DOSERS_GROUPS AS(
    #         select * from(
    #         SELECT id,doser,group_id,MAX(ld.id) over (PARTITION BY doser) max_id FROM lotesdosers ld
    #         ) t where t.max_id=id
    #         ),
    #         LOTES_DOSERS AS (
    #             SELECT doser,group_id,JSON_ARRAYAGG(JSON_OBJECT('group_id',group_id,'artigo_cod',artigo_cod,'n_lote',n_lote,'loteslinha_id',loteslinha_id,'t_stamp',mint_stamp)) lotes FROM(
    #             select ld.group_id,ld.doser,ld.artigo_cod,loteslinha_id,ld.n_lote,MIN(ld.t_stamp) mint_stamp #JSON_ARRAYAGG(JSON_OBJECT('artigo_cod',ld.artigo_cod,'n_lote',ld.n_lote,'t_stamp',ld.t_stamp))
    #             from lotesdosers ld
    #             JOIN DOSERS_GROUPS dg on ld.doser=dg.doser and ld.group_id=dg.group_id
    #             WHERE ld.loteslinha_id IS NOT NULL
    #             GROUP BY ld.group_id,ld.doser,ld.artigo_cod,ld.n_lote,ld.loteslinha_id
    #             ) t2
    #             GROUP BY group_id,doser
    #         )
    #         select group_id,d.doser,ld.lotes
    #         FROM JSON_TABLE(JSON_ARRAY('A1','A2','A3','A4','A5','A6','B1','B2','B3','B4','B5','B6','C1','C2','C3','C4','C5','C6'),"$[*]" COLUMNS(doser VARCHAR(2) PATH "$")) d
    #         LEFT JOIN LOTES_DOSERS ld on d.doser=ld.doser
    #      """),connection,{})['rows']
        
    #     if len(rows)>0:
    #         self.send(text_data=json.dumps({"rows":rows,"item":"lotesdosers"},default=str))

    # def loadLotesAvailability(self, data):
    #     connection = connections["default"].cursor()
    #     rows = db.executeSimpleList(lambda:(f"""		
    #         select t.*,SUM(t.qty_lote_available) over (PARTITION BY t.group_id) qty_artigo_available
    #         FROM (
    #             SELECT distinct
    #             DOSERS.group_id, LOTES.artigo_cod,LOTES.n_lote,LOTES.qty_lote,DOSERS.loteslinha_id,
    #             SUM(DOSERS.qty_consumed) over (PARTITION BY LOTES.artigo_cod,LOTES.n_lote) qty_lote_consumed,
    #             qty_lote + SUM(DOSERS.qty_consumed) over (PARTITION BY LOTES.artigo_cod,LOTES.n_lote) qty_lote_available,
    #             MIN(DOSERS.t_stamp) over (PARTITION BY LOTES.artigo_cod,LOTES.n_lote) min_t_stamp #FIFO DATE TO ORDER ASC
    #             FROM loteslinha LOTES
    #             LEFT JOIN lotesdosers DOSERS ON LOTES.id=DOSERS.loteslinha_id  #and LOTES.`group`=DOSERS.group_id 
    #             WHERE DOSERS.status=1 #and (DOSERS.t_stamp<='2022-04-11 16:37:30')
    #         ) t
    #      """),connection,{})['rows']
        
    #     if len(rows)>0:
    #         self.send(text_data=json.dumps({"rows":rows,"item":"lotesavailability"},default=str))

    def loadDosersSets(self, data):
        connection = connections["default"].cursor()
        rows = db.executeSimpleList(lambda:(f"""		
            SELECT * FROM ig_doseadores order by ig_doseadores_ndx DESC LIMIT 1;
         """),connection,{})['rows']
        
        if len(rows)>0:
            self.send(text_data=json.dumps({"rows":rows,"item":"doserssets"},default=str))

    def loadLotesDosers(self,data):
        connection = connections["default"].cursor()
        rows = db.executeSimpleList(lambda:(f"""		
           WITH
            VIEW_LINHA AS(SELECT * FROM loteslinha where `status` = 1 AND closed=0),
            VIEW_DOSERS AS(
                SELECT id,doser,n_lote,artigo_cod,t_stamp,qty_consumed,type_mov,loteslinha_id,group_id,ig_bobinagem_id,qty_to_consume,lote_id,t_stamp_fix,`order`,closed 
                FROM lotesdosers where `status` = 1 AND closed=0 #AND `order` < (select MIN(`order`) `limit_order` from lotesdosers ld where `status` <> 0 AND closed=0 AND ld.ig_bobinagem_id = 2460)
            ),
            DOSERS_GROUPS AS(
                select * from(
                SELECT id,doser,`order`,group_id,MAX(DOSERS.`order`) over (PARTITION BY doser) max_order FROM VIEW_DOSERS DOSERS
                ) t where t.max_order=`order`
            ),
            BASE_DOSERS AS(
            select * from(
                    select
                    DOSERS.* ,MAX(DOSERS.`order`) over (PARTITION BY DOSERS.lote_id) max_order
                    FROM VIEW_LINHA LINHA
                    LEFT JOIN VIEW_DOSERS DOSERS ON LINHA.id=DOSERS.loteslinha_id 
                ) t WHERE max_order=`order`
            ),
            LOTES_DOSERS_BY_DOSER AS (
            SELECT doser,JSON_ARRAYAGG(JSON_OBJECT('group_id',group_id,'artigo_cod',artigo_cod,'lote_id',lote_id,'n_lote',n_lote,'loteslinha_id',loteslinha_id,'t_stamp',mint_stamp)) lotes FROM(
            select ld.group_id,ld.doser,ld.artigo_cod,loteslinha_id,ld.n_lote,lote_id,MIN(ld.t_stamp) mint_stamp #JSON_ARRAYAGG(JSON_OBJECT('artigo_cod',ld.artigo_cod,'n_lote',ld.n_lote,'t_stamp',ld.t_stamp))
            from BASE_DOSERS ld
            JOIN DOSERS_GROUPS dg on ld.doser=dg.doser and ld.group_id=dg.group_id
            WHERE ld.loteslinha_id IS NOT NULL
            GROUP BY ld.group_id,ld.doser,ld.artigo_cod,ld.lote_id,ld.n_lote,ld.loteslinha_id
            ) t2
            GROUP BY doser
            ),
            LOTES_DOSERS_BY_LOTES AS (
            SELECT 
            t2.*#group_id, artigo_cod,n_lote,loteslinha_id, JSON_ARRAYAGG(JSON_OBJECT('doser',doser,'t_stamp',mint_stamp)) lotes 
            FROM(
            select ld.group_id,ld.doser,ld.artigo_cod,loteslinha_id,ld.lote_id,ld.n_lote,MIN(ld.`order`) min_order #JSON_ARRAYAGG(JSON_OBJECT('artigo_cod',ld.artigo_cod,'n_lote',ld.n_lote,'t_stamp',ld.t_stamp))
            from BASE_DOSERS ld
            JOIN DOSERS_GROUPS dg on ld.doser=dg.doser and ld.group_id=dg.group_id
            WHERE ld.loteslinha_id IS NOT NULL
            GROUP BY ld.group_id,ld.doser,ld.artigo_cod,ld.lote_id,ld.n_lote,ld.loteslinha_id
            ) t2
            #GROUP BY group_id,artigo_cod,n_lote
            ),
            LOTES_AVAILABLE AS(
            select t.*,SUM(t.qty_lote_available) over (PARTITION BY t.group_id) qty_artigo_available
            FROM (
                SELECT DISTINCT * FROM (
                SELECT 
                DOSERS.group_id, LOTES.artigo_cod,LOTES.lote_id,LOTES.n_lote,LOTES.qty_lote,DOSERS.loteslinha_id,DOSERS.`order`,
                SUM(DOSERS.qty_consumed) over (PARTITION BY LOTES.lote_id) qty_lote_consumed,
                qty_lote + SUM(DOSERS.qty_consumed) over (PARTITION BY LOTES.lote_id) qty_lote_available,
                MIN(DOSERS.`order`) over (PARTITION BY LOTES.lote_id) min_order, #FIFO DATE TO ORDER ASC
                MAX(DOSERS.`order`) over (PARTITION BY LOTES.lote_id) max_order
                FROM VIEW_LINHA LOTES
                LEFT JOIN VIEW_DOSERS DOSERS ON LOTES.id=DOSERS.loteslinha_id
                WHERE DOSERS.group_id is not null
                ) t WHERE  max_order=`order`
            ) t WHERE qty_lote_available>0
            )
            SELECT LD.group_id,LD.artigo_cod,
            JSON_ARRAYAGG(d.doser) dosers,
            JSON_ARRAYAGG(JSON_OBJECT('lote_id',LA.lote_id,'n_lote',LA.n_lote,'qty_lote',LA.qty_lote,'qty_lote_consumed',LA.qty_lote_consumed,'qty_lote_available',LA.qty_lote_available)) lotes
            FROM JSON_TABLE(JSON_ARRAY('A1','A2','A3','A4','A5','A6','B1','B2','B3','B4','B5','B6','C1','C2','C3','C4','C5','C6'),"$[*]" COLUMNS(doser VARCHAR(2) PATH "$")) d
            LEFT JOIN LOTES_DOSERS_BY_LOTES LD on LD.doser=d.doser
            LEFT JOIN LOTES_AVAILABLE LA ON LA.group_id = LD.group_id AND LA.loteslinha_id=LD.loteslinha_id
            group by group_id,artigo_cod
         """),connection,{})['rows']
        print("-------------------")
        print(rows)
        if len(rows)>0:
            self.send(text_data=json.dumps({"rows":rows,"item":"lotesdosers"},default=str))

    commands = {
        #'loadlotesdosers':loadLotesDosers,
        'loadlotesdosers':loadLotesDosers,
        'loadinproduction':loadInProductionSettings,
        'loadbuffer':loadBuffer,
        'loadmatprimas':loadMatPrimas,
        #'loadlotesavailability':loadLotesAvailability,
        'loaddoserssets':loadDosersSets,
        'pick':getLote,
        'getlotequantity':getLoteQuantity,
        'getnwlotequantity':getNWLoteQuantity,
        'getgranuladolotequantity':getGranuladoLoteQuantity
    }

    def connect(self):
        #print(f'CONNECT----{self.scope}')
        # self.room_name = 'room'
        # self.room_group_name = 'chat_%s' % self.room_name

        # # Join room group
        # async_to_sync(self.channel_layer.group_add)(
        #     self.room_group_name,
        #     self.channel_name
        # )
        self.accept()

    def disconnect(self, close_code):
        pass
        # leave group room
        # async_to_sync(self.channel_layer.group_discard)(
        #     self.room_group_name,
        #     self.channel_name
        # )

    def receive(self, text_data):
        dt = json.loads(text_data)
        self.commands[dt['cmd']](self, dt)