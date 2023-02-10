import React, { useEffect, useState, Suspense, lazy, useContext } from 'react';
import { Route, Routes, useRoutes, BrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { Button, Spin, Form, Space, Input, InputNumber, Tooltip, Menu, Collapse, Typography, Modal, Select, Tag, DatePicker, Alert, Drawer, Checkbox } from "antd";
import { Container, Row, Col,Hidden } from 'react-grid-system';
import styled from 'styled-components';
import { EnterOutlined, RedoOutlined, WarningTwoTone, CloseCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import Webcam from "react-webcam";
import { useSubmitting } from "utils";
import { API_URL } from "config";
import { fetch, fetchPost, cancelToken } from "utils/fetch";
import Logo from 'assets/logo.svg';
import dayjs from 'dayjs';
import { DATETIME_FORMAT, MESSAGE_IN, MESSAGE_OUT } from 'config';

const StyledButton = styled(Button)`
	font-weight:700;
	width:150px!important;
	height:70px!important;
	font-size:25px;
`;


const videoConstraints = {
	width: 1280,
	height: 720,
	facingMode: "user"
};

export default ({ }) => {
	const submitting = useSubmitting(false);
	const [num, setNum] = useState('');
	const [nome, setNome] = useState('');
	const [error, setError] = useState({ status: false, text: '' });
	const [snapshot, setSnapshot] = useState();
	const [confirmed, setConfirmed] = useState(false);
	const [dateState, setDateState] = useState(new Date());
	const [date, setDate] = useState();
	const [hsh, setHsh] = useState();
	const [type, setType] = useState();
	const webcamRef = React.useRef(null);
	const timeout = React.useRef(null);

	const loadInterval = async () => {
		const request = (async () => setDateState(new Date()));
		request();
		return setInterval(request, 1000);
	}
	useEffect(() => {
		//const controller = new AbortController();
		const interval = loadInterval();
		return (() => { clearInterval(interval); });
	}, []);

	const capture = React.useCallback(
		async () => {

			const imageSrc = webcamRef.current.getScreenshot();
			setSnapshot(imageSrc);
			submitting.trigger();
			try {
				const vals = { num: `F${num.padStart(5, '0')}` };
				setNum(num.padStart(3, '0'));
				const _ds = dateState
				setDate(_ds);
				let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", snapshot: imageSrc, timestamp: dayjs(_ds).format(DATETIME_FORMAT) } });
				if (response.data.status !== "error" && response.data?.rows?.length > 0) {
					setNome(`${response.data.rows[0].SRN_0} ${response.data.rows[0].NAM_0}`);
					//timeout.current = setTimeout(reset, 10000);
				} else {
					setError({ status: true, text: "O número que indicou não existe!" });
				}
				submitting.end();
			} catch (e) {
				setError({ status: true, text: e.message });
				submitting.end();
			};

		},
		[webcamRef, num]
	);

	const reset = () => {
		if (timeout.current) {
			clearTimeout(timeout.current);
		}
		timeout.current = null;
		setNum('');
		setSnapshot(null);
		setNome("");
		setError({ status: false, text: "" });
		setDate(null);
		setConfirmed(false);
		setHsh(null);
		setType(null);
	}

	const onClick = (v) => {
		if (v === "C") {
			setNum('');
		} else if (v === "ENTER") {

		} else {
			if (num.length < 3) {
				setNum(prev => `${prev}${v}`);
			}
		}
	}

	const onConfirm = async (v) => {
		if (v === true) {
			submitting.trigger();
			try {
				const vals = { num: `F${num.padStart(5, '0')}` };
				let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", save: true, snapshot, timestamp: dayjs(date).format(DATETIME_FORMAT) } });
				if (response.data.status !== "error" && response.data.hsh) {
					setConfirmed(true);
					setHsh(response.data.hsh);
					timeout.current = setTimeout(reset, 10000);
				} else {
					setError({ status: true, text: response.data?.title });
				}
				submitting.end();
			} catch (e) {
				setError({ status: true, text: e.message });
				submitting.end();
			};
		}
		else {
			reset();
		}
	}

	const onFinish = async (t) => {
		if (timeout.current) {
			clearTimeout(timeout.current);
		}
		timeout.current = null;
		submitting.trigger();
		try {
			const vals = { num: `F${num.padStart(5, '0')}` };
			let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", hsh, save: true, type: t } });
			if (response.data.status !== "error") {
				setType(t);
				timeout.current = setTimeout(reset, 10000);
			} else {
				setError({ status: true, text: "Ocorreu um erro no registo." });
				submitting.end();
			}
		} catch (e) {
			setError({ status: true, text: e.message });
			submitting.end();
		};
	}

	return (<>
		<Container fluid style={{ fontWeight: 700 }}>

			{type &&
				<Row nogutter style={{ height: "70vh", display: "flex", alignItems: "center" }}>
					<Col>
						<Row>
							<Col></Col>
							<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>{type == "in" ? MESSAGE_IN : MESSAGE_OUT}</Col>
							<Col></Col>
						</Row>
						<Row>
							<Col></Col>
							<Col xs="content"><Button type='link' size="large" onClick={reset} style={{}}>Novo Registo</Button></Col>
							<Col></Col>
						</Row>
					</Col>
				</Row>
			}

			{!type && <>

				<Row gutterWidth={2} style={{ margin: "10px 0px 10px 0px", alignItems: "center" }}>
					<Col>
						<Row nogutter style={{ background: "#f0f0f0", borderRadius: "5px", padding: "5px", display: "flex", alignItems: "center", marginBottom: "30px" }}>
							<Col style={{ textAlign: "left" }}><Logo style={{ width: "100px", height: "16px" }} /></Col>
							<Col style={{ textAlign: "center", fontSize: "24px", fontWeight: 700 }}>{!date && dateState.toLocaleTimeString('pt-PT', {
								hour: '2-digit',
								minute: '2-digit',
								second: '2-digit'
							})}
								{date && date.toLocaleTimeString('pt-PT', {
									hour: '2-digit',
									minute: '2-digit',
									second: '2-digit'
								})}</Col>
							<Col style={{ textAlign: "right", fontWeight: 400, fontSize: "14px" }}>
								{!date && dateState.toLocaleDateString('pt-PT', {
									day: '2-digit',
									month: 'long',
									year: 'numeric'
								})}
								{date && date.toLocaleDateString('pt-PT', {
									day: '2-digit',
									month: 'long',
									year: 'numeric'
								})}
							</Col>
						</Row>
					</Col>
				</Row>

				<Row gutterWidth={2} style={{ margin: "0px 0px 10px 0px", alignItems: "center" }}>
					<Col></Col>
					<Col style={{ display: "flex", justifyContent: "center" }}>
						<Row gutterWidth={15}>
							<Col xs="content" style={{ height: "100%", alignSelf: "center" }}>
								{/* 	<Row nogutter>
									<Col></Col>
									<Col xs="content" style={{ alignSelf: "center" }}><Logo style={{ width: "200px", height: "24px" }} /></Col>
									<Col></Col>
								</Row>
								<Row nogutter>
									<Col style={{ fontSize: "16px", fontWeight: 400, textAlign: "center" }}>
										{!date && dateState.toLocaleDateString('pt-PT', {
											day: '2-digit',
											month: 'long',
											year: 'numeric'
										})}
										{date && date.toLocaleDateString('pt-PT', {
											day: '2-digit',
											month: 'long',
											year: 'numeric'
										})}
									</Col>
								</Row> */}
								{/* <Row nogutter><Col style={{ fontSize: "24px", fontWeight: 700, textAlign: "center" }}>
									{!date && dateState.toLocaleTimeString('pt-PT', {
										hour: '2-digit',
										minute: '2-digit',
										second: '2-digit'
									})}
									{date && date.toLocaleTimeString('pt-PT', {
										hour: '2-digit',
										minute: '2-digit',
										second: '2-digit'
									})}
								</Col></Row> */}
							</Col>
							<Col xs="content">
								{!snapshot && <Webcam
									minScreenshotWidth={1280}
									minScreenshotHeight={720}
									audio={false}
									ref={webcamRef}
									height={180}
									screenshotFormat="image/jpeg"
									videoConstraints={videoConstraints}
									style={{ borderRadius: "5px", /* boxShadow: "rgba(0, 0, 0, 0.16) 0px 1px 4px" */ }}
								/>}
								{snapshot && <img style={{ borderRadius: "5px", boxShadow: "rgba(0, 0, 0, 0.16) 0px 1px 4px" }} height={180} src={snapshot} />}
							</Col>
						</Row>
					</Col>
					<Col></Col>
				</Row>


				<Row gutterWidth={2} style={{ height: "60px", marginTop: "30px", marginBottom: "30px" }}>
					<Col></Col>
					{!snapshot && <Col xs="content" style={{ fontSize: "30px", fontWeight: 700 }}>MARQUE O NÚMERO DE COLABORADOR</Col>}
					{(nome && !confirmed) && <Col xs="content" style={{ fontWeight: 200, fontSize: "25px" }}>Confirma que é <span style={{ fontWeight: 600 }}>{nome}</span>?</Col>}
					{(nome && confirmed) && <Col xs="content" style={{ fontWeight: 200, fontSize: "25px" }}>Olá {nome}</Col>}
					<Col></Col>
				</Row>


				<Row gutterWidth={2} style={{ marginBottom: "10px" }}>
					<Col></Col>
					<Col xs="content" style={{ minWidth: "454px", fontSize: "40px", border: "solid 2px #d9d9d9", borderRadius: "3px", textAlign: "center" }}><span style={{ color: "#8c8c8c" }}>F00</span>{num}</Col>
					<Col></Col>
				</Row>
				{!snapshot && <><Row gutterWidth={2}>
					<Col></Col>
					<Col xs="content"><StyledButton onClick={() => onClick(1)} size="large">1</StyledButton></Col>
					<Col xs="content"><StyledButton onClick={() => onClick(2)} size="large">2</StyledButton></Col>
					<Col xs="content"><StyledButton onClick={() => onClick(3)} size="large">3</StyledButton></Col>
					<Col></Col>
				</Row>
					<Row gutterWidth={2}>
						<Col></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(4)} size="large">4</StyledButton></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(5)} size="large">5</StyledButton></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(6)} size="large">6</StyledButton></Col>
						<Col></Col>
					</Row>
					<Row gutterWidth={2}>
						<Col></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(7)} size="large">7</StyledButton></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(8)} size="large">8</StyledButton></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(9)} size="large">9</StyledButton></Col>
						<Col></Col>
					</Row>
					<Row gutterWidth={2}>
						<Col></Col>
						<Col xs="content"><StyledButton disabled={snapshot} onClick={() => onClick('C')} size="large">C</StyledButton></Col>
						<Col xs="content"><StyledButton onClick={() => onClick(0)} size="large">0</StyledButton></Col>
						<Col xs="content">
							{!snapshot && <StyledButton disabled={!parseInt(num)} onClick={capture} icon={<EnterOutlined />} size="large" />}
							{snapshot && <StyledButton onClick={reset} icon={<RedoOutlined />} size="large" />}
						</Col>
						<Col></Col>
					</Row>
				</>}
				{(nome && !confirmed) && <>
					{/* <Row>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Confirma que é <span style={{ fontWeight: 600 }}>{nome}</span>?</Col>
						<Col></Col>
					</Row> */}
					<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
						<Col></Col>
						<Col xs="content"><Button onClick={() => onConfirm(true)} icon={<CheckCircleOutlined style={{ fontSize: "80px" }} />} shape='circle' style={{ border: "none", minWidth: "130px", minHeight: "130px", color: "green" }}></Button></Col>
						<Col xs="content"><Button onClick={() => onConfirm(false)} icon={<CloseCircleOutlined style={{ fontSize: "80px" }} />} shape='circle' style={{ border: "none", minWidth: "130px", minHeight: "130px", color: "red" }}></Button></Col>
						<Col></Col>
					</Row>
				</>}
				{(nome && confirmed) && <>
					{/* <Row>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Olá {nome}</Col>
						<Col></Col>
					</Row> */}
					<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
						<Col></Col>
						<Col xs="content"><Button onClick={() => onFinish('in')} shape='circle' style={{ minWidth: "130px", minHeight: "130px", background: "green", color: "#fff" }}>Entrada</Button></Col>
						<Col xs="content"><Button onClick={() => onFinish("out")} shape='circle' style={{ minWidth: "130px", minHeight: "130px", background: "red", color: "#fff" }}>Saída</Button></Col>
						<Col></Col>
					</Row>
					<Row>
						<Col></Col>
						<Col xs="content"><Button type='link' size="large" onClick={reset} style={{}}>Eu não sou {nome}</Button></Col>
						<Col></Col>
					</Row>
				</>}
				{error.status === true && <Row gutterWidth={2} style={{ alignItems: "center", fontWeight: 400 }}>
					<Col></Col>
					<Col xs="content">
						<Alert
							banner
							message="Erro no registo"
							showIcon
							description={error.text}
							type="error"
							action={<Button onClick={reset} size="small" type="link" danger>Tentar novamente</Button>}
						/>
					</Col>
					<Col></Col>
				</Row>}
			</>}
		</Container>
	</>
	);
}