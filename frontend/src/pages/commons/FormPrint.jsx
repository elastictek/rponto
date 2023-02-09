import React, { useEffect, useState, useCallback, useRef, useContext, Suspense, lazy } from 'react';
import { createUseStyles } from 'react-jss';
import styled from 'styled-components';
import {  fetchPost } from "utils/fetch";

import { Container, Row, Col, Visible, Hidden } from 'react-grid-system';


import { Space, Typography, Button, Select, Modal, InputNumber, Checkbox, Badge } from "antd";
import { API_URL } from 'config';

export default ({ v, parentRef, closeParent }) => {
    const [values, setValues] = useState({ impressora: "Bobinadora_CAB_A4_200", num_copias: 1 })
    const onClick = async () => {
        const response = await fetchPost({ url: `${API_URL}/printetiqueta/`, parameters: { 
            ...v?.bobinagem && {type: "bobinagem", bobinagem: v.bobinagem},
            ...v?.palete && {type: "palete", palete: v.palete}, 
            ...values } 
        });
        if (response.data.status !== "error") {
            closeParent();
        } else {
            Modal.error({ title: response.data.title })
        }

    }

    const onChange = (t, v) => {
        setValues(prev => ({ ...prev, [t]: v }));
    }

    return (<>
        <Container>
            <Row>
                <Col><b>Cópias:</b></Col>
            </Row>
            <Row>
                <Col><InputNumber onChange={(v) => onChange("num_copias", v)} min={1} max={3} defaultValue={values.num_copias} /></Col>
            </Row>
            <Row>
                <Col><b>Impressora:</b></Col>
            </Row>
            <Row>
                <Col><Select onChange={(v) => onChange("impressora", v)} defaultValue={values.impressora} style={{ width: "100%" }} options={[{ value: 'Bobinadora_CAB_A4_200', label: 'BOBINADORA' }, { value: 'DM12_CAB_A4_200', label: 'DM12' }]} /></Col>
            </Row>
            <Row style={{ marginTop: "15px" }}>
                <Col style={{ textAlign: "right" }}>
                    <Space>
                        <Button onClick={closeParent}>Cancelar</Button>
                        <Button type="primary" onClick={onClick}>Imprimir</Button>
                    </Space>
                </Col>
            </Row>
        </Container>
    </>);
}