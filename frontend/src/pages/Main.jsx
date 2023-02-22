import React, { useEffect } from 'react';
import { Button } from "antd-mobile";
import { Alert } from "antd";
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


const StyledAlert = styled.div`
	.ant-alert{
		display:flex;
		align-items:center;		
	}
	.ant-alert-message{
		font-size:16px;
		margin-bottom:0px;
		font-weight:600;
	}

`;

const Spin01 = styled.div`
.spinner {
	margin: 5px auto 0;
	width: 70px;
	text-align: center;
  }
  
  .spinner > div {
	width: 18px;
	height: 18px;
	background-color: #333;
  
	border-radius: 100%;
	display: inline-block;
	-webkit-animation: sk-bouncedelay 1.4s infinite ease-in-out both;
	animation: sk-bouncedelay 1.4s infinite ease-in-out both;
  }
  
  .spinner .bounce1 {
	-webkit-animation-delay: -0.32s;
	animation-delay: -0.32s;
  }
  
  .spinner .bounce2 {
	-webkit-animation-delay: -0.16s;
	animation-delay: -0.16s;
  }
  
  @-webkit-keyframes sk-bouncedelay {
	0%, 80%, 100% { -webkit-transform: scale(0) }
	40% { -webkit-transform: scale(1.0) }
  }
  
  @keyframes sk-bouncedelay {
	0%, 80%, 100% { 
	  -webkit-transform: scale(0);
	  transform: scale(0);
	} 40% { 
	  -webkit-transform: scale(1.0);
	  transform: scale(1.0);
	}
  }
`;

