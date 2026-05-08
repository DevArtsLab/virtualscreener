import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { LipinskiResult } from "../api/client";

interface DruglikenessRadarProps {
  lipinski: LipinskiResult;
}

export function DruglikenessRadar({ lipinski }: DruglikenessRadarProps) {
  const data = [
    {
      axis: "MW",
      value: Math.min(100, (1 - lipinski.mw / 500) * 100),
      raw: `${lipinski.mw.toFixed(1)} Da`,
      limit: "≤500",
    },
    {
      axis: "LogP",
      value: Math.min(100, (1 - (lipinski.logp + 2) / 9) * 100),
      raw: lipinski.logp.toFixed(2),
      limit: "≤5",
    },
    {
      axis: "HBD",
      value: Math.min(100, (1 - lipinski.hbd / 5) * 100),
      raw: String(lipinski.hbd),
      limit: "≤5",
    },
    {
      axis: "HBA",
      value: Math.min(100, (1 - lipinski.hba / 10) * 100),
      raw: String(lipinski.hba),
      limit: "≤10",
    },
    {
      axis: "TPSA",
      value: Math.min(100, (1 - lipinski.tpsa / 140) * 100),
      raw: `${lipinski.tpsa.toFixed(1)} Å²`,
      limit: "≤140",
    },
    {
      axis: "RotBonds",
      value: Math.min(100, (1 - lipinski.rotatable_bonds / 10) * 100),
      raw: String(lipinski.rotatable_bonds),
      limit: "≤10",
    },
  ];

  return (
    <div className="w-full h-52">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="65%">
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "#94a3b8", fontSize: 10 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
          />
          <Radar
            name="Drug-likeness"
            dataKey="value"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.25}
            strokeWidth={1.5}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div className="rounded bg-slate-800 border border-slate-600 p-2 text-xs shadow-xl">
                  <p className="font-semibold text-slate-200">{d.axis}</p>
                  <p className="text-blue-300">{d.raw}</p>
                  <p className="text-slate-500">limit {d.limit}</p>
                </div>
              );
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
