import React from "react";
const cls={LOW:'low',MODERATE:'moderate',ELEVATED:'elevated',HIGH:'high',VERY_HIGH:'very-high',EXTREME:'extreme'};
export default function RiskBadge({value}){const v=String(value||'NO DATA').toUpperCase().replace(/ /g,'_');return <span className={`badge ${cls[v]||'nodata'}`}><i/>{String(value||'NO DATA').replace('_',' ')}</span>}