const Spinner01 = () => {
	return (<Spin01> <div className="spinner">
		<div className="bounce1"></div>
		<div className="bounce2"></div>
		<div className="bounce3"></div>
	</div></Spin01>);
}



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
		level: 0,
		num: '',
		nome: '',
		error: { status: false, text: '' },
		snapshot: null,
		dateInterval: new Date(),
		date: null,
		hsh: null,
		type: null,
		recon: null,
		foto: null,
		valid_filepaths: [],
		valid_nums: [],
		valid_names: []
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

	const reset = () => {
		if (timeout.current) {
			clearTimeout(timeout.current);
		}
		timeout.current = null;
		updateData(draft => {
			draft.level = 0;
			draft.num = '';
			draft.nome = '';
			draft.snapshot = null;
			draft.hsh = null;
			draft.date = null;
			draft.type = null;
			draft.error = { status: false, text: "" };
			draft.recon = null;
			draft.foto = null;
			draft.valid_filepaths = [];
			draft.valid_nums = [];
			draft.valid_names = [];
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
					console.log("response.data->",response.data)
					updateData(draft => {
						draft.level = 1;
						draft.recon = response.data.result;
						draft.foto = response.data.foto;
						draft.valid_nums = response.data?.valid_nums;
						draft.valid_filepaths = response.data?.valid_filepaths;
						draft.valid_names = response.data?.valid_names;
						draft.nome = `${response.data.rows[0].SRN_0} ${response.data.rows[0].NAM_0.toLowerCase().replace(/(^\w{1})|(\s+\w{1})/g, letter => letter.toUpperCase())}`;
					});
				} else {
					updateData(draft => { draft.error = { status: true, text: response.data?.title } });
				}
				submitting.end();
			} catch (e) {
				updateData(draft => { draft.error = { status: true, text: e.message } });
				submitting.end();
			};

		},
		[webcamRef, data.num]
	);

	const onConfirm = async (v) => {
		if (v === true) {
			submitting.trigger();
			try {
				const vals = { num: `F${data.num.padStart(5, '0')}` };
				let response = await fetchPost({ url: `${API_URL}/rponto/sql/`, filter: { ...vals }, parameters: { method: "SetUser", save: true, snapshot: data.snapshot, timestamp: dayjs(data.date).format(DATETIME_FORMAT) } });
				if (response.data.status !== "error" && response.data.hsh) {
					console.log("vonfirmmmmm...>",data)
					updateData(draft => {
						draft.level = 2;
						draft.hsh = response.data.hsh;
						// draft.recon = response.data.result;
						// draft.foto = response.data.foto;
						// draft.valid_nums = response.data?.valid_nums;
						// draft.valid_filepaths = response.data?.valid_filepaths;
						// draft.valid_names = response.data?.valid_names;
					});
					if (!response.data?.valid_nums || response.data?.valid_nums?.length === 0) {
						timeout.current = setTimeout(reset, 10000);
					}
				} else {
					updateData(draft => { draft.error = { status: true, text: response.data?.title } });
					timeout.current = setTimeout(reset, 15000);
				}
				submitting.end();
			} catch (e) {
				updateData(draft => { draft.error = { status: true, text: e.message } });
				timeout.current = setTimeout(reset, 15000);
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
				updateData(draft => { draft.type = t, draft.level = 3; });
				timeout.current = setTimeout(reset, 10000);
			} else {
				updateData(draft => { draft.error = { status: true, text: "Ocorreu um erro no registo! Por favor entre em contacto com os Recursos Humanos." } });
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
							<Col xs="content"><Button fill="none" color='primary' size="large" onClick={reset} style={{}}>Novo Registo</Button></Col>
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

									height={320}
									screenshotFormat="image/jpeg"
									videoConstraints={videoConstraints}
									style={{ borderRadius: "5px", /* boxShadow: "rgba(0, 0, 0, 0.16) 0px 1px 4px" */ }}
								/>}
								
								{((data.level==0 || data.level==1) && data.snapshot && !data.recon) && <img style={{ borderRadius: "5px" }} height={320} src={data.snapshot} />}
								{((data.level==1 || data.level==2) && data.recon && data.foto !== null) && <img style={{ borderRadius: "5px" }} height={320} src={data.foto} />}
								{(((data.level==1 || data.level==2) && data.foto === null && data.recon) || (data.level==2 && !data.recon)) && <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3PTWBSGcbGzM6GCKqlIBRV0dHRJFarQ0eUT8LH4BnRU0NHR0UEFVdIlFRV7TzRksomPY8uykTk/zewQfKw/9znv4yvJynLv4uLiV2dBoDiBf4qP3/ARuCRABEFAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghggQAQZQKAnYEaQBAQaASKIAQJEkAEEegJmBElAoBEgghgg0Aj8i0JO4OzsrPv69Wv+hi2qPHr0qNvf39+iI97soRIh4f3z58/u7du3SXX7Xt7Z2enevHmzfQe+oSN2apSAPj09TSrb+XKI/f379+08+A0cNRE2ANkupk+ACNPvkSPcAAEibACyXUyfABGm3yNHuAECRNgAZLuYPgEirKlHu7u7XdyytGwHAd8jjNyng4OD7vnz51dbPT8/7z58+NB9+/bt6jU/TI+AGWHEnrx48eJ/EsSmHzx40L18+fLyzxF3ZVMjEyDCiEDjMYZZS5wiPXnyZFbJaxMhQIQRGzHvWR7XCyOCXsOmiDAi1HmPMMQjDpbpEiDCiL358eNHurW/5SnWdIBbXiDCiA38/Pnzrce2YyZ4//59F3ePLNMl4PbpiL2J0L979+7yDtHDhw8vtzzvdGnEXdvUigSIsCLAWavHp/+qM0BcXMd/q25n1vF57TYBp0a3mUzilePj4+7k5KSLb6gt6ydAhPUzXnoPR0dHl79WGTNCfBnn1uvSCJdegQhLI1vvCk+fPu2ePXt2tZOYEV6/fn31dz+shwAR1sP1cqvLntbEN9MxA9xcYjsxS1jWR4AIa2Ibzx0tc44fYX/16lV6NDFLXH+YL32jwiACRBiEbf5KcXoTIsQSpzXx4N28Ja4BQoK7rgXiydbHjx/P25TaQAJEGAguWy0+2Q8PD6/Ki4R8EVl+bzBOnZY95fq9rj9zAkTI2SxdidBHqG9+skdw43borCXO/ZcJdraPWdv22uIEiLA4q7nvvCug8WTqzQveOH26fodo7g6uFe/a17W3+nFBAkRYENRdb1vkkz1CH9cPsVy/jrhr27PqMYvENYNlHAIesRiBYwRy0V+8iXP8+/fvX11Mr7L7ECueb/r48eMqm7FuI2BGWDEG8cm+7G3NEOfmdcTQw4h9/55lhm7DekRYKQPZF2ArbXTAyu4kDYB2YxUzwg0gi/41ztHnfQG26HbGel/crVrm7tNY+/1btkOEAZ2M05r4FB7r9GbAIdxaZYrHdOsgJ/wCEQY0J74TmOKnbxxT9n3FgGGWWsVdowHtjt9Nnvf7yQM2aZU/TIAIAxrw6dOnAWtZZcoEnBpNuTuObWMEiLAx1HY0ZQJEmHJ3HNvGCBBhY6jtaMoEiJB0Z29vL6ls58vxPcO8/zfrdo5qvKO+d3Fx8Wu8zf1dW4p/cPzLly/dtv9Ts/EbcvGAHhHyfBIhZ6NSiIBTo0LNNtScABFyNiqFCBChULMNNSdAhJyNSiECRCjUbEPNCRAhZ6NSiAARCjXbUHMCRMjZqBQiQIRCzTbUnAARcjYqhQgQoVCzDTUnQIScjUohAkQo1GxDzQkQIWejUogAEQo121BzAkTI2agUIkCEQs021JwAEXI2KoUIEKFQsw01J0CEnI1KIQJEKNRsQ80JECFno1KIABEKNdtQcwJEyNmoFCJAhELNNtScABFyNiqFCBChULMNNSdAhJyNSiECRCjUbEPNCRAhZ6NSiAARCjXbUHMCRMjZqBQiQIRCzTbUnAARcjYqhQgQoVCzDTUnQIScjUohAkQo1GxDzQkQIWejUogAEQo121BzAkTI2agUIkCEQs021JwAEXI2KoUIEKFQsw01J0CEnI1KIQJEKNRsQ80JECFno1KIABEKNdtQcwJEyNmoFCJAhELNNtScABFyNiqFCBChULMNNSdAhJyNSiECRCjUbEPNCRAhZ6NSiAARCjXbUHMCRMjZqBQiQIRCzTbUnAARcjYqhQgQoVCzDTUnQIScjUohAkQo1GxDzQkQIWejUogAEQo121BzAkTI2agUIkCEQs021JwAEXI2KoUIEKFQsw01J0CEnI1KIQJEKNRsQ80JECFno1KIABEKNdtQcwJEyNmoFCJAhELNNtScABFyNiqFCBChULMNNSdAhJyNSiEC/wGgKKC4YMA4TAAAAABJRU5ErkJggg==" />}
								{(data.level==1 && !data.recon && data.valid_names.length > 0) &&
									<Alert
										style={{ margin: "10px 0px", padding: "20px" }}
										message={<div style={{ fontSize: "16px", fontWeight: 400 }}><span style={{ fontWeight: 700 }}>Aviso!</span> O sistema identificou-o(a) como:</div>}
										description={<>
											{data.valid_names.map(v => {
												return (<div key={`U-${v.REFNUM_0}`}>
													<div style={{ marginTop: "10px", fontSize: "18px", fontWeight: 600 }}><span style={{ fontWeight: 400 }}>{v.REFNUM_0}</span> <span>{`${v.SRN_0} ${v.NAM_0.toLowerCase().replace(/(^\w{1})|(\s+\w{1})/g, letter => letter.toUpperCase())}`}</span></div>
												</div>);
											})}
										</>}
										type="warning"
										showIcon
									/>}
								{(data.level==1 && !data.recon && data.valid_names.length === 0) &&
									<Alert
										style={{ margin: "10px 0px", padding: "20px" }}
										message={<div style={{ fontSize: "18px", fontWeight: 400 }}><span style={{ fontWeight: 700 }}>Aviso!</span></div>}
										description={<div style={{ marginTop: "10px", fontSize: "16px", fontWeight: 400 }}>O sistema não o(a) identificou!</div>}
										type="warning"
										showIcon
									/>}
							</Col>
						</Row>
					</Col>
					<Col></Col>
				</Row>


				{(submitting.state) &&
					<Row gutterWidth={2} style={{ height: "60px", marginTop: "30px", marginBottom: "30px" }}>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "25px" }}>Aguarde um momento <Spinner01 /></Col>
						<Col></Col>
					</Row>
				}

				{data.error.status === true && <Row gutterWidth={2} style={{ alignItems: "center", fontWeight: 400 }}>
					<Col></Col>
					<Col xs="content">
						<StyledAlert>
							<Alert
								style={{ margin: "10px 0px", padding: "20px" }}
								message={<div style={{ fontSize: "18px", fontWeight: 400 }}><span style={{ fontWeight: 700 }}>Erro!</span></div>}
								showIcon
								description={<div style={{ fontSize: "16px" }}>{data.error.text}</div>}
								type="error"
								action={<Button disabled={submitting.state} onClick={reset} size="small" fill='none' color='danger'>Tentar novamente</Button>}
							/>
						</StyledAlert>
					</Col>
					<Col></Col>
				</Row>}





				{(!submitting.state && !data.error.status) && <>




					<Row gutterWidth={2} style={{ marginTop: "30px", marginBottom: "30px" }}>
						<Col></Col>
						{!data.snapshot && <Col xs="content" style={{ fontSize: "30px", fontWeight: 700 }}>MARQUE O NÚMERO DE COLABORADOR</Col>}
						{(data.level==1 && data.nome) && <Col xs="content" style={{ fontWeight: 200, fontSize: "25px", display: "flex", flexDirection: "column", alignItems: "center" }}>Confirma que é <div><span style={{ fontWeight: 600 }}>{data.nome}</span>?</div></Col>}
						{(data.level==2 && data.nome) && <Col xs="content" style={{ fontWeight: 200, fontSize: "25px", display: "flex", flexDirection: "column", alignItems: "center" }}>
							Olá
							<div><span style={{ fontWeight: 600 }}>{data.nome}</span></div>
						</Col>}
						<Col></Col>
					</Row>


					{!data.nome && <Row gutterWidth={2} style={{ marginBottom: "10px" }}>
						<Col></Col>
						<Col xs="content" style={{ minWidth: "454px", fontSize: "40px", border: "solid 2px #d9d9d9", borderRadius: "3px", textAlign: "center" }}><span style={{ color: "#8c8c8c" }}>F00</span>{data.num}</Col>
						<Col></Col>
					</Row>
					}
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
								{!data.snapshot && <StyledButton disabled={!parseInt(data.num) || submitting.state} onClick={capture} size="large"><EnterOutlined /></StyledButton>}
								{data.snapshot && <StyledButton disabled={submitting.state} onClick={reset} icon={<RedoOutlined />} size="large" />}
							</Col>
							<Col></Col>
						</Row>
					</>}
					{(data.level==1 && data.nome) && <>
						{/* <Row>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Confirma que é <span style={{ fontWeight: 600 }}>{data.nome}</span>?</Col>
						<Col></Col>
					</Row> */}
						<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
							<Col></Col>
							<Col xs="content"><Button disabled={submitting.state} onClick={() => onConfirm(true)} shape='rounded' style={{ border: "none", minWidth: "130px", minHeight: "130px", color: "#52c41a" }}><CheckCircleOutlined style={{ fontSize: "80px" }} /></Button></Col>
							<Col xs="content"><Button disabled={submitting.state} onClick={() => onConfirm(false)} shape='rounded' style={{ border: "none", minWidth: "130px", minHeight: "130px", color: "#f5222d" }}><CloseCircleOutlined style={{ fontSize: "80px" }} /></Button></Col>
							<Col></Col>
						</Row>
					</>}
					{(data.level==2 && data.nome) && <>
						{/* <Row>
						<Col></Col>
						<Col xs="content" style={{ fontWeight: 200, fontSize: "30px" }}>Olá {data.nome}</Col>
						<Col></Col>
					</Row> */}
						<Row style={{ margin: "20px 0px" }} gutterWidth={25}>
							<Col></Col>
							<Col xs="content"><Button disabled={submitting.state} onClick={() => onFinish('in')} shape='rounded' style={{ minWidth: "130px", minHeight: "130px", background: "#52c41a", color: "#fff", fontSize: "20px" }}>Entrada</Button></Col>
							<Col xs="content"><Button disabled={submitting.state} onClick={() => onFinish("out")} shape='rounded' style={{ minWidth: "130px", minHeight: "130px", background: "#f5222d", color: "#fff", fontSize: "20px" }}>Saída</Button></Col>
							<Col></Col>
						</Row>
						{/* <Row>
							<Col></Col>
							<Col xs="content"><Button disabled={submitting.state} type='link' size="large" onClick={reset} style={{ fontSize: "16px" }}>Eu não sou {data.nome}</Button></Col>
							<Col></Col>
						</Row> */}
					</>}
				</>
				}
			</>}
		</Container>
	</>
	);
}