import React, { useEffect, useState, useCallback, useRef, useContext } from 'react';
import { createUseStyles } from 'react-jss';
import styled from 'styled-components';
import dayjs from 'dayjs';
import Joi from 'joi';
import { fetch, fetchPost, cancelToken } from "utils/fetch";
import { API_URL } from "config";
import { WrapperForm, TitleForm, FormLayout, Field, FieldSet, Label, LabelField, FieldItem, AlertsContainer, Item, SelectField, InputAddon } from "components/formLayout";
import Toolbar from "components/toolbar";
import Portal from "components/portal";
import { Button, Spin, Form, Space, Input } from "antd";
import { LoadingOutlined, EditOutlined } from '@ant-design/icons';
import { DATE_FORMAT, DATETIME_FORMAT } from 'config';
import { OFabricoContext } from './FormOFabricoValidar';

const schema = (keys, excludeKeys) => {
    return getSchema({}, keys, excludeKeys).unknown(true);
}

const Drawer = ({ showWrapper, setShowWrapper, parentReload }) => {
    const [formTitle, setFormTitle] = useState({});
    const iref = useRef();
    const { record = {} } = showWrapper;
    const onVisible = () => {
        setShowWrapper(prev => ({ ...prev, show: !prev.show }));
    }
    return (
        <WrapperForm
            title={<TitleForm title={formTitle.title} subTitle={formTitle.subTitle} />}
            type="drawer"
            destroyOnClose={true}
            mask={true}
            style={{}}
            setVisible={onVisible}
            visible={showWrapper.show}
            width={800}
            bodyStyle={{ height: "450px" /*  paddingBottom: 80 *//* , overflowY: "auto", minHeight: "350px", maxHeight: "calc(100vh - 50px)" */ }}
            footer={<div ref={iref} id="form-wrapper" style={{ textAlign: 'right' }}></div>}
        >
            {/* <FormToCall setFormTitle={setFormTitle} record={record} parentRef={iref} closeParent={onVisible} parentReload={parentReload} /> */}
        </WrapperForm>
    );
}

const loadLookup = async ({token}) => {
    const { data: { rows } } = await fetchPost({ url: `${API_URL}/.../`, filter: {  }, sort: [], cancelToken: token });
    return rows;
}

const setId = (id) => {
    if (id) {
        return { key: "update", values: { id } };
    }
    return { key: "insert", values: {} };
}

export default ({ record, setFormTitle, parentRef/* , changedValues = {} */ }) => {
    /* const { form, guides, schema, fieldStatus, ...ctx } = useContext(OFabricoContext); */
    const [form] = Form.useForm();
    const [guides, setGuides] = useState(false);
    const [loading, setLoading] = useState(true);
    const [operation, setOperation] = useState(setId(record.aggItem.paletizacao_id));
    const [showSchema, setShowSchema] = useState({ show: false });
    const [lookupData, setLookupData] = useState([]);
    const [changedValues, setChangedValues] = useState({});
    const [resultMessage, setResultMessage] = useState({ status: "none" });

    const init = () => {
        (setFormTitle) && setFormTitle({ title: `Title`, subTitle: `Title` });
    }

    useEffect(() => {
        init();
    }, []);


    useEffect(() => {
        const cancelFetch = cancelToken();
        loadData({ token: cancelFetch });
        return (() => cancelFetch.cancel("Form Settings Cancelled"));
    }, [changedValues]);



    const onValuesChange = (changedValues, allValues) => {
/*         if ("xxxx" in changedValues) {
            setChangedValues(changedValues);
        } */
    }

    const onFinish = async () => {
        const response = await fetchPost({ url: `${API_URL}/..../`, parameters: { type:"xxxx" } });
        setResultMessage(response.data);
        // const status = { error: [], warning: [], info: [], success: [] };
        // const msgKeys = ["start_date", "start_hour", "end_date", "end_hour"];
        // const { cliente_cod, cliente_nome, iorder, item, ofabrico, produto_id, item_id } = record;
        // const { core_cod: { value: core_cod, label: core_des } = {} } = values;
        // const { cortes_id, cortesordem_id } = form.getFieldsValue(true);
        // let diff = {};
        // const v = schema().custom((v, h) => {
        //     const { start_date, start_hour, end_date, end_hour } = v;
        //     diff = dateTimeDiffValidator(start_date, start_hour, end_date, end_hour);
        //     if (diff.errors == true) {
        //         return h.message("A Data de Fim tem de ser Maior que a Data de Início", { key: "start_date", label: "start_date" })
        //     }
        // }).validate(values, { abortEarly: false });
        // status.error = [...status.error, ...(v.error ? v.error?.details.filter((v) => msgKeys.includes(v.context.key)) : [])];
        // status.warning = [...status.warning, ...(v.warning ? v.warning?.details.filter((v) => msgKeys.includes(v.context.key)) : [])];
        // if (!v.error) { }
        // if (status.error.length === 0) {
        //     const response = await fetchPost({ url: `${API_URL}/savetempordemfabrico/`, parameters: { ...values, cliente_cod, cliente_nome, iorder, item, item_id, ofabrico, core_cod, core_des, produto_id, cortes_id, cortesordem_id } });
        //     setResultMessage(response.data);
        // }
        // setFieldStatus(diff.fields);
        // setFormStatus(status);
    }

    const loadData = (data = {}, type = "init") => {
        const { token } = data;
        switch (type) {
            case "lookup":
                setLoading(true);
                (async () => {
                    setLookupData(await loadLookup({ token }));
                    setLoading(false);
                })();
                break;
            default:
                if (!loading) {
                    setLoading(true);
                }
                (async () => {
                        form.setFieldsValue({});
                        setLoading(false);
                })();
        }
    }

    return (
        <>
            <Spin spinning={loading} indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} tip="A carregar...">
                <Form form={form} name={`form-of-settings`} onFinish={onFinish} onValuesChange={onValuesChange}>
                    <FormLayout
                        id="LAY-SETTINGS"
                        guides={guides}
                        layout="vertical"
                        style={{ width: "100%", padding: "0px"/* , minWidth: "700px" */ }}
                        schema={schema}
                        field={{
                            //wide: [3, 2, 1, '*'],
                            margin: "2px", overflow: false, guides: guides,
                            label: { enabled: true, pos: "top", align: "start", vAlign: "center", /* width: "80px", */ wrap: false, overflow: false, colon: true, ellipsis: true },
                            alert: { pos: "right", tooltip: true, container: true /* container: "el-external" */ },
                            layout: { top: "", right: "", center: "", bottom: "", left: "" },
                            addons: {}, //top|right|center|bottom|left
                            required: true,
                            style: { alignSelf: "top" }
                        }}
                        fieldSet={{
                            guides: guides,
                            wide: 16, margin: "2px", layout: "horizontal", overflow: false
                        }}
                    >
                    </FormLayout>
                </Form>
                {parentRef && <Portal elId={parentRef.current}>
                    <Space>
                        <Button type="primary" onClick={onFinish}>Guardar</Button>
                        <Button onClick={() => setGuides(!guides)}>{guides ? "No Guides" : "Guides"}</Button>
                    </Space>
                </Portal>
                }
            </Spin>
        </>
    );
}