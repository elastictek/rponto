import React, { useEffect } from 'react';
import { Button, Alert } from "antd";
import { Container, Row, Col } from 'react-grid-system';
import styled from 'styled-components';
import { EnterOutlined, RedoOutlined, CloseCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import Webcam from "react-webcam";
import { useSubmitting } from "utils";
import { API_URL } from "config";
import { fetchPost } from "utils/fetch";
import Logo from 'assets/logo.svg';
import dayjs from 'dayjs';
import { DATETIME_FORMAT, MESSAGE_IN, MESSAGE_OUT } from 'config';
import { useImmer } from "use-immer";

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
	const webcamRef = React.useRef(null);
	const timeout = React.useRef(null);

	const [data, updateData] = useImmer({
		num: '',
		nome: '',
		error: { status: false, text: '' },
		snapshot: null,
		confirmed: false,
		dateInterval: new Date(),
		date: null,
		hsh: null,
		type: null,
		recon: null
	});

	const loadInterval = async () => {
		const request = (async () => updateData(draft => { draft.dateInterval = new Date(); }));
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
			submitting.trigger();
			try {
				const vals = { num: `F${data.num.padStart(5, '0')}` };
				const _ds = data.dateInterval
				updateData(draft => {
					draft.num = data.num.padStart(3, '0');
					draft.snapshot = imageSrc;
					draft.date = _ds;
				});
				let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", snapshot: imageSrc, timestamp: dayjs(_ds).format(DATETIME_FORMAT) } });
				if (response.data.status !== "error" && response.data?.rows?.length > 0) {
					updateData(draft => {
						draft.nome = `${response.data.rows[0].SRN_0} ${response.data.rows[0].NAM_0}`;
					});
				} else {
					updateData(draft => { draft.error = { status: true, text: "O número que indicou não existe!" } });
				}
				submitting.end();
			} catch (e) {
				updateData(draft => { draft.error = { status: true, text: e.message } });
				submitting.end();
			};

		},
		[webcamRef, data.num]
	);

	const reset = () => {
		if (timeout.current) {
			clearTimeout(timeout.current);
		}
		timeout.current = null;
		updateData(draft => {
			draft.num = '';
			draft.nome = '';
			draft.snapshot = null;
			draft.confirmed = false;
			draft.hsh = null;
			draft.date = null;
			draft.type = null;
			draft.error = { status: false, text: "" };
			draft.recon = null;
		});
		submitting.end();
	}

	const onClick = (v) => {
		if (v === "C") {
			updateData(draft => { draft.num = '' });
		} else if (v === "ENTER") {

		} else {
			if (data.num.length < 3) {
				updateData(draft => { draft.num = `${data.num}${v}` });
			}
		}
	}

	const onConfirm = async (v) => {
		if (v === true) {
			submitting.trigger();
			try {
				const vals = { num: `F${data.num.padStart(5, '0')}` };
				let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", save: true, snapshot: data.snapshot, timestamp: dayjs(data.date).format(DATETIME_FORMAT) } });
				if (response.data.status !== "error" && response.data.hsh) {
					console.log(response.data, "?????????????")
					updateData(draft => {
						draft.confirmed = true;
						draft.hsh = response.data.hsh;
						draft.recon = response.data.result;
					});
					timeout.current = setTimeout(reset, 10000);
				} else {
					updateData(draft => { draft.error = { status: true, text: response.data?.title } });
				}
				submitting.end();
			} catch (e) {
				updateData(draft => { draft.error = { status: true, text: e.message } });
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
			const vals = { num: `F${data.num.padStart(5, '0')}` };
			let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", hsh: data.hsh, save: true, type: t } });
			if (response.data.status !== "error") {
				updateData(draft => { draft.type = t });
				timeout.current = setTimeout(reset, 10000);
			} else {
				updateData(draft => { draft.error = { status: true, text: "Ocorreu um erro no registo." } });
				submitting.end();
			}
		} catch (e) {
			updateData(draft => { draft.error = { status: true, text: e.message } });
			submitting.end();
		};
	}

	return (<>
		<Container fluid style={{ fontWeight: 700 }}>

			{data.type &&
				<Row nogutter style={{ height: "70vh", display: "flex", alignItems: "center" }}>
					<Col>
						<Row>
							<Col></Col>
							<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>{data.type == "in" ? MESSAGE_IN : MESSAGE_OUT}</Col>
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

			{!data.type && <>

				<Row gutterWidth={2} style={{ margin: "10px 0px 10px 0px", alignItems: "center" }}>
					<Col>
						<Row nogutter style={{ background: "#f0f0f0", borderRadius: "5px", padding: "5px", display: "flex", alignItems: "center", marginBottom: "30px" }}>
							<Col style={{ textAlign: "left" }}><Logo style={{ width: "100px", height: "16px" }} /></Col>
							<Col style={{ textAlign: "center", fontSize: "24px", fontWeight: 700 }}>{!data.date && data.dateInterval.toLocaleTimeString('pt-PT', {
								hour: '2-digit',
								minute: '2-digit',
								second: '2-digit'
							})}
								{data.date && data.date.toLocaleTimeString('pt-PT', {
									hour: '2-digit',
									minute: '2-digit',
									second: '2-digit'
								})}</Col>
							<Col style={{ textAlign: "right", fontWeight: 400, fontSize: "14px" }}>
								{!data.date && data.dateInterval.toLocaleDateString('pt-PT', {
									day: '2-digit',
									month: 'long',
									year: 'numeric'
								})}
								{data.date && data.date.toLocaleDateString('pt-PT', {
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
										{!date && dateInterval.toLocaleDateString('pt-PT', {
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
									{!date && dateInterval.toLocaleTimeString('pt-PT', {
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
								{!data.snapshot && <Webcam
									minScreenshotWidth={1280}
									minScreenshotHeight={720}
									audio={false}
									ref={webcamRef}
									height={180}
									screenshotFormat="image/jpeg"
									videoConstraints={videoConstraints}
									style={{ borderRadius: "5px", /* boxShadow: "rgba(0, 0, 0, 0.16) 0px 1px 4px" */ }}
								/>}
								{data.snapshot && <img style={{ borderRadius: "5px", ...(data.recon === true || data.recon === false) && { boxShadow: data.recon === true ? "rgba(18, 168, 35, 0.8) 10px 10px 3px" : "rgba(248, 178, 17, 0.8) 10px 10px 3px" } }} height={180} src={data.snapshot} />}
							</Col>
						</Row>
					</Col>
					<Col></Col>
				</Row>

				<Row gutterWidth={2} style={{ height: "60px", marginTop: "30px", marginBottom: "30px" }}>
					<Col></Col>
					{!data.snapshot && <Col xs="content" style={{ fontSize: "30px", fontWeight: 700 }}>MARQUE O NÚMERO DE COLABORADOR</Col>}
					{(data.nome && !data.confirmed) && <Col xs="content" style={{ fontWeight: 200, fontSize: "25px" }}>Confirma que é <span style={{ fontWeight: 600 }}>{data.nome}</span>?</Col>}
					{(data.nome && data.confirmed) && <Col xs="content" style={{ fontWeight: 200, fontSize: "25px" }}>Olá {data.nome}</Col>}
					<Col></Col>
				</Row>


				<Row gutterWidth={2} style={{ marginBottom: "10px" }}>
					<Col></Col>
					<Col xs="content" style={{ minWidth: "454px", fontSize: "40px", border: "solid 2px #d9d9d9", borderRadius: "3px", textAlign: "center" }}><span style={{ color: "#8c8c8c" }}>F00</span>{data.num}</Col>
					<Col></Col>
				</Row>
				{!data.snapshot && <><Row gutterWidth={2}>
					<Col></Col>
					<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(1)} size="large">1</StyledButton></Col>
					<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(2)} size="large">2</StyledButton></Col>
					<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(3)} size="large">3</StyledButton></Col>
					<Col></Col>
				</Row>
					<Row gutterWidth={2}>
						<Col></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(4)} size="large">4</StyledButton></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(5)} size="large">5</StyledButton></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(6)} size="large">6</StyledButton></Col>
						<Col></Col>
					</Row>
					<Row gutterWidth={2}>
						<Col></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(7)} size="large">7</StyledButton></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(8)} size="large">8</StyledButton></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(9)} size="large">9</StyledButton></Col>
						<Col></Col>
					</Row>
					<Row gutterWidth={2}>
						<Col></Col>
						<Col xs="content"><StyledButton disabled={data.snapshot || submitting.state} onClick={() => onClick('C')} size="large">C</StyledButton></Col>
						<Col xs="content"><StyledButton disabled={submitting.state} onClick={() => onClick(0)} size="large">0</StyledButton></Col>
						<Col xs="content">
							{!data.snapshot && <StyledButton disabled={!parseInt(data.num) || submitting.state} onClick={capture} icon={<EnterOutlined />} size="large" />}
							{data.snapshot && <StyledButton disabled={submitting.state} onClick={reset} icon={<RedoOutlined />} size="large" />}
						</Col>
						<Col></Col>
					</Row>
				</>}
				{(data.nome && !data.confirmed) && <>
					{/* <Row>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Confirma que é <span style={{ fontWeight: 600 }}>{data.nome}</span>?</Col>
						<Col></Col>
					</Row> */}
					<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
						<Col></Col>
						<Col xs="content"><Button disabled={submitting.state} onClick={() => onConfirm(true)} icon={<CheckCircleOutlined style={{ fontSize: "80px" }} />} shape='circle' style={{ border: "none", minWidth: "130px", minHeight: "130px", color: "green" }}></Button></Col>
						<Col xs="content"><Button disabled={submitting.state} onClick={() => onConfirm(false)} icon={<CloseCircleOutlined style={{ fontSize: "80px" }} />} shape='circle' style={{ border: "none", minWidth: "130px", minHeight: "130px", color: "red" }}></Button></Col>
						<Col></Col>
					</Row>
				</>}
				{(data.nome && data.confirmed) && <>
					{/* <Row>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Olá {data.nome}</Col>
						<Col></Col>
					</Row> */}
					<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
						<Col></Col>
						<Col xs="content"><Button disabled={submitting.state} onClick={() => onFinish('in')} shape='circle' style={{ minWidth: "130px", minHeight: "130px", background: "green", color: "#fff" }}>Entrada</Button></Col>
						<Col xs="content"><Button disabled={submitting.state} onClick={() => onFinish("out")} shape='circle' style={{ minWidth: "130px", minHeight: "130px", background: "red", color: "#fff" }}>Saída</Button></Col>
						<Col></Col>
					</Row>
					<Row>
						<Col></Col>
						<Col xs="content"><Button disabled={submitting.state} type='link' size="large" onClick={reset} style={{}}>Eu não sou {data.nome}</Button></Col>
						<Col></Col>
					</Row>
				</>}
				{data.error.status === true && <Row gutterWidth={2} style={{ alignItems: "center", fontWeight: 400 }}>
					<Col></Col>
					<Col xs="content">
						<Alert
							banner
							message="Erro no registo"
							showIcon
							description={data.error.text}
							type="error"
							action={<Button disabled={submitting.state} onClick={reset} size="small" type="link" danger>Tentar novamente</Button>}
						/>
					</Col>
					<Col></Col>
				</Row>}
			</>}
		</Container>
	</>
	);
}