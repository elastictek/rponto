import React, { useEffect, useState, useCallback, useRef, useContext, Suspense, lazy } from 'react';
import { createUseStyles } from 'react-jss';
import styled from 'styled-components';
import {  fetchPost } from "utils/fetch";

import { Container, Row, Col, Visible, Hidden } from 'react-grid-system';


import { Space, Typography, Button, Select, Modal, InputNumber, Checkbox, Badge,Tag } from "antd";
import { API_URL } from 'config';



export default ({ id, ofid, of_des }) => {
    return (
        <>{ofid ? <Tag style={{ fontWeight: 600 }}>{ofid}</Tag> : of_des}</>
    );
}