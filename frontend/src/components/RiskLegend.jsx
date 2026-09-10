import React from "react";
import RiskBadge from './RiskBadge';
export default function RiskLegend(){return <div className="legend"><div className="legend-title">DYNAMIC RISK</div>{['LOW','MODERATE','ELEVATED','HIGH','VERY_HIGH','EXTREME'].map(x=><RiskBadge key={x} value={x}/>)}</div>}


