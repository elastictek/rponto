import React, { useEffect, useState } from 'react';
import { Route, Routes, useRoutes, BrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { Breadcrumb, Layout, Menu, theme, Drawer, notification } from 'antd';
import Logo from 'assets/logowhite.svg';
import styled, { css } from 'styled-components';
import MainMenu from './MainMenu';
const { Header, Content, Footer } = Layout;

export const LayoutContext = React.createContext({});

const StyledDrawer = styled(Drawer)`
    .ant-drawer-content{
        background:#2a3142;
    }
    .ant-drawer-header{
        border-bottom:none;
    }

`;


export default () => {
	const [api, contextHolder] = notification.useNotification();
	const colorBgContainer = "#fff";
	const [isDrawerVisible, setIsDrawerVisible] = useState(false);
	//   const {
	//     token: { colorBgContainer },
	//   } = theme.useToken();

	const onToggleDrawer = () => {
		setIsDrawerVisible(!isDrawerVisible);
	}



	const openNotification = (status, placement, message, description) => {
		if (status === "error") {
			api.error({
				message: message ? message : `Notificação`,
				description: description,
				placement
			});
		} else if (status === "success") {
			api.success({
				message: message ? message : `Notificação`,
				description: description,
				placement
			});
		} else {
			api.info({
				message: message ? message : `Notificação`,
				description: description,
				placement
			});
		}
	};

	return (
		<LayoutContext.Provider value={{ openNotification }}>
			<Layout className="layout">
				{contextHolder}
				<StyledDrawer
					title={
						<div style={{ display: "flex", flexDirection: "row", alignItems: "center" }}>
							<Logo style={{ width: "100px", height: "24px" }} />
						</div>
					}
					placement="left"
					closable={false}
					onClose={onToggleDrawer}
					open={isDrawerVisible}
				>
					<MainMenu dark onToggleDrawer={onToggleDrawer} />
				</StyledDrawer>
				<Header style={{ lineHeight: "32px", height: "32px", display: "flex", alignItems: "center", padding: "0px 0px" }}>
					<Logo style={{ width: "100px", height: "24px", cursor: "pointer" }} onClick={onToggleDrawer} />
					<Menu
						theme="dark"
						mode="horizontal"
						defaultSelectedKeys={['2']}
						items={[]}
					/>
				</Header>
				<Content style={{ padding: '0 5px', height: "calc(100vh - 32px)" }}>
					<Outlet />
					{/* <Breadcrumb style={{ margin: '16px 0' }}>
					<Breadcrumb.Item>Home</Breadcrumb.Item>
					<Breadcrumb.Item>List</Breadcrumb.Item>
					<Breadcrumb.Item>App</Breadcrumb.Item>
				</Breadcrumb> */}
					{/* <div className="site-layout-content" style={{ background: colorBgContainer }}>
					Content
				</div> */}
				</Content>
				{/* <Footer style={{ textAlign: 'center' }}>Ant Design ©2023 Created by Ant UED</Footer> */}
			</Layout>
		</LayoutContext.Provider>
	);
};
