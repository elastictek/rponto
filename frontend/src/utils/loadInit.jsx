import { getFilterRangeValues } from "utils";
import moment from 'moment';

export default (init, store = {}, props = {}, state = {}, fields) => {
    let df = { ...init };
    for (let v of fields) {
        if (store?.tstamp && state?.tstamp) {
            if (store.tstamp > state.tstamp) {
                if (props && props[v]) { df[v] = props[v]; }
                if (state && state[v]) { df[v] = state[v]; }
                if (store && store[v]) { df[v] = store[v]; }
            } else {
                if (props && props[v]) { df[v] = props[v]; }
                if (store && store[v]) { df[v] = store[v]; }
                if (state && state[v]) { df[v] = state[v]; }
            }
        } else {
            if (store?.tstamp) {
                if (props && props[v]) { df[v] = props[v]; }
                if (store && store[v]) { df[v] = store[v]; }
                if (state && state[v]) { df[v] = state[v]; }
            } else {
                if (props && props[v]) { df[v] = props[v]; }
                if (store && store[v]) { df[v] = store[v]; }
                if (state && state[v]) { df[v] = state[v]; }
            }
        }

    }
    return df;
}

export const fixRangeDates = (fields, values = {}) => {
    const _fieldValues = { ...values };
    const _filterValues = { ...values }
    for (let v of fields) {
        if ((v in _fieldValues) && (Array.isArray(_fieldValues[v]))) {
            let _fval = { formatted: {} };
            let _flval = {};
            for (let [i, x] of _fieldValues[v].entries()) {
                if (x) {
                    let f = (i === 0) ? "startValue" : "endValue";
                    _fval[f] = moment(x.replace("=", '').replace("<", "").replace(">", ""));
                    _fval.formatted = { ..._fval.formatted, [f]: x.replace("=", '').replace("<", "").replace(">", "") };
                    _flval[f] = x.replace("=", '').replace("<", "").replace(">", "");
                }
            }
            _filterValues[v] = getFilterRangeValues(_flval);
            _fieldValues[v] = _fval;
        }
    }
    return { fieldValues: _fieldValues, filterValues: _filterValues };
}