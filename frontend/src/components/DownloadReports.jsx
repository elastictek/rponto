import React, { useEffect, useState, useCallback, useRef, useContext } from 'react';
import { Button, Menu, Dropdown, InputNumber, Popover, Select, message } from "antd";
import { FilePdfTwoTone, FileExcelTwoTone, FileWordTwoTone, FileFilled, DownOutlined } from '@ant-design/icons';
import axios from 'axios';
import uuIdInt from "utils/uuIdInt";
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';


/* const menuItems = [
    { label: 'Packing List', key: 'pl-pdf', icon: <FilePdfTwoTone twoToneColor="red" style={{ fontSize: "18px" }} /> },
    { label: 'Packing List', key: 'pl-excel', icon: <FileExcelTwoTone twoToneColor="#52c41a" style={{ fontSize: "18px" }} /> },
    { label: 'Packing List Detalhado', key: 'pld-pdf', icon: <FilePdfTwoTone twoToneColor="red" style={{ fontSize: "18px" }} /> },
    { label: 'Packing List Detalhado', key: 'pld-excel', icon: <FileExcelTwoTone twoToneColor="#52c41a" style={{ fontSize: "18px" }} /> }
]; */

/* const menu = (
    <Menu onClick={(v) => exportFile(v)}>
        <Menu.Item key="pdf" icon={<FilePdfTwoTone twoToneColor="red" />}>Pdf</Menu.Item>
        <Menu.Item key="excel" icon={<FileExcelTwoTone twoToneColor="#52c41a" />}>Excel</Menu.Item>
        <Menu.Item key="word" icon={<FileWordTwoTone />}>Word</Menu.Item>
    </Menu>
); */

const downloadFile = (data, filename, mime, bom) => {
    var blobData = (typeof bom !== 'undefined') ? [bom, data] : [data]
    var blob = new Blob(blobData, { type: mime || 'application/octet-stream' });
    if (typeof window.navigator.msSaveBlob !== 'undefined') {
        // IE workaround for "HTML7007: One or more blob URLs were
        // revoked by closing the blob for which they were created.
        // These URLs will no longer resolve as the data backing
        // the URL has been freed."
        window.navigator.msSaveBlob(blob, filename);
    }
    else {
        var blobURL = (window.URL && window.URL.createObjectURL) ? window.URL.createObjectURL(blob) : window.webkitURL.createObjectURL(blob);
        var tempLink = document.createElement('a');
        tempLink.style.display = 'none';
        tempLink.href = blobURL;
        tempLink.setAttribute('download', filename);

        // Safari thinks _blank anchor are pop ups. We only want to set _blank
        // target if the browser does not support the HTML5 download attribute.
        // This allows you to download files in desktop safari if pop up blocking
        // is enabled.
        if (typeof tempLink.download === 'undefined') {
            tempLink.setAttribute('target', '_blank');
        }

        document.body.appendChild(tempLink);
        tempLink.click();

        // Fixes "webkit blob resource error 1"
        setTimeout(function () {
            document.body.removeChild(tempLink);
            window.URL.revokeObjectURL(blobURL);
        }, 200);
    }
};

const PopupProgress = ({ controller, content, messageKey }) => {

    const oc = () => {
        message.destroy(messageKey);
        controller.abort();
    }
    return (<div>
        <Button size="small" style={{ marginBottom: "5px" }} onClick={oc}>Cancelar</Button>
        {content}
    </div>);
}


const getMenuItems = (items) => {
    if (items.length === 0) {
        return [
            { label: 'Pdf', key: 'pdf', icon: <FilePdfTwoTone twoToneColor="red" style={{ fontSize: "18px" }} />, data: { orientation: "landscape", extension: "pdf" } },
            { label: 'Excel', key: 'excel', icon: <FileExcelTwoTone twoToneColor="#52c41a" style={{ fontSize: "18px" }} />, data: { orientation: "landscape", extension: "xlsx" } },
            { label: 'Excel (Sem formatação)', key: 'clean-excel', icon: <FileExcelTwoTone twoToneColor="#52c41a" style={{ fontSize: "18px" }} />, data: { orientation: "landscape", extension: "xlsx" } },
            { label: 'Word', key: 'word', icon: <FileWordTwoTone style={{ fontSize: "18px" }} />, data: { orientation: "landscape", extension: "docx" } }
        ];
    }
    return items;
}

const Content = ({ menuItems, limit, setLimit, orientation, setOrientation, setIsDirty, onClick }) => {
    return (
        <div style={{ display: "flex", flexDirection: "column" }}>
            <Menu onClick={(v) => onClick(v)} items={menuItems}></Menu>
            <div style={{ display: "flex", flexDirection: "row", alignItems: "center" }}><div><b>Max. Linhas:</b></div><InputNumber min={100} max={50000} size="small" value={limit} onChange={(v) => { setIsDirty(true); setLimit(v); }} style={{ marginLeft: "5px", marginBottom: "5px", marginTop: "5px" }} /></div>
            <Select value={orientation} onChange={(v) => { setIsDirty(true); setOrientation(v); }} size="small" options={[{ value: "landsacpe", label: "Horizontal" }, { value: "vertical", label: "Vertical" }]} />
        </div>
    );
}


