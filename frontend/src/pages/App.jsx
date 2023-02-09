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

const NotFound = lazy(() => import('./404'));
const Main = lazy(() => import('./Main'));


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
            path: '/',
            element: <Main/>,
            children: [
                // { path: "validateReellings", element: <Suspense fallback={<Spin />}><BobinagensValidarList /></Suspense> }, //TO REMOVE
                // { path: "bobines/validarlist", element: <Suspense fallback={<Spin />}><BobinesValidarList /></Suspense> },
                // { path: "ofabricolist", element: <Suspense fallback={<Spin />}><OFabricoList /></Suspense> },
                // { path: "sorders", element: <Suspense fallback={<Spin />}><SOrders /></Suspense> },
                // { path: "pick", element: <Suspense fallback={<Spin />}><FormPickMP /></Suspense> },
                // { path: "paletes/palete", element: <Suspense fallback={<Spin />}><FormPalete /></Suspense> },
                // { path: "ofabricoshortlist", element: <Suspense fallback={<Spin />}><OFabricoShortList /></Suspense> },
                // { path: "stocklist", element: <Suspense fallback={<Spin />}><StockList /></Suspense> },
                // { path: "artigos/mpbufferlist", element: <Suspense fallback={<Spin />}><MPBufferList /></Suspense> },
                // { path: "logslist/lineloglist", element: <Suspense fallback={<Spin />}><LineLogList /></Suspense> },
                // { path: "logslist/stockloglist", element: <Suspense fallback={<Spin />}><StockLogList /></Suspense> },
                // { path: "logslist/comsumptionneedloglist", element: <Suspense fallback={<Spin />}><ConsumptionNeedLogList /></Suspense> },
                // { path: "bobines/bobinesoriginaislist", element: <Suspense fallback={<Spin />}><BobinesOriginaisList /></Suspense> },
                // { path: "bobines/bobineslist", element: <Suspense fallback={<Spin />}><BobinesList /></Suspense> },
                // { path: "bobinagens/fixlotes", element: <Suspense fallback={<Spin />}><BobinagensFixLotes /></Suspense> },
                // { path: "currentline/menuactions", element: <Suspense fallback={<Spin />}><FormMenuActions /></Suspense> },
                // { path: "expedicoes/timearmazem", element: <Suspense fallback={<Spin />}><ExpedicoesTempoList /></Suspense> },

                // { path: "picking/recicladolist", element: <Suspense fallback={<Spin />}><RecicladoList /></Suspense> },
                // { path: "picking/pickreciclado", element: <Suspense fallback={<Spin />}><PickReciclado /></Suspense> },
                // { path: "picking/pickgranuladolist", element: <Suspense fallback={<Spin />}><PickGranuladoList /></Suspense> },
                // { path: "picking/picknwlist", element: <Suspense fallback={<Spin />}><PickNWList /></Suspense> },

                // { path: "ofabrico/checklists", element: <Suspense fallback={<Spin />}><CheckLists /></Suspense> },

                // { path: "artigos/nwlist", element: <Suspense fallback={<Spin />}><NwList /></Suspense> },
                // { path: "artigos/consumoslist", element: <Suspense fallback={<Spin />}><ConsumosList /></Suspense> },
                // { path: "artigos/granuladobufferlinelist", element: <Suspense fallback={<Spin />}><GranuladoBufferLineList /></Suspense> },
                // { path: "artigos/granuladolist", element: <Suspense fallback={<Spin />}><GranuladoList /></Suspense> },
                // { path: "artigos/mpalternativas", element: <Suspense fallback={<Spin />}><MPAlternativas /></Suspense> },
                // { path: "devolucoes/devolucoeslist", element: <Suspense fallback={<Spin />}><DevolucoesList /></Suspense> },
                // { path: "planeamento/etapascortes", element: <Suspense fallback={<Spin />}><FormEtapasCortes /></Suspense> },

                // { path: "paletes/paleteslist", element: <Suspense fallback={<Spin />}><PaletesList /></Suspense> },

                // { path: "picking/base", element: <Suspense fallback={<Spin />}><BasePick /></Suspense> },

                /*  { path: "ordemfabrico/formdetails", element: <Suspense fallback={<Spin />}><OFDetails /></Suspense> }, */
            ]
        },
        { path: "*", element: <Suspense fallback={<Spin />}><NotFound /></Suspense> }
    ]);
    return element;
};




const App = () => {
    const [width] = useMedia();
    const submitting = useSubmitting(true);

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
                <AppContext.Provider value={{}}>
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