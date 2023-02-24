import axios from "axios";
import { API_URL, ROOT_URL } from "config";
import { json } from "utils/object";
let refresh = false;
axios.interceptors.response.use(resp => resp, async error => {
  const _auth =json(localStorage.getItem('auth'));
  if (error.response.status === 401 && !_auth?.refresh_token){
    window.location.href = '/app/login';
  }
  if (error.response.status === 401 && !refresh && _auth?.refresh_token) {
     refresh = true;
     const response = await axios.post(`${API_URL}/token/refresh/`, {refresh:_auth.refresh_token}, {withCredentials: true});
    if (response.status === 200) {
       axios.defaults.headers.common['Authorization'] = `Bearer 
       ${response.data['access']}`;
       _auth.access_token=response.data.access;
       _auth.access_token=response.data.refresh;
       localStorage.setItem('auth',JSON.stringify(_auth));
       return axios(error.config);
    }
  }
refresh = false;
return error;
});