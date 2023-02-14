import React, { useEffect, useState, Suspense, lazy, useContext } from 'react';
//import ReactDOM from "react-dom";
import * as ReactDOM from 'react-dom/client';
import { Route, Routes, useRoutes, BrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { Spin, Input, Modal } from 'antd';
import { useMediaQuery } from 'react-responsive';
import './app.css'
import 'antd/dist/antd.compact.less';
import { SOCKET } from 'config';
import useWebSocket from 'react-use-websocket';
import { useImmer } from "use-immer";
import useMedia from 'utils/useMedia';
import { ModalProvider } from "react-modal-hook";
import { useSubmitting } from "utils";
import YScroll from "components/YScroll";
import { fetch, fetchPost } from "utils/fetch";
import { API_URL, ROOT_URL } from "config";
import GridLayout from './GridLayout';
import axios from 'axios';


const NotFound = lazy(() => import('./404'));
const Main = lazy(() => import('./Main'));
const Login = lazy(() => import('./Login'));
const RegistosRH = lazy(() => import('./RegistosRH'));


export const MediaContext = React.createContext({});
export const SocketContext = React.createContext({});
export const AppContext = React.createContext({});




// const MainLayout = () => {
//     const location = useLocation();
//     return (<>{(location.pathname === "/" || location.pathname === "/") && <GridLayout />}<Outlet /></>);
// }

const RenderRouter = () => {
    let element = useRoutes([
        {
            path: '/app',
            element: <Outlet />,
            children: [
                { path: "login", element: <Suspense fallback={<Spin />}><Login /></Suspense> },
                { path: "layout", element: <Suspense fallback={<Spin />}><GridLayout /></Suspense> },
                { path: "rh/registos", element: <Suspense fallback={<Spin />}><RegistosRH /></Suspense> }
            ]
        },
        {
            path: '/',
            element: <Main />,
            children: []
        },
        { path: "*", element: <Suspense fallback={<Spin />}><NotFound /></Suspense> }
    ]);
    return element;
};


const App = () => {
    const [width] = useMedia();
    const submitting = useSubmitting(true);
    const [auth, setAuth] = useState({ isAuthenticated: false, });

    useEffect(() => {
        const accessToken = localStorage.getItem('access_token');
        if (accessToken) {
            axios.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
            setAuth({ isAuthenticated: true, username: localStorage.getItem('username'), first_name: localStorage.getItem('first_name'), last_name: localStorage.getItem('last_name') })
        }
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        axios.defaults.headers.common.Authorization = null;
        setAuth({ isAuthenticated: false });
    };

    useEffect(() => {
        const controller = new AbortController();
        loadData({ signal: controller.signal });
        return (() => controller.abort());
    }, []);

    const loadData = async ({ signal }) => {
        submitting.end();
    }

    return (
        <BrowserRouter>
            <MediaContext.Provider value={width}>
                <AppContext.Provider value={{ auth, setAuth, handleLogout }}>
                    <SocketContext.Provider value={{}}>
                        <ModalProvider>
                            <RenderRouter />
                        </ModalProvider>
                    </SocketContext.Provider>
                </AppContext.Provider>
            </MediaContext.Provider>
        </BrowserRouter>
    );
}



export default App;
const container = document.getElementById("app");
const root = ReactDOM.createRoot(container);
root.render(<App />);