export const downloadReport = async ({ dataAPI, url, type, dataexport, limit, title, orientation, isDirty, columns }) => {
    const requestData = dataAPI.getPostRequest({ url });
    const _orientation = (!isDirty && dataexport?.orientation) ? dataexport?.orientation : orientation.value;
    const _title = (dataexport?.title) ? dataexport?.title : title;

    let cols = {};
    if (Array.isArray(columns)) {
        for (const v of columns) {
            cols[v.key] = { title: v?.reportTitle ? v.reportTitle : (typeof (v.name) !== "object" ? v.name : v.key), width: v.width, format: v?.reportFormat && v.reportFormat };
        }
    }else{
        cols=columns;
    }

    requestData.parameters = {
        ...requestData.parameters,
        "config": "default",
        ...(_title) && { title: _title },
        "template": `TEMPLATES-LIST/LIST-A4-${_orientation.toUpperCase()}`,
        "export": type.key,
        "orientation": _orientation.toUpperCase(),
        "limit": limit ? limit : 5000,
        ...(columns) && { cols },
        ...dataexport
    };
    const { filter = {}, sort = [], pagination = {}, parameters = {} } = requestData;
    const fetch = { url: requestData.url, method: "post", responseType: "blob", data: { sort, filter, pagination, parameters } };
    const controller = new AbortController();
    let mkey = uuIdInt(4);
    message.loading({
        key: mkey,
        content: <PopupProgress messageKey={mkey} controller={controller} content={<div>A exportar, aguarde um momento, Por favor...[Limite {limit} linhas]</div>} />,
        duration: 0,
        style: {
            marginRight: '5px',
        }
    });

    const response = await axios({
        ...fetch,
        signal: controller.signal
    });
    message.destroy(mkey);
    downloadFile(response.data, `list-${new Date().toJSON().slice(0, 10)}.${dataexport.extension}`);
}


export const Report = ({ button, items = [], onExport, dataAPI, title, columns, hide }) => {
    const [isDirty, setIsDirty] = useState(false);
    const [limit, setLimit] = useState(10000);
    const [orientation, setOrientation] = useState({ value: "landscape", label: "Horizontal" });
    const menuItems = getMenuItems(items, limit, setLimit);

    const onClick = async (type) => {
        hide();
        if (onExport) {
            if (!onExport(type, limit, orientation, isDirty)) {
                return false;
            }
        }
        let dataexport = menuItems.filter(v => v.key === type.key)[0]?.data;
        await downloadReport({ dataAPI, type, dataexport, columns, limit, orientation, title, isDirty });
    }

    return (
        <Content setIsDirty={setIsDirty} orientation={orientation} setOrientation={setOrientation} limit={limit} setLimit={setLimit} onClick={onClick} menuItems={menuItems} />
    );
}

export default ({ button, items = [], onExport, dataAPI, title, columns }) => {
    const [isDirty, setIsDirty] = useState(false);
    const [limit, setLimit] = useState(10000);
    const [clickPopover, setClickPopover] = useState(false);
    const [orientation, setOrientation] = useState({ value: "landscape", label: "Horizontal" });
    const menuItems = getMenuItems(items, limit, setLimit);

    const hide = () => {
        setClickPopover(false);
    };

    const handleClickPopover = (visible) => {
        setClickPopover(visible);
    };


    const onClick = async (type) => {
        hide();
        if (onExport) {
            if (!onExport(type, limit, orientation, isDirty)) {
                return false;
            }
        }
        let dataexport = menuItems.filter(v => v.key === type.key)[0]?.data;
        await downloadReport({ dataAPI, type, dataexport, columns, limit, orientation, title, isDirty });
        /*  const requestData = dataAPI.getPostRequest();
         const _orientation = (!isDirty && dataexport?.orientation) ? dataexport?.orientation : orientation.value;
         const _title = (dataexport?.title) ? dataexport?.title : title;
         requestData.parameters = {
             ...requestData.parameters,
             "config": "default",
             title: _title,
             "template": `TEMPLATES-LIST/LIST-A4-${_orientation.toUpperCase()}`,
             ...dataexport,
             "export": type.key,
             "orientation": _orientation.toUpperCase(),
             ...(columns) && { cols: columns }
         };
         const { filter = {}, sort = [], pagination = {}, parameters = {} } = requestData;
         const fetch = { url: requestData.url, method: "post", responseType: "blob", data: { sort, filter, pagination, parameters } };
 
         const controller = new AbortController();
         let mkey = uuIdInt(4);
         message.loading({
             key: mkey,
             content: <PopupProgress messageKey={mkey} controller={controller} content={<div>A exportar, aguarde um momento, Por favor...[Limite {limit} linhas]</div>} />,
             duration: 0,
             style: {
                 marginRight: '5px',
             }
         });
 
         const response = await axios({
             ...fetch,
             signal: controller.signal
         });
         message.destroy(mkey);
         downloadFile(response.data, `list-${new Date().toJSON().slice(0, 10)}.${dataexport.extension}`); */
    }

    return (
        <>
            {!button && <Popover
                open={clickPopover}
                onOpenChange={handleClickPopover}
                placement="bottomRight" title="Exportar" content={<Content setIsDirty={setIsDirty} orientation={orientation} setOrientation={setOrientation} limit={limit} setLimit={setLimit} onClick={onClick} menuItems={menuItems} />} trigger="click">
                <Button size="small" icon={<FileFilled />}><DownOutlined /></Button>
            </Popover>}
            {button && <Popover
                open={clickPopover}
                onOpenChange={handleClickPopover}
                placement="bottomRight" title="Exportar" content={<Content setIsDirty={setIsDirty} orientation={orientation} setOrientation={setOrientation} limit={limit} setLimit={setLimit} onClick={onClick} menuItems={menuItems} />} trigger="click">
                {button}
            </Popover>}
            {/*  {!button &&
                <Dropdown overlay={<Menu onClick={(v) => exportFile(v, menuItems, onExport)} items={menuItems}></Menu>} trigger={['click']}>
                    <Button size="small" icon={<FileFilled />}><DownOutlined /></Button>
                </Dropdown>}
            {button && <Dropdown overlay={getMenuItems(items)} trigger={['click']}>
                {button}
            </Dropdown>} */}
        </>
    );
}