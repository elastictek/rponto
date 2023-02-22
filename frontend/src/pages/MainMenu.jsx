import React, { useEffect, useState, useCallback, useRef, Suspense, useContext, useLayoutEffect } from 'react';
import { createUseStyles } from 'react-jss';
import styled from 'styled-components';
import { useNavigate, useLocation } from "react-router-dom";
import dayjs from 'dayjs';
import Joi from 'joi';
import { fetch, fetchPost, cancelToken } from "utils/fetch";
import { API_URL, ROOT_URL } from "config";
// import { useModal } from "react-modal-hook";
import YScroll from "components/YScroll";
import { Button, Select, Typography, Card, Collapse, Space } from "antd";
const { Panel } = Collapse;
// import { EditOutlined, HistoryOutlined } from '@ant-design/icons';
// import ResponsiveModal from 'components/Modal';
// import { usePermission, Permissions } from "utils/usePermission";

const StyledCollapse = styled(Collapse)`
    .ant-collapse-content-box{
        padding:0px 0px !important;
        display:flex;
        flex-direction:column;
        align-items:start;
    }
    .ant-collapse-header-text{
        color:#fff;
        font-size:14px;
    }
    .ant-collapse-expand-icon{
        color:#fff;
    }
    .ant-btn-link{
        color:#d9d9d9;
        &:hover{
            background:#91d5ff;
            color:#000;
        }
    }
    .ant-collapse-header{
        padding:0px 0px !important;
    }
`

const getLocalStorage = (id) => {
    if (id) {
        const selItems = JSON.parse(localStorage.getItem(id));
        return (selItems) ? selItems : ['1'];
    }
    return ['1'];
}
const idMenu = "rponto-menu-01";
const selectedItems = getLocalStorage(idMenu);

export default ({ dark = false, onToggleDrawer }) => {
    const navigate = useNavigate();
    // const permission = usePermission({ name: "mainmenu" });
    // const [modalParameters, setModalParameters] = useState({});
    // const [showModal, hideModal] = useModal(({ in: open, onExited }) => (
    //     <ResponsiveModal footer="ref" onCancel={hideModal} width={800} height={400}>
    //         <div></div>
    //     </ResponsiveModal>
    // ), [modalParameters]);
    // const onEdit = () => {
    //     setModalParameters({ ...record });
    //     showModal();
    // }
    // const [showFrameModal, hideFrameModal] = useModal(({ in: open, onExited }) => (
    //     <ResponsiveModal title={modalParameters.title} lazy={true} footer="ref" onCancel={hideFrameModal} width={5000} height={5000}><IFrame src={modalParameters.src} /></ResponsiveModal>
    // ), [modalParameters]);

    const onMenuChange = (v) => {
        localStorage.setItem(idMenu, JSON.stringify(v));

    }

    // const onClickItemFrame = (src, title) => {
    //     setModalParameters({ src, title });
    //     showFrameModal();
    // }

    return (

        <StyledCollapse defaultActiveKey={selectedItems} ghost={true} expandIconPosition="end" onChange={onMenuChange}>
                <Panel header={<b>Recursos Humanos</b>} key="1">
                    <Button block style={{textAlign:"left"}} size='large' type="link" onClick={() => {navigate('/app/rh/registos', {});onToggleDrawer();}}>Registo de Picagens</Button>
                    <Button block style={{textAlign:"left"}} size='large' type="link" onClick={() => {navigate('/app/rh/plan', {});onToggleDrawer();}}>Plano de Horários</Button>
                </Panel>
        </StyledCollapse>

    );

}