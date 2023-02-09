import React, { useEffect, useState, Suspense, lazy, useContext } from 'react';
import { Route, Routes, useRoutes, BrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { Button, Spin, Form, Space, Input, InputNumber, Tooltip, Menu, Collapse, Typography, Modal, Select, Tag, DatePicker, Alert, Drawer, Checkbox } from "antd";
import { Container, Row, Col } from 'react-grid-system';
import styled from 'styled-components';
import { EnterOutlined, RedoOutlined, WarningTwoTone } from '@ant-design/icons';
import Webcam from "react-webcam";
import { useSubmitting } from "utils";
import { API_URL } from "config";
import { fetch, fetchPost, cancelToken } from "utils/fetch";
import Logo from 'assets/logo.svg';

const StyledButton = styled(Button)`
	font-weight:700;
	width:100px!important;
	height:50px!important;
	font-size:20px;
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
	const [dateState, setDateState] = useState(new Date());
	const webcamRef = React.useRef(null);

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
				setNum(num.padStart(4, '0'));
				console.log(vals);
				let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", snapshot: imageSrc, timestamp: dateState } });
				if (response.data.status !== "error" && response.data?.rows?.length > 0) {
					setNome(`${response.data.rows[0].SRN_0} ${response.data.rows[0].NAM_0}`);
				} else {
					setError({ status: true, text: "O número que indicou não existe!" });
					submitting.end();
				}
			} catch (e) {
				setError({ status: true, text: e.message });
				submitting.end();
			};

		},
		[webcamRef, num]
	);

	const reset = () => {
		setNum('');
		setSnapshot(null);
		setNome("");
		setError({ status: false, text: "" });
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



	return (<>
		<Container fluid style={{ fontWeight: 700 }}>
			<Row gutterWidth={2} style={{ margin: "20px 0px 10px 0px", alignItems: "center" }}>
				<Col></Col>
				<Col style={{display:"flex",justifyContent:"center"}}>
					<Row gutterWidth={15}>
						<Col xs="content" style={{alignSelf:"center"}}>
							<Row nogutter>
								<Col></Col>
								<Col xs="content" style={{ alignSelf: "center" }}><Logo style={{ width: "200px", height: "48px" }} /></Col>
								<Col></Col>
							</Row>
							<Row nogutter>
								<Col style={{ fontSize: "16px", fontWeight: 400, textAlign: "center" }}>{dateState.toLocaleDateString('pt-PT', {
									day: '2-digit',
									month: 'long',
									year: 'numeric'
								})}
								</Col>
							</Row>
							<Row nogutter><Col style={{ fontSize: "24px", fontWeight: 700, textAlign: "center" }}>
								{dateState.toLocaleTimeString('pt-PT', {
									hour: '2-digit',
									minute: '2-digit',
									second: '2-digit'
								})}</Col></Row>
						</Col>
						<Col xs="content">
							{!snapshot && <Webcam
								audio={false}
								height={180}
								ref={webcamRef}
								screenshotFormat="image/jpeg"
								width={320}
								videoConstraints={videoConstraints}
							/>}
							{snapshot && <img height={180} src={snapshot} />}
						</Col>
					</Row>
				</Col>
				<Col></Col>
			</Row>
			{/* <Row gutterWidth={2} style={{ height: "188px" }}>
				<Col></Col>
				<Col xs="content" style={{}}>
					{!snapshot && <Webcam
						audio={false}
						height={180}
						ref={webcamRef}
						screenshotFormat="image/jpeg"
						width={320}
						videoConstraints={videoConstraints}
					/>}
					{snapshot && <img height={180} src={snapshot} />}
				</Col>
				<Col></Col>
			</Row> */}
			{!snapshot && <Row gutterWidth={2} style={{height:"60px"}}>
				<Col></Col>
				<Col xs="content" style={{ fontSize: "35px", fontWeight: 500 }}>Introduza o número de funcionário:</Col>
				<Col></Col>
			</Row>
			}
			{snapshot && <Row gutterWidth={2} style={{height:"60px"}}>
				<Col></Col>
				<Col xs="content" style={{ fontSize: "35px", fontWeight: 500 }}></Col>
				<Col></Col>
			</Row>
			}
			<Row gutterWidth={2} style={{ marginBottom: "10px" }}>
				<Col></Col>
				<Col xs="content" style={{ minWidth: "310px", fontSize: "40px", border: "solid 2px #1890ff", borderRadius: "3px", textAlign: "center" }}><span style={{ color: "#8c8c8c" }}>F0</span>{num}</Col>
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
			{nome && <>
				<Row>
					<Col></Col>
					<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Olá {nome}</Col>
					<Col></Col>
				</Row>
				<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
					<Col></Col>
					<Col xs="content"><Button shape='circle' style={{minWidth:"100px",minHeight:"100px",background:"green", color:"#fff"}}>Entrada</Button></Col>
					<Col xs="content"><Button shape='circle' style={{minWidth:"100px",minHeight:"100px",background:"red", color:"#fff"}}>Saída</Button></Col>
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
						message="Erro no registo"
						showIcon
						description={error.text}
						type="error"
						action={<Button onClick={reset} size="small" type="link" danger>Tentar novamente</Button>}
					/>
				</Col>
				<Col></Col>
			</Row>}
		</Container>
	</>
	);
}