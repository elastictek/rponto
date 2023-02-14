// Login.js
import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Button, Alert, Modal, Input, Space, Checkbox } from "antd";
import { Container, Row, Col } from 'react-grid-system';
import styled from 'styled-components';
import YScroll from "components/YScroll";
import { useSubmitting } from "utils";
import { API_URL } from "config";
import { fetchPost } from "utils/fetch";
import Logo from 'assets/logo.svg';
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { AppContext } from './App';
import jwt_decode from 'jwt-decode';



export default () => {
    const navigate = useNavigate();
    const submitting = useSubmitting(true);
    const { auth, setAuth, handleLogout } = useContext(AppContext);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [remember, setRemember] = useState(false);

    useEffect(() => {
        const listener = async event => {
            if (event.code === "Enter" || event.code === "NumpadEnter") {
                await handleSubmit();
                event.preventDefault();
            }
        };
        document.addEventListener("keydown", listener);
        const controller = new AbortController();
        loadData({ signal: controller.signal });
        return (() => { controller.abort(); document.removeEventListener("keydown", listener); });
    }, []);

    const loadData = async ({ signal }) => {
        submitting.end();
    }

    const handleSubmit = async (e) => {
        if (e){e.preventDefault();}
        console.log(username,password)
        const response = await axios.post('/api/token/', { username, password, remember });
        const decodedToken = jwt_decode(response.data.access);
        localStorage.setItem('access_token', response.data.access);
        localStorage.setItem('refresh_token', response.data.refresh);
        localStorage.setItem('username', username);
        localStorage.setItem('first_name', decodedToken.first_name);
        localStorage.setItem('last_name', decodedToken.last_name);
        setAuth({ isAuthenticated: true, username, first_name: decodedToken.first_name, last_name: decodedToken.last_name });
        navigate('/app/layout');
    };

    const clear = () => {
        setUsername('');
        setPassword('');
        setRemember(false);
    }

    return (
        <Modal open width={400} closable={false} footer={null}>
            {auth.isAuthenticated && <div style={{ display: "flex", justifyItems: "center", flexDirection: "column" }}>
                <div style={{ fontWeight: 800, fontSize: "16px", textAlign: "center" }}>{auth?.first_name} {auth?.last_name}</div>
                <Button type="link" size='large' onClick={handleLogout}>Logout</Button>
            </div>}
            <Space size={30}>
                <Space direction="vertical" size={5}>
                    {!auth.isAuthenticated && <><div style={{ fontWeight: 600 }}>Login</div>
                        <Input placeholder="Login" value={username} onChange={(e) => setUsername(e.target.value)} />
                        <div style={{ fontWeight: 600 }}>Password</div>
                        <Input.Password
                            value={password}
                            placeholder="Password"
                            onChange={(e) => setPassword(e.target.value)}
                            iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
                        />
                        <Checkbox checked={remember} onChange={(v) => setRemember(!remember)}>Lembrar-me neste dispositivo</Checkbox>
                    </>}
                </Space>
                {!auth.isAuthenticated && <><div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ fontWeight: 400 }}>Registo de Ponto</div>
                    <Logo style={{ fontSize: "140px", height: "50px" }} />
                </div></>}
            </Space>
            {!auth.isAuthenticated && <div style={{ display: "flex", justifyContent: "right", marginTop: "20px" }}>
                <Space>
                    <Button onClick={clear}>Cancelar</Button>
                    <Button onClick={handleSubmit} type="primary">Entrar</Button>
                </Space>
            </div>}
        </Modal>



    );
};