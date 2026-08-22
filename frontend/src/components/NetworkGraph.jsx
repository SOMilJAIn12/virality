import { motion } from "framer-motion";
import AgentNode from "./AgentNode";

export default function NetworkGraph({ run, visibleIds, selectedId, onSelect }) {
  if (!run) return null;

  const nodeById = Object.fromEntries(run.nodes.map((n) => [n.id, n]));
  const visibleEdges = run.edges.filter(
    (e) => visibleIds.has(e.from) && visibleIds.has(e.to)
  );
  const visibleNodes = run.nodes.filter((n) => visibleIds.has(n.id));

  return (
    <svg
      viewBox="0 0 1000 520"
      className="h-[360px] w-full sm:h-[420px]"
      preserveAspectRatio="xMidYMid meet"
    >
      <g>
        {visibleEdges.map((e, i) => {
          const from = nodeById[e.from];
          const to = nodeById[e.to];
          if (!from || !to) return null;
          const isDirect = e.kind === "direct";
          return (
            <motion.line
              key={`${e.from}-${e.to}-${i}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={isDirect ? "#9A3B34" : "#C9C2B1"}
              strokeWidth={isDirect ? 1.1 : 0.7}
              strokeDasharray={isDirect ? undefined : "2,3"}
              initial={{ opacity: 0 }}
              animate={{ opacity: isDirect ? 0.85 : 0.55 }}
              transition={{ duration: 0.4 }}
            />
          );
        })}
      </g>
      <g>
        {visibleNodes.map((n) => (
          <AgentNode
            key={n.id}
            node={n}
            isSelected={selectedId === n.id}
            onSelect={onSelect}
          />
        ))}
      </g>
    </svg>
  );
}
